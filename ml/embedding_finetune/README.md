# Embedding fine-tune pipeline

Infrastructure only. Nothing here is imported by `app/` or installed into the app image. Design and acceptance criteria: `docs/design/embedding-finetune.md`. Data rule: DEC-015.

| Step | Script | Needs |
|---|---|---|
| 1. Chunks and synthetic questions | `generate_queries.py` | eval stack with corpus V2 (for chunks), Ollama |
| 2. Variants | `augment.py` | Ollama only with `--english` |
| 3. Hard negatives | `mine_negatives.py` | eval stack with corpus V2 |
| 4. Training | `train.py` | CPU or GPU |
| 5. Evaluation | `eval_retrieval.py` | CPU |

`in_container.py` runs inside the API container. Steps 1 and 3 copy it there and read the database and the app's own hybrid retrieval through it; it writes nothing.

All outputs go under `artifacts/embedding-finetune/` (git-ignored). Corpus text and models are never committed.

## Data rule

Training questions are synthetic. A question that shares a word 4-gram with any of these sets is dropped at steps 1 and 2:
- UAT Q001-Q100;
- held-out v1 and v2;
- RBAC dev, `answer_relevance_dev_v1` and `false_refusal_dev_v1`.

`train.py` refuses to start if any such question remains. The check reads `scripts/eval/question_fingerprints.json` (salted hashes) and fails when that file is missing or stale. Rebuild it with `python scripts/eval/question_leak.py build` after any question set changes.

## Install

`requirements-train.lock` is the freeze of `.venv-nlp` (Python 3.12) without torch. Install torch in the same command, from the index of the host:

```bash
# Local, NVIDIA GPU (GTX 1650, CUDA 12.6 build), repository root
uv venv .venv-nlp --python 3.12
uv pip install --python .venv-nlp -r ml/embedding_finetune/requirements-train.lock \
  torch==2.14.1+cu126 --extra-index-url https://download.pytorch.org/whl/cu126 \
  --index-strategy unsafe-best-match

# GitHub Actions or any CPU-only Linux host
python -m pip install -r ml/embedding_finetune/requirements-train.lock \
  torch==2.14.1+cpu --extra-index-url https://download.pytorch.org/whl/cpu
```

Check: `.venv-nlp/Scripts/python.exe -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"`. Importing `ranx` prints a `SyntaxWarning` from the library; it is harmless.

## Local run (repository root)

```bash
PY=.venv-nlp/Scripts/python.exe   # .venv-nlp/bin/python on Linux/macOS
OUT=artifacts/embedding-finetune/run1

# 1. Needs the corpus V2 eval stack (eaka-p3d-uat) and Ollama
$PY ml/embedding_finetune/generate_queries.py --container eaka-p3d-uat-api-1 \
  --chunks-out $OUT/chunks.jsonl --out $OUT/queries.jsonl
# 2.
$PY ml/embedding_finetune/augment.py --queries $OUT/queries.jsonl --out $OUT/augmented.jsonl
# 3. Same stack
$PY ml/embedding_finetune/mine_negatives.py --container eaka-p3d-uat-api-1 \
  --queries $OUT/augmented.jsonl --chunks $OUT/chunks.jsonl --out $OUT/triples.jsonl
# 4.
$PY ml/embedding_finetune/train.py --triples $OUT/triples.jsonl --chunks $OUT/chunks.jsonl \
  --out $OUT/model --epochs 1
# 5. Base model and candidate on the same chunks
$PY ml/embedding_finetune/eval_retrieval.py --chunks $OUT/chunks.jsonl \
  --models intfloat/multilingual-e5-small $OUT/model --out $OUT/eval.json
```

Add `--limit 10` to step 1 and `--max-pairs 50 --batch-size 8 --max-seq-length 128` to step 4 for a smoke run.

## Training on a 4 GB GPU (GTX 1650)

- Defaults: `--max-seq-length 256`, `--batch-size 128` (effective batch, the in-batch negatives), `--mini-batch-size 16` (what is in memory at once), fp16 on CUDA. The suggested range for 4 GB is an effective batch of 128-256 with a mini batch of 16-32; memory use at 32 is not measured yet.
- **Out of memory:** lower `--mini-batch-size` (16, then 8) and add `--gradient-checkpointing`. The effective batch does not change.
- **NaN under fp16:** GTX 16xx cards can produce non-finite values in half precision. `train.py` checks the loss at every step; on a NaN or inf it stops, restarts from the base model in fp32 with the same seed, and writes the reason to `fp16_fallback` in `training_config.json`. `--no-fp16` skips fp16 from the start.
- `training_config.json` also records the device, GPU name, CUDA version, library versions, the seed, and the SHA256 of the triples, the chunks and the exact examples trained on.
- Models are never committed. Publish one as a GitHub Release asset with its SHA256 (DEC-017).

## Google Colab (GPU)

Steps 1 and 3 need the eval stack, so run them locally. Upload `chunks.jsonl` and `triples.jsonl`, and run steps 4 and 5 on Colab:

```python
!git clone <repo-url> eaka && cd eaka
# Colab ships its own CUDA torch, and the lock has no torch: install the rest from it.
!pip install -q -r ml/embedding_finetune/requirements-train.lock
# Upload chunks.jsonl and triples.jsonl to artifacts/embedding-finetune/run1/, then:
!python ml/embedding_finetune/train.py --triples artifacts/embedding-finetune/run1/triples.jsonl \
    --chunks artifacts/embedding-finetune/run1/chunks.jsonl \
    --out artifacts/embedding-finetune/run1/model --device cuda --batch-size 256 --mini-batch-size 32
!python ml/embedding_finetune/eval_retrieval.py --chunks artifacts/embedding-finetune/run1/chunks.jsonl \
    --models intfloat/multilingual-e5-small artifacts/embedding-finetune/run1/model \
    --out artifacts/embedding-finetune/run1/eval.json
```

`train.py` writes `training_config.json` beside the model: the arguments, the device, the library versions, and the SHA256 of the triples and chunks it used. The data-rule check needs `scripts/eval/question_fingerprints.json` and `docs/eval/heldout-v1.lock` plus `docs/eval/heldout-v2-questions.lock` from the clone. Only their hashes are compared.

## Evaluation set

`eval_retrieval.py` asks UAT Q001-Q100 (`eval-data/uat/questions.json`, dev) as written and without diacritics. With `--english <jsonl>` it also asks an English version. The gold is the document and page each reviewed answer cited (`eval-data/uat/retrieval-gold.json`, 98 questions). It never reads a held-out set.
