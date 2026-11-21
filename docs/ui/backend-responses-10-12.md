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
