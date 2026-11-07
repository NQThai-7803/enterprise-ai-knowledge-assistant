# FIX 2b: 3 flag cho REL-103, REL-303, REL-402

Chạy từ 2026-11-07 22:34 đến 2026-11-08 02:20 trên image `eaka-backend:fix2b` (commit `dc3fa38`), mặc định hiện tại (`strict`, nhóm 1 + 2 bật), `reranker_mode = lexical_fallback`, model `qwen2.5:3b`, seed cố định. Điểm tự động, không phải chấm tay. Chỉ tính thay đổi xuất hiện ở cả 2 lượt. Đây không phải con số công bố.

## Kết luận

**Mặc định chưa đổi.** Cả 3 flag đều tắt. Yêu cầu chỉ là sửa và đo.

| Cấu hình | Rò rỉ API | UAT khớp proxy | Bộ dev mới: sai / đúng | RBAC: sai / đúng | Đề xuất |
|---|---:|---:|---:|---:|---|
| Baseline | 0 | 99/100 | 4 / 18 | 1 / 22 | |
| `RAG_STRICT_OUTCOME_CUES_EXACT_ENABLED=true` (REL-103) | 0 | 99/100 | 4 / 18 | 1 / **20** | Giữ tắt: không giảm câu sai, mất 2 câu đúng |
| `RAG_SHORT_ANSWER_QUESTION_TERMS_ENABLED=true` (REL-303) | 0 | **98/100** | **3 / 19** | 1 / 22 | Giữ tắt: sửa Q004 rồi đo lại |
| `RAG_PARTIAL_REFUSAL_NO_ANSWER_ENABLED=true` (REL-402) | 0 | 99/100 | **3 / 19** | 1 / 22 | Đạt, tốt nhất |

**Kiểm tra quyền ở tầng retrieval:** 7 trên 8 lượt đều 18/18 cặp kết luận được, không cặp nào thấy chunk ở tài khoản không có quyền. **Lượt thứ 8 (flag REL-402, lượt 2) chưa có kết quả:** hệ thống dừng lệnh vì thiếu bộ nhớ và tôi không chạy lại. Lượt 1 của flag này đạt 18/18, và flag không chạm vào retrieval.

## Thay đổi xuất hiện ở cả 2 lượt

| Flag | Bộ dev mới | RBAC | UAT |
|---|---|---|---|
| REL-103 | Không đổi | RBD-04, RBD-05: đối chứng đúng thành từ chối sai | Không đổi |
| REL-303 | REL-303: trả lời sai thành từ chối đúng | Không đổi | Q004: đúng thành từ chối sai |
| REL-402 | REL-402: trả lời sai thành từ chối đúng | Không đổi | Không đổi |

Trên UAT, flag REL-103 và REL-402 giữ nguyên trạng thái và nội dung của cả 100 câu; flag REL-303 chỉ đổi Q004.

## Từng flag

### REL-103: giữ dấu cho từ khóa kết quả

Flag làm đúng việc ở nhánh deterministic: "giám sát" không còn bị coi là "giảm", nên nhánh này không trả lời nữa. Nhưng câu hỏi chuyển sang LLM, và LLM chép nguyên văn một câu khác: "Giám sát trưởng ký biên bản nghiệm thu hạng mục kết cấu." Validator duyệt vì câu đó có nguyên văn trong nguồn. REL-103 vẫn sai, chỉ đổi cơ chế.

Cũng chính sự trùng "giam" đó đang giúp 2 câu RBAC. RBD-04 và RBD-05 có "Phó giám đốc vận hành" trong nguồn, nên nhánh deterministic trả đúng. Khi tắt sự trùng này, LLM từ chối sai 2 câu đó. Vậy nhánh này có đúng một phần nhờ lỗi.

