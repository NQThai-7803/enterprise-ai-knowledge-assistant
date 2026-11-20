# ADR 0005: Mặc định trả lời: chế độ simple s1-s3 + qwen3.5-text:4b

## Status

Accepted (owner, 2026-11-20; DEC-040). Thay ADR 0003 (`legacy` + `qwen2.5:3b`).

## Context

- ADR 0003 giữ `legacy` + `qwen2.5:3b`. DEC-028 đo lại ba model; DEC-029 chọn ứng viên `s3` + `qwen3.5:4b` và đặt điều kiện trước khi đổi mặc định; owner chọn phần cứng mục tiêu: GPU NVIDIA từ 4 GB VRAM, model `qwen3.5-text:4b` (bản không có vision encoder, `PARAMETER num_gpu 99`).
- Held-out v3.1 (DEC-035, luật chọn đăng ký trước khi chạy) chạy một lần, run 44575927833, với hai cấu hình `legacy` + `qwen2.5:3b` và `s3t` = simple s1-s3 + `qwen3.5-text:4b`, cả hai với `RAG_DRAFT_DOCUMENT_POLICY=exclude`.
- Bảng tự động và bảng owner cùng nghiêng về `s3t` (DEC-040; nhãn từng câu: `docs/eval/heldout-v3.1-owner-grading.md`).

## Decision

- Mặc định: `RAG_ANSWER_MODE=simple`, s1-s3 bật (`RAG_SIMPLE_ABSENCE_SENTENCES_ENABLED`, `RAG_SIMPLE_SHORT_PROMPT_ENABLED`, `RAG_SIMPLE_RELAXED_RULES_ENABLED`, `RAG_SIMPLE_CLAIM_RELEVANCE_ENABLED`, `RAG_SIMPLE_QUESTION_LIST_SEGMENTS_ENABLED`), `LLM_OLLAMA_MODEL=qwen3.5-text:4b`, `RAG_DRAFT_DOCUMENT_POLICY=exclude`.
- Quay lui: `RAG_ANSWER_MODE=legacy` + `LLM_OLLAMA_MODEL=qwen2.5:3b`, chỉ đổi biến môi trường và khởi động lại API (`DEPLOYMENT.md` 3.3). Không cần migration hay ingest lại.

## Consequences

- Cần GPU NVIDIA từ 4 GB VRAM. Trên CPU vẫn chạy được nhưng chậm khoảng 2,5 lần (`LLM_TIMEOUT_SECONDS=600`).
- `qwen2.5:3b` không cho phép dùng thương mại; `qwen3.5:4b` là Apache 2.0 (DEC-029).
- Các hạn chế của căn cứ (một lượt quan sát, 11 câu phân biệt, held-out vừa chọn vừa đo, held-out v3.1 đã spent) ghi ở DEC-040. Lần đo độc lập sau cần held-out v4.
- Bộ eval (`scripts/eval/compose.uat-eval.yaml`, `eval.yml`, `heldout-v2.yml`) đo mặc định mới khi cấu hình không đặt gì; cấu hình quay lui là `legacy:EVAL_ANSWER_MODE=legacy,EVAL_LLM_MODEL=qwen2.5:3b`.
