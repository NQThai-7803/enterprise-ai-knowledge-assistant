# HANDOFF — Enterprise AI Knowledge Assistant (EAKA)

**Checkpoint:** 2026-10-30, dừng tại **R27**. **PAUSED**: không bắt đầu R28 hay task phát triển nào khi chưa có phê duyệt mới. `AUTH-02I.1` vẫn **BLOCKED**.

Repo có **2 phạm vi** khác nhau, đừng lẫn số liệu giữa hai phạm vi:
- **(A) Repo EAKA** — thư mục này, nhánh `wip/codex-handoff`. Gồm backend, frontend và RAG.
- **(B) Workspace AUTH-02 candidate (R13–R27)** — nằm **ngoài repo**, tại `%LOCALAPPDATA%\Temp\eaka-auth02\20261023t080222z-2608a685\auth02-local-transport-work`. Workspace này **không có trong commit**: tìm trong repo không thấy `AUTH02`/`eaka-auth02` (chỉ có ID yêu cầu AUTH-02 trong `FUNCTIONAL_REQUIREMENTS.md`). Thư mục Temp có thể bị Windows dọn bất cứ lúc nào, nên **cần sao lưu riêng trước khi làm tiếp**. Trạng thái hiện tại của workspace này: NOT_VERIFIED.

## 1. Công việc dở và bước tiếp theo
**(B) AUTH-02**
- **R27 xong:** baseline offline `AUTH02-LOCAL-R25-BOOTSTRAP-METADATA-CORRECTED-OFFLINE-V1`; admission/post-check PASS. Admission record SHA256 `dd3f8dfc96770b1fbbaec2a9d737ec78c1634b58c2f8ab7a04383df29cac644f`.
- **R28 (Windows native identity collector): chưa bắt đầu.**
- **Blocker:** trusted bootstrap/approved SID; dedicated DPAPI provider (R22 báo `PathNotFound`); asyncpg tương thích với candidate; PostgreSQL auth method; chính sách transport/TLS. Ngân sách TCP probe đã dùng **1/1**.

**(A) Repo EAKA**
- TASK-035 (Release Candidate) ở trạng thái **NO-GO**:
  - **S01:** Staff hỏi về tài liệu không có quyền thì nhận câu trả lời không liên quan nhưng có citation, thay vì NO_ANSWER. Nguyên nhân gốc chưa xác định.
  - **R05:** image API và worker build lệch source/package; backend chưa có lock file.
- Thứ tự đề xuất (chi tiết trong Project doc `claude/bao-cao-kiem-thu-2026-10-28.md`):
  1. Sửa fixture test.
  2. Đánh dấu `xfail(strict)` cho các contract S01.
  3. Xây bộ đánh giá held-out, xong rồi mới sửa logic xếp hạng và ngữ cảnh.

## 2. Test FAIL hiện tại và nguyên nhân
**(B):** báo cáo R26 ghi independent 100 PASS, replay R24 43 PASS, combined 768 PASS, 3 historical deselected. R27 ghi `REGRESSION_NOT_RERUN`. **Lỗi lịch sử đã sửa, không phải lỗi hiện hành:** 10 failures ở R24 (reserved Windows path alias, SID uint32 overflow, type-insensitive mutation), đã sửa ở R25, R26 kiểm lại không còn tái hiện.

**(A):** chạy ngày 28/10 trên **bản sao Linux**, Python 3.12, deps mới nhất, PostgreSQL 16 + pgvector 0.6.2, nên **khác máy Windows**:
- **Unit/API: 1.690 PASS / 16 FAIL.**
  - 14 FAIL là contract **S01 cố ý để đỏ** — đây là blocker runtime thật: `tests/unit/test_multilingual_answer_responsiveness_contract.py` (8) và `test_task0353e_context_admission_contract.py` (6).
  - 2 FAIL do môi trường: font `C:/Windows/Fonts/arial.ttf`, và test cần `.env` riêng (`test_default_compose_keeps_llm_local_safe`).
- **Integration + API có DB: 606 PASS / 40 FAIL.** Đây là lỗi fixture, không phải lỗi logic:
  - 25 test FAIL vì `RERANKER_CANDIDATE_K` > `HYBRID_RETRIEVAL_MAX_TOP_K` trong `make_settings` của test. Khi đặt `RERANKER_CANDIDATE_K=10`, 25/28 PASS.
  - 10 test chat/SSE nhận NO_ANSWER do fixture không vượt qua lớp kiểm chứng mới.
  - 1 test hard-code migration head `0010` (thực tế là `0011`).
  - 4 test conversation memory, trong đó "Are there exceptions?" bị mất chủ đề — **có thể là hồi quy thật**.
- tiktoken tải `cl100k_base` từ Internet khi chạy, nên máy không có mạng sẽ fail chunking.

