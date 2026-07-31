import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil, RotateCcw, Search, UserPlus } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { apiClient } from "../../api/client";
import { safeErrorMessage } from "../../api/errors";
import type { User, UserRole } from "../../api/types";
import { DataTable } from "../../components/data/DataTable";
import { useToast } from "../../components/feedback/ToastProvider";
import { PageHeader } from "../../components/layout/PageHeader";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { ConfirmDialog } from "../../components/ui/ConfirmDialog";
import { FieldWrapper, SelectInput, TextInput } from "../../components/ui/Field";
import { Pagination } from "../../components/ui/Pagination";
import { Panel } from "../../components/ui/Panel";
import { EmptyState, ErrorState, LoadingState } from "../../components/ui/State";
import { formatDateTime, truncateMiddle } from "../../lib/format";

const userSchema = z.object({
  email: z.string().trim().email("Enter a valid email."),
  full_name: z.string().trim().min(1, "Full name is required.").max(200),
  password: z.string().min(12, "Password must be at least 12 characters."),
  role: z.enum(["ADMIN", "MANAGER", "STAFF"]),
  department_id: z.string().trim().optional(),
});

const editUserSchema = userSchema.omit({ password: true }).extend({
  is_active: z.enum(["true", "false"]),
});

type UserForm = z.infer<typeof userSchema>;
type EditUserForm = z.infer<typeof editUserSchema>;

