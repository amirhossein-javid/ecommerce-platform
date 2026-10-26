import assert from "node:assert/strict";
import { spawn, type ChildProcess } from "node:child_process";
import { once } from "node:events";
import { createServer, type IncomingMessage, type ServerResponse } from "node:http";
import test from "node:test";

type RecordedRequest = {
  method: string;
  pathname: string;
  headers: IncomingMessage["headers"];
  body: string;
};

type BackendReply = {
  status?: number;
  body?: unknown;
  headers?: Record<string, string>;
  disconnect?: boolean;
};

type BackendResponder = (
  request: RecordedRequest,
) => BackendReply | Promise<BackendReply>;

const NOW = "2026-10-17T10:00:00Z";
const CUSTOMER = {
  id: 1,
  email: "customer@example.com",
  first_name: "سارا",
  last_name: "اکبری",
  phone_number: "+989121234567",
  created_at: NOW,
  updated_at: NOW,
};

function order(id: number, status = "PENDING_PAYMENT") {
  return {
    id,
    status,
    subtotal: "1000",
    discount_total: "0",
    shipping_total: "0",
    grand_total: "1000",
    shipping_title: "خانه",
    shipping_recipient_first_name: "سارا",
    shipping_recipient_last_name: "اکبری",
    shipping_recipient_phone_number: "+989121234567",
    shipping_province: "اصفهان",
    shipping_city: "اصفهان",
    shipping_address: "میدان نقش جهان",
    shipping_postal_code: "1234567890",
    items: [
      {
        id: 1,
        product_name: "گلدان",
        sku: "VASE",
        unit_price: "1000",
        quantity: 1,
        line_total: "1000",
      },
    ],
    created_at: NOW,
    payment_expires_at: status === "PENDING_PAYMENT" ? NOW : null,
  };
}

function paymentAttempt(id: number) {
  return {
    id,
    status: "PENDING",
    amount: "1000",
    currency: "IRR",
    payment_url: `https://pay.example.com/attempt/${id}`,
    payment_identifier: null,
    created_at: NOW,
    updated_at: NOW,
  };
}

function requestBody(request: IncomingMessage) {
  return new Promise<string>((resolve, reject) => {
    const chunks: Buffer[] = [];
    request.on("data", (chunk) => chunks.push(Buffer.from(chunk)));
    request.on("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
    request.on("error", reject);
  });
}

function sendReply(response: ServerResponse, reply: BackendReply) {
  if (reply.disconnect) {
    response.destroy();
    return;
  }
  const status = reply.status ?? 200;
  const body = status === 204 ? "" : JSON.stringify(reply.body ?? {});
  response.writeHead(status, {
    ...(body ? { "Content-Type": "application/json" } : {}),
    ...reply.headers,
  });
  response.end(body);
}

async function listen(server: ReturnType<typeof createServer>) {
  server.listen(0, "127.0.0.1");
  await once(server, "listening");
  const address = server.address();
  assert(address && typeof address !== "string");
  return address.port;
}

async function unusedPort() {
  const server = createServer();
  const port = await listen(server);
  await new Promise<void>((resolve, reject) =>
    server.close((error) => (error ? reject(error) : resolve())),
  );
  return port;
}

async function waitForNext(baseUrl: string, process: ChildProcess, logs: () => string) {
  const deadline = Date.now() + 60_000;
  while (Date.now() < deadline) {
    if (process.exitCode !== null) {
      throw new Error(`Next.js exited before becoming ready.\n${logs()}`);
    }
    try {
      const response = await fetch(`${baseUrl}/api/health`);
      if (response.ok) return;
    } catch {
      // The development server is still compiling or binding its port.
    }
    await new Promise((resolve) => setTimeout(resolve, 200));
  }
  throw new Error(`Next.js did not become ready.\n${logs()}`);
}

function setCookieHeaders(response: Response) {
  const headers = response.headers as Headers & { getSetCookie?: () => string[] };
  return headers.getSetCookie?.() ?? [];
}

function cookieHeader(values: Record<string, string>) {
  return Object.entries(values)
    .map(([name, value]) => `${name}=${value}`)
    .join("; ");
}

function cookieValue(response: Response, name: string) {
  const prefix = `${name}=`;
  const line = setCookieHeaders(response).find((value) => value.startsWith(prefix));
  return line?.slice(prefix.length).split(";", 1)[0];
}

function sameOriginJson(baseUrl: string, body: unknown, cookies?: string) {
  return {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Origin: baseUrl,
      ...(cookies ? { Cookie: cookies } : {}),
    },
    body: JSON.stringify(body),
  };
}

