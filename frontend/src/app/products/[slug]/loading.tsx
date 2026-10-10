import { Container } from "@/components/container";

export default function ProductDetailLoading() {
  return (
    <Container className="py-6 sm:py-9 lg:py-12">
      <p className="sr-only" role="status">
        در حال دریافت اطلاعات محصول
      </p>
      <div aria-hidden="true">
        <div className="h-5 w-64 max-w-full rounded bg-surface-muted motion-safe:animate-pulse" />
        <div className="mt-7 grid min-w-0 gap-8 lg:grid-cols-[minmax(0,0.88fr)_minmax(0,1.32fr)_minmax(15rem,0.8fr)] lg:gap-6 xl:grid-cols-[minmax(17rem,0.88fr)_minmax(26rem,1.35fr)_minmax(17rem,0.77fr)] xl:gap-8">
          <div className="space-y-4 lg:col-start-1 lg:row-start-1">
            <div className="h-10 w-24 rounded-lg bg-primary-soft motion-safe:animate-pulse" />
            <div className="h-9 w-full rounded bg-surface-muted motion-safe:animate-pulse" />
            <div className="h-9 w-4/5 rounded bg-surface-muted motion-safe:animate-pulse" />
          </div>

          <div className="lg:col-start-2 lg:row-span-2 lg:row-start-1">
            <div className="aspect-square rounded-xl border border-border bg-surface-muted motion-safe:animate-pulse" />
            <div className="mt-4 flex gap-2.5">
              <div className="size-16 rounded-lg bg-surface-muted motion-safe:animate-pulse sm:size-20" />
              <div className="size-16 rounded-lg bg-surface-muted motion-safe:animate-pulse sm:size-20" />
            </div>
          </div>

          <div className="space-y-4 border-t border-border/75 pt-6 lg:col-start-1 lg:row-start-2">
            <div className="h-6 w-32 rounded bg-surface-muted motion-safe:animate-pulse" />
            <div className="h-12 w-full rounded bg-surface-muted motion-safe:animate-pulse" />
            <div className="h-5 w-full rounded bg-surface-muted motion-safe:animate-pulse" />
            <div className="h-5 w-5/6 rounded bg-surface-muted motion-safe:animate-pulse" />
          </div>

          <div className="h-64 rounded-xl border border-border bg-surface p-5 lg:col-start-3 lg:row-span-2 lg:row-start-1">
            <div className="h-6 w-24 rounded bg-surface-muted motion-safe:animate-pulse" />
            <div className="mt-5 h-24 border-y border-border/70 bg-primary-soft/45 motion-safe:animate-pulse" />
            <div className="mt-5 h-12 rounded bg-surface-muted motion-safe:animate-pulse" />
          </div>
        </div>
      </div>
    </Container>
  );
}
