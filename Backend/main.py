from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import os
import ee
from models import AnalysisRequest
from services import run_spatial_analysis

from ai_summary import generate_risk_summary, chat_about_land
from pdf_report import generate_pdf_report
from dotenv import load_dotenv

from fastapi.staticfiles import StaticFiles
load_dotenv()

print("startup environment OPENAI_API_KEY=", os.environ.get("OPENAI_API_KEY"))

app=FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    ee.Initialize(project='flood-482116')
    print("Earth Engine Initialized Successfully")
except Exception as e:
    print(f"Auth Error: {e}")

class ChatRequest(BaseModel):
    question: str
    land_data: dict


class ReportRequest(BaseModel):
    analysis_data: dict

def _pct(v: float) -> float:
    return round(v * 100, 1)

@app.post("/analyze-plot")
async def analyze(request: AnalysisRequest):
    try:
        # ── 1. Coordinate Check (Pre-GEE) ──────────────────────────────
        # Supported bounds: lon: 86.5 to 88.5, lat: 26.2 to 27.5
        try:
            coords = request.geometry.get('coordinates', [])[0]
            avg_lon = sum(c[0] for c in coords) / len(coords)
            avg_lat = sum(c[1] for c in coords) / len(coords)
            if not (86.5 <= avg_lon <= 88.5 and 26.2 <= avg_lat <= 27.5):
                return {
                    "outside_roi": True,
                    "confidence": "NONE",
                    "error": "This location is outside our current coverage area. Bhumi Drishti currently supports land analysis in Sunsari and surrounding Terai districts of Nepal only."
                }
        except:
            pass # Fallback to GEE check if geometry structure is unusual

        # ── 2. Fetch GEE Stats ─────────────────────────────────────────
        stats = run_spatial_analysis(request.geometry)

        if not stats or stats.get('outside_roi'):
            return {
                "outside_roi": True,
                "confidence": "NONE",
                "error": "This location is outside our current coverage area. Bhumi Drishti currently supports land analysis in Sunsari and surrounding Terai districts of Nepal only."
            }

        # ── 3. Data Integrity Check (Post-GEE) ─────────────────────────
        # If all core risk bands were missing and imputed with medians, it's outside ROI
        imputed = stats.get('null_imputed', [])
        core_risks_missing = all(x in imputed for x in ['flood_risk', 'landslide_risk', 'agri_suitability'])
        
        if core_risks_missing:
            return {
                "outside_roi": True,
                "confidence": "NONE",
                "error": "Insufficient raster data found for this plot. This location is outside our high-resolution coverage area."
            }

        # Generate AI risk summary (uses full data dict)
        risk_summary_text = generate_risk_summary(stats)

        # Convenience accessors
        def gs(category, metric, default=0):
            return stats.get(category, {}).get(metric, default)

        confidence  = stats.get('confidence', 'UNKNOWN')
        buffer_tier = stats.get('buffer_tier', 0)
        buffer_m    = stats.get('buffer_m', 0)
        anomaly     = stats.get('anomaly_flag', False)
        outside_roi = stats.get('outside_roi', False)

        # ── Terrain Classification & Risk Logic ────────────────────────
        slope_mean = gs('slope', 'mean')
        terrain_type = "FLAT" if slope_mean < 5 else "SLOPED"

        # Landslide specific display logic
        ls_mean = _pct(gs('landslide_risk', 'mean'))
        ls_max  = _pct(gs('landslide_risk', 'max'))
        
        ls_display = {
            "category":  "landslide",
            "title":     "Landslide Risk",
            "value":     ls_mean,
            "unit":      "%",
            "terrain":   terrain_type,
        }

        if terrain_type == "FLAT":
            ls_display.update({
                "sub_value": None, # Signal to UI to hide numeric peak
                "sub_label": "Not Applicable",
                "sub_note":  "Terrain is flat; landslide risk is negligible. Localized spikes may be due to data noise."
            })
        else:
            # Check for anomaly: low slope but high peak (likely noise/resolution artifact)
            is_anomaly = slope_mean < 8 and (ls_max > ls_mean * 3)
            ls_display.update({
                "sub_value": ls_max,
                "sub_label": "Low Confidence Anomaly" if is_anomaly else "Localized Hotspot Risk",
                "sub_note":  "Represents the highest-risk point within the plot boundary, not the entire land."
            })

        # Build the response payload
        response_payload = {
            "metadata": {
                "source":       stats.get('asset_version', 'Bhumi_Full_Production_Final'),
                "confidence":   confidence,
                "buffer_tier":  buffer_tier,
                "buffer_m":     buffer_m,
                "area_m2":      stats.get('area_m2', None),
                "null_imputed": stats.get('null_imputed', []),
                "anomaly_flag": anomaly,
                "outside_roi":  outside_roi,
                "terrain_type": terrain_type,
                "note": (
                    "Score derived from a 60 m buffer around the plot centroid. "
                    "The parcel is smaller than one 30 m satellite pixel. Results are indicative only; "
                    "on-site verification is recommended before any land-use decision."
                    if confidence == "LOW" else
                    "Analysis based on Bhumi_Full_Production_Final GEE asset (30 m resolution)."
                ),
            },
            "quantitative_data": {
                "indicators": [
                    {
                        "category":  "flood",
                        "title":     "Flood Risk",
                        "value":     _pct(gs('flood_prob', 'mean')),
                        "sub_value": _pct(gs('flood_prob', 'max')),
                        "sub_label": "Peak Risk",
                        "unit":      "%",
                    },
                    ls_display,
                    {
                        "category":  "agri",
                        "title":     "Agricultural Suitability",
                        "value":     _pct(gs('agri_prob', 'mean')),
                        "sub_value": _pct(gs('agri_prob', 'max')),
                        "sub_label": "Peak Suitability",
                        "unit":      "%",
                    },
                ],
                "details": {
                    # Terrain
                    "slope":          gs('slope', 'mean'),
                    "elevation":      gs('elevation', 'mean'),
                    "slope_std":      stats.get('slope_std', 0),
                    "curvature":      stats.get('curvature', 0),

                    # LULC
                    "lulc":           stats.get('lulc', {}).get('label', 'Unknown'),
                    "lulc_code":      stats.get('lulc', {}).get('code', None),

                    # Vegetation — NDVI raw intentionally omitted per contract
                    "ndvi_wet":       gs('vegetation', 'ndvi_wet'),
                    "ndvi_delta":     gs('vegetation', 'ndvi_delta'),
                    "ndvi_note":      "vegetation index data not discriminating in this area; ndvi_wet and ndvi_delta used by model instead.",

                    # Soil
                    "soil_clay_pct":  stats.get('soil_clay', {}).get('percentage', 0),

                    # Climate
                    "rainfall":       gs('rainfall', 'annual_mm'),

                    # Hydrology
                    "twi":            gs('twi', 'mean'),
                    "spi":            gs('spi', 'mean'),
                    "spi_label":      stats.get('spi', {}).get('interpretation', ''),
                    "dist_river_m":   stats.get('dist_river', {}).get('metres', None),
                    "flow_acc_log":   stats.get('flow_acc_log', 0),
                },
                "risk_summary": risk_summary_text,
            },
            # Full raw stats forwarded for PDF / Chat reuse
            "raw_stats": stats,
        }

        print(f"DEBUG: Response payload confidence={confidence}, anomaly={anomaly}")
        return response_payload

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/generate-report")
async def generate_report(request: ReportRequest):
    """Generate and stream a Due Diligence PDF report."""
    try:
        pdf_buffer = generate_pdf_report(request.analysis_data)
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=bhumi_drishti_report.pdf"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")


@app.post("/chat-land")
async def chat_land(request: ChatRequest):
    """Answer user questions about their analyzed land plot."""
    try:
        answer = chat_about_land(request.question, request.land_data)
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    import sys
    print(f"DEBUG: Python: {sys.executable}")
    print("DEBUG: Starting server on port 8081...")
    uvicorn.run("main:app", host="127.0.0.1", port=8081, reload=True)


# Mount Frontend at the end to avoid overriding API routes
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # goes up to project root
app.mount("/", StaticFiles(directory=BASE_DIR / "Frontend", html=True), name="frontend")