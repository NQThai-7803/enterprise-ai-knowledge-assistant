import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronLeft, Info } from "lucide-react";
import { useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useParams } from "react-router-dom";
import { z } from "zod";
import { apiClient } from "../../api/client";
import { isApiError, safeErrorMessage } from "../../api/errors";
import type { Department, DocumentItem, DocumentPermission, User } from "../../api/types";
import { DataTable } from "../../components/data/DataTable";
import { useToast } from "../../components/feedback/ToastProvider";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { ConfirmDialog } from "../../components/ui/ConfirmDialog";
import { FieldWrapper, SelectInput, TextInput } from "../../components/ui/Field";
import { EmptyState, ErrorState, LoadingState } from "../../components/ui/State";
import { truncateMiddle } from "../../lib/format";
import { accessScopeLabels, permissionLevelLabels } from "../../lib/labels";

const permissionSchema = z.object({
  grantee_type: z.enum(["user", "department"]),
  grantee_id: z.string().trim().min(1, "Vui lòng chọn người dùng hoặc phòng ban."),
  permission: z.enum(["VIEW", "EDIT", "MANAGE"]),
});

type PermissionForm = z.infer<typeof permissionSchema>;

const defaultGrant: PermissionForm = {
  grantee_type: "user",
  grantee_id: "",
  permission: "VIEW",
};

const GRANTEE_TYPES = [
  ["user", "Người dùng"],
  ["department", "Phòng ban"],
] as const;

