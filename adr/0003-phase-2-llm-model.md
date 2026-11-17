# ADR 0003: Giai đoạn 2, model sinh câu trả lời: giữ qwen2.5:3b

## Status

Accepted (owner, 2026-11-14). Xét lại khi có GPU từ 8 GB VRAM trở lên.

2026-11-17: đã đo lại với 3 model (DEC-028, mục "Đo lại 2026-11-17" bên dưới). Mặc định chưa đổi; quyết định đổi model chờ owner.

## Context

PROMPT 6 cho thấy phần mất mát chủ yếu nằm sau context: model 3B, validator, check độ đầy đủ và vòng thử lại. Câu hỏi đặt ra: đổi sang qwen2.5:7b có đáng không. Mọi số đo dưới đây chạy trên GitHub Actions (CPU, runner 16 GB RAM, Ollama 0.40.15). Mỗi bộ một job, so với baseline 3B trong cùng job, 2 lượt; hai lượt giống hệt nhau ở mọi ô. Ô: đúng / từ chối sai / trả lời sai (phải từ chối mà trả lời) / sai (nhầm giá trị). 0 rò rỉ ở mọi ô.

### Context gold (oracle), 2026-11-13

| Bộ | 3B, retrieval thật | 3B, oracle | 7B, oracle | Trung vị mỗi câu (3B oracle → 7B oracle) |
|---|---|---|---|---|
| RBAC | 22/12/1/1 | 25/10/1/0 | 26/10/0/0 | 35 s → 106 s |
| relevance | 17/3/5/0 | 16/2/6/1 | 17/2/6/0 | 32 s → 79 s |
| FR v1 | 13/1/6/0 | 13/1/6/0 | 14/2/4/0 | 18 s → 42 s |
| FR v2 | 13/5/5/1 | 15/4/5/0 | 18/4/2/0 | 27 s → 69 s |

### Retrieval thật, 2026-11-14

| Bộ | 3B | 7B | Trung vị mỗi câu 3B → 7B | RAM đỉnh 7B (còn trống thấp nhất) |
|---|---|---|---|---|
| UAT Q001-Q100 | 98/1/0/1; đường LLM 23/1/0/1 | 98/2/0/0; đường LLM 23/2/0/0 | đường LLM 26,3 s → 53,0 s | 10,9 GB (5,1 GB) |
| RBAC | 22/12/1/1 | 23/13/0/0 | 36,7 s → 103,9 s | 11,3 GB (4,7 GB) |
| relevance | 17/3/5/0 | 16/3/5/1 | 19,7 s → 42,7 s | 11,3 GB (4,7 GB) |
| FR v1 | 13/1/6/0 | 14/2/4/0 | 19,2 s → 41,9 s | 11,3 GB (4,7 GB) |
| FR v2 | 14/5/5/0 | 15/6/3/0 | 30,9 s → 65,4 s | 12,6 GB (3,1 GB) |
| compound | 4/3/4/1 | 4/4/3/1 | 24,0 s → 46,1 s | 13,0 GB (3,0 GB) |

3B dùng khoảng 6-7 GB RAM đỉnh trên cùng runner. Route deterministic (75/100 câu UAT) không gọi LLM, nên không đổi theo model (trung vị 0,8 s).

Run: oracle `43360592606`, `43360618591`, `43360643014`, `43360666643`; retrieval thật `43497256962`, `43493755308`, `43493778732`, `43493803065`, `43493825433`, `43493848355`. Chi tiết: `docs/design/pipeline-loss-fix-plan.md` mục 3.

### Đo lại 2026-11-17 (DEC-028)

Danh sách model và luật chọn được ghi vào DEC-028 trước khi đo.

**Cách đo:**

- Model: `qwen2.5:7b`, `qwen3.5:4b`, `sailor2:8b`, đều Q4_K_M, `num_ctx` 8192.
- Mỗi model chạy ở cả `legacy` và `s3`, trên `natural_dev_v1` và 5 bộ dev; không chạy UAT.
- 2 lượt ở 2 job riêng. Mỗi job có `legacy` + 3B làm mốc.
- Timeout LLM 600 s cho mọi cấu hình.

**Kết quả:** 0 rò rỉ ở mọi ô. Tổng trên 6 bộ, ghi lượt a / lượt b:

| Tổ hợp | Đúng | Từ chối sai | Trả lời sai + sai giá trị | DEC-026/027 so với `legacy` + 3B |
|---|---|---|---|---|
| `legacy` + 3B (mốc) | 75 / 75 | 34 / 35 | 28 / 27 | — |
| `legacy` + 7B | 77 / 76 | 38 / 39 | 22 / 22 | không thắng (từ chối sai ở 5 bộ dev tăng thật) |
| `s3` + 7B | 110 / 114 | 7 / 8 | 20 / 15 | **thắng** |
| `legacy` + `qwen3.5:4b` | 78 / 79 | 31 / 33 | 28 / 25 | **thắng** (từ chối sai trên natural giảm thật: 2/4 so với 7/7) |
| `s3` + `qwen3.5:4b` | 117 / 116 | 5 / 11 | 15 / 10 | **thắng** |
| `legacy` + `sailor2:8b` | 65 / 64 | 57 / 57 | 15 / 16 | không thắng (từ chối sai trên natural +7) |
| `s3` + `sailor2:8b` | 101 / 103 | 19 / 19 | 17 / 15 | không thắng (từ chối sai trên natural +11/+10) |

