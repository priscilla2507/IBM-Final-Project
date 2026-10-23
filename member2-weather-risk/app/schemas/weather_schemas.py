"""
member2-weather-risk/app/schemas/weather_schemas.py

Pydantic models for the weather endpoint.

These schemas define the contract for:
  GET /api/weather?lat=<lat>&lon=<lon>

Frontend compatibility
----------------------
The response includes both the canonical field names used internally
(``apparent_temperature``, ``relative_humidity``) and the alias names
consumed by the existing HeatRiskAnalysis.jsx weather panel
(``feels_like``, ``humidity``).  Both sets of names carry the same values.

``uv_index`` and ``heat_index`` are returned when data is genuinely available:
  - ``uv_index``  : sourced from the Open-Meteo ``uv_index`` current variable
                    when the provider returns it; otherwise ``null``.
  - ``heat_index``: derived from temperature + relative humidity via the
                    Rothfusz equation when inputs are within the formula's
                    valid range (T ≥ 27 °C, RH ≥ 40 %); otherwise ``null``.
                    The derivation is clearly flagged in ``data_quality_notes``
                    — it is NOT a direct provider measurement.

Neither field ever carries a hardcoded demo value.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class WeatherResponse(BaseModel):
    """
    Successful weather observation returned by GET /api/weather.

    FIELD REFERENCE
    ---------------
    Primary (canonical) fields
    ~~~~~~~~~~~~~~~~~~~~~~~~~~
    temperature           : 2-metre air temperature in °C  (Open-Meteo temperature_2m)
    apparent_temperature  : Apparent / feels-like temperature in °C
                            (Open-Meteo apparent_temperature — provider-computed blend
                             of heat index, wind chill and wet-bulb temperature)
    relative_humidity     : Relative humidity at 2 m in %  (Open-Meteo relative_humidity_2m)
    wind_speed            : Wind speed at 10 m in km/h     (Open-Meteo wind_speed_10m)
    weather_code          : WMO weather interpretation code (https://open-meteo.com/en/docs)
    observation_time      : ISO-8601 observation timestamp (local timezone from provider)
    timezone              : IANA timezone, e.g. "Asia/Kolkata"
    units                 : Dict of unit strings for each numeric field
    data_quality_notes    : Human-readable caveats (model resolution, derivation flags, etc.)

    Frontend-compatibility aliases (same values, frontend field names)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    feels_like            : Alias for apparent_temperature — consumed by HeatRiskAnalysis.jsx
    humidity              : Alias for relative_humidity    — consumed by HeatRiskAnalysis.jsx

    Derived / optional fields
    ~~~~~~~~~~~~~~~~~~~~~~~~~
    uv_index              : UV index sourced from Open-Meteo uv_index variable.
                            null when the provider does not return a value.
    heat_index            : Rothfusz heat-index estimate in °C, derived from temperature
                            and relative humidity when T ≥ 27 °C and RH ≥ 40 %.
                            null outside that range or when inputs are unavailable.
                            NOT a direct provider measurement — flagged in data_quality_notes.
    """

    latitude: float = Field(..., description="Requested latitude (°N)")
    longitude: float = Field(..., description="Requested longitude (°E)")

    # ── Primary canonical fields ────────────────────────────────────────────
    temperature: float = Field(..., description="Air temperature at 2 m (°C)")
    apparent_temperature: float = Field(
        ..., description="Apparent / feels-like temperature (°C) — provider-computed"
    )
    relative_humidity: int = Field(..., description="Relative humidity at 2 m (%)")
    wind_speed: float = Field(..., description="Wind speed at 10 m (km/h)")
    weather_code: int = Field(..., description="WMO weather interpretation code")
    observation_time: datetime = Field(
        ..., description="ISO-8601 observation timestamp (local timezone)"
    )
    timezone: str = Field(..., description='IANA timezone, e.g. "Asia/Kolkata"')
    units: dict[str, str] = Field(
        ...,
        description="Unit strings for each numeric field",
        examples=[{
            "temperature": "°C",
            "apparent_temperature": "°C",
            "relative_humidity": "%",
            "wind_speed": "km/h",
        }],
    )
    data_quality_notes: list[str] = Field(
        default_factory=list,
        description=(
            "Data-quality caveats: model resolution, observation lag, "
            "derivation flags for heat_index, UV index availability."
        ),
    )

    # ── Frontend-compatibility aliases ──────────────────────────────────────
    # These carry the same values as apparent_temperature / relative_humidity
    # and exist solely so the existing HeatRiskAnalysis.jsx weather panel
    # (which reads weather.feels_like and weather.humidity) receives live data.
    feels_like: float = Field(
        ...,
        description=(
            "Alias for apparent_temperature. "
            "Provided for compatibility with the frontend weather panel."
        ),
    )
    humidity: int = Field(
        ...,
        description=(
            "Alias for relative_humidity. "
            "Provided for compatibility with the frontend weather panel."
        ),
    )

    # ── Derived / optional fields ────────────────────────────────────────────
    uv_index: Optional[float] = Field(
        None,
        description=(
            "UV index sourced from Open-Meteo uv_index variable. "
            "null when the provider does not return a value for this location/time."
        ),
    )
    heat_index: Optional[float] = Field(
        None,
        description=(
            "Rothfusz heat-index estimate in °C. "
            "Derived from temperature and relative humidity when T ≥ 27 °C and RH ≥ 40 %. "
            "null outside that range. "
            "This is a computed estimate, NOT a direct provider measurement."
        ),
    )


class WeatherErrorResponse(BaseModel):
    """Returned when weather data cannot be retrieved from the upstream API."""

    detail: str = Field(
        ...,
        description="Human-readable explanation of why weather data is unavailable",
    )
    latitude: Optional[float] = Field(None, description="Requested latitude")
    longitude: Optional[float] = Field(None, description="Requested longitude")
