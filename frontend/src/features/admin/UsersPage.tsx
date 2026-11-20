import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { useForm, type UseFormReturn } from "react-hook-form";
import { z } from "zod";
import { apiClient } from "../../api/client";
import { isApiError, safeErrorMessage } from "../../api/errors";
import type { Department, User, UserRole } from "../../api/types";
import { DataTable } from "../../components/data/DataTable";
import { useToast } from "../../components/feedback/ToastProvider";
import { PageHeader } from "../../components/layout/PageHeader";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { ConfirmDialog } from "../../components/ui/ConfirmDialog";
import { Drawer } from "../../components/ui/Drawer";
import { FieldWrapper, SelectInput, TextInput } from "../../components/ui/Field";
import { Pagination } from "../../components/ui/Pagination";
import { EmptyState, ErrorState, LoadingState } from "../../components/ui/State";
import { initials } from "../../lib/format";
import { roleLabels } from "../../lib/labels";

// API_SPEC §5: Manager and Staff need a department, an Admin may have none; passwords are at least 12 characters.
const needsDepartment = (values: { role: UserRole; department_id?: string }, context: z.RefinementCtx) => {
  if (values.role !== "ADMIN" && !values.department_id) {
    context.addIssue({ code: z.ZodIssueCode.custom, path: ["department_id"], message: "Quản lý và nhân viên phải có phòng ban." });
  }
};

const baseUser = z.object({
  email: z.string().trim().email("Nhập email hợp lệ."),
  full_name: z.string().trim().min(1, "Nhập họ tên.").max(200, "Họ tên tối đa 200 ký tự."),
  role: z.enum(["ADMIN", "MANAGER", "STAFF"]),
  department_id: z.string().optional(),
});

const userSchema = baseUser
  .extend({ password: z.string().min(12, "Mật khẩu tạm phải có ít nhất 12 ký tự.") })
  .superRefine(needsDepartment);
const editUserSchema = baseUser.extend({ is_active: z.enum(["true", "false"]) }).superRefine(needsDepartment);

type UserForm = z.infer<typeof userSchema>;
type EditUserForm = z.infer<typeof editUserSchema>;

const createDefaults: Partial<UserForm> = { role: "STAFF", department_id: "" };
const roleTones = { ADMIN: "strong", MANAGER: "accent", STAFF: "neutral" } as const;

function valuesFromUser(user: User): EditUserForm {
  return {
    email: user.email,
    full_name: user.full_name,
    role: user.role,
    department_id: user.department_id ?? "",
    is_active: user.is_active ? "true" : "false",
  };
}

