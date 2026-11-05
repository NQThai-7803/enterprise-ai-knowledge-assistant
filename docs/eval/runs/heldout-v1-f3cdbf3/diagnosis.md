# Chẩn đoán held-out v1 (PROMPT 4b)

Chạy ngày 2026-11-05 trên stack `eaka-p3d-uat`, image `eaka-backend:heldout-v1` (commit `f3cdbf3`), không sửa `app/` hay held-out. Script ở `scripts/diagnostics/`; trace chi tiết ở `artifacts/heldout-v1-diagnosis/` (không commit).

## Kết luận

1. **Retrieval không phải điểm nghẽn.** Gold nằm trong top-k hybrid ở 25/26 câu có đáp án; chỉ HO-010 trượt.
2. **Trong 14 câu từ chối sai, 9 câu đã có gold trong prompt.** Câu trả lời bị chặn ở LLM, validator hoặc bước kiểm tra độ đầy đủ. 5 câu còn lại mất gold ở bước lọc và xếp hạng trước khi tới prompt.
3. **Route deterministic bắt nhầm đúng như gợi ý.** Cả 6 câu HO-004, 008, 020, 023, 026, 039 đi `_structured_condition_value_answer`, không gọi LLM, và đều FAIL.
4. **Đây là dấu hiệu overfit rõ nhất:** 75/100 câu dev đi route deterministic, held-out chỉ 6/40.
5. **Cross-encoder không hề chạy.** `BAAI/bge-reranker-v2-m3` không có trong cache của stack nên hệ thống dùng alignment fallback, đúng với log của API. Trên stack này, điểm "reranker" thực chất là điểm trùng từ.
6. **Không thấy rò rỉ quyền ở phạm vi đã trace.** Chunk hạn chế không xuất hiện ở bất kỳ tầng nào trong 140 câu đã trace, với mọi tài khoản. Vì vậy con số này chưa kiểm tra được trường hợp manager có quyền thật sự nhận được tài liệu.

## Bảng câu × tầng bị chặn

"Hybrid" là hạng tốt nhất của chunk gold. Tầng chặn là nguyên nhân chính tôi xác định từ trace.

| Câu | Route | Hybrid | Gold vào prompt | Validator | Tầng chặn | Bằng chứng |
|---|---|---:|---|---|---|---|
| HO-004 | deterministic | 12 | Không | SUPPORTED | Deterministic | Cue `sau `, `khi `; trả nội dung nghỉ phép cho câu về EAP; `low_alignment` bỏ gold |
| HO-026 | deterministic | 4 | Có | SUPPORTED | Deterministic | Cue `neu ` khớp nhầm chữ "nêu"; bỏ qua gold đã có |
| HO-039 | deterministic | 1 | Không | SUPPORTED | Deterministic | Cue `neu `; `low_alignment` bỏ 2 chunk gold (85 còn 1) |
| HO-008 | deterministic | không có gold | — | SUPPORTED | Deterministic | Cue `khi `; đáng lẽ NO_ANSWER |
| HO-020 | deterministic | không có gold | — | SUPPORTED | Deterministic | Cue `chua du` khớp nhầm "chưa dùng"; đáng lẽ NO_ANSWER |
| HO-023 | deterministic | không có gold | — | SUPPORTED | Deterministic | Cue `neu `; đáng lẽ NO_ANSWER |
| HO-001 | LLM | 1 | Không | INSUFFICIENT | Lọc và xếp hạng | Tách sai "Ủy ban Rủi ro" / "Tuân thủ do ai chủ trì"; gold xuống hạng 10+ |
| HO-007 | LLM | 2 | Không | INSUFFICIENT | Lọc và xếp hạng | `low_alignment` bỏ 3 chunk gold; câu phụ "Khi ai phê duyệt" |
| HO-031 | LLM | 1 | Không | CONTRADICTED | Lọc và xếp hạng | `low_alignment` bỏ gold |
| HO-032 | LLM | 3 | Không | INSUFFICIENT | Lọc và xếp hạng | `low_alignment` bỏ 2 chunk gold |
| HO-033 | LLM | 1 | Không | CONTRADICTED | `group_hits[:2]` | Gold hạng 3 ở cả 3 nhóm, bị cắt đúng ở giới hạn 2 |
| HO-028 | LLM | 1 | Có | SUPPORTED một phần | Tách câu hỏi | 3 tên thưởng bị ghép sai thành 2 câu phụ; LLM nói không có quy định |
| HO-005 | LLM | 1 | Có | SUPPORTED | LLM | Trả lời lảng, bị coi là no-answer; `missing_quantity_number` |
| HO-012, 013 | LLM | 9 | Có | CONTRADICTED ×3 | Validator | LLM viết "1 lần", nguồn "01 lần/năm". Đổi thành "01" thì SUPPORTED |
| HO-025 | LLM | 1 | Có | INSUFFICIENT | Validator | Giá trị đúng nguyên văn trong evidence vẫn bị từ chối |
| HO-038 | LLM | 3 | Có | INSUFFICIENT | Validator | Claim "không" bị từ chối; bản sửa của LLM không cứu được cả câu |
| HO-037 | LLM | 1 | Có | INSUFFICIENT rồi SUPPORTED | Validator, không ổn định | Run gốc NO_ANSWER, trace ANSWERED |
| HO-035 | LLM | 1 | Có | SUPPORTED ở lần 3 | Kiểm tra độ đầy đủ | `missing_numeric_unit` chặn "1.200.000 đ/người/năm" |
| HO-036 | LLM | 1 | Có | SUPPORTED | Kiểm tra độ đầy đủ | `missing_person_name`: "who" bắt buộc tên người, "Active users" bị chặn |
| HO-002 | LLM | 3 | Không | SUPPORTED | `group_hits[:2]` | Gold hạng 5 bị cắt; LLM kết luận trái gold |
| HO-010 | LLM | không có | Không | SUPPORTED | Retrieval | Chunk 100 ký tự không vào top 50; manager có quyền xem |
| HO-011 | LLM | không có gold | — | SUPPORTED | Validator quá dễ | Staff; trả lời từ ND-HR-003, không phải tài liệu hạn chế |
| HO-022 | LLM | không có gold | — | SUPPORTED | Validator quá dễ | LLM lấy tên công ty ở tiêu đề trang làm nhà bảo hiểm |

