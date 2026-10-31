# Design: answer language guard

Status: **PROPOSED, design only.** No code yet. Implementation follows
`.claude/skills/eaka-rag-change-guard`: behind a flag, old behaviour by default.
Date: 2026-10-31. Trigger: UAT Q073, labeled FAIL by the owner in PROMPT 3e.

## 1. Problem

The system prompt already says "Answer in the same language as the current question unless the
user asks otherwise." (`app/chat/prompt_builder.py:165`). Still, for a Vietnamese question with a
Vietnamese-only source, `qwen2.5:3b` sometimes answers in English (Q073: "Có. The policy does not
prohibit…").

Two harms follow:
- The answer is in the wrong language for the user.
- `extract_exact_evidence` (`app/citations/evidence.py:65-126`) cannot match the English claim to
  the Vietnamese source. It falls below `best_score 4.0` (`:115`), so the citation has no
  `evidence_text`.

The answer still passes claim validation, which is lexical and folded.

## 2. Language detection

### Options considered (offline only; the app must work without network)

| Option | Offline | Notes |
|---|---|---|
| **Built-in heuristic (proposed)** | yes, no dependency | Deterministic. Vietnamese has a cheap, strong signal: letters outside ASCII that are specific to Vietnamese (`đ ă â ê ô ơ ư` plus tone marks after NFD), together with small function-word lexicons for Vietnamese without diacritics (`khong, duoc, cua, la, thi, cho, nhan vien, bao nhieu…`) and for English (`the, is, are, does, not, of, to, and, when, must…`). Needs only the vi/en pair. |
| `lingua-language-detector` | yes (bundled models) | Accurate on short text and can be limited to {vi, en}. Large wheel and memory (tens of MB per language), compiled code. Adds a dependency for a 2-language decision. |
| `langdetect` | yes | Non-deterministic unless `DetectorFactory.seed` is set; weak on short text and on Vietnamese without diacritics. |
| fastText `lid.176.ftz` | yes (917 KB model) | Needs the `fasttext` binary wheel plus a model file to ship and pin; weak on Vietnamese without diacritics. |

**Recommendation:** start with the heuristic, so no new library is added (CLAUDE.md). Consider
`lingua` only if the acceptance set in section 6 shows false positives the heuristic cannot fix.

### Rules

- **Text cleaning before scoring.** Remove `[n]` / `[SOURCE_n]` markers, URLs, numbers and
  money/time values, and tokens that are all capitals or mix letters and digits (`VPN`, `MFA`,
  `OT`, `HRM`, `ND-HR-005`, `Q4`). Also remove text inside quotes or backticks, and a configured
  list of English workplace terms that Vietnamese policies use verbatim (`hybrid, remote, on-call,
  salary review, payroll, ticket, stipend, calibration…`). Keep that list as data, not
  per-question logic.
- **Sentence language:** Vietnamese when it has a Vietnamese-specific letter, or at least 2
  Vietnamese function words. English when it has no Vietnamese-specific letter, at least 5 Latin
  words, and at least 2 English function words. Otherwise neutral.
- **Question language:**
  - Vietnamese when any sentence is Vietnamese; this covers mixed questions such as "salary
    review diễn ra khi nào?", which count as Vietnamese.
  - English when every non-neutral sentence is English.
  - Otherwise unknown, and the guard does nothing.
- **Mismatch:**
  - Vietnamese question: the generated answer contains at least one English sentence, and the
    English sentences make up at least 40 % of the scored words.
  - English question: the answer contains Vietnamese sentences.
  - Sentence-level checks avoid flagging a Vietnamese answer that only quotes an English term.

## 3. Handling a mismatch

1. **Scope:** only text the LLM generated. Deterministic structured answers copy source clauses,
   and their language is the source's, so they are not checked.
2. **Regenerate once.** Use the same prompt plus an explicit instruction in the system part:
   "Trả lời hoàn toàn bằng tiếng Việt." / "Answer entirely in English." Retrieved text stays out
   of system messages, as today. The new draft goes through the normal citation and claim
   validation, so `evidence_text` is computed on the final answer.
3. **Still mismatched → fail-safe.** Return the fixed no-answer with no citations, the same
   outcome as the existing validation failures.
4. **Streaming:** the SSE path already buffers and validates the full answer before emitting
   anything, so the same guard applies.
5. **Logging:** content-free only, `error_code=ANSWER_LANGUAGE_MISMATCH`, `attempt=1|2`, the
   detected languages, and `conversation_id`. No question or answer text.

## 4. Flag

| Name | Type | Default | Meaning |
|---|---|---|---|
| `RAG_ANSWER_LANGUAGE_GUARD_ENABLED` | bool | `false` | Detect question/answer language; regenerate once on mismatch; then fail-safe. |

Add it to `Settings`, `ENVIRONMENT_VARIABLES.md` and `.env.example`. The workplace-term list
lives next to the detector, with a test that every entry is lower case and ASCII.

## 5. Tests

- **Unit, detector:**
  - Vietnamese with and without diacritics; English; Vietnamese with English terms
    (`VPN/MFA`, `hybrid`, `salary review`, `on-call`, `stipend`); markers, numbers, money and
    times; quoted English inside Vietnamese.
  - Question kinds: mixed questions, English-only questions, unknown.
  - The Q073 answer string must be flagged. The answers to the other 96 Vietnamese questions in baseline v2 must not be flagged.
    These are fixtures in the unit test, not runtime logic.
- **Unit, grounded answer service with a fake LLM:**
  - English then Vietnamese → the Vietnamese answer with citations and non-empty `evidence_text`.
  - English twice → fixed no-answer, no citations.
  - English question with an English answer → unchanged.
  - Deterministic structured answer → not checked.
  - Flag off → byte-identical behaviour.
- **Streaming:** the same outcome on the SSE path.
- **Permission:** a regenerated answer may cite only authorized retrieved chunks; this is the
  existing citation-revalidation suite.

## 6. Acceptance criteria

1. `permission_leak_count = 0`.
2. On the baseline-v2 answers (`artifacts/baseline-v2/`): false positive rate 0 for the
   Vietnamese answers; Q073 detected.
3. UAT Q001-Q100 with the flag on, using the baseline-v2 protocol (warm-up, seed, temperature 0,
   2 runs): Q073 answered in Vietnamese or fail-safe; every other case identical to baseline v2,
   except the known Q096 run-order variance. Group (b) is graded by a person.
4. Latency changes only for regenerated cases (one extra generation each).
5. No new dependency unless criterion 2 fails with the heuristic.

## 7. Rollback

Set `RAG_ANSWER_LANGUAGE_GUARD_ENABLED=false`. There is no schema or data change.
