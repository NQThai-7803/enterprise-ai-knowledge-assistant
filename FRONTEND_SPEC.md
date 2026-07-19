# Frontend Specification

## 1. Phạm vi

Frontend được thực hiện sau khi backend MVP ổn định. Công nghệ dự kiến:

- React.
- TypeScript.
- Vite.
- UI library sẽ được quyết định trước Task frontend đầu tiên.

## 2. Layout

### Auth layout

- Login page.
- Không hiển thị sidebar.

### Application layout

- Sidebar theo role.
- Top bar hiển thị user, department và logout.
- Main content.
- Responsive cho desktop và tablet; mobile là mức hỗ trợ phụ ở MVP.

## 3. Pages

### Login

- Email.
- Password.
- Loading state.
- Error message an toàn.

### Dashboard

MVP hiển thị:

- Số tài liệu READY.
- Tài liệu PROCESSING/FAILED.
- Số chat session của user.
- Câu hỏi gần đây.

### Documents

- Table hoặc card list.
- Search.
- Filter status và access scope.
- Upload modal.
- Processing status.
- Action theo permission.

### Document detail

- Metadata.
- Processing status.
- Download.
- Reprocess cho người có quyền.
- Không hiển thị storage path nội bộ.

### Chat

```text
Left sidebar: chat sessions
Center: conversation
Right drawer/panel: citations and document preview
```

- New chat.
- Loading/streaming state nếu backend hỗ trợ.
- Citation chips.
- Feedback buttons.
- No-answer state.

### User management

Admin only:

- List users.
- Create/edit/deactivate.
- Assign role and department.

### Audit logs

Admin only:

- Filter action, user và date.
- Không hiển thị secret hoặc raw token.

## 4. Role-aware navigation

| Menu | Admin | Manager | Staff |
|---|---:|---:|---:|
| Dashboard | Yes | Yes | Yes |
| Chat | Yes | Yes | Yes |
| Documents | Yes | Yes | Yes |
| Users | Yes | No | No |
| Departments | Yes | No | No |
| Feedback report | Yes | Department | No |
| Audit logs | Yes | No | No |

Frontend chỉ hỗ trợ UX; backend vẫn là nguồn kiểm soát quyền chính thức.

## 5. API client

- Base URL từ environment.
- Gắn access token tự động.
- Refresh token theo flow backend.
- Khi refresh thất bại, logout và chuyển về login.
- Chuẩn hóa error handling.

## 6. Security

- Không lưu password.
- Không render raw HTML từ AI nếu chưa sanitize.
- Không tin role do client tự sửa.
- Không expose internal IDs không cần thiết trong URL công khai.
- Download qua authenticated endpoint.
