# Ánh xạ corpus V2 → corpus v3 (Nova Digital)

Mỗi dòng cho biết nội dung của tài liệu cũ (corpus V2, bản 1.0) nay nằm ở đâu trong corpus v3. "Bỏ" nghĩa là không chuyển sang v3.

| Tài liệu V2 (bản 1.0) | Nội dung | Vị trí trong corpus v3 |
|---|---|---|
| ND-CORP-001 Giới thiệu và cơ cấu tổ chức | Hồ sơ doanh nghiệp, tầm nhìn, sứ mệnh, giá trị, sản phẩm, Ban Điều hành | ND-CORP-001 v2.0 (PUBLIC) |
| | Mục tiêu chiến lược 2026–2028, tầng quản trị, chức năng đơn vị, hội đồng, phân quyền, phối hợp | ND-ORG-001 v1.0, Mục 2–5 |
| | Đầu mối liên hệ (people@, servicedesk@, soc@, privacy@, legal@, compliance@, pmo@) | ND-ORG-001 v1.0, Mục 6 |
| | Danh mục tài liệu (mã cũ ND-HR-001/002/003, ND-SEC-001…, sai lệch với mã thật) | ND-ORG-001 v1.0, Mục 7 (danh mục mới, đúng mã) |
| | Câu hỏi tra cứu mẫu | Bỏ |
| ND-HR-002 Nội quy lao động | Điều 1–4, 9–43 (chuẩn mực, CNTT, ATVSLĐ, quấy rối, tài sản, điều chuyển, kỷ luật, thẩm quyền) | ND-HR-002 v2.0 (đánh số lại Điều 1–43) |
| | Điều 5 giờ làm (khung linh hoạt 08:00–09:30, mâu thuẫn với ND-HR-003) | Bỏ; chỉ còn dẫn chiếu ND-HR-003 v2.0, Mục 3 (08:00–09:00) |
| | Điều 6 làm từ xa, Điều 7 chấm công/đi muộn, Điều 8 làm thêm | ND-HR-003 v2.0, Mục 4, 6, 7, 8 |
| | Danh bạ khẩn cấp và phụ lục A2 (hr@, security@, máy lẻ 111/222) | ND-ORG-001 v1.0, Mục 6 (hr@ → people@, security@ → soc@) |
| | Phụ lục A3 câu hỏi mẫu | Bỏ |
| ND-HR-003 Làm việc và chấm công | Giờ làm, chấm công, điều chỉnh, remote, ca trực, đi muộn, kỳ công | ND-HR-003 v2.0 |
| | Bảng phân loại sự cố P1/P2 | ND-IT-001 v1.0, Mục 10 (mở rộng P1–P4) |
| | Câu hỏi gợi ý kiểm thử | Bỏ |
| ND-HR-004 Chính sách nghỉ | Toàn bộ | ND-HR-004 v2.0 (thêm Ngày Văn hóa Việt Nam 24/11, tổng 12 ngày lễ) |
| | Dẫn chiếu khiếu nại ND-HR-010 | ND-HR-002 v2.0, Chương XI |
| ND-HR-005 Lương, phụ cấp, thưởng | Nguyên tắc, kỳ trả lương, phụ cấp, OT, đánh giá lương, chương trình thưởng, khấu trừ, Payroll Query | ND-HR-005 v2.0 |
| | Dải lương N1–N6, hệ số thưởng hiệu suất | ND-COMP-001 v1.0 (CONFIDENTIAL) |
| | Mốc khóa công "ngày làm việc thứ 2/thứ 4" (mâu thuẫn với ND-HR-003) | Bỏ; dẫn chiếu ND-HR-003 v2.0, Mục 9 |
| ND-HR-006 Bảo hiểm và phúc lợi | Toàn bộ | ND-HR-006 v2.0 |
| | Mục 12 tình huống và câu hỏi kiểm thử, hộp "KIỂM THỬ RAG" | Bỏ |
| ND-HR-007 Tuyển dụng và tiếp nhận | Kế hoạch, ngân sách 2026, mở vị trí, sàng lọc, phỏng vấn, offer, tham chiếu, bảo mật hồ sơ, KPI | ND-HR-007 v2.0 (CONFIDENTIAL) |
| | Hồ sơ nhận việc, lộ trình hội nhập | ND-HR-011 v1.0 (INTERNAL) |
| UAT-LEAVE-AUTHORITY-001 (tài liệu mẫu, DRAFT) | – | Không chuyển sang v3 |

## Tài liệu mới hoàn toàn trong v3

| Mã | Phân loại | Ghi chú |
|---|---|---|
| ND-ORG-001 v1.0 | INTERNAL | Nguồn duy nhất về tổ chức, danh bạ, danh mục |
| ND-HR-011 v1.0 | INTERNAL | Hội nhập, thử việc (thời gian thử việc theo BLLĐ 2019) |
| ND-IT-001 v1.0 | INTERNAL | Lĩnh vực ngoài nhân sự: phân loại dữ liệu, mật khẩu, quyền truy cập, AI, thay đổi, lỗ hổng, sao lưu, sự cố |
| ND-COMP-001 v1.0 | CONFIDENTIAL | Dải lương, hệ số thưởng, mức điều chỉnh lương tham khảo |
| ND-HR-010 v1.0 | RESTRICTED | Hướng dẫn điều tra và xử lý kỷ luật |
| ND-EXEC-001 v1.0 | RESTRICTED | Kế hoạch nhân sự 2027, tái cấu trúc (mã EXEC-2027-R7) |
| ND-HR-003 v2.1 | INTERNAL | Bản thay thế ND-HR-003 v2.0 từ 01/01/2027: remote 03 ngày/tuần, đăng ký trước 12:00 |

## Ghi chú về bản trong repo

Bản gốc của owner còn một mục "Các giá trị dễ gây nhầm cần lưu ý khi soạn gold" (bảng câu hỏi và đáp án). Mục đó không đưa vào repo công khai: file trong repo không chứa câu hỏi hay gold. Bản đầy đủ nằm ở thư mục corpus v3 của owner.
