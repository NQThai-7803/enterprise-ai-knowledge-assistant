# FIX 3a: câu trả lời sai (M2, M1)

Nhánh `feat/fix-3a-false-answers`. Chẩn đoán: `docs/eval/runs/fix3-diagnosis.md` (run `42571829930`). Mọi thay đổi nằm sau flag, mặc định tắt cho tới khi đợt đo dưới đây quyết định.

## Flag

| Flag | Cơ chế | Hành vi khi bật |
|---|---|---|
| `RAG_REFUSAL_PHRASES_EXTENDED_ENABLED` | M2 | REL-402 nhận thêm cụm từ chối sinh theo ngữ pháp: `không`/`chưa` + (`được`) + động từ nêu (`nêu`, `đề cập`, `quy định`, `nói rõ`, `cụ thể hóa`, `ghi rõ`, `xác định`, `đưa ra`, `cung cấp`), cùng `không/chưa có thông tin/dữ liệu`. Có đủ ba dạng: có dấu, không dấu (sinh tự động bằng `fold_text`), và tiếng Anh (`not specified`, `does not mention`, ...). |
| `RAG_QUESTION_HEAD_IN_EVIDENCE_ENABLED` | M1a | Lấy cụm được hỏi: chuỗi từ nội dung đứng sát từ để hỏi, trong mệnh đề chứa từ để hỏi (tách tại `thì`, dấu phẩy, chấm phẩy). Bỏ từ loại (`loại`, `kiểu`, `hạng`, ...), giữ 2 từ cuối, giữ dấu. Nếu evidence được cite không chứa cụm này thì trả NO_ANSWER. Chưa có bộ gán nhãn từ loại, nên "danh từ trung tâm" ở đây là phần cụ thể nhất của cụm được hỏi, và có thể kết thúc bằng một động từ. |
| `RAG_QUESTION_EVIDENCE_SIMILARITY_ENABLED`, `RAG_QUESTION_EVIDENCE_MIN_SIMILARITY` | M1b | Cosine e5 (`query:` là câu hỏi, `passage:` là câu evidence chung nhiều từ nhất với câu trả lời). Dưới ngưỡng thì trả NO_ANSWER. |

Chỉ áp cho câu hỏi có một nhu cầu thông tin. Mỗi lần một nhánh chặn câu trả lời, counter `refusal_phrase_extended`, `question_head_missing` hoặc `question_evidence_dissimilar` tăng 1 (`branch_counters` trong metadata của runner).

## Ngưỡng M1b, ghi trước khi đo đợt chính

Tool: `scripts/eval/calibrate_question_evidence_similarity.py`, trên `answer_relevance_dev_v1` và `false_refusal_dev_v1` (25 câu phải trả lời, 20 câu phải từ chối). Dùng provider e5 của app (CPU, local).

- Câu phải trả lời: cosine giữa câu hỏi và câu chứa fact, **0,858–0,948**.
- Câu phải từ chối: cosine cao nhất giữa câu hỏi và mọi câu của tài liệu trong bộ, **0,819–0,908**.
- **Quy tắc:** lấy giá trị cao nhất, làm tròn xuống 0,01, mà vẫn giữ mọi câu phải trả lời ở trên ngưỡng. **Ngưỡng = 0,85** (câu thấp nhất là 0,858). Đây là mặc định của `RAG_QUESTION_EVIDENCE_MIN_SIMILARITY`.
- **Lý do và giới hạn:** ngưỡng chọn để không tạo thêm câu từ chối sai trên dev. Hai phân bố chồng lấn nhiều: chỉ 2/20 câu phải từ chối nằm dưới ngưỡng, khi tính theo câu gần nhất trong tài liệu. Tính theo câu mà baseline thật sự đã chép, 5 trong 6 câu trả lời sai của `false_refusal_dev_v1` có cosine 0,858–0,908, đều trên ngưỡng. **Dự kiến M1b ở ngưỡng này thay đổi rất ít.** Không chỉnh ngưỡng theo kết quả của đợt đo.

## Đợt đo và quy tắc chọn (DEC-011, DEC-013, viết trước khi đo)

**Cấu hình:** trên GitHub Actions, mỗi bộ một job, 2 lượt xen kẽ mỗi cấu hình.

| Cấu hình | Flag bật |
|---|---|
| `base` | không flag nào |
| `m2` | M2 |
| `m1a` | M1a |
| `m1b` | M1b |
| `m2m1a` | M2 + M1a |
| `m2m1b` | M2 + M1b |

- **Hai cấu hình gộp đều chạy trong cùng đợt,** vì DEC-011 không cho thêm cấu hình sau khi đợt đo đã xong.
- **Bộ đo:** UAT Q001-Q100 (proxy), RBAC dev (API và retrieval), `answer_relevance_dev_v1`, `false_refusal_dev_v1`.

**Quy tắc chọn:**

1. **Bắt buộc với mỗi cấu hình:**
   - 0 rò rỉ;
   - UAT không hồi quy (dung sai 1 câu theo `eaka-rag-change-guard`);
   - trả lời sai không tăng ở bất kỳ bộ nào.
2. **So với `base`, từng bộ một:** (a) ít trả lời sai hơn, rồi (b) nhiều câu đúng hơn. Một cấu hình chỉ thắng khi không tệ hơn ở mọi bộ và tốt hơn ở ít nhất một bộ. Chỉ tính thay đổi xuất hiện ở cả 2 lượt, và báo theo id mọi câu bị tệ đi.
3. **"Phương án M1 tốt hơn"** là phương án thắng `base`, và không thua phương án M1 kia ở bộ nào khi so cùng thứ tự (a), (b). Nếu cả hai cùng thắng nhưng không phương án nào trội ở mọi bộ, owner quyết định.
4. **Cấu hình được bật mặc định:** trong các cấu hình thắng `base`, lấy cấu hình trội ở mọi bộ so với các cấu hình còn lại. Nếu không có cấu hình nào như vậy, owner quyết định. Các flag giữ lại để rollback.
5. Held-out v2 không dùng (DEC-012).
