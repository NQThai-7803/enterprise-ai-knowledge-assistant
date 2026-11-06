# FIX 2: kết quả đo nhóm 1, 2 và 4a

Chạy ngày 2026-11-06 trên image `eaka-backend:fix2` (commit `211afff`), `RAG_DETERMINISTIC_ROUTE_MODE=strict`, `reranker_mode = lexical_fallback`, model `qwen2.5:3b`, seed cố định. Điểm tự động, không phải chấm tay. Chỉ tính thay đổi xuất hiện ở cả 2 lượt (`scripts/eval/compare_flag_runs.py`). Đây không phải con số công bố.

## Kết luận

| Flag | Rò rỉ | UAT khớp proxy | Bộ dev mới: câu sai | Bộ dev mới: câu đúng | RBAC: câu sai / đối chứng đạt | Đề xuất |
|---|---:|---:|---:|---:|---:|---|
| Baseline, mọi flag tắt | 0 | 99/100 | 8 | 13 | 1 / 5 | |
| `RAG_REPAIR_AFTER_LLM_REFUSAL_ENABLED=false` (nhóm 1) | 0 | 99/100 | 7 | 14 | 0 / 5 | Đạt quy tắc |
| `RAG_ANSWER_UNIT_GUARD_ENABLED=true` (nhóm 2) | 0 | 99/100 | **6** | **16** | 0-1 / 5 | Đạt quy tắc, tốt nhất |
| `RAG_RESELECT_REQUIRES_STRONG_SUPPORT_ENABLED=true` (nhóm 4a) | 0 | 99/100 | 8 | 13 | 0-1 / 5 | Chưa có bằng chứng; giữ tắt |

**Mặc định chưa đổi.** Mọi flag vẫn giữ hành vi cũ cho tới khi chủ dự án quyết định.

## Thay đổi xuất hiện ở cả 2 lượt

| Flag | Bộ dev mới | RBAC | UAT |
|---|---|---|---|
| Nhóm 1 | REL-102: trả lời sai thành từ chối đúng | RBD-03: trả lời sai thành từ chối đúng, xem lưu ý | Không đổi |
| Nhóm 2 | REL-201, REL-202: trả lời sai thành từ chối đúng. REL-204: trả lời sai giá trị thành đúng | Không đổi; RBD-03 lúc sai lúc đúng | Không đổi |
| Nhóm 4a | Không đổi | Không đổi; RBD-03 lúc sai lúc đúng | Không đổi |

Trên UAT, cả 3 flag đều giữ nguyên trạng thái và nội dung của cả 100 câu.

**Lưu ý về RBD-03.** Nhóm 1 sửa được câu này ở cả 2 lượt nên quy tắc tính là thay đổi. Nhưng nhóm 2 và 4a, vốn không liên quan, cũng làm nó đổi kết quả ở 1 trong 2 lượt. Vì vậy chưa thể khẳng định công lao là của nhóm 1. Bộ dev mới không có nhiễu này: cả 25 câu cho kết quả giống nhau giữa 2 lượt ở mọi cấu hình.

**Nhóm 2 sửa đúng lỗi gốc.** Ở REL-204, "đồng ý" từng làm câu hỏi về số ngày thành câu hỏi về tiền, nên hệ thống trả "2 triệu đồng". Với flag bật, nó trả đúng "7 ngày". Vậy lỗi này không chỉ gây trả lời sai trên câu không có đáp án, mà còn làm sai câu có đáp án.

## Baseline của bộ dev mới

| Cấu hình | Lượt 1 | Lượt 2 |
|---|---|---|
| `strict`, image `fix1` (mặc định hiện tại) | 8 câu sai, 13 câu đúng | Giống hệt |
| `legacy`, image `fix1` | 8 câu sai, 12 câu đúng | Giống hệt |
| `strict`, image `fix2`, flag tắt | 8 câu sai, 13 câu đúng | Giống hệt |

`legacy` thua `strict` ở REL-106. Yêu cầu ghi "legacy (mặc định hiện tại)", nhưng mặc định đã là `strict` từ FIX 1, nên tôi đo cả hai và dùng `strict` làm baseline. Dòng thứ ba cho thấy code mới với flag tắt không đổi kết quả.

