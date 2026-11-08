# Báo cáo phiên không có người, 2026-11-08 13:20 đến khoảng 15:00

Làm theo thứ tự 9 việc của chủ dự án. Mọi lệnh chạy foreground; cổng RAM 1000 MB chỉ áp dụng lúc khởi động stack. Không đụng V2, AUTH-02, các volume cũ, và không sửa gold held-out v2.

## Từng việc

| # | Việc | Kết quả |
|---|---|---|
| 1 | Merge PR #8 | **Đã merge** (`bb60566`), cả 4 check xanh. |
| 2 | Bật mặc định REL-303 | **Bỏ qua, cần owner quyết định.** Bật mặc định làm 4 unit test fail, vì bộ lọc từ để hỏi chỉ khớp chữ có dấu. Câu hỏi tiếng Anh ("Who is the CEO?") và tiếng Việt không dấu ("CTO Nova Digital la ai?") bị tính từ để hỏi là nội dung, nên câu trả lời đúng bị từ chối. Không mở PR, không có DEC-014. |
| 3 | Held-out v1 diagnostic | **Xong.** Cấu hình: mặc định mới cộng REL-303 bật qua biến môi trường. Xem bảng dưới. Không chỉnh gì theo kết quả này. |
| 4 | Chuẩn bị FIX 3 | **Xong, chờ duyệt.** Dev hiện có không có ca nào cho cả hai cơ chế, nên đã soạn và đóng băng `false_refusal_dev_v1` (20 câu). `docs/eval/runs/fix3-diagnosis.md`. |
| 5 | Kết quả lệch giữa các đợt | **Xong phần chẩn đoán.** Nguyên nhân là Ollama đổi backend GPU từ Vulkan sang CUDA, rồi tự cập nhật phiên bản, không phải do khởi động lại. Chưa chạy thí nghiệm 20 câu vì RAM. `docs/eval/runs/nondeterminism.md`. |
| 6 | Lọc bản rà soát bỏ dấu | **Xong.** Giữ 568 cue một từ có va chạm thật trong corpus, loại 960 cue không có va chạm trong corpus và 124 cue nằm giữa các từ tiếng Anh, rồi xếp theo mức nguy hiểm. Mục "Lọc tay" trong `docs/eval/runs/diacritics-audit.md`. |
| 7 | Eval trên GitHub Actions | **Đã viết workflow, chưa chạy được.** PR #10, không merge. Corpus V2 và UAT không có trong repo, nên workflow chỉ chạy được bộ dev mới và RBAC dev. GitHub chỉ cho kích hoạt workflow đã có trên nhánh mặc định (lỗi 404). |
| 8 | Test lock cần `docs/` | **Xong.** PR #9, không merge. Image chạy `pytest tests/unit -q` sạch mà không cần mount `docs/`. |
| 9 | Báo cáo, HANDOFF, tắt stack | **Xong.** Không còn container nào chạy. |

## Held-out v1 (diagnostic)

| Chỉ số | Baseline `f3cdbf3` | `strict` | Mặc định mới cộng REL-303 |
|---|---:|---:|---:|
| Rò rỉ | 0 | 0 | **0** |
| PASS / PARTIAL / FAIL | 11 / 1 / 28 | 12 / 2 / 26 | 14 / 2 / 24 |
| Trả lời sai | 5/14 | 5/14 | **3/14** |
| Từ chối sai | 14/26 | 15/26 | 14/26 |

- **Không so trực tiếp được:** hai lượt trước chạy trên Vulkan, lượt này chạy trên CUDA.
- **10 câu đổi nhãn:** Claude chấm đề xuất, **chờ owner xác nhận** (`docs/eval/runs/heldout-v1-defaults-bb60566/score.md`).
- **Câu cải thiện:** HO-008 và HO-020 từ trả lời sai thành từ chối đúng; HO-038 thành PASS.
- **Câu xấu đi:** HO-037 từ PASS thành từ chối sai.

## PR

| PR | Nội dung | Trạng thái |
|---|---|---|
| #8 | REL-402 mặc định, REL-303 sửa | Đã merge |
| #9 | Test lock dùng `repo_layout` | Chờ duyệt, không merge |
| #10 | Workflow eval thủ công | Chờ duyệt, không merge |
| #11 | Tài liệu của phiên này: FIX 3, lệch giữa các đợt, lọc bỏ dấu, held-out v1, báo cáo, HANDOFF | Chờ duyệt, không merge |

Ba nhánh PR #9, #10, #11 được verify chung trên một image ghép từ cả ba (`ebcb62e`): 0 fail, 0 hồi quy.

## Quyết định cần owner, theo mức ưu tiên

1. **REL-303:** chọn một trong hai hướng:
    - Xử lý câu hỏi không dấu và tiếng Anh: bỏ từ để hỏi cả trên văn bản không dấu khi câu hỏi không có dấu, thêm danh sách từ để hỏi tiếng Anh, rồi đo lại cùng đợt.
    - Giữ tắt.
2. **Nhãn held-out v1:** xác nhận 10 nhãn đề xuất.
3. **Ollama:** ghim backend và phiên bản, tắt tự cập nhật trong lúc đo, và ghi backend vào metadata. Các baseline trước 2026-11-06 18:26 không so được với các đợt sau.
4. **`false_refusal_dev_v1`:** duyệt bộ dev. Nếu cần sửa thì làm v1.1. Sau đó cần thêm runner chấm theo `fact_alternatives`.
5. **PR #10:** duyệt workflow và cách đưa corpus V2 với UAT lên Actions nếu muốn (dữ liệu hiện không có trong repo); để chạy thử cần merge trước hoặc thêm tạm trigger push.
6. **PR #9 và #11:** duyệt và merge.
7. **Gold held-out v2:** vẫn chờ duyệt, chưa khóa.

## NOT_VERIFIED

- Thí nghiệm khởi động lại Ollama và so CUDA với Vulkan trên 20 câu UAT: chưa chạy vì RAM dưới 1000 MB suốt hơn 15 phút.
- Workflow eval: chưa chạy lần nào trên Actions, nên thời gian, RAM và độ khớp với máy local chưa biết.
- Thứ hạng cue trong bản rà soát bỏ dấu là tự động theo hàm chứa cue; chưa đọc code ở từng vị trí.
- Các lane cần model thật chỉ chạy trên CI.

## Sự cố

- **Build image chạy nền dưới áp lực bộ nhớ:** lần build đầu không tạo ra image; build lại ở foreground thì được.
- **Container BuildKit sót lại:** chiếm RAM, tôi đã dừng (không xóa).
- **Chờ RAM:** OneDrive giữ khoảng 0,9-1,2 GB, nên phải chờ RAM nhiều lần.
