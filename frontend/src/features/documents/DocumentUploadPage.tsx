import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Upload } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { z } from "zod";
import { apiClient } from "../../api/client";
import { isApiError, safeErrorMessage } from "../../api/errors";
import { useToast } from "../../components/feedback/ToastProvider";
import { PageHeader } from "../../components/layout/PageHeader";
import { Button } from "../../components/ui/Button";
import { FieldWrapper, SelectInput, TextArea, TextInput } from "../../components/ui/Field";
import { Panel } from "../../components/ui/Panel";

const uploadSchema = z
  .object({
    title: z.string().trim().min(1, "Title is required.").max(255),
    description: z.string().trim().optional(),
    access_scope: z.enum(["PRIVATE", "DEPARTMENT", "ORGANIZATION"]),
    department_id: z.string().trim().optional(),
    file: z
      .custom<FileList>((value) => value instanceof FileList && value.length === 1, "Choose one PDF file.")
      .refine(
        (files) => files[0]?.type === "application/pdf" || files[0]?.name.toLowerCase().endsWith(".pdf"),
        "Only PDF files are supported.",
      ),
  })
  .superRefine((values, context) => {
    if (values.access_scope === "DEPARTMENT" && !values.department_id?.trim()) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["department_id"],
        message: "Vui lòng chọn phòng ban.",
      });
    }
  });

type UploadForm = z.infer<typeof uploadSchema>;

