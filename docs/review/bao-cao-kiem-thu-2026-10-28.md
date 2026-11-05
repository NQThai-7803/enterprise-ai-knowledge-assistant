# Báo cáo kiểm thử và danh sách việc cần làm — Enterprise AI Knowledge Assistant

Ngày kiểm tra: 28/10/2026. Phạm vi: toàn bộ mã nguồn `app/`, `tests/`, `frontend/`, migrations, cấu hình Docker/CI và các tài liệu chính.
Nguyên tắc: chỉ đọc và chạy test trên **bản sao**, không sửa gì trong thư mục gốc. Không có dòng code nào của dự án bị thay đổi.

Mỗi mục bên dưới đều đã được tự kiểm lại bằng một trong ba cách: chạy test, chạy thử nghiệm nhỏ (experiment) gọi thẳng hàm thật của dự án, hoặc đọc code kèm số dòng. Với từng mục, tôi tự hỏi "sửa cái này có đưa dự án đi đúng hướng không?" và ghi kết luận vào ô **Đáng làm?**. Mục **Rủi ro khi sửa** cho biết thay đổi đó có chạm vào logic trả lời hoặc dữ liệu hay không. Thông tin này quan trọng vì bạn vẫn đang làm song song với Codex.

---

## 1. Kết quả chạy kiểm thử

| Nhóm | Kết quả | Ghi chú |
|---|---|---|
| Ruff lint `app/` | Pass | `ruff check .` toàn repo có 33 lỗi: 24 lỗi nằm trong 3 file `tmp_*_trace.py` chưa commit, 9 lỗi trong `tests/containment*`. |
| Unit + API (không cần DB), 1.706 test | **1.690 pass / 16 fail** | 14 fail là các contract an toàn S01 do Codex cố ý để đỏ. 2 fail còn lại do test phụ thuộc máy Windows (xem mục 2.4). |
| Integration + API có PostgreSQL + pgvector, 646 test | **606 pass / 40 fail** | Phần lớn fail do test lỗi thời so với code, không phải do logic hỏng (xem mục 2.1–2.3). |
| Frontend: ESLint | 0 lỗi, 7 cảnh báo | |
| Frontend: TypeScript typecheck | Pass | |
| Frontend: Vitest | 40/40 pass | |
| Frontend: build | Pass | Build có xuất source map (`sourcemap: true`). |
| Frontend: Playwright (mock backend) | 15/15 pass | |
| `npm audit` | 6 lỗ hổng (3 high, 3 moderate) | Xem mục 4.3. |
| Security scan nội bộ (`.github/scripts/security_scan.py`) | Pass | |

**Chưa chạy được, cần bạn tự chạy trên máy:**
- Test Celery/Redis.
- Test dùng model thật (e5, bge-reranker): sandbox không tải được PyTorch.
- LLM thật qua Ollama.
- `docker compose up` toàn bộ stack.
- E2E live giữa frontend và backend thật.

Môi trường test của tôi cũng khác máy bạn: FastAPI 0.162, SQLAlchemy 2.1.6, PyMuPDF 2.0, PostgreSQL 16 + pgvector 0.6.2. Lý do là `pyproject.toml` chỉ ghi `>=`, không có file lock (xem mục 4.4).

---

## 2. Kiểm thử đang hỏng hoặc không còn bảo vệ được gì

### 2.1 Bộ test phân quyền và retrieval end-to-end không chạy được (25 test) — ưu tiên cao

