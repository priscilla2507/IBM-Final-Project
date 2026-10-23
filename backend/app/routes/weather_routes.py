
from fastapi import APIRouter, HTTPException, Query

from app.services.weather_service import get_weather

router = APIRouter(prefix="/api/weather", tags=["Weather"])


@router.get("/")
def weather(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
):
    try:
        return get_weather(latitude, longitude)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc
