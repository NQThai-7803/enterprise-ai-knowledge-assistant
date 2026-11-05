# HANDOFF: Enterprise AI Knowledge Assistant (EAKA)

Cập nhật 2026-11-05, nhánh `handover/2026-11-05`. Thiết kế và quy tắc nằm trong `CLAUDE.md`; lịch sử việc nằm trong `TASKS.md` và `PROJECT_STATUS.md`. Bản HANDOFF cũ (có phần workspace AUTH-02 nằm ngoài repo): `git show 09e15cf:HANDOFF.md`.

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
- **Không có trong git, phải xin chủ dự án:** `artifacts/` (câu hỏi Q001-Q100, baseline v2, manifest), `data/models`. Thiếu `artifacts/` thì không đo được split dev và 5 unit test bị skip.

## Trạng thái

- **Sửa lõi RAG vẫn tạm dừng cho tới khi xong PROMPT 4b và 4.5c.** Thứ tự: đo trước, sửa logic lõi sau, đặt sau feature flag (`docs/review/claude-code-prompts.md`, PROMPT 5-7).
- **Dev** = Q001-Q100, baseline v2 đạt 99/100 theo proxy; Q096 lệch giữa các lượt là nhiễu đã biết.
- **Held-out v1 đã chấm** (2026-11-05, Claude chấm theo ủy quyền của chủ dự án; [`score.md`](docs/eval/runs/heldout-v1-f3cdbf3/score.md)): `answer_accuracy` 27,5% (11/40). Trong 11 PASS có 9 câu là từ chối đúng: `answerable_accuracy` 7,7% (2/26), `refusal_accuracy` 64,3% (9/14). Từ chối sai 14/26, trả lời sai 5/14, 0 rò rỉ ở mức kiểm tra sơ.
- **Held-out v1 giờ là bộ diagnostic** (DEC-008), không còn là tập test. Con số công bố ra ngoài phải đo trên held-out v2, chưa có.
- **Reranker:** hệ thống đang xếp hạng bằng `lexical_fallback`. Cross-encoder chưa từng chạy trong các lần đo đã xác minh (đã kiểm 2 volume: `eaka-p3d-uat`, `enterprise-ai-uat-v2`). Xem chế độ hiện tại ở `GET /health/ready`.
- TASK-035 (release candidate) vẫn NO-GO vì lỗi S01 chưa đóng.

## Test (2026-11-05, image build từ `requirements.lock`, pgvector/Redis tạm)

| Lane | Pass | Fail | Xfail | Skip |
|---|---:|---:|---:|---:|
| `tests/unit` | 1496 | 1 | 17 | 5 |
| `tests/api` không integration | 51 | 0 | 0 | 0 |
| `tests/api` integration | 245 | 0 | 0 | 0 |
| `tests/integration` | 404 | 0 | 3 | 0 |
| Celery | 4 | 0 | 0 | 0 |

- **Fail:** `test_heldout_runner.py::test_repository_lock_matches_the_frozen_file`. Image không có `docs/eval/`; không phải lỗi logic. Test pass khi chạy trên host (venv).
- **Xfail, đều là lỗi thật còn mở:**
  - 14 ca S01 trong `test_multilingual_answer_responsiveness_contract.py` (8) và `test_task0353e_context_admission_contract.py` (6): câu trả lời không liên quan nhưng vẫn có citation.
  - 3 ca `test_answer_responsiveness_diagnostic.py`: bằng chứng trích nguyên văn chưa chứng minh là trả lời đúng câu hỏi; validator có thể loại mệnh đề điều kiện tiếng Việt.
  - 2 ca `test_semantic_retrieval_hnsw_recall.py`: bộ lọc quyền chạy sau khi HNSW đã lấy kết quả, làm giảm recall.
  - 1 ca `test_conversation_memory.py`: câu nối tiếp bị mất chủ đề.
- **Skip:** 5 ca thiếu manifest trong `artifacts/`.
- **Chưa chạy:** các lane cần model thật (embedding, processing, semantic, hybrid), LLM thật, frontend.

## Việc đang dở

**PROMPT 4b và 4.5 đã xong** (`docs/eval/runs/heldout-v1-f3cdbf3/diagnosis.md`, `docs/eval/runs/rbac-dev-v1/score.md`). **Bước tiếp theo:** chờ chủ dự án quyết định PROMPT 5 và thứ tự sửa route deterministic, alignment filter, validator. PROMPT 6 lùi lại sau các sửa đó (DEC-009).

Báo cáo kiểm thử 28/10: [`docs/review/bao-cao-kiem-thu-2026-10-28.md`](docs/review/bao-cao-kiem-thu-2026-10-28.md).

## Lưu ý bắt buộc

- **Không commit `.env`, `.env.*` (trừ file mẫu) hay `.backups/`.** Repo đang public; kiểm tra `git status` trước khi add.
- **Không cho skill hay công cụ nào đọc hoặc quét `docs/eval/`**, vì đó là gold của held-out. Công cụ quét cả repo phải loại thư mục này.
- **Không chạy `docker compose down -v`**, vì lệnh này xoá volume corpus.
- Không viết logic riêng cho từng câu hỏi test. Không lấy hoặc cite tài liệu ngoài quyền của người dùng.
- Sửa `app/retrieval`, `app/chat`, `app/citations`, validator hoặc phân quyền: dùng `.claude/skills/eaka-rag-change-guard`. Trước khi báo xong: dùng `.claude/skills/eaka-verify`.