- **Bằng chứng:** Toàn bộ `tests/integration/test_hybrid_retrieval.py` (20 test) và `test_grounded_answer_persistence.py` (5 test) đều chết ngay ở bước tạo `Settings`, với lỗi `RERANKER_CANDIDATE_K must be less than or equal to HYBRID_RETRIEVAL_MAX_TOP_K`. Nguyên nhân: test đặt `hybrid_retrieval_max_top_k=10`, trong khi mặc định `reranker_candidate_k=50`.
- **Tác động:** Các test quan trọng nhất cho mục tiêu dự án đều đang không chạy, gồm `test_hybrid_never_returns_unauthorized_chunk`, `test_hybrid_revoke_has_immediate_effect` và `test_grounded_answer_uses_authorized_chunks_only`.
- **Đã tự kiểm lại:** Khi đặt `RERANKER_CANDIDATE_K=10` qua biến môi trường (không sửa code), 25/28 test pass. Vậy **logic phân quyền vẫn đúng, chỉ có test bị lỗi thời**.
- **Đề xuất:** Sửa hàm `make_settings` trong test để truyền thêm `reranker_candidate_k` và `reranker_top_k` phù hợp.
- **Đáng làm?** Có. Đây là lưới an toàn cho RBAC. Sửa xong thì mọi thay đổi sau này của Codex đều được kiểm phân quyền tự động.
- **Rủi ro khi sửa:** Rất thấp, chỉ đụng file test.

### 2.2 Test "happy path" của Chat API không còn đi qua nhánh ANSWERED (10 test)

- **Bằng chứng:** `tests/api/test_chat_messages.py` (5 test), `tests/api/test_chat_streaming.py` (4 test) và `test_grounded_answer_citations.py::test_invalid_citation_persists_no_messages_or_citations` mong đợi `ANSWERED`, nhưng nhận về `NO_ANSWER`. Tôi đã in ra SSE event: hệ thống trả câu "Khong tim thay du thong tin…" với `citations: []`.
- **Nguyên nhân:** Dữ liệu giả của test ("allowed context", "Grounded answer [SOURCE_1]") không còn vượt qua được các lớp kiểm tra bằng chứng mới thêm vào. Vì vậy nhánh kiểm tra citation sai cũng không bao giờ được chạy tới.
- **Tác động:** Hệ thống vẫn an toàn (thất bại thì trả NO_ANSWER), nhưng **hợp đồng API cho trường hợp có câu trả lời** (citations, sự kiện SSE `ready`, web citation, conversation memory) đang không được test nào bảo vệ.
- **Đề xuất:** Viết lại fixture với ngữ cảnh và câu trả lời khớp nhau thật sự, ví dụ hit "Nhân viên được nghỉ 12 ngày phép năm." và answer "Nhân viên được nghỉ 12 ngày phép năm [SOURCE_1]."
- **Đáng làm?** Có.
- **Rủi ro khi sửa:** Thấp, chỉ đụng test.

### 2.3 Test lỗi thời khác

| Test | Vấn đề | Đánh giá |
|---|---|---|
| `test_admin_monitoring.py::test_admin_system_response_does_not_expose_secrets_or_content` | Hard-code migration head `20260803_0010`, trong khi thực tế đã là `20260822_0011`. | Sửa test để đọc head động. |
| `test_grounded_answer_persistence.py::test_internal_system_messages_are_not_grounding_prompt_memory` | Test mong đợi tin nhắn SYSTEM nội bộ có trong prompt, nhưng code hiện tại đã bỏ. README vẫn ghi là có. | Cần chốt hành vi nào là đúng, rồi sửa test hoặc README cho khớp. |
| `test_conversation_memory.py` (4 test) | 2 test chỉ khác về format chuỗi. Riêng ca "Travel Approval?" → "Are there exceptions?" cho thấy câu hỏi nối tiếp **bị mất chủ đề** (query retrieval chỉ còn "Are there exceptions?"). | Ca thứ hai có thể là hồi quy thật, gây NO_ANSWER sai cho câu hỏi nối tiếp. Nên xem lại `follow_up_resolver.py`. |

### 2.4 Test phụ thuộc vào máy của bạn (sẽ fail trên CI hoặc máy khác)

- `test_pdf_extraction_and_chunking.py::..._vietnamese_text` hard-code font `C:/Windows/Fonts/arial.ttf`. Trên Linux, PDF test bị lỗi font và chữ "Hợp đồng" bị trích ra thành "H·p ··ng".
- `test_docker_stack_config.py::test_default_compose_keeps_llm_local_safe` phụ thuộc vào `.env` riêng của bạn (đòi `LLM_PROVIDER=ollama`, model `qwen2.5:3b`…).
- `test_task0353c2e/c2f_eval_harness.py` đọc file trong `artifacts/`, mà thư mục này bị `.gitignore`. Clone mới từ GitHub thì 5 test này fail.
- `test_tiktoken_counter.py::test_token_counter_does_not_require_network` có tên gây hiểu nhầm: nó chỉ chặn mạng *sau khi* encoding đã tải xong (xem mục 4.1).

