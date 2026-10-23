"""
app/routes/chat.py

FastAPI router for POST /api/chat.

Accepts a JSON body with a heat-safety question and a language preference
(english / hindi / telugu). Returns a cautious, grounded answer via the
Gemini service plus an always-present safety disclaimer.

Error mapping:
  RequestValidationError (Pydantic)   → 422  (handled automatically by FastAPI)
  ValueError  (config / bad language) → 422
  RuntimeError (Gemini API failure)   → 503
  Unexpected exception                → 500  (no internals exposed)
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.exceptions import RequestValidationError

from app.config import Settings, get_settings
from app.schemas.ai_schemas import ChatRequest, ChatResponse
from app.services.gemini_service import chat_heat_safety

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Heat-Safety Chat"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Ask the multilingual heat-safety assistant",
    description=(
        "Submit a heat-safety question in English, Hindi, or Telugu. "
        "Returns a concise, grounded answer based on reviewed public-health guidance "
        "(WHO, ICMR, NDMA). Responses are for general awareness only and are not "
        "medical advice. For emergencies, seek urgent medical assistance immediately."
    ),
)
async def chat_endpoint(
    request: ChatRequest,
    settings: Settings = Depends(get_settings),
) -> ChatResponse:
    # Pydantic already validated question length (min 1, max 1000) and
    # language enum membership before this function is called.

    language = request.language.value  # e.g. "english", "hindi", "telugu"

    logger.info("Chat request received (language=%s)", language)

    try:
        answer = chat_heat_safety(
            question=request.question,
            language=language,
            settings=settings,
        )
    except ValueError as exc:
        # Covers missing config and any unexpected language value
        logger.warning("Chat value error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        )
    except RuntimeError as exc:
        # Gemini API failure
        logger.error("Chat runtime error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error during chat")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again later.",
        ) from exc

    return ChatResponse(
        success=True,
        answer=answer,
        language_code=language,
    )
