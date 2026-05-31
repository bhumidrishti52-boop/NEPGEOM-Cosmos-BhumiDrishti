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
