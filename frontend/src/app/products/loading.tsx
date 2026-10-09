import { Container } from "@/components/container";

export default function ProductsLoading() {
  return (
    <Container className="py-7 sm:py-10 lg:py-14">
      <div className="border-b border-border pb-6 sm:pb-8">
        <div className="h-4 w-32 rounded bg-surface-muted motion-safe:animate-pulse" />
        <div className="mt-4 h-11 w-40 rounded bg-surface-muted motion-safe:animate-pulse" />
        <div className="mt-5 h-5 w-full max-w-md rounded bg-surface-muted motion-safe:animate-pulse" />
      </div>

      <div
        aria-hidden="true"
        className="mt-6 rounded-xl bg-surface-muted/60 p-2 sm:mt-8 sm:p-2.5"
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
        <div className="hidden h-72 rounded-xl border border-border/75 bg-surface p-4 lg:block">
          <div className="h-6 w-24 rounded bg-surface-muted motion-safe:animate-pulse" />
          <div className="mt-5 space-y-3 border-t border-border/70 pt-4">
            {Array.from({ length: 4 }, (_, index) => (
              <div key={index} className="h-11 rounded-lg bg-surface-muted motion-safe:animate-pulse" />
            ))}
          </div>
        </div>

        <div className="min-w-0">
          <div className="flex min-h-16 items-center justify-between gap-3 border-y border-border/75 py-3">
            <div className="h-11 w-28 rounded-lg bg-surface-muted motion-safe:animate-pulse" />
            <div className="h-11 w-44 max-w-[55%] rounded-lg bg-surface-muted motion-safe:animate-pulse" />
          </div>
          <div className="mt-7 grid min-w-0 grid-cols-1 gap-x-3 gap-y-8 min-[360px]:grid-cols-2 sm:gap-x-5 sm:gap-y-10 xl:grid-cols-3 xl:gap-x-6">
            {Array.from({ length: 6 }, (_, index) => (
              <div
                key={index}
                className="overflow-hidden rounded-xl border border-border/70 bg-surface shadow-card"
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
