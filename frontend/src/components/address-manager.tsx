"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useRef, useState } from "react";

import {
  ADDRESS_LIMITS,
  type AddressInput,
  type CustomerAddress,
  isCustomerAddress,
  isCustomerAddressList,
} from "@/lib/address-contract";

type FieldErrors = Record<string, string>;

async function readResponseError(response: Response) {
  try {
    const payload = (await response.json()) as {
      error?: unknown;
      fieldErrors?: unknown;
    };
    return {
      error:
        typeof payload.error === "string"
          ? payload.error
          : "انجام درخواست آدرس ممکن نشد.",
      fieldErrors:
        payload.fieldErrors &&
        typeof payload.fieldErrors === "object" &&
        !Array.isArray(payload.fieldErrors)
          ? (payload.fieldErrors as FieldErrors)
          : {},
    };
  } catch {
    return { error: "انجام درخواست آدرس ممکن نشد.", fieldErrors: {} };
  }
}

class AddressSessionExpired extends Error {}

async function fetchAddressList() {
  const response = await fetch("/api/account/addresses", { cache: "no-store" });
  if (response.status === 401) throw new AddressSessionExpired();
  if (!response.ok) {
    const result = await readResponseError(response);
    throw new Error(result.error);
  }
  const payload: unknown = await response.json();
  if (!isCustomerAddressList(payload)) {
    throw new Error("پاسخ فهرست آدرس‌ها معتبر نبود.");
  }
  return payload;
}

function addressInput(form: HTMLFormElement): AddressInput {
  const data = new FormData(form);
  return {
    title: String(data.get("title") ?? ""),
    recipient_first_name: String(data.get("recipient_first_name") ?? ""),
    recipient_last_name: String(data.get("recipient_last_name") ?? ""),
    recipient_phone_number: String(data.get("recipient_phone_number") ?? ""),
    province: String(data.get("province") ?? ""),
    city: String(data.get("city") ?? ""),
    address: String(data.get("address") ?? ""),
    postal_code: String(data.get("postal_code") ?? ""),
  };
}

type AddressFormProps = {
  address?: CustomerAddress;
  onCancel: () => void;
  onSaved: (address: CustomerAddress, message: string) => void;
};

