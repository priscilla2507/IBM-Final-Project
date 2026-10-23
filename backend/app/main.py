from fastapi.middleware.cors import CORSMiddleware
from app.routes.optimization_routes import router as optimization_router
from app.routes.personal_assessment_routes import router as personal_assessment_router
from fastapi import FastAPI, Form, Request, UploadFile
from fastapi.responses import Response
from app.routes.weather_routes import router as weather_router
from app.routes.assessment_routes import router as assessment_router
from app.database import Base, engine
from app import models
from app.routes.location_routes import router as location_router
import httpx
import logging
import json

logger = logging.getLogger(__name__)

# Base URL of the AI backend (Member 3) — runs on port 8002.
_AI_BACKEND_URL = "http://127.0.0.1:8002"

app = FastAPI(
    title="ChhayaRakshak AI",
    description="Urban heat protection and cooling intervention optimizer",
    version="1.0.0",
)
app.include_router(weather_router)
app.include_router(assessment_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def create_tables():
    # Attempt to create DB tables at startup.
    # If MySQL is unreachable (e.g. missing backend/.env credentials),
    # log a warning and continue — health and proxy routes still work.
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created / verified.")
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Database unavailable at startup — DB-backed routes will fail "
            "until backend/.env is configured with valid credentials. "
            "Error: %s",
            exc,
        )


app.include_router(location_router)
app.include_router(optimization_router)
app.include_router(personal_assessment_router)


