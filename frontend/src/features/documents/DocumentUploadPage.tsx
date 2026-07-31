import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Upload } from "lucide-react";
import { useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { z } from "zod";
import { apiClient } from "../../api/client";
import { safeErrorMessage } from "../../api/errors";
import { useToast } from "../../components/feedback/ToastProvider";
import { PageHeader } from "../../components/layout/PageHeader";
import { Button } from "../../components/ui/Button";
import { FieldWrapper, SelectInput, TextArea, TextInput } from "../../components/ui/Field";
import { Panel } from "../../components/ui/Panel";

const uploadSchema = z.object({
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
});

type UploadForm = z.infer<typeof uploadSchema>;

export function DocumentUploadPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { pushToast } = useToast();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [selectedFileName, setSelectedFileName] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    setValue,
    trigger,
    formState: { errors },
  } = useForm<UploadForm>({ resolver: zodResolver(uploadSchema), defaultValues: { access_scope: "PRIVATE" } });
  const fileRegister = register("file");

  const uploadMutation = useMutation({
    mutationFn: (values: UploadForm) =>
      apiClient.documents.upload({
        file: values.file[0],
        title: values.title,
        description: values.description || null,
        access_scope: values.access_scope,
        department_id: values.department_id || null,
      }),
    onSuccess: async (response) => {
      await queryClient.invalidateQueries({ queryKey: ["documents"] });
      pushToast({ tone: "success", title: "Upload accepted", message: "Processing continues in the backend." });
      navigate(`/documents/${response.data.id}`);
    },
    onError: (error) => pushToast({ tone: "error", title: "Upload failed", message: safeErrorMessage(error) }),
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
          <FieldWrapper id="department_id" label="Department ID" error={errors.department_id?.message} help="Required by backend policy for department-scoped documents.">
            <TextInput id="department_id" {...register("department_id")} />
          </FieldWrapper>
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