import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ShieldPlus, Trash2 } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useParams } from "react-router-dom";
import { z } from "zod";
import { apiClient } from "../../api/client";
import { safeErrorMessage } from "../../api/errors";
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
  grantee_id: z.string().trim().min(1, "Grantee ID is required."),
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
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<PermissionForm>({ resolver: zodResolver(permissionSchema), defaultValues: defaultGrant });

  const permissionsQuery = useQuery({
    queryKey: ["documents", "permissions", documentId],
    queryFn: () => apiClient.documents.permissions(documentId as string),
    enabled: Boolean(documentId),
  });

  const permissions = permissionsQuery.data?.data ?? [];
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
      await queryClient.invalidateQueries({ queryKey: ["documents", "permissions", documentId] });
      pushToast({ tone: "success", title: "Permission granted" });
    },
    onError: (error) => pushToast({ tone: "error", title: "Grant failed", message: safeErrorMessage(error) }),
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
    onChange: (event) => setGrantDraft((current) => ({ ...current, grantee_type: event.target.value as PermissionForm["grantee_type"] })),
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
            <FieldWrapper id="grantee_id" label="Grantee ID" error={errors.grantee_id?.message}>
              <TextInput id="grantee_id" {...granteeIdField} />
            </FieldWrapper>
            <FieldWrapper id="permission" label="Permission" error={errors.permission?.message}>
              <SelectInput id="permission" {...permissionField}>
                <option value="VIEW">View</option>
                <option value="EDIT">Edit</option>
                <option value="MANAGE">Manage</option>
              </SelectInput>
            </FieldWrapper>
            <Button type="submit" disabled={duplicateGrant} loading={grantMutation.isPending} icon={<ShieldPlus className="h-4 w-4" aria-hidden="true" />}>
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
                  <td className="px-4 py-3 text-sm">
                    {permission.user_id ? <span>User {truncateMiddle(permission.user_id)}</span> : <span>Department {truncateMiddle(permission.department_id ?? "")}</span>}
                  </td>
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