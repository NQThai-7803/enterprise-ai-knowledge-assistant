from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from app.core.config import Settings, get_settings
from app.document_processing.errors import DocumentExtractionError
from app.document_processing.normalization import normalize_extracted_text
from app.document_processing.ocr.models import OCRHealthResult, OCRImageInput, OCRPageResult


class TesseractOCRProvider:
    def __init__(
        self,
        *,
        languages: tuple[str, ...],
        page_timeout_seconds: int,
        command: str = "tesseract",
        page_segmentation_mode: int = 6,
    ) -> None:
        if not languages:
            msg = "languages must not be empty."
            raise ValueError(msg)
        if page_timeout_seconds <= 0:
            msg = "page_timeout_seconds must be greater than zero."
            raise ValueError(msg)
        if not command.strip():
            msg = "command must not be empty."
            raise ValueError(msg)
        if page_segmentation_mode <= 0:
            msg = "page_segmentation_mode must be greater than zero."
            raise ValueError(msg)
        self.languages = tuple(languages)
        self.page_timeout_seconds = page_timeout_seconds
        self.command = command
        self.page_segmentation_mode = page_segmentation_mode
        self._health_result: OCRHealthResult | None = None

    async def extract_image(self, image: OCRImageInput) -> OCRPageResult:
        suffix = ".png" if image.image_format.lower() == "png" else ".img"
        try:
            with tempfile.TemporaryDirectory(prefix="enterprise-ai-ocr-") as temp_dir:
                image_path = Path(temp_dir) / f"page-{image.page_number}{suffix}"
                image_path.write_bytes(image.image_bytes)
                text = await self._run_tesseract(image_path)
        except DocumentExtractionError:
            raise
        except OSError as exc:
            raise DocumentExtractionError("DOCUMENT_OCR_FAILED") from exc

        return OCRPageResult(
            page_number=image.page_number,
            text=normalize_extracted_text(text),
            language="+".join(self.languages),
            width=image.width,
            height=image.height,
            extraction_method="ocr_tesseract",
        )

    async def health_check(self) -> OCRHealthResult:
        if self._health_result is not None:
            return self._health_result
        try:
            version_process = await asyncio.create_subprocess_exec(
                self.command,
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            version_stdout, _version_stderr = await asyncio.wait_for(
                version_process.communicate(),
                timeout=min(5, self.page_timeout_seconds),
            )
            languages_process = await asyncio.create_subprocess_exec(
                self.command,
                "--list-langs",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            languages_stdout, _languages_stderr = await asyncio.wait_for(
                languages_process.communicate(),
                timeout=min(5, self.page_timeout_seconds),
            )
        except (OSError, TimeoutError):
            self._health_result = OCRHealthResult(available=False, engine="tesseract")
            return self._health_result

        available_languages = _parse_available_languages(languages_stdout)
        requested_languages_available = all(
            language in available_languages for language in self.languages
        )
        version = _parse_version(version_stdout)
        self._health_result = OCRHealthResult(
            available=version_process.returncode == 0
            and languages_process.returncode == 0
            and requested_languages_available,
            engine="tesseract",
            version=version,
            languages=available_languages,
        )
        return self._health_result

    async def _run_tesseract(self, image_path: Path) -> str:
        try:
            process = await asyncio.create_subprocess_exec(
                self.command,
                str(image_path),
                "stdout",
                "-l",
                "+".join(self.languages),
                "--psm",
                str(self.page_segmentation_mode),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except OSError as exc:
            raise DocumentExtractionError("DOCUMENT_OCR_FAILED") from exc

        try:
            stdout, _stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.page_timeout_seconds,
            )
        except TimeoutError as exc:
            process.kill()
            await process.wait()
            raise DocumentExtractionError("DOCUMENT_OCR_TIMEOUT") from exc

        if process.returncode != 0:
            raise DocumentExtractionError("DOCUMENT_OCR_FAILED")
        return stdout.decode("utf-8", errors="replace")


def create_tesseract_ocr_provider(settings: Settings | None = None) -> TesseractOCRProvider:
    resolved_settings = settings or get_settings()
    return TesseractOCRProvider(
        languages=tuple(resolved_settings.ocr_languages),
        page_timeout_seconds=resolved_settings.ocr_page_timeout_seconds,
    )


def _parse_version(output: bytes) -> str | None:
    text = output.decode("utf-8", errors="replace").strip()
    return text.splitlines()[0][:80] if text else None


def _parse_available_languages(output: bytes) -> tuple[str, ...]:
    lines = output.decode("utf-8", errors="replace").splitlines()
    languages = [line.strip() for line in lines if line.strip() and " " not in line.strip()]
    return tuple(dict.fromkeys(languages))
