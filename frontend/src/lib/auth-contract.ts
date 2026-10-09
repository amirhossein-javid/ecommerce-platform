const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const PHONE_PATTERN = /^\+[1-9][0-9]{0,14}$/;

export const MAX_EMAIL_LENGTH = 254;
export const MAX_PASSWORD_LENGTH = 1024;
export const MAX_NAME_LENGTH = 150;
export const MAX_PHONE_LENGTH = 16;
export const MAX_TOKEN_LENGTH = 8192;

export type AuthTokens = {
  access: string;
  refresh: string;
};

export type CustomerProfile = {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  phone_number: string;
  created_at: string;
  updated_at: string;
};

type LoginInput = {
  email: string;
  password: string;
};

export type RegistrationInput = LoginInput & {
  first_name: string;
  last_name: string;
  phone_number: string;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function hasExactKeys(value: Record<string, unknown>, expected: string[]) {
  const keys = Object.keys(value);
  return keys.length === expected.length && expected.every((key) => key in value);
}

function normalizeEmail(value: unknown) {
  if (typeof value !== "string") {
    return null;
  }

  const email = value.trim();
  return email.length > 0 &&
    email.length <= MAX_EMAIL_LENGTH &&
    EMAIL_PATTERN.test(email)
    ? email
    : null;
}

function normalizePassword(value: unknown) {
  return typeof value === "string" &&
    value.length > 0 &&
    value.length <= MAX_PASSWORD_LENGTH
    ? value
    : null;
}

function normalizeName(value: unknown) {
  if (typeof value !== "string") {
    return null;
  }

  const name = value.trim();
  return name.length > 0 && name.length <= MAX_NAME_LENGTH ? name : null;
}

export function normalizeToken(value: unknown) {
  return typeof value === "string" &&
    value.length > 0 &&
    value.length <= MAX_TOKEN_LENGTH
    ? value
    : null;
}

export function parseLoginInput(value: unknown): LoginInput | null {
  if (!isRecord(value) || !hasExactKeys(value, ["email", "password"])) {
    return null;
  }

  const email = normalizeEmail(value.email);
  const password = normalizePassword(value.password);
  return email && password ? { email, password } : null;
}

export function parseRegistrationInput(
  value: unknown,
): RegistrationInput | null {
  const expected = [
    "email",
    "password",
    "first_name",
    "last_name",
    "phone_number",
  ];
  if (!isRecord(value) || !hasExactKeys(value, expected)) {
    return null;
  }

  const email = normalizeEmail(value.email);
  const password = normalizePassword(value.password);
  const first_name = normalizeName(value.first_name);
  const last_name = normalizeName(value.last_name);
  const phone_number =
    typeof value.phone_number === "string" &&
    value.phone_number.length <= MAX_PHONE_LENGTH &&
    PHONE_PATTERN.test(value.phone_number)
      ? value.phone_number
      : null;

  return email && password && first_name && last_name && phone_number
    ? { email, password, first_name, last_name, phone_number }
    : null;
}

export function isAuthTokens(value: unknown): value is AuthTokens {
  return (
    isRecord(value) &&
    Object.keys(value).length === 2 &&
    normalizeToken(value.access) !== null &&
    normalizeToken(value.refresh) !== null
  );
}

export function isCustomerProfile(value: unknown): value is CustomerProfile {
  if (!isRecord(value)) {
    return false;
  }

  return (
    Number.isSafeInteger(value.id) &&
    Number(value.id) > 0 &&
    typeof value.email === "string" &&
    typeof value.first_name === "string" &&
    typeof value.last_name === "string" &&
    typeof value.phone_number === "string" &&
    typeof value.created_at === "string" &&
    typeof value.updated_at === "string"
  );
}
