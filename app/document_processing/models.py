from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ExtractedPage:
    page_number: int
    text: str = field(repr=False)
    raw_character_count: int
    normalized_character_count: int
    usable_character_count: int

    def __post_init__(self) -> None:
        if self.page_number < 1:
            msg = "page_number must be 1-based."
            raise ValueError(msg)
        counts = (
            self.raw_character_count,
            self.normalized_character_count,
            self.usable_character_count,
        )
        if any(count < 0 for count in counts):
            msg = "character counts must not be negative."
            raise ValueError(msg)
        if self.normalized_character_count != len(self.text):
            msg = "normalized_character_count must match text length."
            raise ValueError(msg)
        if self.usable_character_count > self.normalized_character_count:
            msg = "usable_character_count cannot exceed normalized_character_count."
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    page_count: int
    pages: tuple[ExtractedPage, ...]
    pages_with_usable_text: int
    total_raw_characters: int
    total_normalized_characters: int
    total_usable_characters: int

    def __post_init__(self) -> None:
        pages = tuple(self.pages)
        object.__setattr__(self, "pages", pages)
        if self.page_count != len(pages):
            msg = "page_count must match the number of pages."
            raise ValueError(msg)
        if self.page_count < 0:
            msg = "page_count must not be negative."
            raise ValueError(msg)
        expected_pages_with_text = sum(1 for page in pages if page.usable_character_count > 0)
        if self.pages_with_usable_text != expected_pages_with_text:
            msg = "pages_with_usable_text is inconsistent with page counts."
            raise ValueError(msg)
        if self.total_raw_characters != sum(page.raw_character_count for page in pages):
            msg = "total_raw_characters is inconsistent with page counts."
            raise ValueError(msg)
        if self.total_normalized_characters != sum(
            page.normalized_character_count for page in pages
        ):
            msg = "total_normalized_characters is inconsistent with page counts."
            raise ValueError(msg)
        if self.total_usable_characters != sum(page.usable_character_count for page in pages):
            msg = "total_usable_characters is inconsistent with page counts."
            raise ValueError(msg)
