import type { Metadata } from "next";
import Link from "next/link";
import type { ReactNode } from "react";

import { Container } from "@/components/container";
import { ProductCard } from "@/components/product-card";
import { TestimonialCarousel } from "@/components/testimonial-carousel";
import { type Category, getCategories, getProducts, type ProductListItem, type ProductPage } from "@/lib/catalog-api";
import { DEFAULT_PRODUCT_ORDERING } from "@/lib/catalog-query";

export const metadata: Metadata = {
  title: "نقش‌جهان | ویترین فروشگاه",
  description: "مرور محصولات و دسته‌بندی‌های فعال نقش‌جهان با قیمت و موجودی به‌روز.",
};

const homeCatalogQuery = { page: 1, search: "", category: "", ordering: DEFAULT_PRODUCT_ORDERING } as const;

function ArrowIcon() {
  return <svg aria-hidden="true" viewBox="0 0 20 20" fill="none" className="size-4"><path d="M16 10H4m5-5-5 5 5 5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" /></svg>;
}

function SearchIcon() {
  return <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" className="size-5"><circle cx="11" cy="11" r="6" stroke="currentColor" strokeWidth="1.8" /><path d="m16 16 4 4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" /></svg>;
}

function OrnamentLabel({ children }: { children: ReactNode }) {
  return <p className="flex items-center justify-center gap-3 text-xs font-black text-primary sm:text-sm"><span className="size-2 rotate-45 bg-gold" aria-hidden="true" />{children}<span className="size-2 rotate-45 bg-gold" aria-hidden="true" /></p>;
}

function Hero({ product }: { product?: ProductListItem }) {
  return (
    <section className="naghsh-pattern relative isolate overflow-hidden text-white" aria-labelledby="home-title">
      <div className="absolute inset-0 -z-10 bg-lapis-dark/78" />
      <Container className="grid min-h-[34rem] gap-12 py-14 sm:py-20 lg:grid-cols-[1.05fr_0.95fr] lg:items-center lg:gap-20 lg:py-24">
        <div className="max-w-2xl">
          <p className="inline-flex items-center gap-2 rounded-full border border-gold/55 bg-lapis-dark/45 px-4 py-2 text-xs font-black text-gold-light">ویترین آنلاین نقش‌جهان <ArrowIcon /></p>
          <h1 id="home-title" className="mt-6 text-[2.4rem] font-black leading-[1.35] tracking-[-0.035em] text-balance sm:text-5xl lg:text-[3.6rem]">
            هر انتخاب، جایی در <span className="text-gold-light">خانهٔ شما</span>
          </h1>
          <p className="mt-5 max-w-xl text-sm leading-8 text-white/78 sm:text-lg sm:leading-9">هر قطعه در فروشگاه نقش‌جهان، روایتگر هنر، صبر و عشق اصفهان است؛ از میناکاری روی مس تا خاتم‌کاری ظریف، برای آوردن گوشه‌ای از زیبایی هنر ایرانی به خانهٔ شما.</p>
          <div className="mt-8 flex flex-col gap-3 min-[430px]:flex-row">
            <Link href="/products" className="inline-flex min-h-13 items-center justify-center gap-2 rounded-full bg-gold-light px-7 text-sm font-black text-lapis-dark shadow-[0_14px_30px_-14px_rgb(230_201_138/0.65)] transition hover:bg-gold hover:shadow-lg">مشاهدهٔ محصولات <ArrowIcon /></Link>
            <Link href="/#categories" className="inline-flex min-h-13 items-center justify-center rounded-full border border-gold/70 bg-lapis-dark/35 px-7 text-sm font-black text-white transition hover:bg-lapis-dark/70">مرور دسته‌بندی‌ها</Link>
          </div>
        </div>

        <div className="relative mx-auto w-full max-w-md lg:max-w-lg">
          <div className="absolute -inset-4 rounded-[42%] border border-dashed border-gold/45 motion-safe:animate-[spin_40s_linear_infinite]" aria-hidden="true" />
          <Link href={product ? `/products/${product.slug}` : "/products"} aria-label={product ? `مشاهدهٔ ${product.name}` : "مشاهدهٔ محصولات"} className="relative block aspect-square overflow-hidden rounded-[42%] border-8 border-gold/35 bg-lapis shadow-[0_25px_70px_-25px_rgb(0_0_0/0.85)] transition-transform motion-safe:hover:scale-[1.015]">
            {product?.primary_image ? (
              // Media URLs are resolved by the existing Django catalog adapter.
              // eslint-disable-next-line @next/next/no-img-element
              <img src={product.primary_image.image} alt={product.primary_image.alt_text || product.name} className="size-full object-cover" />
            ) : (
              <div className="naghsh-pattern grid size-full place-items-center"><span className="grid size-28 place-items-center rounded-full border border-gold/60 bg-lapis-dark/75 text-center text-sm font-black leading-7 text-gold-light">کاتالوگ<br />نقش‌جهان</span></div>
            )}
            {product ? <span className="absolute inset-x-6 bottom-6 rounded-full bg-lapis-dark/85 px-4 py-2 text-center text-xs font-bold text-white backdrop-blur-sm">{product.name}</span> : null}
          </Link>
        </div>
      </Container>
    </section>
  );
}

