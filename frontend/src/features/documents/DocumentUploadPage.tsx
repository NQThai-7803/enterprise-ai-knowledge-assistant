import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronLeft, Upload, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router-dom";
import { z } from "zod";
import { apiClient } from "../../api/client";
import { isApiError, safeErrorMessage } from "../../api/errors";
import type { DocumentAccessScope, DocumentLifecycleStatus } from "../../api/types";
import { useToast } from "../../components/feedback/ToastProvider";
import { Button } from "../../components/ui/Button";
import { FieldWrapper, SelectInput, TextArea, TextInput } from "../../components/ui/Field";
import { formatBytes } from "../../lib/format";
import { lifecycleLabels } from "../../lib/labels";
import { useAuth } from "../auth/AuthProvider";

// The one 422 message API_SPEC §7 documents word for word.
const EFFECTIVE_ORDER_MESSAGE = "effective_to must not precede effective_from.";
const EFFECTIVE_ORDER_TEXT = "Ngày hết hiệu lực không được trước ngày bắt đầu hiệu lực.";

const uploadSchema = z
  .object({
    title: z.string().trim().min(1, "Nhập tiêu đề.").max(255, "Tiêu đề tối đa 255 ký tự."),
    description: z.string().trim().optional(),
    access_scope: z.enum(["PRIVATE", "DEPARTMENT", "ORGANIZATION"]),
    department_id: z.string().optional(),
    document_code: z.string().trim().max(128, "Mã tài liệu tối đa 128 ký tự.").optional(),
    document_version: z.string().trim().max(64, "Phiên bản tối đa 64 ký tự.").optional(),
    effective_from: z.string().optional(),
    effective_to: z.string().optional(),
    lifecycle_status: z.enum(["ACTIVE", "SUPERSEDED", "ARCHIVED", "DRAFT"]),
    supersedes_document_id: z.string().optional(),
    file: z
      .custom<FileList>((value) => value instanceof FileList && value.length === 1, "Chọn một tệp PDF.")
      .refine(
        (files) => files[0]?.type === "application/pdf" || files[0]?.name.toLowerCase().endsWith(".pdf"),
        "Chỉ nhận tệp PDF.",
      ),
  })
  .superRefine((values, context) => {
    if (values.access_scope === "DEPARTMENT" && !values.department_id) {
      context.addIssue({ code: z.ZodIssueCode.custom, path: ["department_id"], message: "Chọn phòng ban." });
    }
    // YYYY-MM-DD strings compare in date order.
    if (values.effective_from && values.effective_to && values.effective_to < values.effective_from) {
      context.addIssue({ code: z.ZodIssueCode.custom, path: ["effective_to"], message: EFFECTIVE_ORDER_TEXT });
    }
  });

type UploadForm = z.infer<typeof uploadSchema>;

const VERSION_FIELDS = [
  "document_code",
  "document_version",
  "effective_from",
  "effective_to",
  "lifecycle_status",
  "supersedes_document_id",
] as const;

const SCOPE_OPTIONS: { value: DocumentAccessScope; title: string; description: string }[] = [
  { value: "ORGANIZATION", title: "Toàn công ty", description: "Mọi người dùng đang hoạt động" },
  { value: "DEPARTMENT", title: "Phòng ban", description: "Chỉ thành viên phòng được chọn" },
  { value: "PRIVATE", title: "Riêng tư", description: "Người tải lên và người được cấp quyền" },
];