**Đáng làm?** Có, vì việc sửa đơn giản: dùng font đi kèm PyMuPDF, mock `.env`, chuyển manifest cần dùng vào `tests/fixtures/`.

### 2.5 Các contract đỏ của S01 (14 test) đang làm CI luôn đỏ

Đây là các test Codex cố ý để fail, nhằm ghi nhận lỗi S01 chưa sửa. Ý tưởng này đúng, nhưng vì chúng nằm chung `tests/unit`, CI sẽ luôn đỏ và bạn không phân biệt được "đỏ do S01" với "đỏ do lỗi mới".

**Đề xuất:** Đánh dấu `@pytest.mark.xfail(strict=True, reason="S01")`. Khi S01 được sửa, các test này sẽ tự báo xanh bất ngờ để bạn bỏ đánh dấu.

**Đáng làm?** Có. **Rủi ro khi sửa:** Không có.

---

## 3. Độ chính xác của câu trả lời (phần quan trọng nhất)

### 3.1 Xếp hạng bằng từ khóa đè lên reranker và loại mất bằng chứng đúng — ưu tiên cao nhất

- **Code:** Trong `grounded_answer_service.py`, `_rank_hits_for_prompt()` (khoảng dòng 4691–4750) sắp xếp hit theo `alignment_score`, tức điểm trùng từ khóa. Điểm này đi kèm hàng loạt bộ lọc theo chủ đề: lương, phép, lịch làm việc, phụ cấp, người–chức danh. Sau đó `_filter_low_alignment_documents` loại các tài liệu có điểm trùng thấp. Thứ tự của cross-encoder reranker (bge-reranker-v2-m3) chỉ còn làm tiêu chí phụ khi hòa điểm (dòng 1664: `_merge_retrieval_hits(ranked_hits, reranked_hits)`).
- **Thử nghiệm:** Câu hỏi "Nhân viên có được làm việc tại nhà không?" với 2 hit, đưa vào theo đúng thứ tự reranker:
  1. "Người lao động được phép làm việc từ xa tối đa 2 ngày mỗi tuần khi được quản lý phê duyệt." (đây là câu trả lời đúng)
  2. "Nhân viên không được mang tài liệu nội bộ về nhà và phải làm việc đúng giờ tại văn phòng." (câu gây nhiễu)

  Kết quả: `_rank_hits_for_prompt` **chỉ giữ lại câu gây nhiễu** và loại hẳn câu đúng.
- **Tác động:** Cùng một cơ chế này có thể giải thích hai loại lỗi:
  - Từ chối sai: câu đúng dùng từ đồng nghĩa nên bị loại.
  - Lỗi S01: tài liệu không liên quan nhưng trùng nhiều từ lại được đưa lên đầu.
- **Đề xuất:**
  - Dùng điểm reranker làm khóa sắp xếp chính, chỉ dùng trùng từ khóa như một đặc trưng phụ.
  - Hiệu chỉnh ngưỡng (calibrate threshold) cho điểm reranker trên tập dev, rồi đo lại trên tập held-out (mục 3.6).
  - Làm sau một feature flag để so sánh trước và sau.
- **Đáng làm?** Có, đây là việc có giá trị nhất cho mục tiêu "chính xác trước". Nhưng chỉ nên làm sau khi có bộ đánh giá ở mục 3.6, nếu không sẽ không biết là tốt lên hay tệ đi.
- **Rủi ro khi sửa:** Cao, vì đụng logic lõi. Cần làm trên nhánh riêng, không chen vào việc Codex đang làm.

### 3.2 Mỗi câu hỏi chỉ đưa 2 chunk vào LLM

