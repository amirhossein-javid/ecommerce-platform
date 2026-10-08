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

export type ProductDetail = Omit<ProductListItem, "primary_image"> & {
  description: string;
  images: ProductImage[];
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

function isCategorySummary(value: unknown): value is CategorySummary {
  if (!value || typeof value !== "object") {
    return false;
  }

  const category = value as Partial<CategorySummary>;

  return (
    Number.isInteger(category.id) &&
    typeof category.name === "string" &&
    typeof category.slug === "string"
  );
}

function isProductImage(value: unknown): value is ProductImage {
  if (!value || typeof value !== "object") {
    return false;
  }

  const image = value as Partial<ProductImage>;

  return (
    Number.isInteger(image.id) &&
    typeof image.image === "string" &&
    typeof image.alt_text === "string" &&
    typeof image.is_primary === "boolean" &&
    Number.isInteger(image.position)
  );
}

function hasProductSummaryFields(
  value: unknown,
): value is Omit<ProductListItem, "primary_image"> {
  if (!value || typeof value !== "object") {
    return false;
  }

  const product = value as Partial<ProductListItem>;

  return (
    Number.isInteger(product.id) &&
    typeof product.name === "string" &&
    typeof product.slug === "string" &&
    isCategorySummary(product.category) &&
    typeof product.price === "string" &&
    /^\d+$/.test(product.price) &&
    typeof product.in_stock === "boolean"
  );
}

function isProductListItem(value: unknown): value is ProductListItem {
  if (!hasProductSummaryFields(value)) {
    return false;
  }

  const product = value as ProductListItem;

  return (
    product.primary_image === null || isProductImage(product.primary_image)
  );
}

function isProductDetail(value: unknown): value is ProductDetail {
  if (!hasProductSummaryFields(value)) {
    return false;
  }

  const product = value as ProductDetail;

  return (
    typeof product.description === "string" &&
    Array.isArray(product.images) &&
    product.images.every(isProductImage)
  );
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
    Array.isArray(page.results) &&
    page.results.every(isProductListItem)
  );
}

function getPublicMediaUrl() {
  const value = process.env.DJANGO_PUBLIC_MEDIA_URL;

  if (!value) {
    return null;
  }

  try {
    return new URL(value);
  } catch {
    return null;
  }
}

function withPublicImageUrl(
  image: ProductImage,
  apiOrigin: URL,
  publicMediaUrl: URL | null,
): ProductImage {
  if (!publicMediaUrl) {
    return image;
  }

  try {
    const imageUrl = new URL(image.image);

    if (
      imageUrl.origin !== apiOrigin.origin ||
      !imageUrl.pathname.startsWith(publicMediaUrl.pathname)
    ) {
      return image;
    }

    const publicImageUrl = new URL(
      imageUrl.pathname.slice(publicMediaUrl.pathname.length),
      publicMediaUrl,
    );
    publicImageUrl.search = imageUrl.search;

    return { ...image, image: publicImageUrl.toString() };
  } catch {
    return image;
  }
}

function withPublicMediaUrls(page: ProductPage, apiOrigin: URL): ProductPage {
  const publicMediaUrl = getPublicMediaUrl();

  return {
    ...page,
    results: page.results.map((product) => {
      const primaryImage = product.primary_image;

      if (!primaryImage) {
        return product;
      }

      return {
        ...product,
        primary_image: withPublicImageUrl(
          primaryImage,
          apiOrigin,
          publicMediaUrl,
        ),
      };
    }),
  };
}

function withPublicDetailMediaUrls(
  product: ProductDetail,
  apiOrigin: URL,
): ProductDetail {
  const publicMediaUrl = getPublicMediaUrl();

  return {
    ...product,
    images: product.images.map((image) =>
      withPublicImageUrl(image, apiOrigin, publicMediaUrl),
    ),
  };
}

export async function getProducts(page: number): Promise<ProductPage> {
  const apiOrigin = getApiOrigin();
  const url = new URL(PRODUCTS_PATH, apiOrigin);
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

  return withPublicMediaUrls(data, apiOrigin);
}

export async function getProduct(slug: string): Promise<ProductDetail> {
  const apiOrigin = getApiOrigin();
  let normalizedSlug: string;

  try {
    normalizedSlug = decodeURIComponent(slug).trim();
  } catch {
    throw new CatalogApiError(404);
  }

  if (!normalizedSlug) {
    throw new CatalogApiError(404);
  }

  const url = new URL(
    `${PRODUCTS_PATH}${encodeURIComponent(normalizedSlug)}/`,
    apiOrigin,
  );
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

  if (!isProductDetail(data)) {
    throw new CatalogApiError();
  }

  return withPublicDetailMediaUrls(data, apiOrigin);
}
