# FIX 3: chuẩn bị cho lỗi từ chối sai

Chỉ chẩn đoán, không sửa `app/`. Ngày 2026-11-08.

## Đếm trên dev hiện có

Nguồn: các trace đã có từ FIX 2 (`artifacts/fix2-diagnosis/`, image `fix1`, `strict`), gồm 100 câu UAT và 36 lượt RBAC. Không chạy lại hệ thống. `answer_relevance_dev_v1` chưa có trace nên không được đếm.

| Cơ chế | UAT Q001-Q100 | RBAC dev |
|---|---:|---:|
| `_filter_low_alignment_documents` loại chunk gold | không đo được | 0 |
| Validator đánh CONTRADICTED chỉ vì khác dạng số | 0 (trong 11 ca CONTRADICTED) | 0 |

- **UAT:** trace không có gold chunk, vì input của nó không kèm citation chuẩn, nên không đo được bộ lọc có loại chunk gold hay không.
- **RBAC:** gold được xác định theo trang, nên mọi đối chứng đều báo `_filter_non_answer_context_hits` loại "chunk gold". Tiêu chí theo trang quá thô để coi đó là chẩn đoán. Riêng `_filter_low_alignment_documents` thì không loại chunk nào.
- **Khác dạng số:** một ca được tính khi câu trả lời có con số không xuất hiện nguyên dạng trong nguồn, nhưng cùng giá trị sau khi bỏ số 0 ở đầu, bỏ dấu phân cách nghìn và quy đổi nghìn, triệu, tỷ. Ca có `zero_pad_probe` cho kết quả SUPPORTED cũng được tính. Không có ca nào.

Công cụ đếm nằm ở `fix3count.py` trong scratchpad của phiên, chưa commit.

**Kết luận:** dev hiện có không có ca nào cho hai cơ chế này, nên tôi soạn bộ mới.

## Bộ mới: `false_refusal_dev_v1`

- **File:** `tests/acceptance/false_refusal_dev_v1.yaml`, đã đóng băng: SHA256 `5214fd0e5ad97c7963cc6c8d2bbae6c0281ef718d37f228b5f6ed602d719a7ad` trong `false_refusal_dev_v1.lock`. **Chờ chủ dự án duyệt;** nếu cần sửa thì làm bản v1.1.
- **Quy mô:** 20 câu, trên 3 tài liệu tổng hợp của một công ty giả định mới. Soạn không xem câu hỏi hay gold của held-out nào.
- **Nhóm N, số khác dạng (6 câu phải trả lời, 4 câu phải từ chối):** câu trả lời đúng có thể viết số khác nguồn, như "01"/"1", "300.000 đồng"/"300 nghìn đồng", "70%"/"70 phần trăm". `fact_alternatives` liệt kê các dạng được chấp nhận.
- **Nhóm A, diễn đạt khác nguồn (6 câu phải trả lời, 4 câu phải từ chối):** câu hỏi dùng từ khác tài liệu, như "phòng lab" thay cho "phòng thí nghiệm", "loại ghế" thay cho "hạng vé", nên độ khớp từ vựng thấp. Câu phải từ chối giữ gần hết câu chữ nhưng hỏi một điều tài liệu không nêu.
- **Kiểm trùng:** dùng 3-gram ký tự, difflib và 4-gram từ với UAT, held-out v1, held-out v2, `answer_relevance_dev_v1` và RBAC dev. Lần đầu có 4 câu từ 0,60 trở lên, và 1 câu phải từ chối thực ra trả lời được từ tài liệu; tôi viết lại cả 4 trước khi khóa. Bản khóa cao nhất là 0,588 (với held-out v1), không câu nào từ 0,60.

## Chưa làm

- **Runner:** chưa có runner cho bộ này. `run_answer_relevance_dev.py` chỉ chấm một `fact` duy nhất, nên cần thêm phần chấm theo `fact_alternatives`.
- **Fingerprints:** bộ này chưa được thêm vào fingerprints của `question_leak.py`.
- **Trace:** chưa chạy trace, vì đây chỉ là bước chuẩn bị.
