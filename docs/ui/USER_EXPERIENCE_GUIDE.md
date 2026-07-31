# Huong Dan Trai Nghiem Frontend UAT

Tai lieu nay danh cho moi truong local/test cua **Enterprise AI Knowledge Assistant**. Khong dung cac tai khoan, mat khau, hoac provider trong tai lieu nay cho production.

## 1. Khoi Dong He Thong

Chay stack backend, frontend va provider LLM deterministic chi danh cho UAT:

```powershell
$env:UAT_SEED_ENABLED="true"
$env:UAT_ADMIN_PASSWORD="<local-uat-admin-password>"
$env:UAT_MANAGER_PASSWORD="<local-uat-manager-password>"
$env:UAT_STAFF_PASSWORD="<local-uat-staff-password>"

docker compose -f compose.yaml -f compose.uat.yaml --profile frontend --profile test build
docker compose -f compose.yaml -f compose.uat.yaml --profile frontend up -d
docker compose -f compose.yaml -f compose.uat.yaml run --rm api python -m app.scripts.seed_uat_data
```

`compose.uat.yaml` chi bat provider OpenAI-compatible gia lap local cho UAT. No khong goi provider LLM ben ngoai va khong can API key.

## 2. URL Frontend

- Frontend: `http://localhost:5173`
- Backend: `http://127.0.0.1:8000`
- API docs: `http://127.0.0.1:8000/docs`

Nen mo frontend bang `localhost:5173` trong UAT vi origin nay duoc cau hinh CORS cho browser.

## 3. Tai Khoan Admin

- Username: `admin.uat@example.test`
- Password: gia tri `UAT_ADMIN_PASSWORD` trong shell local.

## 4. Tai Khoan Manager

- Username: `manager.uat@example.test`
- Password: gia tri `UAT_MANAGER_PASSWORD` trong shell local.

## 5. Tai Khoan Staff

- Username: `staff.uat@example.test`
- Password: gia tri `UAT_STAFF_PASSWORD` trong shell local.

## 6. Chuc Nang Nen Thu Theo Tung Role

Admin:
- Dang nhap, mo Documents, Users, Departments, Feedback, Audit logs, System status.
- Tao user UAT moi, deactivate user vua tao.
- Tao department UAT moi.
- Upload PDF, cho trang thai `READY`, cap va thu hoi document permission.
- Xem audit log sau cac thao tac.

Manager:
- Dang nhap, mo Documents va Feedback.
- Kiem tra khong thay route Users, Departments, Audit logs.
- Thu truy cap truc tiep `/users` de thay Access denied.
- Xem document neu duoc Admin cap direct permission.

Staff:
- Dang nhap, mo Chat va Documents.
- Tao chat session, gui cau hoi ve "UAT travel approval policy".
- Xem cau tra loi SSE da validate, citation card va gui feedback.
- Thu truy cap truc tiep `/audit-logs` de thay Access denied.

## 7. Cach Upload Tai Lieu

1. Dang nhap bang Admin hoac Manager.
2. Vao Documents.
3. Chon Upload PDF.
4. Nhap Title, Description, Access scope.
5. Chon file PDF khong chua du lieu mat.
6. Bam Upload.

Upload HTTP thanh cong chi co nghia la backend da nhan file. Worker se xu ly tiep.

## 8. Cach Cho Document READY

Sau upload, trang detail se hien Processing status. Cho status chuyen qua:

- `UPLOADED`: backend da tao record va enqueue worker.
- `PROCESSING`: worker dang xu ly.
- `READY`: tai lieu da san sang cho retrieval/chat.
- `FAILED`: worker khong xu ly duoc; xem safe error message.

Neu can cap nhat nhanh, reload trang detail hoac quay lai Document library.

## 9. Cach Chat Va Xem Citation

1. Dang nhap bang Staff.
2. Vao Chat.
3. Bam New session hoac dung session hien co.
4. Hoi: `According to the UAT travel approval policy, what approval is required before booking travel?`
5. UI se hien trang thai dang tim va kiem chung nguon.
6. Khi stream hoan tat, cau tra loi va citation card se xuat hien.

TASK-027 dung chien luoc `buffer_after_validation`, nen UI khong hien token-by-token thuc su. Noi dung chi xuat hien sau khi backend da validate grounding va citation.

## 10. Cach Dung Cau Tra Loi

Khi dang stream, bam Stop. Browser se abort request SSE. Backend khong persist assistant message mot phan.

## 11. Cach Gui Feedback

Trong Chat, dung nut Helpful hoac Not helpful tren assistant answer. Feedback report co the xem bang Admin hoac Manager theo RBAC.

## 12. Cach Kiem Tra Audit

Dang nhap bang Admin, vao Audit logs. Kiem tra cac event sau thao tac:

- Auth/login.
- Document upload.
- Permission grant/revoke.
- User create/deactivate.
- Chat question/answer.
- Feedback.

Audit log khong hien password, bearer token, prompt, document content, full answer, provider payload, API key, hoac raw exception.

## 13. Gioi Han Hien Tai

- Provider status chi hien nhung gi public health API cung cap; backend chua co endpoint provider-status rieng.
- React Bits chua duoc import nhu package/export chinh thuc; UI dung cac motion primitive local lay cam hung tu React Bits va co reduced-motion.
- Document permission form yeu cau user/department UUID vi backend hien chua co selector endpoint rieng.
- React Router advisory van duoc document cho SPA-only usage; khong dung RSC/actions/SSR redirects.
- Explicit cross-instance cancel endpoint khong co; Stop generation dung browser request abort.

## 14. Cach Dung He Thong Khong Mat Du Lieu

Dung an toan, giu volume database:

```powershell
docker compose -f compose.yaml -f compose.uat.yaml stop
```

Hoac neu muon xoa container nhung giu volume:

```powershell
docker compose -f compose.yaml -f compose.uat.yaml down
```

Khong dung `docker compose down -v` neu muon giu database va uploaded files.
