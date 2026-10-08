import Link from "next/link";

import type { ProductListItem } from "@/lib/catalog-api";
import { formatToman } from "@/lib/format-price";

type ProductCardProps = {
  product: ProductListItem;
};

function ProductImagePlaceholder() {
  return (
    <div className="flex size-full flex-col items-center justify-center gap-3 bg-surface-muted text-muted-foreground">
      <span className="flex size-16 items-center justify-center rounded-xl border border-border bg-surface/70">
        <svg
          aria-hidden="true"
          viewBox="0 0 48 48"
          fill="none"
          className="size-9"
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
      <span className="text-sm font-semibold">تصویر محصول موجود نیست</span>
    </div>
  );
}

export function ProductCard({ product }: ProductCardProps) {
  const image = product.primary_image;

  return (
    <article className="group h-full min-w-0 rounded-xl">
      <Link
        href={`/products/${product.slug}`}
        className="flex h-full min-w-0 flex-col overflow-hidden rounded-xl border border-border/90 bg-surface shadow-card motion-safe:transition-[border-color,box-shadow,transform] motion-safe:duration-300 hover:border-primary/30 hover:shadow-card-hover motion-safe:hover:-translate-y-0.5"
      >
        <div className="relative aspect-[5/4] overflow-hidden bg-surface-muted">
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

        <div className="flex flex-1 flex-col p-5 sm:p-6">
          <div className="flex items-center justify-between gap-3 text-sm">
            <p className="font-medium text-muted-foreground">
              {product.category.name}
            </p>
            <span
              className={`inline-flex shrink-0 items-center gap-2 text-xs font-bold ${
                product.in_stock
                  ? "text-success"
                  : "text-destructive"
              }`}
            >
              <span
                aria-hidden="true"
                className={`size-2 rounded-full ${
                  product.in_stock ? "bg-success" : "bg-destructive"
                }`}
              />
              {product.in_stock ? "موجود" : "ناموجود"}
            </span>
          </div>

          <h2 className="mt-3 line-clamp-2 min-h-14 text-lg font-extrabold leading-7 text-foreground transition-colors group-hover:text-primary sm:text-xl sm:leading-8">
            {product.name}
          </h2>

          <p className="mt-6 break-words border-t border-border/80 pt-4 text-[1.35rem] font-black leading-8 tabular-nums text-primary">
            <bdi>{formatToman(product.price)}</bdi>
          </p>
        </div>
      </Link>
    </article>
  );
}
