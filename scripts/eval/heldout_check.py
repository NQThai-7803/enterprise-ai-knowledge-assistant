"""Check docs/eval/heldout-v1.yaml and render the owner review file. Never runs the RAG system.

usage (repo root, project venv):
  python scripts/eval/heldout_check.py check [--e5-scores scores.json]
  python scripts/eval/heldout_check.py e5-input out.json      # questions for the cosine step
  python scripts/eval/heldout_check.py e5 in.json out.json    # where the embedding model is cached

check:
- schema, ids, group counts (design section 4) and pair consistency;
- source PDFs: SHA256 against uat/corpus-v2/manifest.json, then every source_excerpt must appear
  verbatim (whitespace-normalized) on the stated page;
- absent_keywords: hit count in the documents the asking role can see (REVIEW flag only);
- acceptable_status ANSWERED_LIMITED needs limited_pass criteria and fail_examples;
- source_images must exist next to the review file;
- duplicates against Q001-Q100: character 3-gram Jaccard and difflib ratio on diacritic-folded
  text (>= 0.60 means rewrite), plus the multilingual-e5-small cosine from --e5-scores
  (>= 0.90 means REVIEW, never an automatic rejection);
- word 4-grams of every held-out question searched in app/ (must not be hard-coded);
- writes docs/eval/heldout-v1-review.md and docs/eval/heldout-v1-check.json.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import runpy
import sys
import unicodedata
from collections import Counter
from pathlib import Path

_HERE = Path(__file__).resolve()
# The e5 command also runs from a bare copy of this file inside a container.
ROOT = _HERE.parents[2] if len(_HERE.parents) > 2 else _HERE.parent
HELDOUT = ROOT / "docs" / "eval" / "heldout-v1.yaml"
REVIEW = ROOT / "docs" / "eval" / "heldout-v1-review.md"
REPORT = ROOT / "docs" / "eval" / "heldout-v1-check.json"
MANIFEST = ROOT / "uat" / "corpus-v2" / "manifest.json"
UAT_QUESTIONS = ROOT / "artifacts" / "rag-h5-1-stress-uat.py"

GROUP_COUNTS = {"A": 7, "B": 2, "C": 4, "D": 4, "E": 7, "F": 6, "G": 4, "H": 4, "I": 2}
ROLES = {"staff", "manager", "admin"}
STATUSES = {"ANSWERED", "NO_ANSWER", "ANSWERED_LIMITED"}
RESTRICTED = {"UAT-GROUNDING-001"}
VISIBLE = {"staff": "org", "manager": "all", "admin": "all"}
SURFACE_THRESHOLD = 0.60
E5_THRESHOLD = 0.90


def normalize_space(text: str) -> str:
    # PDF bullets come out as private-use glyphs (U+F0B7); treat them as spaces.
    text = "".join(" " if unicodedata.category(ch) == "Co" else ch for ch in text)
    return " ".join(unicodedata.normalize("NFC", text).split())


def fold(text: str) -> str:
    text = unicodedata.normalize("NFD", text.casefold()).replace("đ", "d")
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return " ".join(re.sub(r"[^\w]+", " ", text).split())


def trigrams(text: str) -> set[str]:
    padded = f"  {text} "
    return {padded[i : i + 3] for i in range(len(padded) - 2)}


def jaccard(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if a | b else 0.0


def load_items() -> list[dict]:
    import yaml

    return yaml.safe_load(HELDOUT.read_text(encoding="utf-8"))["items"]


def load_uat() -> dict[str, str]:
    return {row[0]: row[2] for row in runpy.run_path(str(UAT_QUESTIONS))["CORE"]}


def load_pages() -> tuple[dict[str, list[str]], list[str]]:
    import pymupdf

    problems: list[str] = []
    pages: dict[str, list[str]] = {}
    for doc in json.loads(MANIFEST.read_text(encoding="utf-8-sig"))["documents"]:
        data = (ROOT / doc["source"]).read_bytes()
        if hashlib.sha256(data).hexdigest() != doc["sha256"]:
            problems.append(f"{doc['code']}: SHA256 differs from the manifest")
        with pymupdf.open(stream=data, filetype="pdf") as pdf:
            pages[doc["code"]] = [normalize_space(page.get_text()) for page in pdf]
    return pages, problems


def check_schema(items: list[dict]) -> list[str]:
    problems = []
    ids = [item["id"] for item in items]
    if len(set(ids)) != len(ids):
        problems.append("duplicate ids")
    counts = Counter(item["group"] for item in items)
    if dict(counts) != GROUP_COUNTS:
        problems.append(f"group counts {dict(counts)} != design {GROUP_COUNTS}")
    for item in items:
        where = item["id"]
        if item["role"] not in ROLES:
            problems.append(f"{where}: unknown role")
        if item["gold_status"] not in STATUSES:
            problems.append(f"{where}: bad gold_status")
        acceptable = item.get("acceptable_status", [])
        if not set(acceptable) <= STATUSES - {item["gold_status"]}:
            problems.append(f"{where}: bad acceptable_status")
        if "ANSWERED_LIMITED" in acceptable and not (
            item.get("limited_pass") and item.get("fail_examples")
        ):
            problems.append(f"{where}: ANSWERED_LIMITED needs limited_pass and fail_examples")
        for image in item.get("source_images", []):
            if not (REVIEW.parent / image["path"]).is_file():
                problems.append(f"{where}: missing image {image['path']}")
        if item["language"] not in {"vi", "en"}:
            problems.append(f"{where}: bad language")
        answered = item["gold_status"] == "ANSWERED"
        if answered != bool(item["gold_answer"]) or answered != bool(item["gold_citations"]):
            problems.append(f"{where}: gold_answer/gold_citations do not match gold_status")
        cited = {c["document"] for c in item["gold_citations"]}
        if VISIBLE[item["role"]] == "org" and cited & RESTRICTED:
            problems.append(f"{where}: {item['role']} gold cites a restricted document")
        if VISIBLE[item["role"]] == "org" and not item["forbidden"]:
            problems.append(f"{where}: staff item without forbidden list")
        blob = " ".join(item["gold_answer"] + item.get("gold_optional", [])).casefold()
        for entry in item["forbidden"]:
            if entry["value"].casefold() in blob:
                problems.append(f"{where}: gold contains forbidden {entry['value']!r}")
    pairs: dict[str, list[dict]] = {}
    for item in items:
        if item["pair_id"]:
            pairs.setdefault(item["pair_id"], []).append(item)
    for pair_id, members in pairs.items():
        if len(members) != 2 or len({m["question"] for m in members}) != 1:
            problems.append(f"{pair_id}: a pair needs 2 items with the same question")
        if len({m["role"] for m in members}) != 2:
            problems.append(f"{pair_id}: a pair needs 2 different roles")
    return problems


def check_excerpts(items: list[dict], pages: dict[str, list[str]]) -> dict[str, list[dict]]:
    results: dict[str, list[dict]] = {}
    for item in items:
        rows = []
        for excerpt in item["source_excerpt"]:
            doc_pages = pages.get(excerpt["document"], [])
            page = excerpt["page"]
            text = doc_pages[page - 1] if 0 < page <= len(doc_pages) else ""
            rows.append({**excerpt, "verified": normalize_space(excerpt["text"]) in text})
        results[item["id"]] = rows
    return results


def check_absent(items: list[dict], pages: dict[str, list[str]]) -> dict[str, dict[str, int]]:
    results = {}
    for item in items:
        visible = [
            code for code in pages if VISIBLE[item["role"]] == "all" or code not in RESTRICTED
        ]
        corpus = fold(" ".join(" ".join(pages[code]) for code in visible))
        results[item["id"]] = {
            keyword: corpus.count(fold(keyword)) for keyword in item.get("absent_keywords", [])
        }
    return results


def surface_duplicates(items: list[dict], uat: dict[str, str]) -> dict[str, dict]:
    folded_uat = {case_id: fold(q) for case_id, q in uat.items()}
    grams_uat = {case_id: trigrams(q) for case_id, q in folded_uat.items()}
    results = {}
    for item in items:
        question = fold(item["question"])
        grams = trigrams(question)
        best_j = max(folded_uat, key=lambda c: jaccard(grams, grams_uat[c]))
        best_s = max(
            folded_uat,
            key=lambda c: difflib.SequenceMatcher(None, question, folded_uat[c]).ratio(),
        )
        score_j = jaccard(grams, grams_uat[best_j])
        score_s = difflib.SequenceMatcher(None, question, folded_uat[best_s]).ratio()
        results[item["id"]] = {
            "trigram_max": round(score_j, 3),
            "trigram_nearest": best_j,
            "seqmatch_max": round(score_s, 3),
            "seqmatch_nearest": best_s,
            "rewrite": max(score_j, score_s) >= SURFACE_THRESHOLD,
        }
    return results


def app_fourgram_hits(items: list[dict]) -> dict[str, list[str]]:
    from app.retrieval.question_analysis import fold_text

    source = "\n".join(
        path.read_text(encoding="utf-8", errors="replace") for path in (ROOT / "app").rglob("*.py")
    )
    decoded = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), source)
    folded = fold_text(decoded)
    hits = {}
    for item in items:
        words = re.findall(r"\w+", fold_text(item["question"]))
        grams = [" ".join(words[i : i + 4]) for i in range(len(words) - 3)]
        found = sorted({gram for gram in grams if gram in folded})
        if found:
            hits[item["id"]] = found
    return hits


def e5_scores(in_path: str, out_path: str) -> None:
    from sentence_transformers import SentenceTransformer

    data = json.loads(Path(in_path).read_text(encoding="utf-8"))
    model = SentenceTransformer("intfloat/multilingual-e5-small", device="cpu")
    held_ids, uat_ids = list(data["heldout"]), list(data["uat"])

    def embed(texts: list[str]):
        return model.encode(
            [f"query: {t}" for t in texts], normalize_embeddings=True, batch_size=16
        )

    held = embed([data["heldout"][i] for i in held_ids])
    ref = embed([data["uat"][i] for i in uat_ids])
    sims = held @ ref.T
    out = {}
    for row, item_id in enumerate(held_ids):
        col = int(sims[row].argmax())
        out[item_id] = {"cosine_max": round(float(sims[row][col]), 4), "nearest": uat_ids[col]}
    Path(out_path).write_text(json.dumps(out, indent=1), encoding="utf-8")


def render_review(items, uat, excerpts, absent, dupes, e5, app_hits, problems) -> str:
    lines = [
        "# Held-out v1: gold review (owner)",
        "",
        "Status: **DRAFT, waiting for the owner's final review (PROMPT 4 item 2).** Generated by",
        "`scripts/eval/heldout_check.py check` from `docs/eval/heldout-v1.yaml`; do not edit by",
        "hand, edit the YAML and regenerate. Gold was written from the source PDFs only, without",
        "running the system. Every excerpt below was matched verbatim against the PDF text of the",
        "stated page (column 'verified').",
        "",
        "Groups B and C are **RBAC smoke-level**: the corpus has one restricted document",
        "(UAT-GROUNDING-001, about 100 characters, text cut mid-word) and manager and admin see",
        "the same documents.",
        "",
        "Grading rules (design section 7): `ANSWERED_LIMITED` passes only when the answer (a) says",
        "the asked information is not in the documents, (b) adds no number or fact from outside",
        "the documents, (c) cites the related passage, if it cites. Forbidden strings and absent",
        "keywords only raise a REVIEW flag; the grader assigns LEAK when the answer confirms the",
        "existence, the name (beyond repeating the asker's words) or the content of a document",
        "the role cannot see.",
        "",
        "How to review: for every item tick **DUYỆT**, or tick **SỬA** and write the change.",
        "",
        "## Checks",
        "",
        f"- Schema, group counts and pairs: {'OK' if not problems else '; '.join(problems)}",
        f"- Excerpts verified on the stated page: "
        f"{sum(r['verified'] for rows in excerpts.values() for r in rows)}"
        f"/{sum(len(rows) for rows in excerpts.values())}",
        f"- Surface duplicates >= {SURFACE_THRESHOLD} (rewrite): "
        f"{[i for i, d in dupes.items() if d['rewrite']] or 'none'}",
        f"- e5 cosine >= {E5_THRESHOLD} (REVIEW): "
        + (
            str([i for i, d in e5.items() if d["cosine_max"] >= E5_THRESHOLD] or "none")
            if e5
            else "NOT RUN"
        ),
        f"- Held-out 4-grams found in app/: {app_hits or 'none'}",
    ]
    if e5:
        maxima = sorted(d["cosine_max"] for d in e5.values())
        lines.append(
            f"- e5 context: the max cosine of each held-out question to Q001-Q100 ranges "
            f"{maxima[0]} to {maxima[-1]} (median {maxima[len(maxima) // 2]}); e5-small "
            "scores even unrelated Vietnamese HR questions above 0.75, so REVIEW means "
            "'look at the nearest UAT question', not 'duplicate'."
        )
    lines += [
        "",
        "| id | group | role | status | 3-gram max (UAT) | difflib max (UAT) | e5 cosine (UAT) |",
        "|---|---|---|---|---|---|---|",
    ]
    for item in items:
        d = dupes[item["id"]]
        e = e5.get(item["id"]) if e5 else None
        e_cell = (
            f"{e['cosine_max']} ({e['nearest']})"
            + (" **REVIEW**" if e["cosine_max"] >= E5_THRESHOLD else "")
            if e
            else "n/a"
        )
        lines.append(
            f"| {item['id']} | {item['group']} | {item['role']} | {item['gold_status']} | "
            f"{d['trigram_max']} ({d['trigram_nearest']}) | {d['seqmatch_max']} "
            f"({d['seqmatch_nearest']}) | {e_cell} |"
        )
    for item in items:
        d = dupes[item["id"]]
        e = e5.get(item["id"]) if e5 else None
        nearest = e["nearest"] if e else d["trigram_nearest"]
        lines += [
            "",
            "---",
            "",
            f"## {item['id']} | group {item['group']} | role `{item['role']}`"
            + (f" | pair `{item['pair_id']}`" if item["pair_id"] else ""),
            "",
            f"**Question** ({item['language']}): {item['question']}",
            "",
            f"**gold_status:** `{item['gold_status']}`"
            + (
                " | acceptable: " + ", ".join(f"`{x}`" for x in item["acceptable_status"])
                if item.get("acceptable_status")
                else ""
            ),
            "",
        ]
        if item.get("limited_pass"):
            lines.append("**ANSWERED_LIMITED passes when all hold:**")
            lines += [f"- {point}" for point in item["limited_pass"]]
            lines.append("")
        if item.get("fail_examples"):
            lines.append("**FAIL examples:**")
            lines += [f"- {point}" for point in item["fail_examples"]]
            lines.append("")
        if item.get("leak_examples"):
            lines.append("**LEAK examples (grader decides):**")
            lines += [f"- {point}" for point in item["leak_examples"]]
            lines.append("")
        if item["gold_answer"]:
            lines.append("**Required points (gold_answer):**")
            lines += [f"{n}. {point}" for n, point in enumerate(item["gold_answer"], 1)]
            lines.append("")
        if item.get("gold_optional"):
            lines.append("**Optional points (not required for PASS):**")
            lines += [f"- {point}" for point in item["gold_optional"]]
            lines.append("")
        if item["gold_citations"]:
            cites = ", ".join(
                f"{c['document']} p.{','.join(map(str, c['pages']))}"
                for c in item["gold_citations"]
            )
            lines += [f"**gold_citations:** {cites}", ""]
        if item["acceptable_extra_citations"]:
            extra = ", ".join(
                f"{c['document']} p.{','.join(map(str, c['pages']))}"
                for c in item["acceptable_extra_citations"]
            )
            lines += [f"**Acceptable extra citations:** {extra}", ""]
        if item["forbidden"]:
            lines += [
                "**Forbidden strings (REVIEW flag if present; the grader assigns LEAK):** "
                + ", ".join(f"{f['type']}: `{f['value']}`" for f in item["forbidden"]),
                "",
            ]
        lines.append("**Source excerpts (verbatim from the PDF):**")
        if excerpts[item["id"]]:
            for row in excerpts[item["id"]]:
                mark = "verified" if row["verified"] else "**NOT FOUND ON THIS PAGE**"
                lines.append(f"> **{row['document']}, page {row['page']}** ({mark})  ")
                lines.append(f"> {row['text']}")
                lines.append(">")
            lines.pop()
        else:
            lines.append("> (none: no document of the corpus covers this question)")
        for image in item.get("source_images", []):
            lines += ["", f"![{image['caption']}]({image['path']})", f"*{image['caption']}*"]
        if absent[item["id"]]:
            lines += [
                "",
                "**Keywords searched in the documents this role can see (hits; REVIEW flag "
                "only):** " + ", ".join(f"`{k}`: {v}" for k, v in absent[item["id"]].items()),
            ]
        lines += [
            "",
            f"**Nearest UAT question:** {nearest}: {uat[nearest]}  ",
            f"3-gram {d['trigram_max']}, difflib {d['seqmatch_max']}"
            + (f", e5 cosine {e['cosine_max']}" if e else "")
            + (" — **REVIEW** (e5 >= 0.90)" if e and e["cosine_max"] >= E5_THRESHOLD else ""),
        ]
        if item.get("notes"):
            lines += ["", f"**Notes:** {item['notes']}"]
        lines += ["", "- [ ] DUYỆT", "- [ ] SỬA: "]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check")
    check.add_argument("--e5-scores")
    sub.add_parser("e5-input").add_argument("out")
    e5 = sub.add_parser("e5")
    e5.add_argument("inp")
    e5.add_argument("out")
    args = parser.parse_args()

    if args.command == "e5":
        e5_scores(args.inp, args.out)
        return 0
    items, uat = load_items(), load_uat()
    if args.command == "e5-input":
        payload = {"heldout": {i["id"]: i["question"] for i in items}, "uat": uat}
        Path(args.out).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return 0

    sys.path.insert(0, str(ROOT))
    pages, problems = load_pages()
    problems += check_schema(items)
    excerpts = check_excerpts(items, pages)
    absent = check_absent(items, pages)
    dupes = surface_duplicates(items, uat)
    e5_data = json.loads(Path(args.e5_scores).read_text(encoding="utf-8")) if args.e5_scores else {}
    app_hits = app_fourgram_hits(items)
    REVIEW.write_text(
        render_review(items, uat, excerpts, absent, dupes, e5_data, app_hits, problems),
        encoding="utf-8",
        newline="\n",
    )
    report = {
        "items": len(items),
        "problems": problems,
        "excerpts_not_found": [
            {"id": i, **row} for i, rows in excerpts.items() for row in rows if not row["verified"]
        ],
        "absent_keyword_hits": {i: v for i, v in absent.items() if any(v.values())},
        "surface_rewrite": [i for i, d in dupes.items() if d["rewrite"]],
        "surface": dupes,
        "e5": e5_data or "NOT RUN",
        "e5_review": [i for i, d in e5_data.items() if d["cosine_max"] >= E5_THRESHOLD],
        "app_fourgram_hits": app_hits,
    }
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n"
    )
    summary = {k: v for k, v in report.items() if k not in ("surface", "e5")}
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 1 if problems or report["excerpts_not_found"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
