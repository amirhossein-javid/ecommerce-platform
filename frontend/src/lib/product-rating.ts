export type ProductRatingAggregate = {
  average_rating: string | null;
  review_count: number;
};

export function isProductRatingAggregate(
  value: Partial<ProductRatingAggregate>,
): value is ProductRatingAggregate {
  const validAverage =
    value.average_rating === null ||
    (typeof value.average_rating === "string" &&
      /^(?:[1-4]\.[0-9]|5\.0)$/.test(value.average_rating));
  return (
    validAverage &&
    Number.isSafeInteger(value.review_count) &&
    Number(value.review_count) >= 0 &&
    (value.review_count === 0) === (value.average_rating === null)
  );
}

export function productRatingPresentation(rating: ProductRatingAggregate) {
  if (rating.average_rating === null || rating.review_count === 0) {
    return {
      label: "بدون امتیاز",
      ariaLabel: "این محصول هنوز امتیازی ندارد",
    };
  }

  const average = Number(rating.average_rating).toLocaleString("fa-IR", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  });
  const count = rating.review_count.toLocaleString("fa-IR");
  return {
    label: `${average} (${count} نظر)`,
    ariaLabel: `امتیاز ${average} از ۵ بر پایهٔ ${count} نظر تأییدشده`,
  };
}
