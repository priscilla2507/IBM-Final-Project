
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.location import Location

router = APIRouter(prefix="/api/locations", tags=["Locations"])


@router.get("/")
def get_locations(db: Session = Depends(get_db)):
    locations = db.query(Location).order_by(Location.id).all()

    return [
        {
            "id": location.id,
            "name": location.name,
            "latitude": float(location.latitude),
            "longitude": float(location.longitude),
            "location_type": location.location_type,
        }
        for location in locations
    ]
