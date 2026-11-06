"""List every place in app/ that matches on Vietnamese text with its diacritics removed.

usage (repo root, project venv):
  python scripts/diagnostics/diacritics_audit.py --corpus <text file> --output <report.md>

A cue is a string literal in a module that folds text, made only of unaccented ASCII, with at least
one word known to be a folded Vietnamese syllable. Collisions come from Vietnamese text in the repo,
the optional corpus file and the COMMON_FORMS table below, so a missing collision means "not seen",
not "impossible". The report changes nothing; it only lists what to review.
"""

from __future__ import annotations

import argparse
import ast
import re
import unicodedata
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "app"
FOLD_CALLS = {
    "fold_text",
    "_fold_text",
    "_fold_for_person_match",
    "_fold_for_routing",
    "_contains_folded_term",
    "_contains_folded_token",
    "_contains_folded_phrase",
}
WORD = re.compile(r"[^\W\d_]+")
ASCII_CUE = re.compile(r"^[a-z0-9 _\-/.,:;()\[\]\\|?*+^$<>!=%]+$")
# Common words that the repo text may not hold. General Vietnamese, not taken from any question set.
COMMON_FORMS = {
    "ban": ("bạn", "bán", "bản", "bàn", "ban", "bận"),
    "bang": ("bằng", "bảng", "bang", "băng"),
    "bao": ("bao", "báo", "bảo", "bão"),
    "cho": ("cho", "chờ", "chợ", "chó"),
    "chi": ("chi", "chỉ", "chị", "chí"),
    "chuyen": ("chuyển", "chuyến", "chuyện", "chuyên"),
    "co": ("có", "cô", "cơ", "cổ", "cỡ", "cố", "cờ"),
    "con": ("con", "còn", "cơn", "cồn"),
    "cong": ("công", "cộng", "cong", "cổng"),
    "dan": ("dân", "dẫn", "dán", "đan", "đàn", "đạn"),
    "dang": ("đang", "đăng", "đáng", "dạng", "dang", "đằng"),
    "dat": ("đặt", "đạt", "đất", "dạt"),
    "di": ("đi", "dị", "dì", "di"),
    "dich": ("dịch", "đích", "địch"),
    "dien": ("điện", "diện", "điền", "diễn"),
    "dinh": ("định", "đính", "đỉnh", "dính", "đinh"),
    "do": ("do", "đó", "đỏ", "độ", "đồ", "đo", "đổ", "dò"),
    "doi": ("đổi", "đội", "đợi", "đôi", "đời", "đối", "đòi", "dồi"),
    "don": ("đơn", "đón", "dọn", "dồn"),
    "dong": ("đồng", "đóng", "động", "đông", "dòng", "dong", "đống"),
    "du": ("đủ", "dù", "dự", "du", "dư", "đu"),
    "duoc": ("được", "dược"),
    "duong": ("đường", "dương", "dưỡng", "đương"),
    "gia": ("giá", "gia", "già", "giả"),
    "giao": ("giao", "giáo"),
    "gio": ("giờ", "gió", "giỗ"),
    "hai": ("hai", "hải", "hại", "hài"),
    "han": ("hạn", "hàn", "hán", "hân"),
    "hoc": ("học", "hộc"),
    "ky": ("kỳ", "ký", "kỹ", "kỷ", "kỵ"),
    "lan": ("lần", "lan", "lân", "lãn", "lặn"),
    "lam": ("làm", "lâm", "lắm", "lạm", "lam"),
    "le": ("lễ", "lệ", "lẻ", "le", "lê"),
    "loi": ("lỗi", "lợi", "lời", "lối", "lội"),
    "luong": ("lương", "lượng", "lường"),
    "ma": ("mã", "mà", "ma", "mả", "má", "mạ"),
    "mat": ("mất", "mật", "mặt", "mát", "mắt"),
    "may": ("máy", "mấy", "may", "mây", "mày"),
    "mo": ("mở", "mô", "mơ", "mổ", "mộ", "mỏ"),
    "moi": ("mỗi", "mới", "mọi", "môi", "mời", "mối"),
    "muc": ("mục", "mức", "múc", "mực"),
    "nam": ("năm", "nam", "nằm", "nấm", "nắm"),
    "ngay": ("ngày", "ngay", "ngây"),
    "nghi": ("nghỉ", "nghi", "nghĩ", "nghị"),
    "neu": ("nếu", "nêu"),
    "nhan": ("nhận", "nhân", "nhắn", "nhãn", "nhẫn", "nhấn"),
    "nho": ("nhỏ", "nhớ", "nhờ", "nho"),
    "phan": ("phần", "phân", "phản", "phán", "phan"),
    "phi": ("phí", "phi"),
    "phong": ("phòng", "phong", "phỏng", "phóng"),
    "quan": ("quan", "quản", "quận", "quân", "quán", "quần"),
    "quy": ("quy", "quý", "quỹ", "quỳ"),
    "sau": ("sau", "sáu", "sâu"),
    "so": ("số", "so", "sổ", "sở", "sợ", "sơ"),
    "tai": ("tại", "tài", "tải", "tai", "tái"),
    "tan": ("tấn", "tân", "tan", "tận", "tần"),
    "tang": ("tăng", "tầng", "tặng", "tang", "tảng"),
    "tam": ("tạm", "tám", "tâm", "tấm", "tắm"),
    "thang": ("tháng", "thẳng", "thang", "thắng", "thăng"),
    "thi": ("thì", "thi", "thị", "thí"),
    "tho": ("thợ", "thơ", "thở", "thổ"),
    "thu": ("thu", "thứ", "thử", "thư", "thủ", "thú"),
    "thuc": ("thực", "thức", "thúc", "thục"),
    "tien": ("tiền", "tiến", "tiên", "tiện"),
    "tin": ("tin", "tín"),
    "toi": ("tôi", "tối", "tới", "tội", "tỏi"),
    "tu": ("từ", "tự", "tư", "tu", "tủ", "tử", "tứ"),
    "tuan": ("tuần", "tuân", "tuấn"),
    "vien": ("viên", "viện", "viền"),
    "viet": ("viết", "việt"),
}


