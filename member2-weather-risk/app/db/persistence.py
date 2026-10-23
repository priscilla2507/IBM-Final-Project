"""
member2-weather-risk/app/db/persistence.py

Assessment persistence — integration boundary with Member 4's shared database.

PURPOSE
-------
This module is a STUB.  It defines the interface that will be used to persist
heat-risk assessments once the shared database schema and SQLAlchemy session
have been finalised with Member 4.

INTEGRATION PLAN
----------------
When Member 4's shared models are available, replace ``save_assessment_stub``
with a real implementation that:

    1. Receives a SQLAlchemy session injected by FastAPI's dependency system:

           from app.db.session import get_session   # Member 4's module

    2. Maps the AssessmentResponse Pydantic object to Member 4's ORM model:

           from app.models.assessment import Assessment   # Member 4's model

    3. Commits the record:

           db_record = Assessment(
               assessment_id    = result.assessment_id,
               location_name    = result.location,
               latitude         = result.latitude,
               longitude        = result.longitude,
               risk_score       = result.risk_score,
               risk_category    = result.risk_category,
               temperature      = result.temperature,
               humidity         = result.humidity,
               weather_available= result.weather_available,
               model_version    = result.model_version,
               created_at       = result.assessment_timestamp,
           )
           session.add(db_record)
           await session.commit()

DATABASE_URL configuration
---------------------------
The database URL is read from the ``DATABASE_URL`` environment variable.
It is never hardcoded.  Example value (MySQL, Member 4's server):

    DATABASE_URL=mysql+aiomysql://user:password@localhost:3306/chhayarakshak

This value must be set in .env and is NOT included in .env.example as a
real credential.  See .env.example for the placeholder.

CURRENT BEHAVIOUR
-----------------
``save_assessment_stub`` logs the assessment_id and returns without writing
to any database.  This keeps the weather and scoring code testable without
a MySQL connection.
"""

from __future__ import annotations

import logging

from app.schemas.risk_schemas import AssessmentResponse

logger = logging.getLogger(__name__)


def save_assessment_stub(result: AssessmentResponse) -> None:
    """
    Persistence stub — logs the assessment but does not write to any database.

    Replace this function with a real async implementation once Member 4's
    shared session and ORM models are available.  See module docstring for
    the expected implementation pattern.

    Parameters
    ----------
    result :
        The completed assessment to persist.
    """
    logger.info(
        "[PERSISTENCE STUB] Assessment %s (score=%d, category=%s) — "
        "not persisted; awaiting Member 4 database integration.",
        result.assessment_id,
        result.risk_score,
        result.risk_category,
    )
