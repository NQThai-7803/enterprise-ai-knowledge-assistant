# Held-out v3.1: the owner's grading (run 44575927833)

The owner read `grading.md` of run 44575927833 (DEC-035, decrypted on the owner's machine,
DEC-039) and set these labels on 2026-11-20. The public repository holds ids, labels and reason
codes only: no question, gold or answer text.

- Configurations: `legacy` = `legacy` + `qwen2.5:3b`; `s3t` = simple mode with s1-s3 +
  `qwen3.5-text:4b`. Both with `RAG_DRAFT_DOCUMENT_POLICY=exclude`.
- The labels are the same for run1 and run2: the two runs gave the same result for every item.
- Held-out v3.1 is **spent** (DEC-040): it is not used to measure again or to design a fix.

## Labels

| Label | Meaning |
|---|---|
| `PASS` | Right answer, supported by its citation. |
| `PARTIAL` | Part of the answer is right and supported; part is missing. |
| `FAIL_REFUSAL` | The system refused an answerable question. |
| `FAIL_WRONG` | The answer states something wrong. |
| `FAIL_CITATION` | The cited source does not support the answer. |

Reason codes for `s3t`'s failures:

| Code | Meaning |
|---|---|
| `CITATION_DOES_NOT_SUPPORT` | The citation does not prove the answer. |
| `CONTRADICTS_CITED_SOURCE` | The answer states the opposite of the cited source. |
| `SOURCE_CONFLICT_NOT_STATED` | Two sources disagree and the answer does not say so. |

| Item | `legacy` | `s3t` | `s3t` reason code |
|---|---|---|---|
| HO3-01 | FAIL_REFUSAL | FAIL_REFUSAL | |
| HO3-02 | PASS | PARTIAL | |
| HO3-03 | FAIL_REFUSAL | FAIL_CITATION | CITATION_DOES_NOT_SUPPORT |
| HO3-04 | FAIL_WRONG | PASS | |
| HO3-05 | FAIL_REFUSAL | FAIL_REFUSAL | |
| HO3-06 | FAIL_REFUSAL | PARTIAL | |
| HO3-07 | FAIL_REFUSAL | FAIL_REFUSAL | |
| HO3-08 | FAIL_WRONG | PARTIAL | |
| HO3-10 | FAIL_WRONG | FAIL_REFUSAL | |
| HO3-12 | FAIL_WRONG | FAIL_WRONG | CONTRADICTS_CITED_SOURCE |
| HO3-14 | FAIL_WRONG | FAIL_REFUSAL | |
| HO3-15 | FAIL_REFUSAL | FAIL_REFUSAL | |
| HO3-16 | FAIL_WRONG | FAIL_WRONG | SOURCE_CONFLICT_NOT_STATED |
| HO3-17 | FAIL_REFUSAL | FAIL_WRONG | SOURCE_CONFLICT_NOT_STATED |
| HO3-18 | FAIL_WRONG | FAIL_WRONG | SOURCE_CONFLICT_NOT_STATED |
| HO3-19 | PARTIAL | PARTIAL | |

Totals per run:

| Configuration | PASS | PARTIAL | FAIL_REFUSAL | FAIL_WRONG + FAIL_CITATION |
|---|---:|---:|---:|---:|
| `legacy` | 1 | 1 | 7 | 7 |
| `s3t` | 1 | 4 | 6 | 5 |

## Where the owner differs from the automatic grader

| Item | Configuration | Automatic | Owner | Reason code |
|---|---|---|---|---|
| HO3-02 | `legacy` | not correct | PASS | `GRADER_REQUIRES_DERIVED_VALUE`: the grader asks for a value derived from the document that the document does not state. |
| HO3-03 | `s3t` | correct | FAIL_CITATION | `COINCIDENTAL_VALUE_MATCH`: the value matches by chance; the citation does not support it. |

## Items not asked

- HO3-11: excluded by the owner, its gold is wrong (DEC-038, DEC-040).
- HO3-09, HO3-13, HO3-20: removed from v3 before v3.1, their source documents are not in corpus V2
  (DEC-038).
