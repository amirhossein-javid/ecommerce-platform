import { Container } from "@/components/container";

export default function HomeLoading() {
  return (
    <div aria-busy="true" aria-label="در حال آماده‌سازی ویترین نقش‌جهان">
      <div className="naghsh-pattern">
        <Container className="grid min-h-[34rem] gap-12 py-14 sm:py-20 lg:grid-cols-[1.05fr_0.95fr] lg:items-center">
          <div>
            <div className="h-9 w-40 rounded-full bg-white/12 motion-safe:animate-pulse" />
            <div className="mt-7 h-24 max-w-xl rounded-2xl bg-white/12 motion-safe:animate-pulse" />
            <div className="mt-5 h-16 max-w-xl rounded-xl bg-white/8 motion-safe:animate-pulse" />
            <div className="mt-8 h-13 w-72 rounded-full bg-gold/25 motion-safe:animate-pulse" />
          </div>
          <div className="mx-auto aspect-square w-full max-w-md rounded-[42%] border-8 border-gold/20 bg-white/8 motion-safe:animate-pulse" />
        </Container>
      </div>
      <div className="h-28 border-b border-gold/20 bg-surface" />
      <Container className="py-16 sm:py-20">
        <div className="mx-auto h-5 w-32 rounded bg-primary-soft motion-safe:animate-pulse" />
        <div className="mx-auto mt-5 h-12 max-w-lg rounded-xl bg-surface-muted/70 motion-safe:animate-pulse" />
        <div className="mt-10 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
          {Array.from({ length: 5 }, (_, index) => <div key={index} className="h-48 rounded-[1.25rem] bg-surface motion-safe:animate-pulse" />)}
        </div>
      </Container>
      <p className="sr-only" role="status">در حال دریافت دسته‌بندی‌ها و محصولات</p>
    </div>
  );
}