@dataclass(frozen=True)
class Cue:
    file: str
    line: int
    text: str
    collisions: tuple[tuple[str, tuple[str, ...]], ...]

    @property
    def single_word(self) -> bool:
        return len(cue_words(self.text)) == 1


def cue_words(text: str) -> list[str]:
    """Words of a literal, ignoring regex escapes such as the b of a word boundary."""
    return [word for word in WORD.findall(re.sub(r"\\[a-zA-Z]", " ", text)) if len(word) >= 2]


def fold(text: str) -> str:
    stripped = "".join(
        ch
        for ch in unicodedata.normalize("NFD", text.replace("đ", "d").replace("Đ", "D"))
        if unicodedata.category(ch) != "Mn"
    )
    return stripped.casefold()


def vocabulary(texts: Iterable[str]) -> dict[str, set[str]]:
    """Map each folded syllable to the accented forms seen for it, plus COMMON_FORMS."""
    forms: dict[str, set[str]] = defaultdict(set)
    for text in texts:
        for word in WORD.findall(unicodedata.normalize("NFC", text).casefold()):
            folded = fold(word)
            if folded != word:
                forms[folded].add(word)
    for folded, words in COMMON_FORMS.items():
        forms[folded].update(word for word in words if fold(word) == folded)
    return forms


def _docstring_lines(tree: ast.AST) -> set[int]:
    lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            first = node.body[0] if node.body else None
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                lines.add(first.value.lineno)
    return lines


def _folds_text(source: str, tree: ast.AST) -> bool:
    if "unicodedata.normalize" in source and "NFKD" in source:
        return True
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in FOLD_CALLS:
            return True
        if isinstance(node, ast.alias) and node.name in FOLD_CALLS:
            return True
    return False


def cues_in(source: str, file: str, forms: dict[str, set[str]]) -> list[Cue]:
    tree = ast.parse(source)
    if not _folds_text(source, tree):
        return []
    docstrings = _docstring_lines(tree)
    found: list[Cue] = []
    seen: set[tuple[int, str]] = set()
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
            continue
        text = node.value
        if node.lineno in docstrings or not text.strip() or not ASCII_CUE.match(text):
            continue
        words = cue_words(text)
        if not any(word in forms for word in words) or (node.lineno, text) in seen:
            continue
        seen.add((node.lineno, text))
        collisions = tuple(
            (word, tuple(sorted(forms[word])))
            for word in dict.fromkeys(words)
            if len(forms.get(word, ())) >= 2
        )
        found.append(Cue(file, node.lineno, text, collisions))
    return found


