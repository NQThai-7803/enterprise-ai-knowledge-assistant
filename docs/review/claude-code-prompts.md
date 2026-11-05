# Bộ prompt cho Claude Code — tiếp tục phát triển EAKA

Cách dùng: mỗi lần chỉ dán **một** prompt vào Claude Code trong VS Code, theo đúng thứ tự. Hoặc gõ ngắn: `Thực hiện PROMPT <n> trong docs/review/claude-code-prompts.md`. Xong một prompt thì đọc báo cáo, bạn duyệt, rồi mới chuyển sang prompt tiếp theo.

Nguồn: `HANDOFF.md`, `docs/review/bao-cao-kiem-thu-2026-10-28.md`, `docs/release/TASK-035.3*` (kế hoạch Codex để lại) và `CLAUDE.md`.

Quy tắc chung (đã ghi sẵn trong từng prompt):
- Báo cáo bằng tiếng Việt, kèm thuật ngữ tiếng Anh.
- Mỗi kết luận phải có evidence (lệnh đã chạy và kết quả). Chưa chạy được thì ghi `NOT_VERIFIED`.
- Không đụng EAKA gốc, UAT-v2 (`uat/corpus-v2`), volume Docker, migration cũ hay evidence lịch sử.

---

## PROMPT 0 — Tiếp nhận dự án (chỉ đọc, không sửa)

```text
Bạn tiếp nhận dự án EAKA từ Codex. Task này CHỈ ĐỌC: không sửa file, không chạy Docker, không chạy test.

1. Đọc theo thứ tự: CLAUDE.md, HANDOFF.md, docs/review/bao-cao-kiem-thu-2026-10-28.md, phần đầu (mục mới nhất) của PROJECT_STATUS.md và TASKS.md, docs/release/TASK-035.3F-prioritized-remaining-rc-plan-20261014.md, docs/release/TASK-035.3D-rc-blocker-remediation-register-20261014.md.
2. Chạy `git status`, `git branch -vv`, `git log -3 --oneline`. Xác nhận đang ở nhánh wip/codex-handoff, commit c908a05. Kiểm tra nhánh đã push lên origin chưa. Nếu git status hiện hàng loạt file M, kiểm tra `git config core.autocrlf` và `git diff --ignore-cr-at-eol --stat` để phân biệt khác biệt xuống dòng (CRLF) với thay đổi thật. Không commit gì.
3. Kiểm tra workspace AUTH-02 tại %LOCALAPPDATA%\Temp\eaka-auth02\ còn tồn tại không: liệt kê thư mục cấp 1–2 và tổng dung lượng. Không mở và không in nội dung file có thể chứa credential.
4. Tự kiểm lại 5 phát hiện quan trọng trong bản báo cáo bằng cách đọc code, ghi rõ ĐÚNG / SAI / ĐÃ THAY ĐỔI kèm file:dòng:
   (a) group_hits[:2] trong app/services/grounded_answer_service.py
   (b) cue "nam " trong app/retrieval/authority.py
   (c) câu bị cắt trong _no_answer_retry_messages
   (d) _rank_hits_for_prompt xếp theo alignment_score trước, reranker sau
   (e) mapper.py dùng page_number=source.start_page
5. Báo cáo ngắn: trạng thái Git, tình trạng workspace AUTH-02, kết quả bước 4, và những điểm HANDOFF.md ghi sai so với code thực tế.
Không đề xuất code mới trong task này.
```

## PROMPT 1 — Sao lưu workspace AUTH-02 (chống mất dữ liệu)

```text
Chỉ thực hiện sao lưu. Không chạy R28, không chạy Docker, không giải mã DPAPI, không đọc hay in nội dung credential.

1. Sao chép nguyên trạng %LOCALAPPDATA%\Temp\eaka-auth02\ sang %USERPROFILE%\eaka-backups\auth02-<yyyymmdd-HHmm>\ (đặt NGOÀI OneDrive và NGOÀI repo). Dùng robocopy /E /COPY:DAT /R:1 /W:1 và lưu log.
2. Tạo manifest SHA256 cho toàn bộ file đã sao chép (Get-FileHash), so khớp số file và hash giữa nguồn và đích.
3. Không đưa bản sao vào Git. Không xóa hay dọn thư mục Temp gốc.
4. Báo cáo: đường dẫn bản sao, số file, tổng dung lượng, số hash khớp/lệch, đường dẫn log robocopy.
Nếu workspace không tồn tại hoặc bị khóa, dừng và báo BLOCKED kèm thông báo lỗi nguyên văn.
```

## PROMPT 2 — Sửa lưới an toàn kiểm thử (KHÔNG đụng code ứng dụng)

