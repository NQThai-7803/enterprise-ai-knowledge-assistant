from __future__ import annotations

import io
import warnings
from dataclasses import dataclass, field

from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import Settings, get_settings
from app.document_processing.errors import DocumentExtractionError


@dataclass(frozen=True, slots=True)
class ValidatedImage:
    image_bytes: bytes = field(repr=False)
    width: int
    height: int
    image_format: str

    def __post_init__(self) -> None:
        if not self.image_bytes:
            msg = "image_bytes must not be empty."
            raise ValueError(msg)
        if self.width <= 0 or self.height <= 0:
            msg = "image dimensions must be positive."
            raise ValueError(msg)
        if not self.image_format.strip():
            msg = "image_format must not be empty."
            raise ValueError(msg)


def validate_and_normalize_image_bytes(
    image_bytes: bytes,
    *,
    settings: Settings | None = None,
) -> ValidatedImage:
    resolved_settings = settings or get_settings()
    if not image_bytes:
        raise DocumentExtractionError("DOCUMENT_IMAGE_INVALID")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(image_bytes)) as image:
                image.verify()
            with Image.open(io.BytesIO(image_bytes)) as image:
                _validate_image_dimensions(image.size, settings=resolved_settings)
                normalized = ImageOps.exif_transpose(image)
                if normalized.mode not in {"1", "L", "LA", "P", "RGB", "RGBA", "CMYK"}:
                    normalized = normalized.convert("RGB")
                else:
                    normalized = normalized.convert("RGB")
                normalized.load()
                output = io.BytesIO()
                normalized.save(output, format="PNG", optimize=False)
                return ValidatedImage(
                    image_bytes=output.getvalue(),
                    width=normalized.width,
                    height=normalized.height,
                    image_format="png",
                )
    except DocumentExtractionError:
        raise
    except (
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        UnidentifiedImageError,
        OSError,
        ValueError,
    ) as exc:
        raise DocumentExtractionError("DOCUMENT_IMAGE_INVALID") from exc


def _validate_image_dimensions(size: tuple[int, int], *, settings: Settings) -> None:
    width, height = size
    if width <= 0 or height <= 0:
        raise DocumentExtractionError("DOCUMENT_IMAGE_INVALID")
    if width > settings.ocr_max_image_width or height > settings.ocr_max_image_height:
        raise DocumentExtractionError("DOCUMENT_IMAGE_DIMENSIONS_EXCEEDED")
    if width * height > settings.ocr_max_image_pixels:
        raise DocumentExtractionError("DOCUMENT_IMAGE_DIMENSIONS_EXCEEDED")
