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

**Các mục từng ghi CẦN OWNER QUYẾT (owner đã quyết ngày 20/11/2026):**

- BR-1 mục 4: **đã quyết, đã làm**: tìm theo `document_code`.
- BR-3: **đã quyết, đã làm**: thêm `segments`.
- BR-4: **đã quyết (phương án a), đã làm**: tên chỉ dành cho Admin; thêm `uploaded_by_me`.

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

- **Trạng thái:** xong phần hồ sơ của chính mình. Tên trên tài liệu và trên feedback: owner chọn
  **phương án (a)**, đã làm (bổ sung ngày 20/11/2026, nhánh `feat/ui-br-followup`).
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
- **Tên trên tài liệu và feedback (phương án a, đã làm):**
  - Tài liệu: áp dụng cho response 202 của upload, `GET /documents`, `GET /documents/{id}` và
    `PATCH /documents/{id}`.
    - `uploaded_by_me` (boolean) có cho **mọi người xem được tài liệu**.
    - `uploaded_by_name` (họ tên người tải lên) và `department_name` (tên phòng ban của tài liệu,
      `null` nếu không có) **chỉ có khi người gọi là Admin**.
  - Feedback (`GET /feedback`): `user_full_name` và `department_name` chỉ có khi người gọi là
    Admin.
  - Với Manager và Staff, các khóa trên **không có trong response**: không phải `null` mà vắng hẳn,
    để UI không suy ra được là có tồn tại tên.
  - Ví dụ, người gọi là Admin:
    ```json
    { "id": "uuid", "title": "…", "uploaded_by": "uuid", "uploaded_by_me": false,
      "uploaded_by_name": "Nguyễn Văn A", "department_id": "uuid", "department_name": "Nhân sự" }
    ```
    Người gọi là Staff (cùng tài liệu):
    ```json
    { "id": "uuid", "title": "…", "uploaded_by": "uuid", "uploaded_by_me": false,
      "department_id": "uuid" }
    ```
  - **Kết luận về tên phòng ban của tài liệu:** đọc `RBAC.md` thì thấy mục TASK-007 quy định danh
    sách và chi tiết phòng ban chỉ dành cho Admin. Người không phải Admin vẫn có thể xem tài liệu
    `DEPARTMENT` của phòng ban khác nếu được cấp quyền trực tiếp, và `RBAC.md` không có điều nào
    cho phép nêu tên phòng ban đó với họ. Đây là trường hợp mơ hồ, nên theo quyết định của owner
    tên phòng ban **chỉ trả cho Admin**. Lý do đã ghi vào `RBAC.md`, mục "BR-4 names in
    responses".
  - Gợi ý cho UI: với tài liệu thuộc phòng ban của chính người dùng (`department_id` của tài liệu
    trùng `department_id` trong `/auth/me`), UI tự hiện tên lấy từ `/auth/me`
    (`department_name`), không cần server trả thêm. Với Manager, trang feedback chỉ chứa người
    trong phòng ban của chính họ, nên tên phòng ban cũng lấy được như vậy.
- **Test:**
  - `tests/api/test_auth_endpoints.py`
    (`test_login_and_me_return_the_users_own_department_name`).
  - Chống dò tài khoản:
    - `tests/api/test_documents_api.py`
      (`test_names_reach_admin_only_and_uploaded_by_me_every_viewer`): Staff và Manager không nhận
      tên, kể cả khóa, ở danh sách, chi tiết và PATCH; Admin thì nhận.
    - `tests/api/test_document_upload_api.py` (`test_upload_response_names_go_to_admin_only`).
    - `tests/api/test_feedback.py` (`test_feedback_report_names_go_to_admin_only`).

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

---

## Tình trạng phía UI (20/11/2026)

