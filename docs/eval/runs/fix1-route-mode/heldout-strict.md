# Held-out v1 với `strict` (diagnostic, 1 lượt)

Chạy ngày 2026-11-06, sau khi đã chọn mode. Theo DEC-010, kết quả này không ảnh hưởng tới lựa chọn và không dẫn tới thay đổi nào. Đây không phải con số công bố.

- **Hệ thống:** image `eaka-backend:fix1` (commit `89417e7`), `RAG_DETERMINISTIC_ROUTE_MODE=strict`, `reranker_mode = lexical_fallback`.
- **Hiệu lực lượt chạy:** 40/40 câu, 0 INFRA_ERROR, chậm nhất 42,8 giây, Ollama không khởi động lại. Available thấp nhất 292 MB. Chạy 2 đoạn foreground, mỗi đoạn khoảng 4 phút.
- **Cách chấm:** 30 câu có câu trả lời và citation giống hệt baseline `f3cdbf3` lượt 1 nên giữ nhãn cũ. 10 câu đổi câu trả lời do Claude chấm đề xuất theo rubric; owner chấp nhận ở mức diagnostic, đã xem HO-026/HO-037.

## Kết quả

| Chỉ số | Baseline `f3cdbf3` (lượt 1) | `strict` |
|---|---:|---:|
| `permission_leak_count` | 0 | 0 |
| PASS / PARTIAL / FAIL | 11 / 1 / 28 | 12 / 2 / 26 |
| `false_answer_rate` | 35,7% (5/14) | 35,7% (5/14) |
| `false_refusal_rate` | 53,8% (14/26) | 57,7% (15/26) |
| `answer_accuracy` | 27,5% (11/40) | 30,0% (12/40) |
| `answerable_accuracy` | 7,7% (2/26) | 11,5% (3/26) |
| `refusal_accuracy` | 64,3% (9/14) | 64,3% (9/14) |

Baseline chạy trên commit cũ hơn, nên chênh lệch không chỉ do mode này.

## Đọc kết quả

**`strict` không giảm câu trả lời sai trên held-out v1.** HO-008, 011, 020, 022, 023 vẫn trả lời sai, dù trên RBAC số câu sai giảm từ 5 xuống 0.

6 câu trước đây đi nhánh `_structured_condition_value_answer` và đều FAIL:

| Câu | Trước | `strict` |
|---|---|---|
| HO-004, HO-039 | Trả lời sai | Từ chối, vẫn FAIL vì gold có đáp án |
| HO-008, HO-020, HO-023 | Trả lời sai | Vẫn trả lời sai, FAIL |
| HO-026 | Trả lời sai | Đúng một phần: thiếu mức lương tháng, PARTIAL |

Các câu đổi còn lại: HO-037 chuyển từ từ chối sai sang PASS. HO-002, 022, 027 đổi nội dung nhưng vẫn FAIL.

## Chưa kiểm chứng

- Chưa trace route của lượt này, nên chưa biết HO-008, 020, 023 sai vì nhánh `strict` vẫn chạy, vì nhánh deterministic khác, hay vì LLM.
