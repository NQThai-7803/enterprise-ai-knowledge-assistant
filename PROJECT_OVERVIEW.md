# Project Overview

## 1. Tên dự án

**Enterprise AI Knowledge Assistant**

Repository đề xuất: `enterprise-ai-knowledge-assistant`

## 2. Bài toán

Tài liệu doanh nghiệp thường phân tán ở nhiều thư mục, định dạng và phòng ban. Nhân viên mất thời gian tìm kiếm, dễ dùng nhầm phiên bản và khó xác định nguồn thông tin.

Hệ thống này cung cấp một lớp quản lý tài liệu và trợ lý AI giúp:

- Upload và tổ chức tài liệu.
- Gán quyền truy cập.
- Tìm kiếm theo từ khóa và ngữ nghĩa.
- Hỏi đáp dựa trên tài liệu nội bộ.
- Trả lời có citation.
- Ghi nhận lịch sử và feedback.

## 3. Người dùng mục tiêu

- Doanh nghiệp nhỏ và vừa.
- Phòng nhân sự.
- Phòng pháp chế.
- Phòng kỹ thuật.
- Bộ phận chăm sóc khách hàng.
- Bộ phận vận hành.

## 4. Use case cốt lõi

### Admin

- Đăng nhập.
- Tạo và khóa tài khoản.
- Quản lý role và department.
- Upload và quản lý tài liệu.
- Thiết lập quyền truy cập.
- Xem audit log.
- Xem trạng thái xử lý tài liệu.

### Manager

- Upload tài liệu cho phòng ban.
- Chỉnh sửa metadata.
- Xem và quản lý tài liệu thuộc phạm vi phụ trách.
- Xem feedback của người dùng.
- Duyệt tài liệu ở giai đoạn mở rộng.

### Staff

- Xem danh sách tài liệu được phép truy cập.
- Hỏi AI về nội dung tài liệu.
- Xem citation.
- Mở đúng tài liệu và trang tham chiếu.
- Xem lịch sử chat.
- Đánh giá câu trả lời.

## 5. Luồng nghiệp vụ chính

### Luồng nhập tài liệu

```text
User uploads PDF
→ Validate file
→ Save metadata
→ Save original file
→ Queue processing task
→ Extract text by page
→ Clean text
→ Split into chunks
→ Create embeddings
→ Save chunks and vectors
→ Mark document READY
```

### Luồng hỏi đáp

```text
User asks question
→ Authenticate user
→ Resolve accessible documents
→ Normalize question
→ Retrieve candidate chunks
→ Rerank results
→ Apply relevance threshold
→ Build grounded prompt
→ Call LLM
→ Validate citations
→ Save history and metrics
→ Return answer with sources
```

## 6. Phạm vi không làm trong MVP

- Agent tự động gửi email.
- Workflow phê duyệt phức tạp.
- Đồng bộ Google Drive hoặc OneDrive.
- Multi-tenant SaaS hoàn chỉnh.
- Fine-tuning mô hình.
- Voice input.
- Mobile application.
- Billing.

## 7. Tiêu chí thành công MVP

- Người dùng đăng nhập và bị giới hạn đúng quyền.
- PDF được xử lý thành công và có trạng thái rõ ràng.
- Câu hỏi phù hợp trả về câu trả lời có citation.
- Câu hỏi không có dữ liệu trả về fallback, không bịa.
- Người dùng không thể truy xuất chunk thuộc tài liệu trái quyền.
- Có test cho authentication, permission và retrieval.
