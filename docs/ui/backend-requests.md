# Yêu cầu backend từ phiên UI

File này chỉ phiên UI ghi. Phiên backend trả lời bằng PR/commit cập nhật `API_SPEC.md`.
Phiên UI chỉ dùng trường/endpoint mới SAU KHI nó có trên `main` và đã merge `main` vào `feat/ui-redesign`.

Ưu tiên: **Bắt buộc** (chặn một tính năng đã có trong thiết kế), **Nên có** (làm UI đúng thiết kế hơn), **Tùy chọn** (nâng cấp, UI vẫn chạy được nếu không có).

Tình trạng 17/11/2026: BR-1 → BR-9 đều ở trạng thái CHỜ OWNER CHUYỂN.

---

### BR-1: Thông tin phiên bản tài liệu (document_code, document_version, effective_from, effective_to)
- Ưu tiên: **Bắt buộc**
- Màn hình / file frontend: Upload (`features/documents/DocumentUploadPage.tsx`, `api/client.ts` → `documents.upload`), Documents/DocumentDetail (`api/types.ts` → `DocumentItem`), Chat (mã tài liệu trên citation, lấy qua detail).
- Cần gì từ backend:
  1. Ghi vào `API_SPEC.md` §7 `POST /documents/upload` các field form mà code backend đã nhận: `document_code` (str ≤ 128), `document_version` (str ≤ 64), `effective_from` / `effective_to` (date `YYYY-MM-DD`, bắt buộc `effective_to >= effective_from`). Ghi rõ mã lỗi 422 khi sai (ví dụ `effective_to` trước `effective_from`) để UI hiển thị đúng.
  2. Ghi vào `API_SPEC.md` các trường tương ứng trong response của `GET /documents`, `GET /documents/{id}` và response 202 của upload (`DocumentSafeResponse` đã có): `document_code`, `document_version`, `effective_from`, `effective_to`. Nếu `lifecycle_status` và `supersedes_document_id` cũng được trả về thì ghi luôn (UI chưa dùng, chỉ cần biết để không hiểu nhầm).
  3. Xác nhận quy tắc upload của Manager: được chọn phạm vi nào (PATCH chỉ cho `PRIVATE` hoặc `DEPARTMENT` của chính mình; upload thì spec chưa nói) và `department_id` có bị ép về phòng ban của Manager không.
  4. (Tùy ý) `GET /documents?search=` có tìm theo `document_code` không. Thiết kế đặt placeholder "Tên hoặc mã tài liệu".
  - Ví dụ response:
    ```json
    { "id": "uuid", "title": "…", "document_code": "ND-HR-007", "document_version": "1.0",
      "effective_from": "2026-09-01", "effective_to": null }
    ```
- Hiện API_SPEC nói gì: §7 `POST /documents/upload`: "Fields: `file`, `title`, `description`, `access_scope`, `department_id`." Không có field phiên bản. `GET /documents/{id}` không liệt kê trường nào của phiên bản. Trong code (chỉ đọc): `app/api/v1/documents.py` dòng 72–77 nhận các field trên; `app/schemas/document.py` `DocumentSafeResponse` trả về.
- Có làm đổi hành vi/API hiện tại không: Không. Chỉ ghi lại hành vi đã có. Riêng mục 3 và 4 có thể đòi thay đổi nếu hiện chưa đúng.
- UI tạm thời đang xử lý thế nào: Form upload KHÔNG hiện mục "Thông tin phiên bản", không gửi các field này. Ô tìm kiếm ghi "Tên hoặc tên tệp". Có `TODO(BR-1)` trong code.
- Trạng thái: CHỜ OWNER CHUYỂN

### BR-2: Mở tài liệu tại đúng trang từ citation
- Ưu tiên: **Nên có** (owner đã duyệt đường tạm phía UI, endpoint preview giúp nhẹ hơn)
- Màn hình / file frontend: Chat, panel trích dẫn (`features/chat/ChatPage.tsx`, liên kết "Mở tài liệu tại trang N"). Tham chiếu: `docs/review/bao-cao-kiem-thu-2026-10-28.md` mục 6.2.
- Cần gì từ backend: Một cách để trình duyệt mở PDF ở trang N cho đúng người có quyền xem. Đề xuất `GET /documents/{id}/preview` trả `Content-Disposition: inline`, cùng quy tắc quyền như `/download` (404 `RESOURCE_NOT_FOUND` nếu không được xem, `410 DOCUMENT_FILE_UNAVAILABLE` nếu mất file). Trang N do client gắn `#page=N`, backend không cần xử lý. Nếu backend muốn phương án khác (URL ký tạm thời có hạn), ghi rõ cách dùng vào `API_SPEC.md`. Lý do cần: trình duyệt không gửi được header `Authorization` khi mở link thường, nên không thể mở bằng thẻ `<a>`.
  - Ví dụ: `GET /api/v1/documents/{document_id}/preview` → `200 application/pdf`, `Content-Disposition: inline`.
