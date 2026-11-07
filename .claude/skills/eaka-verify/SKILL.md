---
name: eaka-verify
description: Use before reporting any EAKA task as done, and when running or re-running EAKA tests or integration tests, comparing test results between runs, investigating "CI fail", or "test trong image". Takes precedence over general verification skills. Runs tests in the canonical locked image with temporary pgvector/Redis, protects shared stacks, and classifies every failure.
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

- `scripts/test/compose.integration.yaml` dựng pgvector và Redis tạm trên mạng riêng, không publish cổng, dữ liệu nằm trên tmpfs.
- Đặt tên project có tiền tố riêng (ví dụ `eaka-verify-`) để dọn đúng thứ mình tạo.
- Sau khi xong: dừng container tạm, liệt kê anonymous volume do mình tạo, **hỏi** rồi mới xóa.

## Quy trình

1. Build image từ `git archive` của đúng commit cần kiểm, đặt ngoài thư mục OneDrive, với `docker build --target test`: thư mục làm việc có thể lỗi do file placeholder, và bản export chứng minh image khớp commit. Đọc kết quả trước khi chạy bất kỳ việc gì phụ thuộc vào nó, như push.
2. Dựng pgvector + Redis tạm bằng `scripts/test/compose.integration.yaml` với `-p eaka-verify-<tên>`; stack này không publish cổng.
3. Chạy các lane theo `ci.yml`, xuất JUnit XML cho mỗi lane vào `.verify/<run-id>/`. Lane unit cần mount `docs/` chỉ đọc (`-v <repo>/docs:/app/docs:ro`) vì image không có thư mục này; ghi mount đó trong báo cáo. Xanh nghĩa là 0 test fail trong lane đã chạy.
   Đặt giới hạn thời gian đủ dài: `timeout` chỉ dừng client, container test vẫn chạy tiếp. Nếu lượt bị ngắt, dọn container `eaka-verify-<tên>` trước khi chạy lại, vì hai lượt dùng chung một database sẽ làm hàng loạt test fail giả.
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
