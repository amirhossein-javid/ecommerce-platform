import Link from "next/link";

import type { ProductListItem } from "@/lib/catalog-api";
import { formatToman } from "@/lib/format-price";

type ProductCardProps = {
  product: ProductListItem;
};

function ProductImagePlaceholder() {
  return (
    <div className="flex size-full flex-col items-center justify-center gap-2 bg-surface-muted px-2 text-center text-muted-foreground">
      <span className="flex size-12 items-center justify-center rounded-lg bg-surface/75 sm:size-16 sm:rounded-xl">
        <svg
          aria-hidden="true"
          viewBox="0 0 48 48"
          fill="none"
          className="size-7 sm:size-9"
        >
          <path
            d="M8 15.5 24 7l16 8.5v17L24 41 8 32.5v-17Z"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinejoin="round"
          />
          <path
            d="m8.5 15.5 15.5 9 15.5-9M24 24.5V41"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinejoin="round"
          />
        </svg>
      </span>
      <span className="text-xs font-semibold sm:text-sm">تصویر محصول موجود نیست</span>
    </div>
  );
}

export function ProductCard({ product }: ProductCardProps) {
  const image = product.primary_image;

  return (
    <article className="group h-full min-w-0">
      <Link
        href={`/products/${product.slug}`}
        className="flex h-full min-w-0 flex-col overflow-hidden rounded-xl border border-border/70 bg-surface shadow-card motion-safe:transition-[border-color,box-shadow,transform] motion-safe:duration-300 hover:border-primary/25 hover:shadow-card-hover motion-safe:hover:-translate-y-0.5"
      >
        <div className="relative aspect-square overflow-hidden bg-surface-muted sm:aspect-[5/4]">
          {image ? (
            // The public media origin is deployment-owned and not yet fixed, so a
            // native image avoids a speculative Next.js remote-image allowlist.
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={image.image}
              alt={image.alt_text || product.name}
              className="size-full object-cover motion-safe:transition-transform motion-safe:duration-500 motion-safe:group-hover:scale-[1.02]"
            />
          ) : (
            <ProductImagePlaceholder />
          )}
        </div>

        <div className="flex flex-1 flex-col p-3 sm:p-5">
          <div className="flex min-w-0 items-center justify-between gap-2 text-xs sm:text-sm">
            <p className="min-w-0 truncate font-medium text-muted-foreground">
              {product.category.name}
            </p>
            <span
              className={`inline-flex shrink-0 items-center gap-1.5 text-[0.68rem] font-bold sm:text-xs ${
                product.in_stock
                  ? "text-success"
                  : "text-destructive"
              }`}
            >
              <span
                aria-hidden="true"
                className={`size-1.5 rounded-full sm:size-2 ${
                  product.in_stock ? "bg-success" : "bg-destructive"
                }`}
              />
              {product.in_stock ? "موجود" : "ناموجود"}
            </span>
          </div>

          <h2 className="mt-2.5 line-clamp-2 min-h-12 text-sm font-extrabold leading-6 text-foreground transition-colors group-hover:text-primary sm:mt-3 sm:min-h-14 sm:text-lg sm:leading-7 xl:text-xl xl:leading-8">
            {product.name}
          </h2>

          <p className="mt-auto break-words pt-4 text-base font-black leading-7 tabular-nums text-primary sm:pt-5 sm:text-[1.2rem] sm:leading-8 xl:text-[1.3rem]">
            <bdi>{formatToman(product.price)}</bdi>
          </p>
        </div>
      </Link>
    </article>
  );
}