- Hiện API_SPEC nói gì: §7 cuối: "Not implemented yet: … Preview endpoint. Signed download URLs." `/download` trả `Content-Disposition: attachment`. Citation đã có `document_id` và `page_number` (§8A).
- Có làm đổi hành vi/API hiện tại không: Không, chỉ thêm endpoint.
- UI tạm thời đang xử lý thế nào: Owner đã duyệt (17/11/2026). Liên kết "Mở tài liệu tại trang N" mở tab mới tới route `/documents/:id/view?page=N` của app. Trang này gọi `GET /documents/{id}/download` (có Bearer), tạo `blob:` URL, nhúng vào khung PDF với `#page=N`. Chỉ tới được trang, không tô được câu; nhược điểm: tải cả tệp mỗi lần. Có `TODO(BR-2)` để đổi sang endpoint preview khi có. Tài liệu PNG/JPEG hiện ảnh, bỏ `#page`.
  - Ghi nhận khi làm (17/11/2026): token nằm trong `sessionStorage`, nên liên kết dùng `rel="opener"` để tab mới nhận bản sao token (đã kiểm bằng Playwright). Hệ quả: hai tab dùng chung một refresh token; refresh xoay vòng token (API_SPEC §4), nên nếu tab xem tài liệu phải refresh thì tab gốc sẽ bị đăng xuất ở lần refresh sau. Chỉ xảy ra khi access token sắp hết hạn lúc mở tab. Endpoint preview vẫn cần Bearer nên không gỡ được rủi ro này; URL ký tạm thời (phương án thay thế ở trên) thì gỡ được.
- Trạng thái: CHỜ OWNER CHUYỂN

### BR-3: `grounding_status` trong lịch sử chat và hợp đồng của câu "Chưa xác minh được…" (kèm bản tiếng Anh)
- Ưu tiên: **Nên có**
- Màn hình / file frontend: Chat (`features/chat/ChatPage.tsx` → `MessageBubble`, `AssistantStreamBubble`), `api/types.ts` → `ChatMessage`.
- Cần gì từ backend:
  1. Thêm `grounding_status` (`"ANSWERED"` | `"NO_ANSWER"`) vào mỗi message `ASSISTANT` trong `GET /chat/sessions/{id}` (nullable với message cũ). Hiện chỉ có ở response gửi tin và SSE `message.completed`, nên sau khi tải lại trang UI không biết tin nào là NO_ANSWER.
  2. Ghi vào `API_SPEC.md` rằng câu trả lời `ANSWERED` có thể chứa câu cố định bắt đầu bằng "Chưa xác minh được từ tài liệu bạn được phép truy cập: …" (không có số trích dẫn), để UI hiển thị riêng (chữ xám, không chip). Nguồn trong code: `app/services/grounded_answer_service.py` `_UNVERIFIED_PART_SENTENCE`. Prompt (`app/chat/prompt_builder.py` dòng 189-190, 207-208) còn cho phép bản tiếng Anh "Could not be verified from the documents you can access: …"; cần ghi cả hai vào spec. Nếu backend không muốn cố định câu này, đề xuất trả mảng đoạn có cấu trúc thay vì để UI nhận diện theo chữ.
  - Ví dụ: `{ "id": "uuid", "role": "ASSISTANT", "content": "…", "citations": [], "grounding_status": "NO_ANSWER" }`
- Hiện API_SPEC nói gì: §8: "`grounding_status` is `NO_ANSWER`." và "Assistant `citations` is `[]`." (chỉ trong response gửi tin). `ChatMessage` ở frontend không có `grounding_status`.
- Có làm đổi hành vi/API hiện tại không: Không. Chỉ thêm trường.
- UI tạm thời đang xử lý thế nào: Tin vừa gửi dùng `grounding_status` từ response/SSE. Tin trong lịch sử: coi message ASSISTANT không có citation là "không có nguồn" (suy từ quy tắc NO_ANSWER → `citations = []`), kèm `TODO(BR-3)`. Câu "Chưa xác minh được…" nhận diện theo hai tiền tố đó (Việt và Anh), chỉ ảnh hưởng hiển thị; không khớp thì hiển thị như văn bản thường. Không đổi logic xử lý response.
- Trạng thái: CHỜ OWNER CHUYỂN

