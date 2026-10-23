"""
app/schemas/ai_schemas.py

Pydantic request and response models for the AI endpoints.

Design rules applied here:
- Image analysis responses distinguish "not visible" from "does not exist".
- No field claims to measure temperature or prove operational status.
- human_verification_required is always True — AI findings are preliminary.
- Chat responses carry a language_code echo so callers can verify routing.
"""

from typing import Optional

from pydantic import BaseModel, Field
from enum import Enum


# ── Shared / enums ────────────────────────────────────────────────────────── #

class SupportedLanguage(str, Enum):
    english = "english"
    hindi   = "hindi"
    telugu  = "telugu"


# ── Image analysis ────────────────────────────────────────────────────────── #

class VegetationObservation(BaseModel):
    visible: bool = Field(description="True if trees or vegetation are visible in the image.")
    description: Optional[str] = Field(
        default=None,
        description="Brief description of visible vegetation, or null if not visible.",
    )


class ShadedAreaObservation(BaseModel):
    visible: bool
    description: Optional[str] = Field(
        default=None,
        description="Brief description of visibly shaded areas, or null if not visible.",
    )


class SunExposedAreaObservation(BaseModel):
    visible: bool
    description: Optional[str] = Field(
        default=None,
        description="Brief description of visibly sun-exposed areas, or null if not visible.",
    )


class ShelterObservation(BaseModel):
    visible: bool
    description: Optional[str] = Field(
        default=None,
        description=(
            "Brief description of visible shelters or covered bus-stop structures. "
            "Presence in the image does not confirm the facility is operational."
        ),
    )


class DrinkingWaterObservation(BaseModel):
    visible: bool
    description: Optional[str] = Field(
        default=None,
        description=(
            "Brief description of visible drinking-water facilities, or null if not visible. "
            "Not visible does not mean the facility does not exist."
        ),
    )


class ImageAnalysisResult(BaseModel):
    vegetation: VegetationObservation
    shaded_areas: ShadedAreaObservation
    sun_exposed_areas: SunExposedAreaObservation
    shelters: ShelterObservation
    drinking_water: DrinkingWaterObservation
    infrastructure_gaps: list[str] = Field(
        description=(
            "List of potential infrastructure gaps observed in the image. "
            "These are visual observations only, not verified assessments."
        ),
    )
    explanation: str = Field(
        description="Short plain-language summary of what was observed in the image.",
    )
    limitations: str = Field(
        description=(
            "Explicit limitations of this analysis: what could not be determined "
            "from the image alone."
        ),
    )
    human_verification_required: bool = Field(
        default=True,
        description=(
            "Always True. AI findings are preliminary observations. "
            "A qualified person must verify before any intervention decision."
        ),
    )


class ImageAnalysisResponse(BaseModel):
    success: bool
    data: Optional[ImageAnalysisResult] = None
    error: Optional[str] = Field(
        default=None,
        description="Present only when success is False.",
    )


# ── Chat assistant ────────────────────────────────────────────────────────── #

class ChatRequest(BaseModel):
    question: str = Field(
        min_length=1,
        max_length=1000,
        description="The heat-safety question to answer.",
    )
    language: SupportedLanguage = Field(
        default=SupportedLanguage.english,
        description="Preferred response language.",
    )


class ChatResponse(BaseModel):
    success: bool
    answer: Optional[str] = Field(
        default=None,
        description="The assistant's response in the requested language.",
    )
    language_code: Optional[str] = Field(
        default=None,
        description="Echo of the language used for the response.",
    )
    disclaimer: str = Field(
        default=(
            "This information is for general awareness only. "
            "It is not medical advice. For emergencies, seek urgent medical assistance immediately."
        ),
        description="Always-present safety disclaimer.",
    )
    error: Optional[str] = Field(
        default=None,
        description="Present only when success is False.",
    )
