# Điểm held-out v1

Đây là con số tổng quát hóa chính thức của PROMPT 4, chốt ngày 2026-11-05.

- **Hệ thống được chấm:** image `4f8152b4`, commit `f3cdbf3`, cấu hình baseline v2, mọi guard tắt.
- **Bộ câu hỏi:** held-out v1, 40 câu, SHA256 `e4dd3c69445c443d337699bd2639afd17112221f5b6e6baf3018911a44272346`.
- **Lượt chạy:** 2 lượt, hiệu lực VALID / VALID, 0 INFRA_ERROR.
- **Người chấm:** Claude, được chủ dự án ủy quyền, theo rubric `docs/eval/heldout-v1-design.md` mục 7. Lý do từng câu nằm trong cột `notes` của `grading.csv`. Trong bảng dưới, `manual` nghĩa là nhãn của người chấm này, không phải nhãn do chủ dự án tự chấm hay điểm proxy.
- **Tính bằng:** `scripts/eval/metrics.py`.

## Kết quả

| Metric | run1 | run2 |
|---|---|---|
| grade_source | manual | manual |
| scored_cases | 40 | 40 |
| excluded_infra_error | 0 | 0 |
| permission_leak_count | 0 | 0 |
| false_answer_rate | 35.7% (5/14) | 35.7% (5/14) |
| false_refusal_rate | 53.8% (14/26) | 53.8% (14/26) |
| answer_accuracy | 27.5% (11/40) | 27.5% (11/40) |
| answer_accuracy_with_partial | 30.0% (12/40) | 30.0% (12/40) |
| answerable_accuracy | 7.7% (2/26) | 7.7% (2/26) |
| refusal_accuracy | 64.3% (9/14) | 64.3% (9/14) |
| citation_accuracy | 41.7% (5/12) | 50.0% (6/12) |

**run1**

- False answers: HO-008, HO-011, HO-020, HO-022, HO-023
- False refusals: HO-001, HO-005, HO-007, HO-012, HO-013, HO-025, HO-028, HO-031, HO-032, HO-033, HO-035, HO-036, HO-037, HO-038

**run2**

- False answers: HO-008, HO-011, HO-020, HO-022, HO-023
- False refusals: HO-001, HO-005, HO-007, HO-012, HO-013, HO-025, HO-028, HO-031, HO-032, HO-033, HO-035, HO-036, HO-037, HO-038

**Trong 11 PASS có 9 câu là từ chối đúng.** Chỉ 2/26 câu có đáp án được trả lời đạt (`answerable_accuracy` 7,7%); `refusal_accuracy` là 9/14. Đừng đọc `answer_accuracy` 27,5% như khả năng trả lời đúng.

## So với split dev

Baseline v2 trên Q001-Q100 đạt 99/100 theo proxy; đó là bộ đã dùng để tinh chỉnh và chấm theo cách khác, nên hai con số không so sánh trực tiếp được.

## Cách đọc

- `permission_leak_count = 0` chỉ ở mức kiểm tra sơ về phân quyền: nhóm B và C dùng một tài liệu hạn chế rất ngắn, và quyền của manager bằng admin. Con số này chưa chứng minh phân quyền đúng trên quy mô thực.
- `citation_accuracy` xét ở mức tài liệu, trên các câu gold và lượt chạy đều ANSWERED, và độc lập với nhãn. Câu có citation đúng vẫn có thể FAIL vì nội dung sai.
- `false_answer_rate` không tính câu ANSWERED_LIMITED được chấm PASS hoặc PARTIAL.
- Chỉ HO-002 khác nhau giữa hai lượt, cả nội dung lẫn citation. Vì vậy chỉ `citation_accuracy` lệch 1 câu; nhãn vẫn FAIL ở cả hai lượt.

## Trạng thái của bộ này

Từ commit này, held-out v1 **đã dùng để chẩn đoán, không còn là tập test**. Cần held-out v2 trước khi release (`DECISIONS.md`, DEC-008).
