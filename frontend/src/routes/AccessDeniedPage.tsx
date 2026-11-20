import { StatusLink, StatusPage } from "../components/ui/State";

export function AccessDeniedPage() {
  // Written for every restricted page, since some are open to Managers too, not only Admins.
  return (
    <StatusPage
      code="403"
      title="Bạn không có quyền xem trang này"
      description="Trang này chỉ dành cho vai trò được cấp quyền. Nếu bạn cần truy cập, hãy liên hệ người quản lý hệ thống."
      action={
        <StatusLink to="/chat" primary>
          Về trang Trò chuyện
        </StatusLink>
      }
    />
  );
}
