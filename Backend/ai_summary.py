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
