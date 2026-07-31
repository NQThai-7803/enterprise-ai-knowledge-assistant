import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Building2, Pencil, Search } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { apiClient } from "../../api/client";
import { safeErrorMessage } from "../../api/errors";
import type { Department } from "../../api/types";
import { DataTable } from "../../components/data/DataTable";
import { useToast } from "../../components/feedback/ToastProvider";
import { PageHeader } from "../../components/layout/PageHeader";
import { Button } from "../../components/ui/Button";
import { ConfirmDialog } from "../../components/ui/ConfirmDialog";
import { FieldWrapper, TextArea, TextInput } from "../../components/ui/Field";
import { Pagination } from "../../components/ui/Pagination";
import { Panel } from "../../components/ui/Panel";
import { EmptyState, ErrorState, LoadingState } from "../../components/ui/State";
import { formatDateTime, truncateMiddle } from "../../lib/format";

const departmentSchema = z.object({
  name: z.string().trim().min(1, "Name is required.").max(120),
  code: z
    .string()
    .trim()
    .min(1, "Code is required.")
    .max(50)
    .regex(/^[A-Za-z0-9_-]+$/, "Use letters, digits, underscores, or hyphens."),
  description: z.string().trim().optional(),
});

type DepartmentForm = z.infer<typeof departmentSchema>;

function valuesFromDepartment(department: Department): DepartmentForm {
  return {
    name: department.name,
    code: department.code,
    description: department.description ?? "",
  };
}

