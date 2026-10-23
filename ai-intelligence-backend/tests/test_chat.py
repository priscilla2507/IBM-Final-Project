"""
tests/test_chat.py

Route-level tests for POST /api/chat.
Uses httpx AsyncClient against a minimal FastAPI app.
All Gemini calls are mocked — no paid API calls are made.
"""

import pytest
from unittest.mock import patch

from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from app.config import Settings, get_settings
from app.routes.chat import router


# ── Minimal app factory ───────────────────────────────────────────────────── #

def make_app(settings: Settings) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_settings] = lambda: settings
    return app


# ── Fixtures ──────────────────────────────────────────────────────────────── #

@pytest.fixture
def valid_settings():
    return Settings(gemini_api_key="test-key", gemini_model="gemini-test-model")


@pytest.fixture
def unconfigured_settings():
    return Settings(gemini_api_key="", gemini_model="")


# ── Helper ────────────────────────────────────────────────────────────────── #

def _patch_chat(answer: str):
    """Patch chat_heat_safety in the route module to return a fixed answer."""
    return patch(
        "app.routes.chat.chat_heat_safety",
        return_value=answer,
    )


# ── Tests ─────────────────────────────────────────────────────────────────── #

@pytest.mark.asyncio
class TestChatEndpoint:

    # ── Happy-path: all three languages ──────────────────────────────── #

    async def test_english_question_returns_200(self, valid_settings):
        async with AsyncClient(
            transport=ASGITransport(app=make_app(valid_settings)), base_url="http://test"
        ) as client:
            with _patch_chat("Drink water and stay in shade."):
                resp = await client.post(
                    "/api/chat",
                    json={"question": "How do I stay safe in heat?", "language": "english"},
                )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["answer"] == "Drink water and stay in shade."
        assert body["language_code"] == "english"

    async def test_hindi_question_returns_200(self, valid_settings):
        async with AsyncClient(
            transport=ASGITransport(app=make_app(valid_settings)), base_url="http://test"
        ) as client:
            with _patch_chat("पानी पियें और छाँव में रहें।"):
                resp = await client.post(
                    "/api/chat",
                    json={"question": "गर्मी में सुरक्षित कैसे रहें?", "language": "hindi"},
                )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["language_code"] == "hindi"
        assert body["answer"] is not None

    async def test_telugu_question_returns_200(self, valid_settings):
        async with AsyncClient(
            transport=ASGITransport(app=make_app(valid_settings)), base_url="http://test"
        ) as client:
            with _patch_chat("నీళ్ళు తాగండి మరియు నీడలో ఉండండి."):
                resp = await client.post(
                    "/api/chat",
                    json={"question": "వేడిలో సురక్షితంగా ఉండటం ఎలా?", "language": "telugu"},
                )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["language_code"] == "telugu"

    async def test_default_language_is_english(self, valid_settings):
        """Omitting language field should default to english."""
        async with AsyncClient(
            transport=ASGITransport(app=make_app(valid_settings)), base_url="http://test"
        ) as client:
            with _patch_chat("Stay hydrated."):
                resp = await client.post(
                    "/api/chat",
                    json={"question": "What should I do in a heatwave?"},
                )
        assert resp.status_code == 200
        assert resp.json()["language_code"] == "english"

    # ── Disclaimer always present ─────────────────────────────────────── #

    async def test_disclaimer_always_present(self, valid_settings):
        async with AsyncClient(
            transport=ASGITransport(app=make_app(valid_settings)), base_url="http://test"
        ) as client:
            with _patch_chat("Drink water."):
                resp = await client.post(
                    "/api/chat",
                    json={"question": "Heat safety tips?", "language": "english"},
                )
        body = resp.json()
        assert "disclaimer" in body
        assert len(body["disclaimer"]) > 0
        # Must mention general awareness, not medical advice
        assert "general awareness" in body["disclaimer"].lower()

    # ── Input validation (handled by Pydantic before route code runs) ─── #

    async def test_empty_question_returns_422(self, valid_settings):
        async with AsyncClient(
            transport=ASGITransport(app=make_app(valid_settings)), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/chat",
                json={"question": "", "language": "english"},
            )
        assert resp.status_code == 422

    async def test_question_too_long_returns_422(self, valid_settings):
        async with AsyncClient(
            transport=ASGITransport(app=make_app(valid_settings)), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/chat",
                json={"question": "x" * 1001, "language": "english"},
            )
        assert resp.status_code == 422

    async def test_invalid_language_returns_422(self, valid_settings):
        async with AsyncClient(
            transport=ASGITransport(app=make_app(valid_settings)), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/chat",
                json={"question": "How to stay cool?", "language": "french"},
            )
        assert resp.status_code == 422

    async def test_missing_question_field_returns_422(self, valid_settings):
        async with AsyncClient(
            transport=ASGITransport(app=make_app(valid_settings)), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/chat",
                json={"language": "english"},
            )
        assert resp.status_code == 422

    async def test_empty_body_returns_422(self, valid_settings):
        async with AsyncClient(
            transport=ASGITransport(app=make_app(valid_settings)), base_url="http://test"
        ) as client:
            resp = await client.post("/api/chat", json={})
        assert resp.status_code == 422

    # ── Configuration errors ──────────────────────────────────────────── #

    async def test_unconfigured_gemini_returns_422(self, unconfigured_settings):
        async with AsyncClient(
            transport=ASGITransport(app=make_app(unconfigured_settings)), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/chat",
                json={"question": "Heat tips?", "language": "english"},
            )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert "GEMINI_API_KEY" in detail or "GEMINI_MODEL" in detail

    # ── Gemini API failures ───────────────────────────────────────────── #

    async def test_gemini_runtime_error_returns_503(self, valid_settings):
        async with AsyncClient(
            transport=ASGITransport(app=make_app(valid_settings)), base_url="http://test"
        ) as client:
            with patch(
                "app.routes.chat.chat_heat_safety",
                side_effect=RuntimeError("Gemini service is temporarily unavailable."),
            ):
                resp = await client.post(
                    "/api/chat",
                    json={"question": "Heat tips?", "language": "english"},
                )
        assert resp.status_code == 503
        assert "unavailable" in resp.json()["detail"].lower()

    async def test_gemini_value_error_returns_422(self, valid_settings):
        async with AsyncClient(
            transport=ASGITransport(app=make_app(valid_settings)), base_url="http://test"
        ) as client:
            with patch(
                "app.routes.chat.chat_heat_safety",
                side_effect=ValueError("Gemini returned an empty response for the chat request."),
            ):
                resp = await client.post(
                    "/api/chat",
                    json={"question": "Heat tips?", "language": "english"},
                )
        assert resp.status_code == 422

    async def test_unexpected_error_returns_500_without_leaking_detail(self, valid_settings):
        async with AsyncClient(
            transport=ASGITransport(app=make_app(valid_settings)), base_url="http://test"
        ) as client:
            with patch(
                "app.routes.chat.chat_heat_safety",
                side_effect=Exception("internal secret detail"),
            ):
                resp = await client.post(
                    "/api/chat",
                    json={"question": "Heat tips?", "language": "english"},
                )
        assert resp.status_code == 500
        assert "internal secret detail" not in resp.json()["detail"]

    # ── Response schema shape ─────────────────────────────────────────── #

    async def test_response_schema_has_all_required_fields(self, valid_settings):
        async with AsyncClient(
            transport=ASGITransport(app=make_app(valid_settings)), base_url="http://test"
        ) as client:
            with _patch_chat("Stay hydrated and avoid peak sun hours."):
                resp = await client.post(
                    "/api/chat",
                    json={"question": "Heat safety?", "language": "english"},
                )
        assert resp.status_code == 200
        body = resp.json()
        for key in ("success", "answer", "language_code", "disclaimer", "error"):
            assert key in body, f"Missing key in response: {key}"
        assert body["error"] is None

    async def test_success_false_on_error_has_correct_schema(self, valid_settings):
        """Error responses must not expose internal Python exception messages."""
        async with AsyncClient(
            transport=ASGITransport(app=make_app(valid_settings)), base_url="http://test"
        ) as client:
            with patch(
                "app.routes.chat.chat_heat_safety",
                side_effect=RuntimeError("downstream failure"),
            ):
                resp = await client.post(
                    "/api/chat",
                    json={"question": "Heat tips?", "language": "english"},
                )
        # FastAPI HTTPException error responses use {"detail": ...}, not ChatResponse
        assert resp.status_code == 503
        assert "detail" in resp.json()
