"""
app/services/gemini_service.py

Reusable Gemini API service functions for:
  - analyze_image()      →  ImageAnalysisResult
  - chat_heat_safety()   →  str (answer text)

Design rules:
- Config validated via require_gemini_config() before every API call.
- Images passed as inline bytes (Part.from_bytes); no file upload API needed.
- Gemini asked to return strict JSON for image analysis (response_mime_type).
- JSON parsed into Pydantic models; malformed responses raise ValueError.
- SDK errors caught and re-raised as plain RuntimeError with safe messages.
- No API keys, no image bytes, and no personal data are logged.
"""

import json
import logging
from typing import Optional

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from app.config import Settings, require_gemini_config
from app.schemas.ai_schemas import (
    DrinkingWaterObservation,
    ImageAnalysisResult,
    ShadedAreaObservation,
    ShelterObservation,
    SunExposedAreaObservation,
    VegetationObservation,
)

logger = logging.getLogger(__name__)

# ── Supported image MIME types ────────────────────────────────────────────── #
SUPPORTED_MIME_TYPES: set[str] = {"image/jpeg", "image/png"}

# ── Heat-safety system instruction ───────────────────────────────────────── #
# Reviewed, cautious guidance embedded as the system prompt.
# The model is explicitly told what it must NOT do.
_CHAT_SYSTEM_INSTRUCTION = """
You are a heat-safety assistant for ChhayaRakshak AI, a public-health platform
serving residents of Hyderabad, India.

Your role:
- Answer questions about protecting oneself from heat, heat exhaustion, and
  heatstroke using well-established public-health guidance (WHO, ICMR, NDMA).
- Give practical, actionable advice: hydration, shade-seeking, clothing, timing
  of outdoor activity, cooling centres.
- Respond in the language requested by the system (English, Hindi, or Telugu).
- Keep answers concise and understandable for a general audience.

Hard limits — you MUST NOT:
- Diagnose any individual or claim to know a person's medical condition.
- Invent or speculate about medical treatments, drug names, or dosages.
- Present uncertain or unverified information as authoritative fact.
- Recommend ignoring professional medical advice.
- If someone describes emergency symptoms (loss of consciousness, seizures,
  very high body temperature, confusion), instruct them to call emergency
  services or go to the nearest hospital immediately. Do not attempt to
  treat emergencies through chat.

Always be clear that your guidance is for general awareness only and is not
a substitute for professional medical advice.
""".strip()

# ── Image analysis prompt ─────────────────────────────────────────────────── #
_IMAGE_ANALYSIS_PROMPT = """
Analyse this outdoor public-space image for heat-related infrastructure.
You MUST respond with valid JSON only — no markdown fences, no extra text.

Return exactly this JSON structure:
{
  "vegetation": {
    "visible": <true|false>,
    "description": "<short description or null>"
  },
  "shaded_areas": {
    "visible": <true|false>,
    "description": "<short description or null>"
  },
  "sun_exposed_areas": {
    "visible": <true|false>,
    "description": "<short description or null>"
  },
  "shelters": {
    "visible": <true|false>,
    "description": "<short description or null>"
  },
  "drinking_water": {
    "visible": <true|false>,
    "description": "<short description or null>"
  },
  "infrastructure_gaps": ["<gap1>", "<gap2>"],
  "explanation": "<2-3 sentence plain-language summary>",
  "limitations": "<what cannot be determined from this image alone>",
  "human_verification_required": true
}

Rules you must follow:
- Base every observation strictly on what is VISIBLE in the image.
- Use "visible": false with description: null when something is not visible.
  "Not visible" does NOT mean "does not exist".
- Do NOT claim to measure temperature, air quality, or UV index.
- Do NOT claim a facility is operational based on its appearance.
- Do NOT invent objects or observations not supported by the image.
- human_verification_required must always be true.
""".strip()

# ── Language display names for prompt construction ───────────────────────── #
_LANGUAGE_NAMES = {
    "english": "English",
    "hindi":   "Hindi (Devanagari script)",
    "telugu":  "Telugu (Telugu script)",
}


def _build_client(api_key: str) -> genai.Client:
    """Return a configured Gemini client. Does not make any network call."""
    return genai.Client(api_key=api_key)


def _safe_parse_image_json(raw: str) -> ImageAnalysisResult:
    """
    Parse the raw JSON string returned by Gemini into an ImageAnalysisResult.
    Strips accidental markdown fences if the model added them despite instructions.
    Raises ValueError on parse failure.
    """
    text = raw.strip()
    # Strip ```json ... ``` or ``` ... ``` if present
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(
            line for line in lines
            if not line.strip().startswith("```")
        ).strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Gemini returned non-JSON content: {exc}") from exc

    try:
        return ImageAnalysisResult(
            vegetation=VegetationObservation(**data["vegetation"]),
            shaded_areas=ShadedAreaObservation(**data["shaded_areas"]),
            sun_exposed_areas=SunExposedAreaObservation(**data["sun_exposed_areas"]),
            shelters=ShelterObservation(**data["shelters"]),
            drinking_water=DrinkingWaterObservation(**data["drinking_water"]),
            infrastructure_gaps=data.get("infrastructure_gaps", []),
            explanation=data["explanation"],
            limitations=data["limitations"],
            human_verification_required=True,  # always forced True
        )
    except (KeyError, TypeError) as exc:
        raise ValueError(f"Gemini JSON missing expected fields: {exc}") from exc


