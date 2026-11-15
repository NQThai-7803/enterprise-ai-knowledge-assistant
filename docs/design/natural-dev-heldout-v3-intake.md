# Nhập `natural_dev_v1` và held-out v3 (DEC-026)

Chuẩn bị 2026-11-15. Owner thu câu hỏi từ nhóm; quy trình dưới đây giống held-out v2.

## Hai bộ, hai quyền dùng

| Bộ | Dùng để | Quy tắc |
|---|---|---|
| `natural_dev_v1` | thiết kế và chọn cấu hình (DEC-026 bước 3) | đo trên Actions như các bộ dev; câu và gold được đọc khi phân tích |
| held-out v3 | đo một lần ở mốc release | không dùng để thiết kế, không chạy trong phát triển (như DEC-012); chỉ chạy qua workflow release có owner duyệt |

Câu thu được chia ngẫu nhiên giữa hai bộ **trước khi** ai xem câu trả lời của hệ thống, để hai bộ cùng phân bố.

## Các bước

1. **Thu câu:** câu hỏi tự nhiên của người dùng thật, giữ nguyên văn (kể cả lỗi gõ, không dấu, tiếng Anh). Ghi `role` của người hỏi. Nên có cả câu trả lời được, câu một phần, câu tài liệu không có.
2. **Đóng băng câu hỏi:** `tests/acceptance/natural_dev_v1.yaml` (dev) và `docs/eval/heldout-v3-questions.yaml` (held-out), mỗi file một lock SHA256 (`.lock`, như `heldout-v2-questions.lock`), cả hai `eol=lf` trong `.gitattributes`. Sửa gì cũng phải ra phiên bản mới với lock mới.
3. **Fingerprints:** thêm hai nguồn vào `scripts/eval/question_leak.py` và build lại; từ đó `check_no_question_leak.py` chặn câu của hai bộ xuất hiện trong `app/`.
4. **Kiểm trùng** (chỉ báo số, không loại câu): 3-gram ký tự, difflib, 4-gram từ và e5 cosine với Q001-Q100, held-out v1, held-out v2 và các bộ dev, như `heldout_v2_check.py`. Ngưỡng chú ý: bề mặt ≥ 0,60, e5 ≥ 0,90.
5. **Gold từ PDF:** soạn chỉ từ các PDF của corpus, mỗi ý có `source_excerpt` được kiểm khớp đúng trang; các trường như held-out v2 (`gold_status`, `gold_answer`, `missing_points`, `gold_citations`, `forbidden`, `limited_pass`, `fail_examples`). Không chạy hệ thống trên bộ nào trước khi gold được duyệt.
6. **Owner duyệt và khóa gold** (`lock-gold`, như held-out v2). Với `natural_dev_v1`, runner dev chấm proxy theo gold đã khóa; với held-out v3, chỉ workflow release được chạy, và báo cáo tách nhóm gần UAT / còn lại.

## Công cụ cần khi có câu

- Tham số hóa `heldout_v2_check.py` và `heldout_v2_release.py` theo tên bộ (hiện chỉ có v2).
- Runner cho `natural_dev_v1` trong `eval.yml` (`set=natural`), chấm proxy như `run_answer_relevance_dev.py`.
