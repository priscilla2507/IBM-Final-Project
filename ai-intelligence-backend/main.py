"""
main.py

Shared FastAPI application entry point for ChhayaRakshak AI.

This module assembles the application from the individual routers built by
the AI backend team member. Other team members' routers can be imported and
registered here once they are ready — see the integration comment below.

Run locally:
    uvicorn main:app --reload

Interactive API docs (Swagger UI):
    http://127.0.0.1:8000/docs
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routes.chat import router as chat_router
from app.routes.image_analysis import router as image_analysis_router

# ── Logging ───────────────────────────────────────────────────────────────── #
# Basic config here; production deployments should configure logging externally.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)

# ── Settings ──────────────────────────────────────────────────────────────── #
settings = get_settings()

# ── Application ───────────────────────────────────────────────────────────── #
app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    description=settings.app_description,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ── CORS ──────────────────────────────────────────────────────────────────── #
# Permits the React dev server at http://localhost:5173 to call this API.
# Extend allow_origins when deploying or when other dev origins are needed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Accept"],
    allow_credentials=False,
)

# ── Routers ───────────────────────────────────────────────────────────────── #
# AI backend routers (Member 3)
app.include_router(image_analysis_router)
app.include_router(chat_router)

# ── Integration point for other team members ──────────────────────────────── #
# When other modules are ready, import and register their routers here, e.g.:
#
#   from app.routes.weather import router as weather_router
#   from app.routes.map import router as map_router
#   from app.routes.optimization import router as optimization_router
#
#   app.include_router(weather_router)
#   app.include_router(map_router)
#   app.include_router(optimization_router)


# ── Health check ──────────────────────────────────────────────────────────── #
@app.get("/health", tags=["Health"], summary="Service health check")
async def health_check() -> dict:
    """
    Returns 200 OK when the application is running.
    Does not check Gemini connectivity — only confirms the process is alive.
    """
    return {"status": "ok", "version": settings.app_version}


logger.info(
    "ChhayaRakshak AI started — title=%s version=%s",
    settings.app_title,
    settings.app_version,
)
