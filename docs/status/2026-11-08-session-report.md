# Báo cáo phiên 2026-11-08 (tối): việc đang dở và hạ tầng fine-tune embedding

Quy tắc như phiên vắng mặt: lệnh foreground dưới 10 phút, cổng RAM 1000 MB khi khởi động stack, rò rỉ > 0 thì dừng, eaka-verify xanh rồi mới push.

## Tóm tắt

- **Đã merge:** PR #9, #11 và #10, cả ba đều xanh 4 check trước khi merge.
- **Đã làm xong phần code và tài liệu:** A2, B4, B5, B6, C7 và C8. Mọi unit test liên quan đều xanh trên máy.
- **Chưa chạy được vì RAM:** đợt đo REL-303 (B4), đo baseline (C9) và smoke test (C10). Máy ở dưới cổng 1000 MB hơn 1 giờ, chờ nhiều lần, có lúc chỉ còn 400–600 MB. OneDrive giữ 2,1–2,7 GB và vẫn tăng, có lẽ vì repo nằm trong thư mục OneDrive. Tôi không đụng vào OneDrive.
- **Chưa push nhánh nào sau PR #10:** eaka-verify cần dựng stack test tạm, nên cũng phải qua cổng RAM.

## Từng việc

| # | Việc | Kết quả |
|---|---|---|
| A1 | Merge PR #9, #11 | Xong (`835d094`, `867618c`) |
| A2 | Ghim Ollama, DEC-014 | Xong, nhánh `feat/fix-2d-rel303` (`776305f`) |
| A3 | `eval-data/`, merge PR #10, chạy thử 5 câu UAT | Xong (`2b4121a`). Lần chạy đầu hỏng vì ollama.com trả 504; chạy lại thì thành công |
| B4 | REL-303 theo dạng câu hỏi | Code xong (`aa4ec68`). **Chưa đo; mặc định chưa đổi** |
| B5 | Nhãn held-out v1 | Xong (`de8cb22`): "owner chấp nhận ở mức diagnostic" |
| B6 | `false_refusal_dev_v1` | Xong (`6552d67`): fingerprints, `--set`, chấm theo `fact_alternatives` |
| C7 | ADR, DEC-015 | Xong, nhánh `feat/embedding-finetune-infra` (`84cc1c8`) |
| C8 | `ml/embedding_finetune/` | Xong: 5 script, script chạy trong container, lock riêng, README local/Colab, 9 unit test |
| C9 | Đo baseline (không train) | **Chưa chạy (RAM)**. Gold đã dựng: `eval-data/uat/retrieval-gold.json` (98 câu); runner UAT có `--unaccented` |
| C10 | Smoke test pipeline | **Chưa chạy (RAM)** |
| D | TASKS, HANDOFF, báo cáo, tắt stack | Xong; không còn container nào chạy |

## A2: ghim Ollama (DEC-014)

- **Runner nào cũng kiểm Ollama trước khi chạy:** UAT, held-out, RBAC dev và relevance dev đều đi qua `reranker_check.guard`, nên kiểm tra được gắn vào đó.
  - Phiên bản đọc từ `/api/version`.
  - Backend đọc từ các dòng `inference compute` trong log của server đang chạy.
  - Khác 0.40.15 hoặc khác CUDA thì runner từ chối chạy.
  - Phiên bản và backend được ghi vào kết quả lúc bắt đầu và lúc kết thúc; đổi giữa chừng thì lượt bị đánh dấu không hợp lệ.
- **Tự cập nhật:** đã tắt bằng cột `auto_update_enabled` trong `%LOCALAPPDATA%\Ollama\db.sqlite`, tương ứng công tắc "Auto update" trong giao diện. Không có bản cập nhật nào đã tải sẵn. Muốn bật lại thì dùng công tắc đó.
- **Đã kiểm tra trên log thật:** log cũ trước 06/11 18:26 cho ra VULKAN, log hiện tại cho ra CUDA, log của runner Actions cho ra CPU.

## A3: Eval trên Actions (5 câu UAT: Q001, Q021, Q041, Q061, Q081)

