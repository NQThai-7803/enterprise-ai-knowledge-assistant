# Kế hoạch ghép giao diện mới (feat/ui-redesign)

Ngày lập: 17/11/2026. Phiên UI, chỉ sửa `frontend/**` và `docs/ui/**`. Chưa có dòng code nào bị đổi.
Nguồn: `C:\dev\EAKA – UI Animation.html` (16 artboard), `frontend/src`, `API_SPEC.md`, `docs/review/bao-cao-kiem-thu-2026-10-28.md`.
Yêu cầu backend: xem `docs/ui/backend-requests.md` (BR-1 → BR-9).

## 1. Nguyên tắc

- Mọi trường dữ liệu trên giao diện phải có trong `API_SPEC.md` hoặc `frontend/src/api/types.ts`. Chỗ nào thiếu: làm bằng dữ liệu hiện có, để `TODO(BR-n)`, không mock trong code chạy thật.
- Giá trị `[KÍCH THƯỚC TỆP]`, `[UUID]`, `[REQUEST_ID]` của artboard luôn lấy từ API (`file_size`, `id`, `ApiError.requestId`). Không hard-code.
- Không đổi logic: `api/client.ts` (chỉ thêm tham số lọc nếu cần), `api/sse.ts`, `features/chat/streamState.ts`, `AuthProvider`. Chỉ đổi hiển thị.
- Nhãn tiếng Việt, giữ enum nội bộ nguyên vẹn. Một file nhãn dùng chung (mục 3.0).
- Mỗi màn một commit, mỗi commit phải qua `npm run lint`, `typecheck`, `test`, `build`. e2e để CI chạy.

## 2. Hiện trạng so với thiết kế

Giống nhau: màu nhấn `#0F766E`, nền `#F4F7F9`, chữ `#141A21`, font Geist, bán kính 8 px. Sidebar thiết kế sáng (mục đang chọn `#E6F1F0`, chữ `#0B5A54`), hiện tại là sidebar tối. Thiết kế không có thanh tiêu đề trên cùng; mỗi trang tự có `h1`.

Chuyển động hiện có vi phạm quy tắc motion (chỉ CSS, chỉ `transform`/`opacity`, 150/220/320 ms, đường cong `cubic-bezier(0.2, 0, 0, 1)`, không trang trí ở Phân quyền và Nhật ký). Cần sửa trong `styles/index.css`:

| Hiện có | Vấn đề | Cách xử lý |
|---|---|---|
| `.motion-signal` (nền trôi vô hạn ở Login) | Trang trí, 12 s | Bỏ, xóa `SoftSignalBackground` khỏi Login |
| `.motion-shimmer` | Animate `background-position` | Thay bằng lớp phủ `transform: translateX` hoặc nhấp nháy `opacity` |
| `.spotlight-panel` (theo chuột) | Trang trí | Bỏ khỏi Chat |
| `.citation-inline` | `transition` trên màu và nền, 160 ms | Chỉ `transform`/`opacity`, 150 ms |
| `.citation-evidence` | Animate `text-decoration-color`, `background-color`, 520 ms | Gạch chân bằng lớp `::after` `scaleX`, 320 ms |
| `.citation-card-highlight` | Animate `box-shadow`, 1,4 s | Viền tĩnh + `opacity` ≤ 320 ms |
| Class Tailwind `transition` (màu/bóng) rải khắp | Animate nhiều thuộc tính | Xem quyết định D-2 |

Artboard cũng tự vi phạm quy tắc của nó: `eakaShimmer` animate `background-position`, `eakaSweep` animate `background-size`, `eaka-pop` 260 ms. Sẽ làm lại bằng `transform`/`opacity` và đúng token (pop = 220 ms).

## 3. Thứ tự ghép và chi tiết từng màn

Thứ tự theo yêu cầu: AppShell → Chat → Documents/DocumentDetail → Login → Upload/Permissions → admin → States → Profile/SystemStatus. Thêm commit 0 làm nền.