- **Code:** Dòng 746: `group_hits[:2]`.
- **Thử nghiệm:** Retrieval trả về 5 hit liên quan, nhưng `select_context_for_prompt` chỉ nhận **2 hit**, dù `citation_max_sources_per_answer=5`.
- **Tác động:** Các câu hỏi cần tổng hợp nhiều đoạn, như liệt kê, so sánh hay quy định có nhiều điều kiện, bị thiếu ngữ cảnh. Hệ thống dễ trả lời thiếu hoặc NO_ANSWER sai.
- **Đề xuất:** Đưa con số 2 ra config, thử 4–6 chunk trong giới hạn token, đo trên bộ đánh giá.
- **Đáng làm?** Có. Sửa ít code mà kiểm chứng được ngay.
- **Rủi ro khi sửa:** Trung bình, vì thay đổi ngữ cảnh đầu vào của LLM.

### 3.3 Khi LLM đã từ chối trả lời, hệ thống lại hỏi lại để ép trả lời

- **Code:** Dòng 876 và hàm `_should_retry_no_answer` (dòng 4554). Nếu LLM trả NO_ANSWER mà câu hỏi và nguồn trùng nhau **≥ 2 từ**, hệ thống gọi LLM thêm lần nữa với prompt khuyến khích trả lời ("…a false premise is not a reason for no-answer…"). Mỗi câu hỏi có thể tốn tới 3–4 lần gọi LLM.
- **Thử nghiệm:** Với câu hỏi về "làm việc từ xa" và một tài liệu bảo mật không liên quan, hệ thống đã gọi LLM 3 lần. Trong ca giả lập này, lớp validator vẫn chặn được ở cuối nên kết quả là NO_ANSWER. Vì vậy tôi **không khẳng định** đây là nguyên nhân gốc của S01. Đây là cơ chế đi ngược nguyên tắc "không chắc thì từ chối" và cần được đo.
- **Đề xuất:** Thêm flag tắt bước retry này, rồi chạy lại ca S01 của 035.3B và bộ UAT để so sánh. Nếu tắt mà độ chính xác không giảm thì bỏ hẳn, đồng thời giảm được độ trễ (hiện p95 là 23,7 giây, max 96 giây với qwen2.5:3b).
- **Đáng làm?** Có, vì đây là thí nghiệm rẻ và có thể giải được một phần S01.
- **Rủi ro khi sửa:** Trung bình, nhưng nếu đặt sau flag thì đảo ngược được.

### 3.4 Prompt retry bị cắt mất nửa câu

- **Code:** Dòng 3093–3094 trong `_no_answer_retry_messages`: `"Do not merely restate or paraphrase the question. " "when the premise is false; a false premise is not a reason…"`. Phần đầu của câu "when the premise is false…" đã bị xóa, nên LLM nhận một câu cụt, không rõ nghĩa.
- **Đáng làm?** Có. Sửa vài từ, hoặc xóa luôn nếu bỏ retry ở mục 3.3.
- **Rủi ro khi sửa:** Thấp.

### 3.5 Từ "năm" và "Nam" bị coi là câu hỏi về phiên bản cũ

- **Code:** `app/retrieval/authority.py`, dòng 17, có cue `"nam "`.
- **Thử nghiệm:** `is_historical_query()` trả `True` cho các câu sau:
  - "Nhân viên được nghỉ phép **năm** bao nhiêu ngày?"
  - "Làm đủ 5 **năm** thì được thêm mấy ngày phép?"
  - "**Nam** được nghỉ thai sản bao lâu?"
- **Tác động:** Khi câu hỏi bị coi là "lịch sử", keyword retrieval tắt chế độ ưu tiên tài liệu đang hiệu lực, nên có thể lấy nhầm chính sách đã bị thay thế. Trong khi đó, chữ "năm" xuất hiện trong rất nhiều câu hỏi nhân sự, và corpus UAT lại có sẵn 2 chính sách nghỉ chồng chéo nhau (Q018).
- **Đề xuất:** Bỏ cue `"nam "`, chỉ giữ các cụm rõ nghĩa như "năm 2024", "trước đây", "phiên bản cũ". Thêm test cho 3 câu trên.
- **Đáng làm?** Có. Lỗi thật, sửa nhỏ, không đụng dữ liệu.
- **Rủi ro khi sửa:** Thấp.