**Đính chính báo cáo FIX 2a:** tôi nói nhóm 3 như thiết kế không sửa được REL-103. Điều đó đúng khi flag này tắt. Khi bật, REL-103 thành đúng dạng nhóm 3: LLM chép nguyên văn câu lạc đề.

### REL-303: câu trả lời ngắn phải đối chiếu với câu hỏi

Câu trả lời ngắn nay bị từ chối nếu 15 từ mỗi bên của nó có ít hơn 60% từ nội dung của câu hỏi, hoặc nếu nó không có trong nguồn.

- **Sửa được REL-303.**
- **Làm sai Q004.** "Lê Thu Hà" đúng, nhưng từ "tên" trong "tên gì" bị tính là từ nội dung cần có trong nguồn, nên độ phủ là 4/7, dưới ngưỡng 0,6. Đề xuất thêm từ này vào danh sách từ để hỏi, rồi đo lại trong một đợt mới. Tôi không sửa giữa đợt vì sẽ làm mất hiệu lực các lượt đã đo.
- **Ngưỡng 0,6 mới chỉ dựa trên rất ít ca.** Trên 161 câu trả lời dev chỉ có 4 câu đi qua nhánh này.

Lần đo đầu cho thấy lỗi trong chính bản sửa của tôi: lúc đó câu trả lời không tìm thấy trong nguồn vẫn được cho qua, nên câu bị từ chối đã chuyển sang một tài liệu không chứa nó. Tôi sửa (`dc3fa38`), build lại image và bỏ 3 lượt đã chạy; chúng nằm ở `artifacts/fix2b-invalid-first-303`.

### REL-402: từ chối kèm thông tin lạc đề

Với câu hỏi chỉ có một nhu cầu thông tin, nếu câu từ chối nhắc tới từ của câu hỏi mà phần còn lại không nhắc, câu trả lời thành NO_ANSWER. Trên 161 câu trả lời dev, quy tắc chỉ khớp REL-402.

## Bộ đếm nhánh 4a

| Bộ | Cấu hình | Chọn lại nguồn sau khi bị từ chối | Flag 4a sẽ đổi nguồn |
|---|---|---:|---:|
| Bộ dev mới | Baseline / REL-103 | 11 | 0 |
| Bộ dev mới | REL-303 | 13 | 0 |
| Bộ dev mới | REL-402 | 12 | 0 |
| RBAC | Baseline / REL-402 | 31 | 1 |
| RBAC | REL-103 | 32 | 1 |
| RBAC | REL-303 | 33 | 0 |
| UAT | Baseline / REL-103 / REL-402 | 14 | 0 |
| UAT | REL-303 | 16 | 0 |

## Độ tin cậy của phép đo

- **Cùng đợt theo DEC-011:** cùng image, xen kẽ baseline, REL-103, REL-303, REL-402 rồi lặp lại. `artifacts/fix2b/batch.log` có 81 dòng, tất cả cùng thời điểm khởi động Ollama `2026-11-07T21:31:30`.
- **Hợp lệ:** 0 INFRA_ERROR, câu chậm nhất 55,9 giây. Hai lượt của mỗi cấu hình giống nhau trên cả 3 bộ.
- **Bộ nhớ:** cổng 1000 MB đã dừng trước khi khởi động stack nhiều lần, có lần phải chờ tới khoảng 25 phút. OneDrive giữ hơn 1,2 GB ở lần kiểm tra lúc đó.
- **Held-out v2 không được chạy** và không được dùng cho các bản sửa này (DEC-012). Người soạn gold cũng là người sửa code trong cùng phiên; xem giới hạn trong DEC-012.

## Giới hạn

- **Chưa đo các flag bật cùng lúc.**
- **Bộ dev mới nhỏ** và do người sửa code soạn; flag REL-402 và REL-303 mỗi flag chỉ có đúng 1 ca cải thiện.
- **Chấm tự động:** REL-402 bị tính là sai vì trạng thái ANSWERED, dù câu đó không nêu sự thật sai.
