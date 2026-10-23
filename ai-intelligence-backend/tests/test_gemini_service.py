"""
tests/test_gemini_service.py

Unit tests for app/services/gemini_service.py.
All Gemini SDK calls are mocked — no paid API calls are made.
"""

import json
import pytest
from unittest.mock import MagicMock, patch

from app.config import Settings
from app.services.gemini_service import (
    SUPPORTED_MIME_TYPES,
    _safe_parse_image_json,
    analyze_image,
    chat_heat_safety,
)
from app.schemas.ai_schemas import ImageAnalysisResult


# ── Helpers ───────────────────────────────────────────────────────────────── #

def _mock_response(text: str) -> MagicMock:
    mock = MagicMock()
    mock.text = text
    return mock


# ── Fixtures ──────────────────────────────────────────────────────────────── #

@pytest.fixture
def valid_settings():
    return Settings(gemini_api_key="test-key", gemini_model="gemini-test-model")


@pytest.fixture
def missing_key_settings():
    return Settings(gemini_api_key="", gemini_model="gemini-test-model")


@pytest.fixture
def missing_model_settings():
    return Settings(gemini_api_key="test-key", gemini_model="")


@pytest.fixture
def valid_image_json() -> str:
    return json.dumps({
        "vegetation":        {"visible": True,  "description": "Several trees visible."},
        "shaded_areas":      {"visible": True,  "description": "Shade under trees."},
        "sun_exposed_areas": {"visible": True,  "description": "Open footpath exposed."},
        "shelters":          {"visible": False, "description": None},
        "drinking_water":    {"visible": False, "description": None},
        "infrastructure_gaps": [
            "No covered shelter visible",
            "No drinking water point visible",
        ],
        "explanation": "The image shows a tree-lined street with partial shade.",
        "limitations": "Cannot confirm if drinking water exists off-frame.",
        "human_verification_required": True,
    })


# ── _safe_parse_image_json ────────────────────────────────────────────────── #

class TestSafeParseImageJson:
    def test_valid_json_parses_correctly(self, valid_image_json):
        result = _safe_parse_image_json(valid_image_json)
        assert isinstance(result, ImageAnalysisResult)
        assert result.vegetation.visible is True
        assert result.shelters.visible is False
        assert result.human_verification_required is True

    def test_strips_markdown_json_fences(self, valid_image_json):
        fenced = f"```json\n{valid_image_json}\n```"
        result = _safe_parse_image_json(fenced)
        assert isinstance(result, ImageAnalysisResult)

    def test_strips_plain_fences(self, valid_image_json):
        fenced = f"```\n{valid_image_json}\n```"
        result = _safe_parse_image_json(fenced)
        assert isinstance(result, ImageAnalysisResult)

    def test_invalid_json_raises_value_error(self):
        with pytest.raises(ValueError, match="non-JSON"):
            _safe_parse_image_json("not json at all")

    def test_missing_required_field_raises_value_error(self):
        # Only vegetation key present — all other required fields missing
        broken = json.dumps({"vegetation": {"visible": True}})
        with pytest.raises(ValueError, match="missing expected fields"):
            _safe_parse_image_json(broken)

    def test_human_verification_always_forced_true(self, valid_image_json):
        # Simulate model returning false — parser must override to True
        data = json.loads(valid_image_json)
        data["human_verification_required"] = False
        result = _safe_parse_image_json(json.dumps(data))
        assert result.human_verification_required is True


# ── analyze_image ─────────────────────────────────────────────────────────── #

