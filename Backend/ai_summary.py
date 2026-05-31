"""
ai_summary.py — Bhumi Drishti AI narrative layer
=================================================
Generates LLM-backed summaries and answers user questions about their land
plot. Strictly follows the band contract for Bhumi_Full_Production_Final:

  • Risk scores  → reported as % to 1 d.p.  (0.734 → "73.4%")
  • soil_clay    → raw g/kg ÷ 10 → % content (already converted before LLM)
  • dist_river   → exp(log_val) - 1 → metres  (already converted before LLM)
  • NDVI (raw)   → NEVER reported; ndvi_wet + ndvi_delta used instead
  • SPI          → closer to 0 means HIGHER erosion risk
  • Anomaly flag → surfaces a data quality warning
  • LOW conf.    → mandatory 60 m buffer caveat force-appended
"""

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
import os
from dotenv import load_dotenv
ai
load_dotenv()
"""
ai_summary.py — Bhumi Drishti AI narrative layer
=================================================
Generates LLM-backed summaries and answers user questions about their land
plot. Strictly follows the band contract for Bhumi_Full_Production_Final:

  • Risk scores  → reported as % to 1 d.p.  (0.734 → "73.4%")
  • soil_clay    → raw g/kg ÷ 10 → % content (already converted before LLM)
  • dist_river   → exp(log_val) - 1 → metres  (already converted before LLM)
  • NDVI (raw)   → NEVER reported; ndvi_wet + ndvi_delta used instead
  • SPI          → closer to 0 means HIGHER erosion risk
  • Anomaly flag → surfaces a data quality warning
  • LOW conf.    → mandatory 60 m buffer caveat force-appended
"""

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
import os
from dotenv import load_dotenv

load_dotenv()

# ── Mandatory caveat — verbatim per contract ───────────────────────────────────
LOW_CONFIDENCE_CAVEAT = (
    "Score derived from a 60 m buffer around the plot centroid. The parcel "
    "is smaller than one 30 m satellite pixel. Results are indicative only; "
    "on-site verification is recommended before any land-use decision."
)

# ── Shared formatting rules injected into every prompt ────────────────────────
_BASE_RULES = """\
RULES (follow exactly, no exceptions):
- Plain prose only. No markdown, no bullets, no headers.
- Risk scores to 1 decimal place (e.g. "73.4%"). Never round to whole numbers.
- Never mention raw NDVI or values 0.405–0.411. Reference ndvi_wet and ndvi_delta only.
- soil_clay and dist_river are pre-converted — report % and metres as given.
- SPI: a value closer to 0 means higher stream-power / erosion risk.
- No filler openers ("This analysis shows", "It is important to note", "Based on the data").
- Never invent values — every number must come from the PLOT DATA block below.\
"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _pct(v: float) -> str:
    """Convert decimal to percentage string (1 d.p.)"""
    return f"{v * 100:.1f}%"
"""
ai_summary.py — Bhumi Drishti AI narrative layer
=================================================
Generates LLM-backed summaries and answers user questions about their land
plot. Strictly follows the band contract for Bhumi_Full_Production_Final.
"""

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
import os
from dotenv import load_dotenv

load_dotenv()

# ── Mandatory caveat — verbatim per contract ───────────────────────────────────
LOW_CONFIDENCE_CAVEAT = (
    "Score derived from a 60 m buffer around the plot centroid. The parcel "
    "is smaller than one 30 m satellite pixel. Results are indicative only; "
    "on-site verification is recommended before any land-use decision."
)

# ── Shared formatting rules ────────────────────────────────────────────────────
_BASE_RULES = """\
RULES (follow exactly, no exceptions):
- Plain prose only. No markdown, no bullets, no headers.
- Risk scores to 1 decimal place (e.g. "73.4%"). Never round to whole numbers.
- Never mention raw NDVI or values 0.405–0.411. Reference ndvi_wet and ndvi_delta only.
- soil_clay and dist_river are pre-converted — report % and metres as given.
- SPI: a value closer to 0 means higher stream-power / erosion risk.
- No filler openers ("This analysis shows", "It is important to note", "Based on the data").
- Never invent values — every number must come from the PLOT DATA block below.\
"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _pct(v: float) -> str:
    """Convert decimal to percentage string (1 d.p.)"""
    return f"{v * 100:.1f}%"


