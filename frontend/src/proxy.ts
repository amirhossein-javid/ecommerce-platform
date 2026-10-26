import { NextRequest, NextResponse } from "next/server";

import { normalizeToken } from "@/lib/auth-contract";
import { refreshSession } from "@/lib/auth-refresh";
import { privateAuthJson, refreshFailureResponse } from "@/lib/auth-route";
import { RefreshFailure } from "@/lib/refresh-failure";
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
  } catch (error) {
    if (!(error instanceof RefreshFailure) || error.status !== 401) {
      const failure = refreshFailureResponse(
        error instanceof RefreshFailure ? error : new RefreshFailure(),
      )!;
      if (request.nextUrl.pathname === "/api/auth/session") return failure;
      // Stop rendering: continuing could misrepresent this session as a guest.
      const { error: message } = await failure.json() as { error: string };
      return new NextResponse(
        `<!doctype html><html lang="fa" dir="rtl"><meta charset="utf-8"><title>سرویس موقتاً در دسترس نیست</title><body><main><p role="alert">${message}</p><p>صفحه را کمی بعد تازه کنید.</p></main></body></html>`,
        {
          status: failure.status,
          headers: {
            "Content-Type": "text/html; charset=utf-8",
            "Cache-Control": "private, no-store, max-age=0, must-revalidate",
            ...(failure.headers.has("Retry-After")
              ? { "Retry-After": failure.headers.get("Retry-After")! } : {}),
          },
        },
      );
    }
    const response = request.nextUrl.pathname === "/api/auth/session"
      ? privateAuthJson({ error: "نشست شما منقضی شده است. دوباره وارد شوید." }, 401)
      : NextResponse.next();
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
