# HANDOFF: Enterprise AI Knowledge Assistant (EAKA)

Cập nhật 2026-11-08 (trước đó 2026-11-05, nhánh `handover/2026-11-05`). Thiết kế và quy tắc nằm trong `CLAUDE.md`; lịch sử việc nằm trong `TASKS.md` và `PROJECT_STATUS.md`. Bản HANDOFF cũ (có phần workspace AUTH-02 nằm ngoài repo): `git show 09e15cf:HANDOFF.md`.

## Clone và chạy

```powershell
git clone https://github.com/NQThai-7803/enterprise-ai-knowledge-assistant.git
cd enterprise-ai-knowledge-assistant
git switch handover/2026-11-05
Copy-Item .env.example .env      # sửa SECRET_KEY và các giá trị local, xem SETUP.md mục 5
docker compose up -d             # postgres, redis, migrate, api, worker; Swagger ở :8000/docs
docker compose --profile frontend up -d frontend
```

- Thêm LLM giả và tài khoản seed: `docker compose -f compose.yaml -f compose.uat.yaml up -d`.
- **Không có trong git, phải xin chủ dự án:** `artifacts/` (baseline v2, các lượt đo cũ, file chấm tay UAT), `data/models`. Câu hỏi Q001-Q100 và 9 PDF corpus V2 (dữ liệu giả lập) nay nằm trong `eval-data/`.

## Trạng thái (cập nhật 2026-11-08)

- **Mặc định RAG hiện tại:** `strict`, nhóm 1 + 2 (DEC-011) và REL-402 bật. REL-303, REL-103 và 4a tắt. Mỗi flag giữ được để rollback (`ENVIRONMENT_VARIABLES.md`).
- **Quy tắc đo:** baseline và phương án mới chạy cùng một đợt (DEC-011), chọn theo từng bộ (DEC-013). Các bộ dev: Q001-Q100, RBAC dev, `answer_relevance_dev_v1`, và `false_refusal_dev_v1` (owner đã duyệt 2026-11-08; chấm bằng `run_answer_relevance_dev.py --set false_refusal_dev_v1`, cần stack riêng).
- **Ollama là một phần của lượt đo (DEC-014):** runner từ chối chạy nếu Ollama khác 0.40.15 hoặc khác backend CUDA; tự cập nhật của app Ollama đã tắt. Trên Actions đặt `EVAL_OLLAMA_EXPECTED_BACKEND=CPU`.
- **Held-out v1 là diagnostic** (DEC-008). Lượt mới nhất (2026-11-08, mặc định mới cộng REL-303): 0 rò rỉ, trả lời sai 3/14, từ chối sai 14/26, PASS 14/40. Owner chấp nhận 10 nhãn đổi ở mức diagnostic (`docs/eval/runs/heldout-v1-defaults-bb60566/score.md`).
- **Held-out v2 đợt 1:** 20 câu đã đóng băng; gold chờ owner duyệt; hệ thống chưa chạy trên bộ này (DEC-012).
- **Kết quả lệch giữa các đợt là do backend GPU của Ollama** (Vulkan trước 2026-11-06 18:26, CUDA sau đó) và phiên bản Ollama, không phải do khởi động lại (`docs/eval/runs/nondeterminism.md`).
- **Reranker:** vẫn là `lexical_fallback`.
- **Eval trên GitHub Actions:** `eval.yml` (chỉ chạy tay) chạy được `relevance`, `rbac` và `uat` (có thể chọn câu). Chạy trên CPU, nên không so trực tiếp với lượt local.
- **Fine-tune embedding:** mới có hạ tầng, trên nhánh `feat/embedding-finetune-infra` chưa merge (`ml/embedding_finetune/`, `docs/design/embedding-finetune.md`, DEC-015); chưa train, model của app không đổi.

## Test (2026-11-08, image build từ git export, pgvector/Redis tạm)

| Lane | Pass | Fail | Xfail | Skip |
|---|---:|---:|---:|---:|
| `tests/unit`, không mount `docs/` | 1659 | 0 | 17 | 7 |
| `tests/api` không integration | 51 | 0 | 0 | 0 |
| `tests/api` integration | 245 | 0 | 0 | 0 |
| `tests/integration` | 404 | 0 | 3 | 0 |
| LLM provider | 3 | 0 | 0 | 0 |
| Celery | 4 | 0 | 0 | 0 |

Kết quả trên tính cả PR #9 (test lock held-out được skip trong image). Các lane cần model thật chỉ chạy trên CI.

## Việc đang dở

Xem `docs/status/2026-11-08-session-report.md` (mới nhất) và `docs/status/2026-11-08-unattended-report.md`: các nhánh/PR đang chờ và các quyết định cần owner, sắp theo mức ưu tiên.

## Lưu ý bắt buộc

- **Không commit `.env`, `.env.*` (trừ file mẫu) hay `.backups/`.** Repo đang public; kiểm tra `git status` trước khi add.
- **Không cho skill hay công cụ nào đọc hoặc quét `docs/eval/`**, vì đó là gold của held-out. Công cụ quét cả repo phải loại thư mục này.
- **Không chạy `docker compose down -v`**, vì lệnh này xoá volume corpus.
- Không viết logic riêng cho từng câu hỏi test. Không lấy hoặc cite tài liệu ngoài quyền của người dùng.
- Sửa `app/retrieval`, `app/chat`, `app/citations`, validator hoặc phân quyền: dùng `.claude/skills/eaka-rag-change-guard`. Trước khi báo xong: dùng `.claude/skills/eaka-verify`.