### 3.6 Con số 98/98 chưa đo được khả năng tổng quát — cần bộ đánh giá held-out

- **Bằng chứng về overfitting:**
  - 96/481 hàm helper trong `grounded_answer_service.py`, `claim_evidence_validation_service.py`, `context_builder.py` và `retrieval/` được đặt tên theo đúng chủ đề của 9 tài liệu UAT (Nova Digital): `_structured_salary_band_answer`, `_annual_leave_relations_for_question`, `_paid_parent_bereavement_duration_status`, `_overtime_rate_facts`… Có cả câu trả lời viết sẵn theo mẫu: `"Dải lương tham khảo là {value}."` (dòng 9580).
  - `artifacts/` có khoảng 37 lượt chạy `targeted-v1…v37`, khoảng 30 lượt `mini-gate`, cùng nhiều file kiểu `q059`, `q073`, `q096`… Tức là từng câu trong bộ Q001–Q100 đã được sửa riêng cho đến khi pass.
  - Bộ đo 100 câu chỉ có **2 câu cần từ chối** và **không có câu nào hỏi bằng tài khoản khác quyền**. Bộ safety smoke chỉ có 6 câu, trong đó 1 câu unsupported và 1 câu phân quyền.
- **Kết luận:** 98/98 là điểm số trên chính bộ dữ liệu dùng để tinh chỉnh. Gặp tài liệu của công ty khác, độ chính xác thực tế chưa được biết.
- **Đề xuất:** Đây nên là việc làm **trước** mọi thay đổi ở mục 3.1–3.3. Tạo bộ đánh giá mới, không dùng để sửa code:
  - 10–15 tài liệu mới, khác lĩnh vực nhân sự (ví dụ quy trình IT, hợp đồng, sổ tay khách hàng).
  - Khoảng 150 câu, trong đó ≥ 30% không có đáp án trong tài liệu, ≥ 20% hỏi bằng tài khoản không có quyền, cộng thêm các câu về tài liệu đã bị thay thế.
  - Chỉ số đo: tỉ lệ trả lời đúng, tỉ lệ từ chối đúng/sai, tỉ lệ citation đúng, tỉ lệ rò rỉ quyền (phải bằng 0), độ trễ p50/p95.
  - Chia dev/test cố định từ đầu và chỉ chạy tập test khi chốt phiên bản.
- **Đáng làm?** Có, giá trị nhất. Đây cũng là phần đáng đưa vào CV hơn cả.
- **Rủi ro khi sửa:** Không có, vì chỉ thêm dữ liệu và script đo.

### 3.7 Thứ tự ưu tiên tài liệu hiện hành chỉ là tiêu chí phụ

- **Code:** `semantic_repository.py` sắp xếp theo `cosine_distance` trước, sau đó mới tới `current_authority_order_expression()`.
- **Tác động:** Tài liệu SUPERSEDED hoặc hết hạn chỉ cần giống câu hỏi hơn một chút là vẫn đứng đầu.
- **Đề xuất:** Mặc định loại hẳn (hoặc phạt điểm) tài liệu SUPERSEDED/ARCHIVED, trừ khi người dùng hỏi về lịch sử.
- **Đáng làm?** Có, nhưng ở mức ưu tiên trung bình. Làm sau mục 3.5.

---

## 4. Vận hành và dữ liệu

### 4.1 tiktoken tải file encoding từ Internet khi chạy