export function DepartmentsPage() {
  const queryClient = useQueryClient();
  const { pushToast } = useToast();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [editDepartment, setEditDepartment] = useState<Department | null>(null);
  const createForm = useForm<DepartmentForm>({ resolver: zodResolver(departmentSchema) });
  const editForm = useForm<DepartmentForm>({ resolver: zodResolver(departmentSchema) });

  const departmentsQuery = useQuery({
    queryKey: ["departments", page, search],
    queryFn: () =>
      apiClient.departments.list({
        page,
        page_size: 20,
        search: search.trim() || undefined,
      }),
  });

  const createMutation = useMutation({
    mutationFn: (values: DepartmentForm) =>
      apiClient.departments.create({
        name: values.name,
        code: values.code,
        description: values.description || null,
      }),
    onSuccess: async () => {
      createForm.reset({ name: "", code: "", description: "" });
      await queryClient.invalidateQueries({ queryKey: ["departments"] });
      pushToast({ tone: "success", title: "Department created" });
    },
    onError: (error) =>
      pushToast({ tone: "error", title: "Create department failed", message: safeErrorMessage(error) }),
  });

  const updateMutation = useMutation({
    mutationFn: ({ departmentId, values }: { departmentId: string; values: DepartmentForm }) =>
      apiClient.departments.update(departmentId, {
        name: values.name,
        code: values.code,
        description: values.description || null,
      }),
    onSuccess: async (response) => {
      setEditDepartment(response.data);
      editForm.reset(valuesFromDepartment(response.data));
      await queryClient.invalidateQueries({ queryKey: ["departments"] });
      pushToast({ tone: "success", title: "Department updated" });
    },
    onError: (error) =>
      pushToast({ tone: "error", title: "Update department failed", message: safeErrorMessage(error) }),
  });

  const deleteMutation = useMutation({
    mutationFn: (departmentId: string) => apiClient.departments.delete(departmentId),
    onSuccess: async () => {
      setDeleteId(null);
      if (editDepartment?.id === deleteId) {
        setEditDepartment(null);
      }
      await queryClient.invalidateQueries({ queryKey: ["departments"] });
      pushToast({ tone: "success", title: "Department deleted" });
    },
    onError: (error) =>
      pushToast({ tone: "error", title: "Delete failed", message: safeErrorMessage(error) }),
  });

  const departments = departmentsQuery.data?.data ?? [];

  const startEdit = (department: Department) => {
    setEditDepartment(department);
    editForm.reset(valuesFromDepartment(department));
  };

  return (
    <div>
      <PageHeader title="Department management" description="Admin-only department CRUD. Member counts are not guessed when backend does not provide them." />
      <div className="grid gap-4 xl:grid-cols-[24rem_1fr]">
        <div className="space-y-4">
          <Panel className="p-5">
            <h3 className="mb-4 text-sm font-semibold">Create department</h3>
            <form className="space-y-4" onSubmit={createForm.handleSubmit((values) => createMutation.mutate(values))} noValidate>
              <FieldWrapper id="department-name" label="Name" error={createForm.formState.errors.name?.message}>
                <TextInput id="department-name" {...createForm.register("name")} />
              </FieldWrapper>
              <FieldWrapper id="department-code" label="Code" error={createForm.formState.errors.code?.message}>
                <TextInput id="department-code" {...createForm.register("code")} />
              </FieldWrapper>
              <FieldWrapper id="department-description" label="Description" error={createForm.formState.errors.description?.message}>
                <TextArea id="department-description" {...createForm.register("description")} />
              </FieldWrapper>
              <Button type="submit" loading={createMutation.isPending} icon={<Building2 className="h-4 w-4" aria-hidden="true" />}>
                Create department
              </Button>
            </form>
          </Panel>

          {editDepartment ? (
            <Panel className="p-5">
              <h3 className="mb-4 text-sm font-semibold">Edit department</h3>
              <form
                className="space-y-4"
                onSubmit={editForm.handleSubmit((values) => updateMutation.mutate({ departmentId: editDepartment.id, values }))}
                noValidate
              >
                <FieldWrapper id="edit-department-name" label="Edit name" error={editForm.formState.errors.name?.message}>
                  <TextInput id="edit-department-name" {...editForm.register("name")} />
                </FieldWrapper>
                <FieldWrapper id="edit-department-code" label="Edit code" error={editForm.formState.errors.code?.message}>
                  <TextInput id="edit-department-code" {...editForm.register("code")} />
                </FieldWrapper>
                <FieldWrapper id="edit-department-description" label="Edit description" error={editForm.formState.errors.description?.message}>
                  <TextArea id="edit-department-description" {...editForm.register("description")} />
                </FieldWrapper>
                <div className="flex flex-wrap gap-2">
                  <Button type="submit" loading={updateMutation.isPending}>
                    Update department
                  </Button>
                  <Button type="button" variant="secondary" onClick={() => setEditDepartment(null)}>
                    Cancel
                  </Button>
                </div>
              </form>
            </Panel>
          ) : null}
        </div>

        <section>
          <div className="mb-4 rounded-token border border-border bg-surface p-4">
            <FieldWrapper id="department-search" label="Search">
              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-muted" aria-hidden="true" />
                <TextInput
                  id="department-search"
                  className="pl-9"
                  value={search}
                  onChange={(event) => {
                    setPage(1);
                    setSearch(event.target.value);
                  }}
                />
              </div>
            </FieldWrapper>
          </div>
          {departmentsQuery.isLoading ? <LoadingState label="Loading departments" /> : null}
          {departmentsQuery.isError ? <ErrorState message={safeErrorMessage(departmentsQuery.error)} onRetry={() => void departmentsQuery.refetch()} /> : null}
          {!departmentsQuery.isLoading && departments.length === 0 ? <EmptyState title="No departments found" /> : null}
          {departments.length ? (
            <>
              <DataTable columns={["Name", "Code", "Description", "Created", "Actions"]}>
                {departments.map((department) => (
                  <tr key={department.id}>
                    <td className="px-4 py-3">
                      <span className="block font-semibold text-ink">{department.name}</span>
                      <span className="text-xs text-muted">{truncateMiddle(department.id)}</span>
                    </td>
                    <td className="px-4 py-3 font-mono text-sm text-muted">{department.code}</td>
                    <td className="px-4 py-3 text-muted">{department.description ?? "No description"}</td>
                    <td className="px-4 py-3 text-muted">{formatDateTime(department.created_at)}</td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-2">
                        <Button type="button" variant="secondary" onClick={() => startEdit(department)} icon={<Pencil className="h-4 w-4" aria-hidden="true" />}>
                          Edit
                        </Button>
                        <Button type="button" variant="danger" onClick={() => setDeleteId(department.id)}>
                          Delete
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </DataTable>
              {departmentsQuery.data?.meta ? <Pagination meta={departmentsQuery.data.meta} onPageChange={setPage} /> : null}
            </>
          ) : null}
        </section>
      </div>
      <ConfirmDialog
        open={Boolean(deleteId)}
        title="Delete department"
        message="The backend rejects departments that are still referenced by documents or active users."
        confirmLabel="Delete"
        loading={deleteMutation.isPending}
        onCancel={() => setDeleteId(null)}
        onConfirm={() => deleteId && deleteMutation.mutate(deleteId)}
      />
    </div>
  );
}