const createDefaults: Partial<UserForm> = { role: "STAFF", department_id: "" };

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
  const [deactivateId, setDeactivateId] = useState<string | null>(null);
  const [editUser, setEditUser] = useState<User | null>(null);

  const createForm = useForm<UserForm>({
    resolver: zodResolver(userSchema),
    defaultValues: createDefaults,
  });
  const editForm = useForm<EditUserForm>({
    resolver: zodResolver(editUserSchema),
  });

  const usersQuery = useQuery({
    queryKey: ["users", page, search, role],
    queryFn: () =>
      apiClient.users.list({
        page,
        page_size: 20,
        search: search.trim() || undefined,
        role: role || undefined,
      }),
  });

  const createMutation = useMutation({
    mutationFn: (values: UserForm) =>
      apiClient.users.create({
        ...values,
        department_id: values.department_id || null,
      }),
    onSuccess: async () => {
      createForm.reset(createDefaults);
      await queryClient.invalidateQueries({ queryKey: ["users"] });
      pushToast({ tone: "success", title: "User created" });
    },
    onError: (error) =>
      pushToast({ tone: "error", title: "Create user failed", message: safeErrorMessage(error) }),
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
    onSuccess: async (response) => {
      setEditUser(response.data);
      editForm.reset(valuesFromUser(response.data));
      await queryClient.invalidateQueries({ queryKey: ["users"] });
      pushToast({ tone: "success", title: "User updated" });
    },
    onError: (error) =>
      pushToast({ tone: "error", title: "Update user failed", message: safeErrorMessage(error) }),
  });

  const deactivateMutation = useMutation({
    mutationFn: (userId: string) => apiClient.users.deactivate(userId),
    onSuccess: async () => {
      setDeactivateId(null);
      await queryClient.invalidateQueries({ queryKey: ["users"] });
      pushToast({ tone: "success", title: "User deactivated" });
    },
    onError: (error) =>
      pushToast({ tone: "error", title: "Deactivate failed", message: safeErrorMessage(error) }),
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
      pushToast({ tone: "success", title: "User reactivated" });
    },
    onError: (error) =>
      pushToast({ tone: "error", title: "Reactivate failed", message: safeErrorMessage(error) }),
  });

  const users = usersQuery.data?.data ?? [];

  const startEdit = (user: User) => {
    setEditUser(user);
    editForm.reset(valuesFromUser(user));
  };

  return (
    <div>
      <PageHeader title="User management" description="Admin-only account management. Passwords are submitted only to the backend create endpoint." />
      <div className="grid gap-4 xl:grid-cols-[24rem_1fr]">
        <div className="space-y-4">
          <Panel className="p-5">
            <h3 className="mb-4 text-sm font-semibold">Create user</h3>
            <form className="space-y-4" onSubmit={createForm.handleSubmit((values) => createMutation.mutate(values))} noValidate>
              <FieldWrapper id="new-email" label="Email" error={createForm.formState.errors.email?.message}>
                <TextInput id="new-email" type="email" {...createForm.register("email")} />
              </FieldWrapper>
              <FieldWrapper id="new-name" label="Full name" error={createForm.formState.errors.full_name?.message}>
                <TextInput id="new-name" {...createForm.register("full_name")} />
              </FieldWrapper>
              <FieldWrapper id="new-password" label="Temporary password" error={createForm.formState.errors.password?.message}>
                <TextInput id="new-password" type="password" autoComplete="new-password" {...createForm.register("password")} />
              </FieldWrapper>
              <FieldWrapper id="new-role" label="Role" error={createForm.formState.errors.role?.message}>
                <SelectInput id="new-role" {...createForm.register("role")}>
                  <option value="STAFF">Staff</option>
                  <option value="MANAGER">Manager</option>
                  <option value="ADMIN">Admin</option>
                </SelectInput>
              </FieldWrapper>
              <FieldWrapper id="new-department" label="Department ID" error={createForm.formState.errors.department_id?.message}>
                <TextInput id="new-department" {...createForm.register("department_id")} />
              </FieldWrapper>
              <Button type="submit" loading={createMutation.isPending} icon={<UserPlus className="h-4 w-4" aria-hidden="true" />}>
                Create user
              </Button>
            </form>
          </Panel>

          {editUser ? (
            <Panel className="p-5">
              <h3 className="mb-4 text-sm font-semibold">Edit user</h3>
              <form
                className="space-y-4"
                onSubmit={editForm.handleSubmit((values) => updateMutation.mutate({ userId: editUser.id, values }))}
                noValidate
              >
                <FieldWrapper id="edit-email" label="Edit email" error={editForm.formState.errors.email?.message}>
                  <TextInput id="edit-email" type="email" {...editForm.register("email")} />
                </FieldWrapper>
                <FieldWrapper id="edit-name" label="Edit full name" error={editForm.formState.errors.full_name?.message}>
                  <TextInput id="edit-name" {...editForm.register("full_name")} />
                </FieldWrapper>
                <FieldWrapper id="edit-role" label="Edit role" error={editForm.formState.errors.role?.message}>
                  <SelectInput id="edit-role" {...editForm.register("role")}>
                    <option value="STAFF">Staff</option>
                    <option value="MANAGER">Manager</option>
                    <option value="ADMIN">Admin</option>
                  </SelectInput>
                </FieldWrapper>
                <FieldWrapper id="edit-department" label="Edit department ID" error={editForm.formState.errors.department_id?.message}>
                  <TextInput id="edit-department" {...editForm.register("department_id")} />
                </FieldWrapper>
                <FieldWrapper id="edit-active" label="Edit active status" error={editForm.formState.errors.is_active?.message}>
                  <SelectInput id="edit-active" {...editForm.register("is_active")}>
                    <option value="true">Active</option>
                    <option value="false">Inactive</option>
                  </SelectInput>
                </FieldWrapper>
                <div className="flex flex-wrap gap-2">
                  <Button type="submit" loading={updateMutation.isPending}>
                    Update user
                  </Button>
                  <Button type="button" variant="secondary" onClick={() => setEditUser(null)}>
                    Cancel
                  </Button>
                </div>
              </form>
            </Panel>
          ) : null}
        </div>

        <section>
          <div className="mb-4 grid gap-3 rounded-token border border-border bg-surface p-4 md:grid-cols-[1fr_12rem]">
            <FieldWrapper id="user-search" label="Search">
              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-muted" aria-hidden="true" />
                <TextInput
                  id="user-search"
                  className="pl-9"
                  value={search}
                  onChange={(event) => {
                    setPage(1);
                    setSearch(event.target.value);
                  }}
                />
              </div>
            </FieldWrapper>
            <FieldWrapper id="user-role" label="Role">
              <SelectInput
                id="user-role"
                value={role}
                onChange={(event) => {
                  setPage(1);
                  setRole(event.target.value as UserRole | "");
                }}
              >
                <option value="">All roles</option>
                <option value="ADMIN">Admin</option>
                <option value="MANAGER">Manager</option>
                <option value="STAFF">Staff</option>
              </SelectInput>
            </FieldWrapper>
          </div>
          {usersQuery.isLoading ? <LoadingState label="Loading users" /> : null}
          {usersQuery.isError ? <ErrorState message={safeErrorMessage(usersQuery.error)} onRetry={() => void usersQuery.refetch()} /> : null}
          {!usersQuery.isLoading && users.length === 0 ? <EmptyState title="No users found" /> : null}
          {users.length ? (
            <>
              <DataTable columns={["User", "Role", "Department", "Status", "Updated", "Actions"]}>
                {users.map((user) => (
                  <tr key={user.id}>
                    <td className="px-4 py-3">
                      <span className="block font-semibold text-ink">{user.full_name}</span>
                      <span className="text-xs text-muted">{user.email}</span>
                    </td>
                    <td className="px-4 py-3">
                      <Badge tone="accent">{user.role}</Badge>
                    </td>
                    <td className="px-4 py-3 text-muted">{user.department_id ? truncateMiddle(user.department_id) : "Unscoped"}</td>
                    <td className="px-4 py-3">
                      <Badge tone={user.is_active ? "success" : "danger"}>{user.is_active ? "ACTIVE" : "INACTIVE"}</Badge>
                    </td>
                    <td className="px-4 py-3 text-muted">{formatDateTime(user.updated_at)}</td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-2">
                        <Button type="button" variant="secondary" onClick={() => startEdit(user)} icon={<Pencil className="h-4 w-4" aria-hidden="true" />}>
                          Edit
                        </Button>
                        {user.is_active ? (
                          <Button type="button" variant="danger" onClick={() => setDeactivateId(user.id)}>
                            Deactivate
                          </Button>
                        ) : (
                          <Button
                            type="button"
                            variant="secondary"
                            loading={reactivateMutation.isPending}
                            onClick={() => reactivateMutation.mutate(user)}
                            icon={<RotateCcw className="h-4 w-4" aria-hidden="true" />}
                          >
                            Reactivate
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </DataTable>
              {usersQuery.data?.meta ? <Pagination meta={usersQuery.data.meta} onPageChange={setPage} /> : null}
            </>
          ) : null}
        </section>
      </div>
      <ConfirmDialog
        open={Boolean(deactivateId)}
        title="Deactivate user"
        message="This revokes active refresh tokens through the backend policy."
        confirmLabel="Deactivate"
        loading={deactivateMutation.isPending}
        onCancel={() => setDeactivateId(null)}
        onConfirm={() => deactivateId && deactivateMutation.mutate(deactivateId)}
      />
    </div>
  );
}