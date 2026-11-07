# FIX 2a: bật mặc định nhóm 1 + 2, đếm nhánh 4a, trace câu sai còn lại

Chạy từ 2026-11-06 23:27 đến 2026-11-07 01:25 trên image `eaka-backend:fix2a` (commit `3f4f046`), `RAG_DETERMINISTIC_ROUTE_MODE=strict`, `reranker_mode = lexical_fallback`, model `qwen2.5:3b`, seed cố định. Điểm tự động, không phải chấm tay. Chỉ tính thay đổi xuất hiện ở cả 2 lượt. Đây không phải con số công bố.

## Kết luận

Tổ hợp thắng theo DEC-011 nên mặc định đã đổi: `RAG_REPAIR_AFTER_LLM_REFUSAL_ENABLED=false`, `RAG_ANSWER_UNIT_GUARD_ENABLED=true`. Đặt lại giá trị cũ để rollback. `RAG_RESELECT_REQUIRES_STRONG_SUPPORT_ENABLED` vẫn tắt.

| Bên | Rò rỉ (API + retrieval) | UAT khớp proxy | Bộ dev mới: sai / đúng | RBAC: sai / đúng | Tổng sai | Tổng đúng |
|---|---:|---:|---:|---:|---:|---:|
| Baseline | 0 | 99/100 | 8 / 13 | 1 / 22 | 9 | 35 |
| Nhóm 1 + 2 | 0 | 99/100 | 4 / 18 | 1 / 22 | **5** | **40** |

"Đúng" trên RBAC gồm 17 câu từ chối đúng và 5 đối chứng đạt. Câu RBAC sai ở cả hai bên là RBD-03.

**4 câu sai còn lại không thuộc nhóm 3 hay 4b như đã thiết kế.** Làm hai nhóm đó theo thiết kế hiện tại sẽ không sửa được câu nào trong 4 câu này (xem phần trace).

## Thay đổi xuất hiện ở cả 2 lượt

| Câu | Baseline | Nhóm 1 + 2 |
|---|---|---|
| REL-101 | Trả lời sai | Từ chối đúng, xem lưu ý |
| REL-102 | Trả lời sai | Từ chối đúng |
| REL-201 | Trả lời sai | Từ chối đúng |
| REL-202 | Trả lời sai | Từ chối đúng |
| REL-204 | Sai giá trị | Đúng |

- **Không câu nào xấu đi** trên cả hai bộ, không câu nào lúc đúng lúc sai.
- **RBAC không đổi.** Cả 4 lượt đều cho cùng kết quả. RBD-03 vẫn sai khi bật nhóm 1, nên thay đổi của RBD-03 ở FIX 2 không phải công của nhóm 1.
- **UAT:** cả 4 lượt giống hệt nhau về trạng thái và nội dung trên 100 câu. Câu lệch proxy duy nhất là Q071, ở cả hai bên.
- **Kiểm tra quyền ở tầng retrieval:** 4 lượt, mỗi lượt 18/18 cặp kết luận được và không cặp nào thấy chunk ở tài khoản không có quyền.

**Lưu ý về REL-101.** Kết quả này phụ thuộc vào đợt đo. Ở đợt FIX 2, chính LLM đưa ra câu trả lời sai, nên nhóm 1 không chặn được. Ở đợt này LLM từ chối, rồi bước sửa lỗi deterministic tạo ra câu sai, nên nhóm 1 chặn được. Trace REL-101 riêng từng flag xác nhận: chỉ nhóm 1 đổi kết quả, nhóm 2 không đổi. Nếu bỏ REL-101, tổng câu sai là 6 và tổng câu đúng là 39; quyết định không đổi.

## Bộ đếm nhánh 4a

Số lần trong mỗi lượt, đo từ `enterprise_ai_rag_answer_branch_total` và ghi vào metadata của từng lượt. Hai lượt của mỗi bên giống nhau.

| Bộ | Bên | Chọn lại nguồn sau khi bị từ chối | Flag 4a sẽ đổi nguồn |
|---|---|---:|---:|
| Bộ dev mới (25 câu) | Baseline | 12 | 0 |
| Bộ dev mới | Nhóm 1 + 2 | 11 | 0 |
| RBAC (36 lượt hỏi) | Baseline | 32 | 1 |
| RBAC | Nhóm 1 + 2 | 31 | 1 |
| UAT (100 câu) | Cả hai bên | 14 | 0 |

Nhánh chạy khá thường xuyên, nhưng flag gần như không có gì để đổi. Điều này sửa lại phỏng đoán ở `fix2-results.md`, rằng nhánh ít khi chạy vì mỗi tài liệu chỉ có 1 chunk. Bộ đếm tính số lần vào nhánh, không phải số câu, và không cho biết là câu nào.

## Trace các câu sai

Trace 1 lượt trên image `eaka-backend:fix2a-defaults` (commit `0c463f3`) với mặc định mới, bằng `heldout_trace.py` ở mode `full`. Trạng thái khớp với các lượt API của tổ hợp.