test("Next.js BFF route integration", { timeout: 180_000 }, async (t) => {
  let responder: BackendResponder = () => ({ status: 500, body: { detail: "unset" } });
  let requests: RecordedRequest[] = [];
  const backend = createServer(async (request, response) => {
    const recorded = {
      method: request.method ?? "GET",
      pathname: new URL(request.url ?? "/", "http://backend.test").pathname,
      headers: request.headers,
      body: await requestBody(request),
    };
    requests.push(recorded);
    try {
      sendReply(response, await responder(recorded));
    } catch (error) {
      sendReply(response, {
        status: 500,
        body: { detail: error instanceof Error ? error.message : "mock failure" },
      });
    }
  });

  const backendPort = await listen(backend);
  const nextPort = await unusedPort();
  const baseUrl = `http://127.0.0.1:${nextPort}`;
  let nextLogs = "";
  const next = spawn(
    process.execPath,
    [
      "node_modules/next/dist/bin/next",
      "dev",
      "--webpack",
      "--hostname",
      "127.0.0.1",
      "--port",
      String(nextPort),
    ],
    {
      cwd: process.cwd(),
      env: {
        ...process.env,
        DJANGO_API_URL: `http://127.0.0.1:${backendPort}`,
        PAYMENT_REDIRECT_ALLOWED_ORIGINS: "https://pay.example.com",
      },
      stdio: ["ignore", "pipe", "pipe"],
    },
  );
  next.stdout?.on("data", (chunk) => (nextLogs += chunk.toString()));
  next.stderr?.on("data", (chunk) => (nextLogs += chunk.toString()));

  try {
    await waitForNext(baseUrl, next, () => nextLogs);

    await t.test("login cookies, refresh rotation, and logout use real handlers", async () => {
      requests = [];
      responder = (request) => {
        if (request.pathname === "/api/v1/auth/login/") {
          return { body: { access: "access-old", refresh: "refresh-old" } };
        }
        if (request.pathname === "/api/v1/account/profile/") {
          return { body: CUSTOMER };
        }
        if (request.pathname === "/api/v1/checkout/") {
          return request.headers.authorization === "Bearer access-old"
            ? { status: 401, body: { detail: "expired" } }
            : { status: 201, body: order(41) };
        }
        if (request.pathname === "/api/v1/auth/token/refresh/") {
          return { body: { access: "access-new", refresh: "refresh-new" } };
        }
        if (request.pathname === "/api/v1/auth/logout/") {
          return { status: 204 };
        }
        return { status: 404 };
      };

      const login = await fetch(
        `${baseUrl}/api/auth/login`,
        sameOriginJson(baseUrl, {
          email: "customer@example.com",
          password: "correct-password",
        }),
      );
      assert.equal(login.status, 200);
      assert.deepEqual(await login.json(), { authenticated: true, cartMerge: "none" });
      const loginCookies = setCookieHeaders(login);
      assert(loginCookies.some((value) =>
        value.startsWith("store_access=access-old;") &&
        value.includes("HttpOnly") &&
        value.includes("SameSite=lax"),
      ));
      assert(loginCookies.some((value) =>
        value.startsWith("store_refresh=refresh-old;") && value.includes("HttpOnly"),
      ));

      const checkout = await fetch(
        `${baseUrl}/api/checkout`,
        sameOriginJson(
          baseUrl,
          { addressId: 1 },
          cookieHeader({ store_access: "access-old", store_refresh: "refresh-old" }),
        ),
      );
      assert.equal(checkout.status, 201);
      assert.equal((await checkout.json()).id, 41);
      assert.equal(cookieValue(checkout, "store_access"), "access-new");
      assert.equal(cookieValue(checkout, "store_refresh"), "refresh-new");
      assert(requests.some((request) =>
        request.pathname === "/api/v1/auth/token/refresh/" &&
        JSON.parse(request.body).refresh === "refresh-old",
      ));
      assert(requests.some((request) =>
        request.pathname === "/api/v1/checkout/" &&
        request.headers.authorization === "Bearer access-new" &&
        JSON.parse(request.body).address_id === 1,
      ));

      const logout = await fetch(
        `${baseUrl}/api/auth/logout`,
        sameOriginJson(
          baseUrl,
          {},
          cookieHeader({ store_access: "access-new", store_refresh: "refresh-new" }),
        ),
      );
      assert.equal(logout.status, 200);
      assert.deepEqual(await logout.json(), { authenticated: false });
      assert(setCookieHeaders(logout).filter((value) =>
        /^(store_access|store_refresh)=/.test(value) && value.includes("Max-Age=0"),
      ).length === 2);
      assert(requests.some((request) =>
        request.pathname === "/api/v1/auth/logout/" &&
        JSON.parse(request.body).refresh === "refresh-new",
      ));
    });

    await t.test("login atomically merges and clears a guest cart", async () => {
      requests = [];
      const guestToken = "123e4567-e89b-12d3-a456-426614174000";
      responder = (request) => {
        if (request.pathname === "/api/v1/auth/login/") {
          return { body: { access: "access-merge", refresh: "refresh-merge" } };
        }
        if (request.pathname === "/api/v1/account/profile/") {
          return { body: CUSTOMER };
        }
        if (request.pathname === "/api/v1/cart/merge/") {
          return { body: { items: [], subtotal: "0" } };
        }
        return { status: 404 };
      };

      const response = await fetch(
        `${baseUrl}/api/auth/login`,
        sameOriginJson(
          baseUrl,
          { email: "customer@example.com", password: "correct-password" },
          cookieHeader({ guest_cart_token: guestToken }),
        ),
      );
      assert.equal(response.status, 200);
      assert.deepEqual(await response.json(), { authenticated: true, cartMerge: "merged" });
      assert(setCookieHeaders(response).some((value) =>
        value.startsWith("guest_cart_token=;") && value.includes("Max-Age=0"),
      ));
      const merge = requests.find((request) => request.pathname === "/api/v1/cart/merge/");
      assert(merge);
      assert.equal(merge.headers.authorization, "Bearer access-merge");
      assert.equal(merge.headers["x-cart-token"], guestToken);
    });

    await t.test("checkout and payment preserve uncertain failures and Django order truth", async () => {
      requests = [];
      responder = (request) => {
        if (request.pathname === "/api/v1/checkout/") {
          return JSON.parse(request.body).address_id === 99
            ? { disconnect: true }
            : { status: 201, body: order(51) };
        }
        if (request.pathname === "/api/v1/orders/51/payments/") {
          return { status: 201, body: paymentAttempt(7) };
        }
        if (request.pathname === "/api/v1/orders/52/payments/") {
          return { disconnect: true };
        }
        if (request.pathname === "/api/v1/orders/52/") {
          return { body: order(52, "PAID") };
        }
        return { status: 404 };
      };
      const customerCookies = cookieHeader({
        store_access: "access-checkout",
        store_refresh: "refresh-checkout",
      });

      const checkout = await fetch(
        `${baseUrl}/api/checkout`,
        sameOriginJson(baseUrl, { addressId: 1 }, customerCookies),
      );
      assert.equal(checkout.status, 201);
      const checkoutOrder = await checkout.json();
      assert.equal(checkoutOrder.status, "PENDING_PAYMENT");
      assert.equal(checkoutOrder.grand_total, "1000");

      const uncertainCheckout = await fetch(
        `${baseUrl}/api/checkout`,
        sameOriginJson(baseUrl, { addressId: 99 }, customerCookies),
      );
      assert.equal(uncertainCheckout.status, 503);
      assert.equal((await uncertainCheckout.json()).code, "outcome-unknown");

      const payment = await fetch(
        `${baseUrl}/api/orders/51/payments`,
        sameOriginJson(baseUrl, {}, customerCookies),
      );
      assert.equal(payment.status, 200);
      assert.equal((await payment.json()).payment_url, "https://pay.example.com/attempt/7");

      const failedPayment = await fetch(
        `${baseUrl}/api/orders/52/payments`,
        sameOriginJson(baseUrl, {}, customerCookies),
      );
      assert.equal(failedPayment.status, 503);
      assert.equal((await failedPayment.json()).code, "upstream");

      const authoritativeOrder = await fetch(`${baseUrl}/api/orders/52`, {
        headers: { Cookie: customerCookies },
      });
      assert.equal(authoritativeOrder.status, 200);
      assert.equal((await authoritativeOrder.json()).status, "PAID");
    });

    await t.test("management login enforces origin, permissions, and separate cookies", async () => {
      requests = [];
      responder = (request) => {
        if (request.pathname === "/api/v1/auth/login/") {
          const email = JSON.parse(request.body).email;
          return email === "operator@example.com"
            ? { body: { access: "management-access", refresh: "management-refresh" } }
            : { body: { access: "customer-access", refresh: "customer-refresh" } };
        }
        if (request.pathname === "/api/v1/management/dashboard/summary/") {
          return request.headers.authorization === "Bearer management-access"
            ? {
                body: {
                  order_count: 1,
                  successful_revenue: "1000",
                  pending_fulfillment_count: 1,
                  low_stock_product_count: 0,
                  low_stock_threshold: 5,
                },
              }
            : { status: 403, body: { detail: "forbidden" } };
        }
        if (request.pathname === "/api/v1/management/reviews/") {
          return { status: 403, body: { detail: "forbidden" } };
        }
        if (request.pathname === "/api/v1/auth/logout/") {
          return { status: 204 };
        }
        return { status: 404 };
      };

      const beforeCrossOrigin = requests.length;
      const crossOrigin = await fetch(`${baseUrl}/api/management/auth/login`, {
        ...sameOriginJson(baseUrl, {
          email: "operator@example.com",
          password: "correct-password",
        }),
        headers: {
          "Content-Type": "application/json",
          Origin: "https://attacker.example",
        },
      });
      assert.equal(crossOrigin.status, 403);
      assert.equal(requests.length, beforeCrossOrigin);

      const denied = await fetch(
        `${baseUrl}/api/management/auth/login`,
        sameOriginJson(baseUrl, {
          email: "customer@example.com",
          password: "correct-password",
        }),
      );
      assert.equal(denied.status, 403);
      assert.equal(setCookieHeaders(denied).some((value) =>
        value.startsWith("management_access=customer-access"),
      ), false);
      assert(requests.some((request) =>
        request.pathname === "/api/v1/auth/logout/" &&
        JSON.parse(request.body).refresh === "customer-refresh",
      ));

      const login = await fetch(
        `${baseUrl}/api/management/auth/login`,
        sameOriginJson(baseUrl, {
          email: "operator@example.com",
          password: "correct-password",
        }),
      );
      assert.equal(login.status, 200);
      assert.equal(cookieValue(login, "management_access"), "management-access");
      assert(setCookieHeaders(login).some((value) =>
        value.startsWith("management_refresh=management-refresh;") &&
        value.includes("Path=/api/management") &&
        value.includes("HttpOnly"),
      ));

      const customerCookieOnly = await fetch(`${baseUrl}/api/management/dashboard`, {
        headers: { Cookie: "store_access=management-access" },
      });
      assert.equal(customerCookieOnly.status, 401);

      const dashboard = await fetch(`${baseUrl}/api/management/dashboard`, {
        headers: {
          Cookie: cookieHeader({
            management_access: "management-access",
            management_refresh: "management-refresh",
          }),
        },
      });
      assert.equal(dashboard.status, 200);
      assert.equal((await dashboard.json()).order_count, 1);
    });

    const retryDate = new Date("2037-10-21T07:28:00Z").toUTCString();
    const invalidCredentials = "ایمیل یا رمز عبور صحیح نیست.";
    const rateLimited = "تعداد درخواست‌ها زیاد است. کمی بعد دوباره تلاش کنید.";
    const serviceUnavailable = "ارتباط با سرویس حساب کاربری برقرار نشد.";
    const failureCases: Array<{
      name: string;
      reply: BackendReply;
      expectedStatus: number;
      expectedMessage: string;
      expectedRetryAfter?: string;
    }> = [
      { name: "invalid credentials (400)", reply: { status: 400 }, expectedStatus: 401, expectedMessage: invalidCredentials },
      { name: "invalid credentials (401)", reply: { status: 401 }, expectedStatus: 401, expectedMessage: invalidCredentials },
      { name: "rate limit with seconds", reply: { status: 429, headers: { "Retry-After": "60" } }, expectedStatus: 429, expectedMessage: rateLimited, expectedRetryAfter: "60" },
      { name: "rate limit with HTTP date", reply: { status: 429, headers: { "Retry-After": retryDate } }, expectedStatus: 429, expectedMessage: rateLimited, expectedRetryAfter: retryDate },
      { name: "rate limit without Retry-After", reply: { status: 429 }, expectedStatus: 429, expectedMessage: rateLimited },
      { name: "rate limit with invalid Retry-After", reply: { status: 429, headers: { "Retry-After": "private-backend-detail" } }, expectedStatus: 429, expectedMessage: rateLimited },
      { name: "rate limit with invalid date", reply: { status: 429, headers: { "Retry-After": "Invalid Date" } }, expectedStatus: 429, expectedMessage: rateLimited },
      { name: "upstream 500", reply: { status: 500 }, expectedStatus: 503, expectedMessage: serviceUnavailable },
      { name: "upstream 503", reply: { status: 503 }, expectedStatus: 503, expectedMessage: serviceUnavailable },
      { name: "network disconnect", reply: { disconnect: true }, expectedStatus: 503, expectedMessage: serviceUnavailable },
    ];

    for (const scenario of failureCases) {
      await t.test(`management login safely maps ${scenario.name}`, async () => {
        requests = [];
        responder = () => ({
          ...scenario.reply,
          body: {
            detail: "private-backend-detail",
            access: "unexposed-access",
            refresh: "unexposed-refresh",
          },
        });

        const response = await fetch(
          `${baseUrl}/api/management/auth/login`,
          sameOriginJson(baseUrl, {
            email: "operator@example.com",
            password: "incorrect-password",
          }),
        );

        assert.equal(response.status, scenario.expectedStatus);
        assert.equal(response.headers.get("retry-after"), scenario.expectedRetryAfter ?? null);
        assert.deepEqual(await response.json(), { error: scenario.expectedMessage });
        assert.deepEqual(setCookieHeaders(response), []);
        assert.match(response.headers.get("cache-control") ?? "", /private/);
        assert.match(response.headers.get("cache-control") ?? "", /no-store/);
        assert(requests.length > 0);
        assert(requests.every((request) => request.pathname === "/api/v1/auth/login/"));
      });
    }
  } finally {
    next.kill("SIGTERM");
    await Promise.race([
      once(next, "exit"),
      new Promise((resolve) => setTimeout(resolve, 5_000)),
    ]);
    await new Promise<void>((resolve) => backend.close(() => resolve()));
  }
});