const assurances = [
  { title: "ساخته‌شده با عشق", text: "دست هنرمندان اصفهانی" },
  { title: "گواهی اصالت", text: "برای هر محصول" },
  { title: "ارسال ایمن", text: "بسته‌بندی ویژهٔ سفالینه و شیشه" },
  { title: "مشاورهٔ خرید", text: "راهنمایی برای انتخاب هدیه" },
] as const;

function AssuranceIcon({ index }: { index: number }) {
  const icons = [
    <path key="heart" d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10Z" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />,
    <path key="seal" d="m12 3 2 2.2 3-.4.8 2.9 2.7 1.4-1.2 2.8 1.2 2.8-2.7 1.4-.8 2.9-3-.4L12 21l-2-2.2-3 .4-.8-2.9-2.7-1.4 1.2-2.8-1.2-2.8 2.7-1.4L7 4.8l3 .4L12 3Zm0 6v6m-3-3h6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />,
    <path key="truck" d="M3 6h11v10H3V6Zm11 4h4l3 3v3h-7v-6ZM7 19a2 2 0 1 0 0-4 2 2 0 0 0 0 4Zm10 0a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />,
    <path key="guide" d="M5 7h14M5 12h14M5 17h14" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />,
  ];
  return <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" className="size-6">{icons[index]}</svg>;
}

function AssuranceStrip() {
  return (
    <section className="border-b border-gold/35 bg-surface" aria-label="امکانات فروشگاه">
      <Container>
        <div className="grid grid-cols-2 gap-px overflow-hidden bg-gold/30 lg:grid-cols-4">
          {assurances.map((item, index) => <div key={item.title} className="flex min-h-28 items-center gap-3 bg-surface px-3 py-5 sm:justify-center sm:px-5 lg:min-h-32">
            <span className="grid size-11 shrink-0 place-items-center rounded-full border border-gold/70 text-primary"><AssuranceIcon index={index} /></span>
            <span><strong className="block text-xs font-black text-foreground sm:text-sm">{item.title}</strong><span className="mt-1 block text-[0.65rem] leading-5 text-muted-foreground sm:text-xs">{item.text}</span></span>
          </div>)}
        </div>
      </Container>
    </section>
  );
}

function CatalogError({ label }: { label: string }) {
  return <div role="alert" className="rounded-[1.25rem] border border-destructive/20 bg-destructive-soft/55 px-6 py-10 text-center"><h3 className="text-lg font-black">دریافت {label} ممکن نشد</h3><p className="mt-2 text-sm leading-7 text-muted-foreground">ارتباط با کاتالوگ برقرار نشد. کمی بعد دوباره تلاش کنید.</p><Link href="/" className="mt-5 inline-flex min-h-11 items-center rounded-full border border-primary/30 px-5 text-sm font-bold text-primary hover:bg-primary-soft">تلاش دوباره</Link></div>;
}

function CategoryIcon({ index }: { index: number }) {
  const paths = [
    <path key="a" d="M7 7h10v10H7zM4 4h16v16H4z" stroke="currentColor" strokeWidth="1.6" />,
    <path key="b" d="M12 3v18M3 12h18M6 6c3 3 9 3 12 0M6 18c3-3 9-3 12 0" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />,
    <path key="c" d="m5 17 11-11 3 3-11 11H5v-3Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />,
    <path key="d" d="M12 4a8 8 0 1 0 0 16 8 8 0 0 0 0-16Zm0 5a3 3 0 1 0 0 6 3 3 0 0 0 0-6Z" stroke="currentColor" strokeWidth="1.6" />,
    <path key="e" d="m12 3 2.3 6.7L21 12l-6.7 2.3L12 21l-2.3-6.7L3 12l6.7-2.3L12 3Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />,
  ];
  return <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" className="size-7">{paths[index % paths.length]}</svg>;
}

