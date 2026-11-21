import { StatusLink, StatusPage } from "../components/ui/State";

export function NotFoundPage() {
  return (
    <StatusPage
      code="404"
      title="Không tìm thấy trang"
      description="Đường dẫn không tồn tại hoặc tài liệu đã bị xóa."
      action={<StatusLink to="/documents">Quay lại danh sách tài liệu</StatusLink>}
    />
  );
}
