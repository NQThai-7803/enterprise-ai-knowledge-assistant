# Giai đoạn 3: lần đo held-out v2 (DEC-012)

Chuẩn bị 2026-11-15. **Chưa chạy.** Gold đã được owner duyệt và khóa ngày 2026-11-15 (`heldout-v2-gold.lock`, `approved_by: owner (NQThai-7803)`); còn chờ environment `heldout-v2-release` và merge vào `main`. Held-out v2 chỉ chạy một lần, ở mốc release, có owner duyệt.

## Phải nêu trong mọi báo cáo (DEC-022)

Ngày 2026-11-11 owner đã chạy tay 20 câu held-out v2 trên hệ thống, ngoài quy trình DEC-012. Bản ghi lần chạy đó không có trong repo và không được dùng để thiết kế bản sửa nào (chỉ ba lỗi hiển thị chung của D2 được lấy từ đó). Script in câu này ở đầu mọi bảng chấm và báo cáo.

## Các bước

1. **Owner duyệt gold.** Trang duyệt sinh bằng `scripts/eval/heldout_v2_check.py check` (`heldout-v2-review.md`); 8 câu còn chờ duyệt. Sửa trong `heldout-v2-gold.yaml` nếu cần; mọi `owner_decision` phải được giải quyết (ghi quyết định vào `notes`, rồi xoá trường đó).
2. **Khoá gold:** `python scripts/eval/heldout_v2_release.py lock-gold --approved-by "<owner>, <ngày>"` ghi `docs/eval/heldout-v2-gold.lock` (SHA256 của gold, số câu, người duyệt, thời điểm). Lệnh từ chối nếu câu hỏi khác lock, gold có lỗi cấu trúc, hoặc còn `owner_decision`. Commit file lock vào `main`.
3. **Cấu hình GitHub (một lần):** tạo environment `heldout-v2-release` trong Settings → Environments và đặt owner làm required reviewer, để mỗi lần chạy phải được duyệt trên GitHub.
4. **Chạy:** Actions → "Held-out v2 release run", trên `main`, ô `confirm` gõ đúng `DEC-012 release run approved by the owner`. Workflow (`.github/workflows/heldout-v2.yml`):
   - từ chối nếu không phải `main`, sai câu xác nhận, hoặc `gate` không qua (câu hỏi khác lock, gold chưa khoá hoặc đã đổi sau khi khoá);
   - dựng stack eval như `eval.yml` (CPU, Ollama 0.40.15, qwen2.5:3b, corpus V2), **mọi flag ở mặc định hiện tại** (ghi trong `flags.txt`);
   - chạy cả 20 câu **2 lượt**, mỗi câu một phiên, theo vai trò của câu (`run_heldout.py`, chỉ ghi câu trả lời, không chấm);
   - tính e5 cosine từ mỗi câu tới câu gần nhất của Q001-Q100 (`near-uat.json`);
   - viết `grading/grading.md` và `grading/grading.csv` cho owner: cờ REVIEW tự động và gợi ý proxy, **cột nhãn để trống**; chia hai nhóm **gần UAT (e5 ≥ 0,90)** và **còn lại**.
5. **Owner chấm** PASS / PARTIAL / FAIL / LEAK cho từng câu, từng lượt, trong `grading.csv`.
6. **Báo cáo:** `python scripts/eval/heldout_v2_release.py report <thư mục grading>` từ chối khi còn nhãn trống, rồi viết `report.md` / `report.json`: số nhãn, trả lời sai, từ chối sai, rò rỉ, **tách theo nhóm gần UAT / còn lại**, kèm câu DEC-022. Nhóm còn lại là tín hiệu chính, vì nhóm gần UAT dễ được lợi từ các vòng tinh chỉnh trên UAT (`docs/design/pipeline-loss-fix-plan.md` mục 7).

## Giới hạn

- Kiểm tra "Ollama khởi động lại" của held-out v1 dùng bộ theo dõi máy Windows; trên runner Linux, tính hợp lệ của một lượt chỉ xét INFRA_ERROR và độ trễ trên 120 s. `ollama.log` và `memory.log` được lưu để kiểm tay.
- Số đo trên CPU của Actions, không so trực tiếp với lượt local (DEC-016).