### 3.0 Commit 0: nền (tokens, nhãn, định dạng)
- `styles/index.css`: biến `--motion-fast: 150ms`, `--motion-base: 220ms`, `--motion-slow: 320ms`, `--ease: cubic-bezier(0.2, 0, 0, 1)`; các lớp `fade-up`, `slide-in`, `pop`; khối `prefers-reduced-motion` đã có, giữ. Dọn các mục ở bảng mục 2.
- `lib/labels.ts` (mới): bản đồ nhãn tiếng Việt cho vai trò, trạng thái tài liệu, phạm vi, mức quyền, đánh giá, kết quả nhật ký. Chốt mục (8) của handoff: **mọi màn dùng nhãn tiếng Việt**, enum chỉ là giá trị nội bộ. Trạng thái tài liệu: `UPLOADED` Đã tải lên, `PROCESSING` Đang xử lý, `READY` Sẵn sàng, `FAILED` Lỗi, `ARCHIVED` Lưu trữ. Artboard "DocumentStatus" dùng enum thô chỉ để minh họa chuyển động.
- `lib/format.ts`: ngày `dd/MM/yyyy HH:mm` (date-fns, locale `vi`), thay chữ "Unavailable" bằng "Không có", "ago" bằng "trước".
- `lib/permissions.ts`: `roleLabel` dùng bản đồ trên (Quản trị viên / Quản lý / Nhân viên).
- Backend cần: không.

### 3.1 AppShell (`layouts/AppShell.tsx`, `components/layout/PageHeader.tsx`)
- Thay đổi giao diện: sidebar sáng rộng 240–248 px, nhóm "Làm việc / Quản trị / Tài khoản"; mục: Trò chuyện, Tài liệu, Người dùng, Phòng ban, Phản hồi, Nhật ký hệ thống, Trạng thái hệ thống, Hồ sơ. Cuối sidebar: ký tự đầu tên, họ tên, vai trò (nhãn Việt), nút Đăng xuất (`aria-label`). Điều hướng di động giữ ngăn kéo (Escape để đóng). Bỏ thanh tiêu đề trên; `PageHeader` thành `h1` (hiện AppShell giữ `h1`, `PageHeader` dùng `h2`).
- Dữ liệu: `user.full_name`, `user.role`; `GET /health/ready` (đã dùng). Quyền xem mục giữ nguyên (`roles` của `navItems`).
- Khác biệt xử lý: huy hiệu "API ready" của thanh trên chuyển thành chấm trạng thái nhỏ ở cuối sidebar để không mất tính năng (D-6). Cần xem lại test `accessibility.qualification.spec.ts` vì đổi cấp tiêu đề.
- Backend: không.

### 3.2 Chat (`features/chat/ChatPage.tsx`, 1047 dòng; tách thành thành phần trình bày trong `features/chat/`)
- Thay đổi giao diện:
  - Ba cột: danh sách phiên (giữ, mục 5 handoff) | hội thoại | trích dẫn. Tiêu đề phiên + dòng "Chỉ trả lời từ tài liệu bạn được phép xem". Bỏ dòng "SSE strategy: buffer_after_validation" và nút "Phát lại" (chỉ có trong mockup).
  - Chờ câu trả lời: một dòng trạng thái "Đang tìm và kiểm tra nguồn…" theo `connecting/started`. Không dựng 3 bước giả, không ghi "qwen2.5:3b" hay "hybrid retrieval" (BR-6).
  - Câu trả lời xuất hiện cả khối sau khi kiểm tra xong (`fade-up` 320 ms), không hiệu ứng gõ chữ. Nhãn "Đã xác minh nguồn" + "N trích dẫn · chỉ từ tài liệu bạn được phép xem" (N = số citation thật).
  - **NO_ANSWER**: thẻ trung tính (nền xám nhạt, biểu tượng thông tin, không dùng màu đỏ/cảnh báo lỗi), nội dung lấy nguyên từ backend, nhãn "Không có nguồn", vẫn cho đánh giá hữu ích/chưa hữu ích (spec cho phép).
  - **"Chưa xác minh được…"** trong câu trả lời `ANSWERED`: chữ xám, không có số trích dẫn (BR-3).
  - Panel trích dẫn: giữ danh sách theo số thứ tự toàn hội thoại (logic `citationView` giữ nguyên). Bấm chip `[n]` thì thẻ tương ứng được chọn, cuộn tới và trượt vào (`slide-in` 320 ms). Gạch chân bằng chứng theo cách mới ở mục 2.
  - Ô nhập: placeholder "Hỏi về chính sách, quy trình nội bộ…", nút Gửi / Dừng. Giữ Ctrl+Enter.
  - Chuỗi tiếng Việt cho toast, trạng thái rỗng, lỗi, hộp xác nhận xóa phiên ("Cuộc trò chuyện chưa đặt tên", "N tin nhắn").
