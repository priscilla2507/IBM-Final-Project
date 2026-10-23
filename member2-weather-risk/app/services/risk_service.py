"""
member2-weather-risk/app/services/risk_service.py

Deterministic, explainable heat-risk scoring engine.

SCORING MODEL — VERSION 0.2-dev
================================

Overview
--------
The composite risk score (0–100) is computed from five independently weighted
sub-scores.  Each sub-score is scaled to 100 and then weighted to form the
final integer score.  All weights and boundaries are documented below so that
the method is fully auditable and reproducible given the same inputs.

SUB-SCORES AND WEIGHTS
-----------------------

Sub-score              Weight  Description
-------------------------------------------------------------------
1. Temperature           0.35  Based on air temperature (°C)
2. Humidity              0.15  Based on relative humidity (%)
3. Shade / Canopy        0.20  Based on shade availability & canopy density
4. Exposure              0.20  Based on area type, surface type, footfall
5. Vulnerability         0.10  Based on demographics, hydration absence
-------------------------------------------------------------------
Total                    1.00

SUB-SCORE DETAIL
----------------

1. Temperature sub-score (weight 0.35)
   Boundaries (°C → sub-score):
     < 25     →  0
     25–29.9  →  15
     30–34.9  →  35
     35–38.9  →  60
     39–41.9  →  80
     ≥ 42     → 100

2. Humidity sub-score (weight 0.15)
   Humidity compounds heat stress above 60% RH.
   Boundaries (% → sub-score):
     < 30     →   5
     30–44.9  →  20
     45–59.9  →  45
     60–74.9  →  70
     ≥ 75     → 100

3. Shade/Canopy sub-score (weight 0.20)
   More shade → lower score.
   Shade availability (string match) → base sub-score:
     "None / Fully Exposed"         → 100
     "Sparse / Minimal (<25%)"      →  80
     "Moderate (25–50%)"            →  50
     "Good (50–75%)"                →  25
     "Dense (>75%)"                 →   5
     (no match / unknown)           →  70   # conservative default
   Then reduced by canopy density bonus:
     bonus = canopy_density * 0.40  (max 40 points off)
   Final = max(0, base − bonus)

4. Exposure sub-score (weight 0.20)
   Surface component (0–60):
     "Dark Asphalt" / "Granite Cobblestone"  → 60
     "Concrete Slab"                          → 50
     "Interlocking Pavers"                   → 35
     "Red Oxide"                             → 30
     "Grass"                                 → 10
     (unknown)                               → 40
   Footfall component (0–40):
     "Extreme (>1,000)"       → 40
     "High (500–1,000)"       → 30
     "Moderate (100–500)"     → 15
     "Low (<100)"             →  5
     (unknown)                → 20
   Exposure sub-score = surface + footfall (max 100)

5. Vulnerability sub-score (weight 0.10)
   Demographic score (0–60):
     Each high-vulnerability group adds 15 points (cap 60):
       "Daily Wage Laborers", "Elderly Citizens", "Children",
       "Traffic Police / Municipal Workers", "Street Vendors"
   Hydration penalty (0–40):
     hydration_present = False → 40
     hydration_present = True  →  0
   Vulnerability sub-score = demographic_score + hydration_penalty (max 100)

RISK CATEGORY BOUNDARIES
-------------------------
  0  – 24  → low
  25 – 49  → moderate
  50 – 74  → high
  75 – 100 → very_high

DATA-QUALITY NOTES
------------------
- If weather data is unavailable the temperature and humidity sub-scores
  are omitted and the remaining sub-scores are used with re-normalised
  weights (shade: 0.40, exposure: 0.40, vulnerability: 0.20).  The result
  is labelled as a "partial assessment" and the response includes a
  prominent data-quality note.

LIMITATIONS
-----------
- The model is preliminary and has not been validated against observed
  heat-illness outcomes.
- It does not account for time-of-day, solar angle, or recent precipitation.
- Sub-score boundaries are tuned for Hyderabad summer conditions and may
  not generalise to other climates.
- The score should be used as one input among several for field decision-making.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from app.schemas.risk_schemas import (
    AssessmentRequest,
    AssessmentResponse,
    Recommendation,
    RiskCategory,
    RiskFactor,
)
from app.services.weather_service import WeatherObservation

logger = logging.getLogger(__name__)

MODEL_VERSION = "v0.2-dev (Deterministic Preliminary Scorer)"
MODEL_VALID   = "Indicative decision-support measure; not medically validated"

_BASE_LIMITATIONS = (
    "Score is computed from a deterministic preliminary model (v0.2-dev). "
    "It has not been validated against observed heat-illness outcomes. "
    "Sub-score boundaries are tuned for Hyderabad summer conditions. "
    "Time-of-day, solar angle, and recent precipitation are not modelled. "
    "Use as one input among several for field decision-making only."
)

# ---------------------------------------------------------------------------
# Temperature sub-score
# ---------------------------------------------------------------------------

def _temperature_subscore(temp_c: float) -> int:
    if temp_c < 25:
        return 0
    if temp_c < 30:
        return 15
    if temp_c < 35:
        return 35
    if temp_c < 39:
        return 60
    if temp_c < 42:
        return 80
    return 100


# ---------------------------------------------------------------------------
# Humidity sub-score
# ---------------------------------------------------------------------------

def _humidity_subscore(humidity_pct: int) -> int:
    if humidity_pct < 30:
        return 5
    if humidity_pct < 45:
        return 20
    if humidity_pct < 60:
        return 45
    if humidity_pct < 75:
        return 70
    return 100


# ---------------------------------------------------------------------------
# Shade / Canopy sub-score
# ---------------------------------------------------------------------------

_SHADE_BASE: dict[str, int] = {
    "none / fully exposed":    100,
    "sparse":                   80,
    "moderate":                 50,
    "good":                     25,
    "dense":                     5,
}

def _shade_subscore(shade_str: Optional[str], canopy_density: Optional[int]) -> int:
    base = 70  # conservative default when unknown
    if shade_str:
        s = shade_str.lower()
        for key, val in _SHADE_BASE.items():
            if key in s:
                base = val
                break
    bonus = (canopy_density or 0) * 0.40
    return max(0, int(base - bonus))


# ---------------------------------------------------------------------------
# Exposure sub-score
# ---------------------------------------------------------------------------

def _surface_component(surface_str: Optional[str]) -> int:
    if not surface_str:
        return 40  # unknown — conservative default
    s = surface_str.lower()
    if "asphalt" in s or "tar" in s:
        return 60
    if "granite" in s or "cobblestone" in s:
        return 60
    if "concrete" in s:
        return 50
    if "interlocking" in s or "paver" in s:
        return 35
    if "red oxide" in s:
        return 30
    if "grass" in s:
        return 10
    return 40


def _footfall_component(footfall_str: Optional[str]) -> int:
    if not footfall_str:
        return 20  # unknown — conservative default
    s = footfall_str.lower()
    # Match from most-specific to least-specific to avoid substring collisions.
    # e.g. "Low (<100 people/hr)" must not match "100" before "low".
    if "extreme" in s or ">1,000" in s:
        return 40
    if "500" in s:
        return 30
    if "high" in s:
        return 30
    if "moderate" in s:
        return 15
    if "low" in s or "<100" in s:
        return 5
    if "100" in s:
        return 15
    return 20


def _exposure_subscore(surface_str: Optional[str], footfall_str: Optional[str]) -> int:
    return min(100, _surface_component(surface_str) + _footfall_component(footfall_str))


# ---------------------------------------------------------------------------
# Vulnerability sub-score
# ---------------------------------------------------------------------------

_HIGH_VULNERABILITY_GROUPS = frozenset({
    "daily wage laborers",
    "elderly citizens",
    "children",
    "traffic police / municipal workers",
    "traffic police",
    "municipal workers",
    "street vendors",
})


def _vulnerability_subscore(
    demographics: Optional[list[str]], hydration_present: Optional[bool]
) -> int:
    demo_list = demographics or []
    demo_score = 0
    for d in demo_list:
        if d.lower() in _HIGH_VULNERABILITY_GROUPS:
            demo_score += 15
    demo_score = min(60, demo_score)
    hydration_penalty = 0 if hydration_present else 40
    return min(100, demo_score + hydration_penalty)


# ---------------------------------------------------------------------------
# Risk category
# ---------------------------------------------------------------------------

def _score_to_category(score: int) -> RiskCategory:
    if score < 25:
        return "low"
    if score < 50:
        return "moderate"
    if score < 75:
        return "high"
    return "very_high"


# ---------------------------------------------------------------------------
# Factor generation
# ---------------------------------------------------------------------------

def _build_factors(
    req: AssessmentRequest,
    weather: Optional[WeatherObservation],
    *,
    temp_score: Optional[int],
    humidity_score: Optional[int],
    shade_score: int,
    exposure_score: int,
    vuln_score: int,
) -> list[RiskFactor]:
    factors: list[RiskFactor] = []

    # Temperature factor
    if weather is not None:
        temp = weather.temperature
        if temp >= 42:
            factors.append(RiskFactor(
                label="Extreme Air Temperature",
                detail=f"Air temperature is {temp:.1f}°C — well above the 40°C threshold for severe heat stress.",
                impact="high",
            ))
        elif temp >= 39:
            factors.append(RiskFactor(
                label="High Air Temperature",
                detail=f"Air temperature is {temp:.1f}°C — elevated heat stress risk.",
                impact="high",
            ))
        elif temp >= 35:
            factors.append(RiskFactor(
                label="Elevated Air Temperature",
                detail=f"Air temperature is {temp:.1f}°C — moderate heat stress risk.",
                impact="moderate",
            ))

        # Humidity factor
        rh = weather.relative_humidity
        if rh >= 75:
            factors.append(RiskFactor(
                label="Very High Humidity",
                detail=f"Relative humidity is {rh}%, severely limiting the body's ability to cool through sweating.",
                impact="high",
            ))
        elif rh >= 60:
            factors.append(RiskFactor(
                label="Elevated Humidity",
                detail=f"Relative humidity is {rh}%, compounding heat stress above the 60% threshold.",
                impact="moderate",
            ))

    # Shade/canopy factor
    if shade_score >= 80:
        factors.append(RiskFactor(
            label="Critically Low Shade Coverage",
            detail=(
                f"Shade availability: '{req.shade_availability or 'Unknown'}'; "
                f"canopy density: {req.canopy_density or 0}%. "
                "Occupants are highly exposed to direct solar radiation."
            ),
            impact="high",
        ))
    elif shade_score >= 50:
        factors.append(RiskFactor(
            label="Inadequate Shade Coverage",
            detail=(
                f"Shade availability: '{req.shade_availability or 'Unknown'}'. "
                "Partial shade may not protect occupants during peak solar hours."
            ),
            impact="moderate",
        ))
    elif shade_score <= 20:
        factors.append(RiskFactor(
            label="Good Shade / Canopy Coverage",
            detail=(
                f"Shade availability: '{req.shade_availability or 'Unknown'}'; "
                f"canopy density: {req.canopy_density or 0}%. "
                "This is a positive mitigating factor."
            ),
            impact="positive",
        ))

    # Surface factor
    surf = (req.surface_type or "").lower()
    if "asphalt" in surf or "tar" in surf or "granite" in surf or "cobblestone" in surf:
        factors.append(RiskFactor(
            label="Heat-Absorbent Surface Material",
            detail=f"Surface type '{req.surface_type}' has high heat-retention properties and radiates absorbed solar energy.",
            impact="high",
        ))
    elif "concrete" in surf:
        factors.append(RiskFactor(
            label="High Heat-Retention Surface",
            detail=f"Surface type '{req.surface_type}' retains solar heat significantly.",
            impact="moderate",
        ))

    # Footfall factor
    foot = (req.footfall or "").lower()
    if "extreme" in foot or "1,000" in foot:
        factors.append(RiskFactor(
            label="Extreme Pedestrian Exposure",
            detail="Very high pedestrian footfall means large numbers of people are at risk simultaneously.",
            impact="high",
        ))
    elif "high" in foot or "500" in foot:
        factors.append(RiskFactor(
            label="High Pedestrian Volume",
            detail="High footfall increases the number of people at risk.",
            impact="moderate",
        ))

    # Hydration factor
    if not req.hydration_present:
        factors.append(RiskFactor(
            label="No Free Hydration Facility",
            detail="No accessible free hydration facility within 50 m. Dehydration risk is elevated.",
            impact="high",
        ))
    else:
        factors.append(RiskFactor(
            label="Hydration Facility Present",
            detail="A free hydration facility is available within 50 m — a positive mitigating factor.",
            impact="positive",
        ))

    # Demographics
    demo_list = req.demographics or []
    high_vuln = [d for d in demo_list if d.lower() in _HIGH_VULNERABILITY_GROUPS]
    if high_vuln:
        factors.append(RiskFactor(
            label=f"Vulnerable Demographics Present: {', '.join(high_vuln)}",
            detail="These groups have reduced physiological capacity to tolerate heat stress.",
            impact="high",
        ))

    return factors


# ---------------------------------------------------------------------------
# Recommendation generation
# ---------------------------------------------------------------------------

def _build_recommendations(score: int, req: AssessmentRequest) -> list[Recommendation]:
    recs: list[Recommendation] = []
    category = _score_to_category(score)

    if category in ("high", "very_high"):
        recs.append(Recommendation(
            priority="Immediate",
            label="Deploy UV-block shade tarpaulins or tensile canopy over the highest-exposure area",
            cost=12000,
            timeframe="1–2 days",
        ))
        if not req.hydration_present:
            recs.append(Recommendation(
                priority="Immediate",
                label="Set up insulated chilled drinking water booth with ORS packets within 50 m",
                cost=8500,
                timeframe="24 hours",
            ))

    if category in ("moderate", "high", "very_high"):
        recs.append(Recommendation(
            priority="Medium Term",
            label="Apply high-albedo cool-roof or solar-reflective coating to exposed surfaces",
            cost=18000,
            timeframe="2–3 weeks",
        ))
        recs.append(Recommendation(
            priority="Long Term",
            label="Plant deep-rooted shade trees (Neem / Pongamia) with drip irrigation",
            cost=25000,
            timeframe="Upcoming monsoon season",
        ))

    if category == "low":
        recs.append(Recommendation(
            priority="Low Priority",
            label="Maintain existing canopy cover and schedule annual tree-trimming only",
            cost=2000,
            timeframe="Ongoing",
        ))

    return recs


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def compute_assessment(
    req: AssessmentRequest,
    weather: Optional[WeatherObservation],
) -> AssessmentResponse:
    """
    Compute a deterministic heat-risk assessment from field observations and
    an optional live weather snapshot.

    Parameters
    ----------
    req :
        Validated assessment request from the frontend.
    weather :
        Parsed Open-Meteo observation, or ``None`` if weather retrieval failed.

    Returns
    -------
    AssessmentResponse
        Complete assessment including score, category, factors, recommendations,
        and data-quality notes.

    Notes
    -----
    When ``weather`` is ``None`` the temperature and humidity sub-scores are
    omitted and the remaining three sub-scores are re-normalised to sum to 1.0.
    The result is labelled as a partial assessment and includes a prominent
    data-quality note.  No weather values are fabricated.
    """
    shade_score    = _shade_subscore(req.shade_availability, req.canopy_density)
    exposure_score = _exposure_subscore(req.surface_type, req.footfall)
    vuln_score     = _vulnerability_subscore(req.demographics, req.hydration_present)

    quality_notes: list[str] = []

    if weather is not None:
        temp_score     = _temperature_subscore(weather.temperature)
        humidity_score = _humidity_subscore(weather.relative_humidity)

        # Full scoring (all 5 sub-scores)
        composite = (
            temp_score     * 0.35
            + humidity_score * 0.15
            + shade_score    * 0.20
            + exposure_score * 0.20
            + vuln_score     * 0.10
        )
        quality_notes.extend(weather.data_quality_notes)

    else:
        # Partial scoring — no weather data
        temp_score     = None
        humidity_score = None
        # Re-normalised weights: shade 0.40, exposure 0.40, vulnerability 0.20
        composite = (
            shade_score    * 0.40
            + exposure_score * 0.40
            + vuln_score     * 0.20
        )
        quality_notes.append(
            "PARTIAL ASSESSMENT: Weather data was unavailable for this request. "
            "Temperature and humidity sub-scores (weight 0.50 combined) have been "
            "omitted. The remaining sub-scores have been re-normalised. "
            "This score may underestimate actual heat risk. "
            "Retrieve current weather and re-assess when connectivity is restored."
        )

    risk_score = max(0, min(100, round(composite)))
    risk_category = _score_to_category(risk_score)

    location_name = (
        req.location_name or
        f"{req.latitude:.4f}°N, {req.longitude:.4f}°E"
    )

    limitations = _BASE_LIMITATIONS
    if weather is None:
        limitations = (
            "PARTIAL ASSESSMENT (no weather data). "
            + limitations
        )

    factors = _build_factors(
        req,
        weather,
        temp_score=temp_score,
        humidity_score=humidity_score,
        shade_score=shade_score,
        exposure_score=exposure_score,
        vuln_score=vuln_score,
    )

    recommendations = _build_recommendations(risk_score, req)

    logger.info(
        "Assessment computed: score=%d category=%s weather_available=%s",
        risk_score,
        risk_category,
        weather is not None,
    )

    return AssessmentResponse(
        location=location_name,
        latitude=req.latitude,
        longitude=req.longitude,
        risk_score=risk_score,
        risk_category=risk_category,
        temperature=weather.temperature if weather else None,
        apparent_temperature=weather.apparent_temperature if weather else None,
        humidity=weather.relative_humidity if weather else None,
        model_version=MODEL_VERSION,
        model_valid=MODEL_VALID,
        model_limitations=limitations,
        factors=factors,
        recommendations=recommendations,
        assessment_timestamp=datetime.now(timezone.utc),
        weather_available=weather is not None,
        data_quality_notes=quality_notes,
    )
