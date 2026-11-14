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

## Kết quả hiệu chỉnh (Actions run `43498479733`, commit `736f854`, 2026-11-14)

- UAT 100/100 ở cả `base` và `probe`, 2 lượt: **75 câu đi route deterministic, 25 câu đi đường LLM**, đúng hết. `probe` không đổi trạng thái hay citation câu nào (Q033, Q096 chỉ đổi chữ).
- S = 18 câu (đi LLM, đúng, có cosine ở cả 2 lượt). Phân bố (ô thấp hơn của 2 lượt): 0,81 (Q007); 0,82 (Q002, Q034); 0,84 (Q004, Q009, Q011, Q012); 0,85 (Q008, Q014, Q015, Q033); 0,86 (Q055, Q058, Q091, Q095); 0,87 (Q092); 0,89 (Q094); 0,90 (Q070).
- 7 câu đi LLM không có cosine (Q013, Q018, Q071, Q073, Q096, Q097, Q100: câu hỏi nhiều ý hoặc không tìm được câu evidence), nên check không chạm chúng.
- Route deterministic: 74/75 câu có cosine, thấp nhất 0,78; (ii) không kiểm route này.
- **t = 0,81.** Ngưỡng cũ 0,85 của M1b chặn 7/18 câu đúng của phần LLM, cộng các câu deterministic dưới 0,85: khớp với 43 câu hồi quy của FIX 3a.
- Commit hiệu chỉnh chưa có `RAG_COMPLETENESS_NUMBER_NORMALIZATION_ENABLED` (bật sau, PR #25); flag đó chỉ đổi FR2-E01 trong đợt của nó, không đổi câu UAT nào.

## Kết quả đợt đo (Actions, commit `6ea71d5`, t = 0,81, 2026-11-14)

Ô: đúng / từ chối sai / trả lời sai / sai (nhầm giá trị); hai lượt mỗi bên giống hệt nhau. 0 rò rỉ ở mọi ô.

| Bộ (run) | `base` | `resp` | Thay đổi ở cả 2 lượt |
|---|---|---|---|
| UAT (`43517483428`) | 100/0/0/0; deterministic 75/75, LLM 25/25 | 99/1/0/0; deterministic 75/75, LLM 24/25 | Q071 đúng → từ chối sai |
| RBAC (`43517521598`) | 23/12/0/1 | 22/13/1/0 | RBD-13 control sai → từ chối; **RBD-03 negative đúng → trả lời sai** |
| relevance (`43517558708`) | 17/3/5/0 | **19**/3/**3**/0 | REL-401, REL-403 trả lời sai → đúng |
| FR v1 (`43517595504`) | 13/1/6/0 | = | |
| FR v2 (`43517631924`) | 15/4/5/0 | 14/6/4/0 | FR2-E05 trả lời sai → đúng; FR2-E01, E03 (câu hỏi tiếng Anh) đúng → từ chối |
| compound (`43517669294`) | 4/3/4/1 | = | |

Trả lời sai (cả hai nhóm) theo bộ: UAT 0 → 0, RBAC 1 → 1, relevance 5 → 3, FR v1 6 → 6, FR v2 5 → 4, compound 5 → 5. Câu đúng: UAT −1, RBAC −1, relevance +2, FR v2 −1.

**Áp quy tắc:** không rò rỉ, trả lời sai không tăng ở bộ nào, UAT trong dung sai 1 câu. Nhưng ở UAT và RBAC, `resp` có cùng số trả lời sai và **ít hơn 1 câu đúng**, ổn định ở cả 2 lượt: tệ hơn `base` ở hai bộ. **Không thắng; `RAG_RESPONSIVENESS_CHECK_ENABLED` giữ tắt.** Code và bộ đếm cosine được merge (flag tắt), như F.

**Hai điều đợt đo cho thấy:**
1. **NO_ANSWER do check tạo ra chưa phải là điểm dừng.** RBD-03 negative: check chặn câu trả lời đầu (bộ đếm `question_evidence_dissimilar` = 5 trên RBAC), pipeline sinh lại, và một câu lạc đề từ tài liệu được phép ("báo cho lễ tân tầng 1", RBAC-ORG-001, không rò rỉ) qua được ngưỡng. Muốn check chỉ chặn mà không mở đường trả lời khác, câu bị chặn phải dừng ở NO_ANSWER, không đi vào vòng thử lại.
2. **Hiệu chỉnh chỉ phủ các câu tính đúng một cosine.** Q071 không có trong S vì check chạy nhiều lần cho câu này (mỗi lần sinh một lần); một lần sinh trung gian dưới 0,81 đã bị chặn. Câu hỏi tiếng Anh (E01, E03) có cosine thấp hơn với evidence tiếng Việt; UAT gần như không có câu loại này nên ngưỡng lấy từ UAT không phủ chúng.
