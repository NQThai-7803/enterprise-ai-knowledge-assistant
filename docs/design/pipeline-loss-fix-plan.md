# Kế hoạch sửa các tầng làm mất chứng cứ (PROMPT 6)

Trạng thái: bản nháp, đang đo. Nhánh `feat/prompt6-ablation`. Không sửa `app/`, trừ việc bật F nếu F đạt DEC-013 (PR riêng).

## 1. Thiết kế đợt đo (ghi trước khi đo)

**Nơi đo:** GitHub Actions, CPU, Ollama 0.40.15, `qwen2.5:3b`.

**Bộ dev:** UAT Q001-Q100 (proxy), RBAC dev (API và retrieval), `answer_relevance_dev_v1`, `false_refusal_dev_v1`, `false_refusal_dev_v2`. Held-out v1 chỉ dùng để trace. Held-out v2 không đọc.

**Cách ghép đợt (DEC-011):** mỗi bộ có bốn job. Mỗi job có baseline riêng, chạy xen kẽ với các phương án, 2 lượt mỗi cấu hình.

| Job | Cấu hình | Mục đích |
|---|---|---|
| A1 | `base`, `oracle`, `lowalign` (A), `group5` | trần của LLM + validator; đóng góp của bộ lọc và của nhát cắt `[:2]` |
| A2 | `base`, `numnorm` (F), `partial` (C) | chuẩn hoá số; trả lời một phần cho câu hỏi ghép |
| A3 | `base`, `excerpt_off`, `oracle_full` | thêm sau khi đọc code: đoạn trích theo từ vựng thay nội dung chunk; trần thật của LLM + validator |
| R1 | `base`, `ce_bge` | `BAAI/bge-reranker-v2-m3` thật, so với `lexical_fallback` |
| R2 | `base`, `ce_mmarco` | `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` (so sánh hoãn từ DEC-009) |

**Cách áp ablation:** nằm trong `scripts/diagnostics/ablation_patches.py`, nạp vào tiến trình API của stack eval qua `scripts/diagnostics/ablation_site/sitecustomize.py`, và chỉ chạy khi cấu hình đặt `EVAL_ABLATION`.
- Lỗi khi áp patch làm API dừng hẳn.
- `ci_batch.sh` không chạy runner nếu log API thiếu dòng `ABLATION applied`.
- Mỗi lượt ghi `flags.txt`.

**Các ablation:**

- **`oracle`:** retrieval chạy như thường, có lọc quyền, nhưng `top_k` nâng lên 200; chỉ giữ chunk gold; bỏ qua supplement, xếp hạng, bộ lọc và nhát cắt `[:2]` (giữ tối đa 5 chunk). Gold được định nghĩa như sau:
  - UAT: document và trang trong `eval-data/uat/retrieval-gold.json`, 98 câu;
  - các bộ còn lại: document và fact của câu phải trả lời.

  Câu không có gold, hoặc có gold nằm ngoài quyền của người hỏi, chạy như baseline. Vì vậy oracle không thể gây rò rỉ. Mỗi câu ghi một dòng log `oracle hit|miss`.
- **`excerpt_off`:** mỗi source của prompt là nguyên chunk, không qua `query_focused_excerpt` (`app/chat/context_builder.py:221`). Hàm này thay chunk bằng các dòng chọn theo từ vựng khi câu hỏi hỏi người, giá trị, yes/no, điều kiện, hoặc là câu hỏi ghép (khối "CLAIM_n evidence").
- **`oracle_full`:** `oracle` cộng `excerpt_off`, tức đúng nghĩa "đưa thẳng chunk gold cho LLM". Bản `oracle` của A1 vẫn qua bước trích, nên là trần của "bước trích + LLM + validator".
- **`lowalign`:** `_filter_low_alignment_documents` giữ mọi tài liệu.
- **`group5`:** nhát cắt `group_hits[:2]` trong `_prepare_answer_draft` thành `[:5]`. Giới hạn source của prompt là `min(10, RERANKER_TOP_K=6)`, nên 5 lọt được hết.
- **`numnorm`:** flag `RAG_NUMBER_NORMALIZATION_ENABLED` của F.
- **`partial`:** khi câu hỏi ghép chỉ có một phần claim được xác thực, trả lời các phần đó, rồi ghi câu cố định "Tài liệu bạn được phép truy cập không đề cập: …" cho từng phần còn lại. Câu này do server sinh, không cite. Nếu không phần nào được xác thực thì vẫn NO_ANSWER.
- **`ce_bge`, `ce_mmarco`:** model được cache bằng `actions/cache`, mount chỉ đọc vào API, `RERANKER_TIMEOUT_SECONDS=120`. Runner từ chối lượt nào có `reranker_mode` khác `cross_encoder`. Ghi lại RAM (`memory.log`, đo mỗi 30 giây), độ trễ mỗi câu, và số lần `RERANKER_TIMEOUT` trong stack log.