- Dữ liệu (đối chiếu API_SPEC §8, §8A): `chat/sessions` (title, message_count), messages (role, content, created_at, citations, `response_time_ms`), citation (`document_id`, `document_title`, `page_number`, `excerpt`, `evidence_text`, `citation_order`), SSE `stream.started` / `citations.ready` / `message.completed` (`grounding_status`). Phiên mới đặt tên "Cuộc trò chuyện mới" thay "New chat" (`title` do client gửi, được phép).
- Khác biệt xử lý: (5) giữ danh sách phiên, (6) "Mở tài liệu tại trang N" mở tab mới `/documents/:id/view?page=N` (trang xem PDF mới trong `features/documents/`, thanh đầu: tên tài liệu, "Trang N", Đóng, Tải xuống; nội dung PDF qua `blob:` từ `/download`, xem BR-2), mã tài liệu "ND-HR-007" và tên phòng ban trong thẻ trích dẫn chưa có trong `Citation` → bỏ, chỉ hiện tên tài liệu + "Trang N" (BR-1, BR-4).
- Backend: BR-2 (nên có, đã có đường tạm), BR-3, BR-6, BR-1, BR-4.
- Nhận thêm từ rà soát chéo: nhận diện câu chưa xác minh bằng hàm thuần có unit test, hai tiền tố (Việt + "Could not be verified from the documents you can access"); thẻ NO_ANSWER viền nét đứt nền xám badge "Chưa xác minh được"; câu xen kẽ chữ mờ + badge "Đã xác minh nguồn · N ý chưa xác minh"; tên model chỉ hiện khi `stream.started.model` có; Documents tự làm mới khi còn dòng `UPLOADED/PROCESSING`.
- Không đụng: `streamState.ts`, `sse.ts` và test của chúng.

### 3.3 Documents (`features/documents/DocumentsPage.tsx`)
- Thay đổi giao diện: tiêu đề "Tài liệu" + mô tả, nút "Tải lên tài liệu" (Admin/Manager, `canUploadDocuments`), bộ lọc Tìm kiếm / Phạm vi (Tất cả, Toàn công ty, Phòng ban, Riêng tư) / Trạng thái (nhãn Việt), bảng 5 cột Tài liệu | Phạm vi | Trạng thái | Cập nhật | Thao tác, phân trang "Trước/Sau" kèm tổng, trạng thái rỗng "Không có tài liệu phù hợp".
- Dữ liệu: `title`, `original_filename`, `file_size` (dòng phụ: tên tệp · kích thước thật), `status`, `access_scope`, `updated_at`; `meta.total`. Nút Phân quyền chỉ cho Admin như hiện tại.
- Khác biệt xử lý: dòng phụ "mã · N trang" của artboard → chưa có `document_code`, `page_count` (BR-1, BR-5); ô tìm kiếm ghi "Tên hoặc tên tệp" vì API tìm theo `title`, `original_filename`, `description`. Huy hiệu trạng thái chỉ animate khi trạng thái đổi (`key` + `pop` 220 ms), hàng READY đứng yên.
- Backend: BR-1, BR-5 (cải thiện, không chặn).

### 3.4 DocumentDetail (`features/documents/DocumentDetailPage.tsx`)
- Thay đổi giao diện: liên kết "← Tài liệu", huy hiệu trạng thái, tiêu đề, nút Tải xuống / Phân quyền (Admin) / Xóa. Khối "Thông tin" (tên tệp gốc, phạm vi, phòng ban, người tải lên, kích thước, ngày tạo, cập nhật, mã tài liệu ID) và khối "Trạng thái xử lý" dạng dòng thời gian 3 bước từ `status` (giữ polling 5 s khi `UPLOADED/PROCESSING`). Hộp xác nhận xóa theo lời của artboard ("Xóa tài liệu này?", giải thích bản ghi được giữ cho nhật ký, khớp soft delete trong spec). Toast "Đã xóa tài liệu".
- Dữ liệu: `DocumentItem`, `DocumentStatusResponse` (`error_message` đã được làm sạch). `[KÍCH THƯỚC TỆP]` = `formatBytes(file_size)`, `[UUID]` = `id`.
- Khác biệt xử lý: "Số trang" (BR-5), tên phòng ban và người tải lên (Admin tra qua danh sách; vai trò khác xem BR-4), phiên bản/hiệu lực (BR-1). Tên tệp tải xuống lấy từ header, mặc định bỏ "document.pdf" cứng nếu mime không phải PDF. Nút Xóa hiện đang hiện cho mọi vai trò (backend trả 403 nếu thiếu quyền); giữ nguyên hành vi (D-8).
- Backend: BR-1, BR-4, BR-5, BR-7.

