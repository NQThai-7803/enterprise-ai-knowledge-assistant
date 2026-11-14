# FIX 4 (iii): dự phòng cho đoạn trích theo câu hỏi

Viết 2026-11-14, **trước mọi lần đo** của mục này.

## Cơ chế

- `query_focused_excerpt` (`app/chat/context_builder.py`) thay nội dung chunk bằng các dòng chọn theo từ vựng. Đó là lý do UAT đạt cao (`excerpt_off`: UAT −8, RBAC −5), nhưng nó bỏ sót dòng đáp án khi câu hỏi diễn đạt khác nguồn (FR-A01, REL-403, FR2-C05, FR2-L06 được cứu khi bỏ đoạn trích).
- `RAG_EXCERPT_FALLBACK_ENABLED` (mặc định tắt) giữ đoạn trích, nhưng dùng **cả chunk** cho một source khi:
  1. đoạn trích không chứa từ nội dung nào của câu hỏi (các từ `_query_needles` lấy ra, đã bỏ dấu, so theo ranh giới từ); hoặc
  2. câu hỏi ghép mà đoạn trích không có khối `CLAIM_n evidence` cho một ý.
- Cả chunk là tập chứa đoạn trích, nên không mất dòng nào; validator thấy cùng văn bản với LLM. Ngân sách token của context vẫn áp dụng như cũ.

## Đợt đo và quy tắc chọn

- Cấu hình, cùng job, 2 lượt xen kẽ: `base` (mặc định lúc đo, gồm mọi flag đã bật trước đó) và `xfb` = `base` + `EVAL_EXCERPT_FALLBACK=true`.
- Bộ: UAT (báo tách route), RBAC, relevance, FR v1, FR v2, compound.
- **DEC-013, "nhầm giá trị" tính là trả lời sai:** 0 rò rỉ; UAT không hồi quy quá 1 câu, phần đi LLM báo riêng; trả lời sai không tăng ở bộ nào. Thắng khi không tệ hơn `base` ở bộ nào (ít trả lời sai hơn trước, rồi nhiều câu đúng hơn) và tốt hơn ở ít nhất một bộ.
- Thắng thì bật mặc định; không thì giữ tắt.

**Bổ sung trước khi đo (2026-11-14):** (iii) và (iv) đo chung một job với cùng `base`: cấu hình `base`, `xfb` (iii), `cpa` (iv), `both` (iii + iv). Mỗi flag được chọn bằng so sánh của chính nó với `base`. Nếu cả hai cùng thắng, bật cả hai chỉ khi `both` cũng thắng `base` và không thua `xfb` hay `cpa` ở bộ nào; nếu không, bật cái thắng mà không thua cái kia, hoặc để owner quyết định.


## Kết quả (Actions, commit `8be6758`, 2026-11-14)

Mỗi bộ một job, 4 cấu hình, 2 lượt; hai lượt giống hệt nhau ở mọi ô. Ô: đúng / từ chối sai / trả lời sai / sai (nhầm giá trị). 0 rò rỉ ở mọi ô.

| Bộ (run) | `base` | `xfb` (iii) | `cpa` (iv) | `both` |
|---|---|---|---|---|
| UAT (`43561537655`) | 100/0/0/0; deterministic 76, LLM 24 | = | = | = |
| RBAC (`43561557390`) | 23/12/0/1 | = | = | = |
| relevance (`43561577800`) | 17/3/5/0 | = | = | = |
| FR v1 (`43561598132`) | 13/1/6/0 | = | = | = |
| FR v2 (`43561618780`) | 15/4/5/0 | = | = | = |
| compound (`43561638296`) | 4/3/4/1 | 4/4/3/1 (P02 trả lời sai → từ chối) | **6**/0/**5**/1 (P01, P05, P06 → đúng; **R03 đúng → trả lời sai**) | 6/1/4/1 |

**(iii) `xfb`: thắng.** Bằng `base` ở 5 bộ, bớt 1 câu trả lời sai ở compound. **`RAG_EXCERPT_FALLBACK_ENABLED` bật mặc định.** Flag này không có bộ đếm, nên số câu thật sự đi vào nhánh dự phòng chưa đo được; kết quả trên chỉ cho biết nó không đổi câu nào ở 5 bộ kia.