### BR-4: Tên phòng ban và tên người dùng cho vai trò không phải Admin
- Ưu tiên: **Nên có**
- Màn hình / file frontend: Profile, DocumentDetail, Upload (Manager), Feedback (`api/types.ts` → `AuthenticatedUser`, `DocumentItem`, `FeedbackReportItem`).
- Cần gì từ backend: Thêm tên hiển thị để UI không phải hiện UUID:
  - `GET /auth/me` và `user` trong login: `department_name` (hoặc `department: { id, name, code }`).
  - `DocumentItem`: `department_name` và `uploaded_by_name`.
  - `FeedbackReportItem` (Admin/Manager): `user_full_name`, `department_name`. Không thêm nội dung câu hỏi/câu trả lời.
  - Cho Manager khi upload: phòng ban của chính mình (tên + id) lấy từ `/auth/me` là đủ.
  - Ví dụ: `"department_id": "uuid", "department_name": "Nhân sự"`.
- Hiện API_SPEC nói gì: §5 `GET /users`: "Requires Admin." §6 `GET /departments`: "Requires Admin." Các response chỉ có `department_id` / `uploaded_by` / `user_id` (UUID). Thiết kế hiện "Phòng ban: Nhân sự", "Người tải lên: Manager Nhân sự".
- Có làm đổi hành vi/API hiện tại không: Không. Chỉ thêm trường. Lưu ý quyền riêng tư: chỉ trả tên trong phạm vi người gọi đã được xem sẵn các bản ghi đó.
- UI tạm thời đang xử lý thế nào: Admin: tra tên qua `GET /departments` và `GET /users` (page_size 100). Vai trò khác: Profile hiện "Đã gán phòng ban" không kèm ID; DocumentDetail hiện "Phòng ban của tài liệu" không kèm tên. Ghi nhận thêm: trang Upload hiện gọi `GET /departments` cho mọi vai trò khi chọn phạm vi Phòng ban, theo spec Manager sẽ nhận 403; UI sẽ xử lý lỗi này nhẹ nhàng cho tới khi có trường mới.
- Trạng thái: CHỜ OWNER CHUYỂN

### BR-5: Số trang của tài liệu
- Ưu tiên: Tùy chọn
- Màn hình / file frontend: Documents, DocumentDetail ("Số trang"), Upload (thẻ tệp đã chọn), `DocumentItem`.
- Cần gì từ backend: `page_count` (int | null) trong `DocumentItem`; null khi chưa xử lý xong. Ví dụ: `"page_count": 13`.
- Hiện API_SPEC nói gì: Không có trường số trang trong `DocumentItem`; `DocumentSafeResponse` (chỉ đọc) cũng chưa có.
- Có làm đổi hành vi/API hiện tại không: Không.
- UI tạm thời đang xử lý thế nào: Bỏ phần "N trang" ở danh sách, chi tiết và thẻ tệp upload. Chỉ hiện kích thước tệp thật. Không đọc PDF phía trình duyệt để đếm trang.
- Trạng thái: CHỜ OWNER CHUYỂN

### BR-6: Sự kiện tiến trình khi trả lời (SSE)
- Ưu tiên: Tùy chọn
- Màn hình / file frontend: Chat (`api/sse.ts`, `features/chat/streamState.ts`, khối chờ câu trả lời). Tham chiếu: báo cáo kiểm thử 28/10 mục 6.4.
- Cần gì từ backend: Thêm sự kiện SSE `stage` trong lúc chờ kiểm tra (chiến lược `buffer_after_validation` chưa phát gì đến khi xong), ví dụ `{ "stage": "retrieving" | "generating" | "validating" }`.
- Hiện API_SPEC nói gì: §8 stream: các sự kiện hiện có là `stream.started`, `heartbeat`, `message.delta`, `citations.ready`, `message.completed`, `stream.error`, `stream.cancelled`. Không có sự kiện tiến trình.
- Có làm đổi hành vi/API hiện tại không: Không, thêm sự kiện mới; client cũ bỏ qua sự kiện lạ.
- UI tạm thời đang xử lý thế nào: Một dòng trạng thái "Đang tìm và kiểm tra nguồn…" theo `connecting/started`. Không dựng bộ đếm giờ giả cho 3 bước trong thiết kế, không ghi tên mô hình cố định.
- Trạng thái: CHỜ OWNER CHUYỂN