def render(cues: list[Cue], fold_sites: list[str]) -> str:
    risky = [cue for cue in cues if cue.single_word and cue.collisions]
    by_word: dict[str, list[Cue]] = defaultdict(list)
    for cue in risky:
        by_word[cue.collisions[0][0]].append(cue)
    lines = [
        "# Rà soát so khớp trên text tiếng Việt đã bỏ dấu",
        "",
        "Chỉ báo cáo, không sửa. Sinh bởi `scripts/diagnostics/diacritics_audit.py`.",
        "",
        f"- **Số cue:** {len(cues)}, trong đó {sum(bool(c.collisions) for c in cues)} có từ có thể "
        f"va chạm, và {len(risky)} cue chỉ gồm một từ có thể va chạm (rủi ro cao nhất).",
        "- **Cue** là chuỗi trong file có bỏ dấu, chỉ gồm ký tự không dấu và có ít nhất một từ "
        "tiếng Việt đã biết. Chuỗi không phải để so khớp vẫn có thể lọt vào danh sách.",
        "- **Va chạm** lấy từ văn bản tiếng Việt trong repo, phần đầu các chunk UAT đã trace "
        "và "
        'bảng `COMMON_FORMS`. Không có va chạm nghĩa là "chưa thấy", không phải "không thể".',
        "- **Nhiễu:** vài cue là từ tiếng Anh trùng chữ, như `the`, `day`, `no`. "
        "Danh sách chưa được "
        "lọc tay, nên cần đọc code tại từng vị trí trước khi kết luận.",
        "",
        "## Đã xác nhận gây lỗi",
        "",
        '- `dong` trong `_asks_for_amount`: "đồng ý" bị hiểu là tiền (HO-023, REL-201, REL-204). '
        "Đã có cách sửa sau `RAG_ANSWER_UNIT_GUARD_ENABLED`.",
        '- `neu `: khớp "nêu" như "nếu" trong route `legacy` (HO-026). '
        "`strict` so khớp cả từ có dấu.",
        '- `chua du`: khớp một phần "chưa dùng" trong route `legacy` (HO-020). '
        "`strict` so khớp cả từ.",
        "",
        "## Nơi bỏ dấu",
        "",
        *[f"- `{site}`" for site in fold_sites],
        "",
        "## Rủi ro cao: cue chỉ có một từ",
        "",
        "| Từ | Có thể là | Số chỗ | Vị trí |",
        "|---|---|---:|---|",
    ]
    for word, group in sorted(by_word.items(), key=lambda row: (-len(row[1]), row[0])):
        places = ", ".join(f"`{cue.file}:{cue.line}`" for cue in group)
        readings = ", ".join(group[0].collisions[0][1])
        lines.append(f"| `{word}` | {readings} | {len(group)} | {places} |")
    by_file: dict[str, list[Cue]] = defaultdict(list)
    for cue in cues:
        by_file[cue.file].append(cue)
    lines += ["", "## Toàn bộ cue theo file", ""]
    for file, group in sorted(by_file.items()):
        lines += [
            f"### `{file}` ({len(group)})",
            "",
            "| Dòng | Cue | Từ có thể va chạm |",
            "|---:|---|---|",
        ]
        for cue in sorted(group, key=lambda item: item.line):
            shown = cue.text.replace("|", "\\|").replace("`", "'")
            words = "; ".join(f"{word}: {', '.join(forms)}" for word, forms in cue.collisions)
            lines.append(f"| {cue.line} | `{shown}` | {words or '-'} |")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    texts = [args.corpus.read_text(encoding="utf-8")] if args.corpus else []
    for pattern in ("*.md", "docs/**/*.md", "docs/eval/*.yaml", "tests/acceptance/*.yaml"):
        for path in ROOT.glob(pattern):
            texts.append(path.read_text(encoding="utf-8", errors="ignore"))
    forms = vocabulary(texts)
    cues: list[Cue] = []
    fold_sites: list[str] = []
    for path in sorted(APP.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        relative = path.relative_to(ROOT).as_posix()
        for number, line in enumerate(source.splitlines(), start=1):
            if re.search(r'def \w*fold\w*\(|normalize\(\s*"NFK?D"', line):
                fold_sites.append(f"{relative}:{number}")
        cues += cues_in(source, relative, forms)
    args.output.write_text(render(cues, fold_sites), encoding="utf-8", newline="\n")
    print(f"cues: {len(cues)}; with collisions: {sum(bool(cue.collisions) for cue in cues)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
