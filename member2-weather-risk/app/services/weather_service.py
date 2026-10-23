"""
member2-weather-risk/app/services/weather_service.py

Weather data retrieval via the Open-Meteo API.

DESIGN PRINCIPLES
-----------------
1. Never fabricate live weather data.
   If the upstream API fails (timeout, HTTP error, malformed JSON, missing
   required fields), this service raises a ``WeatherServiceError`` instead of
   returning estimated or hardcoded values.

2. Fail fast with structured errors.
   Callers receive a typed exception with a clear message; the route layer
   converts this to an appropriate HTTP response.

3. Testable without network access.
   All HTTP calls go through an ``httpx.AsyncClient`` that is created inside
   ``get_current_weather`` by default, but can be injected via the
   ``client`` parameter to allow mocking in tests.

4. Transparent data-quality notes.
   The returned ``WeatherObservation`` includes a ``data_quality_notes`` list
   that documents known limitations — including when uv_index is absent and
   when heat_index is a derived estimate rather than a provider measurement.

5. Optional fields are genuinely optional.
   ``uv_index`` is requested from the provider and stored only when the
   provider actually supplies a non-null numeric value.
   ``heat_index`` is derived (not requested) and only produced when the
   Rothfusz formula's input range is satisfied (T ≥ 27 °C, RH ≥ 40 %).
   Both fields are ``None`` — never a hardcoded fallback — when unavailable.

Open-Meteo API reference
------------------------
https://open-meteo.com/en/docs

No API key is required. The current-weather endpoint we call is:

    GET https://api.open-meteo.com/v1/forecast
        ?latitude=<lat>
        &longitude=<lon>
        &current=temperature_2m,apparent_temperature,relative_humidity_2m,
                  wind_speed_10m,weather_code,uv_index
        &timezone=auto
        &forecast_days=1

UV index note
-------------
Open-Meteo does include ``uv_index`` in the ``current`` block when the
``uv_index`` variable is requested.  The value is a model estimate (not a
ground measurement), derived from the GFS / ICON solar radiation forecast.
It is absent (null in our response) when the API does not return it — for
example when the request fails or the field is missing in the response body.

Heat index derivation
---------------------
The Rothfusz regression (NWS 1990) is used to derive an apparent heat stress
temperature from dry-bulb temperature and relative humidity:

    HI = -8.78469 + 1.61139411·T + 2.338549·RH
         - 0.14611605·T·RH - 0.01230809·T²
         - 0.01642482·RH² + 0.00221173·T²·RH
         + 0.00072546·T·RH² - 0.00000358·T²·RH²

Where T is in °C and RH is in %.

Valid range: T ≥ 27 °C AND RH ≥ 40 %.  Outside this range the formula
produces unreliable results and we return None.

The derived value is labelled as an ESTIMATE in ``data_quality_notes`` and is
distinct from Open-Meteo's ``apparent_temperature`` (which is a separate
provider-computed field blending heat index, wind chill and wet-bulb effects).

Integration note
----------------
Member 2 will not call any shared database here. Persistence is deferred to
the integration phase with Member 4's shared session and models.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

OPEN_METEO_BASE_URL = "https://api.open-meteo.com/v1/forecast"

# Variables to request from the current-weather block.
# uv_index is included; the provider returns it when available.
_CURRENT_VARS = (
    "temperature_2m,"
    "apparent_temperature,"
    "relative_humidity_2m,"
    "wind_speed_10m,"
    "weather_code,"
    "uv_index"
)

# Timeouts: connect + read.
_CONNECT_TIMEOUT = 5.0   # seconds
_READ_TIMEOUT    = 10.0  # seconds

# Data-quality notes that always apply to Open-Meteo current observations.
_NOTE_MODEL_DERIVED = (
    "Data is sourced from the Open-Meteo ERA5/ICON numerical weather model; "
    "it is model-derived and may lag actual surface conditions by up to 1 hour."
)
_NOTE_WMO_CODES = (
    "Weather codes follow the WMO interpretation code table "
    "(see https://open-meteo.com/en/docs for the full mapping)."
)
_NOTE_UV_ABSENT = (
    "uv_index: Open-Meteo did not return a UV index value for this observation. "
    "The field is null."
)
_NOTE_UV_PRESENT = (
    "uv_index: sourced from the Open-Meteo uv_index model variable "
    "(GFS/ICON solar radiation estimate — not a ground measurement)."
)
_NOTE_HEAT_INDEX_DERIVED = (
    "heat_index: DERIVED ESTIMATE via the Rothfusz regression (NWS 1990) "
    "from temperature and relative humidity. "
    "Valid range: T ≥ 27 °C and RH ≥ 40 %. "
    "This is NOT a direct provider measurement — treat as indicative only."
)
_NOTE_HEAT_INDEX_ABSENT = (
    "heat_index: not computed — inputs are outside the Rothfusz formula's "
    "valid range (T ≥ 27 °C and RH ≥ 40 %). The field is null."
)

# ---------------------------------------------------------------------------
# Result / error types
# ---------------------------------------------------------------------------

@dataclass
class WeatherObservation:
    """
    Parsed and validated observation from Open-Meteo.

    Required fields are sourced directly from the API and are never fabricated.
    Optional fields (``uv_index``, ``heat_index``) are None when unavailable
    rather than filled with fallback values.
    """

    latitude: float
    longitude: float
    temperature: float            # °C  (temperature_2m)
    apparent_temperature: float   # °C  (apparent_temperature — provider-computed)
    relative_humidity: int        # %   (relative_humidity_2m)
    wind_speed: float             # km/h (wind_speed_10m)
    weather_code: int             # WMO code
    observation_time: datetime    # from current.time
    timezone: str                 # IANA, e.g. "Asia/Kolkata"
    units: dict[str, str] = field(default_factory=dict)
    data_quality_notes: list[str] = field(default_factory=list)

    # Optional fields — None when not available / out of derivation range
    uv_index: Optional[float] = None
    heat_index: Optional[float] = None   # Rothfusz estimate; NOT a provider measurement


class WeatherServiceError(Exception):
    """
    Raised when weather data cannot be returned.

    Attributes
    ----------
    message : str
        Human-readable explanation of the failure.
    upstream_status : int or None
        HTTP status code from the upstream response, if available.
    """

    def __init__(self, message: str, upstream_status: Optional[int] = None) -> None:
        super().__init__(message)
        self.message = message
        self.upstream_status = upstream_status


# ---------------------------------------------------------------------------
# Coordinate validation
# ---------------------------------------------------------------------------

def validate_coordinates(lat: float, lon: float) -> None:
    """
    Raise ``WeatherServiceError`` if coordinates are outside valid bounds.

    Valid range: latitude −90 to +90, longitude −180 to +180.
    """
    if not (-90.0 <= lat <= 90.0):
        raise WeatherServiceError(
            f"Latitude {lat} is out of range. Must be between -90 and 90."
        )
    if not (-180.0 <= lon <= 180.0):
        raise WeatherServiceError(
            f"Longitude {lon} is out of range. Must be between -180 and 180."
        )


# ---------------------------------------------------------------------------
# Heat-index derivation
# ---------------------------------------------------------------------------

def derive_heat_index(temp_c: float, rh_pct: int) -> Optional[float]:
    """
    Compute the Rothfusz heat index in °C when inputs are within the valid range.

    The Rothfusz regression (National Weather Service, 1990) is defined for
    T ≥ 27 °C (80 °F) and RH ≥ 40 %.  Outside that range the formula produces
    unreliable results and this function returns ``None``.

    The result is labelled as a DERIVED ESTIMATE in the observation's
    ``data_quality_notes``.  It is NOT Open-Meteo's ``apparent_temperature``
    field and should not be presented as a provider measurement.

    Parameters
    ----------
    temp_c :
        Dry-bulb temperature in °C.
    rh_pct :
        Relative humidity in percent (0–100).

    Returns
    -------
    float
        Heat index in °C, or ``None`` when inputs are outside the valid range.
    """
    if temp_c < 27.0 or rh_pct < 40:
        return None

    T = temp_c
    R = float(rh_pct)

    hi_c = (
        -8.78469
        + 1.61139411 * T
        + 2.338549 * R
        - 0.14611605 * T * R
        - 0.01230809 * T ** 2
        - 0.01642482 * R ** 2
        + 0.00221173 * T ** 2 * R
        + 0.00072546 * T * R ** 2
        - 0.00000358 * T ** 2 * R ** 2
    )
    return round(hi_c, 1)


# ---------------------------------------------------------------------------
# Main service function
# ---------------------------------------------------------------------------

async def get_current_weather(
    lat: float,
    lon: float,
    *,
    client: Optional[httpx.AsyncClient] = None,
) -> WeatherObservation:
    """
    Fetch current weather observations for the given coordinates.

    Parameters
    ----------
    lat :
        Latitude in decimal degrees (−90 to +90).
    lon :
        Longitude in decimal degrees (−180 to +180).
    client :
        Optional ``httpx.AsyncClient`` to use.  Inject a mock client in tests.
        If ``None``, a new client with configured timeouts is created.

    Returns
    -------
    WeatherObservation
        Parsed observation data from Open-Meteo, including:
        - Required fields sourced from the provider.
        - ``uv_index``: provider value when available, otherwise ``None``.
        - ``heat_index``: Rothfusz estimate when T ≥ 27 °C and RH ≥ 40 %,
          otherwise ``None``.  Never fabricated.

    Raises
    ------
    WeatherServiceError
        On invalid coordinates, upstream HTTP errors, timeouts,
        malformed JSON responses, or missing required fields.
    """
    validate_coordinates(lat, lon)

    params = {
        "latitude": lat,
        "longitude": lon,
        "current": _CURRENT_VARS,
        "timezone": "auto",
        "forecast_days": 1,
    }

    timeout = httpx.Timeout(_READ_TIMEOUT, connect=_CONNECT_TIMEOUT)
    own_client = client is None
    if own_client:
        client = httpx.AsyncClient(timeout=timeout)

    try:
        logger.info("Fetching Open-Meteo weather for lat=%.4f lon=%.4f", lat, lon)
        response = await client.get(OPEN_METEO_BASE_URL, params=params)
    except httpx.TimeoutException as exc:
        raise WeatherServiceError(
            "Weather service timed out. Please try again shortly."
        ) from exc
    except httpx.RequestError as exc:
        raise WeatherServiceError(
            f"Could not reach the weather API: {exc}"
        ) from exc
    finally:
        if own_client:
            await client.aclose()

    # ---- HTTP-level error check ----------------------------------------
    if response.status_code != 200:
        raise WeatherServiceError(
            f"Weather API returned HTTP {response.status_code}. "
            "Upstream service may be temporarily unavailable.",
            upstream_status=response.status_code,
        )

    # ---- JSON parse -------------------------------------------------------
    try:
        data = response.json()
    except Exception as exc:
        raise WeatherServiceError(
            "Weather API returned malformed JSON. Cannot parse response."
        ) from exc

    return _parse_observation(data, lat, lon)


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------

def _parse_observation(data: dict, lat: float, lon: float) -> WeatherObservation:
    """
    Parse the Open-Meteo JSON response into a ``WeatherObservation``.

    Raises ``WeatherServiceError`` for any missing required fields.
    Optional fields (``uv_index``) are recorded as ``None`` with a quality
    note when absent rather than causing an error.
    """
    current = data.get("current")
    if not isinstance(current, dict):
        raise WeatherServiceError(
            "Weather API response is missing the 'current' block. "
            "The upstream format may have changed."
        )

    current_units = data.get("current_units", {})

    # --- Required numeric fields ------------------------------------------
    missing: list[str] = []
    for key in (
        "temperature_2m",
        "apparent_temperature",
        "relative_humidity_2m",
        "wind_speed_10m",
        "weather_code",
        "time",
    ):
        if key not in current:
            missing.append(key)

    if missing:
        raise WeatherServiceError(
            f"Weather API response is missing required field(s): {', '.join(missing)}. "
            "Cannot return a reliable observation."
        )

    # --- Parse observation time -------------------------------------------
    raw_time: str = current["time"]
    try:
        observation_time = datetime.fromisoformat(raw_time)
    except (ValueError, TypeError) as exc:
        raise WeatherServiceError(
            f"Weather API returned an unrecognisable time format: {raw_time!r}."
        ) from exc

    # --- Relative humidity is an integer in the API ----------------------
    try:
        humidity = int(current["relative_humidity_2m"])
    except (TypeError, ValueError) as exc:
        raise WeatherServiceError(
            "Weather API returned an invalid relative_humidity_2m value."
        ) from exc

    timezone = data.get("timezone", "UTC")
    temp = float(current["temperature_2m"])
    apparent = float(current["apparent_temperature"])
    wind = float(current["wind_speed_10m"])
    code = int(current["weather_code"])

    # --- Build units dict -------------------------------------------------
    units: dict[str, str] = {
        "temperature": current_units.get("temperature_2m", "°C"),
        "apparent_temperature": current_units.get("apparent_temperature", "°C"),
        "feels_like": current_units.get("apparent_temperature", "°C"),
        "relative_humidity": current_units.get("relative_humidity_2m", "%"),
        "humidity": current_units.get("relative_humidity_2m", "%"),
        "wind_speed": current_units.get("wind_speed_10m", "km/h"),
        "weather_code": "WMO code",
    }

    quality_notes: list[str] = [_NOTE_MODEL_DERIVED, _NOTE_WMO_CODES]

    # --- UV index (optional — sourced from provider when available) -------
    uv_raw = current.get("uv_index")
    if uv_raw is not None:
        try:
            uv_index: Optional[float] = float(uv_raw)
            units["uv_index"] = current_units.get("uv_index", "index")
            quality_notes.append(_NOTE_UV_PRESENT)
        except (TypeError, ValueError):
            uv_index = None
            quality_notes.append(_NOTE_UV_ABSENT)
    else:
        uv_index = None
        quality_notes.append(_NOTE_UV_ABSENT)

    # --- Heat index (derived — Rothfusz; never fabricated) ----------------
    heat_index = derive_heat_index(temp, humidity)
    if heat_index is not None:
        units["heat_index"] = "°C (derived)"
        quality_notes.append(_NOTE_HEAT_INDEX_DERIVED)
    else:
        quality_notes.append(_NOTE_HEAT_INDEX_ABSENT)

    logger.info(
        "Open-Meteo observation parsed: temp=%.1f°C apparent=%.1f°C "
        "humidity=%d%% wind=%.1f km/h code=%d uv=%s hi=%s time=%s tz=%s",
        temp, apparent, humidity, wind, code,
        uv_index, heat_index, raw_time, timezone,
    )

    return WeatherObservation(
        latitude=lat,
        longitude=lon,
        temperature=temp,
        apparent_temperature=apparent,
        relative_humidity=humidity,
        wind_speed=wind,
        weather_code=code,
        observation_time=observation_time,
        timezone=timezone,
        units=units,
        data_quality_notes=quality_notes,
        uv_index=uv_index,
        heat_index=heat_index,
    )
