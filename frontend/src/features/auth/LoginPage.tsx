import { zodResolver } from "@hookform/resolvers/zod";
import { ShieldCheck } from "lucide-react";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { z } from "zod";
import { Button } from "../../components/ui/Button";
import { FieldWrapper, TextInput } from "../../components/ui/Field";
import { SoftSignalBackground } from "../../components/motion/SoftSignalBackground";
import { safeErrorMessage } from "../../api/errors";
import { appConfig } from "../../lib/config";
import { useToast } from "../../components/feedback/ToastProvider";
import { useAuth } from "./AuthProvider";

const loginSchema = z.object({
  email: z.string().trim().email("Enter a valid email."),
  password: z.string().min(1, "Password is required."),
});

type LoginForm = z.infer<typeof loginSchema>;

export function LoginPage() {
  const { status, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { pushToast } = useToast();
  const from = (location.state as { from?: string } | null)?.from ?? "/chat";

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<LoginForm>({ resolver: zodResolver(loginSchema) });

  useEffect(() => {
    if (status === "expired") {
      pushToast({ tone: "warning", title: "Session expired", message: "Sign in again to continue." });
    }
  }, [pushToast, status]);

  if (status === "authenticated") {
    return <Navigate to={from} replace />;
  }

  const onSubmit = handleSubmit(async (values) => {
    try {
      await login(values);
      navigate(from, { replace: true });
    } catch (error) {
      setError("root", { message: safeErrorMessage(error) });
    }
  });

  return (
    <main className="relative min-h-[100dvh] overflow-hidden bg-canvas px-4 py-8 text-ink">
      <SoftSignalBackground />
      <div className="relative z-10 mx-auto grid min-h-[calc(100dvh-4rem)] max-w-6xl items-center gap-8 lg:grid-cols-[1fr_24rem]">
        <section className="max-w-2xl">
          <div className="mb-6 inline-flex items-center gap-2 rounded-token border border-border bg-surface px-3 py-2 text-sm font-semibold text-muted shadow-sm">
            <ShieldCheck className="h-4 w-4 text-accent" aria-hidden="true" />
            Secure enterprise workspace
          </div>
          <h1 className="max-w-2xl text-4xl font-semibold leading-tight tracking-normal text-ink md:text-5xl">
            {appConfig.appName}
          </h1>
          <p className="mt-4 max-w-xl text-base leading-7 text-muted">
            Operate documents, citations, audit controls, and grounded AI answers from one authenticated console.
          </p>
        </section>

        <section className="rounded-token border border-border bg-surface p-6 shadow-panel" aria-labelledby="login-title">
          <div className="mb-6">
            <h2 id="login-title" className="text-xl font-semibold text-ink">
              Sign in
            </h2>
            <p className="mt-1 text-sm text-muted">Use your enterprise account credentials.</p>
          </div>
          <form className="space-y-4" onSubmit={onSubmit} noValidate>
            <FieldWrapper id="email" label="Email" error={errors.email?.message}>
              <TextInput id="email" type="email" autoComplete="email" {...register("email")} />
            </FieldWrapper>
            <FieldWrapper id="password" label="Password" error={errors.password?.message}>
              <TextInput id="password" type="password" autoComplete="current-password" {...register("password")} />
            </FieldWrapper>
            {errors.root?.message ? (
              <p className="rounded-token border border-danger/20 bg-danger/5 px-3 py-2 text-sm font-medium text-danger" role="alert">
                {errors.root.message}
              </p>
            ) : null}
            <Button className="w-full" type="submit" loading={isSubmitting}>
              Sign in
            </Button>
          </form>
        </section>
      </div>
    </main>
  );
}