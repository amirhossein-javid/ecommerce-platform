import type { ProductListItem } from "@/lib/catalog-api";
import { formatRial } from "@/lib/format-price";

type ProductCardProps = {
  product: ProductListItem;
};

function ProductImagePlaceholder() {
  return (
    <div className="flex size-full flex-col items-center justify-center gap-3 bg-surface-subtle text-muted-foreground">
      <svg
        aria-hidden="true"
        viewBox="0 0 48 48"
        fill="none"
        className="size-11"
      >
        <path
          d="M8 15.5 24 7l16 8.5v17L24 41 8 32.5v-17Z"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinejoin="round"
        />
        <path
          d="m8.5 15.5 15.5 9 15.5-9M24 24.5V41"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinejoin="round"
        />
      </svg>
      <span className="text-sm font-medium">بدون تصویر</span>
    </div>
  );
}

export function ProductCard({ product }: ProductCardProps) {
  const image = product.primary_image;

  return (
    <article className="group flex h-full min-w-0 flex-col overflow-hidden rounded-lg border border-border bg-surface shadow-[0_12px_36px_-30px_rgba(29,33,31,0.55)] transition-[border-color,box-shadow,transform] duration-200 hover:-translate-y-0.5 hover:border-primary/35 hover:shadow-[0_20px_48px_-32px_rgba(29,33,31,0.5)]">
      <div className="aspect-[4/3] overflow-hidden border-b border-border bg-surface-subtle">
        {image ? (
          // The public media origin is deployment-owned and not yet fixed, so a
          // native image avoids a speculative Next.js remote-image allowlist.
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={image.image}
            alt={image.alt_text || product.name}
            className="size-full object-cover transition-transform duration-300 group-hover:scale-[1.02]"
          />
        ) : (
          <ProductImagePlaceholder />
        )}
      </div>

      <div className="flex flex-1 flex-col p-4 sm:p-5">
        <div className="flex items-start justify-between gap-3">
          <p className="text-sm font-medium text-muted-foreground">
            {product.category.name}
          </p>
          <span
            className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-semibold ${
              product.in_stock
                ? "bg-success/10 text-success"
                : "bg-destructive/10 text-destructive"
            }`}
          >
            {product.in_stock ? "موجود" : "ناموجود"}
          </span>
        </div>

        <h2 className="mt-3 line-clamp-2 text-base font-bold leading-7 text-foreground sm:text-lg">
          {product.name}
        </h2>

        <p className="mt-auto pt-6 text-base font-extrabold tabular-nums text-foreground sm:text-lg">
          <bdi>{formatRial(product.price)}</bdi>
        </p>
      </div>
    </article>
  );
}
