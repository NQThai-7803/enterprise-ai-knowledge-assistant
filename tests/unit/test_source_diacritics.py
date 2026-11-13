"""D2: server-built answers show copied values with the diacritics of the cited source."""

from __future__ import annotations

import json
import unicodedata
from uuid import uuid4

import pytest

from app.citations.models import PromptSource, PromptSourceRegistry
from app.core.config import Settings
from app.models import CitationSourceType
from app.services import grounded_answer_service as service
from app.services.grounded_answer_service import _restore_source_diacritics

SOURCE = (
    "Điều 4. Nhân viên kho được cấp 750.000 đ/tháng tiền độc hại.\n"
    "Yêu cầu đổi ca phải gửi trước ít nhất 03 ngày làm việc.\n"
    "Người chưa đủ 6 tháng làm việc được tính theo tỷ lệ tương ứng."
)


def test_unaccented_values_take_the_source_spelling() -> None:
    assert (
        _restore_source_diacritics("Giá trị là 750.000 d/thang.", [SOURCE])
        == "Giá trị là 750.000 đ/tháng."
    )
    assert (
        _restore_source_diacritics("Cần báo trước ít nhất 03 ngay lam viec.", [SOURCE])
        == "Cần báo trước ít nhất 03 ngày làm việc."
    )


def test_the_answer_keeps_its_own_capitalisation() -> None:
    assert (
        _restore_source_diacritics("Chua du 6 thang: tinh theo ty le tuong ung.", [SOURCE])
        == "Chưa đủ 6 tháng: tính theo tỷ lệ tương ứng."
    )


def test_decomposed_source_text_is_restored_whole() -> None:
    decomposed = unicodedata.normalize("NFD", SOURCE)
    assert (
        _restore_source_diacritics("Giá trị là 750.000 d/thang.", [decomposed])
        == "Giá trị là 750.000 đ/tháng."
    )


def test_ambiguous_or_absent_words_are_left_alone() -> None:
    sources = ["Phụ cấp năm 2026 cho nhân viên Nam Định.", "Ca trực kéo dài 2 giờ."]
    # "nam" is "năm" in one place and "Nam" in another: the answer keeps "nam".
    assert _restore_source_diacritics("Áp dụng nam 2027.", sources) == "Áp dụng nam 2027."
    assert _restore_source_diacritics("Thời lượng là 2 gio.", sources) == "Thời lượng là 2 giờ."
    assert _restore_source_diacritics("Thời lượng là 5 phut.", sources) == "Thời lượng là 5 phut."
    assert _restore_source_diacritics("Không.", []) == "Không."


@pytest.mark.parametrize(("flag", "expected"), [(True, "45 giờ/tuần"), (False, "45 gio/tuan")])
def test_value_repair_answer_follows_the_flag(
    flag: bool, expected: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        service,
        "get_settings",
        lambda: Settings(_env_file=None, rag_restore_source_diacritics_enabled=flag),
    )
    registry = PromptSourceRegistry(
        sources=(
            PromptSource(
                marker="[SOURCE_1]",
                source_type=CitationSourceType.INTERNAL,
                document_title="Nội quy xưởng",
                text="Ca hành chính 09 giờ/ngày; 45 giờ/tuần.",
                page_numbers=(1,),
                start_page=1,
                end_page=1,
                hybrid_score=1.0,
                chunk_id=uuid4(),
                document_id=uuid4(),
            ),
        )
    )
    generation = service._structured_value_repair_generation(
        question="Một tuần bình thường làm bao nhiêu tiếng?", source_registry=registry
    )
    assert generation is not None
    assert expected in json.loads(generation.content)["answer"]
