"""
tests/test_image_analysis.py

Route-level tests for POST /api/analyze-image.
Uses httpx AsyncClient against a minimal FastAPI app.
All Gemini calls are mocked — no paid API calls are made.
"""

import struct
import zlib
import pytest
from unittest.mock import patch

from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from app.config import Settings, get_settings
from app.routes.image_analysis import router
from app.schemas.ai_schemas import (
    DrinkingWaterObservation,
    ImageAnalysisResult,
    ShadedAreaObservation,
    ShelterObservation,
    SunExposedAreaObservation,
    VegetationObservation,
)


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


@pytest.fixture
def sample_result() -> ImageAnalysisResult:
    return ImageAnalysisResult(
        vegetation=VegetationObservation(visible=True, description="Trees visible."),
        shaded_areas=ShadedAreaObservation(visible=True, description="Shade present."),
        sun_exposed_areas=SunExposedAreaObservation(visible=True, description="Open path."),
        shelters=ShelterObservation(visible=False, description=None),
        drinking_water=DrinkingWaterObservation(visible=False, description=None),
        infrastructure_gaps=["No shelter visible"],
        explanation="Tree-lined street with partial shade.",
        limitations="Cannot confirm off-frame facilities.",
        human_verification_required=True,
    )


# Minimal valid JPEG bytes (SOI + APP0 marker)
MINIMAL_JPEG = bytes([0xFF, 0xD8, 0xFF, 0xE0]) + b"\x00" * 16


def _make_minimal_png() -> bytes:
    """Build a 1×1 px PNG that python-magic correctly identifies as image/png."""
    sig = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])
    ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)  # 1x1, 8-bit RGB
    chunk = b"IHDR" + ihdr_data
    ihdr_chunk = struct.pack(">I", len(ihdr_data)) + chunk + struct.pack(">I", zlib.crc32(chunk) & 0xFFFFFFFF)
    return sig + ihdr_chunk


MINIMAL_PNG = _make_minimal_png()


# ── Helper ────────────────────────────────────────────────────────────────── #

def _patch_analyze(result):
    """Patch analyze_image in the route module to return result."""
    return patch(
        "app.routes.image_analysis.analyze_image",
        return_value=result,
    )


# ── Tests ─────────────────────────────────────────────────────────────────── #

