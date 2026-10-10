import { Container } from "@/components/container";

export default function ProductsLoading() {
  return (
    <Container className="py-6 sm:py-9 lg:py-12">
      <div className="naghsh-pattern rounded-[1.5rem] px-6 py-12 sm:py-16">
        <div className="mx-auto h-4 w-32 rounded bg-gold/45 motion-safe:animate-pulse" />
        <div className="mx-auto mt-4 h-11 w-56 rounded bg-white/20 motion-safe:animate-pulse" />
        <div className="mx-auto mt-5 h-5 w-full max-w-md rounded bg-white/15 motion-safe:animate-pulse" />
      </div>

      <div
        aria-hidden="true"
        className="mx-auto mt-6 max-w-4xl rounded-[1.5rem] border border-gold/40 bg-surface p-2 shadow-card sm:mt-8 sm:p-2.5"
      >
        <div className="flex gap-2">
          <div className="h-12 flex-1 rounded-lg bg-surface-muted motion-safe:animate-pulse" />
          <div className="h-12 w-24 rounded-lg bg-primary-soft motion-safe:animate-pulse sm:w-28" />
        </div>
      </div>

      <p className="sr-only" role="status">
        در حال دریافت محصولات
      </p>
      <div
        aria-hidden="true"
        className="mt-7 grid min-w-0 gap-7 lg:grid-cols-[17rem_minmax(0,1fr)] lg:items-start xl:gap-8"
      >
        <div className="hidden h-72 rounded-[1.5rem] border border-gold/40 bg-surface p-4 shadow-card lg:block">
          <div className="h-6 w-24 rounded bg-surface-muted motion-safe:animate-pulse" />
          <div className="mt-5 space-y-3 border-t border-border/70 pt-4">
            {Array.from({ length: 4 }, (_, index) => (
              <div key={index} className="h-11 rounded-lg bg-surface-muted motion-safe:animate-pulse" />
            ))}
          </div>
        </div>

        <div className="min-w-0">
          <div className="flex min-h-16 items-center justify-between gap-3 rounded-[1.25rem] border border-gold/35 bg-surface px-3 py-3">
            <div className="h-11 w-28 rounded-lg bg-surface-muted motion-safe:animate-pulse" />
            <div className="h-11 w-44 max-w-[55%] rounded-lg bg-surface-muted motion-safe:animate-pulse" />
          </div>
          <div className="mt-7 grid min-w-0 grid-cols-1 gap-5 min-[480px]:grid-cols-2 sm:gap-6 xl:grid-cols-3">
            {Array.from({ length: 6 }, (_, index) => (
              <div
                key={index}
                className="overflow-hidden rounded-[1.25rem] border border-gold/35 bg-surface shadow-card"
              >
                <div className="aspect-square bg-surface-muted motion-safe:animate-pulse sm:aspect-[5/4]" />
                <div className="space-y-3 p-3 sm:p-5">
                  <div className="h-4 w-20 rounded bg-surface-muted motion-safe:animate-pulse" />
                  <div className="h-6 w-4/5 rounded bg-surface-muted motion-safe:animate-pulse" />
                  <div className="h-6 w-2/3 rounded bg-surface-muted motion-safe:animate-pulse" />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </Container>
  );
}
