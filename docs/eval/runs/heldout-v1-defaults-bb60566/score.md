# Held-out v1 với mặc định mới (diagnostic, 1 lượt)

Chạy ngày 2026-11-08 từ 14:05 đến 14:20, trên image `eaka-backend:main-bb60566` (commit `bb60566`).

- **Cấu hình:** `strict`, nhóm 1 + 2, REL-402 (mặc định), cộng REL-303 bật bằng `EVAL_SHORT_ANSWER_QUESTION_TERMS=true`, vì REL-303 chưa được bật mặc định (xem báo cáo `docs/status/2026-11-08-unattended-report.md`).
- **Hệ thống:** `reranker_mode = lexical_fallback`, Ollama 0.40.15 trên CUDA.
- **Hiệu lực:** 40/40 câu, 0 INFRA_ERROR, câu chậm nhất 73,8 giây.
- **Phạm vi dùng:** theo DEC-008 và yêu cầu lần này, kết quả không dẫn tới chỉnh sửa nào. Đây không phải con số công bố.

## Kết quả

| Chỉ số | Baseline `f3cdbf3` (lượt 1) | `strict` (`89417e7`) | Mặc định mới (`bb60566`) |
|---|---:|---:|---:|
| `permission_leak_count` | 0 | 0 | **0** |
| PASS / PARTIAL / FAIL | 11 / 1 / 28 | 12 / 2 / 26 | **14 / 2 / 24** |
| `false_answer_rate` | 35,7% (5/14) | 35,7% (5/14) | **21,4% (3/14)** |
| `false_refusal_rate` | 53,8% (14/26) | 57,7% (15/26) | **53,8% (14/26)** |

**Không so trực tiếp được với hai cột kia.** Baseline (31/10) và `strict` (06/11 13:21) chạy trên backend Vulkan và trên commit cũ hơn; lượt này chạy trên CUDA (`docs/eval/runs/nondeterminism.md`). Chênh lệch có thể do flag, do backend, hoặc cả hai.

## Nhãn

30 câu có trạng thái, câu trả lời và tài liệu trích dẫn giống hệt lượt `strict`, nên giữ nhãn của lượt đó. **10 câu đổi do Claude chấm; owner chấp nhận các nhãn này ở mức diagnostic ngày 2026-11-08** (cột `notes` trong `grading.csv`). Mốc này là diagnostic (DEC-008), không phải kết quả held-out cuối:

| Câu | `strict` | Mới | Nhãn |
|---|---|---|---|
| HO-008 | Trả lời sai | Từ chối | PASS |
| HO-020 | Trả lời sai | Từ chối | PASS |
| HO-038 | Từ chối sai | Trả lời đủ 2 ý, trích đúng tài liệu nhưng sai trang (7 thay vì 8) | PASS |
| HO-037 | PASS | Từ chối sai | FAIL |
| HO-003 | PASS | Vẫn đủ 3 ý, chỉ khác cách viết | PASS |
| HO-023 | Trả lời sai | Vẫn trả lời sai ("10 ngày làm việc") | FAIL |
| HO-002, HO-007, HO-027, HO-029 | FAIL | Đổi nội dung, vẫn sai | FAIL |

Câu trả lời sai còn lại: HO-011, HO-022, HO-023. Từ chối sai: HO-001, 004, 005, 012, 013, 025, 028, 031, 032, 033, 035, 036, 037, 039.
