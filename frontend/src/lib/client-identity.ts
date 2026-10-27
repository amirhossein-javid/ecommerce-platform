import { isIP } from "node:net";

export const TRUSTED_CLIENT_IP_HEADER = "x-naghsh-client-ip";

export function trustedClientIp(headers: Headers): string | undefined {
  const value = headers.get(TRUSTED_CLIENT_IP_HEADER);
  if (!value || value !== value.trim() || isIP(value) === 0) return undefined;
  return value;
}

export function forwardTrustedClientIp(
  headers: Headers,
  clientIp?: string,
) {
  if (clientIp && isIP(clientIp) !== 0) {
    headers.set(TRUSTED_CLIENT_IP_HEADER, clientIp);
  } else {
    headers.delete(TRUSTED_CLIENT_IP_HEADER);
  }
}