So trực tiếp, `s3` + `qwen3.5:4b` và `s3` + 7B **hòa nhau** ở mọi chỉ số theo DEC-027. Cả hai đều hơn `legacy` + `qwen3.5:4b` và hơn `s3` + 3B.

**Phần cứng** (CPU 4 vCPU, RAM 15,6 GiB, không có GPU):

- RAM của model lấy từ log Ollama (trọng số + KV 8192 + compute).
- RAM đỉnh runner tính cả stack: Postgres, Redis, API, worker, embedding và Ollama.
- VRAM là ước tính (RAM của model cộng phần runtime), chưa đo.
- Độ trễ là trung vị của tỉ số độ trễ trung vị so với 3B, tính trên từng bộ.

| Model | RAM của model | RAM đỉnh runner (`legacy` / `s3`) | Độ trễ so với 3B (`legacy` / `s3`) | VRAM ước tính | Giấy phép |
|---|---|---|---|---|---|
| `qwen2.5:3b` | 2,3 GiB | 5,8-6,7 / 5,9-7,8 GB | 1 / 1 | ~3 GB | **Qwen Research: không cho dùng thương mại** nếu không có giấy phép riêng của Alibaba Cloud |
| `qwen2.5:7b` | 5,1 GiB | 8,8-10,1 / 9,0-11,9 GB | ×2,2 / ×2,1 | ~6 GB | Apache 2.0 |
| `qwen3.5:4b` | 2,9 GiB + bộ mã hóa ảnh tới 0,85 GiB | 8,1-12,1 / 8,6-14,0 GB | ×1,6 / ×2,7 | ~4,5 GB | Apache 2.0 |
| `sailor2:8b` | 5,7 GiB | 9,6-10,8 / 9,9-13,8 GB | ×4,7 / ×3,0 | ~6,5 GB | Apache 2.0 |

- Với `s3` + `qwen3.5:4b`, RAM trống thấp nhất còn 1,9 GB: máy CPU 16 GB chạy được nhưng sát giới hạn.
- Ba câu ND-002, ND-003, ND-014 vẫn sai với mọi model.
- ND-011 đúng với `s3` + 7B và `s3` + `qwen3.5:4b`. ND-019 đúng với `s3` + `qwen3.5:4b` và `s3` + `sailor2:8b`.
- Oracle với `qwen3.5:4b` (5 bộ dev, 1 lượt): `s3` + `qwen3.5:4b` đúng 104/117 khi có context gold, còn retrieval thật được 106 / 107. Trên các bộ dev, retrieval thật đã chạm trần. Phần còn lại chủ yếu là trả lời sai ở câu phải từ chối. Trần trên natural_dev_v1 và UAT chưa đo.
- Run và chi tiết: `docs/design/model-comparison.md`.

## Decision

Giữ `qwen2.5:3b` làm model mặc định. Xét lại khi có GPU từ 8 GB VRAM trở lên.

- 7B bớt trả lời sai (tính cả nhầm giá trị) ở 5/6 bộ với retrieval thật: UAT −1, RBAC −2, FR v1 −2, FR v2 −2, compound −1; nhưng thêm 1 ở relevance.
- Câu đúng gần như không tăng (+1 ở RBAC, FR v1, FR v2; −1 ở relevance): phần lớn câu 7B thôi trả lời sai thì thành từ chối.
- Trên CPU, 7B chậm hơn 1,9-2,8 lần (đường LLM của UAT: 53 s mỗi câu) và cần 11-13 GB RAM đỉnh, còn trống chỉ 3 GB trên máy 16 GB. Với phần cứng hiện tại, giá này không đáng với mức cải thiện đó.

## Consequences

- `LLM_OLLAMA_MODEL` giữ `qwen2.5:3b`; eval vẫn đổi được model cho từng cấu hình (`EVAL_LLM_MODEL`).
- Các bản sửa của giai đoạn này phải tự giảm trả lời sai với 3B (validator, độ đáp ứng, câu hỏi ghép), không trông vào model lớn hơn.
- Khi có GPU ≥ 8 GB VRAM: đo lại 7B với cùng 6 bộ, cùng job với 3B, gồm độ trễ và RAM/VRAM, trước khi đổi.
- 2026-11-17: giấy phép của `qwen2.5:3b` (Qwen Research) không cho dùng thương mại nếu không có giấy phép riêng. Ba model ứng viên của DEC-028 đều dùng Apache 2.0.
- 2026-11-17: ngưỡng và prompt chưa được hiệu chỉnh lại cho từng model. Với `qwen3.5:4b`, có những câu trả lời bị bộ kiểm tra claim của s3 từ chối dù nội dung đúng hướng (ví dụ ND-018 "Tháng 01 - 02 của năm" bị loại vì `_numbers_are_contradicted`).
- **Giới hạn đã biết:** ngưỡng độ đáp ứng t = 0,81 (FIX 4 (ii), `docs/eval/runs/fix4-responsiveness.md`) được hiệu chỉnh trên **18 câu** UAT đi đường LLM, với model 3B. Đổi model thì cosine của câu trả lời đổi theo, nên ngưỡng phải hiệu chỉnh lại; 18 câu cũng là mẫu nhỏ, và không có câu hỏi tiếng Anh.
