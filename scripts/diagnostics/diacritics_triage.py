"""Rank the one-word cues of diacritics_audit.py by real collisions and by what the code does.

usage (repo root, project venv):
  python scripts/diagnostics/diacritics_triage.py --audit docs/eval/runs/diacritics-audit.md

A collision is real when the corpus PDFs hold at least two accented forms of the cue, each at least
MIN_FORM_COUNT times; forms only in the COMMON_FORMS table are listed apart. A cue is English when
the other words on its line are not Vietnamese syllables. Danger comes from the enclosing function:
answer routes and the validator first, ranking last. Rewrites only the triage section of the report.
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.diagnostics import diacritics_audit as audit  # noqa: E402

MIN_FORM_COUNT = 3
MARKER = "## Lọc tay"
SYLLABLE = re.compile(
    r"^(?:ngh|ch|gh|gi|kh|ng|nh|ph|qu|th|tr|[bcdghklmnprstvx])?"
    r"(?:[aeiouy]{1,3})(?:ch|ng|nh|[cmnptiouy])?$"
)
# Danger by what the enclosing code decides, from most to least direct effect on the answer.
LEVELS = (
    (
        "Cao",
        "tạo câu trả lời",
        lambda f, fn: "grounded_answer_service" in f and fn.startswith("_structured_"),
    ),
    ("Cao", "duyệt câu trả lời", lambda f, fn: "claim_evidence_validation" in f or "citation" in f),
    (
        "Trung bình",
        "phân loại câu hỏi",
        lambda f, fn: "question_analysis" in f or "subclaims" in f or "structured.py" in f,
    ),
    ("Trung bình", "lọc, sửa hoặc thử lại", lambda f, fn: "grounded_answer_service" in f),
    ("Thấp", "xếp hạng hoặc ngữ cảnh", lambda f, fn: True),
)


def corpus_forms() -> dict[str, Counter]:
    from scripts.eval.heldout_check import load_pages

    pages, _ = load_pages()
    counts: dict[str, Counter] = defaultdict(Counter)
    for texts in pages.values():
        for text in texts:
            for word in audit.WORD.findall(text.casefold()):
                counts[audit.fold(word)][word] += 1
    return counts


def enclosing_functions(tree: ast.AST) -> dict[int, str]:
    owner: dict[int, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            for line in range(node.lineno, (node.end_lineno or node.lineno) + 1):
                if line not in owner or owner[line] == "<module>":
                    owner[line] = node.name
    return owner


def english_context(line: str, word: str) -> bool:
    others = [w for w in audit.cue_words(line.casefold()) if w != word and w.isascii()]
    strings = re.findall(r"\"([^\"]+)\"|'([^']+)'", line)
    words = [w for pair in strings for part in pair for w in audit.cue_words(part.casefold())]
    words = [w for w in words if w != word] or others
    return bool(words) and sum(not SYLLABLE.match(w) for w in words) * 2 >= len(words)


def level(file: str, function: str) -> tuple[int, str, str]:
    for rank, (name, what, test) in enumerate(LEVELS):
        if test(file, function):
            return rank, name, what
    return len(LEVELS), "Thấp", ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", type=Path, required=True)
    args = parser.parse_args()
    counts = corpus_forms()
    forms = audit.vocabulary([])
    rows = []
    english = 0
    unseen = 0
    for path in sorted(audit.APP.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        relative = path.relative_to(ROOT).as_posix()
        tree = ast.parse(source)
        owners = enclosing_functions(tree)
        lines = source.splitlines()
        for cue in audit.cues_in(source, relative, forms | {k: set(v) for k, v in counts.items()}):
            if not cue.single_word:
                continue
            word = audit.cue_words(cue.text)[0]
            seen = {form: n for form, n in counts.get(word, Counter()).items() if form != word}
            seen |= {word: counts[word][word]} if counts.get(word, Counter())[word] else {}
            real = {form: n for form, n in seen.items() if n >= MIN_FORM_COUNT}
            if len(real) < 2:
                unseen += 1
                continue
            if english_context(lines[cue.line - 1], word):
                english += 1
                continue
            function = owners.get(cue.line, "<module>")
            rank, name, what = level(relative, function)
            rows.append(
                (rank, -min(real.values()), word, real, relative, cue.line, function, name, what)
            )
    rows.sort()
    grouped: dict[tuple, list] = defaultdict(list)
    for row in rows:
        grouped[(row[0], row[7], row[8], row[2], row[4], row[6])].append(row)
    out = [
        f"{MARKER} (2026-11-08)",
        "",
        f"Lọc bằng `scripts/diagnostics/diacritics_triage.py` trên các cue một từ. "
        f"Giữ {len(rows)} cue có va chạm thật trong corpus: ít nhất 2 dạng có dấu, mỗi dạng "
        f"xuất hiện từ {MIN_FORM_COUNT} lần trong PDF. Loại {unseen} cue không có va chạm như vậy "
        f"trong corpus, và {english} cue nằm giữa các từ tiếng Anh.",
        "",
        "Mức nguy hiểm theo hàm chứa cue: **Cao** nếu cue tạo hoặc duyệt câu trả lời, "
        "**Trung bình** nếu cue phân loại câu hỏi, lọc hoặc quyết định thử lại, **Thấp** nếu "
        "cue chỉ ảnh hưởng xếp hạng hoặc ngữ cảnh. Dạng hiếm nhất càng nhiều lần thì va chạm "
        "càng dễ xảy ra.",
        "",
        "**Đã xác nhận gây lỗi thêm:** `giam` trong `_structured_condition_value_answer` "
        '("giám" khớp "giảm"): REL-103 trả lời sai, và RBD-04, RBD-05 chỉ đúng nhờ lỗi này '
        "(`docs/eval/runs/fix2b-cues.md`).",
        "",
        "| Mức | Việc | Từ | Dạng trong corpus (số lần) | Hàm | Vị trí |",
        "|---|---|---|---|---|---|",
    ]
    for (_, name, what, word, file, function), group in grouped.items():
        real = group[0][3]
        shown = ", ".join(
            f"{form} ({n})" for form, n in sorted(real.items(), key=lambda kv: -kv[1])
        )
        places = ", ".join(f"`{file}:{row[5]}`" for row in group)
        out.append(f"| {name} | {what} | `{word}` | {shown} | `{function}` | {places} |")
    text = args.audit.read_text(encoding="utf-8")
    head = text.split(MARKER)[0].rstrip("\n")
    args.audit.write_text(head + "\n\n" + "\n".join(out) + "\n", encoding="utf-8", newline="\n")
    print(f"kept {len(rows)}; no corpus collision {unseen}; English context {english}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
