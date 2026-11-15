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
   - `preflight` ngay sau khi dựng stack: reranker, Ollama (DEC-014), đăng nhập mỗi vai trò; lỗi ở đây không tốn bước nạp corpus và chưa gửi câu nào (`preflight_only` chỉ chạy tới đây);
   - dựng stack eval như `eval.yml` (CPU, Ollama 0.40.15, qwen2.5:3b, corpus V2), **mọi flag ở mặc định hiện tại** (ghi trong `flags.txt`);
   - chạy cả 20 câu **2 lượt**, mỗi câu một phiên, theo vai trò của câu (`run_heldout.py`, chỉ ghi câu trả lời, không chấm);
   - tính e5 cosine từ mỗi câu tới câu gần nhất của Q001-Q100 (`near-uat.json`);
   - viết `grading/grading.md` và `grading/grading.csv` cho owner: cờ REVIEW tự động và gợi ý proxy, **cột nhãn để trống**; chia hai nhóm **gần UAT (e5 ≥ 0,90)** và **còn lại**.
5. **Owner chấm** PASS / PARTIAL / FAIL / LEAK cho từng câu, từng lượt, trong `grading.csv`.
6. **Báo cáo:** `python scripts/eval/heldout_v2_release.py report <thư mục grading>` từ chối khi còn nhãn trống, rồi viết `report.md` / `report.json`: số nhãn, trả lời sai, từ chối sai, rò rỉ, **tách theo nhóm gần UAT / còn lại**, kèm câu DEC-022. Nhóm còn lại là tín hiệu chính, vì nhóm gần UAT dễ được lợi từ các vòng tinh chỉnh trên UAT (`docs/design/pipeline-loss-fix-plan.md` mục 7).

## Giới hạn

- Kiểm tra "Ollama khởi động lại" của held-out v1 dùng bộ theo dõi máy Windows; trên runner Linux, tính hợp lệ của một lượt chỉ xét INFRA_ERROR và độ trễ trên 120 s. `ollama.log` và `memory.log` được lưu để kiểm tay.
- Số đo trên CPU của Actions, không so trực tiếp với lượt local (DEC-016).

## Sự cố: run #1 (2026-11-15, Actions run `43697066034`, commit `d907e9a`)

- **Lỗi ở bước "Run held-out v2 twice"** (bước 13), sau 7 phút 34 giây. Các bước trước đều xong: gate, cài Ollama, build image, dựng stack, nạp corpus V2 (38 tài liệu).
- **Nguyên nhân:** runner từ chối chạy ở bước kiểm Ollama (DEC-014): `Ollama backend is unknown (no 'inference compute' line in None since the server started); wait for GPU discovery or set EVAL_OLLAMA_LOG`. Workflow không đặt `EVAL_OLLAMA_LOG` (`eval.yml` có đặt), nên runner không đọc được backend Ollama. Lý do từ chối chỉ in ra stderr, nên `run1/runner.log` rỗng.
- **Số câu held-out đã chạy: 0.** Runner dừng trước câu đầu tiên. Artifact không có `runtime_results.json` và không có `run2/`. `stack.log` có 0 request tới `/api/v1/chat`, 0 dòng chẩn đoán RAG; chỉ có 38 request upload tài liệu và 2 lần đăng nhập. `warmup.json` là lần warm-up Ollama với prompt cố định ("Reply with OK."), không phải câu held-out.
- **Artifact của run #1 không được dùng để chấm** và không được mở ngoài việc liệt kê tên file và đếm dòng.
- **Sửa:** workflow đặt `EVAL_OLLAMA_LOG`; bước mới `preflight` (`heldout_v2_release.py preflight`) chạy mọi kiểm tra của runner (gate, reranker, Ollama, một lần đăng nhập mỗi vai trò) ngay sau khi dựng stack, trước khi nạp corpus và trước câu đầu tiên; `runner.log` ghi cả stderr; input `preflight_only` cho phép chạy riêng phần kiểm mà không gửi câu nào. Test chặn hồi quy: `tests/unit/test_heldout_v2_release.py`.
- Lần chạy kế tiếp vẫn là lần đo held-out v2 đầu tiên theo DEC-012, vì run #1 chưa gửi câu nào. Báo cáo của lần đó phải nêu run #1 cùng với sự việc DEC-022.

## Lượt đo held-out v2 (2026-11-15)

- **Actions run `43701804785`, commit `ff5016d`**, mặc định hiện tại, CPU, Ollama 0.40.15 (backend CPU, kiểm ở đầu và cuối mỗi lượt), `reranker_mode=lexical_fallback`. Trước đó: `43701078424` huỷ sau 14 s, `43701098015` chỉ chạy preflight; cả hai không gửi câu nào.
- **Hai lượt hợp lệ:** mỗi lượt 20/20 câu, 0 INFRA_ERROR, 0 lần thử lại, không câu nào quá 120 s (lớn nhất 84,5 s và 83,0 s). SHA256 câu hỏi và gold khớp lock.
- Bảng chấm: `docs/eval/runs/heldout-v2-ff5016d/grading.md` và `grading.csv`, chép nguyên từng byte từ artifact; **chưa có nhãn**, owner chấm. Cờ REVIEW và gợi ý proxy trong đó là phần tự động của bảng chấm, không phải nhãn.
- **Owner đã chấm** (owner (NQThai-7803), 2026-11-15) trong `grading.csv`. Báo cáo: `docs/eval/runs/heldout-v2-ff5016d/report.md` và `report.json`, sinh bằng `heldout_v2_release.py report --grader "owner (NQThai-7803)" --run "43701804785 (ff5016d)"`. Nhãn lượt 2 để trống được lấy từ lượt 1 theo quy tắc của held-out v1 (chỉ khi hai lượt giống hệt nhau): 18 câu; hai câu có hai lượt khác nhau (HO2-004, HO2-018) có nhãn riêng.