## 3. Lệnh (chỉ ghi những lệnh có evidence)
- **Đã chạy trên bản sao Linux ngày 28/10** (Windows: NOT_VERIFIED):
  - Backend: `python -m pytest -q` với `TIKTOKEN_CACHE_DIR` đã có file `cl100k_base`.
  - Integration: `DATABASE_URL=postgresql+asyncpg://...` cộng với marker string trong `.github/workflows/ci.yml`.
  - Frontend: `npm ci`, `npm run lint`, `npm run typecheck`, `npx vitest run`, `npx vite build`, `CI=1 npx playwright test`.
- **Khởi động backend/worker (`docker compose up`, uvicorn): NOT_VERIFIED.** Frontend dev server: NOT_VERIFIED.
- Lệnh (B): NOT_VERIFIED. Thiếu exact command, interpreter và working directory.

## 4. Biến môi trường (chỉ tên, không giá trị)
Danh sách đầy đủ nằm trong `.env.example`, `.env.production.example`, `frontend/.env.example`. Các nhóm chính:
- **Bảo mật:** `SECRET_KEY` (prod ≥ 32 ký tự, hoặc dùng `SECRET_KEY_FILE`).
- **Hạ tầng:** `DATABASE_URL`, `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`.
- **Model:** `EMBEDDING_MODEL_CACHE_PATH`, `RERANKER_*`.
- **LLM:** `LLM_ENABLED`, `LLM_PROVIDER`, `LLM_MODEL`, `LLM_OLLAMA_BASE_URL`, `LLM_OLLAMA_MODEL`.
- **UAT:** `UAT_SEED_ENABLED`, `UAT_*_PASSWORD`.
- **Frontend:** `VITE_API_BASE_URL`.

(B) dùng **dedicated Windows CurrentUser DPAPI** (chưa provision). Không truyền password qua `DATABASE_URL`, argv, env, `PGPASSWORD`, `.pgpass`, log hay Git.

## 5. Quyết định đã chốt và vùng không được đụng
- Giữ nguyên các thành phần sau:
  - EAKA gốc và UAT-v2 (`uat/corpus-v2`).
  - PostgreSQL AUTH-02 named volume, network, identity pins, containment guard (`tests/containment*`).
  - Models, migrations, protected/immutable sources.
- R13, R18, R25 là **approved OFFLINE baselines**, không phải trusted runtime token. Không sửa manifest, admission hay evidence lịch sử. Không hạ assertion để tạo PASS.
- Không làm các việc sau khi chưa có phê duyệt riêng: Docker start/stop, TCP/SQL, DPAPI unprotect, credential provisioning, thay đổi TLS, migration/seed/restore. **Không `docker compose down -v`.**
- Không viết logic riêng cho từng câu hỏi UAT. Retrieval phải lọc quyền trước LLM. Mọi thay đổi schema đều phải có migration.

## 6. Test phụ thuộc `artifacts/` (thư mục bị `.gitignore`)
Quét bằng `rg -n 'artifacts' tests`, sau đó kiểm tra import `scripts.release.*`:
- `artifacts/task-035-3c2e-20261014/synthetic-manifest.json` ← `tests/unit/test_task0353c2e_eval_harness.py` và `tests/unit/test_task0353c2f_eval_harness.py` (qua `scripts/release/task0353c2e_eval.py`, `MANIFEST`).
- `artifacts/task-035-3c2f-20261014/synthetic-manifest.json` ← `tests/unit/test_task0353c2f_eval_harness.py` (qua `scripts/release/task0353c2f_eval.py`, `MANIFEST`).
- **Không phải dependency của pytest:** các file `tests/acceptance/rag_h5_2_exact_100.py`, `rag_h5_2_model_ab.py`, `task_034_1_2_runtime_acceptance.py` không có tiền tố `test_` nên pytest không thu thập. Chúng chỉ trỏ tới `artifacts/rag-h5-1-stress-uat.py`, `artifacts/rag-h5-2-exact-100/`, `artifacts/rag-h5-2-model-ab.json`, `artifacts/task-034-1-2/`. `results.json` của 3c2f là output, không được test đọc.

## 7. Git checkpoint
- Nhánh `wip/codex-handoff`. Commit gồm: đổi `.gitignore` từ `data/` thành `/data/` (để theo dõi được `frontend/src/components/data/DataTable.tsx`), thêm `HANDOFF.md`, và toàn bộ thay đổi trước đó chưa commit.
- Commit với `core.autocrlf=input`: index giữ LF, working tree không đổi.
- Commit có kèm file nháp `tmp_*_trace.py` và `.cache/huggingface/.agent_harnesses.json` (không chứa secret). Nên dọn ở một commit sau.
