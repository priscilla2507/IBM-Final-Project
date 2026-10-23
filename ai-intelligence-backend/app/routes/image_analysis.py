"""
app/routes/image_analysis.py

FastAPI router for POST /api/analyze-image.

Validation order (fail-fast, cheapest checks first):
  1. File present in request
  2. File extension (.jpg / .jpeg / .png)
  3. File size (≤ MAX_IMAGE_SIZE_MB)
  4. Magic-byte MIME type (python-magic — rejects renamed files)
  5. Gemini service call

Error mapping:
  ValueError  (validation / config / malformed response) → 503
  RuntimeError (Gemini API failure)                      → 503
  Unexpected exception                                   → 500 (no internals exposed)
"""

import logging

import magic
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from app.config import Settings, get_settings
from app.schemas.ai_schemas import ImageAnalysisResponse
from app.services.gemini_service import analyze_image

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Image Analysis"])

# Allowed file extensions (lower-cased)
_ALLOWED_EXTENSIONS: set[str] = {".jpg", ".jpeg", ".png"}
# Allowed MIME types as detected from magic bytes
_ALLOWED_MIME_TYPES: set[str] = {"image/jpeg", "image/png"}


@router.post(
    "/analyze-image",
    response_model=ImageAnalysisResponse,
    summary="Analyse an outdoor image for heat-related infrastructure",
    description=(
        "Upload a JPG or PNG image of an outdoor public space. "
        "Returns a structured analysis of visible shade, vegetation, shelters, "
        "and infrastructure gaps. All findings are preliminary and require "
        "human verification before any intervention decision."
    ),
)
async def analyze_image_endpoint(
    file: UploadFile,
    settings: Settings = Depends(get_settings),
) -> ImageAnalysisResponse:
    # ── 1. File present ───────────────────────────────────────────────── #
    if file is None or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="No file was uploaded.",
        )

    # ── 2. Extension check ────────────────────────────────────────────── #
    filename_lower = file.filename.lower()
    ext = "." + filename_lower.rsplit(".", 1)[-1] if "." in filename_lower else ""
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"File extension '{ext}' is not supported. "
                "Please upload a JPG or PNG image."
            ),
        )

    # ── 3. Read bytes + size check ────────────────────────────────────── #
    max_bytes = settings.max_image_size_mb * 1024 * 1024
    image_bytes = await file.read()

    if len(image_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The uploaded file is empty.",
        )

    if len(image_bytes) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=(
                f"File size exceeds the {settings.max_image_size_mb} MB limit. "
                "Please upload a smaller image."
            ),
        )

    # ── 4. Magic-byte MIME type check ─────────────────────────────────── #
    detected_mime = magic.from_buffer(image_bytes, mime=True)
    if detected_mime not in _ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"File content does not appear to be a valid JPG or PNG image "
                f"(detected: {detected_mime}). Please upload a real image file."
            ),
        )

    # ── 5. Gemini service call ────────────────────────────────────────── #
    logger.info(
        "Image analysis requested: filename=%s size=%d mime=%s",
        file.filename, len(image_bytes), detected_mime,
    )

    try:
        result = analyze_image(
            image_bytes=image_bytes,
            mime_type=detected_mime,
            settings=settings,
        )
    except ValueError as exc:
        logger.warning("Image analysis value error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except RuntimeError as exc:
        logger.error("Image analysis runtime error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error during image analysis")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again later.",
        ) from exc

    return ImageAnalysisResponse(success=True, data=result)