- **Bằng chứng:** `tiktoken.get_encoding("cl100k_base")` gọi tới `openaipublic.blob.core.windows.net`. Trong sandbox không có mạng, 8 test chunking và 6 test tokenizer fail với lỗi `ChunkingError`. `Dockerfile` không đóng gói sẵn file này, trong khi `SECURITY.md` dòng 291 lại ghi "does not call network APIs".
- **Tác động:** Trên máy chủ nội bộ không có Internet (đúng bối cảnh doanh nghiệp, ngân hàng hay VNPT), mọi tài liệu upload sẽ bị FAILED. Phần chat cũng tạo `TiktokenTokenCounter`.
- **Đề xuất:** Tải sẵn file trong Docker build và đặt `TIKTOKEN_CACHE_DIR`. Sửa lại câu trong SECURITY.md.
- **Đáng làm?** Có. Đây là điểm cộng lớn khi giới thiệu dự án là "chạy được on-premise".
- **Rủi ro khi sửa:** Thấp, không đụng dữ liệu.

### 4.2 Kích thước chunk được đo bằng tokenizer khác với tokenizer của model embedding

- **Thử nghiệm:** Dùng tokenizer thật của `multilingual-e5-small` (giới hạn `max_seq_length = 512`), lấy từ thư mục `data/models` trên máy bạn:

| Văn bản | 500 token cl100k (target) | 700 token cl100k (max) |
|---|---|---|
| Tiếng Việt | 239 token e5 (ổn) | 334 token e5 (ổn) |
| Tiếng Anh | **570** token e5 (vượt 512) | **798** token e5 (vượt 512) |

- **Tác động:** Với tài liệu tiếng Anh, khoảng 10–36% cuối chunk bị cắt im lặng khi tạo embedding, nên tìm kiếm ngữ nghĩa không "thấy" phần đó. Tài liệu tiếng Việt không bị ảnh hưởng.
- **Đề xuất:** Đếm token bằng tokenizer của chính model embedding, hoặc giới hạn khoảng 400 token cl100k cho văn bản không phải tiếng Việt.
- **Đáng làm?** Có, ưu tiên trung bình. **Rủi ro khi sửa:** Phải xử lý lại (re-index) toàn bộ tài liệu, tức là có đụng dữ liệu. Nên làm cùng đợt re-index khác.

### 4.3 Lỗ hổng frontend (`npm audit`)

| Gói | Mức | Loại | Nhận định |
|---|---|---|---|
| `zod <4.6.6` | high | Trực tiếp, chạy ở runtime | Chỉ gây DoS phía trình duyệt của chính người dùng. Nâng lên zod 4 là thay đổi phá vỡ (breaking), nên để sau. |
| `source-map-js`, `nanoid`, `postcss-selector-parser`, `vitest`, `@vitest/mocker` | high/moderate | Chỉ dùng lúc build/dev | `npm audit fix` (không cần `--force`) là đủ. |

Cũng nên tắt `sourcemap` khi build production (hiện tạo file map 1,6 MB).

**Đáng làm?** Có, việc nhỏ.

### 4.4 Backend không có file lock dependency

`pyproject.toml` chỉ khai báo `>=`. Đây là gốc của lỗi "API và worker build từ hai bộ package khác nhau" (R05) mà Codex đã ghi nhận: mỗi lần build lại có thể ra tổ hợp phiên bản khác.

**Đề xuất:** Dùng `uv lock` hoặc `pip-compile` để tạo `requirements.lock`, và cả API lẫn worker cùng cài từ file đó.

**Đáng làm?** Có. **Rủi ro khi sửa:** Thấp, nếu chốt đúng các phiên bản đang chạy ổn.

### 4.5 Rủi ro khi dữ liệu lớn lên (chưa gấp)

- **HNSW kết hợp bộ lọc quyền:** Không có `hnsw.ef_search` hay `hnsw.iterative_scan`. Khi số chunk lớn mà phần lớn người dùng không có quyền xem, truy vấn có thể trả về ít hơn top_k kết quả. Với 143 chunk hiện tại thì chưa thấy ảnh hưởng.
- **Keyword search bỏ dấu:** Biểu thức `translate(lower(text))` không có index, nên mỗi truy vấn phải quét toàn bảng.
- **Đáng làm?** Chưa cần. Ghi lại để làm khi mở rộng.

---

## 5. Git và an toàn mã nguồn — nên làm ngay, không đụng logic

