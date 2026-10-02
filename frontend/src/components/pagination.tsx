import Link from "next/link";

type PaginationProps = {
  currentPage: number;
  totalPages: number;
};

function pageHref(page: number) {
  return page === 1 ? "/products" : `/products?page=${page}`;
}

export function Pagination({ currentPage, totalPages }: PaginationProps) {
  if (totalPages <= 1) {
    return null;
  }

  const hasPrevious = currentPage > 1;
  const hasNext = currentPage < totalPages;
  const controlClasses =
    "inline-flex min-h-11 items-center justify-center rounded-md border border-border bg-surface px-4 text-sm font-semibold text-foreground transition-colors hover:border-primary/40 hover:bg-surface-subtle";
  const disabledClasses =
    "inline-flex min-h-11 cursor-not-allowed items-center justify-center rounded-md border border-border bg-surface-subtle px-4 text-sm font-semibold text-muted-foreground opacity-60";

  return (
    <nav
      aria-label="صفحه‌بندی محصولات"
      className="mt-10 flex flex-wrap items-center justify-between gap-4 border-t border-border pt-6 sm:mt-12"
    >
      {hasPrevious ? (
        <Link
          href={pageHref(currentPage - 1)}
          rel="prev"
          className={controlClasses}
        >
          صفحهٔ قبل
        </Link>
      ) : (
        <span aria-disabled="true" className={disabledClasses}>
          صفحهٔ قبل
        </span>
      )}

      <p className="text-sm font-medium text-muted-foreground" aria-live="polite">
        صفحهٔ {currentPage.toLocaleString("fa-IR")} از {totalPages.toLocaleString("fa-IR")}
      </p>

      {hasNext ? (
        <Link
          href={pageHref(currentPage + 1)}
          rel="next"
          className={controlClasses}
        >
          صفحهٔ بعد
        </Link>
      ) : (
        <span aria-disabled="true" className={disabledClasses}>
          صفحهٔ بعد
        </span>
      )}
    </nav>
  );
}
