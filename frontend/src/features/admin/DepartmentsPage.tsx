import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { useState } from "react";
import { useForm, type UseFormReturn } from "react-hook-form";
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
import { EmptyState, ErrorState, LoadingState } from "../../components/ui/State";

const departmentSchema = z.object({
  name: z.string().trim().min(1, "Nhập tên phòng ban.").max(120, "Tên tối đa 120 ký tự."),
  code: z
    .string()
    .trim()
    .min(1, "Nhập mã phòng ban.")
    .max(50, "Mã tối đa 50 ký tự.")
    .regex(/^[A-Za-z0-9_-]+$/, "Chỉ dùng chữ không dấu, số, dấu _ hoặc -."),
  description: z.string().trim().optional(),
});

type DepartmentForm = z.infer<typeof departmentSchema>;

const emptyForm: DepartmentForm = { name: "", code: "", description: "" };

function valuesFromDepartment(department: Department): DepartmentForm {
  return { name: department.name, code: department.code, description: department.description ?? "" };
}

export function DepartmentsPage() {
  const queryClient = useQueryClient();
  const { pushToast } = useToast();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [editDepartment, setEditDepartment] = useState<Department | null>(null);
  const createForm = useForm<DepartmentForm>({ resolver: zodResolver(departmentSchema), defaultValues: emptyForm });
  const editForm = useForm<DepartmentForm>({ resolver: zodResolver(departmentSchema) });

  const departmentsQuery = useQuery({
    queryKey: ["departments", page, search],
    queryFn: () => apiClient.departments.list({ page, page_size: 20, search: search.trim() || undefined }),
  });

  const createMutation = useMutation({
    mutationFn: (values: DepartmentForm) =>
      apiClient.departments.create({ name: values.name, code: values.code, description: values.description || null }),
    onSuccess: async () => {
      createForm.reset(emptyForm);
      await queryClient.invalidateQueries({ queryKey: ["departments"] });
      pushToast({ tone: "success", title: "Đã tạo phòng ban" });
    },
    onError: (error) =>
      pushToast({ tone: "error", title: "Tạo phòng ban thất bại", message: safeErrorMessage(error) }),
  });

  const updateMutation = useMutation({
    mutationFn: ({ departmentId, values }: { departmentId: string; values: DepartmentForm }) =>
      apiClient.departments.update(departmentId, {
        name: values.name,
        code: values.code,
        description: values.description || null,
      }),
    onSuccess: async () => {
      setEditDepartment(null);
      await queryClient.invalidateQueries({ queryKey: ["departments"] });
      pushToast({ tone: "success", title: "Đã cập nhật phòng ban" });
    },
    onError: (error) =>
      pushToast({ tone: "error", title: "Cập nhật thất bại", message: safeErrorMessage(error) }),
  });

  const deleteMutation = useMutation({
    mutationFn: (departmentId: string) => apiClient.departments.delete(departmentId),
    onSuccess: async () => {
      if (editDepartment?.id === deleteId) {
        setEditDepartment(null);
      }
      setDeleteId(null);
      await queryClient.invalidateQueries({ queryKey: ["departments"] });
      pushToast({ tone: "success", title: "Đã xóa phòng ban" });
    },
    onError: (error) => {
      setDeleteId(null);
      pushToast({ tone: "error", title: "Xóa thất bại", message: safeErrorMessage(error) });
    },
  });

  const departments = departmentsQuery.data?.data ?? [];

  const startEdit = (department: Department) => {
    editForm.reset(valuesFromDepartment(department));
    setEditDepartment(department);
  };

  return (
    <div>
      <PageHeader title="Phòng ban" description="Tài liệu phạm vi Phòng ban chỉ hiển thị với thành viên của phòng đó." />
      <div className="grid items-start gap-5 xl:grid-cols-[20rem_minmax(0,1fr)]">
        <section className="rounded-xl border border-border/70 bg-surface p-5" aria-labelledby="department-form-title">
          {editDepartment ? (
            <>
              <h2 id="department-form-title" className="mb-4 text-[15px] font-semibold">
                Sửa phòng ban
              </h2>
              <form
                className="space-y-4"
                onSubmit={editForm.handleSubmit((values) =>
                  updateMutation.mutate({ departmentId: editDepartment.id, values }),
                )}
                noValidate
              >
                <DepartmentFields form={editForm} idPrefix="edit-department" />
                <div className="flex flex-wrap gap-2">
                  <Button type="submit" loading={updateMutation.isPending}>
                    Lưu thay đổi
                  </Button>
                  <Button type="button" variant="secondary" onClick={() => setEditDepartment(null)}>
                    Hủy
                  </Button>
                </div>
              </form>
            </>
          ) : (
            <>
              <h2 id="department-form-title" className="mb-4 text-[15px] font-semibold">
                Tạo phòng ban
              </h2>
              <form
                className="space-y-4"
                onSubmit={createForm.handleSubmit((values) => createMutation.mutate(values))}
                noValidate
              >
                <DepartmentFields form={createForm} idPrefix="department" />
                <Button type="submit" className="w-full" loading={createMutation.isPending}>
                  Tạo phòng ban
                </Button>
              </form>
            </>
          )}
        </section>

        <section aria-label="Danh sách phòng ban">
          <div className="mb-4 max-w-md">
            <FieldWrapper id="department-search" label="Tìm kiếm">
              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-muted" aria-hidden="true" />
                <TextInput
                  id="department-search"
                  className="pl-9"
                  placeholder="Tên hoặc mã"
                  value={search}
                  onChange={(event) => {
                    setPage(1);
                    setSearch(event.target.value);
                  }}
                />
              </div>
            </FieldWrapper>
          </div>
          {departmentsQuery.isLoading ? <LoadingState label="Đang tải phòng ban" /> : null}
          {departmentsQuery.isError ? (
            <ErrorState
              title="Không tải được danh sách phòng ban"
              error={departmentsQuery.error}
              onRetry={() => void departmentsQuery.refetch()}
            />
          ) : null}
          {!departmentsQuery.isLoading && !departmentsQuery.isError && departments.length === 0 ? (
            <EmptyState title={search.trim() ? "Không có phòng ban phù hợp" : "Chưa có phòng ban nào"} />
          ) : null}
          {departments.length ? (
            <>
              <DataTable columns={["Tên", "Mã", "Mô tả", "Thao tác"]}>
                {departments.map((department) => (
                  <tr key={department.id}>
                    <td className="px-5 py-3.5 font-medium text-ink">{department.name}</td>
                    <td className="px-5 py-3.5">
                      <span className="rounded-[6px] bg-elevated px-2 py-0.5 font-mono text-xs text-ink/80">
                        {department.code}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 text-muted">{department.description ?? "—"}</td>
                    <td className="px-5 py-3.5">
                      <div className="flex justify-end gap-4 whitespace-nowrap text-sm">
                        <button
                          type="button"
                          className="text-ink transition hover:text-accent"
                          onClick={() => startEdit(department)}
                        >
                          Sửa
                        </button>
                        <button
                          type="button"
                          className="text-danger transition hover:text-danger/80"
                          onClick={() => setDeleteId(department.id)}
                        >
                          Xóa
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </DataTable>
              {departmentsQuery.data?.meta ? (
                <Pagination meta={departmentsQuery.data.meta} onPageChange={setPage} />
              ) : null}
            </>
          ) : null}
        </section>
      </div>
      <ConfirmDialog
        open={Boolean(deleteId)}
        title="Xóa phòng ban?"
        message="Chỉ xóa được khi phòng ban không còn người dùng đang hoạt động. Người dùng đã vô hiệu hóa sẽ không còn gắn với phòng ban này."
        confirmLabel="Xóa"
        loading={deleteMutation.isPending}
        onCancel={() => setDeleteId(null)}
        onConfirm={() => deleteId && deleteMutation.mutate(deleteId)}
      />
    </div>
  );
}

function DepartmentFields({ form, idPrefix }: { form: UseFormReturn<DepartmentForm>; idPrefix: string }) {
  const errors = form.formState.errors;
  return (
    <>
      <FieldWrapper id={`${idPrefix}-name`} label="Tên" error={errors.name?.message}>
        <TextInput id={`${idPrefix}-name`} {...form.register("name")} />
      </FieldWrapper>
      <FieldWrapper
        id={`${idPrefix}-code`}
        label="Mã"
        error={errors.code?.message}
        help="Chữ không dấu, số, dấu _ hoặc -"
      >
        <TextInput id={`${idPrefix}-code`} className="font-mono" {...form.register("code")} />
      </FieldWrapper>
      <FieldWrapper id={`${idPrefix}-description`} label="Mô tả (tùy chọn)" error={errors.description?.message}>
        <TextArea id={`${idPrefix}-description`} className="min-h-20" {...form.register("description")} />
      </FieldWrapper>
    </>
  );
}

