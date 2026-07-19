# Functional Requirements

## 1. Authentication and Session

| ID | Requirement | Priority |
|---|---|---|
| AUTH-01 | Đăng nhập bằng email và mật khẩu | Must |
| AUTH-02 | Cấp access token và refresh token | Must |
| AUTH-03 | Thu hồi refresh token khi logout | Must |
| AUTH-04 | Khóa đăng nhập khi user inactive | Must |
| AUTH-05 | Rate limit login thất bại | Should |

## 2. User and Department

| ID | Requirement | Priority |
|---|---|---|
| USER-01 | Admin tạo, sửa, khóa user | Must |
| USER-02 | Gán role cho user | Must |
| USER-03 | Gán department cho user | Must |
| USER-04 | Tìm kiếm và phân trang user | Should |

## 3. Documents

| ID | Requirement | Priority |
|---|---|---|
| DOC-01 | Upload PDF | Must |
| DOC-02 | Xem trạng thái xử lý | Must |
| DOC-03 | Danh sách tài liệu theo quyền | Must |
| DOC-04 | Soft delete tài liệu | Must |
| DOC-05 | Reprocess tài liệu lỗi | Should |
| DOC-06 | Cập nhật title, description, access scope | Must |

## 4. Processing

| ID | Requirement | Priority |
|---|---|---|
| PROC-01 | Extract text theo page | Must |
| PROC-02 | Clean text | Must |
| PROC-03 | Chunking có overlap | Must |
| PROC-04 | Embedding và lưu pgvector | Must |
| PROC-05 | Retry task thất bại | Should |

## 5. Search and RAG

| ID | Requirement | Priority |
|---|---|---|
| RAG-01 | Semantic search | Must |
| RAG-02 | Keyword search | Should |
| RAG-03 | Permission-aware retrieval | Must |
| RAG-04 | Relevance threshold | Must |
| RAG-05 | Reranking | Should |
| RAG-06 | Grounded prompt | Must |
| RAG-07 | Citation validation | Must |

## 6. Chat

| ID | Requirement | Priority |
|---|---|---|
| CHAT-01 | Tạo session | Must |
| CHAT-02 | Gửi câu hỏi | Must |
| CHAT-03 | Xem lịch sử session | Must |
| CHAT-04 | Xóa hoặc archive session | Should |
| CHAT-05 | Rename session | Could |

## 7. Feedback and Audit

| ID | Requirement | Priority |
|---|---|---|
| FB-01 | Đánh giá helpful/not helpful | Must |
| FB-02 | Ghi lý do | Should |
| AUDIT-01 | Lưu hành động quan trọng | Must |
| AUDIT-02 | Admin lọc audit log | Should |
