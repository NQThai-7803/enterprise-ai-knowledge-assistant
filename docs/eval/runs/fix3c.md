# FIX 3c: các cơ chế từ chối sai F, C, A

Chẩn đoán gốc: `docs/eval/runs/fix3b-diagnosis.md`. Làm theo thứ tự F, rồi C, rồi A. Mỗi cơ chế có một flag, mặc định tắt, đo cùng đợt với baseline trên GitHub Actions (CPU, Ollama 0.40.15), 2 lượt. Năm bộ đo: UAT Q001-Q100, RBAC dev, `answer_relevance_dev_v1`, `false_refusal_dev_v1`, `false_refusal_dev_v2`. E (câu hỏi tiếng Anh) và M3 để sang giai đoạn NLU.

**Quy tắc chọn (DEC-013, viết trước mỗi đợt đo):**

1. **Bắt buộc:**
   - 0 rò rỉ (API và retrieval);
   - UAT không hồi quy (dung sai 1 câu theo `eaka-rag-change-guard`);
   - trả lời sai không tăng ở bất kỳ bộ nào.
2. **So với `base`, từng bộ một:** (a) ít trả lời sai hơn, rồi (b) nhiều câu đúng hơn. Flag chỉ thắng khi không tệ hơn ở mọi bộ và tốt hơn ở ít nhất một bộ.
3. **Cách đếm:** chỉ tính thay đổi xuất hiện ở cả 2 lượt, và báo theo id mọi câu bị tệ đi. Báo số ca đi vào nhánh mới, khi nhánh đó có counter.
4. **Nếu thắng:** bật mặc định, giữ flag để rollback, merge, rồi mới đến cơ chế sau. Baseline của cơ chế sau là mặc định mới.

## F: chuẩn hoá số và đơn vị trước khi so

- **Flag:** `RAG_NUMBER_NORMALIZATION_ENABLED` (`EVAL_NUMBER_NORMALIZATION`).
- **Phạm vi:** chỉ `_numbers_are_contradicted`. Số được viết lại theo một cách duy nhất trước khi so:
  - bỏ số 0 ở đầu;
  - bỏ dấu phân cách hàng nghìn (nhóm 3 chữ số sau `.` hoặc `,`);
  - đổi dấu phẩy thập phân thành dấu chấm;
  - nhân hệ số của các từ `nghìn`/`ngàn`/`triệu`/`tỷ` (và `thousand`/`million`/`billion`);
  - coi `đ`/`đồng`/`VND`/`₫` là một đơn vị.
- **Không so phần chu kỳ** sau đơn vị (`/năm`, `mỗi năm`), nên `01 lần/năm` bằng `1 lần mỗi năm`. Phần này vốn cũng không được so trước đó.
- **Giới hạn:** trong một khoảng như "3 - 15 triệu", hệ số chỉ áp vào số đứng sát nó.
- **Ca mục tiêu:** HO-012, HO-013 (held-out v1, chỉ để chẩn đoán) và nhóm F của `false_refusal_dev_v2`.
- **Cấu hình:** `base`, `f:EVAL_NUMBER_NORMALIZATION=true`.
