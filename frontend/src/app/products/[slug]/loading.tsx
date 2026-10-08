import { Container } from "@/components/container";

export default function ProductDetailLoading() {
  return (
    <Container className="py-6 sm:py-9 lg:py-12">
      <p className="sr-only" role="status">در حال دریافت اطلاعات محصول</p>
      <div aria-hidden="true">
        <div className="h-5 w-64 max-w-full rounded bg-surface-muted motion-safe:animate-pulse" />
        <div className="mt-7 grid min-w-0 gap-8 lg:grid-cols-[minmax(0,1.08fr)_minmax(20rem,0.92fr)] lg:gap-12 xl:gap-16">
          <div>
            <div className="aspect-square rounded-2xl border border-border bg-surface-muted shadow-card motion-safe:animate-pulse" />
            <div className="mt-4 flex gap-3">
              <div className="size-20 rounded-lg bg-surface-muted motion-safe:animate-pulse sm:size-24" />
              <div className="size-20 rounded-lg bg-surface-muted motion-safe:animate-pulse sm:size-24" />
            </div>
          </div>
          <div className="space-y-5 lg:pt-2">
            <div className="h-4 w-24 rounded bg-surface-muted motion-safe:animate-pulse" />
            <div className="h-11 w-full rounded bg-surface-muted motion-safe:animate-pulse" />
            <div className="h-11 w-4/5 rounded bg-surface-muted motion-safe:animate-pulse" />
            <div className="mt-7 h-16 border-y border-border bg-surface-muted/65 motion-safe:animate-pulse" />
            <div className="mt-7 h-28 rounded-2xl bg-primary-soft/65 motion-safe:animate-pulse" />
          </div>
        </div>
        <div className="mt-12 max-w-4xl border-t border-border pt-9 sm:mt-16">
          <div className="h-8 w-48 rounded bg-surface-muted motion-safe:animate-pulse" />
          <div className="mt-6 h-5 w-full rounded bg-surface-muted motion-safe:animate-pulse" />
          <div className="mt-3 h-5 w-5/6 rounded bg-surface-muted motion-safe:animate-pulse" />
        </div>
      </div>
    </Container>
  );
}