function AddressForm({ address, onCancel, onSaved }: AddressFormProps) {
  const router = useRouter();
  const lock = useRef(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (lock.current) return;
    lock.current = true;
    setPending(true);
    setError("");
    setFieldErrors({});

    try {
      const response = await fetch(
        address ? `/api/account/addresses/${address.id}` : "/api/account/addresses",
        {
          method: address ? "PATCH" : "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(addressInput(event.currentTarget)),
        },
      );
      if (response.status === 401) {
        router.push("/login");
        router.refresh();
        return;
      }
      if (!response.ok) {
        const result = await readResponseError(response);
        setError(result.error);
        setFieldErrors(result.fieldErrors);
        return;
      }
      const savedAddress: unknown = await response.json();
      if (!isCustomerAddress(savedAddress)) {
        setError("پاسخ ذخیرهٔ آدرس معتبر نبود. صفحه را تازه کنید.");
        return;
      }
      onSaved(
        savedAddress,
        address ? "آدرس با موفقیت ویرایش شد." : "آدرس جدید با موفقیت ثبت شد.",
      );
    } catch {
      setError("ارتباط با سرویس آدرس‌ها برقرار نشد. دوباره تلاش کنید.");
    } finally {
      lock.current = false;
      setPending(false);
    }
  };

  return (
    <form
      onSubmit={submit}
      className="rounded-[1.25rem] border border-gold/40 bg-background p-5 sm:p-7"
      aria-busy={pending}
    >
      <div className="flex items-start justify-between gap-4 border-b border-gold/30 pb-4">
        <div>
          <h2 className="text-lg font-black text-foreground">
            {address ? "ویرایش آدرس" : "افزودن آدرس جدید"}
          </h2>
          <p className="mt-1.5 text-xs leading-6 text-muted-foreground">
            مشخصات گیرنده و نشانی را مطابق اطلاعات تحویل وارد کنید.
          </p>
        </div>
        <button
          type="button"
          onClick={onCancel}
          disabled={pending}
          className="inline-flex min-h-11 items-center rounded-full px-3 text-sm font-bold text-muted-foreground hover:bg-surface-muted hover:text-foreground"
        >
          انصراف
        </button>
      </div>

      <div className="mt-6 grid gap-5 sm:grid-cols-2">
        <AddressField
          name="title"
          label="عنوان آدرس (اختیاری)"
          defaultValue={address?.title ?? ""}
          maxLength={ADDRESS_LIMITS.title}
          autoComplete="off"
          placeholder="مثلاً خانه یا محل کار"
          error={fieldErrors.title}
        />
        <div className="hidden sm:block" aria-hidden="true" />
        <AddressField
          name="recipient_first_name"
          label="نام گیرنده"
          defaultValue={address?.recipient_first_name ?? ""}
          maxLength={ADDRESS_LIMITS.name}
          autoComplete="given-name"
          required
          error={fieldErrors.recipient_first_name}
        />
        <AddressField
          name="recipient_last_name"
          label="نام خانوادگی گیرنده"
          defaultValue={address?.recipient_last_name ?? ""}
          maxLength={ADDRESS_LIMITS.name}
          autoComplete="family-name"
          required
          error={fieldErrors.recipient_last_name}
        />
        <AddressField
          name="recipient_phone_number"
          label="شماره تماس گیرنده"
          defaultValue={address?.recipient_phone_number ?? ""}
          maxLength={ADDRESS_LIMITS.phone}
          autoComplete="tel"
          inputMode="tel"
          dir="ltr"
          pattern="\+[1-9][0-9]{0,14}"
          placeholder="+989121234567"
          hint="شماره را با کد کشور و علامت + وارد کنید."
          required
          error={fieldErrors.recipient_phone_number}
        />
        <AddressField
          name="postal_code"
          label="کد پستی"
          defaultValue={address?.postal_code ?? ""}
          maxLength={ADDRESS_LIMITS.postalCode}
          autoComplete="postal-code"
          inputMode="numeric"
          dir="ltr"
          pattern="[0-9]{10}"
          placeholder="1234567890"
          hint="کد پستی ۱۰ رقمی را با اعداد انگلیسی وارد کنید."
          required
          error={fieldErrors.postal_code}
        />
        <AddressField
          name="province"
          label="استان"
          defaultValue={address?.province ?? ""}
          maxLength={ADDRESS_LIMITS.province}
          autoComplete="address-level1"
          required
          error={fieldErrors.province}
        />
        <AddressField
          name="city"
          label="شهر"
          defaultValue={address?.city ?? ""}
          maxLength={ADDRESS_LIMITS.city}
          autoComplete="address-level2"
          required
          error={fieldErrors.city}
        />
        <div className="sm:col-span-2">
          <label htmlFor="address" className="text-sm font-bold text-foreground">
            نشانی کامل
          </label>
          <textarea
            id="address"
            name="address"
            defaultValue={address?.address ?? ""}
            maxLength={ADDRESS_LIMITS.address}
            autoComplete="street-address"
            required
            rows={4}
            aria-invalid={Boolean(fieldErrors.address)}
            aria-describedby={fieldErrors.address ? "address-error" : undefined}
            className="mt-2 w-full resize-y rounded-xl border border-gold/40 bg-surface px-4 py-3 text-sm leading-7 outline-none transition focus:border-primary focus:ring-2 focus:ring-primary-soft"
          />
          {fieldErrors.address ? (
            <p id="address-error" className="mt-1.5 text-xs font-semibold text-destructive">
              {fieldErrors.address}
            </p>
          ) : null}
        </div>
      </div>

      <div className="mt-5 min-h-7" aria-live="polite">
        {error ? <p role="alert" className="text-sm font-semibold text-destructive">{error}</p> : null}
      </div>
      <div className="mt-3 flex flex-col-reverse gap-3 border-t border-gold/30 pt-5 sm:flex-row sm:justify-end">
        <button
          type="button"
          onClick={onCancel}
          disabled={pending}
          className="inline-flex min-h-12 items-center justify-center rounded-full border border-gold/45 px-5 text-sm font-bold text-foreground hover:bg-surface-muted"
        >
          انصراف
        </button>
        <button
          type="submit"
          disabled={pending}
          className="inline-flex min-h-12 items-center justify-center rounded-full bg-primary px-6 text-sm font-extrabold text-primary-foreground hover:bg-primary-hover disabled:cursor-wait disabled:opacity-65"
        >
          {pending ? "در حال ذخیره…" : address ? "ذخیرهٔ ویرایش" : "ثبت آدرس"}
        </button>
      </div>
    </form>
  );
}

type AddressFieldProps = {
  name: string;
  label: string;
  defaultValue: string;
  maxLength: number;
  autoComplete: string;
  error?: string;
  hint?: string;
  placeholder?: string;
  required?: boolean;
  pattern?: string;
  inputMode?: "tel" | "numeric";
  dir?: "ltr";
};

