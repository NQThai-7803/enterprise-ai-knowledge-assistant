# FIX 3b: chẩn đoán lại các câu từ chối sai (không sửa `app/`)

Ngày 2026-11-09. Nhánh `feat/fix-3b-diagnosis`. Dừng ở đây để owner duyệt.

## Trace held-out v1 trên Actions

- **Run:** `42581562670`, `eval.yml` chạy `set=uat` với `cases=Q001` (chỉ để nạp corpus V2) và `trace_heldout_v1`.
- **Môi trường:** CPU, Ollama 0.40.15, `qwen2.5:3b`. Mặc định giống `main`: `strict`, nhóm 1 + 2, REL-402, REL-303. Code `app/` không có thay đổi nào của FIX 3a.
- **Phạm vi:** 14 câu từ chối sai của lượt diagnostic gần nhất (`docs/eval/runs/heldout-v1-defaults-bb60566/score.md`): HO-001, 004, 005, 012, 013, 025, 028, 031, 032, 033, 035, 036, 037, 039.
- **Quy tắc áp dụng:** held-out v1 chỉ dùng để chẩn đoán (DEC-008). Không chấm điểm, không sửa `app/` từ kết quả này. Không đọc held-out v2.
- **Tái hiện:** 13/14 câu vẫn bị từ chối. HO-001 lần này được trả lời: lượt diagnostic chạy trên CUDA, lượt trace chạy trên CPU (DEC-014), nên không so trực tiếp.

### Câu bị chặn ở tầng nào

| Câu | Số nhu cầu | Gold trong retrieval | Gold trong context | Chặn ở | Cơ chế |
|---|---:|---|---|---|---|
| HO-004 | 1 | hạng 13 | không | lọc tài liệu | A |
| HO-031 | 2 | hạng 1, 20 | không | lọc tài liệu → claim 1 CONTRADICTED | A, C |
| HO-032 | 2 | hạng 3–7 | không | lọc tài liệu → claim 1 INSUFFICIENT | A, C |
| HO-033 | 2 | hạng 2–3 | không | lọc tài liệu → claim 1 CONTRADICTED | A, C |
| HO-039 | 1 | hạng 1, 3 | không | lọc tài liệu → LLM nói "nguồn không có" | A, E |
| HO-025 | 2 | hạng 1–3 | có | evidence của claim 2 rỗng → INSUFFICIENT | C |
| HO-037 | 2 | hạng 1–3 | có | evidence của claim 2 rỗng → INSUFFICIENT | C |
| HO-028 | 2 | hạng 1 | có | một claim tự ghi "không được nêu cụ thể", lần thử lại trả `__NO_ANSWER__` | C |
| HO-012, HO-013 | 1 | hạng 8 | có | `_numbers_are_contradicted`: "1 lần" so với "01 lần/năm", trong đoạn có nhiều số khác | F |
| HO-035 | 1 | hạng 1 | có | claim bị so với evidence của nguồn khác → CONTRADICTED. Lần thử lại ra `"answer": ["SOURCE_1"]` → lỗi citation | E |
| HO-036 | 1 | hạng 1 | có | evidence của câu trả lời tiếng Anh rỗng → lỗi citation. Lần thử lại chép tiền tố nội bộ `Answer-focused evidence:` | E |
| HO-005 | 1 | hạng 1–2 | có | LLM trả một mảnh câu ("mọi chi tiết payslip.") → INSUFFICIENT → `__NO_ANSWER__` | (riêng lẻ) |

**Bốn cơ chế:**

