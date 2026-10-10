import Link from "next/link";

import type { CustomerProfile } from "@/lib/auth-contract";

type AccountSidebarProps = {
  customer: CustomerProfile;
  active: "profile" | "addresses" | "orders";
};

const items = [
  { key: "profile", href: "/account", label: "اطلاعات حساب" },
  { key: "orders", href: "/account/orders", label: "سفارش‌های من" },
  { key: "addresses", href: "/account/addresses", label: "آدرس‌های من" },
] as const;

export function AccountSidebar({ customer, active }: AccountSidebarProps) {
  const displayName =
    [customer.first_name, customer.last_name].filter(Boolean).join(" ") ||
    "مشتری فروشگاه";

  return (
    <aside
      className="rounded-xl bg-primary-soft/45 p-4 lg:sticky lg:top-28"
      aria-label="بخش‌های حساب کاربری"
    >
      <div className="border-b border-primary/10 px-2 pb-4">
        <p className="truncate font-black text-foreground">{displayName}</p>
        <p className="mt-1 truncate text-xs text-muted-foreground" dir="ltr">
          {customer.email}
        </p>
      </div>
      <nav className="mt-3" aria-label="ناوبری حساب">
        <ul className="space-y-1.5">
          {items.map((item) => {
            const current = item.key === active;
            return (
              <li key={item.key}>
                <Link
                  href={item.href}
                  aria-current={current ? "page" : undefined}
                  className={`flex min-h-11 items-center gap-3 rounded-lg px-3 text-sm font-bold transition-colors ${
                    current
                      ? "bg-surface text-primary shadow-[0_1px_2px_rgb(var(--shadow-color)/0.05)]"
                      : "text-foreground hover:bg-surface/70 hover:text-primary"
                  }`}
                >
                  <span
                    aria-hidden="true"
                    className={`grid size-7 place-items-center rounded-md ${
                      current ? "bg-primary-soft" : "bg-surface/70"
                    }`}
                  >
                    {item.key === "profile" ? "●" : item.key === "orders" ? "□" : "⌖"}
                  </span>
                  {item.label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </aside>
  );
}