export function DocumentPermissionsPage() {
  const { documentId } = useParams();
  const queryClient = useQueryClient();
  const { pushToast } = useToast();
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [grantDraft, setGrantDraft] = useState<PermissionForm>(defaultGrant);
  const [userFilter, setUserFilter] = useState("");
  const [departmentFilter, setDepartmentFilter] = useState("");
  const {
    register,
    handleSubmit,
    reset,
    setValue,
    clearErrors,
    formState: { errors },
  } = useForm<PermissionForm>({ resolver: zodResolver(permissionSchema), defaultValues: defaultGrant });

  const detailQuery = useQuery({
    queryKey: ["documents", "detail", documentId],
    queryFn: () => apiClient.documents.detail(documentId as string),
    enabled: Boolean(documentId),
  });

  const permissionsQuery = useQuery({
    queryKey: ["documents", "permissions", documentId],
    queryFn: () => apiClient.documents.permissions(documentId as string),
    enabled: Boolean(documentId),
  });

  const usersQuery = useQuery({
    queryKey: ["users", "permission-selector"],
    queryFn: () => apiClient.users.list({ page: 1, page_size: 100, is_active: true }),
    staleTime: 5 * 60_000,
  });

  const departmentsQuery = useQuery({
    queryKey: ["departments", "permission-selector"],
    queryFn: () => apiClient.departments.list({ page: 1, page_size: 100 }),
    staleTime: 5 * 60_000,
  });

  const documentItem = detailQuery.data?.data;
  const permissions = useMemo(() => permissionsQuery.data?.data ?? [], [permissionsQuery.data]);
  const users = useMemo(() => usersQuery.data?.data ?? [], [usersQuery.data]);
  const departments = useMemo(() => departmentsQuery.data?.data ?? [], [departmentsQuery.data]);
  const usersById = useMemo(() => new Map(users.map((user) => [user.id, user])), [users]);
  const departmentsById = useMemo(
    () => new Map(departments.map((department) => [department.id, department])),
    [departments],
  );
  const filteredUsers = useMemo(() => {
    const query = normalizeFilter(userFilter);
    if (!query) {
      return users;
    }
    return users.filter((user) => normalizeFilter(`${user.full_name} ${user.email}`).includes(query));
  }, [userFilter, users]);
  const filteredDepartments = useMemo(() => {
    const query = normalizeFilter(departmentFilter);
    if (!query) {
      return departments;
    }
    return departments.filter((department) => normalizeFilter(`${department.name} ${department.code}`).includes(query));
  }, [departmentFilter, departments]);
  const activeSelectorBusy = grantDraft.grantee_type === "user" ? usersQuery.isLoading : departmentsQuery.isLoading;
  const activeSelectorError = grantDraft.grantee_type === "user" ? usersQuery.isError : departmentsQuery.isError;
  const activeSelectorEmpty = grantDraft.grantee_type === "user" ? users.length === 0 : departments.length === 0;

  const duplicateGrant = permissions.some((permission) => {
    const granteeMatches =
      grantDraft.grantee_type === "user"
        ? permission.user_id === grantDraft.grantee_id
        : permission.department_id === grantDraft.grantee_id;
    return granteeMatches && permission.permission === grantDraft.permission;
  });

  const grantMutation = useMutation({
    mutationFn: (values: PermissionForm) =>
      apiClient.documents.grantPermission(documentId as string, {
        user_id: values.grantee_type === "user" ? values.grantee_id : null,
        department_id: values.grantee_type === "department" ? values.grantee_id : null,
        permission: values.permission,
      }),
    onSuccess: async () => {
      reset(defaultGrant);
      setGrantDraft(defaultGrant);
      setUserFilter("");
      setDepartmentFilter("");
      await queryClient.invalidateQueries({ queryKey: ["documents", "permissions", documentId] });
      pushToast({ tone: "success", title: "Đã cấp quyền" });
    },
    onError: (error) => pushToast({ tone: "error", title: "Cấp quyền thất bại", message: grantErrorMessage(error) }),
  });

  const revokeMutation = useMutation({
    mutationFn: (permissionId: string) => apiClient.documents.revokePermission(documentId as string, permissionId),
    onSuccess: async () => {
      setDeleteId(null);
      await queryClient.invalidateQueries({ queryKey: ["documents", "permissions", documentId] });
      pushToast({ tone: "success", title: "Đã thu hồi quyền" });
    },
    onError: (error) => pushToast({ tone: "error", title: "Thu hồi thất bại", message: safeErrorMessage(error) }),
  });

  const granteeTypeField = register("grantee_type", {
    onChange: (event) => {
      const granteeType = event.target.value as PermissionForm["grantee_type"];
      setValue("grantee_id", "", { shouldDirty: true, shouldValidate: false });
      clearErrors("grantee_id");
      setGrantDraft((current) => ({ ...current, grantee_type: granteeType, grantee_id: "" }));
    },
  });
  const granteeIdField = register("grantee_id", {
    onChange: (event) => setGrantDraft((current) => ({ ...current, grantee_id: event.target.value })),
  });
  const permissionField = register("permission", {
    onChange: (event) =>
      setGrantDraft((current) => ({ ...current, permission: event.target.value as PermissionForm["permission"] })),
  });

  // No decorative motion on this screen (motion rules).
  return (
    <div>
      <Link
        to={`/documents/${documentId}`}
        className="mb-5 inline-flex items-center gap-1 text-sm text-muted transition hover:text-ink"
      >
        <ChevronLeft className="h-4 w-4" aria-hidden="true" />
        {documentItem?.document_code ?? documentItem?.title ?? "Tài liệu"}
      </Link>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-normal text-ink">Phân quyền tài liệu</h1>
        {documentItem ? <p className="mt-1 text-sm text-muted">{documentItem.title}</p> : null}
      </div>

      {documentItem ? (
        <p className="mb-5 flex gap-3 rounded-xl border border-border/70 bg-surface px-5 py-4 text-sm text-ink/80">
          <Info className="mt-0.5 h-4 w-4 shrink-0 text-accent" aria-hidden="true" />
          <span>{scopeSummary(documentItem, departmentsById)}</span>
        </p>
      ) : null}

      <form
        className="mb-5 rounded-xl border border-border/70 bg-surface p-5"
        onSubmit={handleSubmit((values) => grantMutation.mutate(values))}
        noValidate
      >
        <h2 className="mb-4 text-[15px] font-semibold">Cấp quyền trực tiếp</h2>
        <div className="grid items-start gap-4 lg:grid-cols-[auto_minmax(0,1fr)_11rem_auto]">
          <fieldset>
            <legend className="mb-1.5 text-sm font-medium text-ink">Đối tượng</legend>
            <div className="inline-flex rounded-token bg-elevated p-1">
              {GRANTEE_TYPES.map(([value, label]) => (
                <label
                  key={value}
                  className="cursor-pointer rounded-[6px] px-3.5 py-1.5 text-sm text-muted has-[:checked]:bg-surface has-[:checked]:font-medium has-[:checked]:text-ink has-[:checked]:shadow-sm has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-accent/30"
                >
                  <input type="radio" value={value} className="sr-only" {...granteeTypeField} />
                  {label}
                </label>
              ))}
            </div>
          </fieldset>
          {grantDraft.grantee_type === "user" ? (
            <div className="space-y-3">
              {users.length > 8 ? (
                <FieldWrapper id="user_filter" label="Tìm người dùng" help="Lọc theo tên hoặc email.">
                  <TextInput
                    id="user_filter"
                    value={userFilter}
                    onChange={(event) => setUserFilter(event.target.value)}
                    disabled={usersQuery.isLoading}
                  />
                </FieldWrapper>
              ) : null}
              <FieldWrapper id="grantee_id" label="Chọn người dùng" error={errors.grantee_id?.message}>
                <SelectInput
                  id="grantee_id"
                  {...granteeIdField}
                  disabled={usersQuery.isLoading || usersQuery.isError || users.length === 0}
                >
                  <option value="">{usersQuery.isLoading ? "Đang tải người dùng…" : "Chọn người dùng"}</option>
                  {filteredUsers.map((user) => (
                    <option key={user.id} value={user.id}>
                      {formatUserOption(user)}
                    </option>
                  ))}
                </SelectInput>
              </FieldWrapper>
              {renderSelectorState({
                isLoading: usersQuery.isLoading,
                isError: usersQuery.isError,
                total: users.length,
                filteredTotal: filteredUsers.length,
                loadingLabel: "Đang tải người dùng…",
                emptyLabel: "Chưa có người dùng nào.",
                emptyFilterLabel: "Không có người dùng khớp bộ lọc.",
                errorLabel: "Không tải được danh sách người dùng.",
                onRetry: () => void usersQuery.refetch(),
              })}
            </div>
          ) : (
            <div className="space-y-3">
              {departments.length > 8 ? (
                <FieldWrapper id="department_filter" label="Tìm phòng ban" help="Lọc theo tên hoặc mã.">
                  <TextInput
                    id="department_filter"
                    value={departmentFilter}
                    onChange={(event) => setDepartmentFilter(event.target.value)}
                    disabled={departmentsQuery.isLoading}
                  />
                </FieldWrapper>
              ) : null}
              <FieldWrapper id="grantee_id" label="Chọn phòng ban" error={errors.grantee_id?.message}>
                <SelectInput
                  id="grantee_id"
                  {...granteeIdField}
                  disabled={departmentsQuery.isLoading || departmentsQuery.isError || departments.length === 0}
                >
                  <option value="">{departmentsQuery.isLoading ? "Đang tải phòng ban…" : "Chọn phòng ban"}</option>
                  {filteredDepartments.map((department) => (
                    <option key={department.id} value={department.id}>
                      {formatDepartmentOption(department)}
                    </option>
                  ))}
                </SelectInput>
              </FieldWrapper>
              {renderSelectorState({
                isLoading: departmentsQuery.isLoading,
                isError: departmentsQuery.isError,
                total: departments.length,
                filteredTotal: filteredDepartments.length,
                loadingLabel: "Đang tải phòng ban…",
                emptyLabel: "Chưa có phòng ban nào.",
                emptyFilterLabel: "Không có phòng ban khớp bộ lọc.",
                errorLabel: "Không tải được danh sách phòng ban.",
                onRetry: () => void departmentsQuery.refetch(),
              })}
            </div>
          )}
          <FieldWrapper id="permission" label="Quyền" error={errors.permission?.message}>
            <SelectInput id="permission" {...permissionField}>
              {(["VIEW", "EDIT", "MANAGE"] as const).map((level) => (
                <option key={level} value={level}>
                  {permissionLevelLabels[level]}
                </option>
              ))}
            </SelectInput>
          </FieldWrapper>
          <div className="lg:pt-[26px]">
            <Button
              type="submit"
              disabled={duplicateGrant || activeSelectorBusy || activeSelectorError || activeSelectorEmpty}
              loading={grantMutation.isPending}
            >
              Cấp quyền
            </Button>
          </div>
        </div>
        {duplicateGrant ? <p className="mt-3 text-xs font-medium text-warning">Quyền này đã tồn tại.</p> : null}
      </form>

      <section aria-label="Quyền cấp trực tiếp">
        {permissionsQuery.isLoading ? <LoadingState label="Đang tải quyền" /> : null}
        {permissionsQuery.isError ? (
          <ErrorState
            title="Không tải được danh sách quyền"
            message={safeErrorMessage(permissionsQuery.error)}
            onRetry={() => void permissionsQuery.refetch()}
          />
        ) : null}
        {!permissionsQuery.isLoading && !permissionsQuery.isError && permissions.length === 0 ? (
          <EmptyState title="Chưa có quyền cấp trực tiếp nào." />
        ) : null}
        {permissions.length ? (
          <DataTable columns={["Đối tượng", "Loại", "Quyền", "Thao tác"]}>
            {permissions.map((permission) => (
              <tr key={permission.id}>
                <td className="px-5 py-3.5 font-medium">{formatGrantee(permission, usersById, departmentsById)}</td>
                <td className="px-5 py-3.5 text-muted">{permission.user_id ? "Người dùng" : "Phòng ban"}</td>
                <td className="px-5 py-3.5">
                  <Badge tone="accent">{permissionLevelLabels[permission.permission]}</Badge>
                </td>
                <td className="px-5 py-3.5 text-right">
                  <button
                    type="button"
                    className="rounded-token border border-danger/30 px-3 py-1.5 text-sm text-danger transition hover:bg-danger/5"
                    onClick={() => setDeleteId(permission.id)}
                  >
                    Thu hồi
                  </button>
                </td>
              </tr>
            ))}
          </DataTable>
        ) : null}
      </section>

      <ConfirmDialog
        open={Boolean(deleteId)}
        title="Thu hồi quyền này?"
        message="Chỉ xóa quyền cấp trực tiếp. Quyền theo phạm vi của tài liệu vẫn giữ nguyên."
        confirmLabel="Thu hồi"
        loading={revokeMutation.isPending}
        onCancel={() => setDeleteId(null)}
        onConfirm={() => deleteId && revokeMutation.mutate(deleteId)}
      />
    </div>
  );
}

