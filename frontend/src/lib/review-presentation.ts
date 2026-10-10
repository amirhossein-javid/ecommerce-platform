import type {
  ProductReviewAggregate,
  ReviewStatus,
} from "./review-contract.ts";

export const REVIEW_STATUS_COPY: Record<
  ReviewStatus,
  { label: string; message: string; tone: "pending" | "approved" | "rejected" }
> = {
  PENDING: {
    label: "در انتظار بررسی",
    message: "نظر شما ثبت شده و پس از تأیید مدیر برای دیگران نمایش داده می‌شود.",
    tone: "pending",
  },
  APPROVED: {
    label: "تأییدشده",
    message: "نظر شما اکنون در فهرست عمومی این محصول دیده می‌شود.",
    tone: "approved",
  },
  REJECTED: {
    label: "تأیید نشد",
    message: "این نظر در فهرست عمومی نمایش داده نمی‌شود. برای ثبت نظر متفاوت، ابتدا آن را حذف کنید.",
    tone: "rejected",
  },
};

export function aggregateAfterApprovedDeletion(
  aggregate: ProductReviewAggregate,
  deletedRating: number,
): ProductReviewAggregate {
  const nextCount = Math.max(0, aggregate.review_count - 1);
  if (nextCount === 0 || aggregate.average_rating === null) {
    return { average_rating: null, review_count: 0 };
  }
  const nextAverage =
    (Number(aggregate.average_rating) * aggregate.review_count - deletedRating) /
    nextCount;
  return {
    average_rating: Math.max(1, Math.min(5, nextAverage)).toFixed(1),
    review_count: nextCount,
  };
}
