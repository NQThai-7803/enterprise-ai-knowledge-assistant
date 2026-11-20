import { zodResolver } from "@hookform/resolvers/zod";
import { Box, Eye, EyeOff } from "lucide-react";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { z } from "zod";
import { ApiError, safeErrorMessage } from "../../api/errors";
import { Button } from "../../components/ui/Button";
import { FieldWrapper, TextInput } from "../../components/ui/Field";
import { useToast } from "../../components/feedback/ToastProvider";
import { appConfig } from "../../lib/config";
import { useAuth } from "./AuthProvider";

const loginSchema = z.object({
  email: z.string().trim().email("Nhập email hợp lệ."),
  password: z.string().min(1, "Nhập mật khẩu."),
});

type LoginForm = z.infer<typeof loginSchema>;

// D-3: no course line, no "Chạy cục bộ" chip.
const FEATURES = ["Trích dẫn từng ý", "Phân quyền theo phòng ban"];

export function LoginPage() {
  const { status, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { pushToast } = useToast();
  const [showPassword, setShowPassword] = useState(false);
  const from = (location.state as { from?: string } | null)?.from ?? "/chat";

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<LoginForm>({ resolver: zodResolver(loginSchema) });

  useEffect(() => {
    if (status === "expired") {
      pushToast({ tone: "warning", title: "Phiên đăng nhập đã hết hạn", message: "Đăng nhập lại để tiếp tục." });
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
      setError("root", { message: loginErrorMessage(error) });
    }
  });

  return (
    <main className="min-h-[100dvh] bg-canvas text-ink lg:grid lg:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)]">
      <section className="login-panel relative hidden flex-col justify-between overflow-hidden px-12 py-12 text-white lg:flex">
        <Brand />
        <div className="relative max-w-md">
          <h1 className="fade-up text-4xl font-semibold leading-tight tracking-normal">
            Hỏi tài liệu nội bộ, nhận câu trả lời có nguồn.
          </h1>
          <p className="fade-up mt-4 text-[15px] leading-7 text-white/65 [animation-delay:80ms]">
            Mỗi câu trả lời chỉ dùng tài liệu bạn được phép xem và luôn kèm trích dẫn tới đúng trang.
          </p>
          <ul className="fade-up mt-6 flex flex-wrap gap-2 [animation-delay:160ms]">
            {FEATURES.map((feature) => (
              <li key={feature} className="rounded-full border border-white/20 px-3 py-1 text-xs text-white/85">
                {feature}
              </li>
            ))}
          </ul>
        </div>
        <div aria-hidden="true" />
      </section>

      <section
        className="flex min-h-[100dvh] items-center justify-center px-6 py-10 lg:min-h-0"
        aria-labelledby="login-title"
      >
        <div className="fade-up w-full max-w-[380px] [animation-delay:120ms]">
          <div className="mb-8 lg:hidden">
            <Brand compact />
          </div>
          <h2 id="login-title" className="text-2xl font-semibold text-ink">
            Đăng nhập
          </h2>
          <p className="mt-1 text-sm text-muted">Dùng tài khoản do quản trị viên cấp.</p>

          <form className="mt-6 space-y-[18px]" onSubmit={onSubmit} noValidate>
            <FieldWrapper id="email" label="Email" error={errors.email?.message}>
              <TextInput id="email" type="email" autoComplete="email" className="min-h-11" {...register("email")} />
            </FieldWrapper>
            <FieldWrapper id="password" label="Mật khẩu" error={errors.password?.message}>
              <div className="relative">
                <TextInput
                  id="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  className="min-h-11 pr-11"
                  {...register("password")}
                />
                <button
                  type="button"
                  className="absolute right-1.5 top-1.5 flex h-8 w-8 items-center justify-center rounded-token text-muted transition hover:bg-canvas hover:text-ink"
                  onClick={() => setShowPassword((current) => !current)}
                  aria-label={showPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
                  aria-pressed={showPassword}
                >
                  {showPassword ? (
                    <EyeOff className="h-4 w-4" aria-hidden="true" />
                  ) : (
                    <Eye className="h-4 w-4" aria-hidden="true" />
                  )}
                </button>
              </div>
            </FieldWrapper>
            {errors.root?.message ? (
              <p
                className="rounded-token border border-danger/20 bg-danger/5 px-3 py-2 text-sm font-medium text-danger"
                role="alert"
              >
                {errors.root.message}
              </p>
            ) : null}
            <Button className="min-h-11 w-full" type="submit" loading={isSubmitting}>
              {isSubmitting ? "Đang đăng nhập…" : "Đăng nhập"}
            </Button>
          </form>
          <p className="mt-4 text-xs text-muted">Quên mật khẩu? Liên hệ quản trị viên để được cấp lại.</p>
        </div>
      </section>
    </main>
  );
}

function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <div className="relative flex items-center gap-3">
      <div
        className={
          compact
            ? "flex h-8 w-8 items-center justify-center rounded-token bg-accent text-accent-contrast"
            : "flex h-8 w-8 items-center justify-center rounded-token bg-[rgb(45_212_191)] text-[rgb(6_43_39)]"
        }
      >
        <Box className="h-4 w-4" aria-hidden="true" />
      </div>
      <span className="text-sm font-semibold">{appConfig.appName}</span>
    </div>
  );
}

function loginErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === "INVALID_CREDENTIALS") {
      return "Email hoặc mật khẩu không đúng.";
    }
    if (error.code === "USER_INACTIVE") {
      return "Tài khoản đã bị vô hiệu hóa. Liên hệ quản trị viên.";
    }
    if (error.status === 429) {
      return "Đăng nhập sai quá nhiều lần. Thử lại sau ít phút.";
    }
  }
  return safeErrorMessage(error);
}