| | Actions (CPU, 4 vCPU, 16 GB) | Local (CUDA, GTX 1650) |
|---|---|---|
| Tổng thời gian job | 6 phút 32 giây | — |
| Cài thư viện / Ollama + pull model / build image | 1:21 / 1:26 / 1:30 | — |
| Nạp corpus V2 (9 tài liệu) | 60 giây | — |
| 5 câu hỏi | 12 giây (Q001: 7,2 s; 4 câu còn lại: 0,6–0,7 s) | Q001: 24–30 s; còn lại: 1,4–2,4 s |
| RAM dùng / còn trống khi chạy | 5,1–5,9 GB / ~10 GB | — |
| Câu trả lời và tài liệu trích | **giống hệt 2 lượt local `fix2c/base`, 5/5** | |

**Giới hạn:** 4/5 câu trả lời dưới 1 giây, nhiều khả năng đi nhánh tất định không qua LLM. Mẫu này vì vậy gần như không kiểm được chênh lệch CPU/CUDA của LLM. Muốn biết thật thì chạy đủ 100 câu.

**Dữ liệu:**
- 9 PDF trong `eval-data/` đều có metadata "Fictional Sample" và email dùng tên miền `.example`.
- File câu hỏi không chứa mật khẩu. Runner lấy mật khẩu từ `UAT_STAFF_PASSWORD`; nếu không có thì dùng giá trị mặc định đã công khai trong `compose.uat-corpus-v2.yaml`.

## B4: REL-303

Bốn test fail khi bật REL-303 có ba nguyên nhân khác nhau:
1. **Danh sách từ để hỏi chỉ có tiếng Việt có dấu.** "who", "the", "what" bị coi là từ được hỏi.
2. **Văn bản không có từ để hỏi vẫn bị kiểm.** Ví dụ "latest policy update".
3. **Câu trả lời nhắc lại câu hỏi thì không định vị được trong nguồn.** Ví dụ "The CTO is Le Thu Ha" hay "cto la le thu ha".

Bản sửa:
- **Nhận dạng dạng câu hỏi:** có dấu, không dấu hoặc tiếng Anh, chấm theo số từ để hỏi và hư từ khớp; hòa thì ưu tiên tiếng Việt. Danh sách không dấu được sinh tự động từ danh sách có dấu.
- **Không có từ để hỏi thì bỏ qua kiểm tra.**
- **Cắt phần nhắc lại câu hỏi** ở đầu và cuối câu trả lời trước khi tìm nguyên văn trong nguồn. Vẫn từ chối nếu không tìm thấy.

Kết quả unit test:
- **REL-303 bật:** 3 test thường đã pass. Test thứ 4, `N_missing_condition`, là `xfail(strict)` của blocker S01; REL-303 trả đúng `INSUFFICIENT` nên test XPASS. Khi bật mặc định phải gỡ marker này có chủ đích. Lưu ý: REL-303 đúng ở đây là nhờ câu trả lời diễn đạt lại không định vị được, chưa phải nhờ phát hiện điều kiện thiếu.
- **REL-303 tắt:** 1672 pass lúc sửa xong REL-303; sau B6, toàn bộ `tests/unit` trên nhánh là 1703 pass, 17 xfail. Có 23 test mới, tổng quát cho cả ba dạng.

Image đo `eaka-backend:fix2d` (`aa4ec68`) đã build, script đợt đo đã sẵn sàng. **Chưa chạy lượt nào**, kể cả lượt thử trước (theo observation 0010), vì cổng RAM.

## A3/C: Sự cố và quan sát