- **Đọc `.git/index`:** Có 586 file đang được theo dõi. `grounded_answer_service.py` được stage lần cuối ngày 8/9, nhưng file thực tế đã sửa đến 13/10. Như vậy khoảng **5 tuần làm việc chưa được commit**.
- **Ít nhất 19 file mã nguồn và test chưa được theo dõi**, trong đó có `app/retrieval/leave_relations.py` (được 3 module backend import) và `frontend/src/components/data/DataTable.tsx` (được 6 trang frontend import). Nếu clone từ GitHub về và ghép với code hiện tại thì cả backend lẫn frontend đều chạy lỗi.
  - Riêng `DataTable.tsx` thì **commit cũng không vào được**: dòng 33 của `.gitignore` là `data/`, mẫu này khớp với *mọi* thư mục tên `data`, kể cả `frontend/src/components/data/`. Tôi đã kiểm bằng `git check-ignore -v`. Cần đổi thành `/data/` (chỉ thư mục gốc) trước khi commit.
- **Đã commit nhầm:**
  - File tên `tore package.json package-lock.json` (có vẻ do gõ nhầm lệnh `git restore`).
  - `enterprise_ai_md_updates_2026-08-19_v6.zip`.
  - 38 file trong `files-for-chat/` (bản sao code).
  - Gitlink `vite-monorepo` không có `.gitmodules`.
- **Thư mục dự án nằm trong OneDrive:** `.backups/` (bản dump database), `.env`, `.env.task035.production`, `.venv`, `node_modules` và cache model đều đang được đồng bộ lên cloud.
- **Đề xuất:**
  - Tạo nhánh `wip/codex-2026-10` rồi commit toàn bộ hiện trạng. Không sửa gì, chỉ để lưu lại.
  - Sau đó mới dọn file rác bằng một commit riêng.
  - Cân nhắc chuyển dự án ra khỏi OneDrive.
- **Đáng làm?** Có, làm đầu tiên. Đây là việc duy nhất mà nếu không làm thì có thể mất trắng công sức.

---

## 6. Khoảng trống so với mục tiêu sản phẩm

### 6.1 Phân quyền chưa theo "chức vụ cao xem được tài liệu của chức vụ đó"

- **Hiện trạng:** Mô tả Project yêu cầu người có chức vụ cao xem được tài liệu thuộc cấp của mình. Code hiện tại (`permissions.py`, `build_accessible_document_filter`) chỉ phân quyền theo phạm vi: PRIVATE, DEPARTMENT, ORGANIZATION, cộng với cấp quyền trực tiếp. Không có trường mức độ mật (classification) hay vai trò tối thiểu (min_role). Manager và Staff cùng phòng **xem được đúng những tài liệu như nhau**, Manager chỉ hơn ở quyền sửa và quản lý.
- **Đề xuất thiết kế:**
  - Thêm `Document.classification`: `PUBLIC < INTERNAL < CONFIDENTIAL < RESTRICTED`.
  - Ánh xạ vai trò sang mức tối đa được xem (STAFF → INTERNAL, MANAGER → CONFIDENTIAL, ADMIN hoặc Director → RESTRICTED).
  - Điều kiện xem = đúng phạm vi **và** mức độ mật ≤ mức của vai trò. Lọc ngay trong SQL như hiện nay.
  - Kèm migration và bộ test phân quyền mới.
- **Đáng làm?** Có, vì đây đúng là mục tiêu ghi trong mô tả dự án. **Rủi ro khi sửa:** Cao, vì có migration và đụng dữ liệu. Làm sau khi xử lý xong S01.

### 6.2 Citation chưa mở được tài liệu tại đúng trang

PRD yêu cầu "mở đúng tài liệu và trang tham chiếu". Hiện tại `ChatPage.tsx` (khoảng dòng 725) chỉ hiện nhãn "Page N" và đoạn trích. Không có link mở tài liệu, chỉ có nút tải file ở trang chi tiết.

**Đáng làm?** Có. Tính năng này dễ gây ấn tượng khi demo. **Rủi ro khi sửa:** Thấp.

### 6.3 Giao diện tiếng Anh và câu trả lời mặc định không dấu

