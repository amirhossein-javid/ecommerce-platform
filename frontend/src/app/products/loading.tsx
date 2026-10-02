import { Container } from "@/components/container";

export default function ProductsLoading() {
  return (
    <Container className="py-8 sm:py-12 lg:py-16">
      <div className="mb-8 border-b border-border pb-7 sm:mb-10">
        <div className="h-5 w-16 rounded bg-surface-subtle" />
        <div className="mt-3 h-11 w-40 rounded bg-surface-subtle" />
      </div>

      <p className="sr-only" role="status">
        در حال دریافت محصولات
      </p>
      <div
        aria-hidden="true"
        className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
      >
        {Array.from({ length: 8 }, (_, index) => (
          <div
            key={index}
            className="overflow-hidden rounded-lg border border-border bg-surface"
          >
            <div className="aspect-[4/3] bg-surface-subtle" />
            <div className="space-y-4 p-5">
              <div className="h-4 w-20 rounded bg-surface-subtle" />
              <div className="h-6 w-4/5 rounded bg-surface-subtle" />
              <div className="mt-8 h-6 w-28 rounded bg-surface-subtle" />
            </div>
          </div>
        ))}
      </div>
    </Container>
  );
}