- **Stack test tạm sót lại:** lệnh `stop` trong script verify của tôi thiếu biến môi trường mà file compose bắt buộc, nên stack test tạm vẫn chạy thêm 17 phút. Tôi đã dừng nó; dữ liệu nằm trên tmpfs nên không có volume nào. Đã ghi observation 0011 cho `eaka-verify`.
- **Lỗi heredoc của Git Bash:** heredoc nuốt một dấu `\`, làm hỏng hai lần sửa file. Cả hai lỗi lộ ra ngay ở test hoặc assert và đã sửa; từ đó tôi viết script sửa file bằng công cụ Write.

## Nhánh và PR

| Nhánh | Nội dung | Trạng thái |
|---|---|---|
| `feat/fix-2d-rel303` | A2, B4, B5, B6, TASKS, HANDOFF, CHANGELOG, PROJECT_STATUS, báo cáo này | Chỉ có trên máy, **chưa push** (chưa chạy được eaka-verify) |
| `feat/embedding-finetune-infra` | C7, C8, `--unaccented` | Chỉ có trên máy, **chưa push**; PR riêng, không merge |

Hai nhánh cùng thêm một mục vào cuối `DECISIONS.md` (DEC-014 và DEC-015), nên sẽ có xung đột nhỏ khi merge cái thứ hai. Cách xử lý: giữ cả hai mục.

## Quyết định cần owner, theo mức ưu tiên

1. **RAM của máy đo:** cho phép tạm dừng đồng bộ OneDrive trong lúc đo, hoặc chuyển repo ra ngoài OneDrive. Không có một trong hai thì đợt đo REL-303, baseline fine-tune và eaka-verify tiếp tục bị chặn.
2. **REL-303:** sau khi đo theo DEC-013 mà đạt thì bật mặc định, và gỡ marker strict xfail `N_missing_condition`.
3. **Push hai nhánh** sau khi eaka-verify xanh: PR cho fix-2d; PR riêng, không merge, cho phần C.
4. **Workflow eval:** thêm `set -o pipefail` và `curl --retry` cho bước cài Ollama. Lần chạy đầu fail ở bước sau, không phải ở curl, vì pipe che lỗi. Việc này cần một PR nhỏ.
5. **Gold held-out v2:** vẫn chờ owner duyệt.

## NOT_VERIFIED

- **eaka-verify cho cả hai nhánh mới:** chưa chạy. Chỉ có unit test trên máy: `tests/unit` trên nhánh fix-2d 1703 pass, 17 xfail; trên nhánh C, các file test liên quan đều pass.
- **REL-303 trên dữ liệu thật:** chưa chạy đợt DEC-013 nào.
- **Ollama chạy CUDA thật:** cách đọc backend từ log đã kiểm trên log thật, nhưng chưa chạy trong một lượt eval thật trên máy local.
- **Pipeline fine-tune:** `in_container.py`, `generate_queries.py`, `mine_negatives.py`, `train.py` và `eval_retrieval.py` chưa chạy từ đầu đến cuối. Chỉ có phần logic thuần được unit test.
- **Phần kiểm quy tắc dữ liệu (DEC-015):** dùng fingerprints 4-gram, nên không bắt được câu viết lại ý mà không trùng cụm 4 từ nào.

## Cập nhật: sau DEC-016 (CI và Actions thay cho chạy local)

- **PR #12 (đợt đo trên Actions):** đã merge sau 4 check xanh.
  - `eval.yml` có các input: bộ câu hỏi, danh sách cấu hình flag, số lượt.
  - Bước cài Ollama dùng `pipefail` và `curl --retry 5 --retry-delay 10`.
  - UAT được chấm proxy bằng `eval-data/uat/reference-grade.json`.
  - RBAC có thêm kiểm tra rò rỉ ở tầng retrieval.
- **REL-303:** đo theo DEC-013 trên Actions, 4 job, baseline và REL-303 xen kẽ, 2 lượt mỗi bên. **Đạt**; đã bật mặc định và gỡ marker `N_missing_condition` (`docs/eval/runs/fix2d-rel303-actions.md`).
  - Relevance: 6 → 5 câu trả lời sai.
  - False-refusal, RBAC (0 rò rỉ, retrieval 18/18) và UAT (100/100): không đổi.
- **C9 và C10:** chạy trên Actions, nhánh C (`docs/eval/runs/finetune-baseline.md`).
  - **Embedding gốc:** recall@10 0,908 với câu có dấu, 0,480 khi bỏ dấu.
  - **UAT end-to-end:** proxy 98/100 với câu có dấu, 91/100 khi bỏ dấu.
  - **Smoke test:** cả pipeline chạy từ đầu đến cuối trong 7 phút; model smoke đã bị xóa trong job.
- **Chuyển ra khỏi OneDrive:** danh sách cần chép và lệnh nằm ở `docs/status/2026-11-08-move-out-of-onedrive.md`. Chưa thực hiện, không xóa gì.
