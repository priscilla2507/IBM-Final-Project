
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

# Load backend/.env regardless of the terminal's working directory.
BACKEND_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BACKEND_DIR / ".env")

API_KEY = os.getenv("OPENWEATHER_API_KEY")

GEOCODING_URL = "https://api.openweathermap.org/geo/1.0/direct"
WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"


def _check_api_key():
    if not API_KEY:
        raise RuntimeError(
            "OPENWEATHER_API_KEY is missing from backend/.env"
        )


def find_location(location_name: str):
    _check_api_key()

    try:
        response = requests.get(
            GEOCODING_URL,
            params={
                "q": location_name,
                "limit": 5,
                "appid": API_KEY,
            },
            timeout=15,
        )
        response.raise_for_status()
        results = response.json()

        if not results:
            raise ValueError(
                f"No location found for '{location_name}'."
            )

        # Prefer an exact name match if one is available.
        match = next(
            (
                item for item in results
                if item["name"].lower() == location_name.strip().lower()
            ),
            results[0],
        )

        return {
            "name": match["name"],
            "latitude": match["lat"],
            "longitude": match["lon"],
            "admin1": match.get("state"),
            "country": match.get("country"),
        }

    except requests.RequestException as exc:
        raise RuntimeError(
            f"OpenWeatherMap geocoding failed: {exc}"
        ) from exc


def get_weather(latitude: float, longitude: float):
    _check_api_key()

    try:
        response = requests.get(
            WEATHER_URL,
            params={
                "lat": latitude,
                "lon": longitude,
                "appid": API_KEY,
                "units": "metric",
            },
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()

        main = data.get("main", {})
        weather = data.get("weather", [{}])[0]
        wind = data.get("wind", {})
        rain = data.get("rain", {})
        clouds = data.get("clouds", {})

        if main.get("temp") is None or main.get("humidity") is None:
            raise RuntimeError(
                "OpenWeatherMap returned incomplete weather data."
            )

        # Keep the current-weather shape expected by assessment_routes.py.
        return {
            "latitude": data.get("coord", {}).get("lat", latitude),
            "longitude": data.get("coord", {}).get("lon", longitude),
            "current": {
                "temperature_2m": main["temp"],
                "relative_humidity_2m": main["humidity"],
                "apparent_temperature": main.get("feels_like"),
                "precipitation": rain.get("1h", 0),
                "wind_speed_10m": wind.get("speed"),
                "time": data.get("dt"),
                "weather_description": weather.get("description"),
                "weather_condition": weather.get("main"),
                "cloud_cover": clouds.get("all"),
            },
            "timezone": data.get("timezone"),
            "source": "OpenWeatherMap",
        }

    except requests.RequestException as exc:
        raise RuntimeError(
            f"Unable to fetch OpenWeatherMap data: {exc}"
        ) from exc
