import { Container } from "@/components/container";

export default function AccountLoading() {
  return (
    <Container className="py-6 sm:py-9 lg:py-12" aria-busy="true" aria-label="در حال دریافت حساب کاربری">
      <div className="naghsh-pattern h-44 animate-pulse rounded-[1.5rem]" />
      <div className="mt-8 grid gap-7 lg:grid-cols-[15rem_minmax(0,1fr)] lg:gap-10">
        <div className="h-52 animate-pulse rounded-[1.5rem] border border-gold/35 bg-surface" />
        <div className="h-96 animate-pulse rounded-[1.5rem] border border-gold/35 bg-surface" />
      </div>
    </Container>
  );
}
