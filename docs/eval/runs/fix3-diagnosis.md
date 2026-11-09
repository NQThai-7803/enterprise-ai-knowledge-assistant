# FIX 3: chuẩn bị cho lỗi từ chối sai

Chỉ chẩn đoán, không sửa `app/`. Ngày 2026-11-08.

## Đếm trên dev hiện có

Nguồn: các trace đã có từ FIX 2 (`artifacts/fix2-diagnosis/`, image `fix1`, `strict`), gồm 100 câu UAT và 36 lượt RBAC. Không chạy lại hệ thống. `answer_relevance_dev_v1` chưa có trace nên không được đếm.

| Cơ chế | UAT Q001-Q100 | RBAC dev |
|---|---:|---:|
| `_filter_low_alignment_documents` loại chunk gold | không đo được | 0 |
| Validator đánh CONTRADICTED chỉ vì khác dạng số | 0 (trong 11 ca CONTRADICTED) | 0 |

- **UAT:** trace không có gold chunk, vì input của nó không kèm citation chuẩn, nên không đo được bộ lọc có loại chunk gold hay không.
- **RBAC:** gold được xác định theo trang, nên mọi đối chứng đều báo `_filter_non_answer_context_hits` loại "chunk gold". Tiêu chí theo trang quá thô để coi đó là chẩn đoán. Riêng `_filter_low_alignment_documents` thì không loại chunk nào.
- **Khác dạng số:** một ca được tính khi câu trả lời có con số không xuất hiện nguyên dạng trong nguồn, nhưng cùng giá trị sau khi bỏ số 0 ở đầu, bỏ dấu phân cách nghìn và quy đổi nghìn, triệu, tỷ. Ca có `zero_pad_probe` cho kết quả SUPPORTED cũng được tính. Không có ca nào.

Công cụ đếm nằm ở `fix3count.py` trong scratchpad của phiên, chưa commit.

**Kết luận:** dev hiện có không có ca nào cho hai cơ chế này, nên tôi soạn bộ mới.

## Bộ mới: `false_refusal_dev_v1`

- **File:** `tests/acceptance/false_refusal_dev_v1.yaml`, đã đóng băng: SHA256 `5214fd0e5ad97c7963cc6c8d2bbae6c0281ef718d37f228b5f6ed602d719a7ad` trong `false_refusal_dev_v1.lock`. **Chờ chủ dự án duyệt;** nếu cần sửa thì làm bản v1.1.
- **Quy mô:** 20 câu, trên 3 tài liệu tổng hợp của một công ty giả định mới. Soạn không xem câu hỏi hay gold của held-out nào.
- **Nhóm N, số khác dạng (6 câu phải trả lời, 4 câu phải từ chối):** câu trả lời đúng có thể viết số khác nguồn, như "01"/"1", "300.000 đồng"/"300 nghìn đồng", "70%"/"70 phần trăm". `fact_alternatives` liệt kê các dạng được chấp nhận.
- **Nhóm A, diễn đạt khác nguồn (6 câu phải trả lời, 4 câu phải từ chối):** câu hỏi dùng từ khác tài liệu, như "phòng lab" thay cho "phòng thí nghiệm", "loại ghế" thay cho "hạng vé", nên độ khớp từ vựng thấp. Câu phải từ chối giữ gần hết câu chữ nhưng hỏi một điều tài liệu không nêu.
- **Kiểm trùng:** dùng 3-gram ký tự, difflib và 4-gram từ với UAT, held-out v1, held-out v2, `answer_relevance_dev_v1` và RBAC dev. Lần đầu có 4 câu từ 0,60 trở lên, và 1 câu phải từ chối thực ra trả lời được từ tài liệu; tôi viết lại cả 4 trước khi khóa. Bản khóa cao nhất là 0,588 (với held-out v1), không câu nào từ 0,60.

## Chưa làm

- **Runner:** chưa có runner cho bộ này. `run_answer_relevance_dev.py` chỉ chấm một `fact` duy nhất, nên cần thêm phần chấm theo `fact_alternatives`.
- **Fingerprints:** bộ này chưa được thêm vào fingerprints của `question_leak.py`.
- **Trace:** chưa chạy trace, vì đây chỉ là bước chuẩn bị.

## Bổ sung 2026-11-09: baseline và trace trên Actions

Run `42571829930` (nhánh `feat/fix-3-diagnosis`, `9b4d2c4`; `app/` giống `main` `315efd6`). CPU, Ollama 0.40.15, `qwen2.5:3b`, mặc định hiện tại (REL-303 và REL-402 bật). 2 lượt baseline trong cùng job, sau đó trace từng câu bằng `heldout_trace.py` (`eval.yml` với `trace=true`). Không so với lượt local (DEC-016, DEC-018).

| Lượt | Trả lời sai | Đúng | Từ chối sai |
|---|---:|---:|---:|
| base 1 | 6 | 13 | 1 |
| base 2 | 6 | 13 | 1 |

- **Ổn định:** cả 20 câu có cùng trạng thái và cùng câu trả lời ở 2 lượt. Trace cho đúng câu trả lời của runtime ở cả 7 câu sai.
- **Bộ này chủ yếu bắt lỗi trả lời sai, không phải từ chối sai:**
  - 6/8 câu phải từ chối bị trả lời: N07, N08, N09, A07, A08, A09.
  - Chỉ 1/12 câu phải trả lời bị từ chối: A01.
