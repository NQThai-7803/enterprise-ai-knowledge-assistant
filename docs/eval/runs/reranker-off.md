# DEC-025: tắt cross-encoder (ADR 0004 phương án b)

Viết 2026-11-15, **trước khi đo**.

- **Thay đổi:** `RERANKER_PROVIDER` mặc định `heuristic` thay vì `sentence_transformers`. Với `sentence_transformers`, model cross-encoder không có trong cache của stack eval, nên reranker luôn rơi về `HeuristicRetrievalReranker`; với `heuristic`, dùng thẳng reranker đó. Phần xếp hạng theo trùng từ không đổi.
- **Đợt đo:** cùng job, 2 lượt xen kẽ, 6 bộ (UAT tách route, RBAC, relevance, FR v1, FR v2, compound). Cấu hình `base` = mặc định cũ (`EVAL_RERANKER_PROVIDER=sentence_transformers`), `heur` = mặc định mới.
- **Kỳ vọng: 0 câu đổi.** Một câu "đổi" là câu có nhóm (đúng / từ chối sai / trả lời sai / sai), trạng thái hoặc tài liệu được trích khác `base` ở **cả 2 lượt**. Có câu đổi: **dừng, không merge, báo owner**. Chữ của câu trả lời khác nhau mà nhóm, trạng thái, citation giống nhau thì chỉ báo, không tính là đổi (dao động của Ollama).
- Báo kèm: `reranker_mode` của mỗi lượt (phải là `lexical_fallback` ở cả hai), độ trễ, RAM.

## Kết quả (Actions, commit `a110b35`, 2026-11-15)

Mỗi bộ một job, `base` (`RERANKER_PROVIDER=sentence_transformers`) và `heur` (`heuristic`, mặc định mới), 2 lượt. Ô: đúng / từ chối sai / trả lời sai / sai. 0 rò rỉ; `reranker_mode=lexical_fallback` ở mọi lượt của cả hai cấu hình.

| Bộ (run) | `base` | `heur` | Câu đổi (trạng thái, nhóm hoặc citation) |
|---|---|---|---|
| UAT (`43679360303`) | 100/0/0/0; deterministic 75, LLM 25 | = | 0 |
| RBAC (`43679382159`) | 23/13/0/0 | = | 0 |
| relevance (`43679404003`) | 18/3/4/0 | = | 0 |
| FR v1 (`43679423998`) | 13/1/6/0 | = | 0 |
| FR v2 (`43679441747`) | 14/6/4/0 | = | 0 |
| compound (`43679460725`) | 4/4/3/1 | = | 0 |

- **0 câu đổi ở cả 6 bộ.** Chỉ đổi chữ: Q096, FR-N05, FR2-C01, FR2-F06 ở một lượt (dao động đã thấy ở các đợt trước); **Q033 ở cả 2 lượt** (`base` có thêm câu dẫn mục "Trường hợp này được quy định trong mục 1 …"), cùng trạng thái, cùng chunk được trích, vẫn đúng. Đường rơi về của `sentence_transformers` gọi đúng `HeuristicRetrievalReranker`, nên thứ hạng và prompt giống nhau; Q033 cũng đổi chữ ở cả 2 lượt giữa `base` và `probe` của đợt hiệu chỉnh (`probe` không đổi prompt), nên đây là dao động của Ollama theo thời gian chạy, không phải tác dụng của flag.
- **Quyết định:** đạt quy tắc, `RERANKER_PROVIDER=heuristic` giữ làm mặc định (DEC-025).