# ── Public service functions ──────────────────────────────────────────────── #

def analyze_image(
    image_bytes: bytes,
    mime_type: str,
    settings: Settings,
) -> ImageAnalysisResult:
    """
    Send an image to Gemini for heat-infrastructure analysis.

    Args:
        image_bytes: Raw bytes of the uploaded image.
        mime_type:   Must be one of SUPPORTED_MIME_TYPES.
        settings:    Application settings (from get_settings()).

    Returns:
        ImageAnalysisResult populated from Gemini's structured response.

    Raises:
        ValueError:   Config missing, unsupported MIME type, or malformed response.
        RuntimeError: Gemini API call failed.
    """
    api_key, model = require_gemini_config(settings)

    if mime_type not in SUPPORTED_MIME_TYPES:
        raise ValueError(
            f"Unsupported image type '{mime_type}'. "
            f"Accepted: {', '.join(sorted(SUPPORTED_MIME_TYPES))}"
        )

    client = _build_client(api_key)

    image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
    text_part  = types.Part.from_text(text=_IMAGE_ANALYSIS_PROMPT)

    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        temperature=0.1,
        max_output_tokens=1024,
    )

    logger.info(
        "Sending image analysis request to Gemini (model=%s, mime=%s)",
        model, mime_type,
    )

    try:
        response = client.models.generate_content(
            model=model,
            contents=[image_part, text_part],
            config=config,
        )
    except genai_errors.ClientError as exc:
        logger.error("Gemini client error during image analysis: %s", exc.message)
        raise RuntimeError(f"Gemini request failed: {exc.message}") from exc
    except genai_errors.ServerError as exc:
        logger.error("Gemini server error during image analysis: %s", exc.message)
        raise RuntimeError("Gemini service is temporarily unavailable.") from exc
    except genai_errors.APIError as exc:
        logger.error("Gemini API error during image analysis: %s", exc.message)
        raise RuntimeError(f"Gemini API error: {exc.message}") from exc

    raw_text: Optional[str] = response.text
    if not raw_text:
        raise ValueError("Gemini returned an empty response for image analysis.")

    logger.info("Received image analysis response from Gemini.")
    return _safe_parse_image_json(raw_text)


def chat_heat_safety(
    question: str,
    language: str,
    settings: Settings,
) -> str:
    """
    Answer a heat-safety question in the requested language.

    Args:
        question: The user's question (already validated by ChatRequest schema).
        language: One of 'english', 'hindi', 'telugu'.
        settings: Application settings (from get_settings()).

    Returns:
        Answer text in the requested language.

    Raises:
        ValueError:   Config missing or unsupported language.
        RuntimeError: Gemini API call failed.
    """
    api_key, model = require_gemini_config(settings)

    lang_display = _LANGUAGE_NAMES.get(language.lower())
    if lang_display is None:
        raise ValueError(
            f"Unsupported language '{language}'. "
            f"Accepted: {', '.join(_LANGUAGE_NAMES.keys())}"
        )

    client = _build_client(api_key)

    user_prompt = (
        f"Please answer the following heat-safety question in {lang_display}.\n\n"
        f"Question: {question}"
    )

    config = types.GenerateContentConfig(
        system_instruction=_CHAT_SYSTEM_INSTRUCTION,
        temperature=0.3,
        max_output_tokens=512,
    )

    logger.info(
        "Sending chat request to Gemini (model=%s, language=%s)",
        model, language,
    )

    try:
        response = client.models.generate_content(
            model=model,
            contents=user_prompt,
            config=config,
        )
    except genai_errors.ClientError as exc:
        logger.error("Gemini client error during chat: %s", exc.message)
        raise RuntimeError(f"Gemini request failed: {exc.message}") from exc
    except genai_errors.ServerError as exc:
        logger.error("Gemini server error during chat: %s", exc.message)
        raise RuntimeError("Gemini service is temporarily unavailable.") from exc
    except genai_errors.APIError as exc:
        logger.error("Gemini API error during chat: %s", exc.message)
        raise RuntimeError(f"Gemini API error: {exc.message}") from exc

    answer: Optional[str] = response.text
    if not answer or not answer.strip():
        raise ValueError("Gemini returned an empty response for the chat request.")

    logger.info("Received chat response from Gemini.")
    return answer.strip()