**Quy tắc đọc kết quả:**

1. **Ablation không đổi mặc định.** Chúng chỉ xếp hạng mức đóng góp. Với từng bộ, báo thay đổi số câu từ chối sai, trả lời sai và đúng so với `base` (chỉ tính thay đổi xuất hiện ở cả 2 lượt), số rò rỉ, và UAT.
2. **`numnorm` (F) theo DEC-013:**
   - bắt buộc: 0 rò rỉ, UAT không hồi quy (dung sai 1 câu), trả lời sai không tăng ở bộ nào;
   - sau đó so từng bộ: (a) ít trả lời sai hơn, rồi (b) nhiều câu đúng hơn;
   - nếu thắng thì bật mặc định bằng một PR riêng.
3. **Reranker:** chỉ báo số đo. Có dùng hay không, và dùng model nào, là quyết định của owner.
4. **`oracle`** là trần, không phải phương án. Khoảng cách giữa `oracle` và `base` cho biết phần mất ở các tầng trước LLM.

## 2. Từng cơ chế: code, lý do tồn tại, giả thuyết, phương án

Số dòng tính trên `main` `c3f55cd`. "gas" là `app/services/grounded_answer_service.py`, "cev" là `app/services/claim_evidence_validation_service.py`, "cb" là `app/chat/context_builder.py`.

**Bối cảnh chung:** các rule dưới đây phần lớn được thêm trong TASK-034.1.1 (`206cee3`, 14/08, "rag accuracy and context quality") và RAG-H5.2 (09/2026, CHANGELOG mục 2026-09-28). Mục đích lúc đó là đóng các cụm lỗi của chính Q001-Q100: lỗi trả lời bằng tài liệu lạc đề, lỗi chọn sai dòng giá trị trong bảng, lỗi câu hỏi ghép. Mỗi rule vì vậy đang chặn một kiểu **trả lời sai** đã thấy trên dev. Gỡ rule nào thì phải theo dõi trả lời sai trên mọi bộ.

### A. Bộ lọc tài liệu khớp từ vựng thấp
- **Code:** `_filter_low_alignment_documents` (gas:5861), gọi ở bước cuối của `_rank_hits_for_prompt` (gas:4929). Hằng số ở gas:199-201: chỉ lọc khi điểm cao nhất ≥ 40; giữ tài liệu có điểm ≥ 75% điểm cao nhất; trong tài liệu được giữ, giữ hit ≥ 75% điểm tốt nhất của tài liệu đó.
- **Lý do tồn tại:** loại tài liệu lạc đề trước khi vào prompt. `qwen2.5:3b` dễ chép câu từ tài liệu nhiễu, đúng kiểu lỗi S01.
- **Giả thuyết gốc:** "điểm alignment" chỉ là độ trùng từ với câu hỏi (`_prompt_hit_alignment_score`). Tài liệu đúng nhưng diễn đạt khác câu hỏi bị loại, nếu có một tài liệu khác lặp lại nhiều từ của câu hỏi. Trên mọi stack đang có, reranker là `lexical_fallback`, nên không có tín hiệu ngữ nghĩa nào bù lại.
- **Phương án:**
  1. *Vá nhỏ:* miễn lọc cho hit đứng top-k ở nhánh semantic. Flag `RAG_ALIGNMENT_FILTER_SEMANTIC_GUARD_ENABLED`. Rủi ro thấp.
  2. *Cứu bằng ngữ nghĩa:* giữ tài liệu khi cosine e5 giữa câu hỏi và chunk vượt ngưỡng, hiệu chỉnh trên **UAT** và dev (bài học của FIX 3a). Rủi ro S01 quay lại; phải theo dõi trả lời sai trên mọi bộ.
  3. *Thay bằng tín hiệu học được:* xếp hạng theo cross-encoder thật, alignment chỉ dùng để phá hoà, và bỏ bộ lọc khi có cross-encoder (PROMPT 6 cũ, `reranker_first`).