@app.get("/")
def root():
    return {"message": "ChhayaRakshak AI backend is running"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


# ── AI proxy routes ───────────────────────────────────────────────────────────
# The frontend points entirely at port 8000 (VITE_API_URL=http://localhost:8000).
# These two routes accept AI requests on port 8000 and forward them verbatim to
# the AI backend on port 8001, returning the AI backend's response unchanged.
# Only backend/app/main.py is modified; no frontend or AI backend files change.

@app.post("/api/chat", tags=["AI Proxy"])
async def proxy_chat(request: Request) -> Response:
    """Forward POST /api/chat to the AI backend on port 8001."""
    body = await request.body()
    content_type = request.headers.get("content-type", "application/json")
    async with httpx.AsyncClient(timeout=60.0) as client:
        ai_resp = await client.post(
            f"{_AI_BACKEND_URL}/api/chat",
            content=body,
            headers={"content-type": content_type},
        )
    return Response(
        content=ai_resp.content,
        status_code=ai_resp.status_code,
        media_type=ai_resp.headers.get("content-type", "application/json"),
    )


@app.post("/api/analyze-image", tags=["AI Proxy"])
async def proxy_analyze_image(file: UploadFile) -> Response:
    """Forward POST /api/analyze-image (multipart) to the AI backend on port 8001."""
    image_bytes = await file.read()
    async with httpx.AsyncClient(timeout=120.0) as client:
        ai_resp = await client.post(
            f"{_AI_BACKEND_URL}/api/analyze-image",
            files={"file": (file.filename, image_bytes, file.content_type)},
        )
    return Response(
        content=ai_resp.content,
        status_code=ai_resp.status_code,
        media_type=ai_resp.headers.get("content-type", "application/json"),
    )


# ── Analyze-and-Optimize endpoint ────────────────────────────────────────────
# Receives an image + budget + location, forwards the image to the AI backend
# on port 8002 for analysis, then runs the existing OR-Tools optimizer with
# image-derived context to produce a prioritised intervention plan.

@app.post("/api/analyze-and-optimize", tags=["Area Analysis"])
async def analyze_and_optimize(
    file: UploadFile,
    budget: int = Form(...),
    location_name: str = Form(...),
) -> Response:
    """
    Analyse an outdoor image for heat-related vulnerabilities, then run the
    existing OR-Tools budget optimizer using the image findings to inform
    intervention priorities.

    Steps
    -----
    1. Forward the image to the AI backend (port 8002) for analysis.
    2. Parse the structured findings.
    3. Build intervention candidates, boosting benefit scores for
       vulnerabilities identified in the image.
    4. Run the existing OR-Tools optimizer.
    5. Return combined findings + optimized plan as JSON.
    """
    from app.services.optimization_db_service import build_intervention_candidates
    from app.services.optimizer_service import optimize_interventions
    from app.services.weather_service import find_location, get_weather
    from sqlalchemy.orm import Session
    from app.database import SessionLocal
    from app.models.optimization_run import OptimizationRun
    from app.models.optimization_recommendation import OptimizationRecommendation

    # ── 1. AI image analysis ─────────────────────────────────────────────── #
    image_bytes = await file.read()
    ai_analysis_data = None
    ai_error = None

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            ai_resp = await client.post(
                f"{_AI_BACKEND_URL}/api/analyze-image",
                files={"file": (file.filename, image_bytes, file.content_type)},
            )
        if ai_resp.status_code == 200:
            ai_analysis_data = ai_resp.json()
        else:
            ai_error = f"Image analysis returned status {ai_resp.status_code}"
    except Exception as exc:
        ai_error = f"Image analysis service unavailable: {exc}"
        logger.warning("analyze-and-optimize: image analysis failed: %s", exc)

    # ── 2. Resolve location and weather ─────────────────────────────────── #
    try:
        geo = find_location(location_name.strip())
    except (ValueError, RuntimeError) as exc:
        return Response(
            content=json.dumps({"detail": str(exc)}),
            status_code=422,
            media_type="application/json",
        )

    lat = geo["latitude"]
    lon = geo["longitude"]
    resolved_name = geo["name"]
    if geo.get("admin1"):
        resolved_name += f", {geo['admin1']}"
    if geo.get("country"):
        resolved_name += f", {geo['country']}"

    weather_data = {}
    current = {}
    temperature = 35.0
    humidity = 50.0
    apparent_temperature = 35.0
    weather_available = False

    try:
        weather_data = get_weather(lat, lon)
        current = weather_data.get("current", {})
        if current.get("temperature_2m") is not None:
            temperature = float(current["temperature_2m"])
            humidity = float(current.get("relative_humidity_2m", 50))
            apparent_temperature = float(current.get("apparent_temperature", temperature))
            weather_available = True
    except Exception as exc:
        logger.warning("analyze-and-optimize: weather unavailable: %s", exc)

    # ── 3. Build candidates with image-informed benefit boosts ──────────── #
    candidates, heat_score, risk_level = build_intervention_candidates(
        resolved_name, temperature, humidity, apparent_temperature
    )

    # Parse image findings to adjust candidate priorities
    image_findings = None
    if ai_analysis_data and ai_analysis_data.get("success"):
        image_findings = ai_analysis_data.get("data", {})

    if image_findings:
        # Boost "Install Shade Structures" and "Plant Shade Trees" if sun exposure is high
        sun_exposed = image_findings.get("sun_exposed_areas", {}).get("visible", False)
        no_shade = not image_findings.get("shaded_areas", {}).get("visible", True)
        no_vegetation = not image_findings.get("vegetation", {}).get("visible", True)
        no_water = not image_findings.get("drinking_water", {}).get("visible", True)
        no_shelter = not image_findings.get("shelters", {}).get("visible", True)

        for c in candidates:
            itype = c["intervention_type"]
            if (sun_exposed or no_shade) and itype in ("Install Shade Structures",):
                c["benefit_score"] = min(100, c["benefit_score"] + 15)
                c["explanation"] += " Image shows sun-exposed areas with limited shade — shade structures are a priority."
            if (sun_exposed or no_vegetation) and itype == "Plant Shade Trees":
                c["benefit_score"] = min(100, c["benefit_score"] + 12)
                c["explanation"] += " Image shows limited vegetation — tree planting is recommended."
            if no_water and itype == "Public Drinking Water Station":
                c["benefit_score"] = min(100, c["benefit_score"] + 15)
                c["explanation"] += " No drinking water facility visible in the image — installation is a priority."
            if no_shelter and itype == "Cooling Shelter":
                c["benefit_score"] = min(100, c["benefit_score"] + 10)
                c["explanation"] += " No covered shelter visible in the image."

    # ── 4. Run OR-Tools optimizer ────────────────────────────────────────── #
    if budget <= 0:
        return Response(
            content=json.dumps({"detail": "Budget must be greater than zero."}),
            status_code=422,
            media_type="application/json",
        )

    opt_result = optimize_interventions(candidates, budget)

    # ── 5. Persist and return ────────────────────────────────────────────── #
    db: Session = SessionLocal()
    optimization_run_id = None
    try:
        run = OptimizationRun(
            budget=budget,
            total_cost=opt_result["total_cost"],
            total_benefit_score=opt_result["total_benefit_score"],
            recommendations_json={
                "source": "analyze_and_optimize",
                "location_name": resolved_name,
                "image_analysis_available": image_findings is not None,
                "image_error": ai_error,
                "weather_available": weather_available,
                "heat_score": heat_score,
                "risk_level": risk_level,
                "recommendations": opt_result["recommendations"],
                "costs_are_illustrative": True,
            },
        )
        db.add(run)
        db.flush()
        optimization_run_id = run.id
        for rec in opt_result["recommendations"]:
            db.add(OptimizationRecommendation(
                optimization_run_id=run.id,
                intervention_id=None,
                location_name=resolved_name,
                intervention_type=rec["intervention_type"],
                estimated_cost=rec["estimated_cost"],
                benefit_score=rec["benefit_score"],
                explanation=rec["explanation"],
            ))
        db.commit()
    except Exception as exc:
        logger.warning("analyze-and-optimize: DB save failed (non-fatal): %s", exc)
        try:
            db.rollback()
        except Exception:
            pass
    finally:
        db.close()

    payload = {
        "location_resolved": resolved_name,
        "budget": budget,
        "total_cost": opt_result["total_cost"],
        "total_benefit_score": opt_result["total_benefit_score"],
        "remaining_budget": budget - opt_result["total_cost"],
        "recommendations": opt_result["recommendations"],
        "image_analysis": image_findings,
        "image_analysis_available": image_findings is not None,
        "image_error": ai_error,
        "weather_available": weather_available,
        "weather": {
            "temperature": temperature if weather_available else None,
            "humidity": humidity if weather_available else None,
            "apparent_temperature": apparent_temperature if weather_available else None,
            "time": current.get("time"),
        },
        "heat_score": heat_score,
        "risk_level": risk_level,
        "costs_are_illustrative": True,
        "optimization_run_id": optimization_run_id,
    }

    return Response(
        content=json.dumps(payload),
        status_code=200,
        media_type="application/json",
    )