- **A. Tài liệu chứa đáp án bị loại trước khi vào context** (5 câu). Gold đứng cao trong retrieval. Sau khi `lexical_fallback` xếp lại, `_filter_low_alignment_documents` loại tài liệu đó vì từ vựng của nó ít khớp với câu hỏi hơn tài liệu khác.
- **C. Câu hỏi ghép hai ý: một ý hỏng thì cả câu trả lời bị từ chối** (6 câu, 3 câu trùng với A). Có hai dạng. Dạng thứ nhất: evidence riêng của ý thứ hai rỗng dù gold đã có trong context (HO-025, HO-037). Dạng thứ hai: một ý gắn với đoạn evidence sai.
- **F. Số có số 0 đứng đầu, kèm đơn vị có gạch chéo ("01 lần/năm"), nằm giữa nhiều số khác** (2 câu). Câu trả lời viết "1 lần" bị `_numbers_are_contradicted` báo CONTRADICTED. Nhóm N của `false_refusal_dev_v1` có "01"/"1" nhưng không chặn, vì đoạn ở đó ít số và không có đơn vị gạch chéo.
- **E. Câu hỏi tiếng Anh, tài liệu tiếng Việt** (2 câu, và một phần HO-039). Evidence của câu trả lời tiếng Anh rỗng hoặc lấy từ nguồn khác. Các lần thử lại trả về sai định dạng.

## Bộ mới: `false_refusal_dev_v2` (đóng băng, chờ owner duyệt)

- **File:** `tests/acceptance/false_refusal_dev_v2.yaml`, SHA256 `540772d8befb5974a4408a858bdb7de55d995c573bf3ec8049441dc411264e9b` trong `false_refusal_dev_v2.lock`. Cố định LF trong `.gitattributes`. Sửa bất kỳ chỗ nào cũng phải ra v2.1 với lock mới.
- **Nội dung:** 24 câu trên 4 tài liệu giả lập của một công ty mới (kho lạnh, xe nâng, hiệu chuẩn cân, đào tạo vận hành viên). Mỗi cơ chế A (nhóm L), F, C, E có 4 câu phải trả lời và 2 câu phải từ chối.
- **Câu phải từ chối:** viết gần giống câu phải trả lời, nhưng hỏi điều tài liệu không nêu, hoặc dựa trên một tiền đề không có thật ("khóa nâng cao", "cân treo").
- **Cách soạn:** mô phỏng cơ chế, không phải câu chữ. Không diễn đạt lại câu held-out nào, và không dùng lại chủ đề nào của held-out v1.
- **Chấm nhóm C:** khoá mới `also_facts` yêu cầu câu trả lời phải có đủ cả hai fact. `run_answer_relevance_dev.states_fact` đã hỗ trợ khoá này, có test kèm theo.
- **Kiểm trùng** (3-gram ký tự, difflib, 4-gram từ; ngưỡng 0,60 như v1):
  - Lần đầu, 3 cặp vượt ngưỡng trên difflib: FR2-L04 với HO-039 (0,615) và với RBD-05 (0,633); FR2-F05 với FR-N08 (0,654). Tôi viết lại hai câu FR2-L04 và FR2-F05 trước khi khoá.
  - Bản khoá:

| So với | 3-gram ký tự | difflib | 4-gram từ |
|---|---:|---:|---:|
| UAT Q001-Q100 | 0,348 | 0,571 | 0,056 |
| held-out v1 | 0,343 | 0,545 | 0,040 |
| held-out v2 (chỉ so câu hỏi, DEC-012) | 0,288 | 0,525 | 0 |
| `answer_relevance_dev_v1` | 0,301 | 0,562 | 0,080 |
| RBAC dev | 0,278 | 0,550 | 0 |
| `false_refusal_dev_v1` | 0,321 | 0,588 | 0,043 |

- **Fingerprints:** `scripts/eval/question_fingerprints.json` đã dựng lại, có `false_refusal_v2` (24 câu). `check_no_question_leak.py` vì vậy chặn cả các câu này trong `app/`. Lệnh `question_leak.py overlap` chạy qua.
- **Chưa làm:** hệ thống chưa chạy trên v2. `eval.yml`/`ci_batch.sh` mới chỉ có bộ `false_refusal` v1. Việc thêm v2 vào hai file này chờ owner duyệt bộ.

## Không thuộc FIX 3b

- **M3** (FR-A01: "đồng ý" so với "phê duyệt") được ghi vào `TASKS.md`, xử lý ở giai đoạn NLU, không sửa bằng bảng từ đồng nghĩa.
- **HO-005:** LLM trả một mảnh câu. Chỉ có một ca nên không tạo nhóm riêng.
