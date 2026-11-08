# FIX 2c: bật REL-402, đo lại REL-303 theo DEC-013

Chạy từ 2026-11-08 11:21 đến 12:54 trên image `eaka-backend:fix2c` (commit `88067d6`). Mặc định lúc đo: `strict`, nhóm 1 + 2 bật, REL-402 bật. `reranker_mode = lexical_fallback`, model `qwen2.5:3b`, seed cố định. Điểm tự động, không phải chấm tay. Chỉ tính thay đổi xuất hiện ở cả 2 lượt. Đây không phải con số công bố.

## REL-402: bật mặc định

Lần kiểm tra retrieval còn thiếu của đợt FIX 2b (flag REL-402, lượt 2) được chạy lại trên cùng image `dc3fa38` và cùng cấu hình: 18/18 cặp kết luận được, không có chunk bị lộ. Cả 8 lần kiểm tra của đợt đó giờ đều sạch, nên `RAG_PARTIAL_REFUSAL_NO_ANSWER_ENABLED` mặc định là `true`. Đặt `false` để rollback.

## REL-303: danh sách từ để hỏi

Bản trước tính từ "tên" trong "tên gì" là từ nội dung, nên từ chối nhầm Q004. Bản mới bỏ các từ và khung để hỏi trên văn bản còn dấu trước khi bỏ dấu:

- **Từ để hỏi:** ai, gì, nào, đâu, ở đâu, bao nhiêu, bao lâu, bao giờ, mấy, khi nào, lúc nào, tên gì, là gì, là ai, thế nào, như thế nào, ra sao, làm sao, vì sao, tại sao, cách nào.
- **Khung có... không:** "có... không/chưa" khi "không/chưa" đứng cuối câu, các tiểu từ cuối câu, và "phải không", "đúng không", "được không".
- **Hư từ:** cũng bỏ trên văn bản còn dấu.

Làm vậy để từ nội dung có cùng chữ cái khi bỏ dấu vẫn được giữ: "máy" khác "mấy", "sao lưu" khác "vì sao", "cửa" khác "của". "Không" và "chưa" chỉ bị bỏ khi đứng cuối câu, nên "người chưa đủ 12 tháng" vẫn giữ "chưa". Danh sách chỉ có tiếng Việt; từ để hỏi tiếng Anh chưa được xử lý.

## Kết quả theo DEC-013

| Bộ | Baseline: sai / đúng | REL-303 bật: sai / đúng | Thay đổi ở cả 2 lượt |
|---|---:|---:|---|
| `answer_relevance_dev_v1` | 3 / 19 | **2 / 20** | REL-303: trả lời sai thành từ chối đúng |
| RBAC dev | 1 / 22 | 1 / 22 | Không đổi |
| UAT Q001-Q100, khớp proxy | 99/100 | 99/100 | Không đổi; cả 4 lượt giống hệt nhau trên 100 câu |

- **Rò rỉ:** 0 qua API và 0 ở tầng retrieval; cả 4 lần kiểm tra đều 18/18 cặp kết luận được.
- **Q004:** không còn bị từ chối nhầm.
- **Theo DEC-013:** đạt mọi điều kiện bắt buộc. Câu sai không tăng ở bộ nào. Bộ dev mới tốt hơn, RBAC bằng nhau.

**Mặc định chưa đổi:** yêu cầu lần này chỉ là đo. Lưu ý từ DEC-013 vẫn áp dụng: RBD-04 và RBD-05 đúng ở baseline là nhờ lỗi bỏ dấu.

## Bộ đếm nhánh 4a

| Bộ | Baseline | REL-303 bật |
|---|---|---|
| Bộ dev mới | 12 lần vào nhánh, 0 lần flag sẽ đổi nguồn | 14, 0 |
| RBAC | 31, 1 | 33, 0 |
| UAT | 14, 0 | 14, 0 |

## Độ tin cậy

- **Cùng đợt theo DEC-011:** cùng image, xen kẽ baseline và REL-303. `artifacts/fix2c/batch.log` có 40 dòng, tất cả cùng thời điểm khởi động Ollama `2026-11-08T10:57:47`.
- **Hợp lệ:** 0 INFRA_ERROR, câu chậm nhất 54,8 giây.
- **Held-out v2:** không được chạy và không được dùng cho bản sửa này (DEC-012).

## Giới hạn

- **Ngưỡng 0,6 và cửa sổ 15 từ vẫn chỉ dựa trên vài ca dev.** REL-303 là ca duy nhất được cải thiện.
- **Chưa đo REL-303 cùng các flag khác bật;** REL-103 vẫn tắt.
