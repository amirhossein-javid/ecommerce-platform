import "server-only";

const PRODUCTS_PATH = "/api/v1/products/";

export const PRODUCTS_PAGE_SIZE = 12;
export const CATALOG_REVALIDATE_SECONDS = 60;

export type CategorySummary = {
  id: number;
  name: string;
  slug: string;
};

export type ProductImage = {
  id: number;
  image: string;
  alt_text: string;
  is_primary: boolean;
  position: number;
};

export type ProductListItem = {
  id: number;
  name: string;
  slug: string;
  category: CategorySummary;
  price: string;
  in_stock: boolean;
  primary_image: ProductImage | null;
};

export type ProductPage = {
  count: number;
  next: string | null;
  previous: string | null;
  results: ProductListItem[];
};

export class CatalogApiError extends Error {
  constructor(public readonly status?: number) {
    super("The catalog API request failed.");
    this.name = "CatalogApiError";
  }
}

function getApiOrigin() {
  const value = process.env.DJANGO_API_URL;

  if (!value) {
    throw new CatalogApiError();
  }

  try {
    return new URL(value);
  } catch {
    throw new CatalogApiError();
  }
}

function isProductPage(value: unknown): value is ProductPage {
  if (!value || typeof value !== "object") {
    return false;
  }

  const page = value as Partial<ProductPage>;

  return (
    Number.isInteger(page.count) &&
    (page.count ?? -1) >= 0 &&
    (page.next === null || typeof page.next === "string") &&
    (page.previous === null || typeof page.previous === "string") &&
    Array.isArray(page.results)
  );
}

export async function getProducts(page: number): Promise<ProductPage> {
  const url = new URL(PRODUCTS_PATH, getApiOrigin());
  url.searchParams.set("page", page.toString());
  url.searchParams.set("page_size", PRODUCTS_PAGE_SIZE.toString());

  let response: Response;

  try {
    response = await fetch(url, {
      headers: { Accept: "application/json" },
      next: { revalidate: CATALOG_REVALIDATE_SECONDS },
    });
  } catch {
    throw new CatalogApiError();
  }

  if (!response.ok) {
    throw new CatalogApiError(response.status);
  }

  const data: unknown = await response.json();

  if (!isProductPage(data)) {
    throw new CatalogApiError();
  }

  return data;
}