class TestAnalyzeImage:
    def test_missing_api_key_raises_value_error(self, missing_key_settings):
        with pytest.raises(ValueError, match="GEMINI_API_KEY"):
            analyze_image(b"fake", "image/jpeg", missing_key_settings)

    def test_missing_model_raises_value_error(self, missing_model_settings):
        with pytest.raises(ValueError, match="GEMINI_MODEL"):
            analyze_image(b"fake", "image/jpeg", missing_model_settings)

    def test_unsupported_mime_type_raises_value_error(self, valid_settings):
        with pytest.raises(ValueError, match="Unsupported image type"):
            analyze_image(b"fake", "image/gif", valid_settings)

    def test_valid_jpeg_returns_result(self, valid_settings, valid_image_json):
        with patch("app.services.gemini_service._build_client") as mock_build:
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = _mock_response(valid_image_json)
            mock_build.return_value = mock_client

            result = analyze_image(b"fakejpeg", "image/jpeg", valid_settings)

        assert isinstance(result, ImageAnalysisResult)
        assert result.human_verification_required is True

    def test_valid_png_returns_result(self, valid_settings, valid_image_json):
        with patch("app.services.gemini_service._build_client") as mock_build:
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = _mock_response(valid_image_json)
            mock_build.return_value = mock_client

            result = analyze_image(b"fakepng", "image/png", valid_settings)

        assert isinstance(result, ImageAnalysisResult)

    def test_empty_gemini_response_raises_value_error(self, valid_settings):
        with patch("app.services.gemini_service._build_client") as mock_build:
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = _mock_response("")
            mock_build.return_value = mock_client

            with pytest.raises(ValueError, match="empty response"):
                analyze_image(b"fakejpeg", "image/jpeg", valid_settings)

    def test_malformed_json_raises_value_error(self, valid_settings):
        with patch("app.services.gemini_service._build_client") as mock_build:
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = _mock_response("oops not json")
            mock_build.return_value = mock_client

            with pytest.raises(ValueError, match="non-JSON"):
                analyze_image(b"fakejpeg", "image/jpeg", valid_settings)

    def test_gemini_api_error_raises_runtime_error(self, valid_settings):
        from google.genai import errors as genai_errors
        with patch("app.services.gemini_service._build_client") as mock_build:
            mock_client = MagicMock()
            mock_client.models.generate_content.side_effect = genai_errors.APIError(
                500, "quota exceeded", None
            )
            mock_build.return_value = mock_client

            with pytest.raises(RuntimeError):
                analyze_image(b"fakejpeg", "image/jpeg", valid_settings)

    def test_gemini_client_error_raises_runtime_error(self, valid_settings):
        from google.genai import errors as genai_errors
        with patch("app.services.gemini_service._build_client") as mock_build:
            mock_client = MagicMock()
            mock_client.models.generate_content.side_effect = genai_errors.ClientError(
                400, "invalid request", None
            )
            mock_build.return_value = mock_client

            with pytest.raises(RuntimeError, match="Gemini request failed"):
                analyze_image(b"fakejpeg", "image/jpeg", valid_settings)


# ── chat_heat_safety ──────────────────────────────────────────────────────── #

class TestChatHeatSafety:
    def test_missing_api_key_raises_value_error(self, missing_key_settings):
        with pytest.raises(ValueError, match="GEMINI_API_KEY"):
            chat_heat_safety("How to stay cool?", "english", missing_key_settings)

    def test_missing_model_raises_value_error(self, missing_model_settings):
        with pytest.raises(ValueError, match="GEMINI_MODEL"):
            chat_heat_safety("How to stay cool?", "english", missing_model_settings)

    def test_unsupported_language_raises_value_error(self, valid_settings):
        with pytest.raises(ValueError, match="Unsupported language"):
            chat_heat_safety("How to stay cool?", "french", valid_settings)

    @pytest.mark.parametrize("language", ["english", "hindi", "telugu"])
    def test_valid_languages_return_answer(self, language, valid_settings):
        with patch("app.services.gemini_service._build_client") as mock_build:
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = _mock_response(
                "Drink water regularly and stay in shade."
            )
            mock_build.return_value = mock_client

            answer = chat_heat_safety("How to stay safe?", language, valid_settings)

        assert isinstance(answer, str)
        assert len(answer) > 0

    def test_empty_gemini_response_raises_value_error(self, valid_settings):
        with patch("app.services.gemini_service._build_client") as mock_build:
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = _mock_response("   ")
            mock_build.return_value = mock_client

            with pytest.raises(ValueError, match="empty response"):
                chat_heat_safety("question", "english", valid_settings)

    def test_gemini_server_error_raises_runtime_error(self, valid_settings):
        from google.genai import errors as genai_errors
        with patch("app.services.gemini_service._build_client") as mock_build:
            mock_client = MagicMock()
            mock_client.models.generate_content.side_effect = genai_errors.ServerError(
                503, "overloaded", None
            )
            mock_build.return_value = mock_client

            with pytest.raises(RuntimeError, match="temporarily unavailable"):
                chat_heat_safety("question", "english", valid_settings)

    def test_answer_is_stripped_of_whitespace(self, valid_settings):
        with patch("app.services.gemini_service._build_client") as mock_build:
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = _mock_response(
                "  Stay hydrated.  \n"
            )
            mock_build.return_value = mock_client

            answer = chat_heat_safety("question", "english", valid_settings)

        assert answer == "Stay hydrated."