### 3.5 Login (`features/auth/LoginPage.tsx`)
- Thay đổi giao diện: hai cột, cột trái giới thiệu ("Hỏi tài liệu nội bộ, nhận câu trả lời có nguồn.", ba nhãn tính năng), cột phải "Đăng nhập" + "Dùng tài khoản do quản trị viên cấp.", nút hiện/ẩn mật khẩu (`aria-label` đổi theo trạng thái), nút "Đang đăng nhập…" khi gửi, thông báo lỗi dạng `role="alert"`, dòng "Quên mật khẩu? Liên hệ quản trị viên…". Bỏ `SoftSignalBackground`.
- Dữ liệu: `POST /auth/login`. Lỗi đăng nhập sai lấy từ mã lỗi trong `API_ERROR_CODES.md`, ánh xạ sang "Email hoặc mật khẩu không đúng." trong `api/errors.ts` (sẽ đối chiếu khi làm).
- Khác biệt xử lý (D-3): email và mật khẩu điền sẵn trong artboard là dữ liệu UAT, KHÔNG đưa vào code. Liên kết "Vào trang Trò chuyện" chỉ là điều hướng mockup, bỏ. Owner đã duyệt: bỏ dòng chân "Tiểu luận chuyên ngành · 24LC10SP3" và nhãn "Chạy cục bộ" (chỉ còn hai nhãn "Trích dẫn từng ý", "Phân quyền theo phòng ban").
- Backend: không.

### 3.6 Upload (`features/documents/DocumentUploadPage.tsx`)
- Thay đổi giao diện: vùng kéo thả "Kéo thả tệp PDF vào đây hoặc bấm để chọn", thẻ tệp đã chọn (tên + kích thước thật từ `File.size`, nút "Bỏ tệp đã chọn" xóa giá trị form), Tiêu đề, Mô tả (tùy chọn), nhóm radio "Ai được xem tài liệu này?" (Riêng tư / Phòng ban / Toàn công ty, kèm mô tả ngắn) thay ô chọn, ô Phòng ban (giữ bộ lọc khi > 8 phòng), cột bên "Sau khi tải lên" mô tả đúng hành vi spec (kiểm tra định dạng/trùng, xử lý nền, Sẵn sàng thì dùng được). Giữ chuyển hướng sang chi tiết sau khi nhận (HTTP 202).
- Dữ liệu: `POST /documents/upload` với `file`, `title`, `description`, `access_scope`, `department_id`.
- Khác biệt xử lý:
  - (4) "Thông tin phiên bản (tùy chọn)" (4 trường): **chưa làm**, chờ BR-1 (spec chưa ghi). Chỉ để `TODO(BR-1)`. Khi BR-1 được merge: `<details>`, tối đa 128/64 ký tự, `effective_to >= effective_from`.
  - "13 trang" ở thẻ tệp: bỏ (BR-5), không cài thư viện đọc PDF.
  - "Quản lý chỉ tải lên được cho phòng ban của mình": chưa có dữ liệu để thực thi (BR-1 mục 3, BR-4). Hiện UI vẫn gọi `GET /departments` cho Manager (spec: Admin-only), cần xử lý lỗi 403 gọn gàng.
  - Bỏ câu "PDF… chỉ chứa ảnh sẽ báo lỗi" của artboard vì API còn nhận PNG/JPEG (OCR), chưa xác nhận (D-4). Giữ "Chỉ nhận PDF" như thiết kế và code hiện tại.
- Backend: BR-1 (bắt buộc), BR-4.
- Test hiện có: `DocumentUploadPage.test.tsx` cần cập nhật theo nhãn mới.