- **Đo:** ablation `lowalign` (trần của việc gỡ hẳn), R1/R2 (cross-encoder thật).

### B. Nhát cắt `group_hits[:2]`
- **Code:** gas:777, trong `_prepare_answer_draft`. Mỗi nhóm (câu hỏi gốc và từng câu phụ) chỉ giữ 2 hit đã chuẩn bị. Câu hỏi một ý chỉ có một nhóm, nên **context có tối đa 2 chunk**, đúng với `context_selected_count: 2` thấy ở mọi trace. Giới hạn source phía sau là `min(10, RERANKER_TOP_K)` (gas:7105), nên nhát cắt này mới là giới hạn thật.
- **Lý do tồn tại:** có từ commit khởi tạo. Có lẽ để giữ prompt ngắn cho model 3B với ngữ cảnh 8k, và giảm nhiễu.
- **Giả thuyết gốc:** gold bị đẩy xuống hạng 3–5 sau khi xếp theo alignment, nên bị cắt (HO-002, HO-033).
- **Phương án:**
  1. Setting `CHAT_PROMPT_HITS_PER_NEED`, mặc định 2, đo với 3/4/5.
  2. Cắt động theo khoảng cách điểm và ngân sách token.
  3. Cắt theo điểm cross-encoder thay vì thứ hạng alignment.
- **Đo:** ablation `group5`.

### C. Câu hỏi ghép
- **Code:**
  - `information_need_queries` (`app/retrieval/subclaims.py:26`): tách bằng regex trên "và/and" và các cấu trúc cặp.
  - `_compound_draft_with_claim_repair` (gas:1266): **một claim hỏng là từ chối cả câu** (gas:1427).
  - `_claim_focused_excerpt` (cb:518): mỗi ý chỉ giữ các dòng mà `selected_structural_line_indexes` chọn được. Ý nào không chọn được dòng nào thì không có khối "CLAIM_n evidence", nên LLM không thấy chứng cứ của ý đó, dù chunk gold đã vào context (HO-025, HO-037).
- **Lý do tồn tại:** RAG-H5.2 thêm việc tách câu hỏi ghép để truy hồi riêng từng ý, rồi kiểm từng claim. Chính sách "tất cả hoặc không" tránh việc trả lời thiếu mà nghe như đủ.
- **Giả thuyết gốc:** có ba lỗi chồng nhau:
  - tách sai (HO-001, HO-028);
  - đoạn trích theo ý bỏ sót dòng đáp án;
  - chính sách không cho trả lời một phần.
- **Phương án:**
  1. Trả lời một phần, nói rõ ý nào tài liệu không đề cập (ablation `partial`, chính sách cần owner duyệt).
  2. Khi khối evidence của một ý rỗng thì dùng cả chunk cho ý đó.
  3. Tách câu hỏi bằng NLU (mục 4).
- **Đo:** `partial`, `excerpt_off`.

