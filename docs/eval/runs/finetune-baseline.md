# Baseline cho fine-tune embedding (chưa train), và smoke test pipeline

Ngày 2026-11-08. Chạy trên GitHub Actions theo DEC-016: CPU, Ollama 0.40.15, `qwen2.5:3b`. Không so với các lượt local (CUDA).

- **Retrieval và smoke test:** run `42486993473`, set `ml`, nhánh `feat/embedding-finetune-infra` (`d919557`).
- **UAT end-to-end:** run `42486997184`, set `uat`, configs `vi; unacc:EVAL_UAT_UNACCENTED=1`, cùng nhánh.

Các file kết quả nằm trong artifact của từng run, lưu 14 ngày; trên máy local ở `artifacts/actions-eval/`. Không file nào được commit.

## 1. Retrieval bằng embedding gốc

Bộ đánh giá:
- **Câu hỏi:** UAT Q001-Q100, là bộ dev, không dùng held-out.
- **Gold:** tài liệu và trang mà câu trả lời đã chấm tay trích dẫn (`eval-data/uat/retrieval-gold.json`). Có 98 câu có gold; 2 câu bị bỏ vì không có chunk nào phủ trang gold.
- **Cách xếp hạng:** cosine chính xác của `intfloat/multilingual-e5-small` trên toàn bộ 143 chunk của corpus V2, với tiền tố `query: ` và `passage: `. Đây chỉ là phần embedding, không phải xếp hạng hybrid của app.

| Dạng câu hỏi | n | recall@1 | recall@5 | recall@10 | MRR@10 |
|---|---:|---:|---:|---:|---:|
| Có dấu (nguyên văn) | 98 | 0,449 | 0,827 | 0,908 | 0,601 |
| Bỏ dấu (tự động) | 98 | 0,153 | 0,337 | **0,480** | **0,247** |
| Tiếng Anh | — | — | — | — | — |

- **Bỏ dấu là điểm yếu lớn của embedding gốc:** recall@10 giảm 0,43 (từ 0,908 xuống 0,480), MRR@10 giảm còn khoảng 40% (từ 0,601 xuống 0,247).
- **Tiếng Anh: chưa đo.** Chưa có bản tiếng Anh của câu hỏi dev, nên tôi không tự dịch để đưa vào bộ đánh giá.

## 2. UAT end-to-end: có dấu và bỏ dấu, cùng job

Mỗi dạng chạy 1 lượt: cùng image, cùng Ollama, mặc định hiện tại (REL-303 tắt). Chấm proxy theo file chấm tay TASK-035.3B: so trạng thái và các tài liệu được trích.

| Dạng câu hỏi | Proxy khớp | ANSWERED / NO_ANSWER | Câu trả lời trùng nguyên văn bản chấm tay |
|---|---:|---|---:|
| Có dấu | **98/100** | 97 / 3 | 89 |
| Bỏ dấu | **91/100** | 93 / 7 | 78 |

- **Mất 8 câu:** Q004, Q008, Q012, Q022, Q051, Q075, Q094, Q096. Bốn câu chuyển thành từ chối; bốn câu vẫn trả lời nhưng trích sai tài liệu.
- **Được 1 câu:** Q002.
- **Thiệt hại end-to-end nhỏ hơn nhiều so với phần embedding,** vì nhánh keyword bỏ dấu khi so khớp và các nhánh tất định bù lại. Đây chỉ là 1 lượt mỗi dạng; con số chính xác cần 2 lượt.

## 3. Smoke test pipeline (C10)

Chạy trên CPU, chỉ để chứng minh các script chạy được từ đầu đến cuối. Model sinh ra đã bị xóa trong job, không được tải lên, và không dùng cho việc gì khác.

| Bước | Kết quả |
|---|---|
| `generate_queries.py` (10 chunk) | 38 câu hỏi; **3 câu bị loại vì trùng cụm 4 từ với một bộ được bảo vệ** (DEC-015) |
| `augment.py --english` | 190 dòng: 38 câu cho mỗi dạng `vi`, `vi_unaccented`, `vi_partial`, `vi_typo`, `en`; 0 câu bị loại |
| `mine_negatives.py` (hybrid thật, trong container) | 190/190 dòng có negative; chunk dương nằm trong top 10 hybrid ở 145/190 câu |
| `train.py` (50 cặp, batch 8, max_seq_length 128, CPU, 1 epoch) | Chạy trong 21 giây, loss trung bình 2,23. `training_config.json` có hash của dữ liệu và phiên bản thư viện |
| `eval_retrieval.py` (model gốc so với model smoke) | Chạy được. Model smoke **kém hơn** (recall@10 khi có dấu: 0,776 so với 0,908), đúng như dự kiến với 50 cặp và đoạn văn bị cắt ở 128 token |

Thời gian và tài nguyên:
- **Thời gian:** cả bước ML mất 415 giây. Riêng baseline mất 179 giây, gồm cả xuất chunk và sinh câu hỏi.
- **RAM:** runner dùng tối đa khoảng 9,0 GB trên 16 GB, còn trống khoảng 7 GB.
- **Thư viện:** `requirements-train.lock` cài được trên runner (torch 2.14.1+cpu, sentence-transformers 6.1.0).

Quan sát cho lần train thật:
- **Câu hỏi "meta":** model 3B sinh cả câu hỏi về mục lục hay mã tài liệu ("Thông tin về mã tài liệu ND-CORP-001?"). Nên lọc các câu này trước khi train.

## 4. Kết luận cho kế hoạch

Theo `TASKS.md`, fine-tune làm sau FIX 3.
- **Mục tiêu có số đo cụ thể:** nâng recall@10 khi bỏ dấu từ 0,480, mà không làm giảm quá 1 điểm ở 0,908 khi có dấu (tiêu chí trong `docs/design/embedding-finetune.md`).
- **End-to-end:** 7 điểm proxy UAT (98 so với 91) là phần có thể lấy lại.