### 3.7 Permissions (`features/documents/DocumentPermissionsPage.tsx`)
- Thay đổi giao diện: liên kết quay lại, tiêu đề, câu mô tả phạm vi hiện tại ("Phòng ban · Nhân sự", từ `access_scope` + tên phòng ban), khối "Cấp quyền trực tiếp": chọn Đối tượng (Người dùng / Phòng ban) dạng nút chọn một, ô chọn đối tượng, Quyền (Xem / Sửa / Quản lý), nút "Cấp quyền". Bảng: Đối tượng | Loại | Quyền | Thao tác ("Thu hồi"). Rỗng: "Chưa có quyền cấp trực tiếp nào." Lỗi 409 `DOCUMENT_PERMISSION_ALREADY_EXISTS` → "Quyền này đã tồn tại."
- Dữ liệu: `GET/POST/DELETE /documents/{id}/permissions`, `GET /users`, `GET /departments` (Admin, đã dùng). Tên đối tượng tra từ hai danh sách này (giới hạn hiện có: tối đa 100 mục mỗi danh sách).
- Khác biệt xử lý: không animate trang trí ở màn này. Mã tài liệu ở breadcrumb chờ BR-1, tạm dùng tên tài liệu.
- Backend: BR-1 (nhỏ). Test hiện có: `DocumentPermissionsPage.test.tsx` cập nhật nhãn.

### 3.8 Admin
**Users (`features/admin/UsersPage.tsx`)**
- Giao diện: tiêu đề + mô tả, nút "Tạo người dùng" mở ngăn kéo bên phải (thành phần mới `Drawer` có bẫy focus, Escape đóng); lọc Tìm kiếm / Vai trò / Trạng thái (Đang hoạt động, Đã vô hiệu hóa); bảng Người dùng (ký tự đầu + tên + email) | Vai trò | Phòng ban | Trạng thái | Thao tác (Sửa, Vô hiệu hóa/Kích hoạt lại). Sửa người dùng cũng dùng ngăn kéo.
- Khác biệt (2): ô "Department ID" thô → ô chọn phòng ban từ `GET /departments` (page_size 100, kèm ô lọc khi nhiều). Luật theo spec: Manager/Staff bắt buộc có phòng ban, Admin được để trống; mật khẩu ≥ 12 ký tự. Lọc trạng thái dùng `is_active` (spec có), thêm tham số vào `client.users.list`. Tên phòng ban trong bảng tra từ danh sách phòng ban.
- Backend: không.

**Departments (`features/admin/DepartmentsPage.tsx`)**
- Giao diện: form tạo (Tên, Mã kèm gợi ý "Chữ không dấu, số, dấu _ hoặc -", Mô tả), bảng Tên | Mã | Mô tả | Thao tác, hộp xác nhận xóa.
- Khác biệt (D-5): artboard viết "chỉ xóa được khi không còn người dùng hoặc tài liệu"; spec chỉ chặn khi còn **người dùng đang hoạt động** (`409 DEPARTMENT_IN_USE`). Dùng lời đúng spec.
- Backend: không.

**Feedback (`features/feedback/FeedbackPage.tsx`)**
- Giao diện: nút chọn một Tất cả / Hữu ích / Chưa hữu ích (thay ô chọn), thẻ/bảng với đánh giá, ghi chú (`reason`), người dùng, phòng ban, thời gian.
- Khác biệt (3): lọc theo đánh giá (đã có tham số `rating`). Ô "Department ID" thô → ô chọn phòng ban, chỉ hiện cho Admin (spec: bộ lọc này chỉ dành cho Admin, Manager đã bị giới hạn theo phòng ban). Bỏ số đếm theo từng tab (API chỉ trả tổng của bộ lọc hiện tại); hiện "N phản hồi".
- **Mâu thuẫn (D-1)**: artboard hiện nội dung câu hỏi và câu trả lời của từng phản hồi, nhưng API_SPEC §9 cố ý không trả chúng. Không làm theo artboard; không tạo BR vì trái chính sách.
- Backend: BR-4 (tên người dùng/phòng ban cho Manager).

**AuditLogs (`features/audit/AuditLogsPage.tsx`)**
- Giao diện: bộ lọc Loại sự kiện / Kết quả (Thành công, Thất bại) / Request ID, bảng Thời gian | Sự kiện | Người thực hiện | Đối tượng | Kết quả | Chi tiết, hàng mở rộng (Request ID thật, mã lỗi, loại đối tượng, metadata JSON), phân trang "Trang x / y". Không animate trang trí.
- Khác biệt: "Địa chỉ IP" của artboard không có trong `AuditLogItem` → bỏ. Loại sự kiện giữ ô nhập tự do tới khi có BR-9. Người thực hiện và đối tượng hiện UUID rút gọn ("Hệ thống" nếu `actor_user_id = null`).
- Backend: BR-9 (tùy chọn).

