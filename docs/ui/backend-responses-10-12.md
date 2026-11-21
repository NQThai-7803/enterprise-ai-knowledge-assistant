# Trả lời của backend cho BR-10, BR-11, BR-12

Phiên backend, ngày 21/11/2026, nhánh `feat/ui-br-10-12`. Các mục BR-10 và BR-11 nằm trong
`docs/ui/backend-requests.md` trên nhánh `feat/ui-redesign`; BR-12 do owner thêm. Phiên UI gộp
các khối dưới đây vào file BR sau. Trường mới chỉ có trên `main` sau khi PR này merge; API vẫn là
`/api/v1`, không trường cũ nào đổi tên hay bị bỏ.

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
