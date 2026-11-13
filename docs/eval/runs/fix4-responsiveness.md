# FIX 4 (ii): kiểm độ đáp ứng, hiệu chỉnh trên phần UAT đi đường LLM

Viết 2026-11-14, **trước mọi lần đo** của mục này.

## Cơ chế

- Dùng lại check M1b của FIX 3a (`_answer_addresses_question`): cosine e5 giữa câu hỏi và câu evidence mà câu trả lời dựa vào; dưới ngưỡng thì câu trả lời thành NO_ANSWER. Chỉ chuyển SUPPORTED thành NO_ANSWER, không bao giờ ngược lại; câu hỏi nhiều ý không bị kiểm (như M1b).
- M1b làm UAT hồi quy 43 câu vì ngưỡng 0,85 lấy từ bộ giả lập. Bản (ii) khác ở hai điểm:
  1. **Chỉ áp cho câu trả lời đi đường LLM** (`RAG_RESPONSIVENESS_CHECK_ENABLED`); câu trả lời dựng sẵn (route deterministic) không bị kiểm. Route deterministic có kiểu lỗi riêng (D) và để cho bộ phân loại ý định.
  2. **Ngưỡng riêng** (`RAG_RESPONSIVENESS_MIN_SIMILARITY`), lấy từ phần UAT đi đường LLM, không từ bộ giả lập.
- Mỗi cosine đã tính được đếm theo ô 0,01 trên `GET /metrics`; runner UAT ghi `evidence_similarity` và `answer_route` cho từng câu.

## Đợt hiệu chỉnh (chỉ UAT)

- Cấu hình, cùng job, 2 lượt xen kẽ: `base`; `probe` = `EVAL_QUESTION_EVIDENCE_SIMILARITY=true`, `EVAL_QUESTION_EVIDENCE_MIN_SIMILARITY=0.0` (tính cosine cho mọi câu, không chặn câu nào).
- `probe` không được đổi trạng thái hay citation của câu nào so với `base` (chỉ tính khác dao động đã thấy ở cả 2 lượt). Nếu đổi: dừng, báo.
- **Quy tắc chọn ngưỡng `t`:**
  - S = các câu UAT có `answer_route = llm` ở cả 2 lượt `probe`, đúng (proxy) ở cả 2 lượt, và có `evidence_similarity` ở cả 2 lượt; giá trị của mỗi câu là ô thấp hơn trong 2 lượt.
  - `t` = giá trị nhỏ nhất của S. Không câu đúng nào của phần LLM bị chặn; không dùng dung sai 1 câu để đẩy ngưỡng lên.
  - Nếu S có dưới 10 câu: không đủ để hiệu chỉnh; báo owner, không đo tiếp.
- Báo cùng lúc: phân bố S, các câu UAT đi đường LLM nhưng sai và giá trị của chúng, số câu đi route deterministic (không bị kiểm).

## Đợt đo (sau khi có `t`)

- Cấu hình, cùng job, 2 lượt xen kẽ: `base`; `resp` = `EVAL_RESPONSIVENESS=true`, `EVAL_RESPONSIVENESS_MIN=t`.
- Bộ: UAT (báo tách route), RBAC, relevance, FR v1, FR v2, compound.
- **Chọn theo DEC-013**, "trả lời nhầm giá trị" tính là trả lời sai (owner, 2026-11-14): 0 rò rỉ; UAT không hồi quy quá 1 câu, và phần đi đường LLM được báo riêng; trả lời sai không tăng ở bộ nào; thắng khi không tệ hơn ở bộ nào và tốt hơn ở ít nhất một bộ (ít trả lời sai hơn, rồi nhiều câu đúng hơn). Báo số ca vào nhánh (`question_evidence_dissimilar`).
- Thắng thì bật `RAG_RESPONSIVENESS_CHECK_ENABLED` với `t`; không thì giữ tắt.
