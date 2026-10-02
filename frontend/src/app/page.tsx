import { Container } from "@/components/container";

export default function Home() {
  return (
    <Container className="py-10 sm:py-16 lg:py-24">
      <section
        className="overflow-hidden rounded-lg border border-border bg-surface shadow-[0_18px_60px_-40px_rgba(29,33,31,0.35)]"
        aria-labelledby="foundation-title"
      >
        <div className="grid gap-10 px-5 py-9 sm:px-8 sm:py-12 lg:grid-cols-[minmax(0,1fr)_22rem] lg:gap-14 lg:px-12 lg:py-16">
          <div className="max-w-2xl">
            <p className="mb-4 text-sm font-semibold text-primary">
              پایهٔ طراحی فروشگاه
            </p>
            <h1
              id="foundation-title"
              className="text-3xl font-bold leading-[1.45] tracking-tight text-foreground sm:text-4xl lg:text-5xl"
            >
              چارچوبی روشن برای یک تجربهٔ خرید فارسی
            </h1>
            <p className="mt-5 max-w-xl text-base leading-8 text-muted-foreground sm:text-lg sm:leading-9">
              این صفحه فقط ساختار بصری، تایپوگرافی و ریتم رابط را نمایش می‌دهد.
              محتوای واقعی فروشگاه و محصولات در مرحله‌های بعد اضافه می‌شوند.
            </p>
          </div>

          <div className="border-t border-border pt-8 lg:border-s lg:border-t-0 lg:ps-10 lg:pt-0">
            <h2 className="text-base font-bold text-foreground">در این مرحله</h2>
            <ul className="mt-5 space-y-4 text-sm leading-7 text-muted-foreground sm:text-base">
              <li className="flex gap-3">
                <span
                  aria-hidden="true"
                  className="mt-[0.7rem] size-1.5 shrink-0 rounded-full bg-primary"
                />
                <span>پوستهٔ واکنش‌گرا و ناوبری ساده</span>
              </li>
              <li className="flex gap-3">
                <span
                  aria-hidden="true"
                  className="mt-[0.7rem] size-1.5 shrink-0 rounded-full bg-primary"
                />
                <span>تایپوگرافی فارسی و چیدمان راست‌به‌چپ</span>
              </li>
              <li className="flex gap-3">
                <span
                  aria-hidden="true"
                  className="mt-[0.7rem] size-1.5 shrink-0 rounded-full bg-primary"
                />
                <span>پایه‌های بصری قابل توسعه برای ادامهٔ کار</span>
              </li>
            </ul>
          </div>
        </div>
      </section>
    </Container>
  );
}
