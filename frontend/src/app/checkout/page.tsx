import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";

import { CheckoutView } from "@/components/checkout-view";
import { Container } from "@/components/container";
import { getCustomerSession } from "@/lib/auth-session";
import { getCheckoutPageData } from "@/lib/checkout-api";
import { StorefrontPageHeader } from "@/components/storefront-page-header";

export const metadata: Metadata = {
  title: "ثبت سفارش | نقش‌جهان",
  description: "انتخاب آدرس و مرور نهایی سفارش",
};

function CheckoutUnavailable({ missingProfile = false }: { missingProfile?: boolean }) {
  return (
    <Container className="py-10 sm:py-16">
      <section role="alert" className="mx-auto max-w-2xl rounded-[1.5rem] border border-destructive/20 bg-destructive-soft/45 px-5 py-12 text-center sm:px-8">
        <h1 className="text-2xl font-black text-foreground">{missingProfile ? "پروفایل مشتری برای این حساب وجود ندارد" : "دریافت اطلاعات ثبت سفارش ممکن نشد"}</h1>
        <p className="mt-3 leading-8 text-muted-foreground">{missingProfile ? "برای ثبت سفارش باید با یک حساب مشتری وارد شوید." : "ارتباط با سرویس فروشگاه برقرار نشد. کمی بعد دوباره تلاش کنید."}</p>
        <Link href={missingProfile ? "/login" : "/checkout"} className="mt-6 inline-flex min-h-11 items-center rounded-full bg-primary px-5 text-sm font-bold text-primary-foreground hover:bg-primary-hover">{missingProfile ? "ورود با حساب مشتری" : "تلاش دوباره"}</Link>
      </section>
    </Container>
  );
}

export default async function CheckoutPage() {
  const session = await getCustomerSession();
  if (session.state === "guest" || session.state === "invalid") redirect("/login");
  if (session.state === "missing-profile") return <CheckoutUnavailable missingProfile />;
  if (session.state === "upstream-error") return <CheckoutUnavailable />;

  let data;
  try {
    data = await getCheckoutPageData();
  } catch {
    return <CheckoutUnavailable />;
  }

  return (
    <Container className="py-6 sm:py-9 lg:py-12">
      <StorefrontPageHeader eyebrow="تکمیل خرید" title="ثبت سفارش" description="آدرس دریافت و کالاهای سبد را پیش از ثبت نهایی بررسی کنید." />
      <CheckoutView cart={data.cart} addresses={data.addresses} />
    </Container>
  );
}
