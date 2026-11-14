# ADR 0003: Giai đoạn 2, model sinh câu trả lời: giữ qwen2.5:3b

## Status

Accepted (owner, 2026-11-14). Xét lại khi có GPU từ 8 GB VRAM trở lên.

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

## Decision

Giữ `qwen2.5:3b` làm model mặc định. Xét lại khi có GPU từ 8 GB VRAM trở lên.

- 7B bớt trả lời sai (tính cả nhầm giá trị) ở 5/6 bộ với retrieval thật: UAT −1, RBAC −2, FR v1 −2, FR v2 −2, compound −1; nhưng thêm 1 ở relevance.
- Câu đúng gần như không tăng (+1 ở RBAC, FR v1, FR v2; −1 ở relevance): phần lớn câu 7B thôi trả lời sai thì thành từ chối.
- Trên CPU, 7B chậm hơn 1,9-2,8 lần (đường LLM của UAT: 53 s mỗi câu) và cần 11-13 GB RAM đỉnh, còn trống chỉ 3 GB trên máy 16 GB. Với phần cứng hiện tại, giá này không đáng với mức cải thiện đó.

## Consequences

- `LLM_OLLAMA_MODEL` giữ `qwen2.5:3b`; eval vẫn đổi được model cho từng cấu hình (`EVAL_LLM_MODEL`).
- Các bản sửa của giai đoạn này phải tự giảm trả lời sai với 3B (validator, độ đáp ứng, câu hỏi ghép), không trông vào model lớn hơn.
- Khi có GPU ≥ 8 GB VRAM: đo lại 7B với cùng 6 bộ, cùng job với 3B, gồm độ trễ và RAM/VRAM, trước khi đổi.
- **Giới hạn đã biết:** ngưỡng độ đáp ứng t = 0,81 (FIX 4 (ii), `docs/eval/runs/fix4-responsiveness.md`) được hiệu chỉnh trên **18 câu** UAT đi đường LLM, với model 3B. Đổi model thì cosine của câu trả lời đổi theo, nên ngưỡng phải hiệu chỉnh lại; 18 câu cũng là mẫu nhỏ, và không có câu hỏi tiếng Anh.
