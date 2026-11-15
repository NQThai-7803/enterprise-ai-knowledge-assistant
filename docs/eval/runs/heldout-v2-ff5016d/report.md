# Held-out v2: kết quả (owner chấm)

Người chấm: owner (NQThai-7803). Lượt đo: 43701804785 (ff5016d).

**Sự việc phải nêu (DEC-022):** ngày 2026-11-11 owner đã chạy tay 20 câu held-out v2 trên hệ thống, ngoài quy trình DEC-012. Bản ghi lần chạy đó không có trong repo và không được dùng để thiết kế bản sửa nào; chỉ ba lỗi hiển thị chung (D2) được lấy từ đó. Vì vậy đây không phải lần đầu hệ thống gặp bộ câu này.

**Lần chạy trước (run #1, Actions `43697066034`):** dừng ở bước kiểm Ollama trước câu đầu tiên; 0 câu held-out được gửi tới hệ thống; artifact không được dùng để chấm (`docs/design/heldout-v2-release.md`).

Nhãn lượt 2 để trống được lấy từ lượt 1 chỉ khi hai lượt giống hệt nhau (quy tắc của held-out v1): 18 câu.

| Nhóm | Lượt | Số câu | PASS | PARTIAL | FAIL | LEAK | Trả lời sai | Từ chối sai |
|---|---|---:|---:|---:|---:|---:|---|---|
| gần UAT (e5 ≥ 0,90) | run1 | 9 | 0 | 5 | 4 | 0 | - | HO2-003, HO2-008, HO2-018 |
| gần UAT (e5 ≥ 0,90) | run2 | 9 | 0 | 6 | 3 | 0 | - | HO2-003, HO2-008 |
| còn lại | run1 | 11 | 2 | 0 | 9 | 0 | - | HO2-002, HO2-004, HO2-009, HO2-011, HO2-013, HO2-014, HO2-016 |
| còn lại | run2 | 11 | 2 | 0 | 9 | 0 | - | HO2-002, HO2-009, HO2-011, HO2-013, HO2-014, HO2-016 |
| tất cả | run1 | 20 | 2 | 5 | 13 | 0 | - | HO2-002, HO2-003, HO2-004, HO2-008, HO2-009, HO2-011, HO2-013, HO2-014, HO2-016, HO2-018 |
| tất cả | run2 | 20 | 2 | 6 | 12 | 0 | - | HO2-002, HO2-003, HO2-008, HO2-009, HO2-011, HO2-013, HO2-014, HO2-016 |

Nhóm gần UAT đo gần với bộ dev nên dễ được lợi từ việc tinh chỉnh trên UAT; nhóm còn lại là tín hiệu chính.

**Ghi chú từng câu (owner):**
- HO2-020: Câu hỏi trùng nguyên văn câu hỏi gợi ý in trong tài liệu (ND-HR-004 tr. 12); retrieval có thể khớp thẳng vào câu đó.
