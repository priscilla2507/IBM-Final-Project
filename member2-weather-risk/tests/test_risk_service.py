"""
member2-weather-risk/tests/test_risk_service.py

Unit tests for app/services/risk_service.py.

Tests cover:
  - Scoring boundary values for each category
  - Each sub-score function in isolation
  - Full compute_assessment with and without weather data
  - Data-quality notes when weather is unavailable
  - Factor and recommendation generation
"""

from __future__ import annotations

from datetime import datetime

import pytest

from app.schemas.risk_schemas import AssessmentRequest
from app.services.risk_service import (
    _exposure_subscore,
    _footfall_component,
    _humidity_subscore,
    _score_to_category,
    _shade_subscore,
    _surface_component,
    _temperature_subscore,
    _vulnerability_subscore,
    compute_assessment,
)
from app.services.weather_service import WeatherObservation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _req(
    lat: float = 17.385,
    lon: float = 78.487,
    location_name: str = "Test Location",
    area_type: str = "Transit Hub (Bus Stop / Metro / Rail)",
    surface_type: str = "Dark Asphalt / Tar (High Heat Retention)",
    shade_availability: str = "Sparse / Minimal (<25% cover)",
    canopy_density: int = 10,
    footfall: str = "High (500–1,000 people/hr)",
    demographics: list | None = None,
    hydration_present: bool = False,
    notes: str = "",
) -> AssessmentRequest:
    return AssessmentRequest(
        latitude=lat,
        longitude=lon,
        location_name=location_name,
        area_type=area_type,
        surface_type=surface_type,
        shade_availability=shade_availability,
        canopy_density=canopy_density,
        footfall=footfall,
        demographics=demographics or ["Commuters", "Students"],
        hydration_present=hydration_present,
        notes=notes,
    )


def _obs(
    temperature: float = 39.0,
    relative_humidity: int = 50,
    apparent_temperature: float = 42.0,
    wind_speed: float = 15.0,
    weather_code: int = 1,
) -> WeatherObservation:
    return WeatherObservation(
        latitude=17.385,
        longitude=78.487,
        temperature=temperature,
        apparent_temperature=apparent_temperature,
        relative_humidity=relative_humidity,
        wind_speed=wind_speed,
        weather_code=weather_code,
        observation_time=datetime(2024, 5, 15, 12, 0),
        timezone="Asia/Kolkata",
        units={"temperature": "°C"},
        data_quality_notes=["Model-derived."],
    )


# ---------------------------------------------------------------------------
# Temperature sub-score boundaries
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("temp,expected", [
    (24.9,  0),
    (25.0, 15),
    (29.9, 15),
    (30.0, 35),
    (34.9, 35),
    (35.0, 60),
    (38.9, 60),
    (39.0, 80),
    (41.9, 80),
    (42.0, 100),
    (50.0, 100),
])
def test_temperature_subscore_boundaries(temp, expected):
    assert _temperature_subscore(temp) == expected


# ---------------------------------------------------------------------------
# Humidity sub-score boundaries
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("humidity,expected", [
    (0,   5),
    (29,  5),
    (30, 20),
    (44, 20),
    (45, 45),
    (59, 45),
    (60, 70),
    (74, 70),
    (75, 100),
    (100, 100),
])
def test_humidity_subscore_boundaries(humidity, expected):
    assert _humidity_subscore(humidity) == expected


# ---------------------------------------------------------------------------
# Shade sub-score
# ---------------------------------------------------------------------------

def test_shade_subscore_fully_exposed():
    assert _shade_subscore("None / Fully Exposed", 0) == 100


def test_shade_subscore_dense_with_zero_canopy():
    assert _shade_subscore("Dense (>75% cover)", 0) == 5


def test_shade_subscore_canopy_bonus_reduces_score():
    # Sparse base = 80; bonus = 50 * 0.40 = 20; result = 60
    score = _shade_subscore("Sparse / Minimal (<25% cover)", 50)
    assert score == 60