- Nhãn giao diện ("Citations", "Evidence", "No citations") là tiếng Anh.
- Câu NO_ANSWER mặc định không có dấu: "Khong tim thay du thong tin…" (`config.py`, dòng 206).

**Đáng làm?** Có, việc nhỏ cho sản phẩm hướng tới người dùng Việt.

### 6.4 SSE chỉ phát câu trả lời sau khi validate xong

Hệ thống đợi validate xong mới phát câu trả lời, nên người dùng chờ trung bình khoảng 8 giây, p95 24 giây mà không thấy gì. Thiết kế này đúng vì an toàn là ưu tiên. Nên bổ sung sự kiện tiến trình ("đang tìm tài liệu…", "đang kiểm tra nguồn…").

**Đáng làm?** Có, mức thấp.

---

## 7. Tài liệu và quy trình

- **5 file bị lỗi font (mojibake):** `CODEX_START_HERE.md` (34 chỗ), `TASKS.md` (29), `FRONTEND_SPEC.md` (26), `RAG_DESIGN.md` (24), `TESTING_STRATEGY.md` (16).
- **README lỗi thời:** Vẫn ghi "TASK-035 has not started" và "Alembic head 0010". `PROJECT_ROADMAP.md` chưa tick ô nào.
- **Quy trình quá nặng:** Có hơn 60 báo cáo `docs/release/TASK-035.3*` trong 2 ngày. `PROJECT_STATUS.md` nặng 67 KB, `TASKS.md` nặng 81 KB. Codex đang ở chế độ "chờ owner phê duyệt", trong khi owner chính là bạn.
- **Đề xuất:** Gom về một file trạng thái ngắn kèm một file các quyết định, và tự chốt các mục đang chờ quyết định.
- **Đáng làm?** Có, nhưng không gấp.

---

## 8. Những việc tôi đã cân nhắc và **không khuyên làm lúc này**

- **Viết lại toàn bộ `grounded_answer_service.py` (10.631 dòng):** Chưa nên làm khi chưa có bộ đánh giá ở mục 3.6, vì refactor mà không có thước đo thì rất dễ làm hỏng những gì đang chạy được. Nên tách dần từng phần sau khi đã có số đo.
- **Các hạng mục kiểu doanh nghiệp lớn trong TASK-035** (TLS thật, khôi phục dữ liệu ngoài máy, diễn tập rollback, SBOM): Giá trị thấp với dự án portfolio hay thực tập. Chỉ cần ghi trong README là "ngoài phạm vi".
- **Sửa 9 lỗi style của Ruff trong `tests/containment`:** Chỉ là thẩm mỹ.
- **Chuyển token sang cookie httpOnly:** `sessionStorage` là chấp nhận được cho MVP.

---

## 9. Thứ tự đề xuất

1. **Không đụng logic (làm ngay, song song với Codex được):**
   - Sửa `.gitignore` (`data/` → `/data/`), rồi commit lưu hiện trạng (mục 5).
   - Sửa fixture test (2.1, 2.2, 2.3, 2.4).
   - Đánh dấu `xfail` cho các contract S01 (2.5).
   - Đóng gói sẵn tiktoken trong Docker (4.1).
   - Tạo lock dependency (4.4).
2. **Xây thước đo:** Bộ đánh giá held-out và script tính chỉ số (3.6).
3. **Sửa nhỏ có đo lường, đặt sau flag:**
   - Lỗi "năm"/"Nam" (3.5).
   - Prompt bị cắt (3.4).
   - Giới hạn 2 chunk (3.2).
   - Tắt retry khi NO_ANSWER (3.3).
4. **Sửa lớn:** Đưa reranker lên làm tiêu chí chính và hiệu chỉnh ngưỡng (3.1), sau đó gỡ dần các luật viết riêng cho từng chủ đề.
5. **Hoàn thiện mục tiêu sản phẩm:** Phân quyền theo mức độ mật (6.1), citation mở đúng trang (6.2), giao diện tiếng Việt (6.3).
6. **Dọn dẹp:** Tài liệu và quy trình (7), lỗ hổng npm (4.3), các rủi ro khi mở rộng (4.5).