### 3.9 States (`components/ui/State.tsx`, `routes/*`)
- Giao diện: rỗng (tiêu đề + mô tả + nút hành động), đang tải bằng khung xương giữ đúng kích thước nội dung (`SkeletonRows`), lỗi "Không tải được dữ liệu" + `request_id` thật + "Thử lại", 403 "Bạn không có quyền xem trang này", 404 "Không tìm thấy trang".
- Dữ liệu: `request_id` lấy từ `ApiError.requestId` (có sẵn); không có thì ẩn dòng đó. Câu 403 viết chung ("Trang này chỉ dành cho vai trò được cấp quyền") vì artboard nói "chỉ dành cho quản trị viên" mà có trang dành cho cả Manager.
- Backend: không. Test hiện có: `State.test.tsx`, cập nhật.

### 3.10 Profile (`features/profile/ProfilePage.tsx`)
- Giao diện: ký tự đầu tên, họ tên, email, chip "Hoạt động/Vô hiệu hóa", Vai trò (nhãn Việt), Phòng ban, đoạn giải thích quyền xem theo vai trò (Nhân viên/Quản lý theo lời artboard; Admin: xem được mọi tài liệu), "muốn đổi mật khẩu hoặc phòng ban hãy liên hệ quản trị viên" (đúng spec: PATCH user không đổi mật khẩu).
- Khác biệt: tên phòng ban (BR-4); tạm hiện "Đã gán phòng ban" khi không tra được, "Chưa gán" khi `department_id = null`.
- Backend: BR-4.

### 3.11 SystemStatus (`features/system/SystemStatusPage.tsx`)
- Giao diện: tiêu đề, "Kiểm tra lần cuối: …" (từ `dataUpdatedAt`), nút "Kiểm tra lại" (refetch thật, không đếm giờ giả), nhóm "Hạ tầng" (API live, API ready, PostgreSQL, Redis kèm nguồn `GET /health/live`, `checks.database`…), nhóm "Mô hình ngôn ngữ và truy xuất".
- Khác biệt: artboard điền sẵn "Ollama", "qwen2.5:3b", "lexical_fallback" → không có trong API công khai. Chỉ hiện các dòng hợp đồng đã biết (chiến lược trả lời, "gửi sau khi kiểm tra xong"). Nhà cung cấp/mô hình cho Admin chờ BR-8. Giữ dòng "Chỉ hiển thị thông tin backend thật sự cung cấp…".
- Backend: BR-8 (tùy chọn).

## 4. Chuỗi commit dự kiến

0 nền · 1 AppShell · 2 Chat · 3 Documents · 4 DocumentDetail · 5 Login · 6 Upload · 7 Permissions · 8 Users · 9 Departments · 10 Feedback · 11 AuditLogs · 12 States · 13 Profile · 14 SystemStatus. Một PR nháp (draft), không merge. Cuối mỗi đợt: màn đã xong, mô tả thay đổi, BR mới.

## 5. Quyết định của owner (17/11/2026)

Đã chốt: D-1 giữ chính sách riêng tư Feedback; D-3 bỏ dòng "Tiểu luận…" và "Chạy cục bộ"; D-7 làm thật bằng tab mới `/documents/:id/view?page=N` (xem 3.2, BR-2); D-2, D-4, D-5, D-6, D-8 dùng mặc định trong bảng. Bảng dưới giữ để tra cứu.

| # | Câu hỏi | Mặc định |
|---|---|---|
| D-1 | Feedback: artboard hiện câu hỏi/câu trả lời, API cố ý không trả. Giữ chính sách riêng tư? | Giữ. Hiện đánh giá, ghi chú, người dùng, phòng ban, thời gian |
| D-2 | Hover/focus: artboard đổi `background-color` 150 ms, mâu thuẫn "chỉ transform/opacity". Cho phép riêng hover/focus? | Cho phép đổi màu hover/focus (không gây reflow); mọi chuyển động khác tuân quy tắc |
| D-3 | Login: dòng "Tiểu luận chuyên ngành · 24LC10SP3" và nhãn "Chạy cục bộ" có đưa vào? | Không đưa vào tới khi xác nhận; email/mật khẩu mẫu không bao giờ đưa vào |
| D-4 | Upload: giữ "Chỉ nhận PDF" dù API nhận cả PNG/JPEG? | Giữ PDF, bỏ câu về PDF chỉ chứa ảnh |
| D-5 | Phòng ban: dùng lời xóa đúng spec (chỉ chặn khi còn người dùng đang hoạt động)? | Có |
| D-6 | Bỏ thanh tiêu đề trên, đưa trạng thái API thành chấm nhỏ ở sidebar? | Có |
| D-7 | "Mở tài liệu tại trang N" trong lúc chờ BR-2: (A) ẩn liên kết, hoặc (B) tải blob qua `/download` rồi mở `blob:…#page=N` (không cần backend, nhưng tải cả tệp và phụ thuộc trình xem PDF của trình duyệt)? | (A) |
| D-8 | Nút Xóa ở chi tiết tài liệu đang hiện cho mọi vai trò (backend trả 403). Giữ? | Giữ, không đổi hành vi |

