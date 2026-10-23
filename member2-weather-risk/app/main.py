"""
member2-weather-risk/app/main.py

Isolated FastAPI application entry point for Member 2 — Weather & Risk
Assessment module.

PURPOSE
-------
This is a **temporary development entry point** used while Member 2 works in
isolation. It intentionally does NOT share code with, modify, or depend on:

  - frontend/                  (Member 1 — React UI)
  - ai-intelligence-backend/   (Member 3 — Gemini AI)

INTEGRATION PLAN
----------------
Once the weather-risk routers are stable and the shared database schema has
been agreed with Member 4, the routers defined under app/routes/ will be
imported into the team's shared entry point:

    ai-intelligence-backend/main.py

at the marked "Integration point for other team members" section, e.g.:

    from app.routes.weather     import router as weather_router
    from app.routes.assessments import router as assessments_router

    app.include_router(weather_router)
    app.include_router(assessments_router)

All routers use the /api prefix (per team convention).

RUN LOCALLY (isolated dev)
--------------------------
    cd member2-weather-risk
    uvicorn app.main:app --reload --port 8001

Interactive API docs: http://127.0.0.1:8001/docs
"""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.routes.weather import router as weather_router
from app.routes.assessments import router as assessments_router

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="ChhayaRakshak AI — Weather & Risk Assessment (dev)",
    version="0.2.0-dev",
    description=(
        "Member 2 isolated development module. "
        "Provides weather data ingestion and heat-risk assessment endpoints. "
        "This service will be merged into the shared FastAPI application "
        "before final integration. "
        "**Do not use this entry point in production; use the shared backend.**"
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ---------------------------------------------------------------------------
# CORS — allow the Vite React dev server during isolated development
# The Vite default dev port is 5173; also allow 3000 as a fallback.
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept", "Authorization"],
    allow_credentials=False,
)

# ---------------------------------------------------------------------------
# Global exception handler — predictable JSON errors
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again later."},
    )

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(weather_router)
app.include_router(assessments_router)

# ---------------------------------------------------------------------------
# Health check — /api/health (matches frontend api.js: GET /api/health)
# ---------------------------------------------------------------------------
@app.get("/api/health", tags=["Health"], summary="Service health check")
async def health_check() -> dict:
    """Returns 200 OK when the dev server is running."""
    return {
        "status": "ok",
        "module": "weather-risk",
        "version": "0.2.0-dev",
        "note": (
            "Isolated development module for Member 2. "
            "Will be integrated into ai-intelligence-backend before production."
        ),
    }


logger.info("Member 2 weather-risk dev server started (isolated mode).")
