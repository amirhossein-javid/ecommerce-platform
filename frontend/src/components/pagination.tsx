import Link from "next/link";

import { catalogHref, type CatalogQuery } from "@/lib/catalog-query";

type PaginationProps = {
  currentPage: number;
  totalPages: number;
  query: CatalogQuery;
};

export function Pagination({ currentPage, totalPages, query }: PaginationProps) {
  if (totalPages <= 1) {
    return null;
  }

  const hasPrevious = currentPage > 1;
  const hasNext = currentPage < totalPages;
  const controlClasses =
    "inline-flex min-h-11 items-center justify-center gap-2 rounded-full border border-gold/40 bg-surface px-4 text-sm font-bold text-foreground transition-colors hover:border-primary/35 hover:bg-primary-soft hover:text-primary";
  const disabledClasses =
    "inline-flex min-h-11 cursor-not-allowed items-center justify-center gap-2 rounded-full border border-gold/20 bg-surface/60 px-4 text-sm font-bold text-muted-foreground opacity-55";

  return (
    <nav
      aria-label="صفحه‌بندی محصولات"
      className="mt-10 flex flex-wrap items-center justify-between gap-4 border-t border-gold/35 pt-6 sm:mt-14"
    >
      {hasPrevious ? (
        <Link
          href={catalogHref(query, { page: currentPage - 1 })}
          rel="prev"
          className={controlClasses}
        >
          <span aria-hidden="true">→</span>
          صفحهٔ قبل
        </Link>
      ) : (
        <span aria-disabled="true" className={disabledClasses}>
          <span aria-hidden="true">→</span>
          صفحهٔ قبل
        </span>
      )}

      <p className="text-sm font-bold text-muted-foreground" aria-live="polite">
        صفحهٔ {currentPage.toLocaleString("fa-IR")} از {totalPages.toLocaleString("fa-IR")}
      </p>

      {hasNext ? (
        <Link
          href={catalogHref(query, { page: currentPage + 1 })}
          rel="next"
          className={controlClasses}
        >
          صفحهٔ بعد
          <span aria-hidden="true">←</span>
        </Link>
      ) : (
        <span aria-disabled="true" className={disabledClasses}>
          صفحهٔ بعد
          <span aria-hidden="true">←</span>
        </span>
      )}
    </nav>
  );
}
