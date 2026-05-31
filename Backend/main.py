from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import os
import ee
from models import AnalysisRequest
from services import run_spatial_analysis

from fastapi.staticfiles import StaticFiles

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
            pass 
        stats = run_spatial_analysis(request.geometry)

        if not stats or stats.get('outside_roi'):
            return {
                "outside_roi": True,
                "confidence": "NONE",
                "error": "This location is outside our current coverage area. Bhumi Drishti currently supports land analysis in Sunsari and surrounding Terai districts of Nepal only."
            }

        imputed = stats.get('null_imputed', [])
        core_risks_missing = all(x in imputed for x in ['flood_risk', 'landslide_risk', 'agri_suitability'])
        
        if core_risks_missing:
            return {
                "outside_roi": True,
                "confidence": "NONE",
                "error": "Insufficient raster data found for this plot. This location is outside our high-resolution coverage area."
            }

        risk_summary_text = generate_risk_summary(stats)

        def gs(category, metric, default=0):
            return stats.get(category, {}).get(metric, default)

        confidence  = stats.get('confidence', 'UNKNOWN')
        buffer_tier = stats.get('buffer_tier', 0)
        buffer_m    = stats.get('buffer_m', 0)
        anomaly     = stats.get('anomaly_flag', False)
        outside_roi = stats.get('outside_roi', False)

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

            