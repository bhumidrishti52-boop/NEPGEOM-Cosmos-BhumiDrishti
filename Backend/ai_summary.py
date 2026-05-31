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


# ── Public API ────────────────────────────────────────────────────────────────

def generate_risk_summary(data: dict) -> str:
    """
    Returns a tight 3-sentence plain-text risk summary:
      S1 — dominant risk + score
      S2 — key driving factors (terrain/hydrology)
      S3 — agricultural suitability + limiting factor
    Follows the Bhumi_Full_Production_Final band contract exactly.
    """
    llm = _init_llm()
    if llm is None:
        return "⚠️ OPENAI_API_KEY missing — add it to your .env file."

    context    = _build_context_block(data)
    confidence = data.get('confidence', 'UNKNOWN')
    anomaly    = data.get('anomaly_flag', False)

    low_caveat_instruction = (
        f'End with this exact sentence: "{LOW_CONFIDENCE_CAVEAT}"'
        if confidence == 'LOW'
        else 'Do not add any confidence caveat.'
    )

    anomaly_instruction = (
        'Include one brief sentence noting that the model output may require verification by the Bhumi team.'
        if anomaly else ''
    )

    prompt_text = f"""You are a knowledgeable local advisor talking directly to a farmer or landowner about their land.
All numbers come from the GEE asset Bhumi_Full_Production_Final — never invent values.

{_BASE_RULES}
- Tone: Direct, active voice, local advisor. Never say "Sunsari district" — always say "this plot" or "your land".
- 4 to 5 sentences (add 1 extra sentence only if confidence is LOW, to fit the mandatory caveat).
- Sentence 1: what is the biggest risk on this plot and how serious is it (use the mean score).
- Sentence 2: what on this specific land is causing that risk (use actual values). 
  * CRITICAL RULES FOR FLOOD RISK (>50%): Identify the actual dominant driver:
    - If LULC is Grassland or Bare/Sparse: Note the plot sits on active floodplain or sandbar land. Cite low-clay sandy soil, land cover, and high flood accumulation indicating regular monsoon inundation (DO NOT cite river distance).
    - Else if TWI > 8: Cite water accumulation and terrain convergence as the primary driver.
    - Else if flow_acc_log > 8: Cite high upstream drainage area as the driver.
    - Else if dist_river_m < 500: Cite proximity to river channel as the primary driver.
    - Only fall back to river distance if none of the above are met.
- Sentence 3: state the secondary risk if it is above 25%, otherwise skip this sentence and go directly to sentence 4.
- Sentence 4: farming verdict for this plot — is it good land to farm, and what is the one thing holding it back.
- Sentence 5: one practical recommendation — what the landowner should do or watch out for (e.g. "avoid planting in the lowest corners during monsoon", "this land is safe to build on but flood insurance is advisable").
{anomaly_instruction}
{low_caveat_instruction}

{context}"""

    try:
        result = llm.invoke([HumanMessage(content=prompt_text)]).content.strip()

        # Safety nets — fire if LLM drops mandatory content
        if confidence == 'LOW' and LOW_CONFIDENCE_CAVEAT not in result:
            result += f" {LOW_CONFIDENCE_CAVEAT}"

        if anomaly and 'bhumi team' not in result.lower():
            result += (
                " Note: a model output anomaly was detected (all risk scores near zero) — "
                "please report raw predictor values to the Bhumi team."
            )

        return result

    except Exception as e:
        return f"Error generating summary: {e}"


def chat_about_land(question: str, data: dict) -> str:
    """
    Answers a user question about their specific plot using full analysis
    data as context. Respects all band-contract response rules.
    """
    llm = _init_llm()
    if llm is None:
        return "⚠️ OPENAI_API_KEY missing — add it to your .env file."

    context    = _build_context_block(data)
    confidence = data.get('confidence', 'UNKNOWN')

    low_caveat_reminder = (
        f'\nRemind the user (verbatim, at the end): "{LOW_CONFIDENCE_CAVEAT}"'
        if confidence == 'LOW' else ''
    )

    prompt_text = f"""You are a knowledgeable local advisor talking directly to a farmer or landowner about their land.
All values come from the GEE asset Bhumi_Full_Production_Final — never invent numbers.

{_BASE_RULES}
- Tone: Direct, active voice, local advisor. Never say "Sunsari district" — always say "this plot" or "your land".
- Answer in 2–3 sentences. Explain factor relationships only when directly relevant.
- If the question is outside the scope of the plot data, say so clearly.{low_caveat_reminder}

{context}

USER QUESTION: {question}"""

    try:
        result = llm.invoke([HumanMessage(content=prompt_text)]).content.strip()

        if confidence == 'LOW' and LOW_CONFIDENCE_CAVEAT not in result:
            result += f"\n\n{LOW_CONFIDENCE_CAVEAT}"

        return result

    except Exception as e:
        return f"Error: {e}"