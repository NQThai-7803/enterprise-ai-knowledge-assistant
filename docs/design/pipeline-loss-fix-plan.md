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