HO-012 và HO-013 cùng câu hỏi, khác tài khoản. HO-010 và HO-011 cũng cùng câu hỏi.

### Tổng hợp theo tầng

| Tầng | Từ chối sai (14) | Còn lại (10) | Tổng |
|---|---:|---:|---:|
| Retrieval | 0 | 1 | 1 |
| Lọc và xếp hạng | 4 | 0 | 4 |
| `group_hits[:2]` | 1 | 1 | 2 |
| Tách câu hỏi | 1 | 0 | 1 |
| LLM | 1 | 0 | 1 |
| Validator chặn nhầm | 5 | 0 | 5 |
| Kiểm tra độ đầy đủ | 2 | 0 | 2 |
| Route deterministic | 0 | 6 | 6 |
| Validator quá dễ | 0 | 2 | 2 |

Toàn bộ 26 câu có đáp án: gold có trong hybrid 25, sau `_prepare_prompt_retrieval_hits` 22, vào nguồn của prompt 17. `_filter_low_alignment_documents` bỏ chunk gold ở 13 câu (ít nhất một câu phụ).

## Route deterministic

`_structured_condition_value_answer` (`app/services/grounded_answer_service.py:8876`) chạy trước LLM:
- Chỉ cần câu hỏi chứa cue như `sau`, `neu`, `khi`, và một cửa sổ dòng có từ 2 giá trị kèm đơn vị. Không bắt buộc trùng chủ đề với câu hỏi.
- So khớp chuỗi con sau khi bỏ dấu, nên `neu ` (nếu) khớp cả "nêu" và `chua du` khớp cả "chưa dùng".
- Câu trả lời là nguyên văn nguồn, và validator trả SUPPORTED ở cả 6 câu. Vì vậy không có lớp nào chặn nhánh này. Đây cùng loại lỗi với xfail "verbatim source support does not establish question responsiveness".
- Câu trả lời dán từ bảng trong PDF, nên có ký tự bullet U+F0B7 mà TASKS đã ghi nhận.

| | Deterministic | LLM |
|---|---:|---:|
| Q001-Q100 (proxy) | 75 câu, khớp 75 | 25 câu, khớp 24 |
| Held-out v1 (nhãn) | 6 câu, 0 PASS | 34 câu, 11 PASS, 1 PARTIAL |

Trên dev có 22 nhánh deterministic, nhiều nhánh mang tên chủ đề của bộ dev (`attendance_policy`, `credential_sharing`, `remote_accident`, `public_ai_input`). Trên held-out chỉ một nhánh chung kích hoạt, và nhánh đó không phải nhánh trả lời cuối của câu dev nào. Điểm 99/100 của dev vì vậy chủ yếu đo các nhánh viết theo chủ đề.