def test_shade_subscore_cannot_go_below_zero():
    # Dense base = 5; canopy 100% → bonus 40 → 5 - 40 = -35, clamped to 0
    assert _shade_subscore("Dense (>75% cover)", 100) == 0


def test_shade_subscore_unknown_shade_uses_default():
    score = _shade_subscore("Unknown shade type", 0)
    assert score == 70


def test_shade_subscore_none_values():
    score = _shade_subscore(None, None)
    assert score == 70  # conservative default


# ---------------------------------------------------------------------------
# Exposure sub-score
# ---------------------------------------------------------------------------

def test_surface_component_dark_asphalt():
    assert _surface_component("Dark Asphalt / Tar (High Heat Retention)") == 60


def test_surface_component_granite():
    assert _surface_component("Granite Cobblestone (Very High Heat)") == 60


def test_surface_component_concrete():
    assert _surface_component("Concrete Slab (High Heat Retention)") == 50


def test_surface_component_grass():
    assert _surface_component("Grass & Paved Pathway (Low Heat)") == 10


def test_surface_component_unknown():
    assert _surface_component("Something Unknown") == 40


def test_footfall_component_extreme():
    assert _footfall_component("Extreme (>1,000 people/hr continuously)") == 40


def test_footfall_component_low():
    assert _footfall_component("Low (<100 people/hr)") == 5


def test_exposure_subscore_caps_at_100():
    # 60 (asphalt) + 40 (extreme) = 100
    score = _exposure_subscore(
        "Dark Asphalt / Tar (High Heat Retention)",
        "Extreme (>1,000 people/hr continuously)",
    )
    assert score == 100


# ---------------------------------------------------------------------------
# Vulnerability sub-score
# ---------------------------------------------------------------------------

def test_vulnerability_high_vuln_groups():
    score = _vulnerability_subscore(
        ["Daily Wage Laborers", "Elderly Citizens", "Children"],
        hydration_present=False,
    )
    # 3 groups × 15 = 45 + 40 (no hydration) = 85
    assert score == 85


def test_vulnerability_hydration_present_lowers_score():
    score_no_hydration  = _vulnerability_subscore([], hydration_present=False)
    score_with_hydration = _vulnerability_subscore([], hydration_present=True)
    assert score_no_hydration == 40
    assert score_with_hydration == 0


def test_vulnerability_caps_at_100():
    # 4 high-vuln groups × 15 = 60 (capped) + 40 = 100
    score = _vulnerability_subscore(
        ["Daily Wage Laborers", "Elderly Citizens", "Children",
         "Traffic Police / Municipal Workers", "Street Vendors"],
        hydration_present=False,
    )
    assert score == 100


def test_vulnerability_no_demographics():
    score = _vulnerability_subscore(None, hydration_present=True)
    assert score == 0


# ---------------------------------------------------------------------------
# Risk category boundaries
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("score,expected", [
    (0,   "low"),
    (24,  "low"),
    (25,  "moderate"),
    (49,  "moderate"),
    (50,  "high"),
    (74,  "high"),
    (75,  "very_high"),
    (100, "very_high"),
])
def test_score_to_category_boundaries(score, expected):
    assert _score_to_category(score) == expected


# ---------------------------------------------------------------------------
# compute_assessment — full pipeline
# ---------------------------------------------------------------------------

def test_compute_assessment_with_weather():
    req = _req()
    weather = _obs(temperature=42.0, relative_humidity=70)
    result = compute_assessment(req, weather)

    assert result.risk_score >= 0
    assert result.risk_score <= 100
    assert result.risk_category in ("low", "moderate", "high", "very_high")
    assert result.weather_available is True
    assert result.temperature == pytest.approx(42.0)
    assert result.humidity == 70
    assert len(result.factors) > 0
    assert len(result.recommendations) > 0
    assert result.model_version.startswith("v0.2-dev")


