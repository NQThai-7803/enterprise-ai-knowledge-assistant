# Development Guide

## 1. Branch strategy

- `main`: ổn định.
- `develop`: tùy chọn khi dự án lớn hơn.
- Feature branch: `feature/<name>`.
- Fix branch: `fix/<name>`.

## 2. Task size

Một task tốt nên:

- Hoàn thành trong phạm vi nhỏ.
- Có acceptance criteria.
- Có test.
- Không trộn refactor lớn với feature mới.

## 3. Definition of Done

Task hoàn thành khi:

- Code chạy.
- Test liên quan pass.
- Không có lint error mới.
- Migration được tạo nếu cần.
- API docs/schema đúng.
- Security impact đã kiểm tra.
- `PROJECT_STATUS.md` cập nhật.
- `CHANGELOG.md` cập nhật.

## 4. Review checklist

- Có lộ secret không?
- Có bypass permission không?
- Có truy vấn N+1 không?
- Có xử lý lỗi không?
- Có test case trái quyền không?
- Có làm thay đổi API contract không?
- Có cập nhật docs không?

## 5. Seed data

Chỉ tạo seed cho development:

- 1 Admin.
- 2 departments.
- 1 Manager mỗi department.
- 1 Staff mỗi department.

Không hard-code password production.
