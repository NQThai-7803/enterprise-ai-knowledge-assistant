"""DEC-032 value-aware grading, on examples written for these tests (no set item)."""

from __future__ import annotations

import pytest

from scripts.diagnostics.summarize_ablation import UAT, categories
from scripts.eval import value_grading
from scripts.eval.value_grading import check, says, values


@pytest.mark.parametrize(
    ("left", "right"),
    [
        ("trong 02 ngày", "trong 2 ngày"),
        ("mức 1.500.000 đ", "1,5 triệu đồng"),
        ("lúc 9h30", "lúc 09:30"),
        ("ba tuần", "3 tuần"),
        ("ngày 05/03/2027", "ngày 5/3/2027"),
        ("30 phần trăm", "30%"),
    ],
)
def test_a_value_written_two_ways_is_one_value(left: str, right: str) -> None:
    assert values(left) == values(right)


def test_markers_codes_articles_and_list_numbers_are_not_values() -> None:
    text = "1. Theo Điều 7 của ND-AB-012, bậc N4 [SOURCE_2] [3] được 650.000 đồng ở mức này"
    assert values(text) == (("650000", "dong"),)


def test_a_level_written_muc_keeps_its_amount() -> None:
    assert values("hạn mức 40 triệu đồng") == (("40000000", "dong"),)
    assert values("xem mục 4.2") == ()


def test_wrong_number_is_missing_and_conflicting() -> None:
    result = check("Cần báo trước 7 ngày làm việc [1].", "Báo trước ít nhất 04 ngày làm việc.")
    assert result["missing"] == [("4", "ngay")]
    assert result["conflicting"] == [("7", "ngay")]
    assert not result["ok"]


def test_scale_mix_up_is_wrong() -> None:
    result = check("Tối đa 25 triệu đồng mỗi lần.", "Giá trị là 2,5 trieu dong/lan.")
    assert result["missing"] == [("2500000", "dong")]
    assert result["conflicting"] == [("25000000", "dong")]


def test_a_value_the_question_holds_is_still_required() -> None:
    question = "Đi công tác 3 ngày thì nộp báo cáo trong mấy ngày?"
    assert not check("Nộp trong 5 ngày.", "Nộp trong 3 ngày.", question)["ok"]
    assert check("Nộp trong 03 ngày.", "Nộp trong 3 ngày.", question)["ok"]


def test_question_value_is_no_conflict() -> None:
    question = "Đi công tác 3 ngày thì nộp báo cáo trong mấy ngày?"
    assert check("Chuyến 3 ngày nộp trong 5 ngày.", "Nộp trong 5 ngày.", question)["ok"]


def test_threshold_is_no_conflict_but_another_value_is() -> None:
    reference = "Đăng ký trước 12 ngày."
    assert check("Chuyến đi từ 04 ngày trở lên cần đăng ký trước 12 ngày.", reference)["ok"]
    assert check("Chuyến đi trên 4 ngày cần đăng ký trước 12 ngày.", reference)["ok"]
    assert not check("Đăng ký trước 12 ngày, hoặc 9 ngày nếu gấp.", reference)["ok"]


def test_clock_times() -> None:
    reference = "Ca chiều kết thúc lúc 16:45."
    assert check("Kết thúc 16h45 [1].", reference)["ok"]
    assert not check("Kết thúc lúc 17:15.", reference)["ok"]
    assert check("Về lúc 18 giờ.", "Kết thúc khoảng 18:00.")["ok"]


def test_range_with_one_scale_word() -> None:
    assert check("Từ 4 triệu đến 9 triệu đồng.", "Khoảng 4 - 9 triệu đồng.")["ok"]


def test_a_unit_missing_on_one_side_still_matches() -> None:
    assert check("Chi vào ngày 15 mỗi tháng.", "Ngày 15 hằng tháng.")["ok"]
    assert check("Được 10 ngày.", "Tối đa 10.")["ok"]


def test_a_reference_without_values_requires_none() -> None:
    assert check("Người duyệt là trưởng nhóm, trong 2 ngày.", "Trưởng nhóm duyệt.")["ok"]


def test_says_keeps_digits_apart() -> None:
    assert says("1 lần", "được 1 lần mỗi năm")
    assert not says("1 lần", "được 11 lần mỗi năm")
    assert not says("7 ngày", "trong 17 ngày")


def test_uat_regrade_gates_proxy_match() -> None:
    def case(answer: str, match: bool | None, status: str = "ANSWERED") -> dict:
        return {
            "id": "X1",
            "question": "Phụ cấp đi lại là bao nhiêu?",
            "answer": answer,
            "reference_answer": "Giá trị là 450.000 d/thang. [1]",
            "reference_status": status,
            "grounding_status": "ANSWERED",
            "proxy_match": match,
        }

    right, wrong, infra = value_grading.regrade(
        "uat",
        {
            "cases": [
                case("450.000 đồng/tháng [1].", True),
                case("45.000 đồng [1].", True),
                case("", None),
            ]
        },  # fmt: skip
    )["cases"]
    assert (right["value_match"], wrong["value_match"], infra["value_match"]) == (True, False, None)
    assert categories(UAT, {"cases": [right, wrong]}) == {"X1": "wrong"}  # same id: last wins
    assert categories(UAT, {"cases": [right]}) == {"X1": "correct"}
    old = {key: value for key, value in wrong.items() if key not in ("value_match", "values")}
    assert categories(UAT, {"cases": [old]}) == {"X1": "correct"}  # graded before DEC-032


def test_dev_set_regrade_adds_the_conflict_check_and_is_idempotent(monkeypatch) -> None:
    item = {"id": "S1", "expect": "answer", "question": "Phải nộp trong mấy ngày?",
            "fact": "6 ngày", "fact_alternatives": ["06 ngày", "sáu ngày"]}  # fmt: skip
    monkeypatch.setattr(value_grading, "_yaml", lambda name: {"items": [item]})
    results = {
        "cases": [
            {"id": "S1", "answer": "Nộp trong 6 ngày, có thể 8 ngày.", "passed": True},
        ]
    }
    once = value_grading.regrade("relevance", results)
    twice = value_grading.regrade("relevance", once)
    for graded in (once, twice):
        (row,) = graded["cases"]
        assert row["passed"] is False
        assert row["passed_before_values"] is True
        assert row["values"]["conflicting"] == [("8", "ngay")]