- Đã ghép trên `feat/ui-redesign` (PR #42), sau khi merge PR #53 và #54 của backend:
  - BR-1: form upload đủ trường phiên bản; danh sách và chi tiết hiện mã, phiên bản, hiệu lực, vòng
    đời; tìm theo mã; luật upload của Manager.
  - BR-2: trang xem tài liệu dùng `/preview`.
  - BR-3: `grounding_status`, và hiển thị theo `segments`. UI không còn nhận diện câu theo chữ.
  - BR-4: `department_name` của chính mình; tên chỉ hiện khi response có khóa (Admin);
    `uploaded_by_me` cho mọi vai trò.
  - BR-8: trang Trạng thái hệ thống đọc `/admin/system` (chỉ Admin).
  - BR-9: ô chọn 23 `event_type`, xử lý `422 AUDIT_FILTER_INVALID`.
- Hoãn theo owner: BR-5, BR-6, BR-7.
- Yêu cầu mới: BR-10, BR-11 (bên dưới), cùng BR-12 do owner thêm; cả ba đã trả lời trong PR #55
  và đã ghép trên `feat/ui-redesign` ngày 22/11/2026.

## PROMPT CHO PHIÊN BACKEND

Owner dán nguyên khối này sang phiên backend:

> Phiên UI ghi thêm hai yêu cầu, BR-10 và BR-11, ở cuối `docs/ui/backend-requests.md` trên `main`
> (đến cùng PR #42). Với mỗi BR:
> - chỉ thêm trường hoặc ghi lại hành vi đang có, không đổi trường cũ;
> - cập nhật `API_SPEC.md`;
> - trả lời bằng khối "TRẢ LỜI CHO PHIÊN UI — BR-n" trong file đó, kèm tên test.
>
> BR-10 (Nên có): ghi vào API_SPEC §3 dạng `details` của `422 VALIDATION_ERROR`, đủ để UI gắn lỗi
> vào đúng trường của form.
>
> BR-11 (Tùy chọn): trong `GET /audit-logs` (chỉ Admin) thêm họ tên người thực hiện và nhãn an toàn
> của đối tượng, theo cùng quy tắc BR-4 (a).

### BR-10: Dạng `details` của lỗi `422 VALIDATION_ERROR` theo từng trường
- Ưu tiên: **Nên có**
- Màn hình / file frontend: Upload (`features/documents/DocumentUploadPage.tsx`); về sau mọi form
  gửi lên (Users, Departments, Permissions).
- Cần gì từ backend:
  - Ghi vào `API_SPEC.md` §3 ("Standard error response") dạng `details` của
    `422 VALIDATION_ERROR`, đủ để UI gắn lỗi vào đúng trường.
  - Đề xuất: `"details": [{ "field": "effective_to", "message": "effective_to must not precede effective_from." }]`.
    `field` là tên trường đúng như trong request (form hoặc JSON), không phải đường dẫn nội bộ
    kiểu `["body", "…"]`.
  - Nếu server đã trả một dạng ổn định (ví dụ danh sách `loc`/`msg`), chỉ cần ghi đúng dạng đó vào
    spec và cam kết giữ nguyên.
- Hiện API_SPEC nói gì:
  - §3 chỉ có ví dụ `"details": null`.
  - §7 (upload) liệt kê các trường hợp 422 nhưng không ghi `details`. Chỉ một message được ghi
    nguyên văn: `effective_to must not precede effective_from.`.
- Có làm đổi hành vi/API hiện tại không: Không, nếu chỉ ghi lại dạng đang có. Có, nếu phải chuẩn
  hóa sang dạng mới.
- UI tạm thời đang xử lý thế nào:
  - Kiểm tra từng trường phía client trước khi gửi (độ dài, thứ tự ngày, phòng ban, tệp).
  - 422 có đúng message trong spec thì gắn vào ô "Hiệu lực đến".
  - Các 422 khác hiện thành lỗi chung của form, kèm message của server.
  - Có `TODO(BR-10)`.
- Trạng thái: XONG (PR #55, trả lời bên dưới)

### BR-11: Tên người thực hiện và nhãn đối tượng trong nhật ký (chỉ Admin)
- Ưu tiên: Tùy chọn
- Màn hình / file frontend: AuditLogs (`features/audit/AuditLogsPage.tsx`), `api/types.ts` →
  `AuditLogItem`.
- Cần gì từ backend:
  - Trong `GET /audit-logs` (vốn chỉ dành cho Admin) thêm:
    - `actor_full_name`: họ tên người thực hiện; `null` khi `actor_user_id` là null hoặc không còn
      tra được;
    - tùy chọn `target_label`: nhãn an toàn của đối tượng, ví dụ `document_code` hoặc tiêu đề tài
      liệu, mã phòng ban, email người dùng.
  - Theo cùng quy tắc với BR-4 (a).
  - Ví dụ: `{ "actor_user_id": "uuid", "actor_full_name": "Admin UAT", "target_type": "DOCUMENT", "target_id": "uuid", "target_label": "ND-HR-007" }`.
  - Không thêm IP, header hay nội dung chat.
- Hiện API_SPEC nói gì:
  - §10: `AuditLogItem` chỉ có `actor_user_id`, `target_type`, `target_id` (đều là UUID).
  - Artboard "Nhật ký hệ thống" hiện tên người thực hiện ("Staff Nhân sự") và mã đối tượng
    ("ND-HR-007").
- Có làm đổi hành vi/API hiện tại không: Không, chỉ thêm trường cho Admin.
- UI tạm thời đang xử lý thế nào:
  - Hiện UUID rút gọn của người thực hiện ("Hệ thống" khi null) và loại đối tượng.
  - Không gọi thêm `/users` để tra tên.
  - Có `TODO(BR-11)`.
- Trạng thái: XONG (PR #55, trả lời bên dưới)

## Đã nhận từ backend: BR-10, BR-11, BR-12 (PR #55)

Phiên backend trả lời ngày 21/11/2026, nhánh `feat/ui-br-10-12`, ban đầu ở file tạm
`docs/ui/backend-responses-10-12.md`. Phiên UI gộp vào đây và xóa file tạm. BR-12 do owner thêm,
không có mục yêu cầu riêng.

### TRẢ LỜI CHO PHIÊN UI — BR-10 (`details` của lỗi 422 theo từng trường)

- **Trạng thái:** xong.
- **Hành vi trước đây:** mọi lỗi 422 đều trả `"details": null`. Từ bản này, `details` của lỗi 422
  là một danh sách. Đây là điền thêm vào trường vốn rỗng, không đổi trường cũ.
- **Contract** (`API_SPEC.md` §3):
  - `details` là `[{ "field": …, "code": …, "message": … }]`, mỗi phần tử ứng với một trường sai.
  - `field`: tên trường đúng như trong request (form, JSON hoặc query). Trường JSON lồng nhau nối
    bằng dấu `.`. Là `null` khi lỗi thuộc về cả request.
  - `code` **ổn định**, để UI ánh xạ sang câu tiếng Việt:
    - thiếu hoặc rỗng: `REQUIRED`;
    - độ dài: `TOO_LONG`, `TOO_SHORT`;
    - số ngoài giới hạn: `OUT_OF_RANGE`;
    - giá trị không nằm trong danh sách cho phép: `INVALID_CHOICE`;
    - sai định dạng hoặc kiểu: `INVALID_DATE`, `INVALID_FORMAT`, `INVALID_TYPE`;
    - giá trị bị một quy tắc từ chối: `INVALID_VALUE`;
    - sai quy tắc giữa hai trường: `INVALID_RANGE`;
    - không được gửi trường này trong trường hợp này: `NOT_ALLOWED`;
    - trường endpoint không nhận: `UNKNOWN_FIELD`;
    - body không phải JSON hợp lệ: `INVALID_JSON`;
    - còn lại: `INVALID`.
  - `message`: câu tiếng Anh, có thể đổi giữa các phiên bản; `code` thì không. Không bao giờ lặp
    lại giá trị người dùng đã gửi.
  - Mã lỗi chung vẫn là `VALIDATION_ERROR`, hoặc mã riêng của endpoint (`AUDIT_FILTER_INVALID`,
    `FEEDBACK_*`); `details` cùng một dạng.
- **Ví dụ upload**, `effective_to` trước `effective_from`:
  ```json
  { "error": { "code": "VALIDATION_ERROR", "message": "effective_to must not precede effective_from.",
      "details": [ { "field": "effective_to", "code": "INVALID_RANGE",
                     "message": "effective_to must not precede effective_from." } ],
      "request_id": null } }
  ```
- **Các trường hợp upload hay gặp:**

  | Trường hợp | `field` | `code` |
  |---|---|---|
  | `title` dài quá 255 ký tự | `title` | `TOO_LONG` |
  | thiếu `access_scope` | `access_scope` | `REQUIRED` |
  | `access_scope` lạ | `access_scope` | `INVALID_CHOICE` |
  | `DEPARTMENT` mà thiếu `department_id` | `department_id` | `REQUIRED` |
  | `department_id` gửi kèm `PRIVATE` hoặc `ORGANIZATION` | `department_id` | `NOT_ALLOWED` |
  | ngày sai | `effective_from` / `effective_to` | `INVALID_DATE` |
  | `effective_to` trước `effective_from` | `effective_to` | `INVALID_RANGE` |

- **Ví dụ người dùng:**
  - `POST /users`: email sai thì `email` / `INVALID_VALUE`; mật khẩu dưới 12 ký tự thì
    `password` / `TOO_SHORT`; Manager hoặc Staff không có phòng ban thì `department_id` /
    `REQUIRED`.
  - `PATCH /users/{id}`: trường lạ thì `UNKNOWN_FIELD`; vai trò lạ thì `INVALID_CHOICE`.
- **Test:**
  - `tests/api/test_document_upload_api.py`: `test_upload_422_details_name_the_form_field`,
    `test_upload_missing_field_is_a_required_detail`.
  - `tests/api/test_users_api.py`:
    `test_user_create_and_update_422_details_name_each_json_field` (cũng kiểm mật khẩu và email
    đã gửi không bị lặp lại trong response).

### TRẢ LỜI CHO PHIÊN UI — BR-11 (tên người thực hiện và nhãn đối tượng trong nhật ký)

- **Trạng thái:** xong. Chỉ thêm trường cho Admin.
- **Endpoint:** `GET /api/v1/audit-logs`. Endpoint này vốn chỉ dành cho Admin: vai trò khác nhận
  `403 AUDIT_REPORT_FORBIDDEN`. Ngoài ra, serializer kiểm vai trò thêm một lần nữa: item dựng cho
  vai trò khác không có hai khóa mới. Spec: `API_SPEC.md` §10.
- **Field mới trên mỗi item:**
  - `actor_full_name`: họ tên người thực hiện. Là `null` khi `actor_user_id` là `null` (sự kiện
    hệ thống, đăng nhập thất bại) hoặc người dùng không còn.
  - `target_label`: nhãn an toàn của đối tượng, **chỉ là tên hiển thị hoặc mã**:

    | `target_type` | `target_label` |
    |---|---|
    | `USER` | họ tên người dùng |
    | `DEPARTMENT` | mã phòng ban |
    | `DOCUMENT` | `document_code`, nếu không có thì tiêu đề (kể cả tài liệu đã xóa mềm) |
    | `DOCUMENT_PERMISSION` | nhãn của tài liệu mà quyền đó thuộc về; `null` khi quyền đã bị thu hồi |
    | `CHAT_SESSION`, `CHAT_MESSAGE`, `FEEDBACK`, không có | `null` |

  - Ba loại cuối luôn là `null`, vì nội dung duy nhất của chúng là chữ người dùng viết; tiêu đề
    phiên chat có thể chính là câu hỏi.
  - Không bao giờ có nội dung tài liệu, câu hỏi hay câu trả lời chat, email hoặc metadata. Không
    thêm IP hay header.
- **Ví dụ:**
  ```json
  { "id": "uuid", "event_type": "DOCUMENT_UPLOADED", "outcome": "SUCCESS",
    "actor_user_id": "uuid", "actor_full_name": "Admin UAT",
    "target_type": "DOCUMENT", "target_id": "uuid", "target_label": "ND-HR-007",
    "request_id": null, "error_code": null, "metadata": { "access_scope": "DEPARTMENT" },
    "created_at": "2026-11-21T08:00:00Z" }
  ```
- **Lỗi:** không có mã lỗi mới.
- **Test:** `tests/api/test_audit_logs.py`:
  - `test_admin_report_adds_actor_names_and_safe_target_labels`: đủ mọi loại đối tượng; tiêu đề
    phiên chat không xuất hiện trong response;
  - `test_the_serializer_drops_names_for_a_non_admin_even_with_labels`: kiểm vai trò ở
    serializer;
  - `test_audit_report_response_is_sanitized`: đã cập nhật, Admin thấy tên người thực hiện, không
    bao giờ thấy email.

### TRẢ LỜI CHO PHIÊN UI — BR-12 (`break_after` của mỗi segment, owner thêm)

- **Trạng thái:** xong. Chỉ thêm trường.
- **Field:** mỗi phần tử của `segments` (BR-3) có thêm `break_after`: `"none"` | `"line"` |
  `"paragraph"`.
  - Giá trị lấy từ khoảng trắng gốc trong `content` giữa đoạn này và đoạn sau: không xuống dòng
    là `none`, một lần xuống dòng là `line`, từ hai lần trở lên là `paragraph`.
  - Đoạn cuối luôn là `"none"`.
  - Có ở cả lịch sử chat, response của `POST …/messages` và sự kiện SSE `message.completed`.
  - Spec: `API_SPEC.md` §8.
- **Cách dùng:** ghép các `text` theo `break_after`: `none` là một dấu cách (cùng dòng), `line` là
  `\n`, `paragraph` là `\n\n`. Kết quả tái tạo đúng cấu trúc dòng của `content`, chỉ bỏ số
  trích dẫn.
- **Ví dụ** (danh sách gạch đầu dòng):
  ```json
  "segments": [
    { "kind": "verified", "text": "Quy trình gồm:", "citation_ids": [], "break_after": "line" },
    { "kind": "verified", "text": "- Bước 1: nộp đơn.", "citation_ids": [1], "break_after": "line" },
    { "kind": "verified", "text": "- Bước 2: trưởng phòng duyệt.", "citation_ids": [2], "break_after": "paragraph" },
    { "kind": "unverified", "text": "Chưa xác minh được từ tài liệu bạn được phép truy cập: thời hạn.", "citation_ids": [], "break_after": "none" }
  ]
  ```
- **Lưu ý:**
  - Dấu chấm giữa dòng (ví dụ sau `1.` trong danh sách đánh số) cũng tách thành đoạn, với
    `break_after: "none"`. Hiển thị các đoạn `none` trên cùng một dòng, cách nhau một dấu cách,
    thì chữ vẫn giữ nguyên như gốc.
  - Số trích dẫn đứng riêng một dòng được gộp vào đoạn ngay trước.
  - Segment lưu trước BR-12 không có khóa này; API trả `"none"` cho chúng.
- **Test:** `tests/unit/test_answer_segments.py`:
  - `test_break_after_rebuilds_the_line_structure_of_the_content`, với ba dạng: danh sách gạch
    đầu dòng, nhiều đoạn, một câu;
  - `test_citation_numbers_alone_on_a_line_join_the_line_before`;
  - các test BR-3 đã cập nhật.

## PROMPT CHO PHIÊN BACKEND (27/11/2026, demo qua nginx)

Owner dán nguyên khối này sang phiên backend:

> Phiên UI chạy toàn bộ test live trên stack eaka-demo (nginx ở 18480, bản build production) và
> ghi thêm hai yêu cầu, BR-13 và BR-14, ở cuối `docs/ui/backend-requests.md`. Không có lỗi nào làm
> fail test; cả hai lộ ra khi xem demo.
> Trả lời bằng khối "TRẢ LỜI CHO PHIÊN UI — BR-n" trong file đó.
>
> BR-13 (Nên có, deploy): mở demo bằng `http://localhost:18480` thì không đăng nhập được, vì bản
> build gọi API ở `http://127.0.0.1:18480` (origin khác) và preflight CORS trả 400. Phía UI đã làm
> phần của mình: `VITE_API_BASE_URL=""` giờ nghĩa là cùng origin. Phía deploy còn phải làm: cho
> `deploy/frontend/Dockerfile` nhận build arg rỗng (hiện bị `test -n` chặn), build demo với
> `VITE_API_BASE_URL=""`, rồi cập nhật DEMO.md.
>
> BR-14 (Nên có, trích xuất): đoạn trích của trích dẫn bắt đầu giữa chữ và chứa ký tự U+F0B7 (bullet
> của font Symbol trong PDF), hiện thành ô vuông. Sửa qua pipeline xử lý tài liệu rồi xử lý lại tài
> liệu; không sửa `document_chunks` trực tiếp.

### BR-13: Demo mở bằng `localhost` không đăng nhập được (deploy, CORS)

- **Mức:** Nên có. Chỉ ảnh hưởng khi mở bằng `localhost`; `http://127.0.0.1:18480` (URL trong
  DEMO.md) vẫn chạy đúng.
- **Hiện trạng:**
  - `deploy/frontend/Dockerfile` build với `VITE_API_BASE_URL=http://127.0.0.1:18480`, nên giá trị
    này nằm cứng trong bundle.
  - Trang ở `http://localhost:18480` gọi `http://127.0.0.1:18480/api/v1/auth/login`, tức là một
    request khác origin.
  - Preflight `OPTIONS` với `Origin: http://localhost:18480` trả 400, không có
    `Access-Control-Allow-Origin`.
  - Kiểm bằng Chromium: `fetch` từ trang `localhost` bị chặn (`TypeError: Failed to fetch`).
- **Hai cách sửa:**
  - **(a)** Build frontend để gọi API cùng origin (đường dẫn tương đối `/api/v1/...`). Phía UI cần
    một thay đổi nhỏ trong `frontend/src/lib/config.ts`. Hiện `VITE_API_BASE_URL || "http://127.0.0.1:8000"`
    coi chuỗi rỗng là chưa đặt, nên không build "cùng origin" được. Đổi sang `??` thì
    `VITE_API_BASE_URL=""` nghĩa là cùng origin, còn khi biến không được đặt thì vẫn giữ mặc định cho
    dev. Phiên UI làm phần này nếu owner đồng ý. Phía deploy đổi build arg thành chuỗi rỗng.
  - **(b)** Thêm `http://localhost:18480` vào danh sách CORS origin của API trong `compose.demo.yaml`.
- **Đề xuất:** (a). Với nginx cùng origin thì trình duyệt không cần CORS, và cùng một image chạy
  được với mọi host name.
- **Owner chọn (a). Phía UI đã làm (27/11/2026):**
  - `frontend/src/lib/config.ts` dùng `??`:
    - biến không đặt: dùng mặc định dev `http://127.0.0.1:8000`;
    - `""`: cùng origin;
    - giá trị tuyệt đối: giữ nguyên như trước (dev ở 5173 gọi API ở cổng khác).
  - `buildUrl` trong `client.ts` lấy `window.location.origin` làm base khi base rỗng. Luồng chat
    trong `sse.ts` (không đổi) tạo URL tương đối `/api/v1/...`, nên cũng đi về cùng origin.
  - Test: `frontend/src/lib/config.test.ts` (3 trường hợp).
  - Đã kiểm bằng build thật: với `VITE_API_BASE_URL=""`, bundle không còn origin cứng nào.
- **Phía deploy còn phải làm:**
  - `deploy/frontend/Dockerfile` dòng `RUN test -n "$VITE_API_BASE_URL" || …` đang chặn giá trị
    rỗng. Muốn vẫn bắt lỗi quên đặt arg thì kiểm "đã đặt" thay vì "khác rỗng", ví dụ
    `test "${VITE_API_BASE_URL+set}" = set`.
  - Build demo với `--build-arg VITE_API_BASE_URL=`.
  - Cập nhật lệnh build trong DEMO.md.
  - Sau đó mở bằng cả `127.0.0.1:18480` lẫn `localhost:18480` đều phải đăng nhập được.

### BR-14: Đoạn trích của trích dẫn bắt đầu giữa chữ và có ký tự U+F0B7 (trích xuất)

- **Mức:** Nên có. Lỗi lộ ra ngay ở bước 1 của kịch bản demo: staff hỏi Q016 rồi mở trích dẫn.
- **Hiện trạng:** câu trả lời Q016 trích "Nội quy lao động Công ty Công nghệ Nova Digital", trang 5.
  `excerpt` do API trả về:
  - bắt đầu bằng `ỆU NHÂN SỰ 02 THỜI GIỜ L…`, tức là cắt giữa chữ "LIỆU" (dòng đầu trang
    "TÀI LIỆU NHÂN SỰ");
  - chứa U+F0B7 ở chỗ dấu đầu dòng của PDF ("…tiêu chuẩn Thời gian làm việc…"). Font giao diện
    không có glyph cho ký tự này nên hiện thành ô vuông.
  - `evidence_text` của cùng trích dẫn đã bắt đầu đúng chữ.
  - UI hiển thị `excerpt` nguyên văn, không sửa.
- **Yêu cầu:**
  - Ở bước trích xuất: chuẩn hóa các bullet thuộc vùng Private Use của font Symbol/Wingdings (U+F0B7,
    U+F0A7, …) thành `•`.
  - Ở bước dựng `excerpt`: bắt đầu và kết thúc tại ranh giới từ.
  - Sau đó xử lý lại tài liệu qua pipeline (CLAUDE.md: không sửa `document_chunks` trực tiếp).
- **Ghi chú:** đây không phải lỗi riêng của nginx; mọi stack dùng corpus này đều gặp.

### TRẢ LỜI CHO PHIÊN UI — BR-13 (demo cùng origin, đăng nhập qua `localhost`)

- **Trạng thái:** xong, phía deploy. Không đổi API.
- **`deploy/frontend/Dockerfile`:**
  - kiểm arg đã được đặt (`test "${VITE_API_BASE_URL+set}" = set`) thay vì khác rỗng;
  - quên `--build-arg VITE_API_BASE_URL` thì build dừng, kèm lời nhắc;
  - `VITE_API_BASE_URL=` (rỗng) thì build ra bản cùng origin, nhờ `config.ts` của PR #63.
- **Demo:** image frontend build với `--build-arg VITE_API_BASE_URL=`; DEMO.md ghi cả hai URL và lệnh build mới.
- **Đã kiểm trên stack demo** (`check_demo.py`, qua nginx 18480):
  - bundle không còn `127.0.0.1:18480` hay `127.0.0.1:8000`;
  - `POST /api/v1/auth/login` kèm `Origin` cùng host trả 200 ở cả `http://localhost:18480` và `http://127.0.0.1:18480`.
- **Chưa kiểm:** đăng nhập bằng trình duyệt thật. Phiên UI chạy lại `frontend/tests/e2e-live/deploy.spec.ts` trên stack đã dựng lại từ `main`.

### TRẢ LỜI CHO PHIÊN UI — BR-14 (đoạn trích: ranh giới từ và ký tự U+F0B7), bản hẹp

- **Trạng thái:** xong phần hiển thị, theo bản hẹp owner duyệt.
- **Không đổi:** nội dung chunk, embedding, retrieval, prompt và validation, nên không cần xử lý lại tài liệu.
- **Phần chuẩn hóa ở bước trích xuất** chuyển vào TASKS [TB], làm cùng corpus v3.
- **`excerpt` và `evidence_text` của citation** (`app/citations/excerpt.py`, `display_text()`):
  - mọi code point U+F000-U+F0FF (vùng Private Use của font Symbol/Wingdings, như U+F0B7, U+F0A7, U+F0D8) hiển thị thành `•`, độ dài chuỗi giữ nguyên;
  - `evidence_text` được đổi giống hệt `excerpt`, nên UI vẫn tìm được `evidence_text` bên trong `excerpt` để tô sáng.
- **Đầu đoạn trích:**
  - nguyên nhân: chunk thứ 2 trở đi mở đầu bằng phần overlap token của chunk trước, có thể bắt đầu giữa chữ ("ỆU NHÂN SỰ" là đầu thật của chunk đó trong DB);
  - khi đó `excerpt` bỏ mảnh chữ đầu và mở bằng `…`, trừ khi bằng chứng bắt đầu đúng chỗ đó;
  - chunk đầu tài liệu và chunk dòng bảng (DEC-034) giữ nguyên;
  - cuối đoạn trích vẫn cắt tại ranh giới từ và thêm `…` như trước.
- **Ví dụ** (Q016, staff, trang 5): `excerpt` bắt đầu bằng `…NHÂN SỰ 02 THỜI GIỜ LÀM VIỆC…` và không còn U+F0B7.
- **Test:** `tests/unit/test_citation_display_text.py` (6 test: ký tự Symbol, bỏ mảnh chữ đầu, giữ đầu khi không có overlap hoặc khi bằng chứng ở đầu, ngân sách ký tự, đường mapper, đánh dấu ở context).

### TRẢ LỜI CHO PHIÊN UI — BR-15 (`evidence_spans`: vị trí bằng chứng trong `excerpt`)

- **Trạng thái:** xong, chọn cách thứ hai của BR-15 (owner duyệt). Chỉ thêm trường.
- **Field:** mỗi citation có thêm `evidence_spans`: `[{ "start": int, "end": int }]`.
  - `[start, end)` là vị trí ký tự trong `excerpt` đúng như API trả về, tức là bản đã chuẩn hóa sau BR-14.
  - Trường luôn có mặt, ở lịch sử chat, response của `POST …/messages` và SSE (`citations.ready`, `message.completed`).
  - Spec: `API_SPEC.md` §8A.
- **Nhiều span:** bằng chứng không liền thì mỗi mảnh là một span. Ví dụ Q016: bằng chứng thiếu `Điều 5.` ở giữa, nên có 2 span.
- **`[]`:** không có `evidence_text`, hoặc không tìm được trong `excerpt` (khớp dưới 60% số từ). Khi đó UI hiện đoạn trích không tô sáng.
- **`evidence_text`:** giữ nguyên để tương thích. UI nên dùng `evidence_spans` trước, và chỉ quay về cách tìm chuỗi hiện tại khi trường này không có.
- **Cách tính:**
  - khớp từng từ theo thứ tự, chọn đoạn liền dài nhất;
  - từ cuối của bằng chứng có thể là phần đầu của một từ trong `excerpt` (Q084: `2.400.000 đ` nằm trong `2.400.000 đ/năm`);
  - một từ lẻ trong bằng chứng dài bị bỏ qua, coi là trùng ngẫu nhiên;
  - `…` không bao giờ nằm trong span; `•` và ký tự Symbol cũ được so như nhau.
- **Lưu ý cho UI:**
  - vị trí đếm theo code point. Văn bản trong BMP (tiếng Việt, `•`, `…`) thì trùng chỉ số chuỗi của JavaScript;
  - không đổi chunk, embedding, retrieval, prompt hay validation;
  - spans được tính lúc đọc, nên trích dẫn cũ cũng có.
- **Đã kiểm trên demo** (staff):
  - Q016: 2 span;
  - Q043: 1 span (`03 ngày`, chỗ xuất hiện đầu tiên);
  - Q084: 1 span (`2.400.000 đ`).
- **Test:** `tests/unit/test_evidence_spans.py`:
  - các ca giống hình dạng Q016, Q043, Q084;
  - `•` và `…` ở đầu;
  - ký tự Symbol trong trích dẫn cũ;
  - không tìm thấy;
  - schema.
