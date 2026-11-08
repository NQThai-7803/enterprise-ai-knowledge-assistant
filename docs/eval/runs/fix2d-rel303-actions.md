# FIX 2d: REL-303 theo dạng câu hỏi, đo trên GitHub Actions theo DEC-013

Ngày 2026-11-08. Nhánh `feat/fix-2d-rel303` (`702e933`). Đo trên Actions theo DEC-016: CPU, Ollama 0.40.15, `qwen2.5:3b`.

**Cách chạy:** mỗi bộ câu hỏi là một job. Trong job, baseline (REL-303 tắt) và `f303` (`EVAL_SHORT_ANSWER_QUESTION_TERMS=true`) chạy xen kẽ, 2 lượt mỗi bên: base 1, f303 1, base 2, f303 2. Cả 4 lượt dùng cùng image và cùng một tiến trình Ollama. Mỗi runner ghi phiên bản và backend Ollama lúc bắt đầu và lúc kết thúc, và ở mọi lượt đều là 0.40.15 / CPU.

**Phạm vi so sánh:** chỉ trong từng job. Không so với các lượt local (CUDA).

| Bộ | Run | Baseline: sai / đúng | REL-303 bật: sai / đúng | Đổi ở cả 2 lượt |
|---|---|---:|---:|---|
| `answer_relevance_dev_v1` | `42486791914` | 6 / 16 | **5 / 17** | `REL-303`: trả lời sai → từ chối đúng |
| `false_refusal_dev_v1` | `42486801873` | 6 / 13 | 6 / 13 | không |
| RBAC dev | `42486795191` | 0 / 23 | 0 / 23 | không |
| UAT Q001-Q100, proxy | `42486798724` | 100 / 100 | 100 / 100 | không |

Chi tiết từng bộ:
- **Relevance:** đúng ca mục tiêu của REL-303 đổi; không ca nào khác đổi, không ca nào dao động.
- **RBAC:**
  - Qua API: 0 rò rỉ ở cả 4 lượt.
  - Ở tầng retrieval (`rbac_retrieval_check.py`): 0 rò rỉ, 18/18 cặp kết luận được, ở cả 4 lượt.
- **UAT:**
  - Hai lượt REL-303 cho câu trả lời và tài liệu trích dẫn giống hệt baseline lượt 2.
  - Chỉ baseline lượt 1 khác ở Q033 và Q096. Đây là dao động của lượt đầu sau khi model vừa nạp, đã ghi từ PROMPT 3d, và proxy vẫn khớp.
- **Thời gian mỗi lượt:** khoảng 8 phút với relevance và false-refusal, 20 phút với RBAC (gồm kiểm tra retrieval), 18–23 phút với UAT.

## Theo DEC-013

- **Điều kiện bắt buộc: đạt.**
  - 0 rò rỉ (API và retrieval).
  - UAT không hồi quy.
  - Câu trả lời sai không tăng ở bộ nào.
- **So từng bộ:** relevance tốt hơn (ít câu trả lời sai hơn); ba bộ còn lại bằng nhau. **REL-303 thắng.**

## Thay đổi

- **`RAG_SHORT_ANSWER_QUESTION_TERMS_ENABLED=true` là mặc định.** Muốn rollback thì đặt `false`. Đã đổi ở `app/core/config.py`, `.env.example`, `ENVIRONMENT_VARIABLES.md` và giá trị mặc định của `scripts/eval/compose.uat-eval.yaml`.
- **`N_missing_condition` được gỡ khỏi các ca xfail strict của S01.** Với REL-303 bật, câu trả lời diễn đạt lại không định vị được bên cạnh các từ được hỏi, nên bị đánh `INSUFFICIENT` đúng như kỳ vọng. Phần phát hiện điều kiện bị thiếu thì vẫn chưa có.

## Giới hạn

- **Mới có một ca được cải thiện** (REL-303 trên bộ relevance). Ngưỡng 0,6 và cửa sổ 15 từ vẫn dựa trên vài ca dev.
- **Đo trên CPU.** Kết quả trên CUDA ở local có thể khác (DEC-014); khi đo lại được ở local thì chạy lại theo DEC-011.
- **Held-out v2:** không chạy, không dùng (DEC-012).