### D. Route deterministic
- **Code:** `_structured_condition_value_answer` (gas:9192), danh sách cue ở gas:9203 (`"sau "`, `"neu "`, …), so trên chuỗi đã bỏ dấu. `RAG_DETERMINISTIC_ROUTE_MODE=strict` (DEC-010) đã thu hẹp route này.
- **Lý do tồn tại:** trả lời chính xác các câu "nếu/khi/sau … thì bao nhiêu" từ bảng, không cần LLM. Đây là lý do chính dev đạt 99/100.
- **Giả thuyết gốc:** khớp chuỗi con sau khi bỏ dấu ("neu" khớp cả "nêu"), và không kiểm câu trả lời có cùng chủ đề với câu hỏi. Kết quả: dev 75/100 đi route này, held-out chỉ 6/40, và 6/6 sai (4b).
- **Phương án:**
  1. Cue so cả dấu (`RAG_STRICT_OUTCOME_CUES_EXACT_ENABLED` đã có, FIX 2b, đang tắt).
  2. Chỉ cho route chạy khi cửa sổ dòng chứa từ chủ đề của câu hỏi.
  3. Thay cue bằng bộ phân loại ý định (mục 4).
- **Đo:** chưa có ablation riêng trong đợt này; số câu đi route deterministic lấy từ trace (`route`).

### F. So số và đơn vị
- **Code:** `_numbers_are_contradicted` (cev:2696) so chuỗi số thô, nên "1" khác "01", và "1.200.000" bị regex cắt thành "1.200" và "000".
- **Lý do tồn tại:** bắt câu trả lời có con số sai, một lỗi trả lời sai nghiêm trọng.
- **Bản sửa:** `RAG_NUMBER_NORMALIZATION_ENABLED` (nhánh `feat/fix-3c-f`). Đo bằng ablation `numnorm`.

### Đoạn trích theo câu hỏi (thêm khi đọc code)
- **Code:** `query_focused_excerpt` (cb:221) thay nội dung chunk bằng các dòng chọn theo từ vựng khi câu hỏi hỏi người, giá trị, yes/no, điều kiện, hoặc là câu hỏi ghép. Source được kiểm bằng validator cũng chính là đoạn trích này.
- **Lý do tồn tại:** TASK-034.1.1. Đưa đúng dòng giá trị của bảng cho model 3B, tránh việc nó lấy nhầm dòng bên cạnh.
- **Giả thuyết gốc:** câu hỏi diễn đạt khác nguồn thì bộ chọn dòng bỏ sót dòng đáp án. FR-A01 ("ai phải đồng ý") chỉ nhận được ba dòng đầu, không có dòng "trưởng phòng phê duyệt", và LLM trả lời "Khong".
- **Phương án:**
  1. Luôn đưa cả chunk khi vừa ngân sách, với đoạn trích chỉ là phần gợi ý đặt trước.
  2. Dùng cả chunk khi đoạn trích không chứa từ nào của câu hỏi.
  3. Chọn câu bằng mô hình (cross-encoder ở mức câu).
- **Đo:** `excerpt_off`, `oracle_full`.

### E. Câu hỏi tiếng Anh trên tài liệu tiếng Việt
- **Code:**
  - `analyze_question` (`app/retrieval/question_analysis.py:168`): cue tiếng Việt là chính; "budget" không được nhận là câu hỏi giá trị.
  - `_person_answer_missing_source_name` (gas:3986): "who" bắt buộc phải có tên người, nên "Active users" bị chặn (HO-036).
- **Giả thuyết gốc:** mọi lớp luật được viết cho câu hỏi tiếng Việt.
- **Phương án:** để sang giai đoạn NLU (mục 4), theo quyết định của owner.

### V. Validator quá dễ
- **Code:** cev:1387-1396 và cev:1636. Một mệnh đề được chép nguyên văn là SUPPORTED, trước mọi kiểm tra về việc nó có trả lời đúng câu hỏi không. Lỗ hổng này đã ghi nhận từ TASK-035.3C (`docs/release/TASK-035.3C-permission-answer-relevance-diagnostic-20261014.md`).
- **Đã thử:** FIX 3a M1a và M1b. Cả hai làm UAT hồi quy 47 và 43 câu.
- **Phương án:**
  1. Kiểm độ đáp ứng bằng mô hình học được (mục 4), hiệu chỉnh trên UAT.
  2. Dùng cross-encoder hoặc NLI cho cặp (câu hỏi, câu evidence).
  3. Chỉ chặn khi kết hợp nhiều tín hiệu yếu (cosine thấp *và* thiếu cụm được hỏi).
