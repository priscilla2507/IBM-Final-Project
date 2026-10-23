"""
member2-weather-risk/app/schemas/risk_schemas.py

Pydantic request and response models for the heat-risk assessment endpoint.

These schemas define the contract for:
  POST /api/assessments

Frontend compatibility
----------------------
The response schema matches the fields consumed by the existing React frontend
(ChhayaRakshak-AI-main/frontend/src/pages/HeatRiskAnalysis.jsx) and the demo
data structure in demoService.js, including:

  assessment_id, location, risk_score, risk_category,
  temperature, humidity, model_version, model_valid, model_limitations,
  factors, recommendations

Integration note
----------------
This schema is intentionally independent of any SQLAlchemy model.
When Member 4's shared database schema is finalised, a separate persistence
layer (app/db/persistence.py) will map between these Pydantic schemas and the
ORM models. The scoring logic in app/services/risk_service.py remains
testable without any database connection.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Assessment request
# ---------------------------------------------------------------------------

class AssessmentRequest(BaseModel):
    """
    Heat-risk assessment request.

    Accepts field observation data from the frontend survey form.
    All location and microclimate fields are optional except coordinates.
    """

    latitude: float = Field(
        ..., description="Latitude of the survey point (°N)", ge=-90, le=90
    )
    longitude: float = Field(
        ..., description="Longitude of the survey point (°E)", ge=-180, le=180
    )
    location_name: Optional[str] = Field(
        None,
        max_length=256,
        description="Human-readable name for the location (e.g. 'Koti Bus Stop')",
    )

    # --- Area / land-use context ---
    area_type: Optional[str] = Field(
        None,
        max_length=128,
        description="Area type / land use (e.g. 'Transit Hub', 'Open-Air Market')",
    )
    surface_type: Optional[str] = Field(
        None,
        max_length=128,
        description="Primary ground surface material (e.g. 'Dark Asphalt / Tar')",
    )

    # --- Microclimate observations ---
    shade_availability: Optional[str] = Field(
        None,
        max_length=128,
        description="Visible shade availability category",
    )
    canopy_density: Optional[int] = Field(
        None,
        ge=0,
        le=100,
        description="Observed tree canopy density as a percentage (0–100)",
    )

    # --- Exposure factors ---
    footfall: Optional[str] = Field(
        None,
        max_length=128,
        description="Pedestrian exposure / footfall category",
    )
    demographics: Optional[list[str]] = Field(
        default_factory=list,
        description="List of observed vulnerable demographic groups",
    )

    # --- Mitigation factors ---
    hydration_present: Optional[bool] = Field(
        False,
        description="Whether a free hydration facility is present within 50 m",
    )

    # --- Free text ---
    notes: Optional[str] = Field(
        None,
        max_length=2048,
        description="Field surveyor notes",
    )

    @field_validator("demographics", mode="before")
    @classmethod
    def _coerce_demographics(cls, v: object) -> list[str]:
        if v is None:
            return []
        return v


# ---------------------------------------------------------------------------
# Assessment response sub-models
# ---------------------------------------------------------------------------

RiskCategory = Literal["low", "moderate", "high", "very_high"]
ImpactLevel = Literal["high", "moderate", "positive"]
RecommendationPriority = Literal["Immediate", "Medium Term", "Long Term", "Low Priority"]


class RiskFactor(BaseModel):
    """A contributing factor returned in the assessment result."""

    label: str = Field(..., description="Short label for the factor")
    detail: Optional[str] = Field(None, description="Detailed explanation")
    impact: ImpactLevel = Field(..., description="Impact level of this factor")


class Recommendation(BaseModel):
    """A single mitigation recommendation."""

    priority: RecommendationPriority = Field(
        ..., description="Implementation priority tier"
    )
    label: str = Field(..., description="Description of the recommended action")
    cost: Optional[int] = Field(
        None,
        description="Estimated implementation cost in INR (indicative only)",
    )
    timeframe: Optional[str] = Field(
        None, description="Indicative implementation timeframe"
    )


# ---------------------------------------------------------------------------
# Assessment response
# ---------------------------------------------------------------------------

class AssessmentResponse(BaseModel):
    """
    Heat-risk assessment result.

    SCORING BOUNDARIES
    ------------------
    Score range   Category    Meaning
    0  – 24       low         Low heat stress; standard precautions adequate
    25 – 49       moderate    Moderate risk; advisory-level interventions recommended
    50 – 74       high        High risk; targeted interventions required
    75 – 100      very_high   Critical risk; immediate action required

    LIMITATIONS NOTICE
    ------------------
    The risk score is an indicative, deterministic decision-support measure
    derived from field observations and real-time weather data. It is NOT a
    medically validated prediction and must not be used as the sole basis for
    clinical or emergency-response decisions.

    The ``model_limitations`` field always contains a plain-language summary
    of current scoring limitations.
    """

    assessment_id: str = Field(
        default_factory=lambda: f"ASSESS-HYD-{uuid.uuid4().hex[:8].upper()}",
        description="Unique assessment identifier",
    )
    location: str = Field(..., description="Location name used in the assessment")
    latitude: float = Field(..., description="Assessment latitude")
    longitude: float = Field(..., description="Assessment longitude")

    # --- Risk output ---
    risk_score: int = Field(
        ..., ge=0, le=100, description="Composite heat-risk score (0–100)"
    )
    risk_category: RiskCategory = Field(
        ..., description="Risk category derived from the score"
    )

    # --- Weather snapshot used in scoring ---
    temperature: Optional[float] = Field(
        None, description="Air temperature at time of assessment (°C)"
    )
    apparent_temperature: Optional[float] = Field(
        None, description="Apparent / feels-like temperature (°C)"
    )
    humidity: Optional[int] = Field(
        None, description="Relative humidity at time of assessment (%)"
    )

    # --- Model metadata ---
    model_version: str = Field(
        default="v0.2-dev (Deterministic Preliminary Scorer)",
        description="Scoring model version identifier",
    )
    model_valid: str = Field(
        default="Indicative decision-support measure; not medically validated",
        description="Model validity statement",
    )
    model_limitations: str = Field(
        ..., description="Plain-language description of current scoring limitations"
    )

    # --- Explainability ---
    factors: list[RiskFactor] = Field(
        default_factory=list,
        description="Primary contributing vulnerability factors",
    )
    recommendations: list[Recommendation] = Field(
        default_factory=list,
        description="Heat-safety recommendations and mitigation actions",
    )

    # --- Meta ---
    assessment_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the assessment was computed",
    )
    weather_available: bool = Field(
        True,
        description="Whether live weather observations were available for scoring",
    )
    data_quality_notes: list[str] = Field(
        default_factory=list,
        description="Data-quality caveats that apply to this assessment",
    )
