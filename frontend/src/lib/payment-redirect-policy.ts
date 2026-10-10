export function parseAllowedPaymentOrigins(raw: string) {
  return new Set(
    raw
      .split(",")
      .map((value) => value.trim())
      .filter(Boolean)
      .map((value) => {
        try {
          const url = new URL(value);
          return url.username || url.password || url.pathname !== "/" || url.search || url.hash
            ? null
            : url.origin;
        } catch {
          return null;
        }
      })
      .filter((value): value is string => value !== null),
  );
}

export function validatePaymentRedirect(value: string, allowedOrigins: string) {
  let url: URL;
  try {
    url = new URL(value);
  } catch {
    return null;
  }
  const loopback = ["localhost", "127.0.0.1", "[::1]"].includes(url.hostname);
  if (
    url.username ||
    url.password ||
    (url.protocol !== "https:" && !(url.protocol === "http:" && loopback)) ||
    !parseAllowedPaymentOrigins(allowedOrigins).has(url.origin)
  ) {
    return null;
  }
  return url.toString();
}
