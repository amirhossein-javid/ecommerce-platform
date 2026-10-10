"use client";

import { useState } from "react";

const testimonials = [
  {
    quote: "آینه خاتم‌کاری رو برای اتاق پذیرایی سفارش دادم؛ کیفیت کار و بسته‌بندی فوق‌العاده بود. واقعاً حس یک اثر هنری اصیل رو داره.",
    name: "سارا احمدی",
    city: "تهران",
  },
  {
    quote: "ست فیروزه‌کوبی رو به عنوان هدیه ازدواج خریدم، عروس و داماد عاشقش شدن. جنس فیروزه‌ها هم واقعاً اصیل و درجه یک بود.",
    name: "رضا کریمی",
    city: "شیراز",
  },
  {
    quote: "فرش دستبافی که سفارش دادم دقیقاً همون چیزی بود که توی عکس‌ها دیدم؛ رنگ‌ها زنده و بافت فوق‌العاده متراکم و باکیفیت.",
    name: "مریم صالحی",
    city: "اصفهان",
  },
] as const;

export function TestimonialCarousel() {
  const [activeIndex, setActiveIndex] = useState(1);
  const active = testimonials[activeIndex];

  return (
    <div className="mx-auto mt-10 max-w-3xl">
      <figure className="min-h-72 rounded-[1.5rem] border border-gold/40 bg-surface px-6 py-9 text-center shadow-card sm:min-h-80 sm:px-12 sm:py-12">
        <div className="text-lg tracking-[0.2em] text-gold" aria-label="امتیاز ۵ از ۵">★★★★★</div>
        <blockquote className="mx-auto mt-6 max-w-2xl text-base font-medium leading-9 text-foreground sm:text-lg sm:leading-10">«{active.quote}»</blockquote>
        <figcaption className="mt-6">
          <strong className="block text-sm font-black text-primary sm:text-base">{active.name}</strong>
          <span className="mt-1 block text-xs text-muted-foreground">{active.city}</span>
        </figcaption>
      </figure>
      <div className="mt-6 flex items-center justify-center gap-2" role="group" aria-label="انتخاب نظر مشتری">
        {testimonials.map((testimonial, index) => (
          <button
            key={testimonial.name}
            type="button"
            onClick={() => setActiveIndex(index)}
            aria-label={`نمایش نظر ${testimonial.name}`}
            aria-pressed={activeIndex === index}
            className={`h-2.5 rounded-full transition-[width,background-color] ${activeIndex === index ? "w-7 bg-primary" : "w-2.5 bg-gold/35 hover:bg-gold"}`}
          />
        ))}
      </div>
    </div>
  );
}
