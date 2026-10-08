import { Container } from "@/components/container";

export default function Home() {
  return (
    <Container className="py-8 sm:py-14 lg:py-20">
      <section
        className="relative overflow-hidden rounded-2xl border border-border bg-surface shadow-card"
        aria-labelledby="foundation-title"
      >
        <div className="absolute inset-y-0 start-0 w-1.5 bg-primary" aria-hidden="true" />
        <div className="grid gap-10 px-6 py-10 sm:px-9 sm:py-14 lg:grid-cols-[minmax(0,1fr)_22rem] lg:gap-16 lg:px-14 lg:py-20">
          <div className="max-w-2xl">
            <p className="mb-4 text-sm font-bold text-primary">
              پایهٔ طراحی فروشگاه
            </p>
            <h1
              id="foundation-title"
              className="text-3xl font-black leading-[1.45] tracking-tight text-foreground sm:text-4xl lg:text-5xl"
            >
              تجربه‌ای گرم و منسجم برای خرید فارسی
            </h1>
            <p className="mt-5 max-w-xl text-base leading-8 text-muted-foreground sm:text-lg sm:leading-9">
              این صفحه ساختار بصری و تایپوگرافی فروشگاه را معرفی می‌کند. فهرست
              محصولات با داده‌های واقعی در بخش محصولات در دسترس است.
            </p>
          </div>

          <div className="border-t border-border pt-8 lg:border-s lg:border-t-0 lg:ps-12 lg:pt-0">
            <h2 className="text-base font-extrabold text-primary">پایه‌های تجربه</h2>
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
                <span>نمایش داده و تصاویر واقعی کاتالوگ</span>
              </li>
            </ul>
          </div>
        </div>
      </section>
    </Container>
  );
}
