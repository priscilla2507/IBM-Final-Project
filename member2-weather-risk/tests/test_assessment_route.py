"""
member2-weather-risk/tests/test_assessment_route.py

Integration tests for POST /api/assessments using the FastAPI test client.

All weather service calls are mocked — no live network requests or database
connections are made.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.weather_service import WeatherObservation, WeatherServiceError


def _make_observation(temperature: float = 40.0, relative_humidity: int = 55) -> WeatherObservation:
    return WeatherObservation(
        latitude=17.385,
        longitude=78.487,
        temperature=temperature,
        apparent_temperature=temperature + 3,
        relative_humidity=relative_humidity,
        wind_speed=15.0,
        weather_code=1,
        observation_time=datetime(2024, 5, 15, 12, 0),
        timezone="Asia/Kolkata",
        units={"temperature": "°C"},
        data_quality_notes=["Model-derived."],
    )


def _base_payload(**overrides) -> dict:
    payload = {
        "latitude": 17.3850,
        "longitude": 78.4867,
        "location_name": "Test Location Hyderabad",
        "area_type": "Transit Hub (Bus Stop / Metro / Rail)",
        "surface_type": "Dark Asphalt / Tar (High Heat Retention)",
        "shade_availability": "Sparse / Minimal (<25% cover)",
        "canopy_density": 10,
        "footfall": "High (500–1,000 people/hr)",
        "demographics": ["Commuters", "Students"],
        "hydration_present": False,
        "notes": "Test observation",
    }
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------------------
# Successful assessment with weather
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_assessment_with_weather_returns_200():
    obs = _make_observation()
    with patch(
        "app.routes.assessments.get_current_weather",
        new=AsyncMock(return_value=obs),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/api/assessments", json=_base_payload())

    assert response.status_code == 200
    data = response.json()
    assert "assessment_id" in data
    assert "risk_score" in data
    assert "risk_category" in data
    assert "factors" in data
    assert "recommendations" in data
    assert "model_version" in data
    assert "model_limitations" in data
    assert "model_valid" in data
    assert data["weather_available"] is True


@pytest.mark.asyncio
async def test_assessment_response_has_frontend_fields():
    """Verify all fields expected by HeatRiskAnalysis.jsx are present."""
    obs = _make_observation()
    with patch(
        "app.routes.assessments.get_current_weather",
        new=AsyncMock(return_value=obs),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/api/assessments", json=_base_payload())

    data = response.json()
    # Fields consumed by the React frontend
    required_fields = [
        "assessment_id", "location", "risk_score", "risk_category",
        "temperature", "humidity", "model_version", "model_valid",
        "model_limitations", "factors", "recommendations",
    ]
    for field in required_fields:
        assert field in data, f"Missing field: {field}"


@pytest.mark.asyncio
async def test_assessment_risk_score_in_range():
    obs = _make_observation()
    with patch(
        "app.routes.assessments.get_current_weather",
        new=AsyncMock(return_value=obs),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/api/assessments", json=_base_payload())

    data = response.json()
    assert 0 <= data["risk_score"] <= 100


@pytest.mark.asyncio
async def test_assessment_risk_category_valid():
    obs = _make_observation()
    with patch(
        "app.routes.assessments.get_current_weather",
        new=AsyncMock(return_value=obs),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/api/assessments", json=_base_payload())

    data = response.json()
    assert data["risk_category"] in ("low", "moderate", "high", "very_high")


# ---------------------------------------------------------------------------
# Partial assessment when weather is unavailable
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_assessment_partial_when_weather_unavailable():
    with patch(
        "app.routes.assessments.get_current_weather",
        new=AsyncMock(
            side_effect=WeatherServiceError("Weather API timed out.")
        ),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/api/assessments", json=_base_payload())

    assert response.status_code == 200
    data = response.json()
    assert data["weather_available"] is False
    assert data["temperature"] is None
    assert data["humidity"] is None
    # Data quality notes must mention "PARTIAL"
    quality_text = " ".join(data.get("data_quality_notes", [])).upper()
    assert "PARTIAL" in quality_text


@pytest.mark.asyncio
async def test_assessment_partial_limitations_label():
    with patch(
        "app.routes.assessments.get_current_weather",
        new=AsyncMock(
            side_effect=WeatherServiceError("No weather available.")
        ),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/api/assessments", json=_base_payload())

    data = response.json()
    assert "PARTIAL" in data["model_limitations"].upper()


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_assessment_missing_latitude_returns_422():
    payload = _base_payload()
    del payload["latitude"]
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/assessments", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_assessment_missing_longitude_returns_422():
    payload = _base_payload()
    del payload["longitude"]
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/assessments", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_assessment_invalid_latitude_out_of_range():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/assessments",
            json=_base_payload(latitude=200.0),
        )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_assessment_invalid_canopy_density_over_100():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/assessments",
            json=_base_payload(canopy_density=150),
        )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_assessment_minimal_payload_only_coords():
    """Only lat/lon required — optional fields should use defaults."""
    with patch(
        "app.routes.assessments.get_current_weather",
        new=AsyncMock(return_value=_make_observation()),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/assessments",
                json={"latitude": 17.385, "longitude": 78.487},
            )
    assert response.status_code == 200
    data = response.json()
    assert 0 <= data["risk_score"] <= 100


# ---------------------------------------------------------------------------
# Assessment ID format
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_assessment_id_format():
    with patch(
        "app.routes.assessments.get_current_weather",
        new=AsyncMock(return_value=_make_observation()),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/api/assessments", json=_base_payload())

    data = response.json()
    assert data["assessment_id"].startswith("ASSESS-HYD-")
