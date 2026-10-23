"""
member2-weather-risk/tests/test_weather_compatibility.py

Tests for the weather API compatibility fixes (audit finding D1/D2):
  - Frontend-compatibility aliases: feels_like, humidity
  - UV index: present when provider supplies it; null when absent
  - Heat index: Rothfusz derivation with valid-range guard; null outside range
  - Data-quality notes for every case above
  - Missing / null optional values never silently replaced with demo values

All HTTP calls are mocked — no live network requests are made.
All tests are additive and do not duplicate assertions already in
test_weather_service.py or test_weather_route.py.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.weather_service import (
    WeatherObservation,
    WeatherServiceError,
    _parse_observation,
    derive_heat_index,
)


# ---------------------------------------------------------------------------
# Helpers shared across test groups
# ---------------------------------------------------------------------------

def _make_open_meteo_response(
    temperature: float = 39.4,
    apparent_temperature: float = 43.1,
    relative_humidity: int = 55,
    wind_speed: float = 14.5,
    weather_code: int = 1,
    time: str = "2024-05-15T12:00",
    timezone: str = "Asia/Kolkata",
    uv_index: float | None = 8.5,   # provider supplies this by default in new tests
) -> dict:
    """Build a minimal Open-Meteo-like JSON body, optionally with uv_index."""
    current: dict = {
        "time": time,
        "temperature_2m": temperature,
        "apparent_temperature": apparent_temperature,
        "relative_humidity_2m": relative_humidity,
        "wind_speed_10m": wind_speed,
        "weather_code": weather_code,
    }
    if uv_index is not None:
        current["uv_index"] = uv_index
    return {
        "latitude": 17.385,
        "longitude": 78.487,
        "timezone": timezone,
        "current_units": {
            "temperature_2m": "°C",
            "apparent_temperature": "°C",
            "relative_humidity_2m": "%",
            "wind_speed_10m": "km/h",
            "uv_index": "index",
        },
        "current": current,
    }


def _make_observation(
    lat: float = 17.385,
    lon: float = 78.487,
    temperature: float = 39.4,
    apparent_temperature: float = 43.1,
    relative_humidity: int = 55,
    wind_speed: float = 14.5,
    weather_code: int = 1,
    uv_index: float | None = 8.5,
    heat_index: float | None = None,
) -> WeatherObservation:
    """Build a WeatherObservation with optional uv/heat fields."""
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
        units={
            "temperature": "°C",
            "apparent_temperature": "°C",
            "feels_like": "°C",
            "relative_humidity": "%",
            "humidity": "%",
            "wind_speed": "km/h",
            "uv_index": "index",
        },
        data_quality_notes=["Model-derived data."],
        uv_index=uv_index,
        heat_index=heat_index,
    )


# ===========================================================================
# 1. derive_heat_index — unit tests
# ===========================================================================

class TestDeriveHeatIndex:
    """Tests for the Rothfusz heat-index derivation function."""

    def test_returns_none_below_temp_threshold(self):
        """T < 27 °C → None regardless of RH."""
        assert derive_heat_index(26.9, 80) is None

    def test_returns_none_below_rh_threshold(self):
        """RH < 40 % → None regardless of temperature."""
        assert derive_heat_index(35.0, 39) is None

    def test_returns_none_when_both_below_threshold(self):
        assert derive_heat_index(20.0, 30) is None

    def test_returns_none_at_exact_temp_boundary_exclusive(self):
        """Boundary is inclusive at 27 — just below should be None."""
        assert derive_heat_index(26.99, 50) is None

    def test_returns_float_at_exact_boundaries(self):
        """T == 27 and RH == 40 — both inclusive — should return a value."""
        result = derive_heat_index(27.0, 40)
        assert result is not None
        assert isinstance(result, float)

    def test_high_temp_high_humidity_produces_value(self):
        """Classic hot-humid case should produce a heat index above input temp."""
        hi = derive_heat_index(40.0, 70)
        assert hi is not None
        assert hi > 40.0   # heat index > dry-bulb at high humidity

    def test_result_is_rounded_to_one_decimal(self):
        hi = derive_heat_index(39.4, 55)
        assert hi is not None
        assert hi == round(hi, 1)

    def test_moderate_hot_dry_returns_none(self):
        """35 °C but only 20 % RH — below RH threshold."""
        assert derive_heat_index(35.0, 20) is None

    @pytest.mark.parametrize("temp,rh", [
        (27.0, 40),
        (35.0, 50),
        (42.0, 65),
        (45.0, 80),
    ])
    def test_parametrized_valid_range(self, temp, rh):
        result = derive_heat_index(temp, rh)
        assert result is not None
        assert isinstance(result, float)


# ===========================================================================
# 2. _parse_observation — UV index and heat index handling
# ===========================================================================

class TestParseObservationNewFields:
    """Tests for UV index and heat index in the parser."""

    def test_uv_index_present_in_response(self):
        data = _make_open_meteo_response(uv_index=8.5, temperature=39.0, relative_humidity=55)
        obs = _parse_observation(data, 17.385, 78.487)
        assert obs.uv_index == pytest.approx(8.5)

    def test_uv_index_absent_returns_none(self):
        data = _make_open_meteo_response(uv_index=None, temperature=39.0, relative_humidity=55)
        obs = _parse_observation(data, 17.385, 78.487)
        assert obs.uv_index is None

    def test_uv_absent_adds_quality_note(self):
        data = _make_open_meteo_response(uv_index=None)
        obs = _parse_observation(data, 17.385, 78.487)
        combined = " ".join(obs.data_quality_notes).lower()
        assert "uv_index" in combined
        assert "null" in combined

    def test_uv_present_adds_quality_note(self):
        data = _make_open_meteo_response(uv_index=6.0)
        obs = _parse_observation(data, 17.385, 78.487)
        combined = " ".join(obs.data_quality_notes).lower()
        assert "uv_index" in combined
        # Should mention it is a model/estimate, not measurement
        assert "model" in combined or "estimate" in combined or "gfs" in combined

    def test_heat_index_computed_within_valid_range(self):
        """T=39, RH=55 — both above thresholds — heat_index must be a float."""
        data = _make_open_meteo_response(temperature=39.0, relative_humidity=55)
        obs = _parse_observation(data, 17.385, 78.487)
        assert obs.heat_index is not None
        assert isinstance(obs.heat_index, float)
        assert obs.heat_index > 39.0   # heat index > dry-bulb

    def test_heat_index_none_below_temp_threshold(self):
        """T=20 — heat index must be None."""
        data = _make_open_meteo_response(temperature=20.0, relative_humidity=80)
        obs = _parse_observation(data, 17.385, 78.487)
        assert obs.heat_index is None

    def test_heat_index_none_below_rh_threshold(self):
        """RH=30 — heat index must be None."""
        data = _make_open_meteo_response(temperature=40.0, relative_humidity=30)
        obs = _parse_observation(data, 17.385, 78.487)
        assert obs.heat_index is None

    def test_heat_index_absent_adds_quality_note(self):
        data = _make_open_meteo_response(temperature=20.0, relative_humidity=20)
        obs = _parse_observation(data, 17.385, 78.487)
        combined = " ".join(obs.data_quality_notes).lower()
        assert "heat_index" in combined
        assert "null" in combined

    def test_heat_index_present_adds_derived_quality_note(self):
        data = _make_open_meteo_response(temperature=40.0, relative_humidity=65)
        obs = _parse_observation(data, 17.385, 78.487)
        combined = " ".join(obs.data_quality_notes).lower()
        assert "heat_index" in combined
        assert "derived" in combined or "estimate" in combined or "rothfusz" in combined

    def test_heat_index_distinct_from_apparent_temperature(self):
        """heat_index (Rothfusz) must not equal apparent_temperature (provider field)."""
        data = _make_open_meteo_response(
            temperature=39.4,
            apparent_temperature=43.1,  # provider value
            relative_humidity=55,
        )
        obs = _parse_observation(data, 17.385, 78.487)
        assert obs.apparent_temperature == pytest.approx(43.1)
        assert obs.heat_index is not None
        # These are different computations and will differ in value
        assert obs.heat_index != pytest.approx(43.1)

    def test_units_include_feels_like_and_humidity_keys(self):
        data = _make_open_meteo_response()
        obs = _parse_observation(data, 17.385, 78.487)
        assert "feels_like" in obs.units
        assert "humidity" in obs.units

    def test_units_feels_like_value_is_celsius(self):
        data = _make_open_meteo_response()
        obs = _parse_observation(data, 17.385, 78.487)
        assert obs.units["feels_like"] == "°C"

    def test_units_humidity_value_is_percent(self):
        data = _make_open_meteo_response()
        obs = _parse_observation(data, 17.385, 78.487)
        assert obs.units["humidity"] == "%"


# ===========================================================================
# 3. GET /api/weather — response alias fields via route
# ===========================================================================

class TestWeatherRouteAliasFields:
    """Verify the alias fields are present and correct in the HTTP response."""

    @pytest.mark.asyncio
    async def test_response_has_feels_like_field(self):
        obs = _make_observation(apparent_temperature=43.1)
        with patch("app.routes.weather.get_current_weather", new=AsyncMock(return_value=obs)):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/weather", params={"lat": 17.385, "lon": 78.487})
        assert response.status_code == 200
        assert "feels_like" in response.json()

    @pytest.mark.asyncio
    async def test_feels_like_equals_apparent_temperature(self):
        obs = _make_observation(apparent_temperature=43.1)
        with patch("app.routes.weather.get_current_weather", new=AsyncMock(return_value=obs)):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/weather", params={"lat": 17.385, "lon": 78.487})
        data = response.json()
        assert data["feels_like"] == pytest.approx(data["apparent_temperature"])

    @pytest.mark.asyncio
    async def test_response_has_humidity_field(self):
        obs = _make_observation(relative_humidity=55)
        with patch("app.routes.weather.get_current_weather", new=AsyncMock(return_value=obs)):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/weather", params={"lat": 17.385, "lon": 78.487})
        assert response.status_code == 200
        assert "humidity" in response.json()

    @pytest.mark.asyncio
    async def test_humidity_equals_relative_humidity(self):
        obs = _make_observation(relative_humidity=55)
        with patch("app.routes.weather.get_current_weather", new=AsyncMock(return_value=obs)):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/weather", params={"lat": 17.385, "lon": 78.487})
        data = response.json()
        assert data["humidity"] == data["relative_humidity"] == 55

    @pytest.mark.asyncio
    async def test_uv_index_present_in_response_when_available(self):
        obs = _make_observation(uv_index=8.5)
        with patch("app.routes.weather.get_current_weather", new=AsyncMock(return_value=obs)):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/weather", params={"lat": 17.385, "lon": 78.487})
        data = response.json()
        assert "uv_index" in data
        assert data["uv_index"] == pytest.approx(8.5)

    @pytest.mark.asyncio
    async def test_uv_index_null_when_provider_absent(self):
        obs = _make_observation(uv_index=None)
        with patch("app.routes.weather.get_current_weather", new=AsyncMock(return_value=obs)):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/weather", params={"lat": 17.385, "lon": 78.487})
        data = response.json()
        assert "uv_index" in data
        assert data["uv_index"] is None

    @pytest.mark.asyncio
    async def test_heat_index_present_when_in_valid_range(self):
        obs = _make_observation(heat_index=44.2)
        with patch("app.routes.weather.get_current_weather", new=AsyncMock(return_value=obs)):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/weather", params={"lat": 17.385, "lon": 78.487})
        data = response.json()
        assert "heat_index" in data
        assert data["heat_index"] == pytest.approx(44.2)

    @pytest.mark.asyncio
    async def test_heat_index_null_when_out_of_range(self):
        obs = _make_observation(temperature=20.0, heat_index=None)
        with patch("app.routes.weather.get_current_weather", new=AsyncMock(return_value=obs)):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/weather", params={"lat": 17.385, "lon": 78.487})
        data = response.json()
        assert "heat_index" in data
        assert data["heat_index"] is None

    @pytest.mark.asyncio
    async def test_all_frontend_weather_panel_fields_present(self):
        """Every field that HeatRiskAnalysis.jsx weather panel reads must be present."""
        obs = _make_observation(uv_index=7.0, heat_index=45.0)
        with patch("app.routes.weather.get_current_weather", new=AsyncMock(return_value=obs)):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/weather", params={"lat": 17.385, "lon": 78.487})
        data = response.json()
        # Fields read by HeatRiskAnalysis.jsx (weather.X with ?? fallback)
        for field in ("temperature", "feels_like", "heat_index", "uv_index", "humidity"):
            assert field in data, f"Frontend field '{field}' missing from response"

    @pytest.mark.asyncio
    async def test_data_quality_notes_present(self):
        obs = _make_observation()
        with patch("app.routes.weather.get_current_weather", new=AsyncMock(return_value=obs)):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/weather", params={"lat": 17.385, "lon": 78.487})
        data = response.json()
        assert "data_quality_notes" in data
        assert isinstance(data["data_quality_notes"], list)

    @pytest.mark.asyncio
    async def test_observation_time_and_timezone_present(self):
        obs = _make_observation()
        with patch("app.routes.weather.get_current_weather", new=AsyncMock(return_value=obs)):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/weather", params={"lat": 17.385, "lon": 78.487})
        data = response.json()
        assert "observation_time" in data
        assert "timezone" in data
        assert data["timezone"] == "Asia/Kolkata"
