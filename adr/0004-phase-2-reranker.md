# ADR 0004: Giai đoạn 2, reranker: sửa thứ tự xếp hạng hay gỡ khỏi pipeline

## Status

Accepted: phương án (b) (owner, 2026-11-15; DEC-025). Phương án (a) giữ lại sau flag `RERANKER_PROVIDER=sentence_transformers`, làm khi có GPU.

## Context

- Pipeline hiện tại: hybrid retrieval → reranker (`RERANKER_ENABLED=true`, provider `sentence_transformers`, model `BAAI/bge-reranker-v2-m3`, rơi về `HeuristicRetrievalReranker` khi không nạp được model) → `_prepare_prompt_retrieval_hits`.
- Trong `_prepare_prompt_retrieval_hits`, toàn bộ pool được xếp lại theo alignment từ vựng (`_rank_hits_for_prompt`), rồi `_merge_retrieval_hits(ranked_hits, reranked_hits)` (`app/services/grounded_answer_service.py`) nối hai danh sách theo thứ tự đó. **Thứ hạng alignment luôn đứng trước**; điểm cross-encoder chỉ xếp phần còn lại. Hợp đồng ở `RAG_DESIGN.md` ("RAG-H2.1 Reranker Authority") nói ngược lại, và code không theo hợp đồng.
- Đo PROMPT 6 (2026-11-12, Actions CPU, 5 bộ dev, `reranker_mode=cross_encoder` đã kiểm ở mọi lượt):
  - `BAAI/bge-reranker-v2-m3` và `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`: **0 câu trả lời thay đổi** ở mọi bộ, 0 `RERANKER_TIMEOUT`.
  - Chi phí: RAM đỉnh của runner 5,9-6,8 GB (base) → 6,2-7,4 GB (bge) / 6,4-7,2 GB (mMiniLM). Trung vị mỗi câu: relevance 11,0-12,3 s → 17,3 s (bge) / 12,0 s (mMiniLM); UAT 1,1 s → **101,6 s** (bge) / 9,8 s (mMiniLM). Cross-encoder chạy trước route deterministic, nên cộng thẳng vào cả 75 câu UAT không gọi LLM.
- Mọi số đo từ trước tới nay chạy ở `lexical_fallback`. Vì thứ tự trên, chúng không lệch so với khi có cross-encoder thật.
- DEC-021: chưa dùng cross-encoder, trên Actions hay production. ADR 0003: giữ 3B trên CPU.

## Phương án (a): sửa thứ tự để điểm cross-encoder có tác dụng, đo mMiniLMv2

- **Thay đổi:** sau reranker, thứ hạng của reranker là chính; alignment chỉ phá hoà, hoặc chỉ dùng khi reranker ở `lexical_fallback`. Một flag, mặc định tắt (ví dụ `RAG_RERANKER_ORDER_FIRST_ENABLED`). Bộ lọc tài liệu khớp từ vựng thấp (cơ chế A) và nhát cắt `group_hits[:2]` (B) giữ nguyên trong lần đầu, để chỉ đo một thay đổi.
- **Model:** `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`; bge-reranker-v2-m3 quá chậm trên CPU (~100 s mỗi câu UAT).
- **Đo:** cùng job, 2 lượt, 6 bộ, cấu hình `base` (`lexical_fallback`), `ce_first` (mMiniLM + thứ tự mới), có thể thêm `ce_only` (mMiniLM, thứ tự cũ, để tách tác dụng của thứ tự). Chọn theo DEC-013, "nhầm giá trị" tính là trả lời sai. Báo RAM, độ trễ theo route.
- **Ưu:** sửa đúng chỗ code lệch hợp đồng; tín hiệu học được thay cho alignment từ vựng, hướng tới NLU (pipeline-loss-fix-plan mục 4); mMiniLM rẻ trên phần đi LLM (relevance +0-1 s mỗi câu).
- **Nhược:** UAT nhiều khả năng hồi quy, vì alignment chính là lý do UAT cao (ablation `lowalign`, `group5`); +~9 s mỗi câu UAT trên CPU nếu reranker vẫn chạy trước route deterministic; model ~470 MB cần cache và tải lúc khởi động; dự đoán từ PROMPT 6 (oracle context gần như không giúp) là trần cải thiện thấp, vì phần mất nằm sau context.
- **Chi phí làm:** nhỏ ở code (một nhánh trong `_prepare_prompt_retrieval_hits`), lớn ở đo (job UAT với cross-encoder dài).

## Phương án (b): gỡ reranker khỏi pipeline

- **Thay đổi:** bỏ bước cross-encoder (`RERANKER_ENABLED=false` mặc định, hoặc gỡ lớp `sentence_transformers` khỏi đường trả lời); giữ `HeuristicRetrievalReranker` / alignment, đúng thứ đang chạy ở mọi số đo. Sửa `RAG_DESIGN.md` cho khớp code: alignment là thứ hạng chính.
- **Đo:** cùng job, 2 lượt, 6 bộ, `base` và `no_reranker`. Kỳ vọng giống từng câu, vì mọi số đo hiện tại đã ở `lexical_fallback`; khác biệt nào cũng phải được giải thích trước khi merge.
- **Ưu:** khớp hành vi đã đo; bỏ phụ thuộc model, tải model và nhánh rơi về (fallback) khỏi đường trả lời; tài liệu nói đúng điều code làm; không thêm độ trễ.
- **Nhược:** bỏ hướng tín hiệu học được ở bước xếp hạng; muốn thử lại cross-encoder sau này phải thêm lại lớp này (interface `RetrievalReranker` vẫn giữ).

## So sánh

| | (a) sửa thứ tự + mMiniLMv2 | (b) gỡ reranker |
|---|---|---|
| Đổi câu trả lời | có thể (mục đích), UAT có rủi ro | kỳ vọng 0 |
| Độ trễ CPU | +~9 s mỗi câu UAT, +0-1 s phần LLM | không đổi hoặc giảm |
| RAM | +0,3-0,5 GB | không đổi hoặc giảm |
| Khớp `RAG_DESIGN.md` | sửa code theo hợp đồng | sửa hợp đồng theo code |
| Rủi ro khớp quá mức dev | thêm một vòng tinh chỉnh trên 6 bộ | không |

## Đề xuất

Làm (b) trước: nó khớp với mọi số đo hiện có, bỏ chi phí không mang lại câu đúng nào, và làm tài liệu đúng với code. Giữ (a) như một thí nghiệm có flag, làm khi có GPU (cùng điều kiện với ADR 0003) hoặc khi bộ phân loại ý định thay route deterministic, vì lúc đó cross-encoder không còn bị cộng vào 75 câu UAT dựng sẵn.
