from __future__ import annotations

from pathlib import Path

import pytest

from app.document_processing.errors import DocumentExtractionError
from app.document_processing.ocr.models import OCRImageInput
from app.document_processing.ocr.tesseract_provider import TesseractOCRProvider


class FakeProcess:
    def __init__(self, *, stdout: bytes = b"", returncode: int = 0) -> None:
        self.stdout = stdout
        self.returncode = returncode
        self.killed = False
        self.waited = False

    async def communicate(self) -> tuple[bytes, bytes]:
        return self.stdout, b""

    def kill(self) -> None:
        self.killed = True

    async def wait(self) -> int:
        self.waited = True
        return self.returncode


def make_provider() -> TesseractOCRProvider:
    return TesseractOCRProvider(
        languages=("vie", "eng"),
        page_timeout_seconds=5,
        command="fake-tesseract",
    )


def make_image() -> OCRImageInput:
    return OCRImageInput(
        page_number=3,
        image_bytes=b"\x89PNG\r\n\x1a\nbody",
        width=20,
        height=10,
        image_format="png",
    )


@pytest.mark.anyio
async def test_extract_image_invokes_tesseract_with_language_and_psm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, ...]] = []

    async def fake_create_subprocess_exec(*args, **kwargs):  # noqa: ANN001, ARG001
        calls.append(tuple(str(arg) for arg in args))
        image_path = Path(args[1])
        assert image_path.exists()
        assert image_path.read_bytes().startswith(b"\x89PNG")
        return FakeProcess(stdout=b" OCR policy text \n")

    monkeypatch.setattr(
        "app.document_processing.ocr.tesseract_provider.asyncio.create_subprocess_exec",
        fake_create_subprocess_exec,
    )

    result = await make_provider().extract_image(make_image())

    assert result.page_number == 3
    assert result.text == "OCR policy text"
    assert result.language == "vie+eng"
    assert result.width == 20
    assert result.height == 10
    assert result.extraction_method == "ocr_tesseract"
    assert calls[0][0] == "fake-tesseract"
    assert calls[0][2:] == (
        "stdout",
        "-l",
        "vie+eng",
        "--psm",
        "6",
    )


@pytest.mark.anyio
async def test_extract_image_maps_nonzero_tesseract_exit_to_safe_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_create_subprocess_exec(*args, **kwargs):  # noqa: ANN001, ARG001
        return FakeProcess(returncode=2)

    monkeypatch.setattr(
        "app.document_processing.ocr.tesseract_provider.asyncio.create_subprocess_exec",
        fake_create_subprocess_exec,
    )

    with pytest.raises(DocumentExtractionError) as exc_info:
        await make_provider().extract_image(make_image())

    assert exc_info.value.code == "DOCUMENT_OCR_FAILED"
    assert "PNG" not in exc_info.value.safe_message


@pytest.mark.anyio
async def test_extract_image_kills_tesseract_on_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = FakeProcess()

    async def fake_create_subprocess_exec(*args, **kwargs):  # noqa: ANN001, ARG001
        return process

    async def fake_wait_for(awaitable, timeout):  # noqa: ANN001, ARG001
        awaitable.close()
        raise TimeoutError

    monkeypatch.setattr(
        "app.document_processing.ocr.tesseract_provider.asyncio.create_subprocess_exec",
        fake_create_subprocess_exec,
    )
    monkeypatch.setattr(
        "app.document_processing.ocr.tesseract_provider.asyncio.wait_for",
        fake_wait_for,
    )

    with pytest.raises(DocumentExtractionError) as exc_info:
        await make_provider().extract_image(make_image())

    assert exc_info.value.code == "DOCUMENT_OCR_TIMEOUT"
    assert process.killed is True
    assert process.waited is True


@pytest.mark.anyio
async def test_health_check_reports_available_languages_and_caches_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, ...]] = []

    async def fake_create_subprocess_exec(*args, **kwargs):  # noqa: ANN001, ARG001
        calls.append(tuple(str(arg) for arg in args))
        if args[1] == "--version":
            return FakeProcess(stdout=b"tesseract 5.3.0\nleptonica")
        return FakeProcess(stdout=b"List of available languages in .\neng\nvie\n")

    monkeypatch.setattr(
        "app.document_processing.ocr.tesseract_provider.asyncio.create_subprocess_exec",
        fake_create_subprocess_exec,
    )
    provider = make_provider()

    first = await provider.health_check()
    second = await provider.health_check()

    assert first.available is True
    assert first.engine == "tesseract"
    assert first.version == "tesseract 5.3.0"
    assert first.languages == ("eng", "vie")
    assert second is first
    assert len(calls) == 2


@pytest.mark.anyio
async def test_health_check_requires_requested_languages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_create_subprocess_exec(*args, **kwargs):  # noqa: ANN001, ARG001
        if args[1] == "--version":
            return FakeProcess(stdout=b"tesseract 5.3.0\n")
        return FakeProcess(stdout=b"List of available languages in .\neng\n")

    monkeypatch.setattr(
        "app.document_processing.ocr.tesseract_provider.asyncio.create_subprocess_exec",
        fake_create_subprocess_exec,
    )

    result = await make_provider().health_check()

    assert result.available is False
    assert result.languages == ("eng",)