```text
Mục tiêu: test phản ánh đúng hành vi hiện tại, để mọi thay đổi sau này đều được kiểm. CHỈ sửa file trong tests/. Không sửa app/, scripts/, uat/, artifacts/ hay migrations.

Làm từng mục, chạy lại đúng các test liên quan sau mỗi mục:
1. tests/integration/test_hybrid_retrieval.py và tests/integration/test_grounded_answer_persistence.py: hàm make_settings tạo Settings không hợp lệ (RERANKER_CANDIDATE_K=50 > HYBRID_RETRIEVAL_MAX_TOP_K=10). Truyền reranker_candidate_k và reranker_top_k nhất quán với max_top_k của test. Không hạ assertion phân quyền.
2. tests/api/test_chat_messages.py (5 test), tests/api/test_chat_streaming.py (4 test), tests/integration/test_grounded_answer_citations.py::test_invalid_citation_persists_no_messages_or_citations: fixture "allowed context"/"Grounded answer" hiện bị lớp claim validation trả NO_ANSWER. Viết lại fixture để ngữ cảnh và câu trả lời khớp nhau thật sự (ví dụ chunk "Nhân viên được nghỉ 12 ngày phép năm." và answer "Nhân viên được nghỉ 12 ngày phép năm [SOURCE_1]."), sao cho test ANSWERED thật sự đi qua nhánh ANSWERED và test citation-sai thật sự chạm tới nhánh validate citation. Không mock bỏ qua validator.
3. tests/api/test_admin_monitoring.py: bỏ hard-code migration head 20260803_0010, đọc head động từ Alembic ScriptDirectory.
4. tests/integration/test_pdf_extraction_and_chunking.py: bỏ phụ thuộc C:/Windows/Fonts/arial.ttf, dùng font có hỗ trợ tiếng Việt đi kèm PyMuPDF (kiểm bằng cách trích lại được "Hợp đồng").
5. tests/integration/test_docker_stack_config.py::test_default_compose_keeps_llm_local_safe: không phụ thuộc .env cá nhân (dùng --env-file trỏ tới file tạm hoặc .env.example).
6. tests/unit/test_task0353c2e_eval_harness.py và test_task0353c2f_eval_harness.py: thêm pytest.skip có lý do rõ ràng khi file manifest trong artifacts/ không tồn tại (clone mới). Không di chuyển artifact.
7. Các contract S01 trong tests/unit/test_multilingual_answer_responsiveness_contract.py và tests/unit/test_task0353e_context_admission_contract.py: CHỈ những param ID đang fail mới đánh dấu xfail(strict=True, reason="S01 open: <id>"). Param đang pass giữ nguyên, nếu không sẽ thành XPASS strict.
8. test_conversation_memory.py: sửa 2 test chỉ lệch format chuỗi. Riêng ca "Travel Approval?" → "Are there exceptions?" bị mất chủ đề: KHÔNG sửa expectation. Đánh dấu xfail(strict=True, reason="follow-up topic loss, needs fix") và ghi vào báo cáo như một lỗi thật.

Sau cùng chạy: `python -m pytest -q` và `python -m pytest tests/unit -q`. Integration CHỈ chạy nếu có sẵn PostgreSQL test mà tôi xác nhận (DATABASE_URL trỏ tới database test riêng, không phải V2). Nếu chưa có thì ghi NOT_RUN. KHÔNG tự start Docker.
Báo cáo: bảng trước/sau (pass/fail/xfail theo file), diff tóm tắt, danh sách xfail kèm lý do. Commit: "test: realign stale fixtures and mark open S01 contracts". Không push.
```

## PROMPT 3 — Vận hành không đụng logic: tiktoken offline + lock dependency

