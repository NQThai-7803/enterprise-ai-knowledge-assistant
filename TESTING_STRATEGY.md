# Testing Strategy

## 1. Test levels

### Unit tests

- Security helpers.
- Permission policies.
- Chunking.
- Prompt builder.
- Citation parser/validator.
- Text normalization.

### Integration tests

- Repository với PostgreSQL test database.
- Login và refresh flow.
- Document CRUD.
- Permission-aware list và retrieval.
- Celery task ở eager/test mode nếu phù hợp.

### API tests

- Status code.
- Response schema.
- Role restrictions.
- Pagination và validation.

### RAG evaluation tests

- Known answer.
- No answer.
- Unauthorized source.
- Exact keyword.
- Multi-page answer.

## 2. Critical security tests

1. Staff không gọi được user management.
2. Staff phòng A không xem document phòng B.
3. Search không trả title của tài liệu trái quyền.
4. Retrieval không trả chunk trái quyền.
5. Citation không expose document trái quyền.
6. User không xem chat session của người khác.
7. Deleted hoặc archived document không được retrieve.

## 3. Fixtures

Tạo fixtures:

- admin_user
- manager_department_a
- staff_department_a
- staff_department_b
- organization_document
- department_a_document
- private_document
- ready_document_chunks

## 4. Test naming

```python
def test_staff_cannot_access_admin_user_list(): ...
def test_retrieval_excludes_other_department_chunks(): ...
def test_chat_returns_no_answer_when_score_below_threshold(): ...
```

## 5. Mocking

Mock external provider:

- Embedding API.
- LLM API.
- Object storage.

Không mock permission query trong integration test quan trọng.

## 6. Coverage priority

Ưu tiên coverage cao cho:

- auth
- RBAC
- document permission
- retrieval
- citation validation

Coverage tổng chỉ là chỉ báo; không thay thế test case nghiệp vụ.

## 7. Manual acceptance test

Mỗi task phải ghi cách test bằng Swagger hoặc command line nếu chưa có frontend.
