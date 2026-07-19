# Enterprise AI Knowledge Assistant

Hệ thống trợ lý AI nội bộ giúp doanh nghiệp upload, quản lý, tìm kiếm và hỏi đáp trên tài liệu bằng RAG, có phân quyền, citation, lịch sử chat, feedback và audit log.

## Mục tiêu chính

- Tập trung tài liệu nội bộ vào một hệ thống có kiểm soát.
- Cho phép người dùng hỏi đáp bằng ngôn ngữ tự nhiên.
- Chỉ sử dụng tài liệu mà người dùng được phép truy cập.
- Trả lời kèm tài liệu nguồn và số trang.
- Giảm hallucination bằng retrieval threshold và fallback rõ ràng.
- Theo dõi hoạt động bằng audit log.

## Vai trò

- **Admin:** quản lý người dùng, phòng ban, tài liệu, quyền và hệ thống.
- **Manager:** quản lý tài liệu và quy trình trong phạm vi phòng ban.
- **Staff:** tìm kiếm, chat, xem tài liệu và gửi feedback.

## Phạm vi MVP

1. Authentication bằng JWT.
2. RBAC cho Admin, Manager, Staff.
3. Quản lý người dùng và phòng ban.
4. Upload PDF.
5. Trích xuất text theo trang.
6. Chunking và embedding.
7. PostgreSQL + pgvector.
8. Hybrid retrieval cơ bản.
9. Chat với tài liệu.
10. Citation theo file và trang.
11. Lịch sử chat.
12. Feedback.
13. Audit log cơ bản.
14. Docker Compose.

## Công nghệ dự kiến

- Python 3.12+
- FastAPI
- SQLAlchemy 2
- Alembic
- PostgreSQL
- pgvector
- Redis
- Celery
- PyMuPDF
- React + TypeScript ở giai đoạn frontend
- Docker và Docker Compose

## Cấu trúc tài liệu

- `CODEX_START_HERE.md`: quy tắc làm việc cho Codex.
- `PROJECT_OVERVIEW.md`: tổng quan nghiệp vụ.
- `PRODUCT_REQUIREMENTS.md`: yêu cầu sản phẩm.
- `ARCHITECTURE.md`: kiến trúc hệ thống.
- `DATABASE_DESIGN.md`: thiết kế dữ liệu.
- `API_SPEC.md`: đặc tả API.
- `SECURITY.md`: nguyên tắc bảo mật.
- `RAG_DESIGN.md`: thiết kế pipeline AI/RAG.
- `SETUP.md`: hướng dẫn cài đặt.
- `PROJECT_ROADMAP.md`: lộ trình phát triển.
- `PROJECT_STATUS.md`: tiến độ hiện tại.
- `TASKS.md`: danh sách task triển khai.

## Thứ tự triển khai

```text
Project Setup
→ Database
→ Authentication
→ RBAC
→ User Management
→ Document Upload
→ Document Processing
→ Vector Search
→ AI Chat
→ Citation
→ Feedback
→ Audit Log
→ Frontend
→ Workflow
→ Deployment
```

## Trạng thái

Dự án đang ở giai đoạn chuẩn bị tài liệu và khởi tạo nền tảng.