| Câu | Kết quả | Nhánh | Nguồn | Validator | Phân loại |
|---|---|---|---|---|---|
| REL-101 | Từ chối đúng | LLM từ chối 2 lần (`llm_no_answer_like_json`), không còn sửa lỗi deterministic | Không trích dẫn | Không chạy | Đã xử lý bởi nhóm 1, phụ thuộc đợt đo |
| REL-103 | Trả lời sai | `_structured_condition_value_answer` (strict), trước LLM | RELDEV-NT-001, câu "giám sát trưởng ghi nhận trước khi chuyển sang phòng kế toán" | `SUPPORTED` vì chép nguyên văn, `claim_evidence_validation_service.py:1394` | Nhánh khác: lỗi bỏ dấu |
| REL-303 | Trả lời sai | LLM, "Giám đốc dự án" | RELDEV-NT-001, câu về duyệt thanh toán đợt cuối, không phải tạm ứng | `SUPPORTED` vì câu trả lời ít nội dung, `claim_evidence_validation_service.py:1681` | Nhánh khác: câu trả lời ngắn |
| REL-401 | Trả lời sai | LLM, lấy tên công ty ở tiêu đề trang làm nhà cung cấp | RELDEV-PM-001 | `SUPPORTED` vì `_answer_has_grounded_signal`, `claim_evidence_validation_service.py:1661` | Nhánh khác: sai quan hệ giữa các từ |
| REL-402 | Bộ chấm tính là sai | LLM, nêu một sự thật không liên quan rồi nói tài liệu không có thông tin | RELDEV-PM-001 | `SUPPORTED` vì `_answer_has_grounded_signal`, `claim_evidence_validation_service.py:1661` | Nhánh khác: từ chối một phần |

### Vì sao không thuộc nhóm 3 hay 4b

- **REL-103.** Từ "giám sát" bỏ dấu thành "giam", trùng với từ khóa kết quả "giam" (giảm) ở `grounded_answer_service.py:9130`. Trong đoạn văn đó, "giam" là tín hiệu kết quả duy nhất, và chỉ có 1 cặp số + đơn vị, nên chính sự trùng này làm điều kiện `has_outcome` đúng. Nhóm 3 loại trừ nhánh deterministic. Nhánh này chạy trước LLM nên nhóm 1 không chạm tới. `strict` của FIX 1 chỉ giữ dấu cho từ khóa điều kiện, chưa giữ cho từ khóa kết quả.
- **REL-303.** Câu trả lời chỉ có 1 từ từ 4 ký tự trở lên, nên `_answer_has_grounded_signal` đã trả `False` và 4b không có tác dụng. Câu được duyệt ở nhánh ít nội dung, không so với điều kiện "tạm ứng" trong câu hỏi. Nhóm 3 chỉ áp dụng cho câu chép nguyên văn và loại trừ giá trị ngắn. Bộ dev gắn câu này vào nhóm 3 theo dạng câu hỏi, nhưng cơ chế thực tế khác.
- **REL-401.** Mô phỏng offline với danh sách từ đã đóng băng của 4b: còn 5 từ sau khi bỏ từ chung, cả 5 đều là nguyên từ có trong nguồn, nên 4b vẫn cho qua. Đây là cùng dạng với HO-022: mọi từ đều có trong nguồn nhưng quan hệ giữa chúng thì không.
- **REL-402.** Cụm từ chối nằm ở vị trí 49, sau ngưỡng 40 của `_is_no_answer_like_json_answer`, và "6 máy" được tính là có nội dung, nên câu không bị coi là từ chối. 4b giữ lại cặp số + đơn vị nên cũng cho qua. Câu này không nêu sự thật sai; nó bị tính sai vì trạng thái là ANSWERED.

## Độ tin cậy của phép đo

- **Cùng đợt theo DEC-011:** cùng image, chạy xen kẽ baseline, tổ hợp, baseline, tổ hợp. `artifacts/fix2a/batch.log` ghi thời điểm khởi động Ollama ở mọi đoạn, tất cả là `2026-11-06T21:48:59`.
- **Hợp lệ:** 0 INFRA_ERROR, `reranker_mode` không đổi, câu chậm nhất 68,0 giây trên bộ dev mới, 53,0 giây trên RBAC, 36,8 giây trên UAT.
- **Bộ nhớ:** Available trước mỗi lượt đạt ít nhất 1000 MB (sau `drop_caches` nếu cần), xuống 371-1022 MB khi đang chạy. Ba lần bị dừng trước khi khởi động stack vì RAM thấp, và không lượt nào bị bỏ. Một lần phải chờ khoảng 19 phút; lúc đó OneDrive giữ khoảng 1 GB.
- **Mặc định mới:** `Settings(_env_file=None)` trong image `fix2a-defaults` trả đúng `False`, `True`, `False`.

## Giới hạn

- **Bộ dev mới nhỏ** và do người sửa code soạn. REL-101 cho thấy một câu có thể đổi theo đợt đo.
- **Trace đối chứng REL-101 riêng từng flag** chỉ chạy 1 lượt, sau đợt đo.
- **Mô phỏng 4b** chạy offline trên câu đã ghi, không qua code thật vì 4b chưa được viết.
- **Held-out v1 không chạy lại**, theo đúng phạm vi yêu cầu.