## 6. Môi trường thực hiện

Code giao diện do Claude Code chạy trực tiếp trên máy Windows (git, npm lint/typecheck/test/build chạy được). Các rào cản git/node_modules chỉ áp dụng cho phiên chat Linux dùng để lập kế hoạch.

## 7. Hạn chế đã biết (22/11/2026)

- **Mở tài liệu đúng trang (D-7, BR-2):** liên kết "Mở tài liệu tại trang N" gắn `#page=N` vào `blob:` URL của
  PDF lấy từ `/preview`. Mới kiểm trên Chromium (trình xem PDF của Chrome và Edge): bằng Playwright với
  Chromium bản đầy đủ, trên một PDF 6 trang (mở ở 4/6) và trên stack eaka-smoke (mở ở 4/13). Firefox
  và Safari **chưa kiểm**. Ở trình duyệt không đọc `#page`, tài liệu vẫn mở, nhưng ở trang 1. Ảnh
  PNG/JPEG không có trang, nên không gắn `#page`.
- **Refresh token dùng chung giữa hai tab (BR-2):**
  - Token nằm trong `sessionStorage`. Liên kết dùng `rel="opener"` để tab xem tài liệu nhận bản sao
    token.
  - Hai tab vì vậy dùng chung một refresh token, mà refresh thì xoay vòng token (API_SPEC §4). Nếu
    tab xem tài liệu phải refresh (access token sắp hết hạn lúc mở), tab gốc sẽ bị đăng xuất ở lần
    refresh sau.
  - Chỉ gỡ được rủi ro này bằng URL ký tạm thời; backend chưa làm (xem khối trả lời BR-2).
- **BR-5, BR-6, BR-7 đang hoãn** theo quyết định của owner:
  - BR-5: không hiện số trang ở danh sách, chi tiết và thẻ tệp khi tải lên.
  - BR-6: lúc chờ câu trả lời chỉ có một dòng trạng thái "Đang tìm và kiểm tra nguồn…", không có
    tiến trình theo bước.
  - BR-7: dòng thời gian xử lý tài liệu có 3 bước, suy từ `status`, không có giai đoạn chi tiết.
- **Ranh giới phiên trong một tab:**
  - Khi người dùng đổi (đăng nhập, đăng xuất, phiên hết hạn), `useSessionDataReset` hủy các query đang
    chạy rồi gọi `queryClient.clear()` (gồm cả query và mutation). Trang của người mới chỉ được dựng
    sau khi cache đã rỗng. Toast bị xóa khi có người đăng nhập.
  - Bản nháp chat, luồng SSE và form nằm trong state của trang, dưới `ProtectedRoute`, nên bị hủy cùng
    trang; SSE abort khi trang unmount. Ngoài token trong `sessionStorage` (AuthProvider xóa), app không
    lưu gì vào `localStorage`, IndexedDB hay Cache API.
  - Còn lại 2 điểm chưa xử lý:
    1. Một lượt refresh token đang chạy đúng lúc đăng xuất có thể ghi lại token mới vào
       `sessionStorage` sau khi đã xóa (`refreshAccessToken` trong `api/client.ts`). Tải lại tab khi đó
       sẽ khôi phục phiên cũ. Cách sửa đề xuất: chỉ lưu khi refresh token hiện tại vẫn là token đã gửi
       đi. Cần owner đồng ý vì `client.ts` không được đổi logic.
    2. Khi phiên hết hạn, màn đăng nhập giữ đường dẫn cuối (`from`) để quay lại đúng chỗ. Nếu người
       khác đăng nhập ở tab đó, họ được đưa tới đường dẫn ấy. Đường dẫn có thể chứa id tài liệu, nhưng
       API vẫn kiểm quyền, nên nội dung không lộ.