function scopeSummary(documentItem: DocumentItem, departmentsById: ReadonlyMap<string, Department>): string {
  const scope = accessScopeLabels[documentItem.access_scope];
  if (documentItem.access_scope === "DEPARTMENT") {
    const department = documentItem.department_id ? departmentsById.get(documentItem.department_id) : undefined;
    const name = department?.name ?? "của tài liệu";
    return `Phạm vi hiện tại: ${scope} · ${name}. Thành viên phòng ${name} đã xem được. Quyền cấp trực tiếp dưới đây dành cho người hoặc phòng ban khác, và có hiệu lực ngay.`;
  }
  if (documentItem.access_scope === "ORGANIZATION") {
    return `Phạm vi hiện tại: ${scope}. Mọi người dùng đang hoạt động đã xem được. Quyền cấp trực tiếp dưới đây có hiệu lực ngay.`;
  }
  return `Phạm vi hiện tại: ${scope}. Chỉ người tải lên xem được. Quyền cấp trực tiếp dưới đây mở thêm cho người hoặc phòng ban khác, và có hiệu lực ngay.`;
}

function renderSelectorState({
  isLoading,
  isError,
  total,
  filteredTotal,
  loadingLabel,
  emptyLabel,
  emptyFilterLabel,
  errorLabel,
  onRetry,
}: {
  isLoading: boolean;
  isError: boolean;
  total: number;
  filteredTotal: number;
  loadingLabel: string;
  emptyLabel: string;
  emptyFilterLabel: string;
  errorLabel: string;
  onRetry: () => void;
}) {
  if (isLoading) {
    return (
      <p className="text-xs text-muted" role="status">
        {loadingLabel}
      </p>
    );
  }
  if (isError) {
    return (
      <div
        className="flex items-center justify-between gap-3 rounded-token border border-danger/20 bg-danger/5 p-3 text-xs text-danger"
        role="alert"
      >
        <span>{errorLabel}</span>
        <Button type="button" variant="secondary" onClick={onRetry}>
          Thử lại
        </Button>
      </div>
    );
  }
  if (total === 0) {
    return (
      <p className="text-xs text-muted" role="status">
        {emptyLabel}
      </p>
    );
  }
  if (filteredTotal === 0) {
    return (
      <p className="text-xs text-muted" role="status">
        {emptyFilterLabel}
      </p>
    );
  }
  return null;
}

