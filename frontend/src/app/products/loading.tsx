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
        className="mt-7 rounded-2xl border border-border bg-surface p-4 shadow-card sm:mt-9 sm:p-5 lg:p-6"
      >
        <div className="flex flex-col gap-3 sm:flex-row">
          <div className="h-12 flex-1 rounded-lg bg-surface-muted motion-safe:animate-pulse" />
          <div className="h-12 w-full rounded-lg bg-primary-soft motion-safe:animate-pulse sm:w-28" />
        </div>
        <div className="mt-5 hidden grid-cols-[1fr_1fr_7rem] gap-4 border-t border-border pt-5 sm:grid">
          <div className="h-12 rounded-lg bg-surface-muted motion-safe:animate-pulse" />
          <div className="h-12 rounded-lg bg-surface-muted motion-safe:animate-pulse" />
          <div className="h-12 rounded-lg bg-primary-soft motion-safe:animate-pulse" />
        </div>
        <div className="mt-4 h-11 border-t border-border pt-4 sm:hidden">
          <div className="h-5 w-40 rounded bg-surface-muted motion-safe:animate-pulse" />
        </div>
      </div>

      <div
        aria-hidden="true"
        className="mt-6 h-6 w-32 rounded bg-surface-muted motion-safe:animate-pulse"
      />

      <p className="sr-only" role="status">
        در حال دریافت محصولات
      </p>
      <div
        aria-hidden="true"
        className="mt-7 grid grid-cols-1 gap-x-6 gap-y-8 sm:mt-9 sm:grid-cols-2 lg:grid-cols-3 lg:gap-x-7 lg:gap-y-10"
      >
        {Array.from({ length: 6 }, (_, index) => (
          <div
            key={index}
            className="overflow-hidden rounded-xl border border-border bg-surface shadow-card"
          >
            <div className="aspect-[5/4] bg-surface-muted motion-safe:animate-pulse" />
            <div className="space-y-4 p-6">
              <div className="h-4 w-20 rounded bg-surface-muted motion-safe:animate-pulse" />
              <div className="h-7 w-4/5 rounded bg-surface-muted motion-safe:animate-pulse" />
              <div className="mt-8 h-7 w-32 rounded bg-surface-muted motion-safe:animate-pulse" />
            </div>
          </div>
        ))}
      </div>
    </Container>
  );
}
