import { NextRequest, NextResponse } from "next/server";

import { normalizeToken } from "@/lib/auth-contract";
import { refreshSession } from "@/lib/auth-refresh";
import {
  ACCESS_COOKIE_NAME,
  getAuthCookieOptions,
  REFRESH_COOKIE_NAME,
} from "@/lib/auth-security";
import { trustedClientIp } from "@/lib/client-identity";

function clearSession(response: NextResponse) {
  const isProduction = process.env.NODE_ENV === "production";
  response.cookies.set(ACCESS_COOKIE_NAME, "", {
    ...getAuthCookieOptions("access", isProduction),
    maxAge: 0,
  });
  response.cookies.set(REFRESH_COOKIE_NAME, "", {
    ...getAuthCookieOptions("refresh", isProduction),
    maxAge: 0,
  });
}

export async function proxy(request: NextRequest) {
  const access = normalizeToken(request.cookies.get(ACCESS_COOKIE_NAME)?.value);
  const refresh = normalizeToken(request.cookies.get(REFRESH_COOKIE_NAME)?.value);
  if (access || !refresh) {
    return NextResponse.next();
  }

  try {
    const tokens = await refreshSession(refresh, trustedClientIp(request.headers));
    request.cookies.set(ACCESS_COOKIE_NAME, tokens.access);
    request.cookies.set(REFRESH_COOKIE_NAME, tokens.refresh);
    const requestHeaders = new Headers(request.headers);
    requestHeaders.set("cookie", request.cookies.toString());
    const response = NextResponse.next({ request: { headers: requestHeaders } });
    const isProduction = process.env.NODE_ENV === "production";
    response.cookies.set(
      ACCESS_COOKIE_NAME,
      tokens.access,
      getAuthCookieOptions("access", isProduction),
    );
    response.cookies.set(
      REFRESH_COOKIE_NAME,
      tokens.refresh,
      getAuthCookieOptions("refresh", isProduction),
    );
    return response;
  } catch {
    const response = NextResponse.next();
    clearSession(response);
    return response;
  }
}

export const config = {
  matcher: [
    "/api/auth/session",
    "/((?!api|_next/static|_next/image|favicon.ico).*)",
  ],
};
