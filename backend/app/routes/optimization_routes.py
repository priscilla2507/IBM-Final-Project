
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.optimization import (
    OptimizationRequest,
    OptimizationResponse,
)
from app.services.optimization_db_service import run_and_save_optimization

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Optimization"])


@router.post("/optimize", response_model=OptimizationResponse)
def optimize(
    request: OptimizationRequest,
    db: Session = Depends(get_db),
):
    try:
        return run_and_save_optimization(
            db,
            request.budget,
            request.location_name,
        )

    except ValueError as exc:
        logger.exception("Invalid optimization request")
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except Exception:
        logger.exception("Optimization failed with traceback")
        raise HTTPException(
            status_code=500,
            detail="Optimization failed. Check the backend terminal.",
        )
