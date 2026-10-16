export const MANAGEMENT_ACCESS_COOKIE_NAME = "management_access";
export const MANAGEMENT_REFRESH_COOKIE_NAME = "management_refresh";
export const MANAGEMENT_COOKIE_PATH = "/api/management/";

export function getManagementCookieOptions(
  kind: "access" | "refresh",
  isProduction: boolean,
) {
  return {
    httpOnly: true,
    secure: isProduction,
    sameSite: "lax" as const,
    path: MANAGEMENT_COOKIE_PATH,
    maxAge: kind === "access" ? 60 * 5 : 60 * 60 * 24 * 7,
  };
}
