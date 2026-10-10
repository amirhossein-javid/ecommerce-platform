import {
  productRatingPresentation,
  type ProductRatingAggregate,
} from "@/lib/product-rating";

export function ProductRating({ rating }: { rating: ProductRatingAggregate }) {
  const presentation = productRatingPresentation(rating);
  const isRated = rating.review_count > 0;

  return (
    <span
      aria-label={presentation.ariaLabel}
      className={`inline-flex min-w-0 items-center gap-1 text-[0.68rem] font-bold sm:text-xs ${isRated ? "text-foreground" : "text-muted-foreground"}`}
    >
      <span aria-hidden="true" className={isRated ? "text-gold" : "text-border"}>
        ★
      </span>
      <span className="truncate">{presentation.label}</span>
    </span>
  );
}
