# FIX 2: chẩn đoán 5 câu trả lời sai trên held-out v1

Chạy ngày 2026-11-06 trên image `eaka-backend:fix1` (commit `89417e7`) với `RAG_DETERMINISTIC_ROUTE_MODE=strict`. So với `main`, `app/` chỉ khác giá trị mặc định của mode này. Giai đoạn này không sửa `app/`. Trace nằm ở `artifacts/fix2-diagnosis/` (không commit); công cụ là `scripts/diagnostics/heldout_trace.py`.

## Kết luận

1. **5 câu sai đi qua 4 cơ chế khác nhau, không có một lỗi chung.** Mỗi cơ chế cần một cách sửa riêng.
2. **Cả 5 câu đều qua được validator claim vì validator chỉ hỏi "câu này có trong nguồn không", không hỏi "câu này có trả lời câu hỏi không".** Kiểm tra citation chỉ xét marker và quyền. Kiểm tra độ đầy đủ chỉ xét dạng câu trả lời.
3. **Với HO-008, LLM đã từ chối đúng 2 lần nhưng hệ thống vẫn trả lời thay.** Đây là cách sửa rủi ro thấp nhất: mô phỏng không đổi câu dev nào.
4. **Con số "RBAC 0/18 câu sai" của `strict` không ổn định và cần đính chính.** Trong trace này RBD-03 trả lời sai dưới `strict`. Lựa chọn `strict` vẫn đúng theo DEC-010, xem mục [Độ nhiễu](#độ-nhiễu).
5. **Dev gần như không có ca thất bại thuộc các nhóm này**, nên cần thêm bộ dev mới trước khi đánh giá.

## Trace từng câu

Cả 5 câu đều trả về đúng câu trả lời như lượt API của `strict`. Gold của cả 5 là NO_ANSWER. Số dòng là của `app/services/claim_evidence_validation_service.py`.

| Câu | Nhánh sinh câu trả lời | Chunk nguồn | Claim | Citation | Độ đầy đủ |
|---|---|---|---|---|---|
| HO-008 | `_structured_policy_clause_repair_generation`, gọi từ `_draft_from_deterministic_repair`, sau 2 lần LLM trả `__NO_ANSWER__` | `ae1ca52b`, ND-HR-003 tr.9 | SUPPORTED, dòng 1373 (`_answer_is_verbatim_supported`) | Đạt | Đạt |
| HO-011 | LLM, lần gọi đầu | `0440dfc1`, ND-HR-003 tr.5 | SUPPORTED, dòng 1614 (`_answer_is_verbatim_supported`) | Đạt | Đạt |
| HO-020 | LLM, lần gọi đầu | `aee96f13`, UAT-LEAVE-AUTHORITY-001 tr.3 | SUPPORTED, dòng 1614 (`_answer_is_verbatim_supported`) | Đạt | Đạt |
| HO-022 | LLM, lần gọi đầu | `9d3a4592`, ND-HR-006 tr.11 | SOURCE_1: INSUFFICIENT, dòng 1665. Chọn lại SOURCE_2: SUPPORTED, dòng 1640 (`_answer_has_grounded_signal`) | Đạt cả 2 lần | Đạt |
| HO-023 | `_structured_direct_value_answer`, trước LLM, không gọi LLM | `3c8618e4`, ND-HR-006 tr.5 | SUPPORTED, dòng 1640 (`_answer_has_grounded_signal`) | Đạt | **Không chạy** |

### Vì sao validator cho qua

- **HO-008.** LLM từ chối đúng. Sau đó bước sửa lỗi tìm một dòng trong nguồn có "trước" và khớp 2 từ khóa của câu hỏi. Hai từ đó là "trước" và "công" (trong "chấm công"), nên nó chép một câu về dữ liệu chấm công. Câu chép nguyên văn nên validator cho qua ngay.
- **HO-011.** Câu hỏi về người phê duyệt đặt vé công tác. LLM chép câu về quản lý duyệt một việc chấm công. Câu chép nguyên văn nên qua; validator không xét chủ đề.
- **HO-020.** Câu hỏi hỏi số ngày, câu trả lời nói về "03 năm" của quy tắc nghỉ gộp. Validator kiểm tra giá trị có gắn với chủ thể và thấy đạt, rồi cho qua vì chép nguyên văn. Không có bước nào so đơn vị được hỏi với đơn vị trả lời.
- **HO-022.** Validator từ chối đúng ở lần đầu. Sau đó `select_supporting_source_labels` thử các nguồn khác cho cùng câu trả lời và SOURCE_2 đạt, vì `_answer_has_grounded_signal` chỉ cần 3 từ của câu trả lời xuất hiện ở đâu đó trong nguồn. "Nova", "Digital", "Technology" có trong tiêu đề trang, nhưng nguồn không hề nói NovaCare do công ty này cung cấp.
- **HO-023.** Sau khi bỏ dấu, "đồng ý" thành "dong y", và `_asks_for_amount` (`app/retrieval/question_analysis.py`) khớp "dong" như tiền tệ. Câu hỏi về số ngày bị xếp thành AMOUNT, nên nhánh giá trị lấy "1,2 triệu đồng/lần". Số này có trong nguồn nên validator cho qua. Nhánh trước LLM trả về thẳng, nên kiểm tra độ đầy đủ không chạy (cả 75 câu UAT đi nhánh trước LLM cũng vậy).

## Nhóm nguyên nhân và đề xuất sửa

Cột dev là số lần cơ chế xảy ra trên 100 câu UAT và 36 lượt RBAC trong trace này. Mô phỏng chạy offline trên văn bản đã ghi, không gọi lại LLM. Mọi flag đều mặc định giữ hành vi cũ.

| Nhóm | Câu | Cơ chế | Có trên dev |
|---|---|---|---|
| 1 | HO-008 | Sửa lỗi deterministic ghi đè lời từ chối của LLM | 0 |
| 2 | HO-023 (và HO-020) | Nhầm loại giá trị, không kiểm tra đơn vị được hỏi | 0 câu "đồng ý"; 2 câu trả lời có đơn vị để so, đều đúng |
| 3 | HO-011, HO-020 | LLM chép nguyên văn câu lạc đề | 1 lượt LLM chép nguyên văn (RBD-16), đúng |
| 4 | HO-022 (và RBD-03) | Câu đã bị từ chối được cứu bằng tín hiệu yếu | 3 lượt chọn lại nguồn (Q034, Q043, RBD-06); 1 lượt thử lại (RBD-03) |

### Nhóm 1: tôn trọng lời từ chối của LLM

- **Cách sửa:** khi lần sinh cuối của LLM là `__NO_ANSWER__`, không chạy `_draft_from_deterministic_repair`. Vẫn giữ bước sửa lỗi khi validator từ chối câu trả lời của LLM.
- **Flag:** `RAG_REPAIR_AFTER_LLM_REFUSAL_ENABLED`, mặc định `true`.
- **Ví dụ unit test:** LLM trả sentinel 2 lần, nguồn có câu "Nhật ký bảo dưỡng bất thường phải được đối chiếu trước khi kết luận lỗi", câu hỏi "Quy trình thuê xe ngoài yêu cầu tài xế làm gì trước khi khởi hành?". Kỳ vọng: NO_ANSWER. Test đối chứng: validator từ chối câu trả lời của LLM thì bước sửa lỗi vẫn chạy.
- **Mô phỏng:** chặn HO-008; dev không đổi. Câu dev duy nhất dùng nhánh này là Q091, chạy sau 3 lần CONTRADICTED chứ không sau lời từ chối.

### Nhóm 2: đơn vị được hỏi phải khớp đơn vị trả lời

- **Cách sửa (a):** `_asks_for_amount` không coi "đồng ý" là tiền.
- **Cách sửa (b):** với câu hỏi "bao nhiêu" + đơn vị thời gian hoặc số đếm, câu trả lời phải có số đi với đơn vị đó, ở mọi nhánh. Câu nói rõ tài liệu không quy định thì được miễn.
- **Flag:** `RAG_ANSWER_UNIT_GUARD_ENABLED`, mặc định `false`.
- **Ví dụ unit test:** "Nếu không đồng ý với biên bản nghiệm thu, nhà thầu có bao nhiêu ngày để khiếu nại?" không được xếp AMOUNT (hiện code xếp AMOUNT với câu cùng dạng). Nguồn chỉ có "phí 2 triệu đồng/lần" thì câu trả lời "2 triệu đồng" bị từ chối. Đối chứng: nguồn có "trong 7 ngày" thì đạt.
- **Mô phỏng:** (b) chặn HO-020 và HO-023; dev không đổi, nhưng chỉ 2 câu trả lời dev có đơn vị để so, nên bằng chứng còn mỏng.
- **Đã loại:** cho đơn vị thời gian thắng từ khóa tiền tệ, vì sẽ xếp sai Q072 (hỏi số tháng lương). Cũng bỏ "phần trăm" khỏi (b), vì 3 câu dev đúng viết bằng ký hiệu "%" hoặc nói không quy định.

### Nhóm 3: câu LLM chép nguyên văn phải đúng chủ đề

- **Cách sửa:** với câu trả lời do LLM sinh và được duyệt vì chép nguyên văn, yêu cầu tỷ lệ từ khóa câu hỏi có trong câu trả lời đạt ngưỡng. Không áp dụng cho nhánh deterministic và câu trả lời là giá trị ngắn.
- **Flag:** `RAG_LLM_VERBATIM_TOPIC_CHECK_ENABLED`, mặc định `false`.
- **Ví dụ unit test:** "Trước khi mượn máy đo, kỹ thuật viên cần ai ký?", LLM chép "Trưởng ca kiểm tra nhật ký và ký xác nhận hoàn thành ca." Kỳ vọng: bị từ chối. Đối chứng: "Trước khi mượn máy đo, kỹ thuật viên cần trưởng kho ký phiếu mượn máy đo." đạt.
- **Mô phỏng:** tỷ lệ của HO-011 là 0,17, HO-020 là 0,25, RBD-16 (đúng) là 1,0. Đây là nhóm có bằng chứng yếu nhất, vì dev chỉ có 1 ca. **Chưa chốt ngưỡng; phải chọn trên bộ dev mới, không chọn theo held-out.** Rủi ro là từ chối nhầm câu hỏi diễn đạt bằng từ đồng nghĩa.

### Nhóm 4: không cứu câu đã bị từ chối bằng tín hiệu yếu

- **Cách sửa (a):** khi chọn lại nguồn cho cùng câu trả lời đã bị từ chối, nguồn mới phải có câu trả lời nguyên văn hoặc đúng cặp số + đơn vị. Flag: `RAG_RESELECT_REQUIRES_STRONG_SUPPORT_ENABLED`, mặc định `false`.
- **Cách sửa (b):** với câu trả lời do LLM sinh, `_answer_has_grounded_signal` không chấp nhận số đứng một mình, chỉ khớp nguyên từ và bỏ từ quá chung. Flag: `RAG_LLM_STRICT_SIGNAL_ENABLED`, mặc định `false`.
- **Ví dụ unit test (a):** LLM trả lời "Phần mềm KhoNhanh do công ty Hoàng Minh cung cấp."; nguồn đầu bị từ chối; nguồn thứ hai có "KhoNhanh" ở nội dung và "HOANG MINH LOGISTICS" ở tiêu đề trang. Kỳ vọng: không được cứu. Đối chứng: "Thời hạn là 7 ngày." và nguồn thứ hai có "7 ngày" thì vẫn được chọn lại.
- **Ví dụ unit test (b):** câu hỏi về mã liên lạc, câu trả lời "Nhân viên báo cho lễ tân tầng 1", nguồn chỉ có câu đó. Kỳ vọng: không đạt.
- **Mô phỏng (a):** chặn HO-022. Q034 và Q043 vẫn qua. RBD-06 bị chặn; ca này đang FAIL vì cite sai tài liệu, nên sẽ thành từ chối.
- **Mô phỏng (b):** chặn RBD-03, không chặn thêm câu LLM nào trên dev. Không chặn được HO-022, vì mọi từ đều có trong nguồn. Danh sách từ bỏ qua có "tầng", do tôi thêm sau khi xem RBD-03, nên có nguy cơ khớp riêng ca đó và cần soạn lại theo hướng tổng quát.

### Đã thử và loại

| Ý tưởng | Kết quả mô phỏng |
|---|---|
| Bỏ header và footer trang khỏi evidence | Không đổi câu nào. HO-022 vẫn qua. |
| Bật `require_subject_attribute_alignment` có sẵn cho mọi câu | Chỉ chặn HO-022 trong 5 câu sai, nhưng chặn cả 8 câu UAT (Q012-015, 025, 033, 051, 095) và RBD-06 |
| So từ khóa câu hỏi với mọi câu trả lời | Không tách được: 29/102 câu trả lời dev có tỷ lệ 0, vì thường chỉ là một giá trị ngắn |
| Chỉ đổi sang khớp nguyên từ | Không đổi câu nào |
| Áp `RAG_LLM_STRICT_SIGNAL_ENABLED` cho cả nhánh deterministic | Chặn nhầm Q021 và RBD-11 |
| Dừng ngay khi LLM từ chối ở lượt thử lại | Sửa RBD-03 nhưng mất Q058 đang đúng; lợi 1, mất 1 |

## Độ nhiễu

Cùng image, cùng seed, temperature 0, nhưng kết quả vẫn khác giữa các lượt:

- **UAT:** 92/100 câu trả lời giống hệt lượt API. Q033 và Q071 đổi trạng thái: Q033 từ từ chối thành trả lời, Q071 từ trả lời thành từ chối.
- **RBAC:** RBD-03 từ chối ở lượt API của `strict`, nhưng trả lời sai trong trace này với đúng câu mà lượt API của `off` đã trả lời. Vì vậy `off` có 1 câu sai không phải do mode.
- **Ảnh hưởng tới DEC-010:** số câu sai của `strict` nên đọc là 0 đến 1, không phải 0. Lựa chọn không đổi: nếu `strict` và `off` hòa ở 1 câu sai, tiêu chí (b) vẫn chọn `strict` với 5 đối chứng đạt so với 3.
- **Chưa rõ nguyên nhân:** trace gọi `_prepare_answer_draft` trực tiếp, không qua API. Khác biệt có thể do đường chạy, hoặc do Ollama không tái lập hoàn toàn. Chưa kiểm tra.

Vì nhiễu này lớn hơn dung sai 1 câu, mỗi so sánh cần ít nhất 2 lượt.

## Đề xuất bộ dev mới

Bộ dev hiện tại không đủ: sau FIX 1, UAT chỉ có 2 câu gold NO_ANSWER và không có câu trả lời sai theo proxy; RBAC chỉ có ca không có quyền. Đề xuất thêm `tests/acceptance/answer_relevance_dev_v1.yaml`:

- **Stack:** `eaka-rbac-dev`, không đưa vào corpus chính, để baseline v2 còn hiệu lực.
- **Tài liệu:** tài liệu tổng hợp về đội xe và kho thiết bị, không trùng chủ đề với held-out.
- **Quy mô:** khoảng 24 ca, mỗi nhóm 3 câu không có đáp án và 3 câu đối chứng có đáp án.
- **Chống rò câu hỏi:** chạy `question_leak.py overlap` với held-out trước khi dùng.

| Nhóm | Dạng câu không có đáp án | Đối chứng |
|---|---|---|
| 1 | Hỏi việc làm "trước khi" một hành động; nguồn chỉ có câu "trước khi" về việc khác | Nguồn có đúng việc đó |
| 2 | Hỏi "bao nhiêu ngày/giờ/kg"; nguồn chỉ có số với đơn vị khác | Nguồn có đúng đơn vị |
| 3 | Hỏi "ai duyệt việc X"; nguồn có người duyệt việc Y | Có người duyệt việc X, kể cả diễn đạt bằng từ đồng nghĩa |
| 4 | Hỏi nhà cung cấp của X; nguồn có tên X và một tên công ty không liên quan | Nguồn nêu rõ quan hệ đó |

## Cách đánh giá mỗi flag

Mỗi flag được đo riêng, flag bật so với flag tắt, mỗi bên 2 lượt:

| Chỉ số | Điều kiện |
|---|---|
| `permission_leak_count` | = 0 trên RBAC |
| Q001-Q100 khớp proxy | Không giảm quá 1 câu so với 99/100 |
| RBAC: câu trả lời sai, đối chứng đạt | Câu sai không tăng, đối chứng không giảm |
| Bộ dev mới: câu trả lời sai, đối chứng đạt | Câu sai giảm, đối chứng không giảm quá 1 câu |

Held-out v1 không dùng để chọn flag hay ngưỡng. 5 câu này đã được dùng để thiết kế cách sửa, nên kết quả sau sửa trên chúng không chứng minh được khả năng tổng quát. Con số công bố vẫn phải đo trên held-out v2.

Thứ tự đề xuất: 1, 2, 4a, rồi 3 và 4b sau khi có bộ dev mới.

## Giới hạn

- Mô phỏng chỉ cho biết câu trả lời có bị chặn ở bước đó không. Sau khi bị chặn, hệ thống có thể thử lại và sinh câu khác, nên kết quả thật phải đo qua API.
- Mô phỏng dùng 1200 ký tự đầu của mỗi nguồn. Mọi câu đã mô phỏng đều tái lập được SUPPORTED với phần cắt này.
- Sửa HO-023 ở (a) sẽ đưa câu này sang LLM; chưa biết LLM sẽ trả lời hay từ chối.
- Các lượt trace RBAC chạy theo `rbac_retrieval_check.py`: đối chứng chạy khi còn cấp quyền, câu không có quyền chạy sau khi thu hồi.
