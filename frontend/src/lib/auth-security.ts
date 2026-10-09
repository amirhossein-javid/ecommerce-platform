export const ACCESS_COOKIE_NAME = "store_access";
export const REFRESH_COOKIE_NAME = "store_refresh";
export const ACCESS_COOKIE_MAX_AGE = 60 * 5;
export const REFRESH_COOKIE_MAX_AGE = 60 * 60 * 24 * 7;

export function getAuthCookieOptions(
  kind: "access" | "refresh",
  isProduction: boolean,
) {
  return {
    httpOnly: true,
    secure: isProduction,
    sameSite: "lax" as const,
    path: "/",
    maxAge:
      kind === "access" ? ACCESS_COOKIE_MAX_AGE : REFRESH_COOKIE_MAX_AGE,
  };
}
