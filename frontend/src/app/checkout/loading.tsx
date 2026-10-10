import { Container } from "@/components/container";

export default function CheckoutLoading() {
  return (
    <Container className="py-6 sm:py-9 lg:py-12" aria-busy="true" aria-label="در حال دریافت اطلاعات ثبت سفارش">
      <div className="naghsh-pattern h-44 rounded-[1.5rem] motion-safe:animate-pulse" />
      <div className="mt-8 grid gap-8 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <div className="space-y-5">
          <div className="h-56 rounded-[1.5rem] border border-gold/35 bg-surface motion-safe:animate-pulse" />
          <div className="h-72 rounded-[1.5rem] border border-gold/35 bg-surface motion-safe:animate-pulse" />
        </div>
        <div className="h-80 rounded-[1.5rem] border border-gold/35 bg-surface motion-safe:animate-pulse" />
      </div>
    </Container>
  );
}
