# Design: fine-tuning the embedding model (ADR)

Status:
- **PROPOSED.** Infrastructure only (`ml/embedding_finetune/`). No model has been trained for use, and the app's model is unchanged.
- Order in TASKS: after FIX 3, before the final held-out v2 measurement.

Date: 2026-11-08. Data rule: DEC-015.

## 1. Problem

The app embeds with `intfloat/multilingual-e5-small` (384 dimensions, `query: ` / `passage: ` prefixes). Users also type:
- **without diacritics** ("nghi phep nam bao nhieu ngay");
- **in English** about Vietnamese documents;
- **company terms and abbreviations** the base model has not seen in context (CTO, phụ cấp lưu trú, chấm công hybrid).

The hybrid retrieval (semantic + keyword + fusion) recovers part of this through the keyword side, which folds diacritics. The semantic side does not. `docs/eval/runs/finetune-baseline.md` measures how much recall the base model loses per form.

## 2. Decision

Fine-tune the same base model; do not switch model family.
- **Base:** `intfloat/multilingual-e5-small`. The output keeps 384 dimensions, so the `vector(384)` column, the HNSW index and the exact-KNN path stay as they are.
- **Prefixes:** unchanged, `query: ` for questions and `passage: ` for chunks, in training and in the app.
- **Loss:** `CachedMultipleNegativesRankingLoss`. Each question is trained against its positive chunk, one hard negative, and the other passages of the batch. The cache makes the effective batch (default 128) independent of the mini batch held in memory (default 16), so a 4 GB GPU still gets many in-batch negatives.
- **Hardware (DEC-017):** real training runs locally on the GTX 1650 (4 GB) or on Colab; defaults are `max_seq_length` 256 and fp16 on CUDA. A non-finite loss under fp16 restarts the run from the base model in fp32, and `training_config.json` records why.
- **Hard negatives:** taken from the app's current hybrid retrieval, run inside an eval stack (`mine_negatives.py`). These are the chunks the system confuses today. The positive, chunks with the same text, and the chunks next to the positive in the same document (they overlap by 100 tokens) are excluded.
- **Training questions:** synthetic only. The local LLM writes 3-5 questions per chunk (`generate_queries.py`). `augment.py` then adds, per question, a version without diacritics, a version with about half of the diacritics, one light typo, and optionally an English translation.

## 3. Data rule (DEC-015)

No question from UAT Q001-Q100, held-out v1, held-out v2, RBAC dev, `answer_relevance_dev_v1` or `false_refusal_dev_v1` may be training data.
- **Enforced in code.** Every training question is checked against `scripts/eval/question_fingerprints.json`, which holds salted word 4-gram hashes of all six sets. Generation and augmentation drop any match, and `train.py` refuses to start if one remains. A missing or stale fingerprint file is an error, never "no match".
- **Corpus overlap is allowed.** Training uses corpus V2 chunks, the same documents the dev and held-out questions ask about. Only questions are protected.
- **Known limit:** a synthetic question can paraphrase a protected one without sharing a 4-gram. The held-out sets stay the guard here: held-out v2 is never used to choose training data or settings.

## 4. Evaluation

`eval_retrieval.py` reports recall@1/5/10 and MRR@10 for the base model and each candidate.
- **Split by form:** as written, without diacritics (generated), and English when a dev translation exists.
- **Questions:** UAT Q001-Q100, a dev set. Held-out sets are never used here.
- **Gold:** `eval-data/uat/retrieval-gold.json`, the document and page cited by each manually reviewed answer (98 questions). A gold chunk is any chunk covering that page.
- **Scope:** this measures the embedding alone (exact cosine over all chunks), not the app's hybrid ranking. End-to-end effect is measured the usual way (section 6).

## 5. How a fine-tuned model would reach the app (not done now)

1. **Publish the model** as a GitHub Release asset with its SHA256 (DEC-017), never in the repository. Record `training_config.json`, which holds the data hashes, the arguments, the device and the library versions. The eval workflow is to download it, check the hash, and measure it in the same job as the base model (not built yet).
2. **Configure it** through the existing settings `EMBEDDING_MODEL_NAME` and `EMBEDDING_MODEL_REVISION`. No new code path is needed to load it.
3. **Re-embed the whole corpus before switching (blue-green).** The semantic query does not filter on `document_chunks.embedding_model`, so a half re-embedded corpus would silently compare new query vectors with old passage vectors.
   - Build a second stack: restore the corpus and reprocess every document through the normal pipeline with the new model.
   - Validate it, then switch traffic.
   - A follow-up change could also restrict semantic search to chunks whose `embedding_model` matches the configured one. That change is flag-gated and lives under `eaka-rag-change-guard`.
4. **Rollback:** switch back to the old stack, whose vectors are untouched. Do not re-embed in place.

## 6. Acceptance criteria

A candidate model is proposed for the app only if all of these hold:
- **Without diacritics:** recall@10 and MRR@10 improve on UAT questions without diacritics.
- **As written:** recall@10 does not drop by more than 1 point.
- **End to end:** the same-batch comparison of DEC-011 and DEC-013 passes on every dev set with the new model on its re-embedded stack:
  - 0 permission leaks;
  - no UAT regression;
  - false answers do not increase on any set.
- **Held-out v2:** the final held-out v2 measurement is run once, after the choice is made, and does not feed back into training.

## 7. Risks

- **Overfitting to corpus V2.** The model learns this company's documents. A new corpus needs new training data, or the gain may reverse. Mitigation: keep the base model as the default and judge the candidate per corpus.
- **Synthetic questions are cleaner than real ones.** The typo and diacritic variants help only partly. English questions translated by a 3B model can be literal.
- **Protected-set contamination by paraphrase.** See section 3.
- **Vector mixing during migration.** See section 5.3: never re-embed in place.
- **Reproducibility.** Training on CPU and GPU, or in fp16 and fp32, gives slightly different weights. The config records the device, GPU, precision and versions, and `requirements-train.lock` pins every library except torch, whose build is chosen per host (cu126 locally, CPU on Actions). Numbers from different hosts are never compared (DEC-017).
- **Library versions differ from the app.** The training lock follows `.venv-nlp` (sentence-transformers 6.2.0, transformers 5.22.2); the app image has 6.1.0 and 5.19.0. `eval_retrieval.py` scores the base model and the candidate in the same environment, but before a switch the candidate must also load and embed identically in the app image.
- **Licence.** multilingual-e5-small is MIT-licensed. A fine-tuned copy stays internal.