def test_compute_assessment_without_weather():
    req = _req()
    result = compute_assessment(req, weather=None)

    assert result.risk_score >= 0
    assert result.risk_score <= 100
    assert result.weather_available is False
    assert result.temperature is None
    assert result.humidity is None
    # Must include a data-quality note about partial assessment
    quality_note_text = " ".join(result.data_quality_notes).upper()
    assert "PARTIAL" in quality_note_text
    # Limitations should mention partial assessment
    assert "PARTIAL" in result.model_limitations.upper()


def test_compute_assessment_score_in_valid_range_low_risk():
    req = _req(
        surface_type="Grass & Paved Pathway (Low Heat)",
        shade_availability="Dense (>75% cover)",
        canopy_density=80,
        footfall="Low (<100 people/hr)",
        demographics=[],
        hydration_present=True,
    )
    weather = _obs(temperature=28.0, relative_humidity=40)
    result = compute_assessment(req, weather)

    assert result.risk_category in ("low", "moderate")
    assert result.risk_score <= 50


def test_compute_assessment_score_high_risk():
    req = _req(
        surface_type="Dark Asphalt / Tar (High Heat Retention)",
        shade_availability="None / Fully Exposed",
        canopy_density=0,
        footfall="Extreme (>1,000 people/hr continuously)",
        demographics=["Daily Wage Laborers", "Elderly Citizens", "Children"],
        hydration_present=False,
    )
    weather = _obs(temperature=43.0, relative_humidity=65)
    result = compute_assessment(req, weather)

    assert result.risk_category in ("high", "very_high")
    assert result.risk_score >= 70


def test_compute_assessment_location_name_fallback():
    req = AssessmentRequest(latitude=17.385, longitude=78.487)  # no location_name
    result = compute_assessment(req, weather=None)
    # Should fall back to coordinate string
    assert "17.3850" in result.location


def test_compute_assessment_assessment_id_format():
    req = _req()
    result = compute_assessment(req, weather=None)
    assert result.assessment_id.startswith("ASSESS-HYD-")


def test_compute_assessment_factors_have_required_fields():
    req = _req()
    weather = _obs(temperature=40.0, relative_humidity=55)
    result = compute_assessment(req, weather)

    for factor in result.factors:
        assert factor.label
        assert factor.impact in ("high", "moderate", "positive")


def test_compute_assessment_recommendations_have_required_fields():
    req = _req()
    weather = _obs(temperature=44.0, relative_humidity=70)
    result = compute_assessment(req, weather)

    for rec in result.recommendations:
        assert rec.priority in ("Immediate", "Medium Term", "Long Term", "Low Priority")
        assert rec.label


# ---------------------------------------------------------------------------
# Assessment request validation
# ---------------------------------------------------------------------------

def test_assessment_request_requires_latitude():
    with pytest.raises(Exception):
        AssessmentRequest(longitude=78.487)  # type: ignore[call-arg]


def test_assessment_request_requires_longitude():
    with pytest.raises(Exception):
        AssessmentRequest(latitude=17.385)  # type: ignore[call-arg]


def test_assessment_request_latitude_out_of_range():
    with pytest.raises(Exception):
        AssessmentRequest(latitude=91.0, longitude=78.487)


def test_assessment_request_longitude_out_of_range():
    with pytest.raises(Exception):
        AssessmentRequest(latitude=17.385, longitude=200.0)


def test_assessment_request_canopy_density_out_of_range():
    with pytest.raises(Exception):
        AssessmentRequest(latitude=17.385, longitude=78.487, canopy_density=101)


def test_assessment_request_optional_fields_default_to_none():
    req = AssessmentRequest(latitude=17.385, longitude=78.487)
    assert req.location_name is None
    assert req.area_type is None
    assert req.surface_type is None
    assert req.shade_availability is None
    assert req.canopy_density is None
    assert req.footfall is None
    assert req.demographics == []
    assert req.hydration_present is False
    assert req.notes is None