function Categories({ categories }: { categories: Category[] }) {
  if (categories.length === 0) return <div className="rounded-[1.25rem] border border-gold/30 bg-surface px-6 py-12 text-center"><h3 className="font-black">هنوز دسته‌بندی فعالی ثبت نشده است</h3><p className="mt-2 text-sm text-muted-foreground">دسته‌بندی‌های فعال پس از ثبت در کاتالوگ اینجا نمایش داده می‌شوند.</p></div>;
  return <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5 lg:gap-5">{categories.slice(0, 5).map((category, index) => (
    <Link key={category.id} href={`/products?category=${encodeURIComponent(category.slug)}`} className="group flex min-h-48 flex-col items-center justify-center rounded-[1.25rem] border border-gold/35 bg-surface p-5 text-center shadow-[0_14px_34px_-28px_rgb(var(--shadow-color)/0.4)] transition motion-safe:hover:-translate-y-1 hover:border-gold/75 hover:shadow-card-hover">
      <span className="grid size-16 place-items-center rounded-full border-2 border-gold bg-background text-primary transition-colors group-hover:bg-primary group-hover:text-white"><CategoryIcon index={index} /></span>
      <h3 className="mt-5 line-clamp-2 text-sm font-black leading-6 sm:text-base">{category.name}</h3>
      {category.parent ? <p className="mt-1 text-xs text-muted-foreground">در {category.parent.name}</p> : <p className="mt-1 text-xs text-muted-foreground">مشاهدهٔ محصولات</p>}
    </Link>
  ))}</div>;
}

function ProductEmpty() {
  return <div className="rounded-[1.25rem] border border-gold/30 bg-background px-6 py-12 text-center"><h3 className="text-lg font-black">هنوز محصول فعالی برای نمایش نیست</h3><p className="mt-2 text-sm leading-7 text-muted-foreground">محصولات فعال پس از ثبت در کاتالوگ، در همین ویترین ظاهر می‌شوند.</p></div>;
}

function Heritage() {
  return (
    <section id="heritage" className="naghsh-pattern relative isolate scroll-mt-36 overflow-hidden py-16 text-white sm:py-20 lg:py-24" aria-labelledby="heritage-title">
      <div className="absolute inset-0 -z-10 bg-lapis-dark/82" />
      <Container>
        <p className="flex items-center justify-center gap-3 text-xs font-black text-gold-light sm:text-sm"><span className="size-2 rotate-45 bg-gold" aria-hidden="true" />میراث اصفهان<span className="size-2 rotate-45 bg-gold" aria-hidden="true" /></p>
        <h2 id="heritage-title" className="mx-auto mt-4 max-w-3xl text-center text-3xl font-black leading-[1.5] text-white sm:text-4xl">روایتی که از میدان نقش‌جهان آغاز می‌شود</h2>
        <p className="mx-auto mt-4 max-w-3xl text-center text-sm leading-8 text-white/72 sm:text-base">نام نقش‌جهان یادآور پیوند دیرپای اصفهان با رنگ، هندسه و هنرهای ایرانی است؛ از میناکاری و خاتم‌کاری تا قلم‌زنی و فیروزه‌کوبی.</p>
        <div className="mt-10 grid gap-4 lg:grid-cols-[1.05fr_0.95fr] lg:items-center">
          <article className="rounded-[1.5rem] border border-gold/35 bg-lapis-dark/75 p-7 backdrop-blur-sm sm:p-9 lg:py-12">
            <span className="text-sm font-black text-gold-light">زبان مشترک هنرهای اصفهان</span>
            <h3 className="mt-3 text-2xl font-black leading-10 text-white">رنگ، نقش و مهارتی که در جزئیات دیده می‌شود</h3>
            <p className="mt-4 text-sm leading-8 text-white/72">هر رشتهٔ هنری زبان خودش را دارد: نظم هندسی خاتم، آبی درخشان مینا، رد قلم روی فلز و ترکیب سنگ فیروزه با زمینهٔ مسی. نقش‌جهان این تنوع را در یک ویترین فارسی گرد هم می‌آورد.</p>
          </article>
          <div className="grid gap-4">
            <article className="rounded-[1.25rem] border border-gold/35 bg-lapis-dark/75 p-6 backdrop-blur-sm sm:p-7"><h3 className="text-lg font-black text-gold-light">برای خانه یا یک هدیهٔ معنادار</h3><p className="mt-3 text-sm leading-8 text-white/72">برای انتخاب دقیق‌تر، تصویر، قیمت، موجودی و توضیحات ثبت‌شده در صفحهٔ هر محصول را بررسی کنید.</p></article>
            <article className="rounded-[1.25rem] border border-gold/35 bg-lapis-dark/75 p-6 backdrop-blur-sm sm:p-7"><h3 className="text-lg font-black text-gold-light">آنچه می‌بینید، از کاتالوگ می‌آید</h3><p className="mt-3 text-sm leading-8 text-white/72">نام، تصویر و قیمت محصولات از دادهٔ واقعی فروشگاه نمایش داده می‌شود؛ بدون ساخت محصول یا ادعای تأییدنشده.</p></article>
          </div>
        </div>
      </Container>
    </section>
  );
}

