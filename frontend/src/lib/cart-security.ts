export const GUEST_CART_COOKIE_NAME = "guest_cart_token";
export const GUEST_CART_COOKIE_MAX_AGE = 60 * 60 * 24 * 30;

export function getGuestCartCookieOptions(isProduction: boolean) {
  return {
    httpOnly: true,
    secure: isProduction,
    sameSite: "lax" as const,
    path: "/",
    maxAge: GUEST_CART_COOKIE_MAX_AGE,
  };
}

export function isTrustedMutationRequest(url: string, headers: Headers) {
  const origin = headers.get("origin");

  if (!origin) {
    return false;
  }

  try {
    const originUrl = new URL(origin);
    const requestUrl = new URL(url);
    const requestHost = headers.get("host") ?? requestUrl.host;

    if (
      originUrl.protocol !== requestUrl.protocol ||
      originUrl.host !== requestHost
    ) {
      return false;
    }
  } catch {
    return false;
  }

  const fetchSite = headers.get("sec-fetch-site");
  return !fetchSite || fetchSite === "same-origin";
}

export function hasJsonContentType(headers: Headers) {
  const mediaType = headers.get("content-type")?.split(";", 1)[0].trim();
  return mediaType?.toLowerCase() === "application/json";
}
