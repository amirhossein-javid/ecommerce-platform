import { Container } from "@/components/container";

export default function ProductsLoading() {
  return (
    <Container className="py-7 sm:py-10 lg:py-14">
      <div className="border-b border-border pb-6 sm:pb-8">
        <div className="h-4 w-32 rounded bg-surface-muted motion-safe:animate-pulse" />
        <div className="mt-4 h-11 w-40 rounded bg-surface-muted motion-safe:animate-pulse" />
        <div className="mt-5 h-5 w-full max-w-md rounded bg-surface-muted motion-safe:animate-pulse" />
      </div>

      <p className="sr-only" role="status">
        در حال دریافت محصولات
      </p>
      <div
        aria-hidden="true"
        className="mt-8 grid grid-cols-1 gap-x-6 gap-y-8 sm:mt-10 sm:grid-cols-2 lg:grid-cols-3 lg:gap-x-7 lg:gap-y-10"
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