```text
Không sửa logic trả lời. Phạm vi: Dockerfile, file lock dependency, SECURITY.md, ENVIRONMENT_VARIABLES.md.

1. Dockerfile: ở builder stage, tải sẵn encoding cl100k_base vào TIKTOKEN_CACHE_DIR=/opt/tiktoken (RUN python -c "import tiktoken; tiktoken.get_encoding('cl100k_base')"), copy sang runtime stage và đặt ENV TIKTOKEN_CACHE_DIR=/opt/tiktoken. Không đổi các phần khác.
2. Ghi rõ trong SECURITY.md và ENVIRONMENT_VARIABLES.md: tiktoken cần file cache. Đính chính câu "does not call network APIs" (thực tế lần đầu sẽ tải từ openaipublic.blob.core.windows.net nếu chưa có cache).
3. Tạo lock dependency cho backend (ví dụ requirements.lock bằng `uv pip compile pyproject.toml` hoặc pip-tools). Ưu tiên khớp phiên bản đang chạy ổn: nếu có package list 92 gói Codex ghi trong docs/release/TASK-035.3A-* hoặc artifacts/task-035-3a-20261013/, đối chiếu và báo phần lệch. KHÔNG nâng phiên bản nào trong task này. Dockerfile chưa dùng lock vội, chỉ đề xuất.
4. Frontend: chạy `npm audit` và báo cáo. Chỉ chạy `npm audit fix` (không --force) nếu tôi xác nhận. Sau đó lint, typecheck, test, build.
5. Không docker build hay docker run nếu tôi chưa xác nhận. Nếu được phép build, chỉ build image với tag mới, không đụng container V2 đang chạy.
Báo cáo: diff, lệnh đã chạy kèm kết quả, phần NOT_VERIFIED. Commit: "build: bundle tiktoken encoding and add dependency lock".
```

## PROMPT 4 — Xây bộ đánh giá held-out (thước đo độ chính xác)

```text
Mục tiêu: có thước đo khách quan TRƯỚC khi sửa logic trả lời. Không sửa app/.

1. Thiết kế thư mục eval/heldout-v1/ gồm: docs/ (tài liệu nguồn), questions.jsonl, README.md (quy trình, phiên bản, ai duyệt).
2. Soạn bản nháp 10–12 tài liệu ngắn tiếng Việt về lĩnh vực KHÁC nhân sự Nova Digital (ví dụ quy trình IT helpdesk, hợp đồng dịch vụ, sổ tay sản phẩm, quy định an toàn), có:
   - ít nhất 2 cặp tài liệu "phiên bản cũ / phiên bản thay thế" (effective_from, supersedes);
   - mức truy cập khác nhau (ORGANIZATION, DEPARTMENT, PRIVATE).
3. Soạn khoảng 150 câu hỏi với schema: id, split (dev|test, chia cố định 50/100), account (admin/manager/staff), question, expected_status (ANSWERED|NO_ANSWER|ACCESS_DENIED_CONTENT), gold_answer_facts, gold_citations (document, page), category. Tỉ lệ:
   - ≥30% câu không có đáp án;
   - ≥20% câu hỏi bằng tài khoản không có quyền với tài liệu chứa đáp án (phải NO_ANSWER, không được lộ nội dung);
   - có câu diễn đạt lại (paraphrase), câu nhiều điều kiện, câu nối tiếp hội thoại, câu về tài liệu đã bị thay thế.
4. Viết scripts/eval/run_heldout.py, gọi API thật qua HTTP:
   - đầu vào: base URL và tài khoản qua env;
   - kết quả: JSON và bảng tóm tắt các chỉ số answer_accuracy, abstain_precision/recall, false_answer_rate, citation_doc_accuracy, citation_page_accuracy, permission_leak_count (bắt buộc = 0), p50/p95 latency;
   - không ghi password vào file.
5. CHƯA ingest tài liệu và CHƯA chạy với runtime. Dừng lại để tôi duyệt gold label. Đánh dấu README là DRAFT – CHỜ DUYỆT.
Tuyệt đối không dùng câu hỏi này trong code runtime hay để tinh chỉnh luật (quy tắc "No question-specific runtime logic"). Tập test chỉ được chạy khi chốt phiên bản.
Commit: "eval: add held-out evaluation draft and runner".
```

## PROMPT 5 — Các sửa nhỏ về độ chính xác, đặt sau flag, có đo lường

```text
Điều kiện: PROMPT 2 và PROMPT 4 đã xong; tôi đã duyệt gold label và đã có kết quả baseline trên split dev. Nếu chưa, dừng và báo.

Mỗi thay đổi là một commit riêng, có setting flag (mặc định GIỮ hành vi cũ), có unit test, và chạy run_heldout.py trên split dev trước/sau:
1. app/retrieval/authority.py: cue "nam " làm mọi câu chứa "năm"/"Nam" bị coi là câu hỏi lịch sử. Thay bằng cue rõ nghĩa (ví dụ "năm 20xx", "trước đây", "phiên bản cũ"). Unit test cho "nghỉ phép năm", "đủ 5 năm", "Nam được nghỉ thai sản" (False) và "phiên bản cũ của quy định" (True).
2. Câu prompt bị cắt cụt trong _no_answer_retry_messages: viết lại cho trọn nghĩa.
3. group_hits[:2] trong _prepare_answer_draft: đưa ra setting CHAT_PROMPT_HITS_PER_NEED (mặc định 2). Đo với 2, 4, 6.
4. Retry sau khi LLM trả NO_ANSWER (_should_retry_no_answer): thêm setting CHAT_RETRY_AFTER_NO_ANSWER_ENABLED (mặc định true). Đo khi tắt, đặc biệt false_answer_rate và ca S01.
Báo cáo bảng chỉ số dev cho từng biến thể. Chỉ đề xuất đổi mặc định khi permission_leak_count = 0, false_answer_rate không tăng và answer_accuracy không giảm. Không chạy split test. Không xóa luật cũ.
```

