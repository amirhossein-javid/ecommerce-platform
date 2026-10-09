"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useRef, useState } from "react";

type AuthFormProps =
  | { mode: "login"; registered?: boolean }
  | { mode: "register"; registered?: never };

type FieldErrors = Record<string, string>;

async function readError(response: Response) {
  try {
    const payload = (await response.json()) as {
      error?: unknown;
      fieldErrors?: unknown;
    };
    return {
      error:
        typeof payload.error === "string"
          ? payload.error
          : "انجام درخواست ممکن نشد. دوباره تلاش کنید.",
      fieldErrors:
        payload.fieldErrors &&
        typeof payload.fieldErrors === "object" &&
        !Array.isArray(payload.fieldErrors)
          ? (payload.fieldErrors as FieldErrors)
          : {},
    };
  } catch {
    return { error: "انجام درخواست ممکن نشد. دوباره تلاش کنید.", fieldErrors: {} };
  }
}

function PasswordField({
  error,
  autoComplete,
}: {
  error?: string;
  autoComplete: "current-password" | "new-password";
}) {
  const [visible, setVisible] = useState(false);

  return (
    <div>
      <label htmlFor="password" className="text-sm font-bold text-foreground">
        رمز عبور
      </label>
      <div className="relative mt-2">
        <input
          id="password"
          name="password"
          type={visible ? "text" : "password"}
          autoComplete={autoComplete}
          required
          maxLength={1024}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? "password-error" : undefined}
          className="min-h-12 w-full rounded-lg border border-border bg-surface px-3 ps-4 pe-20 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-primary-soft"
        />
        <button
          type="button"
          onClick={() => setVisible((current) => !current)}
          className="absolute inset-y-0 end-1 inline-flex min-w-16 items-center justify-center rounded-md px-2 text-xs font-bold text-primary hover:bg-primary-soft"
          aria-pressed={visible}
        >
          {visible ? "پنهان" : "نمایش"}
        </button>
      </div>
      {error ? (
        <p id="password-error" className="mt-1.5 text-xs font-semibold text-destructive">
          {error}
        </p>
      ) : null}
    </div>
  );
}

export function AuthForm(props: AuthFormProps) {
  const router = useRouter();
  const lock = useRef(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const isLogin = props.mode === "login";

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (lock.current) return;
    lock.current = true;
    setPending(true);
    setError("");
    setFieldErrors({});

    const data = new FormData(event.currentTarget);
    const payload: Record<string, string> = {
      email: String(data.get("email") ?? ""),
      password: String(data.get("password") ?? ""),
    };
    if (!isLogin) {
      payload.first_name = String(data.get("first_name") ?? "");
      payload.last_name = String(data.get("last_name") ?? "");
      payload.phone_number = String(data.get("phone_number") ?? "");
    }

    try {
      const response = await fetch(
        isLogin ? "/api/auth/login" : "/api/auth/register",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        },
      );
      if (!response.ok) {
        const result = await readError(response);
        setError(result.error);
        setFieldErrors(result.fieldErrors);
        return;
      }

      if (isLogin) {
        const result: unknown = await response.json();
        const cartMerge =
          result &&
          typeof result === "object" &&
          !Array.isArray(result) &&
          "cartMerge" in result &&
          typeof result.cartMerge === "string"
            ? result.cartMerge
            : "none";
        if (["pending", "unavailable"].includes(cartMerge)) {
          router.push(`/cart?merge=${cartMerge}`);
        } else if (cartMerge === "merged") {
          router.push("/cart");
        } else {
          router.push("/");
        }
        router.refresh();
      } else {
        router.push("/login?registered=1");
      }
    } catch {
      setError("ارتباط با سرویس حساب کاربری برقرار نشد. دوباره تلاش کنید.");
    } finally {
      lock.current = false;
      setPending(false);
    }
  };

  return (
    <form onSubmit={submit} className="mt-8 space-y-5" aria-busy={pending}>
      {isLogin && props.registered ? (
        <p className="rounded-lg bg-success-soft px-4 py-3 text-sm font-bold text-success" role="status">
          حساب شما ساخته شد. اکنون وارد شوید.
        </p>
      ) : null}

      {!isLogin ? (
        <div className="grid gap-5 sm:grid-cols-2">
          <TextField name="first_name" label="نام" autoComplete="given-name" maxLength={150} error={fieldErrors.first_name} />
          <TextField name="last_name" label="نام خانوادگی" autoComplete="family-name" maxLength={150} error={fieldErrors.last_name} />
        </div>
      ) : null}

      <TextField name="email" label="ایمیل" type="email" inputMode="email" autoComplete="email" dir="ltr" maxLength={254} error={fieldErrors.email} />
      {!isLogin ? (
        <TextField
          name="phone_number"
          label="شماره تلفن"
          type="tel"
          inputMode="tel"
          autoComplete="tel"
          dir="ltr"
          maxLength={16}
          placeholder="+989121234567"
          hint="با کد کشور و علامت + وارد کنید."
          error={fieldErrors.phone_number}
        />
      ) : null}
      <PasswordField
        error={fieldErrors.password}
        autoComplete={isLogin ? "current-password" : "new-password"}
      />

      <div className="min-h-7" aria-live="polite">
        {error ? <p role="alert" className="text-sm font-semibold text-destructive">{error}</p> : null}
      </div>

      <button
        type="submit"
        disabled={pending}
        className="inline-flex min-h-12 w-full items-center justify-center rounded-lg bg-primary px-5 text-sm font-extrabold text-primary-foreground transition-colors hover:bg-primary-hover disabled:cursor-wait disabled:opacity-65"
      >
        {pending ? "در حال ارسال…" : isLogin ? "ورود به حساب" : "ساخت حساب"}
      </button>

      <p className="text-center text-sm text-muted-foreground">
        {isLogin ? "هنوز حساب ندارید؟" : "قبلاً ثبت‌نام کرده‌اید؟"}{" "}
        <Link
          href={isLogin ? "/register" : "/login"}
          className="inline-flex min-h-11 items-center font-bold text-primary underline-offset-4 hover:underline"
        >
          {isLogin ? "ثبت‌نام" : "ورود"}
        </Link>
      </p>
    </form>
  );
}

type TextFieldProps = {
  name: string;
  label: string;
  error?: string;
  hint?: string;
  type?: string;
  inputMode?: "email" | "tel";
  autoComplete?: string;
  dir?: "ltr";
  maxLength: number;
  placeholder?: string;
};

function TextField({ name, label, error, hint, ...inputProps }: TextFieldProps) {
  const descriptionId = error ? `${name}-error` : hint ? `${name}-hint` : undefined;
  return (
    <div>
      <label htmlFor={name} className="text-sm font-bold text-foreground">{label}</label>
      <input
        id={name}
        name={name}
        required
        aria-invalid={Boolean(error)}
        aria-describedby={descriptionId}
        className="mt-2 min-h-12 w-full rounded-lg border border-border bg-surface px-4 text-sm outline-none transition placeholder:text-muted-foreground/70 focus:border-primary focus:ring-2 focus:ring-primary-soft"
        {...inputProps}
      />
      {error ? (
        <p id={`${name}-error`} className="mt-1.5 text-xs font-semibold text-destructive">{error}</p>
      ) : hint ? (
        <p id={`${name}-hint`} className="mt-1.5 text-xs text-muted-foreground">{hint}</p>
      ) : null}
    </div>
  );
}