function formatGrantee(
  permission: DocumentPermission,
  usersById: ReadonlyMap<string, User>,
  departmentsById: ReadonlyMap<string, Department>,
) {
  if (permission.user_id) {
    const user = usersById.get(permission.user_id);
    return user ? (user.full_name || user.email) : truncateMiddle(permission.user_id);
  }
  const departmentId = permission.department_id ?? "";
  const department = departmentsById.get(departmentId);
  return department ? formatDepartmentOption(department) : truncateMiddle(departmentId);
}

function formatUserOption(user: User) {
  return user.full_name ? `${user.full_name} — ${user.email}` : user.email;
}

function formatDepartmentOption(department: Department) {
  return department.code ? `${department.name} (${department.code})` : department.name;
}

function normalizeFilter(value: string) {
  return value.trim().toLocaleLowerCase("vi");
}

function grantErrorMessage(error: unknown): string {
  if (isApiError(error)) {
    if (error.status === 422) {
      return "Vui lòng chọn người dùng hoặc phòng ban hợp lệ.";
    }
    if (error.status === 404) {
      return "Người dùng hoặc phòng ban được chọn không hợp lệ.";
    }
    if (error.status === 409) {
      return "Quyền này đã tồn tại.";
    }
  }
  return safeErrorMessage(error);
}
