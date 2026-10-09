import { Container } from "@/components/container";

export default function CartLoading() {
  return (
    <Container className="py-7 sm:py-10 lg:py-14">
      <p className="sr-only" role="status">
        در حال دریافت سبد خرید
      </p>
      <div aria-hidden="true">
        <div className="border-b border-border/75 pb-6">
          <div className="h-4 w-20 rounded bg-primary-soft motion-safe:animate-pulse" />
          <div className="mt-4 h-10 w-40 rounded bg-surface-muted motion-safe:animate-pulse" />
          <div className="mt-4 h-5 w-full max-w-md rounded bg-surface-muted motion-safe:animate-pulse" />
        </div>
        <div className="mt-9 grid gap-8 lg:grid-cols-[minmax(0,1fr)_20rem]">
          <div className="space-y-5 border-y border-border/75 py-5">
            {Array.from({ length: 2 }, (_, index) => (
              <div key={index} className="flex gap-5">
                <div className="size-24 shrink-0 rounded-xl bg-surface-muted motion-safe:animate-pulse sm:size-32" />
                <div className="flex-1 space-y-4 py-2">
                  <div className="h-6 w-4/5 rounded bg-surface-muted motion-safe:animate-pulse" />
                  <div className="h-5 w-2/5 rounded bg-surface-muted motion-safe:animate-pulse" />
                  <div className="h-11 w-32 rounded-lg bg-surface-muted motion-safe:animate-pulse" />
                </div>
              </div>
            ))}
          </div>
          <div className="h-72 rounded-xl border border-border bg-surface p-5">
            <div className="h-7 w-28 rounded bg-surface-muted motion-safe:animate-pulse" />
            <div className="mt-6 h-20 border-y border-border/70 bg-primary-soft/45 motion-safe:animate-pulse" />
            <div className="mt-6 h-12 rounded-lg bg-primary-soft motion-safe:animate-pulse" />
          </div>
        </div>
      </div>
    </Container>
  );
}
