"""
member2-weather-risk/app/routes/weather.py

Weather router — GET /api/weather

Matches the frontend API contract:
    fetchWeather(lat, lon) → apiClient.get('/api/weather', { params: { lat, lon } })
    (ChhayaRakshak-AI-main/frontend/src/services/api.js)

Query parameters
----------------
lat : float  — Latitude (°N), required.  Range: -90 to 90.
lon : float  — Longitude (°E), required. Range: -180 to 180.

Responses
---------
200  WeatherResponse     — Successful observation from Open-Meteo.
400  WeatherErrorResponse — Invalid coordinates supplied by the caller.
503  WeatherErrorResponse — Upstream weather API is unavailable or returned
                            an error; no fabricated data is returned.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.schemas.weather_schemas import WeatherErrorResponse, WeatherResponse
from app.services.weather_service import WeatherServiceError, get_current_weather

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Weather"])


@router.get(
    "/weather",
    response_model=WeatherResponse,
    responses={
        400: {"model": WeatherErrorResponse, "description": "Invalid coordinates"},
        503: {"model": WeatherErrorResponse, "description": "Upstream weather API error"},
    },
    summary="Current weather observation for a lat/lon pair",
    description=(
        "Retrieves current weather observations from Open-Meteo for the supplied "
        "coordinates. Returns real API data only — never fabricated values. "
        "Returns HTTP 503 if the upstream service is unavailable."
    ),
)
async def get_weather(
    lat: float = Query(..., description="Latitude (°N)", ge=-90, le=90),
    lon: float = Query(..., description="Longitude (°E)", ge=-180, le=180),
) -> JSONResponse | WeatherResponse:
    """
    Fetch current weather for ``lat``, ``lon``.

    Uses Open-Meteo (no API key required). On any upstream failure the
    endpoint returns a structured error — it never substitutes fabricated data.
    """
    try:
        obs = await get_current_weather(lat=lat, lon=lon)
    except WeatherServiceError as exc:
        # Distinguish coordinate-validation errors (400) from upstream errors (503)
        if "out of range" in exc.message.lower():
            return JSONResponse(
                status_code=400,
                content=WeatherErrorResponse(
                    detail=exc.message, latitude=lat, longitude=lon
                ).model_dump(),
            )
        logger.warning("Weather service error: %s", exc.message)
        return JSONResponse(
            status_code=503,
            content=WeatherErrorResponse(
                detail=exc.message, latitude=lat, longitude=lon
            ).model_dump(),
        )

    return WeatherResponse(
        latitude=obs.latitude,
        longitude=obs.longitude,
        temperature=obs.temperature,
        apparent_temperature=obs.apparent_temperature,
        relative_humidity=obs.relative_humidity,
        wind_speed=obs.wind_speed,
        weather_code=obs.weather_code,
        observation_time=obs.observation_time,
        timezone=obs.timezone,
        units=obs.units,
        data_quality_notes=obs.data_quality_notes,
        # Frontend-compatibility aliases
        feels_like=obs.apparent_temperature,
        humidity=obs.relative_humidity,
        # Optional / derived fields — None when unavailable
        uv_index=obs.uv_index,
        heat_index=obs.heat_index,
    )
