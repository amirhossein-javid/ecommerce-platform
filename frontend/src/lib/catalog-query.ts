export const DEFAULT_PRODUCT_ORDERING = "-created_at";
export const MAX_CATALOG_SEARCH_LENGTH = 100;
export const MAX_CATEGORY_SLUG_LENGTH = 255;

export const PRODUCT_ORDERINGS = [
  "-created_at",
  "created_at",
  "price",
  "-price",
] as const;

export type ProductOrdering = (typeof PRODUCT_ORDERINGS)[number];

export type CatalogQuery = {
  page: number;
  search: string;
  category: string;
  ordering: ProductOrdering;
};

export type RawCatalogSearchParams = {
  page?: string | string[];
  search?: string | string[];
  category?: string | string[];
  ordering?: string | string[];
};

function firstValue(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

function normalizeSearch(value: string | undefined) {
  return Array.from(value?.trim() ?? "")
    .slice(0, MAX_CATALOG_SEARCH_LENGTH)
    .join("");
}

function normalizeCategory(value: string | undefined) {
  const category = value?.trim() ?? "";

  if (
    Array.from(category).length > MAX_CATEGORY_SLUG_LENGTH ||
    (category && !/^[-\p{L}\p{N}_]+$/u.test(category))
  ) {
    return "";
  }

  return category;
}

function parsePage(value: string | undefined) {
  if (!value || !/^\d+$/.test(value)) {
    return 1;
  }

  const page = Number(value);
  return Number.isSafeInteger(page) && page > 0 ? page : 1;
}

function isProductOrdering(value: string): value is ProductOrdering {
  return PRODUCT_ORDERINGS.some((ordering) => ordering === value);
}

export function parseCatalogQuery(
  searchParams: RawCatalogSearchParams,
): CatalogQuery {
  const orderingValue = firstValue(searchParams.ordering)?.trim() ?? "";

  return {
    page: parsePage(firstValue(searchParams.page)),
    search: normalizeSearch(firstValue(searchParams.search)),
    category: normalizeCategory(firstValue(searchParams.category)),
    ordering: isProductOrdering(orderingValue)
      ? orderingValue
      : DEFAULT_PRODUCT_ORDERING,
  };
}

function isCanonicalValue(
  rawValue: string | string[] | undefined,
  canonicalValue: string | undefined,
) {
  return !Array.isArray(rawValue) && rawValue === canonicalValue;
}

export function catalogQueryNeedsNormalization(
  searchParams: RawCatalogSearchParams,
  query: CatalogQuery,
) {
  return !(
    isCanonicalValue(searchParams.search, query.search || undefined) &&
    isCanonicalValue(searchParams.category, query.category || undefined) &&
    isCanonicalValue(
      searchParams.ordering,
      query.ordering === DEFAULT_PRODUCT_ORDERING ? undefined : query.ordering,
    ) &&
    isCanonicalValue(
      searchParams.page,
      query.page === 1 ? undefined : query.page.toString(),
    )
  );
}

export function catalogHref(
  query: CatalogQuery,
  changes: Partial<CatalogQuery> = {},
) {
  const nextQuery = { ...query, ...changes };
  const params = new URLSearchParams();

  if (nextQuery.search) {
    params.set("search", nextQuery.search);
  }
  if (nextQuery.category) {
    params.set("category", nextQuery.category);
  }
  if (nextQuery.ordering !== DEFAULT_PRODUCT_ORDERING) {
    params.set("ordering", nextQuery.ordering);
  }
  if (nextQuery.page > 1) {
    params.set("page", nextQuery.page.toString());
  }

  const queryString = params.toString();
  return queryString ? `/products?${queryString}` : "/products";
}
