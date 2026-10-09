"use client";

import { useState } from "react";

import type { ProductImage } from "@/lib/catalog-api";

type ProductGalleryProps = {
  images: ProductImage[];
  productName: string;
};

function GalleryPlaceholder() {
  return (
    <div className="flex size-full flex-col items-center justify-center gap-4 bg-surface-muted/65 px-6 text-center text-muted-foreground">
      <span className="flex size-20 items-center justify-center rounded-xl bg-surface/80">
        <svg
          aria-hidden="true"
          viewBox="0 0 48 48"
          fill="none"
          className="size-11"
        >
          <path
            d="M8 15.5 24 7l16 8.5v17L24 41 8 32.5v-17Z"
            stroke="currentColor"
            strokeWidth="1.7"
            strokeLinejoin="round"
          />
          <path
            d="m8.5 15.5 15.5 9 15.5-9M24 24.5V41"
            stroke="currentColor"
            strokeWidth="1.7"
            strokeLinejoin="round"
          />
        </svg>
      </span>
      <p className="text-sm font-semibold">تصویری برای این محصول ثبت نشده است</p>
    </div>
  );
}

export function ProductGallery({ images, productName }: ProductGalleryProps) {
  const primaryIndex = Math.max(
    0,
    images.findIndex((image) => image.is_primary),
  );
  const [activeIndex, setActiveIndex] = useState(primaryIndex);
  const activeImage = images[activeIndex];

  if (!activeImage) {
    return (
      <section
        aria-label="تصاویر محصول"
        className="overflow-hidden rounded-xl border border-border/80 bg-surface"
      >
        <div className="aspect-square">
          <GalleryPlaceholder />
        </div>
      </section>
    );
  }

  const showPrevious = () => {
    setActiveIndex((index) => (index === 0 ? images.length - 1 : index - 1));
  };

  const showNext = () => {
    setActiveIndex((index) => (index === images.length - 1 ? 0 : index + 1));
  };

  const imageAlt =
    activeImage.alt_text ||
    `${productName}، تصویر ${(activeIndex + 1).toLocaleString("fa-IR")}`;

  return (
    <section aria-label="گالری تصاویر محصول" className="min-w-0">
      <div className="relative overflow-hidden rounded-xl border border-border/80 bg-surface">
        <div className="aspect-square bg-surface">
          {/* The media origin remains deployment-owned, so native images avoid a speculative allowlist. */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            key={activeImage.id}
            src={activeImage.image}
            alt={imageAlt}
            className="size-full object-contain p-4 sm:p-6"
            loading={activeIndex === primaryIndex ? "eager" : "lazy"}
          />
        </div>

        {images.length > 1 ? (
          <div className="pointer-events-none absolute inset-x-3 top-1/2 flex -translate-y-1/2 justify-between">
            <button
              type="button"
              onClick={showPrevious}
              className="pointer-events-auto grid size-11 place-items-center rounded-lg border border-border/90 bg-surface/95 text-xl text-foreground shadow-card transition-colors hover:bg-primary hover:text-primary-foreground"
              aria-label="تصویر قبلی"
            >
              <span aria-hidden="true">→</span>
            </button>
            <button
              type="button"
              onClick={showNext}
              className="pointer-events-auto grid size-11 place-items-center rounded-lg border border-border/90 bg-surface/95 text-xl text-foreground shadow-card transition-colors hover:bg-primary hover:text-primary-foreground"
              aria-label="تصویر بعدی"
            >
              <span aria-hidden="true">←</span>
            </button>
          </div>
        ) : null}
      </div>

      <p className="sr-only" aria-live="polite">
        تصویر {(activeIndex + 1).toLocaleString("fa-IR")} از{" "}
        {images.length.toLocaleString("fa-IR")}
      </p>

      {images.length > 1 ? (
        <div
          role="group"
          className="mt-4 overflow-x-auto pb-1"
          aria-label="انتخاب تصویر محصول"
        >
          <div className="flex w-max gap-2.5">
            {images.map((image, index) => {
              const thumbnailAlt =
                image.alt_text ||
                `تصویر ${(index + 1).toLocaleString("fa-IR")}`;

              return (
                <button
                  key={image.id}
                  type="button"
                  onClick={() => setActiveIndex(index)}
                  aria-label={`نمایش ${thumbnailAlt}`}
                  aria-pressed={index === activeIndex}
                  className={`size-16 shrink-0 overflow-hidden rounded-lg border-2 bg-surface transition-[border-color,opacity] sm:size-20 ${
                    index === activeIndex
                      ? "border-primary"
                      : "border-transparent opacity-65 hover:border-border hover:opacity-100"
                  }`}
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={image.image}
                    alt=""
                    className="size-full object-contain p-1"
                    loading="lazy"
                  />
                </button>
              );
            })}
          </div>
        </div>
      ) : null}
    </section>
  );
}