### BR-7: Giai đoạn xử lý tài liệu
- Ưu tiên: Tùy chọn
- Màn hình / file frontend: DocumentDetail, Documents (`DocumentStatusResponse`, `GET /documents/{id}/status`).
- Cần gì từ backend: Trường `stage` (ví dụ `extracting` | `chunking` | `embedding`) khi `status = PROCESSING`.
- Hiện API_SPEC nói gì: §7 `GET /documents/{id}/status`: "Returns `id`, `status`, sanitized `error_message`, and `updated_at`."
- Có làm đổi hành vi/API hiện tại không: Không.
- UI tạm thời đang xử lý thế nào: Dòng thời gian 3 bước suy từ `status` (Đã tải lên → Đang xử lý → Sẵn sàng hoặc Lỗi kèm `error_message`), không hiện phần trăm hay tên thư viện như artboard.
- Trạng thái: CHỜ OWNER CHUYỂN

### BR-8: Ví dụ JSON cho các endpoint giám sát Admin
- Ưu tiên: Tùy chọn
- Màn hình / file frontend: SystemStatus (`features/system/SystemStatusPage.tsx`).
- Cần gì từ backend: Ghi ví dụ JSON response cho `GET /admin/health`, `/admin/providers`, `/admin/version`, `/admin/system` (hiện chỉ có mô tả chữ) để UI định kiểu được và hiện nhà cung cấp LLM, mô hình, phiên bản cho Admin.
- Hiện API_SPEC nói gì: "TASK-032 Admin Monitoring API" chỉ có mô tả chữ, không có JSON mẫu. Trang System hiện ghi "Not exposed by current backend API" cho provider, đã lỗi thời so với TASK-032.
- Có làm đổi hành vi/API hiện tại không: Không.
- UI tạm thời đang xử lý thế nào: Mọi vai trò chỉ thấy `live/ready` + `checks.database` + `checks.redis`. Mục "Mô hình ngôn ngữ" chỉ hiện các dòng hợp đồng đã biết (chiến lược trả lời, SSE). Không hiện Ollama/qwen2.5:3b/lexical_fallback như artboard.
- Trạng thái: CHỜ OWNER CHUYỂN

### BR-9: Danh sách `event_type` của nhật ký
- Ưu tiên: Tùy chọn
- Màn hình / file frontend: AuditLogs (`features/audit/AuditLogsPage.tsx`).
- Cần gì từ backend: Liệt kê các giá trị `event_type` ổn định vào `API_SPEC.md` §10 (hoặc endpoint trả danh sách) để UI làm ô chọn thay vì ô nhập tự do.
- Hiện API_SPEC nói gì: §10: "`event_type`, optional stable audit event type." Không có danh sách. Artboard liệt kê 7 giá trị (ví dụ `AUTH_LOGIN_SUCCEEDED`, `CHAT_NO_ANSWER_GENERATED`); chưa đối chiếu được với backend.
- Có làm đổi hành vi/API hiện tại không: Không.
- UI tạm thời đang xử lý thế nào: Giữ ô nhập tự do cho loại sự kiện. Không hiện "Địa chỉ IP" của artboard vì `AuditLogItem` không có trường này và spec cố ý không trả header thô.
- Trạng thái: CHỜ OWNER CHUYỂN

---

## Đã nhận từ backend

Phiên backend trả lời ngày 20/11/2026 trên nhánh `feat/ui-backend-requests` (một PR, mỗi BR một
commit). Các trường và endpoint dưới đây chỉ dùng được khi PR đó đã merge vào `main`. API vẫn là
`/api/v1`: chỉ thêm trường hoặc endpoint, không đổi trường cũ. BR-5, BR-6, BR-7 đang hoãn theo
quyết định của owner.

**CẦN OWNER QUYẾT (chưa làm):**

- BR-1 mục 4: **đã quyết, đã làm**: tìm theo `document_code`.
- BR-3: **đã quyết, đã làm**: thêm `segments`.
- BR-4: tên người tải lên và tên phòng ban trên tài liệu, tên người dùng trên feedback, cho vai trò
  không phải Admin. Việc này trái với quy tắc chống dò tài khoản của `RBAC.md`.

### TRẢ LỜI CHO PHIÊN UI — BR-1 (thông tin phiên bản tài liệu)

- **Trạng thái:** xong mục 1, 2, 3 (chỉ ghi lại hành vi đã có, không đổi code). Mục 4: xong
  theo quyết định của owner (bổ sung ngày 20/11/2026, nhánh `feat/ui-br-followup`).
