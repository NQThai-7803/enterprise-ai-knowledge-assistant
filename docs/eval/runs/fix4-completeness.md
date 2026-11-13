# FIX 4 (i): vòng thử lại sau check độ đầy đủ

Nhánh `feat/fix-4-completeness`. Chẩn đoán gốc: `docs/design/pipeline-loss-fix-plan.md` (trace `false_refusal_dev_v2`, run `42802589033`). Thứ tự do owner duyệt (DEC-021).

## Check này là gì và vì sao tồn tại

- **Code:** `_should_retry_incomplete_answer` (`app/services/grounded_answer_service.py`, nay gọi `_incomplete_answer_reason`), 15 check con. Gọi sau khi câu trả lời đầu **đã qua** citation validation và claim validation (`_prepare_answer_draft`).
- **Nguồn gốc:** TASK-034.1.1 (`206cee3`, 2026-08-14, "rag accuracy and context quality"), mở rộng trong RAG-H5.2. Mục đích: chặn câu trả lời **thiếu** trên Q001-Q100 với model 3B: hỏi người mà không nêu tên, hỏi số mà không có số của dòng đúng, hỏi khoảng mà thiếu một đầu, câu hỏi yes/no mà không có "có/không", số thiếu đơn vị.
- **Khi check bác:** hệ thống sinh lại (`_answer_quality_retry_messages`). Lần sinh lại hỏng, bị từ chối hoặc vẫn thiếu thì trả NO_ANSWER; lần sinh lại qua check thì **thay** câu đầu, kể cả khi nó tệ hơn.

## Vì sao nó bác câu đúng ở 5 ca đã trace (tái hiện local bằng nguyên chunk)

| Ca | Check bác | Nguyên nhân | Sau đó |
|---|---|---|---|
| FR2-F01 | `_yes_no_answer_missing_polarity` | `analyze_question` xếp câu "…mấy lần một năm?" vào YES_NO (lỗi phân loại ý định, thuộc NLU) | thử lại: `"answer": [SOURCE_1]` → lỗi citation → NO_ANSWER |
| FR2-F02 | `_quantity_answer_missing_source_number` | `_question_focused_source_number_unit_pairs` chọn cặp số của **tài liệu khác** trong context (12 tháng, 6 tháng); câu trả lời "2 lần" không chứa chúng | thử lại: LLM chép số tài liệu khác → thiếu đơn vị → NO_ANSWER |
| FR2-L03 | `_quantity_answer_missing_source_number` | như trên (1 quý, 24 tháng, 3 mét) | thử lại: 4 con số của tài liệu khác, qua check, **thay câu đúng** → trả lời sai |
| FR2-E01 | `_numeric_answer_missing_source_unit` | `\d+` cắt "2.500 kg" thành "2" và "500"; "2" có đơn vị "lần" trong nguồn, câu trả lời không có "lần" | thử lại hỏng định dạng → NO_ANSWER |
| (HO-035, held-out v1, chỉ chẩn đoán) | `missing_numeric_unit` | cùng lỗi cắt số "1.200.000" | — |

**Đính chính so với kế hoạch PROMPT 6:** check số lượng đã bỏ số 0 ở đầu (`int()`), nên "01"/"1" không phải nguyên nhân ở F02; nguyên nhân là chọn nhầm cặp số của tài liệu khác.

## Flag (mặc định tắt)

| Flag | Biến eval | Hành vi |
|---|---|---|
| `RAG_COMPLETENESS_NUMBER_NORMALIZATION_ENABLED` | `EVAL_COMPLETENESS_NUMBERS` | (1) số có nhóm hàng nghìn là **một** số trong check đơn vị, khi nguồn có đúng giá trị đó (dùng `canonical_number_unit_pairs` của F) |
| `RAG_KEEP_VALIDATED_FIRST_ANSWER_ENABLED` | `EVAL_KEEP_FIRST_ANSWER` | (2) câu đầu đã ANSWERED (qua citation và claim validation) và chỉ bị bác vì **hình thức** (`yes_no_missing_leading_polarity`, `missing_quantity_number`, `missing_numeric_unit`): nếu thử lại hỏng, bị từ chối hoặc vẫn thiếu thì trả câu đầu thay vì NO_ANSWER |
| `RAG_RETRY_MUST_KEEP_VALIDATED_VALUES_ENABLED` | `EVAL_RETRY_KEEPS_VALUES` | (3) lần thử lại qua check nhưng không còn giá trị nào của câu đầu **và** cite chunk khác thì không được thay câu đầu |

- Các lý do về **nội dung** (lệch dòng/điều khoản, thiếu tên người, thiếu đầu khoảng, placeholder, thiếu giá trị của câu ghép) không thuộc (2): ở đó check nói câu trả lời sai, không chỉ sai hình thức.
- Không flag nào nới validator: câu được giữ luôn là câu đã SUPPORTED.
- Phương án "chỉ yêu cầu bổ sung phần thiếu" chưa làm: cần prompt mới, và với model 3B mọi lần sinh thêm đều là rủi ro đã thấy. (2) chọn cách không phụ thuộc lần sinh lại.
- Counter: `first_answer_kept`, `retry_abandoned_first`.

## Đợt đo và quy tắc chọn (DEC-011, DEC-013; viết trước khi đo)

- **Cấu hình, cùng job, 2 lượt xen kẽ:** `base`, `c1` (1), `c2` (2), `c3` (3), `all` (1+2+3).
- **Bộ:** UAT Q001-Q100, RBAC dev, `answer_relevance_dev_v1`, `false_refusal_dev_v1`, `false_refusal_dev_v2`, `compound_partial_dev_v1` (mới; 6 câu "nửa trả lời được" được kỳ vọng **không đạt** ở mọi cấu hình cho tới khi làm C, bộ này ở đây để phát hiện trả lời sai tăng).
- **Bắt buộc:** 0 rò rỉ; UAT không hồi quy (dung sai 1 câu); trả lời sai không tăng ở **bất kỳ** bộ nào.
- **So từng bộ với `base`:** (a) ít trả lời sai hơn, rồi (b) nhiều câu đúng hơn. Thắng khi không tệ hơn ở mọi bộ và tốt hơn ở ít nhất một bộ. Chỉ tính thay đổi ở cả 2 lượt; báo id mọi câu tệ đi và số ca vào nhánh (counter).
- **Chọn mặc định:** cấu hình thắng `base` và không thua cấu hình thắng nào khác ở bộ nào. Ưu tiên `all` nếu nó thắng và không thua từng flag riêng; nếu không có cấu hình trội thì owner quyết định. Flag giữ lại để rollback.
