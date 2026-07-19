# Coding Standards

## 1. Python

- Python 3.12+.
- Type hints cho function và method public.
- Dùng `pathlib` thay vì ghép path thủ công.
- Không dùng mutable default arguments.
- Không catch `Exception` nếu không xử lý hoặc log có chủ đích.
- Function nên ngắn và có một trách nhiệm chính.

## 2. Formatting and lint

Đề xuất:

- Ruff cho lint và format.
- Pyright hoặc mypy cho type checking.
- Pytest cho test.

Codex không tự thêm tool khác nếu chưa cập nhật tài liệu.

## 3. Naming

- Module, function, variable: `snake_case`.
- Class: `PascalCase`.
- Constant: `UPPER_SNAKE_CASE`.
- Database table: plural `snake_case`.
- Enum value: uppercase string.

## 4. Project organization

- Router không chứa business logic.
- Service không trả `HTTPException` trực tiếp nếu có thể; dùng domain exception.
- Repository không phụ thuộc FastAPI.
- Schema request và response tách khỏi ORM model.
- Provider external nằm sau interface.

## 5. Database

- Mọi schema change có migration.
- Query list phải có pagination.
- Tránh N+1 query.
- Dùng transaction cho thay đổi nhiều bảng liên quan.
- Không expose ORM object trực tiếp nếu chứa field nhạy cảm.

## 6. Error handling

Tạo domain errors như:

- `ResourceNotFoundError`
- `PermissionDeniedError`
- `DocumentNotReadyError`
- `InvalidFileError`
- `ProviderUnavailableError`

Global exception handler chuyển thành error response chuẩn.

## 7. Logging

- Dùng structured logger.
- Không dùng `print` trong application code.
- Không log secret, token hoặc password.
- Log có request_id, user_id khi phù hợp.

## 8. Documentation

- Public module quan trọng có docstring ngắn.
- Không viết comment lặp lại code.
- Cập nhật tài liệu khi thay đổi behavior, endpoint hoặc schema.

## 9. Git commits

Đề xuất Conventional Commits:

```text
feat(auth): add JWT login
fix(rag): filter archived documents
refactor(documents): extract storage service
test(rbac): add department access tests
docs: update project status
```
