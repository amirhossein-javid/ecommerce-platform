import { Container } from "@/components/container";

export default function CartLoading() {
  return (
    <Container className="py-6 sm:py-9 lg:py-12">
      <p className="sr-only" role="status">
        در حال دریافت سبد خرید
      </p>
      <div aria-hidden="true">
        <div className="naghsh-pattern rounded-[1.5rem] px-6 py-11">
          <div className="mx-auto h-4 w-20 rounded bg-gold/45 motion-safe:animate-pulse" />
          <div className="mx-auto mt-4 h-10 w-40 rounded bg-white/20 motion-safe:animate-pulse" />
          <div className="mx-auto mt-4 h-5 w-full max-w-md rounded bg-white/15 motion-safe:animate-pulse" />
        </div>
        <div className="mt-9 grid gap-8 lg:grid-cols-[minmax(0,1fr)_20rem]">
          <div className="space-y-4">
            {Array.from({ length: 2 }, (_, index) => (
              <div key={index} className="flex gap-5 rounded-[1.25rem] border border-gold/35 bg-surface p-4 shadow-card">
                <div className="size-24 shrink-0 rounded-xl bg-surface-muted motion-safe:animate-pulse sm:size-32" />
                <div className="flex-1 space-y-4 py-2">
                  <div className="h-6 w-4/5 rounded bg-surface-muted motion-safe:animate-pulse" />
                  <div className="h-5 w-2/5 rounded bg-surface-muted motion-safe:animate-pulse" />
                  <div className="h-11 w-32 rounded-lg bg-surface-muted motion-safe:animate-pulse" />
                </div>
              </div>
            ))}
          </div>
          <div className="h-72 rounded-[1.5rem] border border-gold/40 bg-surface p-5 shadow-card">
            <div className="h-7 w-28 rounded bg-surface-muted motion-safe:animate-pulse" />
            <div className="mt-6 h-20 border-y border-border/70 bg-primary-soft/45 motion-safe:animate-pulse" />
            <div className="mt-6 h-12 rounded-lg bg-primary-soft motion-safe:animate-pulse" />
          </div>
        </div>
      </div>
    </Container>
  );
}
