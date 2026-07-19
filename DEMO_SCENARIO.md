# MVP Demo Scenario

## 1. Seed users

- Admin toàn hệ thống.
- Manager phòng Nhân sự.
- Staff phòng Nhân sự.
- Staff phòng Kế toán.

## 2. Seed documents

- `Quy_che_nhan_su_2026.pdf` — scope DEPARTMENT, Human Resources.
- `Huong_dan_an_toan_thong_tin.pdf` — scope ORGANIZATION.
- `Bao_cao_tai_chinh_noi_bo.pdf` — scope DEPARTMENT, Accounting.

## 3. Demo flow

1. Admin đăng nhập và xem users.
2. Manager Nhân sự upload quy chế nhân sự.
3. UI/API hiển thị trạng thái UPLOADED → PROCESSING → READY.
4. Staff Nhân sự hỏi về nghỉ phép.
5. Hệ thống trả lời kèm file, trang và excerpt.
6. Staff Kế toán hỏi cùng câu hỏi.
7. Hệ thống không dùng tài liệu Nhân sự nếu Staff Kế toán không có quyền.
8. Staff hỏi một câu không tồn tại trong tài liệu.
9. Hệ thống trả fallback, không bịa.
10. Staff gửi feedback.
11. Admin xem audit log.

## 4. Demo success criteria

- Không có permission leakage.
- Citation mở được tài liệu đúng quyền.
- Document status rõ ràng.
- Lỗi provider được hiển thị an toàn.
- Audit log ghi nhận hành động quan trọng.