- **Endpoint:** `POST /api/v1/documents/upload` (multipart form), `GET /api/v1/documents`,
  `GET /api/v1/documents/{document_id}`. Spec: `API_SPEC.md` §7.
- **Field gửi lên (form):** `document_code` (chuỗi ≤ 128 ký tự), `document_version` (≤ 64),
  `effective_from`, `effective_to` (ngày `YYYY-MM-DD`). Server cắt khoảng trắng hai đầu; chuỗi rỗng
  thành `null`. Có thêm `lifecycle_status` (`ACTIVE` mặc định, `SUPERSEDED`, `ARCHIVED`, `DRAFT`) và
  `supersedes_document_id`. Tài liệu `DRAFT` vẫn hiện trong danh sách và tải được, nhưng không bao
  giờ được dùng để trả lời, vì mặc định là `RAG_DRAFT_DOCUMENT_POLICY=exclude`.
- **Field trả về:** cả bốn trường trên, cùng `lifecycle_status` và `supersedes_document_id`, có
  trong response 202 của upload, trong từng item của `GET /documents` và trong
  `GET /documents/{id}`. Ví dụ:
  ```json
  { "id": "uuid", "title": "Quy định nghỉ phép", "document_code": "ND-HR-007",
    "document_version": "1.0", "effective_from": "2026-09-01", "effective_to": null,
    "lifecycle_status": "ACTIVE", "supersedes_document_id": null }
  ```
- **Mã lỗi:**
  - `422 VALIDATION_ERROR`: trường sai quy tắc. Với `effective_to` trước `effective_from`, message
    là `effective_to must not precede effective_from.`; lỗi này được kiểm trước khi lưu tệp.
  - `404 RESOURCE_NOT_FOUND`: `department_id` không tồn tại, hoặc `supersedes_document_id` người
    gọi không xem được.
  - `403 FORBIDDEN`: sai vai trò hoặc phạm vi (xem quy tắc của Manager bên dưới).
- **Quy tắc upload của Manager (mục 3):** được chọn `PRIVATE`, hoặc `DEPARTMENT` với đúng
  `department_id` của chính mình. Server **không** tự điền hay ép `department_id`: UI phải gửi id
  phòng ban của Manager (lấy từ `GET /auth/me`, BR-4). Các trường hợp bị `403 FORBIDDEN`:
  `ORGANIZATION`, phòng ban khác, hoặc Manager chưa có phòng ban.
- **Tìm kiếm (mục 4, owner đã quyết):** `GET /documents?search=` tìm trong `title`,
  `original_filename`, `description` **và `document_code`**.
  - So khớp không phân biệt hoa thường, theo chuỗi con, nên gõ tiền tố của mã cũng tìm được.
  - Tìm kiếm chạy bên trong bộ lọc quyền như cũ: tài liệu người gọi không được xem thì không bao giờ
    hiện ra, kể cả khi gõ đúng mã.
  - Ví dụ: `GET /api/v1/documents?search=nd-hr` trả về tài liệu có mã `ND-HR-007` nếu người gọi xem
    được tài liệu đó.
  - UI có thể đổi placeholder thành "Tên hoặc mã tài liệu".
- **Test:** `tests/api/test_document_upload_api.py`
  (`test_upload_version_fields_are_returned_by_upload_detail_and_list`,
  `test_upload_effective_to_before_effective_from_returns_422`); `tests/api/test_documents_api.py`
  (`test_search_by_document_code_stays_inside_the_access_filter`: Staff tìm theo mã của tài liệu
  ngoài quyền thì không thấy).

### TRẢ LỜI CHO PHIÊN UI — BR-3 (`grounding_status` trong lịch sử, câu "Chưa xác minh được…")

- **Trạng thái:** xong mục 1; mục 2 đã ghi hợp đồng. Phương án "mảng đoạn có cấu trúc" là
  **CẦN OWNER QUYẾT**.
- **Endpoint:** `GET /api/v1/chat/sessions/{session_id}` (lịch sử) và `assistant_message` của
  `POST /chat/sessions/{id}/messages`. Sự kiện SSE `message.completed` vốn đã có
  `grounding_status` ở cấp ngoài, không đổi. Spec: `API_SPEC.md` §8.
