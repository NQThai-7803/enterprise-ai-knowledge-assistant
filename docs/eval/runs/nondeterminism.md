# Vì sao kết quả lệch giữa các đợt

Ngày 2026-11-08. Câu hỏi: vì sao cùng seed, temperature 0, mà hai lượt UAT trong cùng đợt giống nhau 100/100, còn lượt khác ngày chỉ giống 90/100? **Chưa đổi cấu hình mặc định nào.**

## Kết luận

**Lệch xảy ra khi Ollama đổi backend GPU, không phải khi Ollama khởi động lại.** Ngày 2026-11-06, trước 18:26, Ollama 0.40.14 chạy model trên Vulkan, vì không thấy driver NVIDIA (log ghi `driver=0.0`). Sau khi máy khởi động lại, Ollama nhận driver CUDA 13.3 và chuyển sang CUDA. Lúc 18:27, nó tự cập nhật lên 0.40.15. Cùng một card GTX 1650, hai backend tính số thực khác nhau, nên văn bản sinh ra có thể khác.

## Bằng chứng từ các lượt đã có

Mỗi lượt được gán backend theo giờ bắt đầu và log của Ollama (`%LOCALAPPDATA%\Ollama\server*.log`).

| So sánh | Cấu hình | Backend | Giống nhau |
|---|---|---|---:|
| UAT: FIX 2 baseline lượt 2 (06/11 18:57) với FIX 2a baseline (07/11 01:06) | giống | CUDA, CUDA; Ollama khởi động lại ở giữa | **100/100** |
| UAT, bộ dev mới, RBAC: FIX 2a tổ hợp (07/11 00h) với FIX 2b baseline (07/11 22h) | giống | CUDA, CUDA; Ollama khởi động lại ở giữa | **100/100, 25/25, 36/36** |
| Bộ dev mới: FIX 2 baseline (06/11 15:40) với FIX 2a baseline (06/11 23:28) | giống | **Vulkan**, CUDA | 23/25 |
| RBAC: FIX 2 baseline (06/11 16:07) với FIX 2a baseline (07/11 00:12) | giống | **Vulkan**, CUDA | 34/36; RBD-07 đổi trạng thái |
| UAT: `strict` FIX 1 (05/11) với FIX 2 baseline (06/11 18:42), tức con số "90/100" ghi trong TASKS | giống mode | **Vulkan**, CUDA | 90/100 |

- **Cùng backend thì khớp hoàn toàn,** dù khác ngày, khác phiên và Ollama đã khởi động lại.
- **Khác backend thì lệch.** REL-101 đổi cơ chế giữa FIX 2 (Vulkan) và FIX 2a (CUDA) chính là ở mốc này.

## Cấu hình Ollama ghi nhận

- **Phiên bản:** 0.40.15, cập nhật tự động từ 0.40.14 lúc 2026-11-06 18:27. Bộ kiểm tra cập nhật chạy mỗi giờ.
- **Biến môi trường:** `OLLAMA_CONTEXT_LENGTH=8192`, `OLLAMA_NUM_PARALLEL=1`, `OLLAMA_FLASH_ATTENTION=false` (nhưng log vẫn ghi flash attention bật ở chế độ `auto`), `OLLAMA_VULKAN=true`, `OLLAMA_LLM_LIBRARY` để trống, `OLLAMA_KEEP_ALIVE=5m` (app gửi `10m`).
- **Runner:** `n_threads = 4` (máy có 4 nhân, 8 luồng), `n_seq_max = 1`, `n_ctx_slot = 8192`, `n_batch = 512`, 37/37 lớp chạy trên GPU.
- **Phần cứng:** Intel i5-10300H, NVIDIA GTX 1650 4 GB và Intel UHD (Ollama bỏ qua GPU tích hợp).
- **Model:** `qwen2.5:3b`, Q4_K_M. App gửi `seed=20261031` và `temperature=0`.

`OLLAMA_NUM_PARALLEL` đã là 1 và `n_threads` không đổi giữa các log, nên không phải hai yếu tố này.

## Thí nghiệm khởi động lại Ollama

Chưa chạy: RAM trống ở dưới 1000 MB suốt hơn 15 phút, nên tôi bỏ qua theo quy tắc. Dữ liệu cũ đã cho thấy kết quả không đổi qua 2 lần khởi động lại Ollama khi vẫn trên CUDA. Nếu có thời gian, thí nghiệm đúng nên làm là cùng 20 câu, so CUDA với Vulkan, bật/tắt bằng `OLLAMA_VULKAN` hoặc `CUDA_VISIBLE_DEVICES`, thay vì chỉ khởi động lại.

## Đề xuất, chưa áp dụng

1. **Ghi backend và phiên bản Ollama vào metadata của mỗi lượt eval** (đọc `/api/version` và log), và từ chối so hai lượt khác backend hoặc khác phiên bản, giống cách DEC-011 làm với image.
2. **Tắt tự cập nhật Ollama** trong thời gian đo, hoặc ghim phiên bản.
3. **Ghim backend:** CUDA nếu driver luôn có. Kiểm tra `driver=` trong log trước mỗi đợt; `driver=0.0` nghĩa là đang chạy trên Vulkan.
4. **Coi mọi baseline trước 2026-11-06 18:26 là từ backend khác.** Các đợt FIX 1, FIX 2 (trừ UAT) và held-out v1 `f3cdbf3` không so trực tiếp được với các đợt sau.