function AddressField({ name, label, error, hint, ...inputProps }: AddressFieldProps) {
  const descriptionId = error ? `${name}-error` : hint ? `${name}-hint` : undefined;
  return (
    <div>
      <label htmlFor={name} className="text-sm font-bold text-foreground">{label}</label>
      <input
        id={name}
        name={name}
        aria-invalid={Boolean(error)}
        aria-describedby={descriptionId}
        className="mt-2 min-h-12 w-full rounded-xl border border-gold/40 bg-surface px-4 text-sm outline-none transition placeholder:text-muted-foreground/65 focus:border-primary focus:ring-2 focus:ring-primary-soft"
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

export function AddressManager() {
  const router = useRouter();
  const [addresses, setAddresses] = useState<CustomerAddress[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [editing, setEditing] = useState<CustomerAddress | "new" | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<number | null>(null);
  const [pendingAction, setPendingAction] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    fetchAddressList()
      .then((items) => {
        if (active) setAddresses(items);
      })
      .catch((caught) => {
        if (!active) return;
        if (caught instanceof AddressSessionExpired) {
          router.push("/login");
          router.refresh();
          return;
        }
        setError(caught instanceof Error ? caught.message : "دریافت آدرس‌ها ممکن نشد.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [router]);

  const saved = (savedAddress: CustomerAddress, message: string) => {
    setAddresses((current) => {
      const exists = current.some((item) => item.id === savedAddress.id);
      return exists
        ? current.map((item) => (item.id === savedAddress.id ? savedAddress : item))
        : [...current, savedAddress];
    });
    setEditing(null);
    setError("");
    setSuccess(message);
    router.refresh();
  };

  const mutate = async (id: number, action: "delete" | "default") => {
    const key = `${action}-${id}`;
    if (pendingAction) return;
    setPendingAction(key);
    setError("");
    setSuccess("");
    try {
      const response = await fetch(
        action === "delete"
          ? `/api/account/addresses/${id}`
          : `/api/account/addresses/${id}/default`,
        { method: action === "delete" ? "DELETE" : "POST" },
      );
      if (response.status === 401) {
        router.push("/login");
        router.refresh();
        return;
      }
      if (!response.ok) {
        const result = await readResponseError(response);
        setError(result.error);
        return;
      }
      if (action === "delete") {
        const payload: unknown = await response.json();
        if (
          !payload ||
          typeof payload !== "object" ||
          Array.isArray(payload) ||
          !("deleted" in payload) ||
          payload.deleted !== true
        ) {
          throw new Error("پاسخ حذف آدرس معتبر نبود. صفحه را تازه کنید.");
        }
        setAddresses((current) => current.filter((item) => item.id !== id));
      } else {
        const selected: unknown = await response.json();
        if (!isCustomerAddress(selected)) {
          throw new Error("پاسخ تغییر آدرس پیش‌فرض معتبر نبود. صفحه را تازه کنید.");
        }
        setAddresses((current) =>
          current.map((item) =>
            item.id === selected.id
              ? selected
              : { ...item, is_default: false },
          ),
        );
      }
      setConfirmDelete(null);
      setSuccess(action === "delete" ? "آدرس حذف شد." : "آدرس پیش‌فرض تغییر کرد.");
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "انجام درخواست آدرس ممکن نشد.");
    } finally {
      setPendingAction(null);
    }
  };

  if (loading) {
    return (
      <div aria-busy="true" aria-label="در حال دریافت آدرس‌ها" className="space-y-4">
        <div className="h-44 animate-pulse rounded-[1.25rem] border border-gold/30 bg-background" />
        <div className="h-44 animate-pulse rounded-[1.25rem] border border-gold/30 bg-background" />
      </div>
    );
  }

  if (editing) {
    return (
      <AddressForm
        key={editing === "new" ? "new" : editing.id}
        address={editing === "new" ? undefined : editing}
        onCancel={() => setEditing(null)}
        onSaved={saved}
      />
    );
  }

  return (
    <section aria-labelledby="addresses-title">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-gold/30 pb-5">
        <div>
          <h2 id="addresses-title" className="text-xl font-black text-foreground sm:text-2xl">آدرس‌های من</h2>
          <p className="mt-2 text-sm leading-7 text-muted-foreground">نشانی‌ها و مشخصات گیرندگان سفارش را مدیریت کنید.</p>
        </div>
        <button
          type="button"
          onClick={() => {
            setEditing("new");
            setError("");
            setSuccess("");
          }}
          className="inline-flex min-h-11 items-center justify-center rounded-full bg-primary px-5 text-sm font-extrabold text-primary-foreground hover:bg-primary-hover"
        >
          افزودن آدرس
        </button>
      </div>

      <div className="min-h-12 py-3" aria-live="polite">
        {error ? <p role="alert" className="rounded-xl border border-destructive/20 bg-destructive-soft/60 px-4 py-3 text-sm font-semibold text-destructive">{error}</p> : null}
        {success ? <p role="status" className="rounded-xl border border-primary/15 bg-primary-soft/65 px-4 py-3 text-sm font-bold text-primary">{success}</p> : null}
      </div>

      {addresses.length === 0 ? (
        <div className="rounded-[1.25rem] border border-gold/35 bg-background px-5 py-12 text-center sm:px-8 sm:py-16">
          <div className="mx-auto grid size-14 place-items-center rounded-full border-2 border-gold bg-surface text-2xl text-primary" aria-hidden="true">⌖</div>
          <h3 className="mt-5 text-xl font-black text-foreground">هنوز آدرسی ثبت نشده است</h3>
          <p className="mx-auto mt-3 max-w-md text-sm leading-7 text-muted-foreground">اولین آدرسی که ثبت کنید، به‌صورت خودکار آدرس پیش‌فرض خواهد بود.</p>
          <button type="button" onClick={() => setEditing("new")} className="mt-6 inline-flex min-h-11 items-center rounded-full bg-primary px-5 text-sm font-bold text-primary-foreground hover:bg-primary-hover">ثبت اولین آدرس</button>
        </div>
      ) : (
        <div className="space-y-4">
          {addresses.map((item) => {
            const deleting = pendingAction === `delete-${item.id}`;
            const settingDefault = pendingAction === `default-${item.id}`;
            return (
              <article key={item.id} className="rounded-[1.25rem] border border-gold/35 bg-background p-4 sm:p-5">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="font-black text-foreground">{item.title || "آدرس بدون عنوان"}</h3>
                      {item.is_default ? <span className="rounded-full bg-primary-soft px-3 py-1 text-xs font-bold text-primary">پیش‌فرض</span> : null}
                    </div>
                    <p className="mt-3 text-sm font-bold text-foreground">{item.recipient_first_name} {item.recipient_last_name}</p>
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {!item.is_default ? (
                      <button type="button" onClick={() => mutate(item.id, "default")} disabled={Boolean(pendingAction)} className="inline-flex min-h-11 items-center rounded-full px-3 text-xs font-bold text-primary hover:bg-primary-soft disabled:opacity-50">
                        {settingDefault ? "در حال تغییر…" : "انتخاب به‌عنوان پیش‌فرض"}
                      </button>
                    ) : null}
                    <button type="button" onClick={() => setEditing(item)} disabled={Boolean(pendingAction)} className="inline-flex min-h-11 items-center rounded-full px-3 text-xs font-bold text-foreground hover:bg-surface-muted disabled:opacity-50">ویرایش</button>
                    <button type="button" onClick={() => setConfirmDelete(item.id)} disabled={Boolean(pendingAction)} className="inline-flex min-h-11 items-center rounded-full px-3 text-xs font-bold text-destructive hover:bg-destructive-soft disabled:opacity-50">حذف</button>
                  </div>
                </div>

                <dl className="mt-4 grid min-w-0 gap-x-6 gap-y-3 text-sm sm:grid-cols-2">
                  <div><dt className="text-xs text-muted-foreground">استان و شهر</dt><dd className="mt-1 text-foreground">{item.province}، {item.city}</dd></div>
                  <div><dt className="text-xs text-muted-foreground">شماره تماس</dt><dd className="mt-1 break-all text-foreground" dir="ltr">{item.recipient_phone_number}</dd></div>
                  <div className="sm:col-span-2"><dt className="text-xs text-muted-foreground">نشانی</dt><dd className="mt-1 whitespace-pre-wrap break-words leading-7 text-foreground">{item.address}</dd></div>
                  <div><dt className="text-xs text-muted-foreground">کد پستی</dt><dd className="mt-1 tabular-nums text-foreground" dir="ltr">{item.postal_code}</dd></div>
                </dl>

                {confirmDelete === item.id ? (
                  <div role="alertdialog" aria-modal="false" aria-labelledby={`delete-title-${item.id}`} className="mt-5 rounded-xl border border-destructive/20 bg-destructive-soft/55 p-4">
                    <p id={`delete-title-${item.id}`} className="text-sm font-bold text-foreground">از حذف این آدرس مطمئن هستید؟</p>
                    {item.is_default ? <p className="mt-1 text-xs leading-6 text-muted-foreground">با حذف آدرس پیش‌فرض، آدرس دیگری خودکار جایگزین نمی‌شود.</p> : null}
                    <div className="mt-3 flex flex-wrap gap-2">
                      <button type="button" onClick={() => mutate(item.id, "delete")} disabled={deleting} className="inline-flex min-h-11 items-center rounded-full bg-destructive px-4 text-xs font-bold text-white disabled:opacity-60">{deleting ? "در حال حذف…" : "بله، حذف شود"}</button>
                      <button type="button" onClick={() => setConfirmDelete(null)} disabled={deleting} className="inline-flex min-h-11 items-center rounded-full border border-gold/40 bg-surface px-4 text-xs font-bold text-foreground">انصراف</button>
                    </div>
                  </div>
                ) : null}
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