function Testimonials() {
  return (
    <section className="bg-background py-16 sm:py-20 lg:py-24" aria-labelledby="testimonials-title">
      <Container>
        <OrnamentLabel>مشتریان می‌گویند</OrnamentLabel>
        <h2 id="testimonials-title" className="mt-4 text-center text-3xl font-black sm:text-4xl">روایت‌هایی از دل مشتریان</h2>
        <TestimonialCarousel />
      </Container>
    </section>
  );
}

export default async function Home() {
  let categories: Category[] | null = null;
  let products: ProductPage | null = null;
  const [categoryResult, productResult] = await Promise.allSettled([getCategories(), getProducts(homeCatalogQuery)]);
  if (categoryResult.status === "fulfilled") categories = categoryResult.value;
  if (productResult.status === "fulfilled") products = productResult.value;

  return <>
    <Hero product={products?.results[0]} />
    <AssuranceStrip />

    <section id="categories" className="scroll-mt-36 bg-background py-16 sm:py-20 lg:py-24" aria-labelledby="categories-title">
      <Container>
        <OrnamentLabel>دسته‌بندی‌ها</OrnamentLabel>
        <h2 id="categories-title" className="mt-4 text-center text-3xl font-black tracking-tight sm:text-4xl">راه کوتاه‌تر برای کشف محصولات</h2>
        <p className="mx-auto mt-4 max-w-2xl text-center text-sm leading-7 text-muted-foreground sm:text-base">دسته‌بندی‌های فعال فروشگاه را مرور کنید و مستقیم به محصولات مرتبط برسید.</p>
        <div className="mt-10">{categories === null ? <CatalogError label="دسته‌بندی‌ها" /> : <Categories categories={categories} />}</div>
      </Container>
    </section>

    <section id="products" className="scroll-mt-36 border-y border-gold/25 bg-surface py-16 sm:py-20 lg:py-24" aria-labelledby="products-title">
      <Container>
        <OrnamentLabel>محصولات فروشگاه</OrnamentLabel>
        <h2 id="products-title" className="mt-4 text-center text-3xl font-black tracking-tight sm:text-4xl">تازه‌های کاتالوگ نقش‌جهان</h2>
        <p className="mx-auto mt-4 max-w-2xl text-center text-sm leading-7 text-muted-foreground sm:text-base">محصولات فعال، با تصویر، موجودی و قیمت واقعی ثبت‌شده در فروشگاه.</p>

        <form action="/products" method="get" role="search" className="mx-auto mt-8 flex max-w-2xl items-center gap-2 overflow-hidden rounded-full border border-gold/55 bg-background p-1.5 shadow-card transition focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/15">
          <label htmlFor="home-search" className="sr-only">جست‌وجوی محصولات</label><span className="ms-3 text-primary"><SearchIcon /></span>
          <input id="home-search" name="search" type="search" maxLength={100} placeholder="در محصولات جست‌وجو کنید" className="catalog-search-field min-w-0 flex-1 border-0 bg-transparent px-2 text-sm outline-none placeholder:text-muted-foreground" />
          <button type="submit" className="min-h-11 shrink-0 rounded-full bg-primary px-5 text-sm font-black text-white hover:bg-primary-hover">جست‌وجو</button>
        </form>

        {categories && categories.length > 0 ? <nav className="mt-7 flex flex-wrap justify-center gap-2" aria-label="مرور محصول بر اساس دسته‌بندی"><Link href="/products" className="inline-flex min-h-10 items-center rounded-full bg-primary px-5 text-xs font-black text-white">همه</Link>{categories.slice(0, 5).map((category) => <Link key={category.id} href={`/products?category=${encodeURIComponent(category.slug)}`} className="inline-flex min-h-10 items-center rounded-full border border-gold/45 bg-surface px-5 text-xs font-bold text-foreground hover:border-gold hover:text-primary">{category.name}</Link>)}</nav> : null}

        <div className="mt-10">{products === null ? <CatalogError label="محصولات" /> : products.results.length === 0 ? <ProductEmpty /> : <div className="grid min-w-0 grid-cols-1 gap-5 min-[390px]:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">{products.results.slice(0, 8).map((product) => <ProductCard key={product.id} product={product} />)}</div>}</div>
        {products && products.results.length > 0 ? <div className="mt-10 text-center"><Link href="/products" className="inline-flex min-h-12 items-center justify-center gap-2 rounded-full border border-primary/35 px-7 text-sm font-black text-primary hover:bg-primary-soft">مشاهدهٔ همهٔ محصولات <ArrowIcon /></Link></div> : null}
      </Container>
    </section>
    <Heritage />
    <Testimonials />
  </>;
}
