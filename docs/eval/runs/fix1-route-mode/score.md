# FIX 1: chọn `RAG_DETERMINISTIC_ROUTE_MODE` (DEC-010)

Chạy ngày 2026-11-05 và 2026-11-06, image `eaka-backend:fix1` (commit `89417e7`), `reranker_mode = lexical_fallback`, model `qwen2.5:3b`, seed cố định. UAT chạy trên stack `eaka-p3d-uat`, RBAC trên `eaka-rbac-dev`. Điểm tự động: UAT là proxy (trạng thái và mã tài liệu cite), không phải chấm ngữ nghĩa.

## Kết luận

**Chọn `strict`.** Cả 3 mode đều 0 rò rỉ và không hồi quy trên Q001-Q100. Theo DEC-010 bản mới, `strict` ít câu trả lời sai nhất trên RBAC, và cũng nhiều câu đúng nhất.

| Mode | `permission_leak_count` | Q001-Q100 khớp proxy | RBAC trả lời sai (18 câu không có quyền) | RBAC đối chứng đạt (18) |
|---|---:|---:|---:|---:|
| `legacy` | 0 | 99/100 | 5 (RBD-03, 04, 05, 15, 18) | 4 (RBD-04, 05, 11, 16) |
| `strict` | 0 | 99/100 | 0 | 5 (RBD-04, 05, 11, 15, 16) |
| `off` | 0 | 99/100 | 1 (RBD-03) | 3 (RBD-11, 15, 16) |

Kiểm tra ở tầng retrieval cho cả 3 mode: 18/18 cặp kết luận được, không cặp nào rò rỉ.

## Q001-Q100

- Cả 3 mode: 97 ANSWERED, 3 NO_ANSWER, 0 INFRA_ERROR, không câu nào quá 120 giây. Câu lệch proxy duy nhất là Q033 (từ chối sai), giống nhau ở cả 3 mode.
- `strict` giống hệt `legacy` lượt 1 (trạng thái, citation, câu trả lời).
- `off` khác `legacy` ở nội dung Q094 và Q096, trạng thái không đổi. Hai câu này nằm trong đoạn chạy tiếp.

## Lượt `off`: bị ngắt và chạy tiếp

Lượt UAT của `off` bị ngắt sau Q092 và chạy tiếp từ Q093, chủ dự án đã chấp nhận. Giữa hai đoạn, container API được tạo lại từ cùng image, và model được warm-up lại trước Q093. Q093 mất 48 giây. `off-uat-metadata.json` ghi `run_note` và `interruption`.

## Giới hạn

- RBAC chỉ có 18 câu mỗi phía và mỗi mode chạy 1 lượt. **Đính chính 2026-11-06:** RBD-03 cũng trả lời sai dưới `strict` trong trace của FIX 2, nên số câu sai của `strict` nên đọc là 0 đến 1 (`docs/eval/runs/fix2-diagnosis.md`). Lựa chọn không đổi, vì `strict` đạt 5 đối chứng so với 3 của `off`.
- Tầng trả lời vẫn yếu: `strict` còn 12/18 đối chứng bị từ chối sai, và RBD-06 trả lời đúng thông tin nhưng cite sai tài liệu ở cả 3 mode.
- Đây không phải con số công bố. Con số công bố phải đo trên held-out v2.
