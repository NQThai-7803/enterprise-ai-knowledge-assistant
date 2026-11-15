# DEC-025: tắt cross-encoder (ADR 0004 phương án b)

Viết 2026-11-15, **trước khi đo**.

- **Thay đổi:** `RERANKER_PROVIDER` mặc định `heuristic` thay vì `sentence_transformers`. Với `sentence_transformers`, model cross-encoder không có trong cache của stack eval, nên reranker luôn rơi về `HeuristicRetrievalReranker`; với `heuristic`, dùng thẳng reranker đó. Phần xếp hạng theo trùng từ không đổi.
- **Đợt đo:** cùng job, 2 lượt xen kẽ, 6 bộ (UAT tách route, RBAC, relevance, FR v1, FR v2, compound). Cấu hình `base` = mặc định cũ (`EVAL_RERANKER_PROVIDER=sentence_transformers`), `heur` = mặc định mới.
- **Kỳ vọng: 0 câu đổi.** Một câu "đổi" là câu có nhóm (đúng / từ chối sai / trả lời sai / sai), trạng thái hoặc tài liệu được trích khác `base` ở **cả 2 lượt**. Có câu đổi: **dừng, không merge, báo owner**. Chữ của câu trả lời khác nhau mà nhóm, trạng thái, citation giống nhau thì chỉ báo, không tính là đổi (dao động của Ollama).
- Báo kèm: `reranker_mode` của mỗi lượt (phải là `lexical_fallback` ở cả hai), độ trễ, RAM.