def _build_context_block(data: dict) -> str:
    """
    Converts the services.py output dict into a readable context block.
    All band-contract unit conversions are applied here so the LLM always
    sees final human-readable values.
    """
    flood = data.get('flood_prob', {})
    ls    = data.get('landslide_risk', {})
    agri  = data.get('agri_prob', {})
    slope = data.get('slope', {})
    elev  = data.get('elevation', {})
    twi   = data.get('twi', {})
    spi   = data.get('spi', {})
    veg   = data.get('vegetation', {})
    rain  = data.get('rainfall', {})
    clay  = data.get('soil_clay', {})
    lulc  = data.get('lulc', {})
    dist  = data.get('dist_river', {})

    confidence  = data.get('confidence', 'UNKNOWN')
    buffer_tier = data.get('buffer_tier', 0)
    anomaly     = data.get('anomaly_flag', False)
    outside_roi = data.get('outside_roi', False)
    imputed     = data.get('null_imputed', [])

    lines = [
        "=== PLOT DATA (Bhumi_Full_Production_Final) ===",
        "",
        f"Confidence : {confidence}  (buffer_tier={buffer_tier},  area={data.get('area_m2', 'N/A')} m²)",
        "",
        "RISK SCORES",
        f"  Flood risk       : mean={_pct(flood.get('mean', 0))}  peak={_pct(flood.get('max', 0))}",
        f"  Landslide risk   : mean={_pct(ls.get('mean', 0))}  peak={_pct(ls.get('max', 0))}",
        f"  Agri suitability : mean={_pct(agri.get('mean', 0))}  peak={_pct(agri.get('max', 0))}",
        "",
        "TERRAIN",
        f"  Elevation : mean={elev.get('mean', 0):.0f} m  (min={elev.get('min', 0):.0f}, max={elev.get('max', 0):.0f})",
        f"  Slope     : mean={slope.get('mean', 0):.1f}°  max={slope.get('max', 0):.1f}°  std={data.get('slope_std', 0):.2f}°",
        f"  Curvature : {data.get('curvature', 0):.3f}",
        "",
        "HYDROLOGY",
        f"  TWI              : {twi.get('mean', 0):.2f}  (higher = wetter / more flood-prone)",
        f"  SPI              : {spi.get('mean', 0):.3f}  → {spi.get('interpretation', 'N/A')}",
        f"  Distance to river: {dist.get('metres', 0)} m",
        f"  Flow acc (log)   : {data.get('flow_acc_log', 0):.3f}",
        "",
        "VEGETATION  (raw NDVI non-informative — use wet/delta only)",
        f"  ndvi_wet   : {veg.get('ndvi_wet', 0):.3f}  (Sentinel-2 wet season)",
        f"  ndvi_delta : {veg.get('ndvi_delta', 0):.3f}  (wet−dry crop signal)",
        "",
        "CLIMATE & SOIL",
        f"  Rainfall   : {rain.get('annual_mm', 0):.0f} mm/yr  (CHIRPS 2024)",
        f"  Soil clay  : {clay.get('percentage', 0):.1f}%  (raw={clay.get('raw_g_per_kg', 0):.1f} g/kg)",
        "",
        "LAND USE",
        f"  LULC : {lulc.get('label', 'Unknown')}  (ESA WorldCover code={lulc.get('code', '?')})",
    ]

    warnings = []
    if anomaly:
        warnings.append(
            "ANOMALY: flood_risk=0.0, landslide<0.04, agri=0.0 — "
            "possible Platt calibration collapse; report raw predictors to Bhumi team."
        )
    if outside_roi:
        warnings.append("LOCATION: Elevation outside model ROI (75–1267 m) — results may be unreliable.")
    if imputed:
        warnings.append(f"NULL IMPUTATION: Bands {imputed} used ROI-wide medians.")
    if confidence == 'LOW':
        warnings.append(f"LOW CONFIDENCE: 60 m buffer applied — {LOW_CONFIDENCE_CAVEAT}")

    if warnings:
        lines += ["", "WARNINGS"] + [f"  ⚠ {w}" for w in warnings]

    return "\n".join(lines)
"""
ai_summary.py — Bhumi Drishti AI narrative layer
=================================================
Generates LLM-backed summaries and answers user questions about their land
plot. Strictly follows the band contract for Bhumi_Full_Production_Final.
"""

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
import os
from dotenv import load_dotenv

load_dotenv()

# ── Mandatory caveat — verbatim per contract ───────────────────────────────────
LOW_CONFIDENCE_CAVEAT = (
    "Score derived from a 60 m buffer around the plot centroid. The parcel "
    "is smaller than one 30 m satellite pixel. Results are indicative only; "
    "on-site verification is recommended before any land-use decision."
)

# ── Shared formatting rules ────────────────────────────────────────────────────
_BASE_RULES = """\
RULES (follow exactly, no exceptions):
- Plain prose only. No markdown, no bullets, no headers.
- Risk scores to 1 decimal place (e.g. "73.4%"). Never round to whole numbers.
- Never mention raw NDVI or values 0.405–0.411. Reference ndvi_wet and ndvi_delta only.
- soil_clay and dist_river are pre-converted — report % and metres as given.
- SPI: a value closer to 0 means higher stream-power / erosion risk.
- No filler openers ("This analysis shows", "It is important to note", "Based on the data").
- Never invent values — every number must come from the PLOT DATA block below.\
"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _pct(v: float) -> str:
    """Convert decimal to percentage string (1 d.p.)"""
    return f"{v * 100:.1f}%"


def _build_context_block(data: dict) -> str:
    """Converts the services.py output dict into a readable context block."""
    # (context building code from previous commit...)
    pass


def _init_llm():
    """Initialise LangChain LLM. Returns None if API key is absent."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    base_url = "https://openrouter.ai/api/v1" if api_key.startswith("sk-or-") else None
    return ChatOpenAI(
        model="gpt-3.5-turbo",
        temperature=0.3,          # lowered from 0.5 → tighter, more factual output
        api_key=api_key,
        **({'base_url': base_url} if base_url else {})
    )