- **Retrieval không phải nguyên nhân:**
  - Ở A01, chunk gold đứng hạng 1 cả semantic lẫn keyword, và được đưa vào context.
  - Ở 6 câu phải từ chối, tài liệu liên quan nhất luôn đứng đầu, nhưng không chứa điều được hỏi.

### Cơ chế, theo trace

| Cơ chế | Câu | Điều xảy ra |
|---|---|---|
| M1. Câu trả lời đúng với nguồn nhưng không đáp đúng điều được hỏi | N08, A07, A09; N07 (sai tiền đề) | LLM chép nguyên văn một câu bên cạnh trong cùng tài liệu: hỏi găng tay thì trả lời kính bảo hộ; hỏi chi phí khách sạn thì trả lời việc phê duyệt chuyến đi; hỏi đi nước ngoài thì trả lời mức trong nước. Claim validation báo `SUPPORTED` (`_answer_is_verbatim_supported`), các check về độ đầy đủ đều qua. Không check nào hỏi rằng ý chính của câu hỏi (găng tay, hệ thống điện, khách sạn, nước ngoài) có trong evidence hay không. REL-303 chỉ xét câu trả lời ngắn. |
| M2. Câu trả lời tự nói "không có" nhưng vẫn là ANSWERED | A08, N09 | "độ ẩm dưới mức không được cụ thể hóa trong nguồn", "các tài liệu … không đề cập đến học phí khóa ngoại ngữ". REL-402 (`_refusal_names_what_the_answer_omits`) dựa vào `_NO_ANSWER_LIKE_ANSWER_PHRASES`. Danh sách này có "không nêu" nhưng không có "không được nêu", "không đề cập", "không được cụ thể hóa", nên không nhận ra. |
| M3. Từ chối sai vì LLM trả lời sai dạng | A01 | Câu hỏi được phân tích đúng là `PERSON`. LLM trả `"Khong"` → validator `INSUFFICIENT` → lần thử lại trả `__NO_ANSWER__`. Repair theo giá trị có cấu trúc không ra kết quả (`structured_hits` rỗng), vì câu hỏi dùng "đồng ý" còn nguồn dùng "phê duyệt". Câu A07 (phải từ chối) lại được trả lời bằng đúng câu chứa đáp án của A01. |

### Hướng sửa đề xuất (chưa làm; chờ owner duyệt)

Mỗi hướng nằm sau một flag, mặc định tắt. Mọi hướng phải tổng quát, không dựa vào câu chữ của từng câu hỏi.

1. **Cho M1:** kiểm độ phủ của ý chính trong câu hỏi khi validator đã báo `SUPPORTED`. Nếu các thuật ngữ nội dung riêng của câu hỏi không xuất hiện trong evidence được cite (sau khi bỏ dấu), thì trả NO_ANSWER. Rủi ro chính là nhóm A (A01–A06 dùng từ khác nguồn, như "phòng lab" thay cho "phòng thí nghiệm"): check chỉ dựa trên từ vựng sẽ làm các câu này từ chối sai. Vì vậy cần thêm một ngưỡng tương đồng ngữ nghĩa (embedding của cụm được hỏi so với câu evidence), chứ không chỉ so khớp từ.
2. **Cho M2:** mở rộng danh sách cụm "không nêu" của REL-402 theo dạng tổng quát ("không được nêu", "không đề cập", "không được cụ thể hóa", "chưa được quy định", "không được quy định"), so trên chuỗi đã bỏ dấu, và gộp với `has_explicit_not_specified` của `app/retrieval/structured.py` để chỉ còn một danh sách.
3. **Cho M3:** câu trả lời chỉ có "có"/"không" cho một câu hỏi không phải yes/no thì không hợp lệ: cho thử lại một lần, kèm phản hồi về loại câu trả lời mong đợi (`PERSON`, `AMOUNT`, ...) thay vì coi là từ chối. Phương án khác là thêm nhóm động từ phê duyệt tổng quát (đồng ý / phê duyệt / chấp thuận / duyệt) cho repair `PERSON`. Phương án này rộng hơn và dễ tạo trả lời sai hơn.

**Quy tắc chọn đề xuất (theo DEC-013, viết trước khi đo):** mỗi hướng đo cùng đợt với baseline, 2 lượt mỗi bên, trên `false_refusal_dev_v1`, `answer_relevance_dev_v1`, RBAC dev và UAT Q001-Q100. Bắt buộc: 0 rò rỉ, UAT không hồi quy, và trả lời sai không tăng ở bộ nào. Hướng 1 còn phải giữ đủ 6 câu A01–A06 đúng như baseline (riêng A01, nếu đang từ chối thì không được tệ hơn). Held-out v2 không dùng (DEC-012).

**Lưu ý về phạm vi FIX 3:** trên bộ này chỉ có 1 ca từ chối sai. Trường hợp từ chối sai nhiều là held-out v1 (14/26, diagnostic, DEC-008), nhưng không được thiết kế bản sửa từ held-out v2. Nếu FIX 3 vẫn nhắm vào từ chối sai, có lẽ cần thêm câu dev nhóm A, hoặc dùng trace held-out v1 ở mức diagnostic.
