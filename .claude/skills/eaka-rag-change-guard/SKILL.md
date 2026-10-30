---
name: eaka-rag-change-guard
description: Use BEFORE and AFTER any change to EAKA's RAG core — app/retrieval, app/chat, app/citations, grounded_answer_service, answer/citation validators — or anything touching ranking, prompts, or document permissions. Enforces no per-question logic, no permission leaks, flag-gated changes, and a dev-split held-out gate.
---

# EAKA RAG change guard

Lõi RAG là nơi rủi ro cao nhất của EAKA: sai một chỗ là lộ tài liệu (permission leak) hoặc trả lời bịa (false answer). Skill này là checklist bắt buộc cho mọi thay đổi trong phạm vi trên.

## Quy tắc bất biến (hard rules)

1. **Không viết logic riêng cho từng câu hỏi.** Không if/regex/dict theo nội dung câu hỏi cụ thể trong `tests/acceptance`, `uat/`, `eval/`. Sửa phải tổng quát.
2. **Không lộ tài liệu ngoài quyền.** Lọc theo quyền (permission filter) phải chạy *trước* khi chunk vào ranking, prompt hoặc citation — không lọc sau.
3. **Citation chỉ lấy từ chunk được phép** và đã thực sự đưa vào context.
4. Vi phạm 1 trong 3 quy tắc trên → dừng, báo người dùng, không "sửa tạm".

## Quy trình

### Trước khi sửa
1. Đọc phần liên quan, xác định module bị đụng.
2. Ghi baseline trên split **dev**:
   ```bash
   python run_heldout.py --split dev --out .eval/before.json   # chỉnh tham số theo repo
   ```
   **Không bao giờ chạy split `test`** trong quá trình phát triển. Split test chỉ chạy ở mốc release và phải có người duyệt.

### Khi sửa
3. Đặt mọi thay đổi hành vi sau một setting flag (ví dụ `EAKA_RAG_<FEATURE>_ENABLED`), **mặc định giữ hành vi cũ**.
4. Thêm flag vào `ENVIRONMENT_VARIABLES.md`: tên, kiểu, mặc định, ý nghĩa, thay đổi ở task nào.

### Sau khi sửa
5. Chạy kiểm tra hard-code câu hỏi:
   ```bash
   python .claude/skills/eaka-rag-change-guard/scripts/check_no_question_leak.py --base HEAD
   # hoặc với thay đổi đã stage:
   python .claude/skills/eaka-rag-change-guard/scripts/check_no_question_leak.py --staged
   ```
   Exit code ≠ 0 → xem từng match; nếu là trùng thật thì sửa lại cho tổng quát.
6. Chạy các file test bắt buộc theo bảng ánh xạ bên dưới (dùng skill `eaka-verify` để chạy trong môi trường chuẩn).
7. Chạy lại held-out với flag **bật**:
   ```bash
   python run_heldout.py --split dev --out .eval/after.json
   ```
8. Áp cổng quyết định (gate) dưới đây.

## Cổng đổi mặc định (default-flip gate)

Chỉ được đề xuất đổi mặc định của flag khi **đồng thời**:

| Chỉ số | Điều kiện |
|---|---|
| `permission_leak_count` | **= 0 tuyệt đối**, không dung sai |
| `false_answer_rate` | không tăng quá dung sai |
| `answer_accuracy` | không giảm quá dung sai |

Dung sai (tolerance): split dev nhỏ nên lệch 1 câu là nhiễu. Mặc định dung sai = **1 câu** (tức `1 / n_dev`). TODO: ghi `n_dev` thực tế của repo vào đây: `n_dev = ___`.

Nếu chênh lệch nằm trong dung sai mà không có cải thiện rõ ràng → giữ mặc định cũ, ghi nhận trong báo cáo.

## Bảng ánh xạ module → test bắt buộc

TODO: điền đường dẫn test thực tế của repo.

| Sửa ở | Phải chạy |
|---|---|
| `app/retrieval/` | `tests/...retrieval...`, test phân quyền |
| `app/chat/` | `tests/...chat...` |
| `app/citations/` | `tests/...citation...`, test phân quyền |
| `grounded_answer_service` | `tests/...grounded...`, acceptance liên quan |
| validators | `tests/...validator...` |
| Bất kỳ chỗ nào chạm permission | **toàn bộ** test permission leak |

## Báo cáo cuối task

- Flag mới + mặc định.
- Bảng before/after của 3 chỉ số (kèm `n_dev`).
- Kết quả `check_no_question_leak.py`.
- Test đã chạy + kết quả. Phần nào chưa kiểm chứng → mục **NOT_VERIFIED**.
