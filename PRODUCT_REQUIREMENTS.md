# Product Requirements Document

## 1. Tầm nhìn

Xây dựng trợ lý tri thức nội bộ đáng tin cậy, dễ dùng và có thể kiểm toán, giúp nhân viên tiếp cận đúng thông tin trong thời gian ngắn.

## 2. Mục tiêu sản phẩm

- Giảm thời gian tìm tài liệu.
- Tăng khả năng tái sử dụng kiến thức nội bộ.
- Giảm trả lời sai hoặc không có nguồn.
- Bảo vệ tài liệu theo role và department.
- Hỗ trợ quản trị và đánh giá chất lượng câu trả lời.

## 3. User stories

### Authentication

- Là người dùng, tôi muốn đăng nhập để truy cập chức năng đúng quyền.
- Là người dùng, tôi muốn refresh token khi access token hết hạn.
- Là Admin, tôi muốn khóa tài khoản để ngăn truy cập.

### User management

- Là Admin, tôi muốn tạo người dùng và gán role.
- Là Admin, tôi muốn gán người dùng vào department.
- Là Admin, tôi muốn xem trạng thái active/inactive.

### Document management

- Là người có quyền, tôi muốn upload PDF.
- Là người upload, tôi muốn xem trạng thái xử lý.
- Là Admin hoặc Manager, tôi muốn cập nhật metadata.
- Là người dùng, tôi chỉ muốn thấy tài liệu mình được phép xem.

### AI chat

- Là Staff, tôi muốn đặt câu hỏi bằng tiếng Việt.
- Là Staff, tôi muốn nhận câu trả lời kèm nguồn.
- Là Staff, tôi muốn mở đúng trang tài liệu liên quan.
- Là Staff, tôi muốn được thông báo rõ nếu hệ thống không đủ dữ liệu.

### Feedback

- Là người dùng, tôi muốn đánh giá câu trả lời.
- Là Manager, tôi muốn xem phản hồi tiêu cực để cải thiện dữ liệu.

### Audit

- Là Admin, tôi muốn biết ai upload, xem, tải hoặc xóa tài liệu.

## 4. Yêu cầu chức năng MVP

### FR-001 Authentication

- Login bằng email và password.
- Password được hash.
- Access token ngắn hạn.
- Refresh token có thể thu hồi.
- Tài khoản inactive không được đăng nhập.

### FR-002 RBAC

- Role mặc định: ADMIN, MANAGER, STAFF.
- Endpoint phải kiểm tra role.
- Document retrieval phải kiểm tra quyền ở tầng database query.

### FR-003 Document upload

- Hỗ trợ PDF ở MVP.
- Giới hạn dung lượng qua config.
- Validate MIME type và phần mở rộng.
- Lưu checksum để hỗ trợ phát hiện file trùng.
- Có trạng thái UPLOADED, PROCESSING, READY, FAILED, ARCHIVED.

### FR-004 Document processing

- Trích xuất text theo trang.
- Phát hiện trang không có text.
- Làm sạch nội dung.
- Chia chunk có metadata.
- Tạo embeddings.

### FR-005 Retrieval

- Semantic search bằng pgvector.
- Keyword search cơ bản.
- Lọc theo quyền trước khi trả kết quả.
- Hỗ trợ top-k và minimum score qua config.

### FR-006 Chat

- Tạo chat session.
- Lưu user message và assistant message.
- Hỗ trợ lịch sử ngắn hạn.
- Trả answer, citations, response time và confidence label.

### FR-007 Citation

- Citation chứa document_id, title, page_number, chunk_id và excerpt.
- Backend xác thực citation tồn tại.
- Không cho citation tới tài liệu trái quyền.

### FR-008 Feedback

- Hỗ trợ helpful, not_helpful và reason.
- Một người dùng có thể cập nhật feedback của mình cho một message.

### FR-009 Audit log

- Ghi lại login, upload, view, download, delete, permission change và chat access quan trọng.

## 5. Yêu cầu giai đoạn mở rộng

- OCR.
- DOCX, XLSX, TXT.
- Document versioning.
- Workflow approval.
- Notifications.
- Contract comparison.
- Expiration reminder.
- Google Drive integration.
- Advanced analytics.

## 6. Acceptance criteria chung

- API có schema rõ ràng.
- Mọi lỗi nghiệp vụ dùng error code nhất quán.
- Không trả stack trace cho client.
- Tài liệu trái quyền không xuất hiện trong list, search hoặc chat.
- Mỗi task có test hoặc hướng dẫn kiểm thử.
