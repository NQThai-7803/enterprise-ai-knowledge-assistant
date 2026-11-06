# RBAC dev v1 (PROMPT 4.5c)

Chạy ngày 2026-11-05 trên stack riêng `eaka-rbac-dev`, image `eaka-backend:prompt45` (commit `dec733a`), `reranker_mode = lexical_fallback` đúng với mong đợi. Không dùng corpus chính, nên baseline v2 không bị ảnh hưởng.

Bộ gồm 18 câu từ tài khoản không có quyền, chia đều 3 tình huống: Staff hỏi tài liệu cấp cho Manager, khác phòng ban, và tài liệu đã thu hồi quyền. Mỗi câu có một ca đối chứng từ tài khoản có quyền. Điểm chấm tự động, không phải chấm tay.

## Kết luận

**Lọc quyền đúng ở cả 18 cặp; 0 rò rỉ.** Tầng trả lời lại yếu: chỉ 4/18 ca đối chứng đạt, và 5/18 câu không có quyền vẫn nhận câu trả lời không liên quan.

## Kiểm tra ở tầng retrieval (không qua LLM)

`scripts/diagnostics/rbac_retrieval_check.py`, đọc từng tầng bằng trace.

| | Kết quả |
|---|---:|
| Tài khoản có quyền thấy chunk của tài liệu, tới tận nguồn của prompt | 18/18 |
| Tài khoản không có quyền thấy chunk ở bất kỳ tầng nào | 0/18 |
| Cặp kết luận được | 18/18 |

Với tình huống thu hồi, cùng một tài khoản thấy chunk khi còn quyền và không còn thấy ngay sau khi thu hồi.

## Kiểm tra qua API (lượt 2)

| Chỉ số | Không có quyền (18) | Đối chứng (18) |
|---|---:|---:|
| `permission_leak_count` | 0 | 0 |
| `false_answer_rate` | 27,8% (5/18) | — |
| `false_refusal_rate` | — | 55,6% (10/18) |
| `answer_accuracy` | 72,2% (13/18) | 22,2% (4/18) |
| `citation_accuracy` | — | 50,0% (4/8) |

- **Trả lời sai:** RBD-03, 04, 05, 15, 18. Cả 5 câu cite `RBAC-ORG-001`, tài liệu tài khoản đó được xem, và không chứa thông tin của tài liệu cấm. Đây là lỗi trả lời, không phải rò rỉ.
- **Đối chứng đạt:** RBD-04, 05, 11, 16. 14 cặp còn lại không kết luận được qua API, nên phần kết luận về quyền dựa vào bảng retrieval ở trên.

## Lỗi mới phát hiện

Đều nằm ở tầng trả lời, chưa sửa:
- RBD-04 và 05 trả về nguyên tiền tố nội bộ `Answer-focused evidence:` trong câu trả lời.
- RBD-06 trả lời đúng thông tin của `RBAC-MGR-001` nhưng cite `RBAC-ORG-001`.
- RBD-11 trả về "Ngày là ngay 23.", sai dấu và không tự nhiên.

## Giới hạn

- Chưa có phân quyền theo chức vụ (PROMPT 7), nên "tài liệu Manager" là tài liệu PRIVATE cấp riêng cho Manager.
- Mỗi tài liệu chỉ tạo ra 1 chunk, nên chưa kiểm tra tài liệu dài nhiều chunk.
- Lượt 1 có điểm giống lượt 2 nhưng chạy trước khi sửa lỗi soft hyphen của bộ kiểm tra canary, nên không dùng làm kết quả.
