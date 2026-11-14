# HANDOFF: Enterprise AI Knowledge Assistant (EAKA)

Cập nhật 2026-11-15, đóng giai đoạn 1 (trước đó 2026-11-08; bản cũ: `git show 09e15cf:HANDOFF.md`). Thiết kế và quy tắc nằm trong `CLAUDE.md`; lịch sử việc nằm trong `TASKS.md` và `PROJECT_STATUS.md`; tóm tắt giai đoạn 1 ở `docs/design/pipeline-loss-fix-plan.md` mục 7.

## Clone và chạy

```powershell
git clone https://github.com/NQThai-7803/enterprise-ai-knowledge-assistant.git
cd enterprise-ai-knowledge-assistant
Copy-Item .env.example .env      # sửa SECRET_KEY và các giá trị local, xem SETUP.md mục 5
docker compose up -d             # postgres, redis, migrate, api, worker; Swagger ở :8000/docs
docker compose --profile frontend up -d frontend
```

- Thêm LLM giả và tài khoản seed: `docker compose -f compose.yaml -f compose.uat.yaml up -d`.
- **Không có trong git, phải xin chủ dự án:** `artifacts/` (baseline v2, các lượt đo cũ, file chấm tay UAT), `data/models`. Câu hỏi Q001-Q100 và 9 PDF corpus V2 (dữ liệu giả lập) nay nằm trong `eval-data/`.

## Trạng thái (cập nhật 2026-11-15)

- **Giai đoạn 1 đã đóng.** Danh sách flag đang bật/tắt, kết quả từng bước và rủi ro khớp quá mức: `docs/design/pipeline-loss-fix-plan.md` mục 7. Mọi flag giữ được để rollback (`ENVIRONMENT_VARIABLES.md`).
- **Mới bật trong giai đoạn này:** vòng thử lại giữ giá trị đã xác thực (c3), số có nhóm hàng nghìn (c1), dấu tiếng Việt và bỏ câu lặp (D2, DEC-023), dự phòng đoạn trích (iii), kiểm độ đáp ứng trên câu LLM với t = 0,80 và điểm dừng (ii + a). Trả lời một phần câu hỏi ghép (iv) giữ tắt.
- **Model:** qwen2.5:3b, xét lại khi có GPU ≥ 8 GB VRAM (ADR 0003, DEC-024). **Reranker:** chạy `lexical_fallback`; cross-encoder không đổi câu nào vì thứ tự xếp hạng; hai phương án ở ADR 0004 (đề xuất, chưa code).
- **Báo cáo UAT tách route:** 75-76 câu đi câu trả lời dựng sẵn, 24-25 câu đi LLM; tổng UAT chủ yếu phản ánh route deterministic (`by_route` trong `scripts/eval/metrics.py`).
- **Bộ dev (6):** Q001-Q100, RBAC dev, `answer_relevance_dev_v1`, `false_refusal_dev_v1`, `false_refusal_dev_v2`, `compound_partial_dev_v1` (owner chấp nhận 2026-11-14). Chạy bằng `eval.yml` (`set=uat|rbac|relevance|false_refusal|false_refusal_v2|compound`).
- **Quy tắc đo:** baseline và phương án cùng job, 2 lượt (DEC-011); chọn theo DEC-013, "nhầm giá trị" tính là trả lời sai; quy tắc chọn ghi trước khi đo. Đo trên Actions (CPU, Ollama 0.40.15, DEC-014).
- **Verify:** eaka-verify local trước mỗi lần push (DEC-018); khi cổng RAM 1000 MB đóng quá 15 phút thì CI thay (DEC-019).
- **Held-out:** v1 là diagnostic (DEC-008). v2 chưa chạy theo quy trình (DEC-012); owner đã chạy tay một lần ngoài quy trình (DEC-022), bản ghi không có trong repo và không dùng để thiết kế; mọi báo cáo held-out v2 phải nêu sự kiện này.
- **Fine-tune embedding:** hạ tầng ở PR #14 (mở); không fine-tune trước held-out v2 (DEC-021).

## Test (2026-11-09, `315efd6`, image build từ git export, pgvector/Redis tạm, chạy local)

| Lane | Pass | Fail | Xfail | Skip |
|---|---:|---:|---:|---:|
| `tests/unit`, mount `docs/` chỉ đọc | 1698 | 0 | 16 | 8 |
| `tests/api` không integration | 51 | 0 | 0 | 0 |
| `tests/api` integration | 245 | 0 | 0 | 0 |
| `tests/integration` | 404 | 0 | 3 | 0 |
| LLM provider | 3 | 0 | 0 | 0 |

Lane Celery (4 pass ngày 2026-11-08) không chạy trong lượt này; các lane cần model thật chỉ chạy trên CI.

## Việc đang dở

- **Owner chọn phương án reranker** (ADR 0004: (a) sửa thứ tự + mMiniLMv2, hay (b) gỡ reranker; đề xuất (b)).
- **(iv) trả lời một phần** cần một kiểm tra mỗi ý chặt hơn cosine e5 (CP1-R03: "chung" và "ở nước ngoài" có cosine ≥ 0,82).
- **Câu hỏi tiếng Anh** (FR2-E01, E03) bị kiểm độ đáp ứng chặn; ngưỡng t chưa được hiệu chỉnh cho tiếng Anh.
- **Held-out v2** một lần ở mốc release, có người duyệt (DEC-012).
- PR #14 (fine-tune embedding) vẫn mở.

## Lưu ý bắt buộc

- **Không commit `.env`, `.env.*` (trừ file mẫu) hay `.backups/`.** Repo đang public; kiểm tra `git status` trước khi add.
- **Không cho skill hay công cụ nào đọc hoặc quét `docs/eval/`**, vì đó là gold của held-out. Công cụ quét cả repo phải loại thư mục này.
- **Không chạy `docker compose down -v`**, vì lệnh này xoá volume corpus.
- Không viết logic riêng cho từng câu hỏi test. Không lấy hoặc cite tài liệu ngoài quyền của người dùng.
- Sửa `app/retrieval`, `app/chat`, `app/citations`, validator hoặc phân quyền: dùng `.claude/skills/eaka-rag-change-guard`. Trước khi báo xong: dùng `.claude/skills/eaka-verify`.
