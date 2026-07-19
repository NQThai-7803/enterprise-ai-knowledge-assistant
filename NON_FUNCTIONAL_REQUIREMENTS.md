# Non-Functional Requirements

## 1. Security

- Password phải được hash bằng thuật toán phù hợp.
- Secret chỉ đọc từ environment variables.
- API phải xác thực và phân quyền ở backend.
- File upload phải được validate.
- Không log nội dung nhạy cảm, password, token hoặc API key.
- Retrieval phải lọc quyền trước khi gửi context cho LLM.

## 2. Performance

Mục tiêu MVP:

- API CRUD thông thường: p95 dưới 500 ms trong môi trường local phù hợp.
- Chat không tính thời gian nhà cung cấp LLM: retrieval dưới 2 giây với tập dữ liệu demo.
- Upload trả response nhanh và xử lý bất đồng bộ.
- Có pagination cho list endpoint.

## 3. Reliability

- Task xử lý tài liệu có retry có giới hạn.
- Trạng thái tài liệu phải phản ánh đúng bước xử lý.
- Transaction phải rollback khi lỗi.
- Migration phải có khả năng chạy lặp an toàn theo phiên bản.

## 4. Maintainability

- Tách router, service, repository và model.
- Không để business logic trong router.
- Mỗi module có test tương ứng.
- Type hint cho public function.
- Code format và lint tự động.

## 5. Observability

- Structured logging.
- Correlation/request ID.
- Log thời gian xử lý document và chat.
- Ghi token usage khi dùng API LLM.
- Health check cho database và Redis.

## 6. Scalability

- Backend stateless ngoại trừ external services.
- Worker có thể scale độc lập.
- File storage có abstraction để thay local bằng object storage.
- Embedding provider và LLM provider có interface thay thế.

## 7. Compatibility

- Phát triển trên Windows với Visual Studio Code.
- Chạy dịch vụ phụ trợ bằng Docker Compose.
- Backend có thể chạy local bằng virtual environment.
