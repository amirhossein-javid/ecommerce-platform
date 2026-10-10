import "server-only";

import { NextResponse } from "next/server";

import type { AuthTokens } from "@/lib/auth-contract";
import {
  getManagementCookieOptions,
  MANAGEMENT_ACCESS_COOKIE_NAME,
  MANAGEMENT_REFRESH_COOKIE_NAME,
} from "@/lib/management-auth-security";

const PRIVATE_HEADERS = {
  "Cache-Control": "private, no-store, max-age=0, must-revalidate",
};

export function privateManagementJson(body: unknown, status = 200) {
  return NextResponse.json(body, { status, headers: PRIVATE_HEADERS });
}

export function setManagementCookies(response: NextResponse, tokens: AuthTokens) {
  const isProduction = process.env.NODE_ENV === "production";
  response.cookies.set(
    MANAGEMENT_ACCESS_COOKIE_NAME,
    tokens.access,
    getManagementCookieOptions("access", isProduction),
  );
  response.cookies.set(
    MANAGEMENT_REFRESH_COOKIE_NAME,
    tokens.refresh,
    getManagementCookieOptions("refresh", isProduction),
  );
}

export function clearManagementCookies(response: NextResponse) {
  const isProduction = process.env.NODE_ENV === "production";
  response.cookies.set(MANAGEMENT_ACCESS_COOKIE_NAME, "", {
    ...getManagementCookieOptions("access", isProduction),
    maxAge: 0,
  });
  response.cookies.set(MANAGEMENT_REFRESH_COOKIE_NAME, "", {
    ...getManagementCookieOptions("refresh", isProduction),
    maxAge: 0,
  });
}
