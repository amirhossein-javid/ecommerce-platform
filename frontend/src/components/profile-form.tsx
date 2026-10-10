"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useRef, useState } from "react";

import {
  type CustomerProfile,
  isCustomerProfile,
} from "@/lib/auth-contract";

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
          : "ذخیرهٔ اطلاعات ممکن نشد.",
      fieldErrors:
        payload.fieldErrors &&
        typeof payload.fieldErrors === "object" &&
        !Array.isArray(payload.fieldErrors)
          ? (payload.fieldErrors as FieldErrors)
          : {},
    };
  } catch {
    return { error: "ذخیرهٔ اطلاعات ممکن نشد.", fieldErrors: {} };
  }
}

export function ProfileForm({ profile }: { profile: CustomerProfile }) {
  const router = useRouter();
  const lock = useRef(false);
  const [current, setCurrent] = useState(profile);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (lock.current) return;
    lock.current = true;
    setPending(true);
    setError("");
    setSuccess("");
    setFieldErrors({});

    const data = new FormData(event.currentTarget);
    const payload = {
      first_name: String(data.get("first_name") ?? ""),
      last_name: String(data.get("last_name") ?? ""),
      phone_number: String(data.get("phone_number") ?? ""),
    };

    try {
      const response = await fetch("/api/account/profile", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (response.status === 401) {
        router.push("/login");
        router.refresh();
        return;
      }
      if (!response.ok) {
        const result = await readError(response);
        setError(result.error);
        setFieldErrors(result.fieldErrors);
        return;
      }

      const updated: unknown = await response.json();
      if (!isCustomerProfile(updated)) {
        setError("پاسخ پروفایل معتبر نبود. صفحه را تازه کنید.");
        return;
      }
      setCurrent(updated);
      setSuccess("اطلاعات حساب با موفقیت ذخیره شد.");
      router.refresh();
    } catch {
      setError("ارتباط با سرویس حساب کاربری برقرار نشد. دوباره تلاش کنید.");
    } finally {
      lock.current = false;
      setPending(false);
    }
  };

  return (
    <form onSubmit={submit} className="mt-7" aria-busy={pending}>
      <div className="grid gap-5 sm:grid-cols-2">
        <ProfileField
          name="first_name"
          label="نام"
          defaultValue={current.first_name}
          autoComplete="given-name"
          maxLength={150}
          error={fieldErrors.first_name}
        />
        <ProfileField
          name="last_name"
          label="نام خانوادگی"
          defaultValue={current.last_name}
          autoComplete="family-name"
          maxLength={150}
          error={fieldErrors.last_name}
        />
        <ProfileField
          name="phone_number"
          label="شماره تلفن"
          defaultValue={current.phone_number}
          autoComplete="tel"
          inputMode="tel"
          dir="ltr"
          maxLength={16}
          placeholder="+989121234567"
          hint="شماره را با کد کشور و علامت + وارد کنید."
          error={fieldErrors.phone_number}
        />
        <div>
          <label htmlFor="profile-email" className="text-sm font-bold text-foreground">
            ایمیل
          </label>
          <input
            id="profile-email"
            value={current.email}
            readOnly
            dir="ltr"
            className="mt-2 min-h-12 w-full cursor-not-allowed rounded-xl border border-gold/30 bg-surface-muted/45 px-4 text-sm text-muted-foreground outline-none"
          />
          <p className="mt-1.5 text-xs text-muted-foreground">ایمیل حساب قابل ویرایش نیست.</p>
        </div>
      </div>

      <div className="mt-6 min-h-7" aria-live="polite">
        {error ? <p role="alert" className="rounded-xl border border-destructive/20 bg-destructive-soft px-4 py-3 text-sm font-semibold text-destructive">{error}</p> : null}
        {success ? <p role="status" className="rounded-xl border border-success/20 bg-success-soft px-4 py-3 text-sm font-bold text-success">{success}</p> : null}
      </div>

      <div className="mt-4 flex justify-end border-t border-gold/30 pt-5">
        <button
          type="submit"
          disabled={pending}
          className="inline-flex min-h-12 w-full items-center justify-center rounded-full bg-primary px-6 text-sm font-extrabold text-primary-foreground transition-colors hover:bg-primary-hover disabled:cursor-wait disabled:opacity-65 sm:w-auto"
        >
          {pending ? "در حال ذخیره…" : "ذخیرهٔ تغییرات"}
        </button>
      </div>
    </form>
  );
}

type ProfileFieldProps = {
  name: string;
  label: string;
  defaultValue: string;
  error?: string;
  hint?: string;
  autoComplete: string;
  inputMode?: "tel";
  dir?: "ltr";
  maxLength: number;
  placeholder?: string;
};

function ProfileField({
  name,
  label,
  error,
  hint,
  ...inputProps
}: ProfileFieldProps) {
  const descriptionId = error ? `${name}-error` : hint ? `${name}-hint` : undefined;
  return (
    <div>
      <label htmlFor={name} className="text-sm font-bold text-foreground">{label}</label>
      <input
        id={name}
        name={name}
        aria-invalid={Boolean(error)}
        aria-describedby={descriptionId}
        className="mt-2 min-h-12 w-full rounded-xl border border-gold/40 bg-background px-4 text-sm outline-none transition placeholder:text-muted-foreground/70 focus:border-primary focus:ring-2 focus:ring-primary-soft"
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