## Câu sai còn lại

Với cả nhóm 1 lẫn nhóm 2, các câu REL-101, 103, 303, 401, 402 vẫn trả lời sai khi đo từng flag riêng. REL-105, 304, 305 vẫn từ chối sai ở mọi cấu hình, và đây là lỗi từ chối sai có từ trước.

REL-103 trả về trong chưa tới 0,5 giây nên nhiều khả năng đi nhánh deterministic trước LLM, là nhánh nhóm 1 không chạm tới. Chưa trace để xác nhận.

## Bộ dev `answer_relevance_dev_v1`

- **Đóng băng:** commit `b4efd99`, SHA256 `08f095ba3ed716a7...`, xem `tests/acceptance/answer_relevance_dev_v1.lock`. Runner từ chối chạy khi hash khác. Bộ này cũng khóa danh sách từ của nhóm 4b, soạn theo loại từ, chưa dùng trong `app/`.
- **Quy mô:** 25 câu, gồm 12 câu phải từ chối và 13 câu phải trả lời, trên 4 tài liệu tổng hợp.
- **Stack:** dùng `eaka-relevance-dev` riêng, không dùng `eaka-rbac-dev` như đề xuất ban đầu, vì thêm tài liệu vào đó sẽ làm đổi baseline RBAC.
- **Kiểm trùng:** Jaccard cao nhất với held-out vẫn là 0,190 (từ bộ dev cũ), với Q001-Q100 là 0,091; giới hạn 0,60.

## Độ tin cậy của phép đo

- **Trong cùng điều kiện, UAT lặp lại hoàn toàn.** Hai lượt của mỗi cấu hình giống hệt nhau trên cả 100 câu.
- **Khác ngày thì khác.** Baseline hôm nay chỉ giống lượt `strict` ngày 2026-11-05 ở 90/100 câu, và Q033, Q071 đổi trạng thái. Vì vậy baseline phải đo lại trên cùng đợt với flag, như lần này. Câu lệch proxy duy nhất hôm nay là Q071, không phải Q033.
- **Lượt bị ngắt:** UAT baseline lượt 1 chạy tiếp từ Q091 sau khi vượt giới hạn thời gian của script, và API được tạo lại. Metadata có ghi. Kết quả của lượt này giống hệt lượt 2.
- **Lượt bỏ:** một lượt của bộ dev mới (`run0`) chạy khi chưa warm-up và không tính. Một lượt UAT baseline dừng ở Q085 khi Docker tắt cũng không tính.
- **Bộ nhớ:** Available trước mỗi đoạn từ 1007 đến 2083 MB khi stack dừng, xuống khoảng 420-700 MB khi đang chạy. 0 INFRA_ERROR, câu chậm nhất 74,6 giây.

## Đính chính sau FIX 2a

`docs/eval/runs/fix2a-defaults.md` đo lại trong một đợt theo DEC-011. Bộ đếm cho thấy nhánh 4a chạy 11-32 lần mỗi lượt, không phải ít khi chạy như mục Giới hạn dưới đây phỏng đoán, nhưng flag gần như không có gì để đổi. Thay đổi của RBD-03 không phải công của nhóm 1.

## Giới hạn

- **Chưa đo các flag bật cùng lúc.** Nên đo tổ hợp nhóm 1 + 2 trước khi đổi mặc định.
- **Bộ dev mới nhỏ và mỗi tài liệu chỉ có 1 chunk.** Nhóm 4a cần câu trả lời bị từ chối ở nguồn này rồi được chọn lại ở nguồn khác, nên ít có cơ hội xảy ra ở đây. Cơ chế của nó mới được kiểm chứng bằng unit test.
- **Chấm tự động:** câu trả lời "tài liệu không nêu" có trạng thái ANSWERED bị tính là trả lời sai.
- **Kiểm tra quyền ở tầng API:** các lượt đo này không chạy lại kiểm tra quyền ở tầng retrieval, vì flag không chạm vào retrieval.
- **Held-out v1 không được chạy lại**, theo đúng phạm vi yêu cầu.