## PROMPT 6 — Sửa lõi xếp hạng: reranker làm tiêu chí chính

```text
Điều kiện: PROMPT 5 xong và có số đo dev. Làm trên nhánh riêng feat/reranker-first-ranking.

Vấn đề đã tái hiện: _rank_hits_for_prompt xếp theo alignment_score (trùng từ khóa) và các bộ lọc theo chủ đề; _filter_low_alignment_documents có thể loại mất bằng chứng đúng. Ví dụ "làm việc tại nhà": đoạn "làm việc từ xa…" bị loại, giữ lại đoạn nhiễu "mang tài liệu về nhà".
1. Viết test tái hiện ca trên trước (phải fail với hành vi cũ).
2. Thêm chế độ ranking qua setting PROMPT_RANKING_MODE=legacy|reranker_first:
   - reranker_first: sắp xếp theo điểm cross-encoder; alignment chỉ dùng phá hòa;
   - không lọc bỏ hit có điểm reranker cao chỉ vì trùng từ thấp.
3. Hiệu chỉnh ngưỡng điểm reranker trên split dev (vẽ đường precision/recall của quyết định "có trả lời"). Ghi ngưỡng và cách chọn vào RAG_DESIGN.md.
4. Đo dev: legacy vs reranker_first. Báo cáo các câu đổi kết quả (đúng→sai, sai→đúng).
5. Không xóa các hàm theo chủ đề trong task này. Chỉ lập danh sách hàm không còn được gọi trong chế độ mới.
Chỉ đổi mặc định sang reranker_first khi điều kiện như PROMPT 5 thỏa. Không push lên main.
```

## PROMPT 7 — Phân quyền theo mức độ mật (mục tiêu dự án)

```text
Mục tiêu dự án: người có chức vụ cao xem được tài liệu thuộc chức vụ đó. Hiện chỉ có phạm vi PRIVATE/DEPARTMENT/ORGANIZATION + direct grant; Manager và Staff cùng phòng xem như nhau.

Bước 1 (chỉ thiết kế, dừng để tôi duyệt): viết ADR docs/adr/0003-document-classification.md gồm:
- Document.classification (PUBLIC < INTERNAL < CONFIDENTIAL < RESTRICTED);
- ánh xạ role → mức tối đa được xem;
- quan hệ với scope và direct grant (AND hay OR; direct grant có vượt classification không);
- migration cho dữ liệu cũ (mặc định INTERNAL);
- ảnh hưởng tới retrieval SQL, citation revalidation, upload UI, audit;
- danh sách test phân quyền mới (ma trận role × scope × classification × grant).
Bước 2 (sau khi tôi duyệt): triển khai migration Alembic mới, lọc ngay trong build_accessible_document_filter, test ma trận. Chạy lại toàn bộ test phân quyền và run_heldout.py: permission_leak_count phải = 0. Không sửa migration cũ.
```

## PROMPT 8 (tùy chọn) — Tiếp tục R28 của Codex

Nhận định của tôi: R28 (Windows native identity collector, DPAPI, SID, TLS cho PostgreSQL local) là hardening hạ tầng. Nó **không cải thiện độ chính xác trả lời** và đang bị chặn bởi nhiều quyết định chưa có. Chỉ dùng prompt này nếu bạn thật sự cần AUTH-02.

```text
Chỉ đọc và lập kế hoạch, KHÔNG thực thi R28.
1. Từ bản sao lưu ở PROMPT 1, đọc các báo cáo R22–R27 và approved manifest. Không in secret.
2. Tóm tắt: mục tiêu R28, đầu vào/đầu ra, các blocker trong HANDOFF.md (trusted bootstrap/SID, DPAPI provider PathNotFound, asyncpg compatible, PostgreSQL auth method, TLS policy) và quyết định tôi cần đưa ra cho từng blocker (phương án, rủi ro).
3. Đề xuất R28 tối thiểu có thể kiểm chứng offline, kèm điều kiện dừng.
Dừng lại chờ tôi phê duyệt. AUTH-02I.1 vẫn BLOCKED. Không Docker, TCP/SQL, DPAPI unprotect hay provisioning.
```