- **Đo:** `oracle`/`oracle_full` cho biết phần trả lời sai còn lại khi context đã đúng.

## 4. NLU: thiết kế, chưa làm

**Mục tiêu:** thay các rule viết theo cue bằng mô hình nhỏ, học được và đo được, nhưng không bỏ các bất biến an toàn (lọc quyền trước, citation chỉ từ chunk đã được phép, validator ở cuối).

**Dữ liệu huấn luyện (mọi phần):**
- Chỉ sinh từ chunk của corpus, theo DEC-015. Dùng lại `ml/embedding_finetune/generate_queries.py`: câu hỏi sinh từ chunk, kèm các biến thể không dấu, dấu một phần, lỗi gõ, tiếng Anh.
- Mọi câu đều đi qua kiểm fingerprint với các bộ được bảo vệ, như với fine-tune.
- Bộ dev chỉ dùng để đánh giá. Held-out không dùng cho việc gì.

| Thành phần | Thay cho | Mô hình đề xuất | Nhãn sinh thế nào | Đánh giá | Đưa vào app |
|---|---|---|---|---|---|
| Phân loại ý định / loại câu trả lời | cue trong `analyze_question` và route deterministic (D) | đầu phân loại trên encoder e5-small (dùng chung model embedding, thêm vài trăm nghìn tham số) | LLM gán loại (PERSON, AMOUNT, COUNT, DURATION, CONDITION, YES_NO, DEFINITION, …) cho câu hỏi sinh từ chunk; câu nào hai lần gán khác nhau thì bỏ | độ chính xác trên nhãn tay của Q001-Q100 và các bộ relevance (chỉ đánh giá) | flag; khi bật, route deterministic chỉ chạy nếu ý định là CONDITION/VALUE với độ tin cậy ≥ ngưỡng |
| Tách câu hỏi ghép | regex trong `subclaims.py` (C) | sinh có ràng buộc: LLM tách, server chỉ nhận các ý ghép được từ chính từ của người dùng (như quy tắc hiện tại) | ghép hai câu hỏi sinh từ hai chunk thành một câu, nhãn là hai câu gốc | khớp ý trên câu ghép của UAT, nhóm C của `false_refusal_dev_v2` | flag; regex giữ lại làm dự phòng |
| Kiểm độ đáp ứng | M1a/M1b (V) | cross-encoder (câu hỏi, câu evidence) → "trả lời đúng điều được hỏi" | dương: (câu hỏi sinh từ câu s, s); âm: (câu hỏi đó, câu bên cạnh s′ trong cùng tài liệu), đúng là kiểu lỗi M1 | **hiệu chỉnh và kiểm trên UAT** cùng relevance và false_refusal v1/v2; điều kiện bắt buộc là không hồi quy UAT (bài học FIX 3a) | flag, sau validator hiện có; chỉ chuyển SUPPORTED thành NO_ANSWER, không bao giờ ngược lại |
| E: câu hỏi tiếng Anh | cue tiếng Việt, check "who" phải có tên người | ý định đa ngôn ngữ (cùng bộ phân loại), check độ đầy đủ theo ý định thay vì theo từ | biến thể tiếng Anh của câu hỏi sinh từ chunk | nhóm E của `false_refusal_dev_v2`, câu tiếng Anh của UAT | cùng flag với bộ phân loại ý định |
| M3: đồng nghĩa ("đồng ý"/"phê duyệt") | so khớp từ trong đoạn trích, repair PERSON | chọn câu bằng cross-encoder, thay cho chọn dòng theo từ | các cặp diễn đạt lại do LLM viết từ câu trong chunk | FR-A01 và nhóm A của `false_refusal_dev_v1`, nhóm L của v2 | flag ở `query_focused_excerpt` |

**Thứ tự đề xuất:** (1) kiểm độ đáp ứng, vì nó chặn trả lời sai, lỗi nặng hơn từ chối sai; (2) phân loại ý định, thay route deterministic; (3) tách câu hỏi ghép; (4) E và M3. Thứ tự cuối cùng chốt sau khi có số đo ablation (mục 3).
