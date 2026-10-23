
import os

from google import genai
from pydantic import BaseModel, Field
import time
from google.genai import errors

MODEL_NAME = "gemini-3.8-flash"


class InterventionPriority(BaseModel):
    intervention_type: str = Field(
        description="Exact intervention name supplied in the input."
    )
    benefit_score: int = Field(
        ge=1,
        le=100,
        description="Relative planning priority from 1 to 100."
    )
    explanation: str = Field(
        description="Why this intervention may help in this location."
    )


class LocationAnalysis(BaseModel):
    location_summary: str
    recommendations: list[InterventionPriority]


def analyze_location_interventions(
    location_name: str,
    weather: dict,
    candidates: list[dict],
) -> dict:
    """
    Use Gemini to prioritize supplied heat-protection interventions.

    Weather is live input from the existing weather service.
    Costs remain fixed planning assumptions supplied by our backend.
    Missing site and population data must not be invented.
    """

    if not os.getenv("GEMINI_API_KEY"):
        raise RuntimeError(
            "GEMINI_API_KEY is missing from the backend environment."
        )

    client = genai.Client()

    current = weather.get("current", {})

    available_interventions = [
        {
            "intervention_type": item["intervention_type"],
            "estimated_cost": item["estimated_cost"],
            "description": item["explanation"],
        }
        for item in candidates
    ]

    prompt = f"""
You are assisting with a heat-resilience planning prototype.

TARGET LOCATION:
{location_name}

CURRENT WEATHER:
Temperature: {current.get("temperature_2m")} °C
Feels-like temperature: {current.get("apparent_temperature")} °C
Relative humidity: {current.get("relative_humidity_2m")} %
Weather description: {current.get("weather_description", "Not available")}

AVAILABLE INTERVENTIONS:
{available_interventions}

TASK:
1. Evaluate the relative usefulness of each supplied intervention
   for heat protection, considering the supplied location and weather.
2. Return every supplied intervention exactly once.
3. Copy each intervention name exactly as provided.
4. Assign a relative planning priority from 1 to 100.
5. Explain the reasoning clearly and briefly.
6. Do not change or invent intervention costs.
7. Do not claim that a location has missing shade, water facilities,
   vulnerable residents, or particular infrastructure unless that
   information was explicitly supplied.
8. Treat site conditions, population vulnerability, and local
   infrastructure availability as unknown when no evidence is supplied.
9. Do not claim to have measured actual health outcomes.
10. Scores are planning priorities, not measured effectiveness.

Provide a concise summary of how the supplied weather and location
context affected your assessment.
"""

   
    response = None

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": LocationAnalysis,
                },
            )
            break

        except errors.ServerError as exc:
            if attempt == 2:
                raise RuntimeError(
                    "Gemini is temporarily unavailable. "
                    "Please try again shortly."
                ) from exc

            time.sleep(2 ** attempt)


    if not response.text:
        raise RuntimeError("Gemini returned an empty analysis.")

    analysis = LocationAnalysis.model_validate_json(response.text)

    expected_names = {
        item["intervention_type"] for item in candidates
    }
    returned_names = [
        item.intervention_type for item in analysis.recommendations
    ]

    if (
        set(returned_names) != expected_names
        or len(returned_names) != len(expected_names)
    ):
        raise RuntimeError(
            "Gemini returned missing, duplicate, or unknown interventions."
        )

    return analysis.model_dump()