@pytest.mark.asyncio
class TestAnalyzeImageEndpoint:

    async def test_valid_jpeg_returns_200(self, valid_settings, sample_result):
        async with AsyncClient(
            transport=ASGITransport(app=make_app(valid_settings)), base_url="http://test"
        ) as client:
            with _patch_analyze(sample_result):
                resp = await client.post(
                    "/api/analyze-image",
                    files={"file": ("street.jpg", MINIMAL_JPEG, "image/jpeg")},
                )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["human_verification_required"] is True

    async def test_valid_png_returns_200(self, valid_settings, sample_result):
        async with AsyncClient(
            transport=ASGITransport(app=make_app(valid_settings)), base_url="http://test"
        ) as client:
            with _patch_analyze(sample_result):
                resp = await client.post(
                    "/api/analyze-image",
                    files={"file": ("image.png", MINIMAL_PNG, "image/png")},
                )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    async def test_jpeg_extension_accepted(self, valid_settings, sample_result):
        """.jpeg extension (not just .jpg) must be accepted."""
        async with AsyncClient(
            transport=ASGITransport(app=make_app(valid_settings)), base_url="http://test"
        ) as client:
            with _patch_analyze(sample_result):
                resp = await client.post(
                    "/api/analyze-image",
                    files={"file": ("photo.jpeg", MINIMAL_JPEG, "image/jpeg")},
                )
        assert resp.status_code == 200

    async def test_unsupported_extension_returns_415(self, valid_settings):
        async with AsyncClient(
            transport=ASGITransport(app=make_app(valid_settings)), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/analyze-image",
                files={"file": ("image.gif", b"GIF89a" + b"\x00" * 16, "image/gif")},
            )
        assert resp.status_code == 415
        assert "JPG or PNG" in resp.json()["detail"]

    async def test_wrong_extension_rejected_before_magic_check(self, valid_settings):
        """.txt file containing real JPEG bytes must be rejected by extension check."""
        async with AsyncClient(
            transport=ASGITransport(app=make_app(valid_settings)), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/analyze-image",
                files={"file": ("data.txt", MINIMAL_JPEG, "text/plain")},
            )
        assert resp.status_code == 415

    async def test_empty_file_returns_422(self, valid_settings):
        async with AsyncClient(
            transport=ASGITransport(app=make_app(valid_settings)), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/analyze-image",
                files={"file": ("empty.jpg", b"", "image/jpeg")},
            )
        assert resp.status_code == 422
        assert "empty" in resp.json()["detail"].lower()

    async def test_oversized_file_returns_413(self, valid_settings):
        # 11 MB with JPEG header so it passes extension + magic checks
        oversized = bytes([0xFF, 0xD8, 0xFF, 0xE0]) + b"\x00" * (11 * 1024 * 1024)
        async with AsyncClient(
            transport=ASGITransport(app=make_app(valid_settings)), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/analyze-image",
                files={"file": ("big.jpg", oversized, "image/jpeg")},
            )
        assert resp.status_code == 413
        assert "MB limit" in resp.json()["detail"]

    async def test_renamed_non_image_returns_415(self, valid_settings):
        """.jpg file with PDF magic bytes must be rejected by magic-byte check."""
        pdf_bytes = b"%PDF-1.4" + b"\x00" * 16
        async with AsyncClient(
            transport=ASGITransport(app=make_app(valid_settings)), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/analyze-image",
                files={"file": ("fake.jpg", pdf_bytes, "image/jpeg")},
            )
        assert resp.status_code == 415
        assert "valid JPG or PNG" in resp.json()["detail"]

    async def test_unconfigured_gemini_returns_503(self, unconfigured_settings):
        async with AsyncClient(
            transport=ASGITransport(app=make_app(unconfigured_settings)), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/analyze-image",
                files={"file": ("street.jpg", MINIMAL_JPEG, "image/jpeg")},
            )
        assert resp.status_code == 503
        detail = resp.json()["detail"]
        assert "GEMINI_API_KEY" in detail or "GEMINI_MODEL" in detail

    async def test_gemini_runtime_error_returns_503(self, valid_settings):
        async with AsyncClient(
            transport=ASGITransport(app=make_app(valid_settings)), base_url="http://test"
        ) as client:
            with patch(
                "app.routes.image_analysis.analyze_image",
                side_effect=RuntimeError("Gemini service is temporarily unavailable."),
            ):
                resp = await client.post(
                    "/api/analyze-image",
                    files={"file": ("street.jpg", MINIMAL_JPEG, "image/jpeg")},
                )
        assert resp.status_code == 503

    async def test_gemini_value_error_returns_503(self, valid_settings):
        async with AsyncClient(
            transport=ASGITransport(app=make_app(valid_settings)), base_url="http://test"
        ) as client:
            with patch(
                "app.routes.image_analysis.analyze_image",
                side_effect=ValueError("Gemini returned non-JSON content"),
            ):
                resp = await client.post(
                    "/api/analyze-image",
                    files={"file": ("street.jpg", MINIMAL_JPEG, "image/jpeg")},
                )
        assert resp.status_code == 503

    async def test_unexpected_error_returns_500_without_leaking_detail(self, valid_settings):
        async with AsyncClient(
            transport=ASGITransport(app=make_app(valid_settings)), base_url="http://test"
        ) as client:
            with patch(
                "app.routes.image_analysis.analyze_image",
                side_effect=Exception("internal secret detail"),
            ):
                resp = await client.post(
                    "/api/analyze-image",
                    files={"file": ("street.jpg", MINIMAL_JPEG, "image/jpeg")},
                )
        assert resp.status_code == 500
        # Internal exception message must not reach the caller
        assert "internal secret detail" not in resp.json()["detail"]

    async def test_response_schema_has_all_required_fields(self, valid_settings, sample_result):
        async with AsyncClient(
            transport=ASGITransport(app=make_app(valid_settings)), base_url="http://test"
        ) as client:
            with _patch_analyze(sample_result):
                resp = await client.post(
                    "/api/analyze-image",
                    files={"file": ("street.jpg", MINIMAL_JPEG, "image/jpeg")},
                )
        body = resp.json()
        assert body["success"] is True
        assert body["error"] is None
        data = body["data"]
        for key in (
            "vegetation", "shaded_areas", "sun_exposed_areas",
            "shelters", "drinking_water", "infrastructure_gaps",
            "explanation", "limitations", "human_verification_required",
        ):
            assert key in data, f"Missing key in response data: {key}"
