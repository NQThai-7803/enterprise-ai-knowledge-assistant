# FIX 4 (ii): kiểm độ đáp ứng, hiệu chỉnh trên phần UAT đi đường LLM

Viết 2026-11-14, **trước mọi lần đo** của mục này.

## Cơ chế

- Dùng lại check M1b của FIX 3a (`_answer_addresses_question`): cosine e5 giữa câu hỏi và câu evidence mà câu trả lời dựa vào; dưới ngưỡng thì câu trả lời thành NO_ANSWER. Chỉ chuyển SUPPORTED thành NO_ANSWER, không bao giờ ngược lại; câu hỏi nhiều ý không bị kiểm (như M1b).
- M1b làm UAT hồi quy 43 câu vì ngưỡng 0,85 lấy từ bộ giả lập. Bản (ii) khác ở hai điểm:
  1. **Chỉ áp cho câu trả lời đi đường LLM** (`RAG_RESPONSIVENESS_CHECK_ENABLED`); câu trả lời dựng sẵn (route deterministic) không bị kiểm. Route deterministic có kiểu lỗi riêng (D) và để cho bộ phân loại ý định.
  2. **Ngưỡng riêng** (`RAG_RESPONSIVENESS_MIN_SIMILARITY`), lấy từ phần UAT đi đường LLM, không từ bộ giả lập.
- Mỗi cosine đã tính được đếm theo ô 0,01 trên `GET /metrics`; runner UAT ghi `evidence_similarity` và `answer_route` cho từng câu.

## Đợt hiệu chỉnh (chỉ UAT)

- Cấu hình, cùng job, 2 lượt xen kẽ: `base`; `probe` = `EVAL_QUESTION_EVIDENCE_SIMILARITY=true`, `EVAL_QUESTION_EVIDENCE_MIN_SIMILARITY=0.0` (tính cosine cho mọi câu, không chặn câu nào).
- `probe` không được đổi trạng thái hay citation của câu nào so với `base` (chỉ tính khác dao động đã thấy ở cả 2 lượt). Nếu đổi: dừng, báo.
- **Quy tắc chọn ngưỡng `t`:**
  - S = các câu UAT có `answer_route = llm` ở cả 2 lượt `probe`, đúng (proxy) ở cả 2 lượt, và có `evidence_similarity` ở cả 2 lượt; giá trị của mỗi câu là ô thấp hơn trong 2 lượt.
  - `t` = giá trị nhỏ nhất của S. Không câu đúng nào của phần LLM bị chặn; không dùng dung sai 1 câu để đẩy ngưỡng lên.
  - Nếu S có dưới 10 câu: không đủ để hiệu chỉnh; báo owner, không đo tiếp.
- Báo cùng lúc: phân bố S, các câu UAT đi đường LLM nhưng sai và giá trị của chúng, số câu đi route deterministic (không bị kiểm).

## Đợt đo (sau khi có `t`)

- Cấu hình, cùng job, 2 lượt xen kẽ: `base`; `resp` = `EVAL_RESPONSIVENESS=true`, `EVAL_RESPONSIVENESS_MIN=t`.
- Bộ: UAT (báo tách route), RBAC, relevance, FR v1, FR v2, compound.
- **Chọn theo DEC-013**, "trả lời nhầm giá trị" tính là trả lời sai (owner, 2026-11-14): 0 rò rỉ; UAT không hồi quy quá 1 câu, và phần đi đường LLM được báo riêng; trả lời sai không tăng ở bộ nào; thắng khi không tệ hơn ở bộ nào và tốt hơn ở ít nhất một bộ (ít trả lời sai hơn, rồi nhiều câu đúng hơn). Báo số ca vào nhánh (`question_evidence_dissimilar`).
- Thắng thì bật `RAG_RESPONSIVENESS_CHECK_ENABLED` với `t`; không thì giữ tắt.

## Kết quả hiệu chỉnh (Actions run `43498479733`, commit `736f854`, 2026-11-14)

