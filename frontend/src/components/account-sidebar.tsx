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
      className="overflow-hidden rounded-[1.5rem] border border-gold/40 bg-surface p-4 shadow-card lg:sticky lg:top-28"
      aria-label="بخش‌های حساب کاربری"
    >
      <div className="rounded-[1rem] bg-background px-3 py-4">
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
                  className={`flex min-h-11 items-center gap-3 rounded-xl px-3 text-sm font-bold transition-colors ${
                    current
                      ? "bg-primary text-primary-foreground shadow-sm"
                      : "text-foreground hover:bg-background hover:text-primary"
                  }`}
                >
                  <span
                    aria-hidden="true"
                    className={`grid size-7 place-items-center rounded-lg ${
                      current ? "bg-white/15" : "bg-background"
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
