# Numbers in bare table cells: the corpus v3 controls (2026-11-29)

## Diagnosis

- **Input:** the 7 control probes of the corpus v3 access matrix, where an account that may read a restricted document asks about it.
  - 5 ask about ND-COMP-001: hr, manager, ceo, payroll and chro.
  - 2 ask about ND-EXEC-001: ceo and chro.
  - 6 got NO_ANSWER. Probe text and drafts stay outside the repo.
- **Trace:** stack `eaka-corpusv3`, image `demo-3bd3e0a`, `EVAL_ABLATION=simple_trace`, system date. All 6 failures end the same way.
  - The value-bearing chunk is the prompt's first source.
  - The model gives the right value with its marker.
  - The claim validator rejects the claim with `_numbers_are_contradicted`, in simple mode's normalized path (`_canonical_numbers_are_contradicted`), on both attempts (3 first attempts lack a marker instead).
- **Root cause:** the rule takes the word right after a number as its unit, whatever that word is.
  - It calls a claim contradicted when no (value, unit) pair of the claim is among the source's.
  - A table gives its unit once, in a header ("Đơn vị: triệu đồng/tháng"), and its cells bare. Its pairs are cell values followed by the next row's first word.
  - A claim word after a number ("N4 có", "2027 có") is taken for a unit too.
  - So a right value is rejected while every number of the claim is in the source.
- **Hypotheses ruled out, with the evidence:**
  - (a) The citation and post-checks use another permission scope. Ruled out: every layer uses `build_accessible_document_filter` with direct user grants. The rejections are validator verdicts, and the chro answer on ND-EXEC-001 (PRIVATE, granted) kept its citation.
  - (b) The model refuses because of the CONFIDENTIAL/RESTRICTED labels. Ruled out: all 14 drafts state the value; none refuses.
  - (c) The claim-relevance threshold 0.78 or the token ratio 0.99 is uncalibrated. Ruled out as the cause: claim similarities were 0.834-0.893, and prompts were 2.2-2.3k tokens. The validator does misjudge table numbers, but through the number rule above, not a threshold.
  - (d) EVAL_AS_OF_DATE or the lifecycle filter drops ND-EXEC-001 (effective 2027-01-01). Ruled out: its chunks are sources 1 and 2. Authority only orders tied candidates, and only DRAFT documents are filtered.
  - (e) The cap of 2 chunks per document cuts the value. Ruled out: the value-bearing chunk is source 1 in every failure.
- **Also seen, not changed:** the PDF text wraps the code EXEC-2027-R7 at its hyphen (`EXEC-2027-` / `R7`), so the chunk never holds the code as one string.

## Change (behind a flag, off by default)

`RAG_UNITLESS_EVIDENCE_NUMBERS_ENABLED` (`_unitless_evidence_numbers_are_contradicted`):

- Only real units count (`_VALUE_UNITS`).
- A claim value is supported when the source has it with the same unit, or bare (unscaled "28" for "28 triệu").
- Contradicted when no unit-bearing value of the claim is supported while the source has unit-bearing values, or when every value the claim gives with a unit is missing from the source.
- The all-numbers check is kept.
- Offline (no LLM) on the recorded drafts:
  - the 10 rejected sentences of the controls pass;
  - on the DEC-042 `base` traces of the 7 dev sets (225 cited sentences), only 3 UAT sentences change verdict, and only 1 of them was rejected by this rule.

## Measurement, fixed before any result

- **Sets:** the 7 dev sets on Actions (`eval.yml`).
  - `configs`: `base` and `unitless` (`EVAL_UNITLESS_NUMBERS=true`), 1 run (seeded, DEC-041).
  - UAT as 2 jobs: Q001-Q050 and Q051-Q100.
- **Two separate rounds** (DEC-027), each job with its own `base`.
- **Categories** as in `scripts/diagnostics/summarize_ablation.py`: correct, false refusal, false answer, wrong value, infra; leaks.
- **The flag may become the default only when:**
  1. permission leaks = 0 on every set, in both rounds;
  2. on **no** set does false answer + wrong value increase against `base`. An increase seen in only one round is listed case by case and blocks the flip until it is explained;
  3. then fewer false refusals are preferred (`natural_dev_v1` first, DEC-026).
- UAT is reported for regression only (DEC-041).
- **The corpus v3 access matrix** (`bootstrap_corpus_v3.py`) and the leak probes are re-run with the flag on. Every blocked cell must stay blocked.
- **The owner's group D** (RBAC pairs) of the corpus v3 dev set confirms the change later: these 7 controls served the diagnosis only.
