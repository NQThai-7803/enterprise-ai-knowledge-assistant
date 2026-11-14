# FIX 4 (iv): câu hỏi ghép trả lời một phần (DEC-021)

Viết 2026-11-14, **trước mọi lần đo** của mục này.

## Cơ chế

- Hiện tại: câu hỏi ghép chỉ được trả lời khi **mọi** ý đều qua validator (sau vòng sửa); thiếu một ý là NO_ANSWER cả câu.
- `RAG_COMPOUND_PARTIAL_ANSWER_ENABLED` (mặc định tắt): khi ít nhất một ý đã được xác thực và các ý còn lại vẫn hỏng sau vòng sửa, câu trả lời gồm các ý đã xác thực, và với mỗi ý còn lại câu cố định: **"Chưa xác minh được từ tài liệu bạn được phép truy cập: {ý}."** Không nói tài liệu "không đề cập"; không viết gì cho ý còn thiếu ngoài chính ý đó (lời của người hỏi). Citation chỉ từ các ý đã xác thực, vẫn qua `validate_and_map` và kiểm lại quyền như mọi câu trả lời.
- Không có ý nào được xác thực: NO_ANSWER như cũ.
- Nếu `RAG_CONTENT_BLOCKS_TERMINAL_ENABLED` bật: một ý bị bác vì nội dung không được sinh lại, mà đi thẳng vào câu "chưa xác minh được".

## Đợt đo và quy tắc chọn

- Cấu hình, cùng job, 2 lượt xen kẽ: `base` (mặc định lúc đo) và `cpa` = `base` + `EVAL_COMPOUND_PARTIAL=true`.
- Bộ: UAT (báo tách route), RBAC, relevance, FR v1, FR v2, compound (`compound_partial_dev_v1`: 6 câu nửa trả lời được, 3 câu trả lời đủ, 3 câu phải từ chối; runner chấm câu "partial" đạt khi có sự kiện đúng **và** câu "chưa xác minh được", và tính câu "partial" trả lời đủ mà không có câu đó là trả lời sai).
- **DEC-013, "nhầm giá trị" tính là trả lời sai:** 0 rò rỉ; UAT không hồi quy quá 1 câu (phần LLM báo riêng); trả lời sai không tăng ở bộ nào. Thắng khi không tệ hơn `base` ở bộ nào và tốt hơn ở ít nhất một bộ (ít trả lời sai hơn trước, rồi nhiều câu đúng hơn).
- Ở RBAC, một câu negative có câu "chưa xác minh được" vẫn là ANSWERED, nên runner tính là trả lời sai nếu có phần nào được trả lời: quy tắc trên chặn việc trả lời một phần làm lộ tài liệu hay trả lời câu phải từ chối.
- Nội dung bộ compound còn chờ owner duyệt (lock ghi "content pending owner review"); số đo trên bộ này báo kèm ghi chú đó.