- **Field:** `grounding_status` trên mọi message: `"ANSWERED"` | `"NO_ANSWER"` với ASSISTANT;
  `null` với USER và với ASSISTANT lưu trước migration `20261120_0013` (không backfill). Ví dụ:
  ```json
  { "id": "uuid", "role": "ASSISTANT", "content": "…", "citations": [],
    "created_at": "2026-11-20T08:00:00Z", "response_time_ms": 900, "grounding_status": "NO_ANSWER" }
  ```
  Với tin cũ có `grounding_status: null`, UI giữ cách suy hiện tại (không có citation thì coi là
  không có nguồn).
- **Câu "Chưa xác minh được…":**
  - Prompt yêu cầu dạng cố định `Chưa xác minh được từ tài liệu bạn được phép truy cập: …`; với
    câu hỏi tiếng Anh là `Could not be verified from the documents you can access: …`.
  - Ở đường trả lời mặc định (simple, s1), câu này do **mô hình viết**, nên phần sau tiền tố, đôi
    khi cả tiền tố, có thể khác đôi chút.
  - Server nhận diện câu chứa `chưa xác minh được`, `không xác minh được` hoặc
    `could not be verified` (không phân biệt hoa thường và dấu). Server không kiểm câu đó như một
    khẳng định và bỏ marker nguồn của nó, nên câu không có số trích dẫn. Ngoại lệ: câu chứa một con
    số mà câu hỏi không có thì vẫn được coi là khẳng định và giữ marker.
  - UI nên nhận diện theo ba cụm từ trên (gập dấu, không phân biệt hoa thường) thay vì khớp nguyên
    tiền tố. Câu nào không khớp vẫn hiển thị như văn bản thường.
- **`segments` (owner đã quyết, đã làm; bổ sung ngày 20/11/2026, migration `20261120_0014`):**
  - Mỗi tin ASSISTANT có trạng thái `ANSWERED` mang thêm `segments`. Đây là `content` được cắt theo
    câu bằng **chính bước nhận diện** mà server dùng để quyết định câu nào phải kiểm, nên khớp với
    cách server đã xử lý câu trả lời.
  - Dạng mỗi phần tử: `{ "kind": "verified" | "unverified", "text": …, "citation_ids": [...] }`.
    - `text`: câu, đã bỏ số trích dẫn.
    - `citation_ids`: các `citation_order` của trích dẫn mà câu đó hiển thị. Chỉ tính số là trích dẫn
      thật của tin; số trong ngoặc khác vẫn giữ nguyên trong `text`.
  - `content` giữ nguyên.
  - `segments` là `null` với: tin USER, tin `NO_ANSWER` (content là câu từ chối cố định), và tin
    lưu trước migration.
  - Có ở cả ba chỗ: lịch sử `GET /chat/sessions/{id}`, `assistant_message` của
    `POST …/messages`, và sự kiện SSE `message.completed` (`segments`).
  - Ví dụ:
    ```json
    { "role": "ASSISTANT", "grounding_status": "ANSWERED",
      "content": "Nhân viên được nghỉ 12 ngày phép năm. [1] Chưa xác minh được từ tài liệu bạn được phép truy cập: mức phụ cấp.",
      "segments": [
        { "kind": "verified", "text": "Nhân viên được nghỉ 12 ngày phép năm.", "citation_ids": [1] },
        { "kind": "unverified", "text": "Chưa xác minh được từ tài liệu bạn được phép truy cập: mức phụ cấp.", "citation_ids": [] }
      ] }
    ```
  - Cách UI nên dùng: hiển thị theo `segments` khi trường này khác `null`: đoạn `unverified` chữ
    xám, không có chip; đoạn `verified` có chip theo `citation_ids`. Khi `segments` là `null`, hiển
    thị `content` như hiện nay.
  - Giới hạn: việc nhận diện vẫn dựa trên 3 cụm từ (heuristic), đã ghi vào TASKS.
- **Lỗi:** không có mã lỗi mới.
- **DB:** cột `chat_messages.grounding_status` (nullable). Đây là thay đổi lưu trữ duy nhất của
  BR-3; cách trả lời và retrieval không đổi.
- **Test:** `tests/api/test_chat_messages.py`
  (`test_session_history_returns_each_assistant_messages_grounding_status_and_segments`),
  `tests/api/test_chat_streaming.py` (`segments` trong `message.completed`),
  `tests/unit/test_answer_segments.py`: có test cho câu có và câu không có đoạn "Chưa xác minh
  được…".

### TRẢ LỜI CHO PHIÊN UI — BR-4 (tên phòng ban và tên người dùng)

- **Trạng thái:** xong phần hồ sơ của chính mình. Tên trên tài liệu và trên feedback: **CẦN OWNER
  QUYẾT**.
