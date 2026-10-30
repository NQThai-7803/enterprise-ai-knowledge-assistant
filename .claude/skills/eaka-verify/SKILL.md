---
name: eaka-verify
description: Use when running or re-running EAKA tests or integration tests, comparing test results between runs, investigating "CI fail", or "test trong image". Runs tests in the canonical locked image with temporary pgvector/Redis, protects shared stacks, and classifies every failure.
---

# EAKA verify — chạy test an toàn trong môi trường chuẩn

## Nguyên tắc

- **Môi trường chuẩn = image build từ lock file.** Kết quả từ venv không pin chỉ để tham khảo, không dùng làm kết luận.
- **Tổ hợp marker lấy đúng từ `ci.yml`**, không tự chế. Đọc `ci.yml` trước mỗi lần chạy nếu file đã đổi.

## Tài nguyên được bảo vệ (KHÔNG BAO GIỜ đụng)

- V2, AUTH-02, stack EAKA gốc.
- **Không bao giờ `docker compose down -v`** trên các stack này.
- Trước khi xóa bất kỳ volume/container nào → liệt kê và **hỏi người dùng**.

## Hạ tầng tạm cho test

- DB pgvector tạm: `127.0.0.1:55499`.
- Redis: chọn cổng trống (kiểm tra trước, không đoán).
- Đặt tên container/project có tiền tố riêng (ví dụ `eaka-verify-`) để dọn đúng thứ mình tạo.
- Sau khi xong: dừng container tạm, liệt kê anonymous volume do mình tạo, **hỏi** rồi mới xóa.

## Quy trình

1. Build/lấy image từ lock.
2. Dựng pgvector + Redis tạm.
3. Chạy các lane theo `ci.yml` (dùng `scripts/run_ci_lanes.sh` nếu có), xuất JUnit XML cho mỗi lane vào `.verify/<run-id>/`.
4. Tóm tắt:
   ```bash
   python .claude/skills/eaka-verify/scripts/junit_summary.py .verify/<run-id>/*.xml
   ```
5. So với lần chạy trước (nếu có):
   ```bash
   python .claude/skills/eaka-verify/scripts/compare_junit.py .verify/<old>/ .verify/<new>/
   ```
6. Phân loại **mỗi** test fail vào đúng một nhóm:

   | Nhóm | Dấu hiệu |
   |---|---|
   | `stale-fixture` | fixture/dữ liệu mẫu lỗi thời so với code hiện tại |
   | `environment` | lỗi kết nối, cổng, version lib, thiếu service |
   | `real-logic` | lỗi logic thật trong code |
   | `host-only-file` | test phụ thuộc file chỉ có trên host, không có trong image |

7. Dọn hạ tầng tạm (hỏi trước khi xóa volume).

## Báo cáo

- Bảng pass/fail/xfail theo file (từ `junit_summary.py`).
- Khác biệt so với lần trước (từ `compare_junit.py`).
- Danh sách fail kèm nhóm phân loại và bằng chứng (evidence) ngắn.
- Phần nào chạy ngoài image chuẩn hoặc chưa kiểm chứng → mục **NOT_VERIFIED**.
