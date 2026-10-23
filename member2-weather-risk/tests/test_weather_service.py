"""
member2-weather-risk/tests/test_weather_service.py

Unit tests for app/services/weather_service.py.

All HTTP calls are mocked — no live network requests are made.
"""

from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.services.weather_service import (
    WeatherObservation,
    WeatherServiceError,
    _parse_observation,
    get_current_weather,
    validate_coordinates,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_open_meteo_response(
    temperature: float = 39.4,
    apparent_temperature: float = 43.1,
    relative_humidity: int = 48,
    wind_speed: float = 14.5,
    weather_code: int = 1,
    time: str = "2024-05-15T12:00",
    timezone: str = "Asia/Kolkata",
) -> dict:
    """Build a minimal Open-Meteo-like JSON body."""
    return {
        "latitude": 17.385,
        "longitude": 78.487,
        "timezone": timezone,
        "current_units": {
            "temperature_2m": "°C",
            "apparent_temperature": "°C",
            "relative_humidity_2m": "%",
            "wind_speed_10m": "km/h",
        },
        "current": {
            "time": time,
            "temperature_2m": temperature,
            "apparent_temperature": apparent_temperature,
            "relative_humidity_2m": relative_humidity,
            "wind_speed_10m": wind_speed,
            "weather_code": weather_code,
        },
    }


def _mock_client(response_data: dict, status_code: int = 200) -> httpx.AsyncClient:
    """Return a mock AsyncClient that returns the given response."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = status_code
    mock_response.json.return_value = response_data

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.aclose = AsyncMock()
    # Support async context manager protocol
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


# ---------------------------------------------------------------------------
# validate_coordinates
# ---------------------------------------------------------------------------

def test_valid_coordinates_pass():
    validate_coordinates(17.385, 78.487)  # Hyderabad — must not raise


@pytest.mark.parametrize("lat,lon", [
    (91.0,   0.0),    # lat too high
    (-91.0,  0.0),    # lat too low
    (0.0,    181.0),  # lon too high
    (0.0,   -181.0),  # lon too low
])
def test_invalid_coordinates_raise(lat, lon):
    with pytest.raises(WeatherServiceError) as exc_info:
        validate_coordinates(lat, lon)
    assert "out of range" in exc_info.value.message.lower()


# ---------------------------------------------------------------------------
# _parse_observation — unit tests for the parser in isolation
# ---------------------------------------------------------------------------

def test_parse_observation_success():
    data = _make_open_meteo_response()
    obs = _parse_observation(data, lat=17.385, lon=78.487)

    assert isinstance(obs, WeatherObservation)
    assert obs.temperature == pytest.approx(39.4)
    assert obs.apparent_temperature == pytest.approx(43.1)
    assert obs.relative_humidity == 48
    assert obs.wind_speed == pytest.approx(14.5)
    assert obs.weather_code == 1
    assert obs.timezone == "Asia/Kolkata"
    assert obs.latitude == pytest.approx(17.385)
    assert obs.longitude == pytest.approx(78.487)
    assert isinstance(obs.observation_time, datetime)
    assert len(obs.data_quality_notes) >= 1


def test_parse_observation_missing_current_block():
    data = {"timezone": "Asia/Kolkata"}  # no 'current' key
    with pytest.raises(WeatherServiceError) as exc_info:
        _parse_observation(data, 17.0, 78.0)
    assert "current" in exc_info.value.message.lower()


@pytest.mark.parametrize("missing_key", [
    "temperature_2m",
    "apparent_temperature",
    "relative_humidity_2m",
    "wind_speed_10m",
    "weather_code",
    "time",
])
def test_parse_observation_missing_field(missing_key):
    data = _make_open_meteo_response()
    del data["current"][missing_key]
    with pytest.raises(WeatherServiceError) as exc_info:
        _parse_observation(data, 17.0, 78.0)
    assert missing_key in exc_info.value.message


def test_parse_observation_bad_time_format():
    data = _make_open_meteo_response(time="not-a-date")
    with pytest.raises(WeatherServiceError) as exc_info:
        _parse_observation(data, 17.0, 78.0)
    assert "time" in exc_info.value.message.lower()


# ---------------------------------------------------------------------------
# get_current_weather — integration tests with mocked HTTP
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_current_weather_success():
    data = _make_open_meteo_response()
    client = _mock_client(data, status_code=200)

    obs = await get_current_weather(lat=17.385, lon=78.487, client=client)

    assert obs.temperature == pytest.approx(39.4)
    assert obs.relative_humidity == 48
    assert obs.timezone == "Asia/Kolkata"


@pytest.mark.asyncio
async def test_get_current_weather_upstream_error_status():
    client = _mock_client({}, status_code=500)

    with pytest.raises(WeatherServiceError) as exc_info:
        await get_current_weather(lat=17.385, lon=78.487, client=client)
    assert "500" in exc_info.value.message
    assert exc_info.value.upstream_status == 500


@pytest.mark.asyncio
async def test_get_current_weather_404():
    client = _mock_client({}, status_code=404)

    with pytest.raises(WeatherServiceError) as exc_info:
        await get_current_weather(lat=17.385, lon=78.487, client=client)
    assert exc_info.value.upstream_status == 404


@pytest.mark.asyncio
async def test_get_current_weather_timeout():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
    mock_client.aclose = AsyncMock()

    with pytest.raises(WeatherServiceError) as exc_info:
        await get_current_weather(lat=17.385, lon=78.487, client=mock_client)
    assert "timed out" in exc_info.value.message.lower()


@pytest.mark.asyncio
async def test_get_current_weather_request_error():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(
        side_effect=httpx.RequestError("connection refused", request=MagicMock())
    )
    mock_client.aclose = AsyncMock()

    with pytest.raises(WeatherServiceError) as exc_info:
        await get_current_weather(lat=17.385, lon=78.487, client=mock_client)
    assert "weather api" in exc_info.value.message.lower()


@pytest.mark.asyncio
async def test_get_current_weather_malformed_json():
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.side_effect = json.JSONDecodeError("Expecting value", "", 0)

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.aclose = AsyncMock()

    with pytest.raises(WeatherServiceError) as exc_info:
        await get_current_weather(lat=17.385, lon=78.487, client=mock_client)
    assert "malformed" in exc_info.value.message.lower()


@pytest.mark.asyncio
async def test_get_current_weather_invalid_coords():
    """Coordinate validation fires before any HTTP call."""
    with pytest.raises(WeatherServiceError) as exc_info:
        await get_current_weather(lat=200.0, lon=78.487)
    assert "out of range" in exc_info.value.message.lower()
