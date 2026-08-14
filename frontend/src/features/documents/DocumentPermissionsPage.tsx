import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ShieldPlus, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { useParams } from "react-router-dom";
import { z } from "zod";
import { apiClient } from "../../api/client";
import { isApiError, safeErrorMessage } from "../../api/errors";
import type { Department, DocumentPermission, User } from "../../api/types";
import { DataTable } from "../../components/data/DataTable";
import { useToast } from "../../components/feedback/ToastProvider";
import { PageHeader } from "../../components/layout/PageHeader";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { ConfirmDialog } from "../../components/ui/ConfirmDialog";
import { FieldWrapper, SelectInput, TextInput } from "../../components/ui/Field";
import { Panel } from "../../components/ui/Panel";
import { EmptyState, ErrorState, LoadingState } from "../../components/ui/State";
import { formatDateTime, truncateMiddle } from "../../lib/format";

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

  const permissions = permissionsQuery.data?.data ?? [];
  const users = usersQuery.data?.data ?? [];
  const departments = departmentsQuery.data?.data ?? [];
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
      pushToast({ tone: "success", title: "Permission granted" });
    },
    onError: (error) => pushToast({ tone: "error", title: "Grant failed", message: grantErrorMessage(error) }),
  });

  const revokeMutation = useMutation({
    mutationFn: (permissionId: string) => apiClient.documents.revokePermission(documentId as string, permissionId),
    onSuccess: async () => {
      setDeleteId(null);
      await queryClient.invalidateQueries({ queryKey: ["documents", "permissions", documentId] });
      pushToast({ tone: "success", title: "Permission revoked" });
    },
    onError: (error) => pushToast({ tone: "error", title: "Revoke failed", message: safeErrorMessage(error) }),
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
    onChange: (event) => setGrantDraft((current) => ({ ...current, permission: event.target.value as PermissionForm["permission"] })),
  });

  return (
    <div>
      <PageHeader title="Document permission management" description="Direct grants supplement backend scope permissions. Effective access remains server-side." />
      <div className="grid gap-4 lg:grid-cols-[24rem_1fr]">
        <Panel className="p-5">
          <h3 className="mb-4 text-sm font-semibold">Grant permission</h3>
          <form className="space-y-4" onSubmit={handleSubmit((values) => grantMutation.mutate(values))} noValidate>
            <FieldWrapper id="grantee_type" label="Grantee type" error={errors.grantee_type?.message}>
              <SelectInput id="grantee_type" {...granteeTypeField}>
                <option value="user">User</option>
                <option value="department">Department</option>
              </SelectInput>
            </FieldWrapper>
            {grantDraft.grantee_type === "user" ? (
              <div className="space-y-3">
                {users.length > 8 ? (
                  <FieldWrapper id="user_filter" label="Find user" help="Filter by name or email.">
                    <TextInput
                      id="user_filter"
                      value={userFilter}
                      onChange={(event) => setUserFilter(event.target.value)}
                      disabled={usersQuery.isLoading}
                      placeholder="Search users"
                    />
                  </FieldWrapper>
                ) : null}
                <FieldWrapper id="grantee_id" label="User" error={errors.grantee_id?.message}>
                  <SelectInput
                    id="grantee_id"
                    {...granteeIdField}
                    disabled={usersQuery.isLoading || usersQuery.isError || users.length === 0}
                  >
                    <option value="">{usersQuery.isLoading ? "Loading users..." : "Select a user"}</option>
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
                  loadingLabel: "Loading users...",
                  emptyLabel: "No users available.",
                  emptyFilterLabel: "No users match the filter.",
                  errorLabel: "Could not load users.",
                  onRetry: () => void usersQuery.refetch(),
                })}
              </div>
            ) : (
              <div className="space-y-3">
                {departments.length > 8 ? (
                  <FieldWrapper id="department_filter" label="Find department" help="Filter by name or code.">
                    <TextInput
                      id="department_filter"
                      value={departmentFilter}
                      onChange={(event) => setDepartmentFilter(event.target.value)}
                      disabled={departmentsQuery.isLoading}
                      placeholder="Search departments"
                    />
                  </FieldWrapper>
                ) : null}
                <FieldWrapper id="grantee_id" label="Department" error={errors.grantee_id?.message}>
                  <SelectInput
                    id="grantee_id"
                    {...granteeIdField}
                    disabled={departmentsQuery.isLoading || departmentsQuery.isError || departments.length === 0}
                  >
                    <option value="">{departmentsQuery.isLoading ? "Loading departments..." : "Select a department"}</option>
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
                  loadingLabel: "Loading departments...",
                  emptyLabel: "No departments available.",
                  emptyFilterLabel: "No departments match the filter.",
                  errorLabel: "Could not load departments.",
                  onRetry: () => void departmentsQuery.refetch(),
                })}
              </div>
            )}
            <FieldWrapper id="permission" label="Permission" error={errors.permission?.message}>
              <SelectInput id="permission" {...permissionField}>
                <option value="VIEW">View</option>
                <option value="EDIT">Edit</option>
                <option value="MANAGE">Manage</option>
              </SelectInput>
            </FieldWrapper>
            <Button
              type="submit"
              disabled={duplicateGrant || activeSelectorBusy || activeSelectorError || activeSelectorEmpty}
              loading={grantMutation.isPending}
              icon={<ShieldPlus className="h-4 w-4" aria-hidden="true" />}
            >
              Grant
            </Button>
            {duplicateGrant ? <p className="text-xs font-medium text-warning">This exact direct grant already exists.</p> : null}
          </form>
        </Panel>

        <section>
          {permissionsQuery.isLoading ? <LoadingState label="Loading permissions" /> : null}
          {permissionsQuery.isError ? <ErrorState message={safeErrorMessage(permissionsQuery.error)} onRetry={() => void permissionsQuery.refetch()} /> : null}
          {!permissionsQuery.isLoading && permissions.length === 0 ? <EmptyState title="No direct permissions" /> : null}
          {permissions.length ? (
            <DataTable columns={["Grantee", "Permission", "Created by", "Created", "Actions"]}>
              {permissions.map((permission) => (
                <tr key={permission.id}>
                  <td className="px-4 py-3 text-sm">{formatGrantee(permission, usersById, departmentsById)}</td>
                  <td className="px-4 py-3"><Badge tone="accent">{permission.permission}</Badge></td>
                  <td className="px-4 py-3 text-muted">{truncateMiddle(permission.created_by)}</td>
                  <td className="px-4 py-3 text-muted">{formatDateTime(permission.created_at)}</td>
                  <td className="px-4 py-3">
                    <Button type="button" variant="danger" onClick={() => setDeleteId(permission.id)} icon={<Trash2 className="h-4 w-4" aria-hidden="true" />}>Revoke</Button>
                  </td>
                </tr>
              ))}
            </DataTable>
          ) : null}
        </section>
      </div>
      <ConfirmDialog
        open={Boolean(deleteId)}
        title="Revoke permission"
        message="This removes only the direct grant row. Scope-based access may still apply."
        confirmLabel="Revoke"
        loading={revokeMutation.isPending}
        onCancel={() => setDeleteId(null)}
        onConfirm={() => deleteId && revokeMutation.mutate(deleteId)}
      />
    </div>
  );
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
      <div className="flex items-center justify-between gap-3 rounded-token border border-danger/20 bg-danger/5 p-3 text-xs text-danger" role="alert">
        <span>{errorLabel}</span>
        <Button type="button" variant="secondary" onClick={onRetry}>
          Retry
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
    return user ? <span>User {formatUserOption(user)}</span> : <span>User {truncateMiddle(permission.user_id)}</span>;
  }
  const departmentId = permission.department_id ?? "";
  const department = departmentsById.get(departmentId);
  return department ? <span>Department {formatDepartmentOption(department)}</span> : <span>Department {truncateMiddle(departmentId)}</span>;
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