- UAT 100/100 ở cả `base` và `probe`, 2 lượt: **75 câu đi route deterministic, 25 câu đi đường LLM**, đúng hết. `probe` không đổi trạng thái hay citation câu nào (Q033, Q096 chỉ đổi chữ).
- S = 18 câu (đi LLM, đúng, có cosine ở cả 2 lượt). Phân bố (ô thấp hơn của 2 lượt): 0,81 (Q007); 0,82 (Q002, Q034); 0,84 (Q004, Q009, Q011, Q012); 0,85 (Q008, Q014, Q015, Q033); 0,86 (Q055, Q058, Q091, Q095); 0,87 (Q092); 0,89 (Q094); 0,90 (Q070).
- 7 câu đi LLM không có cosine (Q013, Q018, Q071, Q073, Q096, Q097, Q100: câu hỏi nhiều ý hoặc không tìm được câu evidence), nên check không chạm chúng.
- Route deterministic: 74/75 câu có cosine, thấp nhất 0,78; (ii) không kiểm route này.
- **t = 0,81.** Ngưỡng cũ 0,85 của M1b chặn 7/18 câu đúng của phần LLM, cộng các câu deterministic dưới 0,85: khớp với 43 câu hồi quy của FIX 3a.
- Commit hiệu chỉnh chưa có `RAG_COMPLETENESS_NUMBER_NORMALIZATION_ENABLED` (bật sau, PR #25); flag đó chỉ đổi FR2-E01 trong đợt của nó, không đổi câu UAT nào.

## Kết quả đợt đo (Actions, commit `6ea71d5`, t = 0,81, 2026-11-14)

Ô: đúng / từ chối sai / trả lời sai / sai (nhầm giá trị); hai lượt mỗi bên giống hệt nhau. 0 rò rỉ ở mọi ô.

| Bộ (run) | `base` | `resp` | Thay đổi ở cả 2 lượt |
|---|---|---|---|
| UAT (`43517483428`) | 100/0/0/0; deterministic 75/75, LLM 25/25 | 99/1/0/0; deterministic 75/75, LLM 24/25 | Q071 đúng → từ chối sai |
| RBAC (`43517521598`) | 23/12/0/1 | 22/13/1/0 | RBD-13 control sai → từ chối; **RBD-03 negative đúng → trả lời sai** |
| relevance (`43517558708`) | 17/3/5/0 | **19**/3/**3**/0 | REL-401, REL-403 trả lời sai → đúng |
| FR v1 (`43517595504`) | 13/1/6/0 | = | |
| FR v2 (`43517631924`) | 15/4/5/0 | 14/6/4/0 | FR2-E05 trả lời sai → đúng; FR2-E01, E03 (câu hỏi tiếng Anh) đúng → từ chối |
| compound (`43517669294`) | 4/3/4/1 | = | |

Trả lời sai (cả hai nhóm) theo bộ: UAT 0 → 0, RBAC 1 → 1, relevance 5 → 3, FR v1 6 → 6, FR v2 5 → 4, compound 5 → 5. Câu đúng: UAT −1, RBAC −1, relevance +2, FR v2 −1.

**Áp quy tắc:** không rò rỉ, trả lời sai không tăng ở bộ nào, UAT trong dung sai 1 câu. Nhưng ở UAT và RBAC, `resp` có cùng số trả lời sai và **ít hơn 1 câu đúng**, ổn định ở cả 2 lượt: tệ hơn `base` ở hai bộ. **Không thắng; `RAG_RESPONSIVENESS_CHECK_ENABLED` giữ tắt.** Code và bộ đếm cosine được merge (flag tắt), như F.

**Hai điều đợt đo cho thấy:**
1. **NO_ANSWER do check tạo ra chưa phải là điểm dừng.** RBD-03 negative: check chặn câu trả lời đầu (bộ đếm `question_evidence_dissimilar` = 5 trên RBAC), pipeline sinh lại, và một câu lạc đề từ tài liệu được phép ("báo cho lễ tân tầng 1", RBAC-ORG-001, không rò rỉ) qua được ngưỡng. Muốn check chỉ chặn mà không mở đường trả lời khác, câu bị chặn phải dừng ở NO_ANSWER, không đi vào vòng thử lại.
2. **Hiệu chỉnh chỉ phủ các câu tính đúng một cosine.** Q071 không có trong S vì check chạy nhiều lần cho câu này (mỗi lần sinh một lần); một lần sinh trung gian dưới 0,81 đã bị chặn. Câu hỏi tiếng Anh (E01, E03) có cosine thấp hơn với evidence tiếng Việt; UAT gần như không có câu loại này nên ngưỡng lấy từ UAT không phủ chúng.


## Hiệu chỉnh lại trên mọi lần sinh (viết 2026-11-14, trước khi đo)

- **Lý do:** đợt đầu chỉ lấy câu có đúng một cosine; Q071 bị chặn ở một lần sinh trung gian. Với điểm dừng (`respt`), chặn ở **bất kỳ** lần sinh LLM nào cũng là NO_ANSWER, nên ngưỡng phải nằm dưới mọi cosine của mọi lần sinh LLM của các câu đúng.
- **Thu thập:** bộ đếm cosine giờ tách route (`llm` / `local`); runner UAT ghi `evidence_similarities` = mọi cosine trên bản nháp LLM của câu đó, kể cả lần trung gian. Đợt hiệu chỉnh: chỉ UAT, `base` và `probe` (`EVAL_QUESTION_EVIDENCE_SIMILARITY=true`, `EVAL_QUESTION_EVIDENCE_MIN_SIMILARITY=0.0`), 2 lượt.
- **Quy tắc chọn t mới:** S' = các câu UAT đi đường LLM ở cả 2 lượt `probe`, đúng ở cả 2 lượt, có ít nhất một cosine LLM; giá trị của mỗi câu là cosine **nhỏ nhất trên mọi lần sinh của cả 2 lượt**. t = min(S'). Không câu đúng nào bị chặn ở bất kỳ lần sinh nào. Ghi t và |S'| trước đợt đo.
- **Giới hạn:** UAT chỉ có ~25 câu đi đường LLM, không có câu tiếng Anh; câu hỏi nhiều ý không được kiểm (check bỏ qua chúng), nên t không được hiệu chỉnh cho kiểm độ đáp ứng trên từng ý của (iv).

