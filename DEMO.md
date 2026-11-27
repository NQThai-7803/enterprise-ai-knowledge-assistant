# Demo stack (eaka-demo)

Stack trình diễn trên một máy, có frontend mới (PR #61), dựng thẳng từ repo bằng
`deploy/demo/demo.ps1`. Không có secret trong file này. Kịch bản cũ của MVP nằm ở `DEMO_SCENARIO.md`.

- **URL:** <http://127.0.0.1:18480> hoặc <http://localhost:18480>.
  - Bản build gọi API cùng origin (BR-13, `VITE_API_BASE_URL=""`), nên host nào cũng chạy.
  - Không publish cổng nào khác: nginx của frontend chuyển `/api/` và `/health/` sang container API.
- **Cấu hình:**
  - mặc định của `main`: `simple` (s1-s3), `qwen3.5-text:4b`, DRAFT `exclude`, chọn chunk `rrf`;
  - `.env` của demo (do `demo.ps1 init` tạo) thêm `LLM_OLLAMA_KEEP_ALIVE=30m` để model không bị dỡ giữa buổi.

## Chạy từ bản clone mới

Mọi thứ cần để dựng demo đều nằm trong repo: script ở `deploy/demo/`, 9 PDF của UAT Corpus v2 ở
`eval-data/corpus-v2/` (kiểm SHA-256 trước khi nạp), 4 tài liệu RBAC dev sinh từ
`tests/acceptance/rbac_dev_v1.yaml`, câu hỏi dev đọc theo ID từ `eval-data/uat/questions.json` và
`tests/acceptance/rbac_dev_v1.yaml`. Không cần file nào ở ngoài repo.

**Yêu cầu máy**

- Windows 10/11, Windows PowerShell 5.1 hoặc PowerShell 7, Git, Python 3.12 trên host (chỉ thư
  viện chuẩn, cho `scripts/deploy/ollama_text_model.py` và `check_demo.py`).
- Docker Desktop (WSL 2), VM được cấp ít nhất 4 GB. RAM máy tối thiểu 8 GB (máy đã đo), nên có 16 GB.
- Ollama chạy trên host (đã đo với 0.40.15). Nên có GPU NVIDIA từ 4 GB VRAM; chỉ CPU vẫn chạy
  nhưng khoảng 77 s mỗi câu (`DEPLOYMENT.md`).
- Khoảng 15 GB đĩa trống: image backend khoảng 2,4 GB, model Ollama khoảng 3,3 GB, model e5,
  cache build.
- Mạng ở lần đầu: Docker Hub, PyPI, npm, Hugging Face (model e5), registry của Ollama.
- Cổng `127.0.0.1:18480` còn trống.

**Các bước** (PowerShell, đứng ở thư mục gốc của bản clone)

```powershell
git clone https://github.com/NQThai-7803/enterprise-ai-knowledge-assistant.git eaka
cd eaka
git checkout test-2026-11-27
Set-ExecutionPolicy -Scope Process Bypass   # Windows mặc định chặn chạy .ps1

# 1. Ollama (DEPLOYMENT.md 3.1, 3.2): đặt 2 biến rồi khởi động lại Ollama
[Environment]::SetEnvironmentVariable('OLLAMA_CONTEXT_LENGTH', '8192', 'User')
[Environment]::SetEnvironmentVariable('LLAMA_ARG_CACHE_RAM', '2048', 'User')

# 2. Model qwen3.5-text:4b (một lần; máy không có GPU thì bỏ --num-gpu 99)
python scripts/deploy/ollama_text_model.py qwen3.5:4b qwen3.5-text:4b --num-gpu 99

# 3. .env từ .env.example và 4 mật khẩu demo
.\deploy\demo\demo.ps1 init

# 4-7. image, stack, dữ liệu, làm nóng
.\deploy\demo\demo.ps1 build     # 2 image theo commit, lần đầu khoảng 10-20 phút
.\deploy\demo\demo.ps1 up        # chờ /health/live qua 18480
.\deploy\demo\demo.ps1 seed      # 13 tài liệu và tài khoản ops, vài phút
.\deploy\demo\demo.ps1 warmup    # nạp LLM, đo 3 câu dev

# 8. kiểm tra
python deploy\demo\check_demo.py --matrix
.\deploy\demo\demo.ps1 questions # ID và nội dung các câu mẫu
```

- **`init`:**
  - chép `.env.example` thành `.env`, thay `SECRET_KEY` và mật khẩu Postgres bằng giá trị ngẫu nhiên;
  - đặt `LLM_ENABLED=true`, `LLM_PROVIDER=ollama`, `LLM_OLLAMA_KEEP_ALIVE=30m`, `LLM_MAX_OUTPUT_TOKENS=512`;
  - tạo 4 biến môi trường User `EAKA_DEMO_{ADMIN,MANAGER,STAFF,OPS}_PASSWORD` ngẫu nhiên nếu chưa có;
  - không ghi đè `.env` có sẵn, không in mật khẩu nào.
- **Máy chỉ có CPU:** sau `init`, sửa `LLM_TIMEOUT_SECONDS=600` trong `.env`.
- **Mật khẩu để đăng nhập giao diện:** `[Environment]::GetEnvironmentVariable('EAKA_DEMO_STAFF_PASSWORD', 'User')` (thay `STAFF` bằng vai trò cần dùng).
- **Kết quả mong đợi** (đã thử từ bản clone mới của `a4add79` ngày 2026-11-28, 47/47 kiểm tra đạt):
  - `seed` báo `READY` cho cả 13 tài liệu, khoảng 6,5 phút (gồm tải model e5);
  - `warmup` in 3 dòng `ANSWERED citations=1`; câu đầu tiên sau khi dựng mới mất khoảng 130 s, hai câu sau khoảng 16-17 s;
  - `check_demo.py --matrix` kết thúc bằng `N/N checks passed`, và bảng câu hỏi × vai trò khớp bảng ở mục "Kịch bản".
- **`.env` và volume đi cùng nhau:** `demo.ps1` dùng `.env` ở gốc repo nó nằm trong, và volume Postgres giữ mật khẩu của `.env` lúc volume được tạo.
  - Chạy từ một checkout có `.env` khác (ví dụ `.env` của stack phát triển) trên volume cũ thì `migration` dừng với `password authentication failed`, và không ghi gì vào DB.
  - Volume `eaka-demo_*` có sẵn trên máy của owner được tạo bằng `C:\dev\eaka-demo\src\.env`.
  - Với một bản clone mới, `init` rồi `reset` cho ra cặp `.env` và volume khớp nhau.
- **Chạy song song với một stack demo khác trên cùng máy:** đặt `$env:EAKA_DEMO_PROJECT` (mặc định `eaka-demo`) trước mọi lệnh. Hai stack vẫn dùng chung cổng 18480, nên chỉ bật một stack mỗi lúc.

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
  | api | 1536m (1,5 GiB) | đỉnh 1200 MiB, chạm giới hạn cũ 1200m trong lượt test 2026-11-27, nên đã nâng |
  | worker | 1600m | 1,2 GiB sau khi nạp tài liệu |
  | postgres | 384m | |
  | redis | 64m | |
  | frontend | 64m | |

- **Không container nào tự khởi động lại** (`restart: "no"`). Container nào dừng (ví dụ api bị giết vì hết bộ nhớ) thì chạy lại `.\deploy\demo\demo.ps1 up`.

## Bố cục (trong repo, `deploy/demo/`)

| Đường dẫn | Nội dung |
|---|---|
| `deploy/demo/demo.ps1` | `init` / `build` / `up` / `seed` / `warmup` / `questions` / `status` / `down` / `reset`; chạy trên repo chứa nó, từ thư mục nào cũng được |
| `deploy/demo/compose.demo.yaml` | Phủ lên `compose.yaml` + `compose.uat-corpus-v2.yaml`:<br>• image riêng;<br>• `restart: "no"`;<br>• giới hạn bộ nhớ;<br>• chỉ frontend có cổng (`127.0.0.1:18480`);<br>• `RAG_DIAGNOSTICS_ENABLED=false` (mặc định của app) |
| `deploy/demo/seed_demo.py` | Nạp dữ liệu demo (chạy qua `demo.ps1 seed`, trong mạng của container API, repo mount chỉ đọc) |
| `deploy/demo/check_demo.py` | Kiểm qua nginx, gồm cả xử lý Host (TC-SEC-08: Host lạ không được trả lời, redirect chỉ có đường dẫn tương đối) và profile của API; `--matrix` hỏi các câu mẫu bằng cả 4 tài khoản |
| `deploy/demo/check_profile.py` | Chạy trong container API (qua `check_demo.py`): báo cờ `RAG_*` nào khác mặc định của `main`, cùng model và chế độ trả lời |
| `.env` (gốc repo) | Do `demo.ps1 init` tạo từ `.env.example`, secret ngẫu nhiên; không commit (`.gitignore`) |

- **Câu hỏi:** repo công khai chỉ ghi ID. `demo.ps1` và `check_demo.py` đọc nội dung theo ID từ bộ dev trong repo, không có câu held-out nào.
- **Image:**
  - `demo.ps1 build` dựng backend `eaka-backend:demo-<commit>` (`docker build --target runtime`) và frontend `eaka-frontend:demo-<commit>`:

    ```
    docker build -f deploy/frontend/Dockerfile --build-arg VITE_API_BASE_URL= .
    ```

    Image frontend là nginx phục vụ bản build của SPA, kèm reverse proxy `/api/`. SSE không bị buffer hay nén, `proxy_read_timeout` là 300 s, và mọi route của app đều trả về `index.html`.
  - Tag theo commit đang checkout, nên `up` báo thiếu image nếu repo đã đổi commit mà chưa `build` lại.
- **Volume:**
  - `eaka-demo_*` (hoặc `<EAKA_DEMO_PROJECT>_*`); `demo.ps1 down` giữ nguyên volume;
  - **Không bao giờ chạy `docker compose down -v`.**
  - Model e5 được tải về volume `*_model_cache` ở lần `seed` đầu; volume này được giữ qua `reset`.
- **Bản cũ ở `C:\dev\eaka-demo`** (bản export, image `demo-5197874`) chạy cùng các script này. Từ nay dùng bản trong repo.

## Lệnh

Đứng ở thư mục gốc của repo. **Ngay trước buổi demo, chạy `.\deploy\demo\demo.ps1 reset`.**

- Lệnh hỏi xác nhận: phải gõ `reset demo`.
- Sau đó nó chạy `down`, xoá **chỉ** 3 volume dữ liệu `eaka-demo_postgres_data`, `eaka-demo_redis_data`, `eaka-demo_uploads_data`, rồi chạy lại `up` (gồm migrate), `seed` và `warmup`.
- Nhờ vậy không còn lịch sử chat của lần thử trước, và cache trả lời cũng sạch.
- Volume cache model e5 được giữ lại.
- Toàn bộ mất khoảng 5 phút.

```powershell
.\deploy\demo\demo.ps1 reset      # trước buổi demo: xoá dữ liệu demo, dựng lại (hỏi xác nhận)
.\deploy\demo\demo.ps1 up         # bật stack, chờ /health/live qua 18480
.\deploy\demo\demo.ps1 warmup     # nạp LLM + embedding, đo 3 câu dev (chạy trước khi trình bày)
.\deploy\demo\demo.ps1 status
.\deploy\demo\demo.ps1 down       # tắt, giữ volume
.\deploy\demo\demo.ps1 seed       # chỉ khi dựng mới: nạp dữ liệu (idempotent)
.\deploy\demo\demo.ps1 questions  # ID và nội dung các câu mẫu
python deploy\demo\check_demo.py [--matrix]
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

Câu hỏi chỉ lấy từ bộ dev (UAT Q001-Q100 và RBAC dev), không dùng held-out. Nội dung câu in bằng `.\deploy\demo\demo.ps1 questions` (kèm 4 câu dự phòng: Q027, Q061, RBD-02, RBD-09). Kết quả dưới đây đo ngày 2026-11-27.

| Câu | Tài liệu (mức hiển thị) | admin | manager | staff | ops-staff |
|---|---|---|---|---|---|
| Q016 | ND-HR-002 (ORGANIZATION) | trả lời | trả lời | trả lời | trả lời |
| Q043 | ND-HR-004 (ORGANIZATION) | trả lời | trả lời | trả lời | trả lời |
| Q084 | ND-HR-006 (ORGANIZATION) | trả lời | trả lời | trả lời | trả lời |
| RBD-01 | RBAC-MGR-001 (PRIVATE, quyền cho manager) | trả lời | trả lời | từ chối | từ chối |
| RBD-13 | RBAC-REV-001 (DEPARTMENT, UAT-KNOWLEDGE) | trả lời | trả lời | trả lời | từ chối |
| RBD-07 | RBAC-OPS-001 (DEPARTMENT, UAT-OPS) | trả lời | từ chối | từ chối | trả lời |

1. **(1 phút) staff:** đăng nhập, hỏi Q016, rồi mở trích dẫn để xem trang PDF.
   - Q016 đã chạy trong `warmup`, nên trả lời trong 1-2 s nhờ cache.
2. **(1,5 phút) staff:** hỏi Q084, một câu **mới** chưa có trong `warmup`.
   - Mất 15-19 s: đây là thời gian thật, gồm tìm tài liệu, gọi LLM và kiểm câu trả lời.
   - Nói rõ: câu đã hỏi trước đó thì trả nhanh vì có cache trả lời.
   - Nếu còn thời gian, hỏi thêm Q043.
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
| Câu đầu sau `up` hoặc `reset` (model và API còn nguội) | 50-100 s; khoảng 130 s ngay sau khi dựng mới |
| Câu mới khi model đã nạp | 15-21 s |
| Câu đã hỏi (cache trả lời) | 1-3 s |

- Luôn chạy `.\deploy\demo\demo.ps1 warmup` sau `up` và ngay trước khi trình bày.
- Model ở lại trên GPU 30 phút sau câu cuối. Nếu ngồi chờ lâu hơn, chạy `warmup` lại.
- Nếu một câu vượt quá khoảng 60 s, xem `ollama ps`: model phải báo `100% GPU` và `qwen3.5-text:4b`.