- **Đã làm — endpoint:** `GET /api/v1/auth/me`, cùng `user` trong response của
  `POST /auth/login` và `POST /auth/refresh`. Spec: `API_SPEC.md` §4.
- **Field:** `department_name` (chuỗi | `null`), là tên phòng ban **của chính người gọi**; `null`
  khi người đó chưa có phòng ban. Ví dụ:
  ```json
  { "id": "uuid", "email": "manager@example.com", "full_name": "…", "role": "MANAGER",
    "department_id": "uuid", "department_name": "Nhân sự", "is_active": true }
  ```
  Như vậy là đủ cho Profile và cho Manager khi upload (id và tên phòng ban của chính mình). UI
  không cần gọi `GET /departments`, vốn chỉ dành cho Admin.
- **Lỗi:** không có mã lỗi mới.
- **CẦN OWNER QUYẾT:** `department_name` và `uploaded_by_name` trong `DocumentItem`;
  `user_full_name` và `department_name` trong `FeedbackReportItem`.
  - Mâu thuẫn với RBAC: `RBAC.md` (TASK-007) quy định Manager và Staff đọc thông tin người dùng
    khác thì nhận 404, để chống dò tài khoản. `GET /users` và `GET /departments` chỉ dành cho
    Admin.
  - Nếu trả tên người tải lên cho mọi người xem được tài liệu, Staff sẽ thấy tên người ở phòng ban
    khác (với tài liệu `ORGANIZATION` hoặc được cấp quyền trực tiếp). Manager cũng sẽ thấy tên
    người dùng, điều mà hiện không endpoint nào cho phép.
  - Các phương án để owner chọn:
    - (a) chỉ trả tên khi người gọi là Admin, các vai trò khác nhận `null`;
    - (b) trả tên cho mọi người xem được bản ghi, và sửa `RBAC.md` cho khớp;
    - (c) giữ nguyên, không thêm tên.
  - Chưa làm phần này. Trong lúc chờ, UI giữ cách hiện tại: Admin tra tên qua `/departments` và
    `/users`, các vai trò khác hiện nhãn không kèm tên.
- **Test:** `tests/api/test_auth_endpoints.py`
  (`test_login_and_me_return_the_users_own_department_name`).

### TRẢ LỜI CHO PHIÊN UI — BR-2 (mở tài liệu tại đúng trang)

- **Trạng thái:** xong theo đề xuất `GET /documents/{id}/preview`. URL ký tạm thời: **không làm**
  (BR chỉ nêu như phương án thay thế).
- **Endpoint:** `GET /api/v1/documents/{document_id}/preview` → `200`, đúng `Content-Type` đã lưu
  (`application/pdf`, `image/png`, `image/jpeg`), `Content-Disposition: inline; filename="…"`,
  `X-Content-Type-Options: nosniff`, `Cache-Control: private, no-store`. Spec: `API_SPEC.md` §7.
- **Quyền và lỗi:** giống hệt `/download`.
  - `401`: thiếu token hoặc token sai.
  - `404 RESOURCE_NOT_FOUND`: không có quyền xem, không tồn tại, hoặc đã xóa.
  - `410 DOCUMENT_FILE_UNAVAILABLE`: mất tệp.
  - Mỗi lần xem được ghi audit `DOCUMENT_DOWNLOADED`, như tải xuống.
- **Cách dùng:**
  - Vẫn cần header `Authorization: Bearer`. Cách UI đang làm vẫn đúng: `fetch` → `blob:` URL →
    gắn `#page=N` cho PDF. Chỉ cần đổi `/download` thành `/preview`.
  - Server không đọc `#page`.
  - Rủi ro dùng chung refresh token giữa hai tab mà BR đã nêu vẫn còn. Muốn gỡ thì cần URL ký tạm
    thời; nếu owner muốn thì ghi thành BR mới.
- **Test:** `tests/api/test_documents_api.py`
  (`test_document_preview_is_inline_with_the_download_access_rules`).

### TRẢ LỜI CHO PHIÊN UI — BR-8 (ví dụ JSON cho giám sát Admin)

- **Trạng thái:** xong. Chỉ thêm tài liệu, không đổi response.
- **Endpoint:** `GET /api/v1/admin/system`, `/admin/health`, `/admin/providers`, `/admin/version`,
  chỉ dành cho Admin (Manager và Staff nhận `403 FORBIDDEN`). Ví dụ JSON đầy đủ có ở `API_SPEC.md`,
  mục "TASK-032 Admin Monitoring API".
