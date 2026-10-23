"""
member2-weather-risk/app/routes/assessments.py

Assessments router — POST /api/assessments

Matches the frontend API contract:
    submitAssessment(payload) → apiClient.post('/api/assessments', payload)
    (ChhayaRakshak-AI-main/frontend/src/services/api.js)

Request body
------------
See AssessmentRequest in app/schemas/risk_schemas.py.
Required: latitude, longitude.
Optional: location_name, area_type, surface_type, shade_availability,
          canopy_density, footfall, demographics, hydration_present, notes.

Response
--------
200  AssessmentResponse  — Successful assessment with score, factors, recommendations.
422  Validation error    — Invalid request body (FastAPI default).
503  Error detail        — Assessment cannot proceed (e.g. fatal internal error).

Weather integration
-------------------
The route attempts to fetch live weather for the supplied coordinates.
If weather is unavailable, a partial assessment is returned (not an error)
with a prominent data-quality note. No fabricated weather values are used.

Persistence
-----------
Assessment persistence is intentionally stubbed.  See app/db/persistence.py
for the integration boundary with Member 4's shared database session.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.db.persistence import save_assessment_stub
from app.schemas.risk_schemas import AssessmentRequest, AssessmentResponse
from app.services.risk_service import compute_assessment
from app.services.weather_service import WeatherServiceError, get_current_weather

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Assessments"])


@router.post(
    "/assessments",
    response_model=AssessmentResponse,
    responses={
        503: {"description": "Assessment could not be completed"},
    },
    summary="Submit a heat-risk assessment",
    description=(
        "Accepts field observation data, fetches live weather from Open-Meteo, "
        "and returns a deterministic heat-risk score with explainable factors and "
        "mitigation recommendations. "
        "If weather is unavailable a partial assessment is still returned with a "
        "clear data-quality note. "
        "No weather values are fabricated."
    ),
)
async def post_assessment(body: AssessmentRequest) -> AssessmentResponse | JSONResponse:
    """
    Compute and return a heat-risk assessment.

    Steps
    -----
    1. Attempt to fetch live weather for the supplied coordinates.
    2. Pass the request + optional weather observation to the scoring engine.
    3. (Stub) Persist via the Member-4 integration boundary.
    4. Return the assessment response.
    """
    # Step 1 — weather retrieval (best-effort; failure is non-fatal)
    weather = None
    try:
        weather = await get_current_weather(lat=body.latitude, lon=body.longitude)
    except WeatherServiceError as exc:
        logger.warning(
            "Weather unavailable for assessment (lat=%.4f lon=%.4f): %s",
            body.latitude,
            body.longitude,
            exc.message,
        )
        # Continue — compute_assessment handles missing weather gracefully

    # Step 2 — scoring
    try:
        result = compute_assessment(body, weather)
    except Exception as exc:
        logger.error("Assessment scoring failed: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=503,
            content={"detail": "Assessment computation failed. Please try again."},
        )

    # Step 3 — persistence stub
    save_assessment_stub(result)

    return result
