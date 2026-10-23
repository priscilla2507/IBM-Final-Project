
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.database import get_db
from app.models.assessment import Assessment
from app.models.location import Location
from app.services.weather_service import find_location, get_weather

router = APIRouter(
    prefix="/api/assessments",
    tags=["Assessments"]
)


class AssessmentCreate(BaseModel):
    location_name: str = Field(min_length=2, max_length=150)
    location_type: str = Field(default="City", max_length=80)


@router.post("/")
def create_assessment(
    data: AssessmentCreate,
    db: Session = Depends(get_db)
):
    # 1. Find coordinates using the location name.
    try:
        geo = find_location(data.location_name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    latitude = geo["latitude"]
    longitude = geo["longitude"]
    name = geo["name"]

    # Include region and country to distinguish similarly named places.
    if geo.get("admin1"):
        name += f", {geo['admin1']}"
    if geo.get("country"):
        name += f", {geo['country']}"

    # 2. Fetch current weather.
    try:
        weather_data = get_weather(latitude, longitude)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    current = weather_data.get("current", {})
    temperature = current.get("temperature_2m")
    humidity = current.get("relative_humidity_2m")
    apparent_temperature = current.get("apparent_temperature")

    if temperature is None or humidity is None:
        raise HTTPException(
            status_code=502,
            detail="Current temperature or humidity is unavailable."
        )

    # 3. Calculate an initial, illustrative heat-risk score.
    # This is a prototype formula, not a validated health-risk model.
    heat_score = max(
        0,
        min(
            100,
            round(
                max(0, float(apparent_temperature or temperature) - 25) * 4
                + float(humidity) * 0.2
            )
        )
    )

    if heat_score >= 70:
        risk_level = "High"
    elif heat_score >= 40:
        risk_level = "Moderate"
    else:
        risk_level = "Low"

    # 4. Reuse an existing location record where possible.
    location = (
        db.query(Location)
        .filter(
            Location.latitude == latitude,
            Location.longitude == longitude
        )
        .first()
    )

    if not location:
        location = Location(
            name=name,
            latitude=latitude,
            longitude=longitude,
            location_type=data.location_type
        )
        db.add(location)
        db.flush()

    # 5. Save the assessment.
    assessment = Assessment(
        location_id=location.id,
        temperature=temperature,
        humidity=humidity,
        risk_score=heat_score,
        risk_level=risk_level
    )

    try:
        db.add(assessment)
        db.commit()
        db.refresh(assessment)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to save assessment."
        )

    return {
        "message": "Weather-based assessment created successfully",
        "location": {
            "id": location.id,
            "name": location.name,
            "latitude": float(location.latitude),
            "longitude": float(location.longitude)
        },
        "weather": {
            "temperature": float(temperature),
            "humidity": float(humidity),
            "apparent_temperature": apparent_temperature,
            "precipitation": current.get("precipitation"),
            "wind_speed": current.get("wind_speed_10m"),
            "time": current.get("time")
        },
        "assessment": {
            "id": assessment.id,
            "risk_score": assessment.risk_score,
            "risk_level": assessment.risk_level,
            "assessed_at": assessment.assessed_at
        }
    }


@router.get("/")
def get_assessments(
    location_id: int | None = None,
    db: Session = Depends(get_db)
):
    query = db.query(Assessment)

    if location_id is not None:
        query = query.filter(
            Assessment.location_id == location_id
        )

    assessments = query.order_by(
        Assessment.assessed_at.desc()
    ).all()

    return [
        {
            "id": item.id,
            "location_id": item.location_id,
            "temperature": float(item.temperature),
            "humidity": float(item.humidity),
            "risk_score": item.risk_score,
            "risk_level": item.risk_level,
            "assessed_at": item.assessed_at
        }
        for item in assessments
    ]
