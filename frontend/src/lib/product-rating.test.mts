import assert from "node:assert/strict";
import test from "node:test";

import {
  isProductRatingAggregate,
  productRatingPresentation,
} from "./product-rating.ts";

test("validates rated and unrated product aggregates", () => {
  assert.equal(
    isProductRatingAggregate({ average_rating: "4.5", review_count: 2 }),
    true,
  );
  assert.equal(
    isProductRatingAggregate({ average_rating: null, review_count: 0 }),
    true,
  );
  assert.equal(
    isProductRatingAggregate({ average_rating: "5.0", review_count: 0 }),
    false,
  );
});

test("renders clear Persian rated and unrated card labels", () => {
  assert.deepEqual(
    productRatingPresentation({ average_rating: null, review_count: 0 }),
    {
      label: "بدون امتیاز",
      ariaLabel: "این محصول هنوز امتیازی ندارد",
    },
  );
  const rated = productRatingPresentation({
    average_rating: "4.5",
    review_count: 3,
  });
  assert.match(rated.label, /۴٫۵/);
  assert.match(rated.label, /۳ نظر/);
  assert.match(rated.ariaLabel, /نظر تأییدشده/);
});