## Đợt đo cuối của giai đoạn 1 (viết trước khi đo)

- Cấu hình, cùng job, 2 lượt xen kẽ, 6 bộ (UAT tách route, RBAC, relevance, FR v1, FR v2, compound): `base` (mặc định hiện tại); `respt` = `EVAL_RESPONSIVENESS=true`, `EVAL_RESPONSIVENESS_MIN=t`, `EVAL_RESP_TERMINAL=true`; `respt_cpa` = `respt` + `EVAL_COMPOUND_PARTIAL=true` (trả lời một phần, mỗi ý LLM được giữ phải qua kiểm độ đáp ứng với cùng t; ý không đạt → câu "chưa xác minh được"; không ý nào đạt → NO_ANSWER, không thử lại).
- **DEC-013, "nhầm giá trị" tính là trả lời sai:** 0 rò rỉ; UAT không hồi quy quá 1 câu, phần LLM báo riêng; trả lời sai không tăng ở bộ nào; thắng khi không tệ hơn `base` ở bộ nào (ít trả lời sai hơn trước, rồi nhiều câu đúng hơn) và tốt hơn ở ít nhất một bộ.
- Hai cấu hình cùng thắng: chọn cái không thua cái kia ở bộ nào; `respt_cpa` chỉ được bật cùng `respt`. Không cái nào thắng: mọi flag giữ tắt.
- Báo riêng: Q071, RBD-03, CP1-R03, CP1-P01/P05/P06, FR2-E01/E03, và các bộ đếm `terminal_block`, `claim_unresponsive`, `excerpt_fallback`.

### Kết quả hiệu chỉnh lại (Actions run `43607041349`, commit `06856ee`, ghi trước đợt đo)

- UAT `base` 98-99/1/0/0-1 và `probe` 99/1/0/0, 2 lượt; route: 75 deterministic, 25 LLM. `probe` không đổi trạng thái hay citation câu nào so với `base`, trừ Q002 dao động ở `base` lượt 1.
- **Q071 từ chối sai ở cả `base` lẫn `probe`, cả 2 lượt** (3 lần sinh mỗi lượt, mọi cosine 0,80). Ở các đợt trước nó đúng ở `base`. Code của commit này chỉ đổi hành vi khi bật cả (iv) và kiểm độ đáp ứng, nên đây là dao động giữa các job, ổn định trong một job; Q071 không vào S'.
- **S' = 20 câu** (đi LLM, đúng ở cả 2 lượt, có cosine). Cosine nhỏ nhất trên mọi lần sinh của 2 lượt: 0,80 (Q018, có lần sinh trung gian); 0,81 (Q007, Q012); 0,82 (Q002, Q033, Q034); 0,84 (Q004, Q009, Q011, Q073); 0,85 (Q008, Q014, Q015, Q091); 0,86 (Q055, Q058, Q095); 0,87 (Q092); 0,89 (Q094); 0,90 (Q070). Q018 và Q073 có 2 lần sinh mỗi lượt; các câu khác 1.
- 4 câu đi LLM, đúng, không có cosine (Q013, Q096, Q097, Q100): câu hỏi nhiều ý, check không chạm.
- **t mới = 0,80.** Đợt đo dùng `EVAL_RESPONSIVENESS_MIN=0.80`.

