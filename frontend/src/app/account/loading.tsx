import { Container } from "@/components/container";

export default function AccountLoading() {
  return (
    <Container className="py-7 sm:py-10 lg:py-14" aria-busy="true" aria-label="در حال دریافت حساب کاربری">
      <div className="h-28 animate-pulse rounded-xl bg-surface-muted/70" />
      <div className="mt-8 grid gap-7 lg:grid-cols-[15rem_minmax(0,1fr)] lg:gap-10">
        <div className="h-40 animate-pulse rounded-xl bg-primary-soft/45" />
        <div className="h-96 animate-pulse rounded-xl bg-surface-muted/70" />
      </div>
    </Container>
  );
}