- **Field UI cần cho mục "Mô hình ngôn ngữ":** lấy từ `data.llm` của `/admin/providers` (hoặc
  `data.providers.llm` của `/admin/system`): `provider`, `display_name`, `model`, `status`
  (`healthy` | `disabled` | `misconfigured` | `unhealthy`), `enabled`, `configured`, `message`.
  Ở cấu hình mặc định: `"provider": "ollama"`, `"display_name": "Ollama"`,
  `"model": "qwen3.5-text:4b"`. Ví dụ:
  ```json
  { "provider_type": "llm", "provider": "ollama", "status": "healthy", "enabled": true,
    "configured": true, "display_name": "Ollama", "model": "qwen3.5-text:4b",
    "external_allowed": null, "connectivity_checked": false, "message": "…" }
  ```
  Endpoint chỉ kiểm cấu hình, không gọi tới mô hình (`connectivity_checked: false`).
- **Phiên bản:** `/admin/version` trả `app_name`, `version`, `environment`, `python_version`,
  `api_prefix`, `migration_head`, `database_revision`, `started_at`, `uptime_seconds`.
- **Không có trong các endpoint này:**
  - Chế độ trả lời (simple hay legacy) và cấu hình reranker như `lexical_fallback`. Reranker chỉ có
    ở `GET /health/ready` (`reranker_mode`). Nếu UI cần hiện chế độ trả lời thì ghi thành BR mới.
  - Câu cũ "Not exposed by current backend API" trên trang System đã lỗi thời; nên bỏ.
- **Test:** `tests/api/test_admin_monitoring.py`
  (`test_admin_monitoring_responses_keep_the_documented_example_shape`) kiểm các khóa của response
  khớp với ví dụ trong spec.

### TRẢ LỜI CHO PHIÊN UI — BR-9 (danh sách `event_type`)

- **Trạng thái:** xong, bằng cách ghi danh sách vào spec. Không thêm endpoint.
- **Endpoint:** `GET /api/v1/audit-logs?event_type=…` (chỉ Admin). Danh sách có ở `API_SPEC.md`
  §10, mục "Audit event types".
- **Giá trị (23):**
  - Xác thực: `AUTH_LOGIN_SUCCEEDED`, `AUTH_LOGIN_FAILED`.
  - Người dùng: `USER_CREATED`, `USER_UPDATED`, `USER_STATUS_CHANGED`, `USER_DEACTIVATED`,
    `USER_REACTIVATED`.
  - Phòng ban: `DEPARTMENT_CREATED`, `DEPARTMENT_UPDATED`, `DEPARTMENT_DELETED`.
  - Tài liệu: `DOCUMENT_UPLOADED`, `DOCUMENT_UPDATED`, `DOCUMENT_DOWNLOADED`, `DOCUMENT_DELETED`.
  - Quyền tài liệu: `DOCUMENT_PERMISSION_GRANTED`, `DOCUMENT_PERMISSION_UPDATED`,
    `DOCUMENT_PERMISSION_REVOKED`.
  - Chat: `CHAT_SESSION_CREATED`, `CHAT_SESSION_DELETED`, `CHAT_QUESTION_SUBMITTED`,
    `CHAT_ANSWER_GENERATED`, `CHAT_NO_ANSWER_GENERATED`.
  - Feedback: `FEEDBACK_UPSERTED`.
- **Lưu ý cho ô chọn:**
  - `USER_DEACTIVATED` và `USER_REACTIVATED` được filter chấp nhận nhưng server **không ghi**: khóa
    hoặc mở lại tài khoản được ghi là `USER_STATUS_CHANGED`. UI có thể ẩn hai giá trị này.
  - Xem tài liệu qua `/preview` cũng ghi là `DOCUMENT_DOWNLOADED`.
- **Mã lỗi:** `event_type` ngoài danh sách → `422 AUDIT_FILTER_INVALID`.
- **Ví dụ:** `GET /api/v1/audit-logs?event_type=CHAT_NO_ANSWER_GENERATED&outcome=SUCCESS`.
- **Không có địa chỉ IP:** `AuditLogItem` không trả IP. Server có lưu IP, nhưng spec cố ý không
  trả ra. Giữ như ghi chú của UI.
- **Test:** `tests/unit/test_audit_events.py`
  (`test_audit_event_types_are_the_ones_api_spec_lists`). Thêm loại sự kiện mới thì test này đỏ,
  nhắc cập nhật spec.
