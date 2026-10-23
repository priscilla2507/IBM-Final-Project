"""
member2-weather-risk/tests/test_weather_route.py

Integration tests for GET /api/weather using mocked weather service calls.

All HTTP calls are intercepted — no live network requests are made.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.weather_service import WeatherObservation, WeatherServiceError


def _make_observation(
    lat: float = 17.385,
    lon: float = 78.487,
    temperature: float = 39.4,
    apparent_temperature: float = 43.1,
    relative_humidity: int = 48,
    wind_speed: float = 14.5,
    weather_code: int = 1,
) -> WeatherObservation:
    return WeatherObservation(
        latitude=lat,
        longitude=lon,
        temperature=temperature,
        apparent_temperature=apparent_temperature,
        relative_humidity=relative_humidity,
        wind_speed=wind_speed,
        weather_code=weather_code,
        observation_time=datetime(2024, 5, 15, 12, 0),
        timezone="Asia/Kolkata",
        units={"temperature": "°C", "apparent_temperature": "°C",
               "relative_humidity": "%", "wind_speed": "km/h"},
        data_quality_notes=["Model-derived data."],
    )


# ---------------------------------------------------------------------------
# Successful weather retrieval
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_weather_route_success():
    obs = _make_observation()
    with patch(
        "app.routes.weather.get_current_weather",
        new=AsyncMock(return_value=obs),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/weather", params={"lat": 17.385, "lon": 78.487})

    assert response.status_code == 200
    data = response.json()
    assert data["temperature"] == pytest.approx(39.4)
    assert data["relative_humidity"] == 48
    assert data["wind_speed"] == pytest.approx(14.5)
    assert data["weather_code"] == 1
    assert data["timezone"] == "Asia/Kolkata"
    assert "units" in data
    assert "data_quality_notes" in data
    assert "observation_time" in data


# ---------------------------------------------------------------------------
# Invalid coordinates → 400
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_weather_route_invalid_lat():
    """
    FastAPI's Query(ge=-90, le=90) rejects lat=200 with 422 (Unprocessable Entity)
    before the service layer is reached.  The service-level coordinate validation
    is tested separately in test_weather_service.py.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/weather", params={"lat": 200.0, "lon": 78.487})

    assert response.status_code == 422
    assert "detail" in response.json()


@pytest.mark.asyncio
async def test_weather_route_missing_lat():
    """lat query param is required; FastAPI returns 422 if omitted."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/weather", params={"lon": 78.487})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_weather_route_missing_lon():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/weather", params={"lat": 17.385})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Upstream errors → 503
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_weather_route_upstream_unavailable():
    with patch(
        "app.routes.weather.get_current_weather",
        new=AsyncMock(
            side_effect=WeatherServiceError(
                "Weather API returned HTTP 500.", upstream_status=500
            )
        ),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/weather", params={"lat": 17.385, "lon": 78.487})

    assert response.status_code == 503
    assert "detail" in response.json()


@pytest.mark.asyncio
async def test_weather_route_timeout():
    with patch(
        "app.routes.weather.get_current_weather",
        new=AsyncMock(
            side_effect=WeatherServiceError("Weather service timed out.")
        ),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/weather", params={"lat": 17.385, "lon": 78.487})

    assert response.status_code == 503
