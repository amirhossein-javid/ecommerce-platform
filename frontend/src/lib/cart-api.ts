import "server-only";

import { cache } from "react";
import { cookies } from "next/headers";

import {
  type Cart,
  EMPTY_CART,
  isCart,
  normalizeGuestCartToken,
} from "@/lib/cart-contract";
import { GUEST_CART_COOKIE_NAME } from "@/lib/cart-security";

const CART_PATH = "/api/v1/cart/";
const CART_ITEMS_PATH = "/api/v1/cart/items/";
const CART_TOKEN_HEADER = "X-Cart-Token";

export class CartApiError extends Error {
  constructor(
    public readonly status?: number,
    public readonly payload?: unknown,
    public readonly retryAfter?: string | null,
  ) {
    super("The cart API request failed.");
    this.name = "CartApiError";
  }
}

function getApiOrigin() {
  const value = process.env.DJANGO_API_URL;

  if (!value) {
    throw new CartApiError();
  }

  try {
    return new URL(value);
  } catch {
    throw new CartApiError();
  }
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

function withPublicMediaUrls(cart: Cart, apiOrigin: URL): Cart {
  const publicMediaUrl = getPublicMediaUrl();

  if (!publicMediaUrl) {
    return cart;
  }

  return {
    ...cart,
    items: cart.items.map((item) => {
      const image = item.product.primary_image;

      if (!image) {
        return item;
      }

      try {
        const imageUrl = new URL(image.image);

        if (
          imageUrl.origin !== apiOrigin.origin ||
          !imageUrl.pathname.startsWith(publicMediaUrl.pathname)
        ) {
          return item;
        }

        const publicImageUrl = new URL(
          imageUrl.pathname.slice(publicMediaUrl.pathname.length),
          publicMediaUrl,
        );
        publicImageUrl.search = imageUrl.search;

        return {
          ...item,
          product: {
            ...item.product,
            primary_image: { ...image, image: publicImageUrl.toString() },
          },
        };
      } catch {
        return item;
      }
    }),
  };
}

async function parseErrorPayload(response: Response) {
  try {
    return (await response.json()) as unknown;
  } catch {
    return undefined;
  }
}

async function requestDjango(
  path: string,
  init: RequestInit,
  token?: string,
) {
  const apiOrigin = getApiOrigin();
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");

  if (token) {
    headers.set(CART_TOKEN_HEADER, token);
  }

  let response: Response;

  try {
    response = await fetch(new URL(path, apiOrigin), {
      ...init,
      headers,
      cache: "no-store",
    });
  } catch {
    throw new CartApiError();
  }

  if (!response.ok) {
    throw new CartApiError(
      response.status,
      await parseErrorPayload(response),
      response.headers.get("retry-after"),
    );
  }

  return { apiOrigin, response };
}

async function parseCartResponse(response: Response, apiOrigin: URL) {
  let payload: unknown;

  try {
    payload = await response.json();
  } catch {
    throw new CartApiError();
  }

  if (!isCart(payload)) {
    throw new CartApiError();
  }

  return withPublicMediaUrls(payload, apiOrigin);
}

export async function fetchGuestCart(token?: string) {
  const { apiOrigin, response } = await requestDjango(
    CART_PATH,
    { method: "GET" },
    token,
  );
  return parseCartResponse(response, apiOrigin);
}

export async function addGuestCartItem(
  token: string | undefined,
  productSlug: string,
  quantity: number,
) {
  const { apiOrigin, response } = await requestDjango(
    CART_ITEMS_PATH,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ product_slug: productSlug, quantity }),
    },
    token,
  );
  const responseToken = normalizeGuestCartToken(
    response.headers.get(CART_TOKEN_HEADER) ?? undefined,
  );

  if (!responseToken) {
    throw new CartApiError();
  }

  return {
    cart: await parseCartResponse(response, apiOrigin),
    token: responseToken,
  };
}

export async function updateGuestCartItem(
  token: string,
  itemId: number,
  quantity: number,
) {
  await requestDjango(
    `${CART_ITEMS_PATH}${itemId}/`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ quantity }),
    },
    token,
  );
  return fetchGuestCart(token);
}

export async function removeGuestCartItem(token: string, itemId: number) {
  await requestDjango(
    `${CART_ITEMS_PATH}${itemId}/`,
    { method: "DELETE" },
    token,
  );
  return fetchGuestCart(token);
}

export const getCurrentGuestCart = cache(async () => {
  const cookieStore = await cookies();
  const token = normalizeGuestCartToken(
    cookieStore.get(GUEST_CART_COOKIE_NAME)?.value,
  );

  if (!token) {
    return fetchGuestCart();
  }

  try {
    return await fetchGuestCart(token);
  } catch (error) {
    if (error instanceof CartApiError && error.status === 404) {
      return EMPTY_CART;
    }
    throw error;
  }
});
