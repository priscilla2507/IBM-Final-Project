
import time
import requests

API_BASE_URL = "https://api.worldpop.org/v2"


def get_population_near_landmark(
    latitude: float,
    longitude: float,
    radius_m: int = 500,
    year: int = 2025,
    resolution: str = "100m",
) -> dict:
    """
    Estimate resident population within a square area around a landmark.

    Note: This is resident population, not daily visitors or
    people protected by heat-mitigation interventions.
    """

    if not -90 <= latitude <= 90:
        raise ValueError("Latitude must be between -90 and 90.")

    if not -180 <= longitude <= 180:
        raise ValueError("Longitude must be between -180 and 180.")

    if radius_m <= 0:
        raise ValueError("radius_m must be greater than zero.")

    if resolution not in {"100m", "1km"}:
        raise ValueError("Resolution must be '100m' or '1km'.")

    if not 2015 <= year <= 2030:
        raise ValueError("Year must be between 2015 and 2030.")

    # Approximate a square area around the landmark.
    # Longitude distance varies with latitude.
    latitude_offset = radius_m / 111_320
    longitude_offset = radius_m / (
        111_320 * max(abs(__import__("math").cos(
            __import__("math").radians(latitude)
        )), 0.01)
    )

    west = longitude - longitude_offset
    east = longitude + longitude_offset
    south = max(-90, latitude - latitude_offset)
    north = min(90, latitude + latitude_offset)

    polygon = {
        "type": "Polygon",
        "coordinates": [[
            [west, south],
            [east, south],
            [east, north],
            [west, north],
            [west, south],
        ]],
    }

    try:
        response = requests.post(
            f"{API_BASE_URL}/population",
            json={
                "geojson": polygon,
                "year": year,
                "resolution": resolution,
            },
            timeout=30,
        )
        response.raise_for_status()
        task = response.json()

        task_id = task.get("task_id")
        if not task_id:
            raise RuntimeError(
                f"WorldPop did not return a task ID: {task}"
            )

        # Poll for the asynchronous result, up to 60 seconds.
        deadline = time.monotonic() + 60

        while time.monotonic() < deadline:
            result_response = requests.get(
                f"{API_BASE_URL}/tasks/{task_id}",
                timeout=15,
            )
            result_response.raise_for_status()
            result = result_response.json()

            if result.get("status") == "success":
                data = result.get("result", {})
                return {
                    "estimated_resident_population": round(
                        data["total_population"]
                    ),
                    "area_km2": data.get("area_km2"),
                    "data_year": data.get("data_year", year),
                    "resolution": resolution,
                    "source": data.get(
                        "data_source",
                        "WorldPop Global 2 Population Data",
                    ),
                    "radius_m": radius_m,
                    "area_shape": "square",
                    "interpretation": (
                        "Estimated resident population in the defined "
                        "square area; not daily visitors or people protected."
                    ),
                }

            if result.get("status") == "failure":
                raise RuntimeError(
                    f"WorldPop task failed: {result.get('error')}"
                )

            time.sleep(2)

        raise TimeoutError(
            "WorldPop is still processing the request. Please try again."
        )

    except requests.RequestException as exc:
        raise RuntimeError(
            f"Unable to retrieve WorldPop population data: {exc}"
        ) from exc
