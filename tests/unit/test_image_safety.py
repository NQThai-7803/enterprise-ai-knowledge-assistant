from __future__ import annotations

import io

import pytest
from PIL import Image

from app.core.config import Settings
from app.document_processing.errors import DocumentExtractionError
from app.document_processing.image_safety import validate_and_normalize_image_bytes


def make_image_bytes(*, width: int = 4, height: int = 3, image_format: str = "PNG") -> bytes:
    image = Image.new("RGB", (width, height), color=(255, 255, 255))
    output = io.BytesIO()
    image.save(output, format=image_format)
    return output.getvalue()


def make_settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "ocr_document_timeout_seconds": 240,
        "celery_task_soft_time_limit_seconds": 300,
    }
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)


def test_validate_and_normalize_image_bytes_returns_png_rgb_payload() -> None:
    result = validate_and_normalize_image_bytes(
        make_image_bytes(image_format="JPEG"),
        settings=make_settings(),
    )

    assert result.width == 4
    assert result.height == 3
    assert result.image_format == "png"
    assert result.image_bytes.startswith(b"\x89PNG\r\n\x1a\n")


def test_validate_and_normalize_image_bytes_rejects_empty_payload() -> None:
    with pytest.raises(DocumentExtractionError) as exc_info:
        validate_and_normalize_image_bytes(b"", settings=make_settings())

    assert exc_info.value.code == "DOCUMENT_IMAGE_INVALID"


def test_validate_and_normalize_image_bytes_rejects_invalid_payload() -> None:
    with pytest.raises(DocumentExtractionError) as exc_info:
        validate_and_normalize_image_bytes(b"not an image", settings=make_settings())

    assert exc_info.value.code == "DOCUMENT_IMAGE_INVALID"


def test_validate_and_normalize_image_bytes_rejects_dimension_limit() -> None:
    with pytest.raises(DocumentExtractionError) as exc_info:
        validate_and_normalize_image_bytes(
            make_image_bytes(width=4, height=3),
            settings=make_settings(ocr_max_image_width=3),
        )

    assert exc_info.value.code == "DOCUMENT_IMAGE_DIMENSIONS_EXCEEDED"


def test_validate_and_normalize_image_bytes_rejects_pixel_limit() -> None:
    with pytest.raises(DocumentExtractionError) as exc_info:
        validate_and_normalize_image_bytes(
            make_image_bytes(width=4, height=3),
            settings=make_settings(ocr_max_image_pixels=10),
        )

    assert exc_info.value.code == "DOCUMENT_IMAGE_DIMENSIONS_EXCEEDED"