Thời gian xác nhận route: trung vị 2,1 s (deterministic) so với 9,8 s (LLM) ở baseline v2.

## Nhóm H: tiếng Anh và tiếng Việt

Bản dịch do tôi viết để chẩn đoán. Cosine là giữa câu hỏi và chunk gold tốt nhất.

| Câu | Cosine EN | Cosine VI | Cosine EN-VI | Khác biệt của `analyze_question` |
|---|---:|---:|---:|---|
| HO-035 | 0,785 | 0,852 | 0,892 | EN: DEFINITION; VI: COUNT, `asks_for_explicit_value` |
| HO-036 | 0,887 | 0,777 | 0,814 | Không |
| HO-037 | 0,852 | 0,887 | 0,926 | EN: NUMBER; VI: AMOUNT |
| HO-038 | 0,833 | 0,875 | 0,879 | Không; bản EN không bị tách câu phụ |

- Embedding không phải nguyên nhân chính: cả 4 câu gốc đều có gold ở hạng 1-3 của hybrid.
- Với câu tiếng Anh, tín hiệu phân loại yếu hơn: "budget" không được nhận là câu hỏi giá trị. Kiểm tra `missing_person_name` cũng hiểu "who" là phải có tên người.
- HO-036 bản tiếng Việt lại trượt top 50, vì tài liệu viết bằng tiếng Anh. Đây là lỗi truy vấn khác ngôn ngữ theo chiều ngược lại.
- HO-035 bản tiếng Việt được ANSWERED nhưng câu trả lời bị vỡ ("000 đ/người..."), tức bước lắp câu có lỗi riêng với dấu phân cách hàng nghìn.

## HO-011 và HO-022

Cả hai đều **không phải rò rỉ quyền**:
- **HO-011 (staff):** cite ND-HR-003 tr.5 và tr.9. Tài khoản được xem tài liệu này. Chunk `UAT-GROUNDING-001` không xuất hiện ở bất kỳ tầng nào.
- **HO-022 (staff):** cite ND-HR-006 tr.5, tài khoản được xem. LLM ghép tên công ty ở tiêu đề trang thành nhà bảo hiểm. Validator trả SUPPORTED vì chuỗi đó có trong nguồn.

HO-010 cùng câu hỏi với HO-011 nhưng là manager: chunk hạn chế cũng không vào top 50. Vì vậy hai câu cho cùng câu trả lời, và cặp này **không kiểm tra được phân quyền**.

## 31 dòng trong `app/` trùng cụm 4 từ với Q001-Q100

Không có câu hỏi nguyên văn nào trong `app/`, và không có ánh xạ câu hỏi sang câu trả lời.

| Loại | Số dòng | Ví dụ |
|---|---:|---|
| Thuật ngữ miền dùng làm cue | 19 | `thoi gian lam viec` (9), `lam viec ban dem` (7), `tai khoan bi lo` (3) |
| Cách hỏi dùng làm cue | 6 | `may gio duoc ve` (2), `lam bao nhieu tieng`, `xu ly the nao`, `khoan ho tro nao`, `can tuan thu bao mat nao` |
| Cụm từ của tài liệu nguồn | 3 | `khong co dinh ty le`, `nghi khong luong dai ngay`, `thoi gian phat sinh` |
| Trùng ngẫu nhiên | 3 | Tập stopword `co, ho, tro, tien` |

Nhóm "cách hỏi" và các hàm theo chủ đề chứa chúng là fit theo chủ đề, nhưng không vi phạm trực tiếp quy tắc "no question-specific logic" ở mức từng câu. Bảng này do tôi phân loại khi đọc từng dòng và hàm chứa nó.

## Giới hạn

- Mỗi câu chỉ trace 1 lần. 23/24 câu ra cùng status với run gốc; HO-037 lệch.
- Trace gọi `_prepare_answer_draft` trực tiếp, không qua lớp lưu tin nhắn, với câu hỏi đơn lẻ.
- Chunk gold xác định bằng `source_excerpt` (nếu khớp) hoặc theo trang, nên có thể rộng hơn thực tế.
- Đếm route dừng ở lần gọi LLM đầu tiên, nên không tính nhánh sửa lỗi deterministic chạy sau LLM.
- 4 câu FAIL còn lại chưa trace vì ngoài phạm vi yêu cầu: HO-027, 029, 034, 040.
- Câu hỏi nhóm H gồm 2 câu tiếng Anh; quá ít để kết luận về tiếng Anh nói chung.