export function DocumentUploadPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { pushToast } = useToast();
  const { user } = useAuth();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [departmentFilter, setDepartmentFilter] = useState("");
  const [versionOpen, setVersionOpen] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    setValue,
    setError,
    resetField,
    trigger,
    watch,
    clearErrors,
    formState: { errors },
  } = useForm<UploadForm>({
    resolver: zodResolver(uploadSchema),
    defaultValues: { access_scope: "PRIVATE", lifecycle_status: "ACTIVE" },
  });
  const fileRegister = register("file");
  const accessScope = watch("access_scope");
  const lifecycleStatus = watch("lifecycle_status");
  const selectedFile = watch("file")?.[0] ?? null;
  const requiresDepartment = accessScope === "DEPARTMENT";

  // BR-1: Admin may upload anywhere; a Manager only PRIVATE or DEPARTMENT with their own department (from /auth/me).
  const isAdmin = user?.role === "ADMIN";
  const ownDepartment = !isAdmin && user?.department_id ? { id: user.department_id, name: user.department_name } : null;
  const scopeDisabled = (scope: DocumentAccessScope) =>
    !isAdmin && (scope === "ORGANIZATION" || (scope === "DEPARTMENT" && !ownDepartment));

  const departmentsQuery = useQuery({
    queryKey: ["departments", "upload-selector"],
    queryFn: () => apiClient.departments.list({ page: 1, page_size: 100 }),
    enabled: isAdmin && requiresDepartment,
    staleTime: 5 * 60_000,
  });

  // shortcut: offers the first 100 documents the caller can view; switch to a search box when lists grow.
  const supersedableQuery = useQuery({
    queryKey: ["documents", "supersedable"],
    queryFn: () => apiClient.documents.list({ page: 1, page_size: 100 }),
    enabled: versionOpen,
    staleTime: 60_000,
  });

  const departments = useMemo(() => departmentsQuery.data?.data ?? [], [departmentsQuery.data]);
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
        document_code: values.document_code || null,
        document_version: values.document_version || null,
        effective_from: values.effective_from || null,
        effective_to: values.effective_to || null,
        lifecycle_status: values.lifecycle_status,
        supersedes_document_id: values.supersedes_document_id || null,
      }),
    onSuccess: async (response) => {
      await queryClient.invalidateQueries({ queryKey: ["documents"] });
      pushToast({ tone: "success", title: "Đã nhận tài liệu", message: "Tài liệu đang được xử lý nền." });
      navigate(`/documents/${response.data.id}`);
    },
    onError: (error) => {
      if (isApiError(error) && error.status === 422 && error.message === EFFECTIVE_ORDER_MESSAGE) {
        setVersionOpen(true);
        setError("effective_to", { message: EFFECTIVE_ORDER_TEXT });
        return;
      }
      setServerError(uploadErrorMessage(error));
    },
  });

  const setDroppedFiles = async (files: FileList) => {
    setValue("file", files, { shouldDirty: true, shouldValidate: true });
    await trigger("file");
  };

  const removeFile = () => {
    resetField("file");
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const onSubmit = handleSubmit(
    (values) => {
      setServerError(null);
      uploadMutation.mutate(values);
    },
    (formErrors) => {
      if (VERSION_FIELDS.some((field) => formErrors[field])) {
        setVersionOpen(true);
      }
    },
  );

  return (
    <div>
      <Link to="/documents" className="mb-5 inline-flex items-center gap-1 text-sm text-muted transition hover:text-ink">
        <ChevronLeft className="h-4 w-4" aria-hidden="true" />
        Tài liệu
      </Link>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-normal text-ink">Tải tài liệu lên</h1>
        <p className="mt-1 max-w-3xl text-sm leading-6 text-muted">
          Chỉ nhận PDF. Hệ thống kiểm tra tệp, rồi xử lý nền trước khi tài liệu được dùng để trả lời.
        </p>
      </div>

      <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,1fr)_19rem]">
        <form
          className="space-y-5 rounded-xl border border-border/70 bg-surface p-6"
          onSubmit={onSubmit}
          noValidate
        >
          <FieldWrapper id="file" label="Tệp PDF" error={errors.file?.message}>
            {selectedFile ? (
              <div className="flex items-center gap-3 rounded-xl border border-border/70 bg-elevated px-4 py-3">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-token bg-danger/10 text-[11px] font-semibold text-danger">
                  PDF
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">{selectedFile.name}</p>
                  <p className="text-xs text-muted">{formatBytes(selectedFile.size)}</p>
                </div>
                <button
                  type="button"
                  className="flex h-8 w-8 items-center justify-center rounded-token text-muted transition hover:bg-canvas hover:text-ink"
                  onClick={removeFile}
                  aria-label="Bỏ tệp đã chọn"
                >
                  <X className="h-4 w-4" aria-hidden="true" />
                </button>
              </div>
            ) : (
              <div
                className={`rounded-xl border border-dashed p-6 text-center transition ${dragActive ? "border-accent bg-accent/10" : "border-border bg-elevated"}`}
                role="button"
                tabIndex={0}
                aria-label="Chọn tệp PDF"
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
                <Upload className="mx-auto h-7 w-7 text-accent" aria-hidden="true" />
                <p className="mt-2 text-sm font-medium text-ink">Kéo thả tệp PDF vào đây hoặc bấm để chọn</p>
                <p className="mt-1 text-xs text-muted">Một tệp PDF mỗi lần tải lên.</p>
              </div>
            )}
            <TextInput
              id="file"
              className="sr-only"
              type="file"
              accept="application/pdf,.pdf"
              name={fileRegister.name}
              onBlur={fileRegister.onBlur}
              onChange={(event) => void fileRegister.onChange(event)}
              ref={(element) => {
                fileRegister.ref(element);
                fileInputRef.current = element;
              }}
            />
          </FieldWrapper>

          <FieldWrapper id="title" label="Tiêu đề" error={errors.title?.message}>
            <TextInput id="title" maxLength={255} {...register("title")} />
          </FieldWrapper>
          <FieldWrapper id="description" label="Mô tả (tùy chọn)" error={errors.description?.message}>
            <TextArea id="description" className="min-h-20" {...register("description")} />
          </FieldWrapper>

          <fieldset>
            <legend className="mb-2 text-sm font-medium text-ink">Ai được xem tài liệu này?</legend>
            <div className="grid gap-2.5 sm:grid-cols-3">
              {SCOPE_OPTIONS.map((option) => {
                const disabled = scopeDisabled(option.value);
                return (
                  <label
                    key={option.value}
                    className="flex cursor-pointer flex-col gap-1 rounded-xl border border-border/70 p-3.5 transition hover:bg-canvas has-[:checked]:border-accent has-[:checked]:bg-accent/5 has-[:disabled]:cursor-not-allowed has-[:disabled]:opacity-50 has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-accent/30"
                  >
                    <span className="flex items-center gap-2 text-sm font-medium">
                      <input
                        type="radio"
                        value={option.value}
                        disabled={disabled}
                        className="accent-[rgb(var(--color-accent))]"
                        {...register("access_scope")}
                      />
                      {option.title}
                    </span>
                    <span className="text-xs text-muted">
                      {disabled
                        ? option.value === "ORGANIZATION"
                          ? "Chỉ quản trị viên chọn được"
                          : "Bạn chưa thuộc phòng ban nào"
                        : option.description}
                    </span>
                  </label>
                );
              })}
            </div>
          </fieldset>

          {requiresDepartment ? (
            <div className="space-y-3">
              {isAdmin && departments.length > 8 ? (
                <FieldWrapper id="department_filter" label="Tìm phòng ban" help="Lọc theo tên hoặc mã.">
                  <TextInput
                    id="department_filter"
                    value={departmentFilter}
                    onChange={(event) => setDepartmentFilter(event.target.value)}
                    disabled={departmentsQuery.isLoading}
                  />
                </FieldWrapper>
              ) : null}
              <FieldWrapper
                id="department_id"
                label="Phòng ban"
                error={errors.department_id?.message}
                help={isAdmin ? undefined : "Quản lý chỉ tải lên được cho phòng ban của mình."}
              >
                {/* Not pre-filled: the user picks the department, even when only their own is allowed. */}
                <SelectInput
                  id="department_id"
                  {...register("department_id")}
                  disabled={isAdmin && (departmentsQuery.isLoading || departmentsQuery.isError || departments.length === 0)}
                >
                  <option value="">
                    {isAdmin && departmentsQuery.isLoading ? "Đang tải phòng ban…" : "Chọn phòng ban"}
                  </option>
                  {isAdmin
                    ? filteredDepartments.map((department) => (
                        <option key={department.id} value={department.id}>
                          {department.code ? `${department.name} (${department.code})` : department.name}
                        </option>
                      ))
                    : null}
                  {ownDepartment ? (
                    <option value={ownDepartment.id}>{ownDepartment.name ?? "Phòng ban của bạn"}</option>
                  ) : null}
                </SelectInput>
              </FieldWrapper>
              {isAdmin && departmentsQuery.isError ? (
                <div
                  className="flex items-center justify-between gap-3 rounded-token border border-danger/20 bg-danger/5 p-3 text-xs text-danger"
                  role="alert"
                >
                  <span>Không tải được danh sách phòng ban.</span>
                  <Button type="button" variant="secondary" onClick={() => void departmentsQuery.refetch()}>
                    Thử lại
                  </Button>
                </div>
              ) : null}
              {isAdmin && !departmentsQuery.isLoading && !departmentsQuery.isError && departments.length === 0 ? (
                <p className="text-xs text-muted" role="status">
                  Chưa có phòng ban nào.
                </p>
              ) : null}
              {isAdmin && departments.length > 0 && filteredDepartments.length === 0 ? (
                <p className="text-xs text-muted" role="status">
                  Không có phòng ban khớp bộ lọc.
                </p>
              ) : null}
            </div>
          ) : null}

          <details
            className="border-t border-border/70 pt-4"
            open={versionOpen}
            onToggle={(event) => setVersionOpen(event.currentTarget.open)}
          >
            <summary className="cursor-pointer text-sm font-medium text-ink">
              Thông tin phiên bản <span className="font-normal text-muted">(tùy chọn)</span>
            </summary>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <FieldWrapper id="document_code" label="Mã tài liệu" error={errors.document_code?.message}>
                <TextInput id="document_code" maxLength={128} placeholder="ND-HR-007" {...register("document_code")} />
              </FieldWrapper>
              <FieldWrapper id="document_version" label="Phiên bản" error={errors.document_version?.message}>
                <TextInput id="document_version" maxLength={64} placeholder="1.0" {...register("document_version")} />
              </FieldWrapper>
              <FieldWrapper id="effective_from" label="Hiệu lực từ" error={errors.effective_from?.message}>
                <TextInput id="effective_from" type="date" {...register("effective_from")} />
              </FieldWrapper>
              <FieldWrapper id="effective_to" label="Hiệu lực đến" error={errors.effective_to?.message}>
                <TextInput id="effective_to" type="date" {...register("effective_to")} />
              </FieldWrapper>
              <FieldWrapper
                id="lifecycle_status"
                label="Vòng đời"
                help={
                  lifecycleStatus === "DRAFT"
                    ? "Bản nháp vẫn hiện trong danh sách nhưng không được dùng để trả lời."
                    : undefined
                }
              >
                <SelectInput id="lifecycle_status" {...register("lifecycle_status")}>
                  {(Object.keys(lifecycleLabels) as DocumentLifecycleStatus[]).map((value) => (
                    <option key={value} value={value}>
                      {lifecycleLabels[value]}
                    </option>
                  ))}
                </SelectInput>
              </FieldWrapper>
              <FieldWrapper id="supersedes_document_id" label="Thay thế tài liệu">
                <SelectInput id="supersedes_document_id" {...register("supersedes_document_id")}>
                  <option value="">
                    {supersedableQuery.isLoading ? "Đang tải tài liệu…" : "Không thay thế tài liệu nào"}
                  </option>
                  {(supersedableQuery.data?.data ?? []).map((document) => (
                    <option key={document.id} value={document.id}>
                      {document.document_code ? `${document.document_code} · ${document.title}` : document.title}
                    </option>
                  ))}
                </SelectInput>
              </FieldWrapper>
            </div>
          </details>

          {serverError ? (
            <p
              className="rounded-token border border-danger/20 bg-danger/5 px-3 py-2 text-sm font-medium text-danger"
              role="alert"
            >
              {serverError}
            </p>
          ) : null}

          <Button
            type="submit"
            loading={uploadMutation.isPending}
            icon={<Upload className="h-4 w-4" aria-hidden="true" />}
          >
            Tải lên
          </Button>
        </form>

        <aside className="rounded-xl border border-border/70 bg-surface p-5 text-sm" aria-labelledby="after-upload">
          <h2 id="after-upload" className="mb-3 font-semibold">
            Sau khi tải lên
          </h2>
          <ol className="list-decimal space-y-2 pl-5 text-ink/80">
            <li>Kiểm tra định dạng PDF, kích thước và tệp trùng.</li>
            <li>Trích xuất văn bản theo trang, chia đoạn và tạo embedding.</li>
            <li>Khi trạng thái là Sẵn sàng, tài liệu được dùng để trả lời cho người có quyền.</li>
          </ol>
          <p className="mt-4 rounded-token bg-elevated px-3 py-2 text-xs text-muted">
            Tài liệu ở trạng thái Bản nháp không bao giờ được dùng để trả lời.
          </p>
        </aside>
      </div>
    </div>
  );
}

function uploadErrorMessage(error: unknown): string {
  if (!isApiError(error)) {
    return safeErrorMessage(error);
  }
  if (error.status === 422) {
    // TODO(BR-10): map 422 details to fields once API_SPEC documents their shape.
    return `Thông tin tải lên chưa hợp lệ: ${error.message}`;
  }
  if (error.status === 403) {
    return "Bạn không được tải lên với phạm vi hoặc phòng ban này.";
  }
  if (error.status === 404) {
    return "Không tìm thấy phòng ban, hoặc tài liệu được thay thế mà bạn xem được.";
  }
  if (error.code === "DUPLICATE_DOCUMENT") {
    return "Tệp này đã được tải lên trước đó.";
  }
  if (error.status === 413) {
    return "Tệp quá lớn.";
  }
  if (error.status === 415) {
    return "Chỉ nhận tệp PDF.";
  }
  return safeErrorMessage(error);
}
