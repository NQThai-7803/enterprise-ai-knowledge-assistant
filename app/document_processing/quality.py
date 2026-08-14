from __future__ import annotations

import unicodedata
from dataclasses import dataclass

from app.core.config import Settings, get_settings
from app.document_processing.models import ExtractedPage


@dataclass(frozen=True, slots=True)
class TextQualityResult:
    is_usable: bool
    usable_character_count: int
    alnum_ratio: float
    replacement_character_ratio: float
    control_character_ratio: float


@dataclass(frozen=True, slots=True)
class ExtractionQualityEvaluator:
    min_characters_per_page: int
    min_alnum_ratio: float
    max_replacement_character_ratio: float
    max_control_character_ratio: float

    def __post_init__(self) -> None:
        if self.min_characters_per_page < 0:
            msg = "min_characters_per_page must not be negative."
            raise ValueError(msg)
        for value in (
            self.min_alnum_ratio,
            self.max_replacement_character_ratio,
            self.max_control_character_ratio,
        ):
            if not 0.0 <= value <= 1.0:
                msg = "quality ratios must be in [0, 1]."
                raise ValueError(msg)

    def evaluate_page(self, page: ExtractedPage) -> TextQualityResult:
        text = page.text or ""
        non_space = [character for character in text if not character.isspace()]
        denominator = max(1, len(non_space))
        alnum_count = sum(1 for character in non_space if character.isalnum())
        replacement_count = text.count("\ufffd")
        control_count = sum(
            1
            for character in non_space
            if unicodedata.category(character).startswith("C") and character != "\ufffd"
        )
        result = TextQualityResult(
            is_usable=False,
            usable_character_count=page.usable_character_count,
            alnum_ratio=alnum_count / denominator,
            replacement_character_ratio=replacement_count / denominator,
            control_character_ratio=control_count / denominator,
        )
        is_usable = (
            result.usable_character_count >= self.min_characters_per_page
            and result.alnum_ratio >= self.min_alnum_ratio
            and result.replacement_character_ratio <= self.max_replacement_character_ratio
            and result.control_character_ratio <= self.max_control_character_ratio
        )
        return TextQualityResult(
            is_usable=is_usable,
            usable_character_count=result.usable_character_count,
            alnum_ratio=result.alnum_ratio,
            replacement_character_ratio=result.replacement_character_ratio,
            control_character_ratio=result.control_character_ratio,
        )

    def page_has_usable_native_text(self, page: ExtractedPage) -> bool:
        return self.evaluate_page(page).is_usable

    def page_has_usable_ocr_text(self, page: ExtractedPage) -> bool:
        result = self.evaluate_page(page)
        return (
            result.usable_character_count > 0
            and result.alnum_ratio >= self.min_alnum_ratio
            and result.replacement_character_ratio <= self.max_replacement_character_ratio
            and result.control_character_ratio <= self.max_control_character_ratio
        )


def create_extraction_quality_evaluator(
    settings: Settings | None = None,
) -> ExtractionQualityEvaluator:
    resolved_settings = settings or get_settings()
    return ExtractionQualityEvaluator(
        min_characters_per_page=resolved_settings.ocr_native_text_min_characters_per_page,
        min_alnum_ratio=resolved_settings.ocr_native_text_min_alnum_ratio,
        max_replacement_character_ratio=resolved_settings.ocr_max_replacement_character_ratio,
        max_control_character_ratio=resolved_settings.ocr_max_control_character_ratio,
    )
