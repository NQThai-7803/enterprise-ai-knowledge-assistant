# CODEX START HERE

## Mục đích

Tài liệu này là điểm bắt đầu bắt buộc cho mọi phiên làm việc với Codex trong dự án **Enterprise AI Knowledge Assistant**.

Codex phải đọc các tài liệu theo thứ tự sau trước khi sửa code:

1. `CODEX_START_HERE.md`
2. `README.md`
3. `PROJECT_OVERVIEW.md`
4. `PRODUCT_REQUIREMENTS.md`
5. `ARCHITECTURE.md`
6. `DATABASE_DESIGN.md`
7. `API_SPEC.md`
8. `SECURITY.md`
9. `RAG_DESIGN.md`
10. `CODING_STANDARDS.md`
11. `TESTING_STRATEGY.md`
12. `PROJECT_ROADMAP.md`
13. `PROJECT_STATUS.md`
14. `TASKS.md`

## Quy tắc bắt buộc cho Codex

- Không tự ý thay đổi phạm vi dự án.
- Không tự thêm thư viện nếu chưa giải thích lý do.
- Không sửa nhiều module không liên quan trong cùng một task.
- Không xóa code đang hoạt động chỉ để viết lại theo sở thích.
- Không lưu secret, API key hoặc mật khẩu vào Git.
- Không bỏ qua migration khi thay đổi database.
- Không cho AI truy xuất tài liệu mà người dùng không có quyền xem.
- Không tạo câu trả lời không có nguồn nếu chức năng yêu cầu citation.
- Không giả định file, model hoặc cấu hình đã tồn tại; phải kiểm tra trước.
- Mỗi task phải có cách kiểm thử rõ ràng.
- Sau mỗi task phải cập nhật `PROJECT_STATUS.md` và `CHANGELOG.md`.

## Quy trình làm một task

1. Đọc task hiện tại trong `TASKS.md`.
2. Kiểm tra các file liên quan đang tồn tại.
3. Tóm tắt ngắn những gì sẽ thay đổi.
4. Thực hiện thay đổi nhỏ, có kiểm soát.
5. Chạy lint, test hoặc kiểm thử thủ công phù hợp.
6. Ghi lại file đã thêm/sửa.
7. Cập nhật `PROJECT_STATUS.md`.
8. Cập nhật `CHANGELOG.md`.
9. Báo rõ giới hạn hoặc lỗi còn tồn tại.

## Chuẩn đầu ra sau mỗi task

Codex phải báo cáo theo mẫu:

```text
TASK COMPLETED: <tên task>

Files created:
- ...

Files modified:
- ...

How to test:
1. ...
2. ...

Known limitations:
- ...

Documentation updated:
- PROJECT_STATUS.md
- CHANGELOG.md
```

## Quy tắc hỏi lại

Chỉ hỏi người dùng khi thiếu một trong các thông tin sau và không thể suy ra an toàn:

- API key hoặc lựa chọn nhà cung cấp LLM.
- File mẫu cần xử lý.
- Chính sách phân quyền chưa được định nghĩa.
- Thông tin triển khai thực tế như domain, server, cloud provider.
- Quyết định có ảnh hưởng lớn tới kiến trúc.

Nếu không thiếu các thông tin trên, Codex phải tiếp tục bằng phương án mặc định đã mô tả trong tài liệu.
