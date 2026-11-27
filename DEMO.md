# Demo stack (eaka-demo)

Stack trình diễn trên một máy, có frontend mới (PR #61), chạy từ một bản export của `main`.
Không có secret trong file này. Kịch bản cũ của MVP nằm ở `DEMO_SCENARIO.md`.

- **URL:** <http://127.0.0.1:18480>.
  - Mở đúng `127.0.0.1`, **không dùng `localhost`**: bản build đã cố định địa chỉ API, nên trang mở bằng `localhost` gọi API khác origin và bị chặn CORS.
  - Không publish cổng nào khác: nginx của frontend chuyển `/api/` và `/health/` sang container API.
- **Cấu hình:**
  - mặc định của `main`: `simple` (s1-s3), `qwen3.5-text:4b`, DRAFT `exclude`, chọn chunk `rrf`;
  - riêng `.env` của demo thêm `LLM_OLLAMA_KEEP_ALIVE=30m` để model không bị dỡ giữa buổi.

## Phần cứng và chuẩn bị

- **Máy đã đo:**
  - RAM 8 GB, Docker Desktop (VM 4 GB);
  - GPU NVIDIA GTX 1650 4 GB;
  - Ollama chạy trên host, với `qwen3.5-text:4b` dựng bằng `PARAMETER num_gpu 99` (`scripts/deploy/ollama_text_model.py`, `DEPLOYMENT.md`). `ollama ps` phải báo `100% GPU`.
- **Trước khi demo:**
  - tắt V2, stack chính (`enterprise-ai-knowledge-assistant`) và `eaka-smoke`;
  - đóng các ứng dụng nặng (trình duyệt nhiều tab, IDE);
  - RAM trống nên còn ≥ 2 GB.
- **Giới hạn bộ nhớ** (giống `eaka-smoke`) và mức đã dùng:

  | Container | Giới hạn | Đã dùng |
  |---|---|---|
  | api | 1200m | khoảng 1,0 GiB |
  | worker | 1600m | 1,2 GiB sau khi nạp tài liệu |
  | postgres | 384m | |
  | redis | 64m | |
  | frontend | 64m | |

- **Không container nào tự khởi động lại** (`restart: "no"`). Container nào dừng (ví dụ api bị giết vì hết bộ nhớ) thì chạy lại `.\demo.ps1 up`.

## Bố cục (ngoài repo, `C:\dev\eaka-demo`)

| Đường dẫn | Nội dung |
|---|---|
| `src\` | `git archive` của `main`; `src\.env` là `.env` riêng của demo (secret ngẫu nhiên, không nằm trong repo nào) |
| `compose.demo.yaml` | Phủ lên `compose.yaml` + `compose.uat-corpus-v2.yaml`:<br>• image riêng;<br>• `restart: "no"`;<br>• giới hạn bộ nhớ;<br>• chỉ frontend có cổng (`127.0.0.1:18480`);<br>• `RAG_DIAGNOSTICS_ENABLED=false` (mặc định của app) |
| `demo.ps1` | `up` / `down` / `status` / `warmup` / `seed` |
| `seed_demo.py` | Nạp dữ liệu demo (chạy qua `demo.ps1 seed`) |
| `check_demo.py` | Kiểm qua nginx; `--matrix` hỏi các câu mẫu bằng cả 4 tài khoản |
| `questions.md` | Nội dung các câu mẫu (chỉ ở máy, vì repo công khai chỉ ghi ID) |

- **Image:**
  - backend `eaka-backend:demo-<sha>`, `docker build --target runtime` trong `src`;
  - frontend `eaka-frontend:demo-<sha>`:

    ```
    docker build -f deploy/frontend/Dockerfile --build-arg VITE_API_BASE_URL=http://127.0.0.1:18480 .
    ```

    Image này là nginx phục vụ bản build của SPA, kèm reverse proxy `/api/`. SSE không bị buffer hay nén, `proxy_read_timeout` là 300 s, và mọi route của app đều trả về `index.html`.
- **Volume:**
  - `eaka-demo_*`; `demo.ps1 down` giữ nguyên volume;
  - **Không bao giờ chạy `docker compose down -v`.**
  - Cache model e5 (`eaka-demo_model_cache`) được chép từ cache của một stack khác, nên lúc nạp tài liệu không phải tải lại.

## Lệnh

```powershell
cd C:\dev\eaka-demo
.\demo.ps1 up       # bật stack, chờ /health/live qua 18480
.\demo.ps1 warmup   # nạp LLM + embedding, đo 3 câu dev (chạy trước khi trình bày)
.\demo.ps1 status
.\demo.ps1 down     # tắt, giữ volume
.\demo.ps1 seed     # chỉ khi dựng mới: nạp dữ liệu (idempotent)
python check_demo.py [--matrix]
```

## Dữ liệu và tài khoản

- **Tài liệu:**
  - UAT Corpus v2: 9 tài liệu, nạp qua `scripts/eval/bootstrap_corpus_v2.py` như eval. `UAT-LEAVE-AUTHORITY-001` là DRAFT nên không bao giờ được dùng để trả lời; `UAT-GROUNDING-001` là PRIVATE và chỉ cấp quyền cho manager.
  - 4 tài liệu của bộ RBAC dev (`tests/acceptance/rbac_dev_v1.yaml`). Riêng trong demo, `RBAC-REV-001` là tài liệu DEPARTMENT của UAT-KNOWLEDGE (trong bộ dev nó là PRIVATE, có quyền bị thu hồi). Nhờ vậy mỗi phòng ban có một tài liệu DEPARTMENT.
- **Tài khoản** (chỉ ghi email). Mật khẩu ngẫu nhiên, lưu ở biến môi trường cấp User `EAKA_DEMO_<VAI_TRÒ>_PASSWORD`:

  | Email | Vai trò | Phòng ban | Thấy |
  |---|---|---|---|
  | `admin.uat@example.test` | ADMIN | (không) | 13 tài liệu |
  | `manager.uat@example.test` | MANAGER | UAT-KNOWLEDGE | 12 (mọi tài liệu trừ RBAC-OPS-001) |
  | `staff.uat@example.test` | STAFF | UAT-KNOWLEDGE | 10 (ORGANIZATION + RBAC-REV-001) |
  | `ops-staff.rbac@example.test` | STAFF | UAT-OPS | 10 (ORGANIZATION + RBAC-OPS-001) |

  `<VAI_TRÒ>` lần lượt là `ADMIN`, `MANAGER`, `STAFF`, `OPS`.

## Kịch bản 5-7 phút

Câu hỏi chỉ lấy từ bộ dev (UAT Q001-Q100 và RBAC dev), không dùng held-out. Nội dung câu nằm trong `C:\dev\eaka-demo\questions.md`. Kết quả dưới đây đo ngày 2026-11-27.

| Câu | Tài liệu (mức hiển thị) | admin | manager | staff | ops-staff |
|---|---|---|---|---|---|
| Q016 | ND-HR-002 (ORGANIZATION) | trả lời | trả lời | trả lời | trả lời |
| Q043 | ND-HR-004 (ORGANIZATION) | trả lời | trả lời | trả lời | trả lời |
| RBD-01 | RBAC-MGR-001 (PRIVATE, quyền cho manager) | trả lời | trả lời | từ chối | từ chối |
| RBD-13 | RBAC-REV-001 (DEPARTMENT, UAT-KNOWLEDGE) | trả lời | trả lời | trả lời | từ chối |
| RBD-07 | RBAC-OPS-001 (DEPARTMENT, UAT-OPS) | trả lời | từ chối | từ chối | trả lời |

1. **(1 phút) staff:** đăng nhập, hỏi Q016, rồi mở trích dẫn để xem trang PDF.
2. **(1 phút) staff:** hỏi Q043, một câu khác trong cùng bộ quy định chung.
3. **(1,5 phút) staff rồi manager:**
   - staff hỏi RBD-01 và nhận câu từ chối cố định, không có trích dẫn (tài liệu PRIVATE của manager);
   - đổi sang manager, hỏi lại RBD-01 và được trả lời từ RBAC-MGR-001.
4. **(1,5 phút) cùng phòng và khác phòng:**
   - staff hỏi RBD-13 và được trả lời (tài liệu DEPARTMENT của phòng mình);
   - ops-staff hỏi RBD-13 thì bị từ chối;
   - ops-staff hỏi RBD-07 và được trả lời (tài liệu của phòng vận hành), còn staff hỏi RBD-07 thì bị từ chối.
5. **(1 phút) admin:**
   - trang tài liệu: admin thấy cả 13 tài liệu, gồm tài liệu DRAFT;
   - nhắc rằng DRAFT không bao giờ được dùng để trả lời, và câu trả lời chỉ trích tài liệu người hỏi được quyền xem.

## Khi câu đầu chậm

| Trạng thái | Thời gian |
|---|---|
| Câu đầu sau `up` (model chưa nạp) | 49-60 s |
| Câu mới khi model đã nạp | 15-19 s |
| Câu đã hỏi (cache trả lời) | 1-2 s |

- Luôn chạy `.\demo.ps1 warmup` sau `up` và ngay trước khi trình bày.
- Model ở lại trên GPU 30 phút sau câu cuối. Nếu ngồi chờ lâu hơn, chạy `warmup` lại.
- Nếu một câu vượt quá khoảng 60 s, xem `ollama ps`: model phải báo `100% GPU` và `qwen3.5-text:4b`.
