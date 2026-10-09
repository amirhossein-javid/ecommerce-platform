import { Container } from "@/components/container";

export default function CheckoutLoading() {
  return (
    <Container className="py-7 sm:py-10 lg:py-14" aria-busy="true" aria-label="در حال دریافت اطلاعات ثبت سفارش">
      <div className="h-28 rounded-xl bg-surface-muted/70 motion-safe:animate-pulse" />
      <div className="mt-8 grid gap-8 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <div className="space-y-5">
          <div className="h-56 rounded-xl bg-surface-muted/70 motion-safe:animate-pulse" />
          <div className="h-72 rounded-xl bg-surface-muted/70 motion-safe:animate-pulse" />
        </div>
        <div className="h-80 rounded-xl border border-border bg-surface motion-safe:animate-pulse" />
      </div>
    </Container>
  );
}