export function UsersPage() {
  const queryClient = useQueryClient();
  const { pushToast } = useToast();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [role, setRole] = useState<UserRole | "">("");
  const [active, setActive] = useState<"" | "true" | "false">("");
  const [creating, setCreating] = useState(false);
  const [deactivateId, setDeactivateId] = useState<string | null>(null);
  const [editUser, setEditUser] = useState<User | null>(null);

  const createForm = useForm<UserForm>({ resolver: zodResolver(userSchema), defaultValues: createDefaults });
  const editForm = useForm<EditUserForm>({ resolver: zodResolver(editUserSchema) });

  const usersQuery = useQuery({
    queryKey: ["users", page, search, role, active],
    queryFn: () =>
      apiClient.users.list({
        page,
        page_size: 20,
        search: search.trim() || undefined,
        role: role || undefined,
        is_active: active === "" ? undefined : active === "true",
      }),
  });

  const departmentsQuery = useQuery({
    queryKey: ["departments", "user-selector"],
    queryFn: () => apiClient.departments.list({ page: 1, page_size: 100 }),
    staleTime: 5 * 60_000,
  });
  const departments = useMemo(() => departmentsQuery.data?.data ?? [], [departmentsQuery.data]);
  const departmentsById = useMemo(() => new Map(departments.map((item) => [item.id, item])), [departments]);

  const createMutation = useMutation({
    mutationFn: (values: UserForm) => apiClient.users.create({ ...values, department_id: values.department_id || null }),
    onSuccess: async () => {
      createForm.reset(createDefaults);
      setCreating(false);
      await queryClient.invalidateQueries({ queryKey: ["users"] });
      pushToast({ tone: "success", title: "Đã tạo người dùng" });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ userId, values }: { userId: string; values: EditUserForm }) =>
      apiClient.users.update(userId, {
        email: values.email,
        full_name: values.full_name,
        role: values.role,
        department_id: values.department_id || null,
        is_active: values.is_active === "true",
      }),
    onSuccess: async () => {
      setEditUser(null);
      await queryClient.invalidateQueries({ queryKey: ["users"] });
      pushToast({ tone: "success", title: "Đã cập nhật người dùng" });
    },
  });

  const deactivateMutation = useMutation({
    mutationFn: (userId: string) => apiClient.users.deactivate(userId),
    onSuccess: async () => {
      setDeactivateId(null);
      await queryClient.invalidateQueries({ queryKey: ["users"] });
      pushToast({ tone: "success", title: "Đã vô hiệu hóa người dùng" });
    },
    onError: (error) => pushToast({ tone: "error", title: "Vô hiệu hóa thất bại", message: userErrorMessage(error) }),
  });

  const reactivateMutation = useMutation({
    mutationFn: (user: User) =>
      apiClient.users.update(user.id, {
        email: user.email,
        full_name: user.full_name,
        role: user.role,
        department_id: user.department_id,
        is_active: true,
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["users"] });
      pushToast({ tone: "success", title: "Đã kích hoạt lại người dùng" });
    },
    onError: (error) => pushToast({ tone: "error", title: "Kích hoạt lại thất bại", message: userErrorMessage(error) }),
  });

  const users = usersQuery.data?.data ?? [];
  const filtered = Boolean(search.trim() || role || active);

  const startEdit = (user: User) => {
    updateMutation.reset();
    editForm.reset(valuesFromUser(user));
    setEditUser(user);
  };

  return (
    <div>
      <PageHeader
        title="Người dùng"
        description="Vai trò quyết định thao tác; phòng ban quyết định tài liệu được xem."
        actions={
          <Button
            type="button"
            onClick={() => {
              createMutation.reset();
              setCreating(true);
            }}
            icon={<Plus className="h-4 w-4" aria-hidden="true" />}>
            Tạo người dùng
          </Button>
        }
      />

      <section className="mb-5 grid gap-3 md:grid-cols-[minmax(0,1fr)_12rem_12rem]" aria-label="Bộ lọc người dùng">
        <FieldWrapper id="user-search" label="Tìm kiếm">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-muted" aria-hidden="true" />
            <TextInput
              id="user-search"
              className="pl-9"
              placeholder="Tên hoặc email"
              value={search}
              onChange={(event) => {
                setPage(1);
                setSearch(event.target.value);
              }}
            />
          </div>
        </FieldWrapper>
        <FieldWrapper id="user-role" label="Vai trò">
          <SelectInput
            id="user-role"
            value={role}
            onChange={(event) => {
              setPage(1);
              setRole(event.target.value as UserRole | "");
            }}
          >
            <option value="">Tất cả vai trò</option>
            {(Object.keys(roleLabels) as UserRole[]).map((value) => (
              <option key={value} value={value}>
                {roleLabels[value]}
              </option>
            ))}
          </SelectInput>
        </FieldWrapper>
        <FieldWrapper id="user-active" label="Trạng thái">
          <SelectInput
            id="user-active"
            value={active}
            onChange={(event) => {
              setPage(1);
              setActive(event.target.value as "" | "true" | "false");
            }}
          >
            <option value="">Tất cả</option>
            <option value="true">Hoạt động</option>
            <option value="false">Vô hiệu hóa</option>
          </SelectInput>
        </FieldWrapper>
      </section>

      {usersQuery.isLoading ? <LoadingState label="Đang tải người dùng" /> : null}
      {usersQuery.isError ? (
        <ErrorState
          title="Không tải được danh sách người dùng"
          error={usersQuery.error}
          onRetry={() => void usersQuery.refetch()}
        />
      ) : null}
      {!usersQuery.isLoading && !usersQuery.isError && users.length === 0 ? (
        <EmptyState title={filtered ? "Không có người dùng phù hợp" : "Chưa có người dùng nào"} />
      ) : null}
      {users.length ? (
        <>
          <DataTable columns={["Người dùng", "Vai trò", "Phòng ban", "Trạng thái", "Thao tác"]}>
            {users.map((user) => (
              <tr key={user.id}>
                <td className="px-5 py-3">
                  <div className="flex items-center gap-3">
                    <span
                      className="flex h-[30px] w-[30px] shrink-0 items-center justify-center rounded-full bg-border/50 text-xs font-semibold text-ink/80"
                      aria-hidden="true"
                    >
                      {initials(user.full_name)}
                    </span>
                    <div className="min-w-0">
                      <p className="truncate font-medium text-ink">{user.full_name}</p>
                      <p className="truncate text-xs text-muted">{user.email}</p>
                    </div>
                  </div>
                </td>
                <td className="px-5 py-3">
                  <Badge tone={roleTones[user.role]}>{roleLabels[user.role]}</Badge>
                </td>
                <td className="px-5 py-3 text-ink/80">
                  {user.department_id ? (departmentsById.get(user.department_id)?.name ?? "Phòng ban") : "—"}
                </td>
                <td className="px-5 py-3">
                  <Badge tone={user.is_active ? "success" : "neutral"}>
                    <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden="true" />
                    {user.is_active ? "Đang hoạt động" : "Đã vô hiệu hóa"}
                  </Badge>
                </td>
                <td className="px-5 py-3">
                  <div className="flex justify-end gap-4 whitespace-nowrap text-sm">
                    <button type="button" className="text-ink transition hover:text-accent" onClick={() => startEdit(user)}>
                      Sửa
                    </button>
                    {user.is_active ? (
                      <button
                        type="button"
                        className="text-ink transition hover:text-danger"
                        onClick={() => setDeactivateId(user.id)}
                      >
                        Vô hiệu hóa
                      </button>
                    ) : (
                      <button
                        type="button"
                        className="text-ink transition hover:text-accent disabled:opacity-50"
                        disabled={reactivateMutation.isPending}
                        onClick={() => reactivateMutation.mutate(user)}
                      >
                        Kích hoạt lại
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </DataTable>
          {usersQuery.data?.meta ? <Pagination meta={usersQuery.data.meta} onPageChange={setPage} /> : null}
        </>
      ) : null}

      <Drawer open={creating} title="Tạo người dùng" onClose={() => setCreating(false)}>
        <form
          className="space-y-4"
          onSubmit={createForm.handleSubmit((values) => createMutation.mutate(values))}
          noValidate
        >
          <UserFields form={createForm} departments={departments} departmentsFailed={departmentsQuery.isError} />
          <FieldWrapper id="new-password" label="Mật khẩu tạm" error={createForm.formState.errors.password?.message}>
            <TextInput id="new-password" type="password" autoComplete="new-password" {...createForm.register("password")} />
          </FieldWrapper>
          {createMutation.isError ? (
            <p className="rounded-token border border-danger/20 bg-danger/5 px-3 py-2 text-sm font-medium text-danger" role="alert">
              Tạo người dùng thất bại. {userErrorMessage(createMutation.error)}
            </p>
          ) : null}
          <Button type="submit" loading={createMutation.isPending}>
            Tạo người dùng
          </Button>
        </form>
      </Drawer>

      <Drawer open={editUser !== null} title="Sửa người dùng" onClose={() => setEditUser(null)}>
        {editUser ? (
          <form
            className="space-y-4"
            onSubmit={editForm.handleSubmit((values) => updateMutation.mutate({ userId: editUser.id, values }))}
            noValidate
          >
            <UserFields form={editForm} departments={departments} departmentsFailed={departmentsQuery.isError} />
            <FieldWrapper id="user-is-active" label="Trạng thái" error={editForm.formState.errors.is_active?.message}>
              <SelectInput id="user-is-active" {...editForm.register("is_active")}>
                <option value="true">Đang hoạt động</option>
                <option value="false">Đã vô hiệu hóa</option>
              </SelectInput>
            </FieldWrapper>
            {updateMutation.isError ? (
              <p className="rounded-token border border-danger/20 bg-danger/5 px-3 py-2 text-sm font-medium text-danger" role="alert">
                Cập nhật thất bại. {userErrorMessage(updateMutation.error)}
              </p>
            ) : null}
            <Button type="submit" loading={updateMutation.isPending}>
              Lưu thay đổi
            </Button>
          </form>
        ) : null}
      </Drawer>

      <ConfirmDialog
        open={Boolean(deactivateId)}
        title="Vô hiệu hóa người dùng?"
        message="Người dùng sẽ không đăng nhập được nữa và mọi phiên đăng nhập đang mở bị thu hồi."
        confirmLabel="Vô hiệu hóa"
        loading={deactivateMutation.isPending}
        onCancel={() => setDeactivateId(null)}
        onConfirm={() => deactivateId && deactivateMutation.mutate(deactivateId)}
      />
    </div>
  );
}

/** Fields shared by the create and edit drawers; only one drawer is open at a time, so ids stay unique. */
function UserFields({
  form,
  departments,
  departmentsFailed,
}: {
  form: UseFormReturn<UserForm> | UseFormReturn<EditUserForm>;
  departments: Department[];
  departmentsFailed: boolean;
}) {
  // Both forms share these four fields; narrow to the common shape.
  const { register, formState } = form as unknown as UseFormReturn<z.infer<typeof baseUser>>;
  const errors = formState.errors;
  return (
    <>
      <FieldWrapper id="user-email" label="Email" error={errors.email?.message}>
        <TextInput id="user-email" type="email" autoComplete="off" {...register("email")} />
      </FieldWrapper>
      <FieldWrapper id="user-full-name" label="Họ tên" error={errors.full_name?.message}>
        <TextInput id="user-full-name" {...register("full_name")} />
      </FieldWrapper>
      <FieldWrapper id="user-form-role" label="Vai trò" error={errors.role?.message}>
        <SelectInput id="user-form-role" {...register("role")}>
          {(Object.keys(roleLabels) as UserRole[]).map((value) => (
            <option key={value} value={value}>
              {roleLabels[value]}
            </option>
          ))}
        </SelectInput>
      </FieldWrapper>
      <FieldWrapper
        id="user-department"
        label="Phòng ban"
        error={errors.department_id?.message}
        help={departmentsFailed ? "Không tải được danh sách phòng ban." : "Quản trị viên có thể không thuộc phòng ban nào."}
      >
        <SelectInput id="user-department" {...register("department_id")}>
          <option value="">Không thuộc phòng ban</option>
          {departments.map((department) => (
            <option key={department.id} value={department.id}>
              {department.code ? `${department.name} (${department.code})` : department.name}
            </option>
          ))}
        </SelectInput>
      </FieldWrapper>
    </>
  );
}

function userErrorMessage(error: unknown): string {
  if (isApiError(error)) {
    if (error.code === "USER_EMAIL_ALREADY_EXISTS") {
      return "Email này đã được dùng.";
    }
    if (error.code === "LAST_ACTIVE_ADMIN") {
      return "Không thể bỏ quản trị viên đang hoạt động cuối cùng.";
    }
    if (error.code === "SELF_MODIFICATION_NOT_ALLOWED") {
      return "Bạn không thể tự đổi vai trò hoặc trạng thái của chính mình.";
    }
  }
  return safeErrorMessage(error);
}
