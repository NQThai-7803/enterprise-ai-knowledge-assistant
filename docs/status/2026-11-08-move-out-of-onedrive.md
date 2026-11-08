# Chuyển repo ra khỏi OneDrive sang `C:\dev\eaka` (chuẩn bị, chưa thực hiện)

Lý do: OneDrive giữ 2,1–2,7 GB RAM khi đồng bộ thư mục repo, khiến máy ở dưới cổng 1000 MB (DEC-016). **Không xóa gì trong thư mục OneDrive.** Bản cũ giữ nguyên cho tới khi bản mới chạy được và owner quyết định.

## Những gì chỉ có ở local (không có trong git)

| Đường dẫn | Kích thước | Nội dung | Cần chép? |
|---|---:|---|---|
| `.env` | nhỏ | Cấu hình local, có `SECRET_KEY`, mật khẩu DB và tài khoản dev | **Có** |
| `.env.task035.production` | nhỏ | Cấu hình bản dựng production của TASK-035 | **Có** |
| `frontend/.env.local` | nhỏ | `VITE_API_BASE_URL` | **Có** |
| `artifacts/` | 614 MB | Mọi lượt đo, baseline v2, file chấm tay, manifest, backup corpus | **Có** |
| `.backups/` | 2,9 MB | Dump PostgreSQL và tar uploads (task035, task035-dev, uat-corpus-v2) | **Có** |
| `data/` | 471 MB | `models/` (cache embedding) và `uploads/` của lần chạy không qua Docker | **Có** (hoặc tải lại model) |
| `.ci-data/` | 471 MB | Cache model cho test | Không bắt buộc (tải lại được) |
| `.verify/` | 4,5 MB | JUnit XML của các lượt eaka-verify | Có (để so sánh lần sau) |
| `graphify-out/cache/` | trong 16 MB | Cache của graphify | Không bắt buộc |
| `vite-monorepo/` | lớn (có `node_modules`) | Thư mục thử nghiệm frontend, bị ignore hoàn toàn | Có, trừ `node_modules` |
| `.git/` | 22 MB | **Có nhánh chưa push:** `master`, `feat/react-bits-ai-motion` | **Có**: chép nguyên `.git` |
| `.venv/`, `.venv312/`, `node_modules/`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `frontend/dist/`, `*.tsbuildinfo` | lớn | Sinh lại được | **Không**: tạo lại |

**Nằm ngoài repo, không bị ảnh hưởng:**
- **Volume Docker** (`enterprise-ai-knowledge-assistant_*`, `enterprise-ai-uat-v2_*`, `eaka-p3d-uat_*`, `eaka-rbac-dev_*`, `eaka-relevance-dev_*`, AUTH-02, ...): nằm trong máy ảo của Docker Desktop. Volume `enterprise-ai-knowledge-assistant_*` vẫn khớp sau khi chuyển vì `compose.yaml` cố định `name: enterprise-ai-knowledge-assistant`. Các stack eval luôn dùng `-p` với tên cố định nên cũng khớp. Compose không có bind mount nào trỏ vào thư mục repo, trừ `deploy/` của `compose.prod.yaml`, và thư mục đó có trong git.
- **Ollama:** model nằm trong `%USERPROFILE%\.ollama`, cấu hình nằm trong `%LOCALAPPDATA%\Ollama`.
- **Memory của Claude Code** gắn theo đường dẫn: `%USERPROFILE%\.claude\projects\c--Users--ASUS--OneDrive-M-y-t-nh-Documents-Python-LTPYTHON-Enterprise-AI-Knowledge-Assistant\`. Ở đường dẫn mới, Claude Code tạo một thư mục project khác, nên cần chép memory sang (bước 4). Còn `skill-observations` nằm ở `%USERPROFILE%\.claude\skill-observations`, dùng chung, không cần làm gì.

## Lệnh chép (PowerShell)

Trước khi chép: trong OneDrive, chọn "Always keep on this device" cho thư mục repo. Nếu không, file chỉ có trên đám mây (placeholder) sẽ được tải về giữa chừng, hoặc bị chép thành file lỗi.

```powershell
$src = "C:\Users\_ASUS_\OneDrive\Máy tính\Documents\Python\LTPYTHON\Enterprise AI Knowledge Assistant"
$dst = "C:\dev\eaka"

# 1. Chép mọi thứ, kể cả .git, .env, artifacts/ và các file bị ignore; bỏ những gì tạo lại được.
#    /E: cả thư mục con; /COPY:DAT: dữ liệu, thuộc tính, thời gian; không có /MIR nên không xóa gì ở đâu.
robocopy $src $dst /E /COPY:DAT /DCOPY:DAT /R:1 /W:1 /NP /NFL /NDL `
  /XD .venv .venv312 node_modules __pycache__ .pytest_cache .ruff_cache dist test-results `
  /XF *.pyc *.tsbuildinfo /LOG:C:\dev\eaka-copy.log
# Mã thoát 0-7 là thành công; từ 8 trở lên là có lỗi (xem C:\dev\eaka-copy.log).

# 2. Kiểm tra bản mới
git -C $dst status --short --branch
git -C $dst branch -vv
git -C $dst stash list
git -C $dst fsck --no-dangling
(Get-ChildItem "$src\artifacts" -Recurse -File | Measure-Object Length -Sum).Sum
(Get-ChildItem "$dst\artifacts" -Recurse -File | Measure-Object Length -Sum).Sum   # phải bằng nhau
Get-FileHash "$src\.env","$dst\.env" | Format-Table Hash, Path

# 3. Tạo lại môi trường trong bản mới
cd $dst
uv venv .venv312 --python 3.12
uv pip install --python .venv312 -e ".[dev]"
cd frontend; npm ci; cd ..
cd vite-monorepo; npm ci; cd ..        # chỉ khi còn dùng

# 4. Memory của Claude Code: chép sang thư mục project mới (tên thư mục mới chỉ có sau lần
#    đầu mở Claude Code trong C:\dev\eaka; kiểm tra tên bằng: Get-ChildItem $HOME\.claude\projects)
$old = "$HOME\.claude\projects\c--Users--ASUS--OneDrive-M-y-t-nh-Documents-Python-LTPYTHON-Enterprise-AI-Knowledge-Assistant\memory"
$new = "$HOME\.claude\projects\C--dev-eaka\memory"
robocopy $old $new /E /COPY:DAT /R:1 /W:1 /NP
```

## Sau khi chép

- **Chạy thử:** `python -m pytest tests\unit -q` trong `C:\dev\eaka`, rồi `docker compose ps` để thấy các stack cũ vẫn nhận volume của chúng.
- **Không còn mở repo từ thư mục OneDrive.** Nếu không, hai bản sẽ trôi lệch nhau. Có thể tạm dừng đồng bộ OneDrive cho thư mục cũ.
- **Thư mục OneDrive giữ nguyên** cho tới khi owner quyết định; trong đó có `.git` với hai nhánh chưa push.
- **Kết thúc DEC-016** khi `C:\dev\eaka` chạy eaka-verify và các lượt đo local được trở lại, rồi ghi một DEC mới.
