"""
backend/app/routes/personal_assessment_routes.py  # noqa

POST /api/personal-assessment

Accepts personal profile information and returns a personalised heat-risk
assessment with practical precautions and action plan.

This endpoint reuses the existing weather service (get_weather / find_location)
and the established heat-scoring approach from optimization_db_service.py.

DESIGN NOTES
------------
- No sensitive health information is persisted by default.
- The risk classification uses documented, transparent factors.
- Results are explicitly labelled as general-awareness guidance, not medical
  advice or clinical diagnosis.
- Weather data comes from the existing Open-Meteo integration.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.weather_service import find_location, get_weather

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Personal Heat Assessment"])


# ── Request schema ─────────────────────────────────────────────────────────── #

class PersonalAssessmentRequest(BaseModel):
    """
    Personal profile data for an individual heat-risk assessment.
    All health-related fields are optional and not persisted.
    """
    location_name: str = Field(
        min_length=2,
        max_length=150,
        description="City or locality name for weather lookup",
        examples=["Hyderabad, Telangana"],
    )
    age_range: str = Field(
        description="Age range (e.g. 'Under 5', '5-17', '18-59', '60+')",
        examples=["18-59"],
    )
    outdoor_duration_hours: float = Field(
        ge=0,
        le=24,
        description="Approximate daily outdoor exposure duration in hours",
        examples=[4.0],
    )
    outdoor_activity: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Type of outdoor activity or occupation",
        examples=["Construction worker"],
    )
    has_water_access: bool = Field(
        default=True,
        description="Whether the person has reliable access to drinking water outdoors",
    )
    has_shade_access: bool = Field(
        default=True,
        description="Whether the person has access to shade or cool spaces outdoors",
    )
    # Optional health-context flags — not stored, used only for risk scoring
    is_pregnant: Optional[bool] = Field(
        default=None,
        description="[Optional] Pregnancy status — increases heat sensitivity",
    )
    has_chronic_condition: Optional[bool] = Field(
        default=None,
        description="[Optional] Whether the person has a relevant chronic condition (e.g. cardiovascular, diabetes, kidney disease)",
    )
    takes_heat_affecting_medication: Optional[bool] = Field(
        default=None,
        description="[Optional] Whether taking medications that may affect heat tolerance (e.g. diuretics, antihypertensives)",
    )


# ── Response schema ─────────────────────────────────────────────────────────── #

class PersonalWeatherSnapshot(BaseModel):
    temperature: Optional[float]
    apparent_temperature: Optional[float]
    humidity: Optional[int]
    observation_time: Optional[str] = None   # ISO string or None
    weather_available: bool


class PersonalRiskFactor(BaseModel):
    label: str
    detail: str
    impact: Literal["high", "moderate", "positive"]


class PersonalPrecaution(BaseModel):
    phase: Literal["before", "during", "after"]
    action: str


class PersonalAssessmentResponse(BaseModel):
    risk_category: Literal["low", "moderate", "high", "very_high"]
    risk_score: int = Field(ge=0, le=100)
    risk_label: str
    risk_explanation: str
    location_resolved: str
    weather: PersonalWeatherSnapshot
    contributing_factors: list[PersonalRiskFactor]
    precautions: list[PersonalPrecaution]
    warning_signs: list[str]
    emergency_guidance: str
    disclaimer: str
    model_limitations: str


# ── Scoring helpers ─────────────────────────────────────────────────────────── #

def _age_score(age_range: str) -> int:
    """Higher score = greater heat vulnerability by age."""
    r = age_range.strip().lower()
    if "under 5" in r or "< 5" in r:
        return 35
    if r.startswith("60") or "60+" in r or "65+" in r or "elderly" in r:
        return 30
    if "5" in r and "17" in r:
        return 20
    return 0  # 18-59 general adult


def _exposure_score(duration_hours: float, has_shade: bool, has_water: bool) -> int:
    """Score based on outdoor exposure duration and mitigation access."""
    dur_score = min(40, int(duration_hours * 5))  # up to 8 hrs = 40
    shade_pen = 0 if has_shade else 15
    water_pen = 0 if has_water else 15
    return min(70, dur_score + shade_pen + water_pen)


def _health_score(
    is_pregnant: Optional[bool],
    has_chronic: Optional[bool],
    takes_medication: Optional[bool],
) -> int:
    score = 0
    if is_pregnant:
        score += 20
    if has_chronic:
        score += 25
    if takes_medication:
        score += 15
    return min(60, score)


def _weather_score(temperature: Optional[float], humidity: Optional[int]) -> int:
    if temperature is None:
        return 0
    t = float(temperature)
    if t < 25:
        t_score = 0
    elif t < 30:
        t_score = 15
    elif t < 35:
        t_score = 35
    elif t < 39:
        t_score = 60
    elif t < 42:
        t_score = 80
    else:
        t_score = 100

    h = int(humidity or 50)
    if h < 30:
        h_score = 5
    elif h < 45:
        h_score = 20
    elif h < 60:
        h_score = 45
    elif h < 75:
        h_score = 70
    else:
        h_score = 100

    return round(t_score * 0.7 + h_score * 0.3)


# ── Factor / precaution builders ─────────────────────────────────────────────── #

def _build_factors(
    req: PersonalAssessmentRequest,
    temperature: Optional[float],
    humidity: Optional[int],
) -> list[PersonalRiskFactor]:
    factors: list[PersonalRiskFactor] = []
    if temperature is not None and temperature >= 35:
        impact = "high" if temperature >= 39 else "moderate"
        factors.append(PersonalRiskFactor(
            label=f"High Ambient Temperature ({temperature:.1f}°C)",
            detail="Temperatures above 35°C significantly increase the risk of heat exhaustion.",
            impact=impact,
        ))
    if humidity is not None and humidity >= 60:
        impact = "high" if humidity >= 75 else "moderate"
        factors.append(PersonalRiskFactor(
            label=f"Elevated Humidity ({humidity}%)",
            detail="High humidity limits the body's ability to cool itself through sweating.",
            impact=impact,
        ))
    age_s = _age_score(req.age_range)
    if age_s >= 30:
        factors.append(PersonalRiskFactor(
            label=f"Age-Related Vulnerability ({req.age_range})",
            detail="Very young children and older adults have reduced capacity to regulate body temperature.",
            impact="high",
        ))
    elif age_s >= 20:
        factors.append(PersonalRiskFactor(
            label=f"Age-Related Sensitivity ({req.age_range})",
            detail="Adolescents may underestimate heat risk during active outdoor play.",
            impact="moderate",
        ))
    if req.outdoor_duration_hours >= 6:
        factors.append(PersonalRiskFactor(
            label=f"Extended Outdoor Exposure ({req.outdoor_duration_hours:.0f} hours)",
            detail="Prolonged outdoor exposure significantly raises cumulative heat load.",
            impact="high",
        ))
    elif req.outdoor_duration_hours >= 3:
        factors.append(PersonalRiskFactor(
            label=f"Moderate Outdoor Exposure ({req.outdoor_duration_hours:.0f} hours)",
            detail="Several hours outdoors during hot weather requires regular hydration and rest.",
            impact="moderate",
        ))
    if not req.has_water_access:
        factors.append(PersonalRiskFactor(
            label="No Reliable Water Access",
            detail="Lack of drinking water access during outdoor heat exposure significantly increases dehydration risk.",
            impact="high",
        ))
    else:
        factors.append(PersonalRiskFactor(
            label="Water Access Available",
            detail="Access to drinking water is an important mitigating factor.",
            impact="positive",
        ))
    if not req.has_shade_access:
        factors.append(PersonalRiskFactor(
            label="No Shade or Cool Space Access",
            detail="Without access to shade or cool spaces, recovery from heat exposure is difficult.",
            impact="high",
        ))
    else:
        factors.append(PersonalRiskFactor(
            label="Shade or Cool Space Available",
            detail="Access to shade or cool spaces significantly reduces heat-related risk.",
            impact="positive",
        ))
    if req.has_chronic_condition:
        factors.append(PersonalRiskFactor(
            label="Chronic Health Condition (self-reported)",
            detail="Certain chronic conditions (cardiovascular disease, diabetes, kidney disease) increase susceptibility to heat illness.",
            impact="high",
        ))
    if req.is_pregnant:
        factors.append(PersonalRiskFactor(
            label="Pregnancy (self-reported)",
            detail="Pregnancy increases metabolic heat production and fluid requirements.",
            impact="high",
        ))
    if req.takes_heat_affecting_medication:
        factors.append(PersonalRiskFactor(
            label="Medications that May Affect Heat Tolerance (self-reported)",
            detail="Some medications (diuretics, antihypertensives, antihistamines) can impair heat regulation. Consult your doctor about heat precautions.",
            impact="moderate",
        ))
    return factors


def _build_precautions(risk_category: str, req: PersonalAssessmentRequest) -> list[PersonalPrecaution]:
    precautions = []
    precautions.append(PersonalPrecaution(phase="before", action="Check the daily heat forecast and plan outdoor activities for early morning (before 9 AM) or after 5 PM."))
    precautions.append(PersonalPrecaution(phase="before", action="Drink at least 2–3 litres of water before going outdoors. Do not wait until you feel thirsty."))
    precautions.append(PersonalPrecaution(phase="before", action="Wear light-coloured, loose-fitting, breathable clothing that covers your arms and legs."))
    if not req.has_shade_access:
        precautions.append(PersonalPrecaution(phase="before", action="Identify the nearest cooling shelter or air-conditioned space along your route before leaving."))
    precautions.append(PersonalPrecaution(phase="during", action="Take a 10–15 minute break in shade or a cool space every 30–45 minutes of outdoor activity."))
    precautions.append(PersonalPrecaution(phase="during", action="Drink 250 ml of water every 20 minutes during outdoor exposure. Avoid alcohol and sugary drinks."))
    if req.outdoor_activity and any(w in req.outdoor_activity.lower() for w in ["construct", "labor", "worker", "outdoor", "field"]):
        precautions.append(PersonalPrecaution(phase="during", action="If doing physical work, reduce your pace in peak heat hours. Heavy work should be done in the morning or late afternoon only."))
    if risk_category in ("high", "very_high"):
        precautions.append(PersonalPrecaution(phase="during", action="Immediately stop outdoor activity if you feel dizzy, nauseous, have a headache, or stop sweating despite heat."))
    precautions.append(PersonalPrecaution(phase="after", action="After outdoor exposure, move to a cool space and rehydrate with water or an oral rehydration solution (ORS)."))
    precautions.append(PersonalPrecaution(phase="after", action="Monitor yourself and others for warning signs for at least 1 hour after returning indoors."))
    if req.has_chronic_condition or req.is_pregnant or req.age_range in ("60+", "Under 5"):
        precautions.append(PersonalPrecaution(phase="after", action="Consult your doctor about specific precautions given your health situation before your next heat exposure."))
    return precautions


# ── Route ──────────────────────────────────────────────────────────────────── #

@router.post(
    "/personal-assessment",
    response_model=PersonalAssessmentResponse,
    summary="Personal heat-risk assessment",
    description=(
        "Accepts personal profile data and returns a personalised heat-risk "
        "assessment with practical precautions. Uses live weather from the "
        "existing weather service. No sensitive health data is persisted. "
        "Results are general-awareness guidance only, not medical advice."
    ),
)
def personal_assessment(request: PersonalAssessmentRequest) -> PersonalAssessmentResponse:
    # 1. Resolve location and fetch weather
    try:
        geo = find_location(request.location_name.strip())
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    lat = geo["latitude"]
    lon = geo["longitude"]
    resolved_name = geo["name"]
    if geo.get("admin1"):
        resolved_name += f", {geo['admin1']}"
    if geo.get("country"):
        resolved_name += f", {geo['country']}"

    temperature: Optional[float] = None
    apparent_temperature: Optional[float] = None
    humidity: Optional[int] = None
    obs_time: Optional[str] = None
    weather_available = False

    try:
        weather_data = get_weather(lat, lon)
        current = weather_data.get("current", {})
        temperature = current.get("temperature_2m")
        apparent_temperature = current.get("apparent_temperature")
        humidity = current.get("relative_humidity_2m")
        raw_time = current.get("time")
        # OpenWeatherMap returns dt as a unix timestamp int; convert to ISO string
        if isinstance(raw_time, int):
            obs_time = datetime.fromtimestamp(raw_time, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        elif raw_time:
            obs_time = str(raw_time)
        else:
            obs_time = None
        if temperature is not None:
            temperature = float(temperature)
            weather_available = True
        if humidity is not None:
            humidity = int(humidity)
        if apparent_temperature is not None:
            apparent_temperature = float(apparent_temperature)
    except Exception as exc:
        logger.warning("Weather unavailable for personal assessment: %s", exc)

    # 2. Composite score
    w_score = _weather_score(temperature, humidity)
    age_s = _age_score(request.age_range)
    exp_s = _exposure_score(request.outdoor_duration_hours, request.has_shade_access, request.has_water_access)
    h_score = _health_score(request.is_pregnant, request.has_chronic_condition, request.takes_heat_affecting_medication)

    if weather_available:
        raw = w_score * 0.45 + age_s * 0.15 + exp_s * 0.25 + h_score * 0.15
    else:
        raw = age_s * 0.25 + exp_s * 0.45 + h_score * 0.30

    risk_score = max(0, min(100, round(raw)))

    if risk_score < 25:
        risk_category = "low"
        risk_label = "Low Risk"
        risk_explanation = "Current conditions suggest a low level of heat stress for your profile. Standard hydration and shade precautions are sufficient."
    elif risk_score < 50:
        risk_category = "moderate"
        risk_label = "Moderate Risk"
        risk_explanation = "Moderate heat stress is likely given your profile and conditions. Follow the precautions below and monitor yourself for warning signs."
    elif risk_score < 75:
        risk_category = "high"
        risk_label = "High Risk"
        risk_explanation = "High heat stress risk. Limit outdoor exposure, take frequent breaks in shade or cool spaces, and stay well hydrated."
    else:
        risk_category = "very_high"
        risk_label = "Very High Risk"
        risk_explanation = "Very high heat stress risk. Avoid outdoor activity during peak heat hours where possible. If you must go outdoors, take all precautions and watch closely for warning signs."

    factors = _build_factors(request, temperature, humidity)
    precautions = _build_precautions(risk_category, request)

    return PersonalAssessmentResponse(
        risk_category=risk_category,
        risk_score=risk_score,
        risk_label=risk_label,
        risk_explanation=risk_explanation,
        location_resolved=resolved_name,
        weather=PersonalWeatherSnapshot(
            temperature=temperature,
            apparent_temperature=apparent_temperature,
            humidity=humidity,
            observation_time=obs_time,
            weather_available=weather_available,
        ),
        contributing_factors=factors,
        precautions=precautions,
        warning_signs=[
            "Heavy sweating followed by sudden cessation of sweating",
            "Dizziness, lightheadedness, or fainting",
            "Nausea or vomiting",
            "Rapid or weak pulse",
            "Headache or confusion",
            "Skin that is hot, red, dry, or damp",
            "Loss of consciousness",
            "Body temperature above 39°C",
        ],
        emergency_guidance=(
            "If you or someone nearby shows signs of heatstroke (confusion, loss of "
            "consciousness, seizures, or very high body temperature), call emergency "
            "services immediately (India: 112 / 108) or go to the nearest hospital. "
            "Move the person to a cool place, apply cool water to skin, and do not "
            "leave them alone while waiting for help."
        ),
        disclaimer=(
            "This assessment is for general awareness only. It is not medical advice "
            "and does not constitute a clinical diagnosis. Consult a qualified health "
            "professional if you have concerns about your health or heat sensitivity."
        ),
        model_limitations=(
            "Score is an indicative planning measure based on self-reported inputs and "
            "live weather data. It has not been clinically validated. Optional health "
            "fields improve relevance but are not medically verified. "
            "Use as one input among several for personal decision-making."
            + ("" if weather_available else
               " PARTIAL: Weather data was unavailable; temperature and humidity "
               "sub-scores are omitted and remaining factors are re-weighted.")
        ),
    )