export function DocumentUploadPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { pushToast } = useToast();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [selectedFileName, setSelectedFileName] = useState<string | null>(null);
  const [departmentFilter, setDepartmentFilter] = useState("");
  const {
    register,
    handleSubmit,
    setValue,
    trigger,
    watch,
    clearErrors,
    formState: { errors },
  } = useForm<UploadForm>({ resolver: zodResolver(uploadSchema), defaultValues: { access_scope: "PRIVATE" } });
  const fileRegister = register("file");
  const accessScope = watch("access_scope");
  const requiresDepartment = accessScope === "DEPARTMENT";

  const departmentsQuery = useQuery({
    queryKey: ["departments", "upload-selector"],
    queryFn: () => apiClient.departments.list({ page: 1, page_size: 100 }),
    enabled: requiresDepartment,
    staleTime: 5 * 60_000,
  });

  const departments = departmentsQuery.data?.data ?? [];
  const filteredDepartments = useMemo(() => {
    const query = departmentFilter.trim().toLocaleLowerCase("vi");
    if (!query) {
      return departments;
    }
    return departments.filter((department) =>
      `${department.name} ${department.code}`.toLocaleLowerCase("vi").includes(query),
    );
  }, [departmentFilter, departments]);

  useEffect(() => {
    if (!requiresDepartment) {
      setValue("department_id", "", { shouldDirty: true, shouldValidate: false });
      clearErrors("department_id");
      setDepartmentFilter("");
    }
  }, [clearErrors, requiresDepartment, setValue]);

  const uploadMutation = useMutation({
    mutationFn: (values: UploadForm) =>
      apiClient.documents.upload({
        file: values.file[0],
        title: values.title,
        description: values.description || null,
        access_scope: values.access_scope,
        department_id: values.access_scope === "DEPARTMENT" ? values.department_id || null : null,
      }),
    onSuccess: async (response) => {
      await queryClient.invalidateQueries({ queryKey: ["documents"] });
      pushToast({ tone: "success", title: "Upload accepted", message: "Processing continues in the backend." });
      navigate(`/documents/${response.data.id}`);
    },
    onError: (error) => pushToast({ tone: "error", title: "Upload failed", message: uploadErrorMessage(error) }),
  });

  const setDroppedFiles = async (files: FileList) => {
    setValue("file", files, { shouldDirty: true, shouldValidate: true });
    setSelectedFileName(files[0]?.name ?? null);
    await trigger("file");
  };

  return (
    <div>
      <PageHeader title="Document upload" description="Upload completion and document processing are separate backend states." />
      <Panel className="max-w-2xl p-5">
        <form className="space-y-4" onSubmit={handleSubmit((values) => uploadMutation.mutate(values))} noValidate>
          <FieldWrapper id="title" label="Title" error={errors.title?.message}>
            <TextInput id="title" {...register("title")} />
          </FieldWrapper>
          <FieldWrapper id="description" label="Description" error={errors.description?.message}>
            <TextArea id="description" {...register("description")} />
          </FieldWrapper>
          <FieldWrapper id="access_scope" label="Access scope" error={errors.access_scope?.message}>
            <SelectInput id="access_scope" {...register("access_scope")}>
              <option value="PRIVATE">Private</option>
              <option value="DEPARTMENT">Department</option>
              <option value="ORGANIZATION">Organization</option>
            </SelectInput>
          </FieldWrapper>
          {requiresDepartment ? (
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
              <FieldWrapper id="department_id" label="Department" error={errors.department_id?.message}>
                <SelectInput
                  id="department_id"
                  {...register("department_id")}
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
              {departmentsQuery.isLoading ? (
                <p className="text-xs text-muted" role="status">
                  Loading departments...
                </p>
              ) : null}
              {departmentsQuery.isError ? (
                <div
                  className="flex items-center justify-between gap-3 rounded-token border border-danger/20 bg-danger/5 p-3 text-xs text-danger"
                  role="alert"
                >
                  <span>Could not load departments.</span>
                  <Button type="button" variant="secondary" onClick={() => void departmentsQuery.refetch()}>
                    Retry
                  </Button>
                </div>
              ) : null}
              {!departmentsQuery.isLoading && !departmentsQuery.isError && departments.length === 0 ? (
                <p className="text-xs text-muted" role="status">
                  No departments available.
                </p>
              ) : null}
              {!departmentsQuery.isLoading &&
              !departmentsQuery.isError &&
              departments.length > 0 &&
              filteredDepartments.length === 0 ? (
                <p className="text-xs text-muted" role="status">
                  No departments match the filter.
                </p>
              ) : null}
            </div>
          ) : null}
          <FieldWrapper id="file" label="PDF file" error={errors.file?.message}>
            <div
              className={`rounded-token border border-dashed p-5 text-center transition ${dragActive ? "border-accent bg-accent/10" : "border-border bg-elevated"}`}
              role="button"
              tabIndex={0}
              onClick={() => fileInputRef.current?.click()}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  fileInputRef.current?.click();
                }
              }}
              onDragEnter={(event) => {
                event.preventDefault();
                setDragActive(true);
              }}
              onDragOver={(event) => {
                event.preventDefault();
                setDragActive(true);
              }}
              onDragLeave={() => setDragActive(false)}
              onDrop={(event) => {
                event.preventDefault();
                setDragActive(false);
                if (event.dataTransfer.files.length > 0) {
                  void setDroppedFiles(event.dataTransfer.files);
                }
              }}
            >
              <Upload className="mx-auto h-8 w-8 text-accent" aria-hidden="true" />
              <p className="mt-2 text-sm font-semibold text-ink">Drop a PDF here or choose a file</p>
              <p className="mt-1 text-xs text-muted">{selectedFileName ?? "One PDF per upload request."}</p>
              <TextInput
                id="file"
                className="sr-only"
                type="file"
                accept="application/pdf,.pdf"
                name={fileRegister.name}
                onBlur={fileRegister.onBlur}
                onChange={(event) => {
                  void fileRegister.onChange(event);
                  setSelectedFileName(event.target.files?.[0]?.name ?? null);
                }}
                ref={(element) => {
                  fileRegister.ref(element);
                  fileInputRef.current = element;
                }}
              />
            </div>
          </FieldWrapper>
          <Button type="submit" loading={uploadMutation.isPending} icon={<Upload className="h-4 w-4" aria-hidden="true" />}>
            Upload
          </Button>
        </form>
      </Panel>
    </div>
  );
}

function formatDepartmentOption(department: { name: string; code: string }) {
  return department.code ? `${department.name} (${department.code})` : department.name;
}

function uploadErrorMessage(error: unknown): string {
  if (isApiError(error) && error.status === 422) {
    const message = error.message.toLocaleLowerCase("vi");
    const details = JSON.stringify(error.details ?? "").toLocaleLowerCase("vi");
    if (message.includes("department") || details.includes("department")) {
      return "Vui lòng chọn phòng ban.";
    }
    return "Thông tin tải lên chưa hợp lệ. Vui lòng kiểm tra lại biểu mẫu.";
  }
  return safeErrorMessage(error);
}