### Kết quả đợt đo cuối của giai đoạn 1 (Actions, commit `a4dbfab`, t = 0,80, 2026-11-15)

Mỗi bộ một job, 3 cấu hình, 2 lượt; hai lượt giống hệt nhau ở mọi ô. Ô: đúng / từ chối sai / trả lời sai / sai (nhầm giá trị). 0 rò rỉ ở mọi ô.

| Bộ (run) | `base` | `respt` (t = 0,80) | `respt_cpa` |
|---|---|---|---|
| UAT (`43617744818`) | 100/0/0/0; deterministic 76, LLM 24 | = | = |
| RBAC (`43617769586`) | 23/12/0/1 | 23/13/0/**0** (RBD-13 sai → từ chối) | như `respt` |
| relevance (`43617795124`) | 17/3/5/0 | **18**/3/**4**/0 (REL-403 → đúng) | như `respt` |
| FR v1 (`43617819390`) | 13/1/6/0 | = | = |
| FR v2 (`43617842031`) | 15/4/5/0 | 14/6/**4**/0 (E05 → đúng; E01, E03 → từ chối) | như `respt` |
| compound (`43617865245`) | 4/5/2/1 | = | 7/1/**3**/1 (P01, P03, P05, P06 → đúng; **R03 → trả lời sai**) |

**Các câu owner hỏi:**
- **Q071:** đúng ở cả 3 cấu hình, cả 2 lượt. Với t = 0,80, các lần sinh của nó (0,80) không bị chặn.
- **RBD-03 negative:** từ chối đúng ở cả 3 cấu hình (ở `base` của job này nó không bị trả lời sai).
- **CP1-R03:** từ chối ở `base` và `respt`; **trả lời sai ở `respt_cpa`**. Ý 1 ("mức chi hội thảo chung") có cosine ≥ 0,82 với "hội thảo ở nước ngoài, viện đài thọ mức nào", tức trên t: cosine e5 không phân biệt được "chung" và "ở nước ngoài".
- **CP1-P01, P05, P06** (và P03): từ chối sai ở `base`/`respt`, **đúng** ở `respt_cpa`.
- **FR2-E01, FR2-E03:** từ chối sai ở `respt` và `respt_cpa` (câu hỏi tiếng Anh, ngưỡng lấy từ UAT tiếng Việt).
- Bộ đếm (`respt_cpa`, compound, lượt 1): `compound_partial_answer` 5, `terminal_block` 2, `claim_unresponsive` 0; `excerpt_fallback` 3 ở mọi cấu hình của compound.

**Áp quy tắc (viết trước khi đo):**
- **`respt` thắng:** tốt hơn `base` ở RBAC, relevance, FR v2 (ít trả lời sai hơn); bằng ở UAT, FR v1, compound; 0 rò rỉ. **Bật mặc định: `RAG_RESPONSIVENESS_CHECK_ENABLED=true`, `RAG_RESPONSIVENESS_MIN_SIMILARITY=0.80`, `RAG_RESPONSIVENESS_BLOCK_TERMINAL_ENABLED=true`.**
- **`respt_cpa` không thắng:** trả lời sai tăng ở compound (3 → 4, CP1-R03). `RAG_COMPOUND_PARTIAL_ANSWER_ENABLED` giữ tắt.
- **Giới hạn:** t = 0,80 dựa trên 20 câu UAT tiếng Việt đi đường LLM với qwen2.5:3b; không có câu tiếng Anh (E01, E03 mất). Đổi model hay corpus phải hiệu chỉnh lại (ADR 0003).
