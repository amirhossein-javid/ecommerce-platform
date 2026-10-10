const PHONE_PATTERN = /^\+[1-9][0-9]{0,14}$/;
const POSTAL_CODE_PATTERN = /^[0-9]{10}$/;

export const ADDRESS_LIMITS = {
  title: 50,
  name: 150,
  phone: 16,
  province: 100,
  city: 100,
  address: 500,
  postalCode: 10,
} as const;

export type CustomerAddress = {
  id: number;
  title: string;
  recipient_first_name: string;
  recipient_last_name: string;
  recipient_phone_number: string;
  province: string;
  city: string;
  address: string;
  postal_code: string;
  is_default: boolean;
  created_at: string;
  updated_at: string;
};

export type AddressInput = Pick<
  CustomerAddress,
  | "title"
  | "recipient_first_name"
  | "recipient_last_name"
  | "recipient_phone_number"
  | "province"
  | "city"
  | "address"
  | "postal_code"
>;

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function hasExactKeys(value: Record<string, unknown>, expected: string[]) {
  const keys = Object.keys(value);
  return keys.length === expected.length && expected.every((key) => key in value);
}

function trimmed(value: unknown, maxLength: number, required = true) {
  if (typeof value !== "string") return null;
  const normalized = value.trim();
  if (normalized.length > maxLength || (required && normalized.length === 0)) {
    return null;
  }
  return normalized;
}

const INPUT_KEYS = [
  "title",
  "recipient_first_name",
  "recipient_last_name",
  "recipient_phone_number",
  "province",
  "city",
  "address",
  "postal_code",
];

export function parseAddressInput(value: unknown): AddressInput | null {
  if (!isRecord(value) || !hasExactKeys(value, INPUT_KEYS)) return null;

  const title = trimmed(value.title, ADDRESS_LIMITS.title, false);
  const recipient_first_name = trimmed(
    value.recipient_first_name,
    ADDRESS_LIMITS.name,
  );
  const recipient_last_name = trimmed(
    value.recipient_last_name,
    ADDRESS_LIMITS.name,
  );
  const recipient_phone_number = trimmed(
    value.recipient_phone_number,
    ADDRESS_LIMITS.phone,
  );
  const province = trimmed(value.province, ADDRESS_LIMITS.province);
  const city = trimmed(value.city, ADDRESS_LIMITS.city);
  const address = trimmed(value.address, ADDRESS_LIMITS.address);
  const postal_code = trimmed(value.postal_code, ADDRESS_LIMITS.postalCode);

  if (
    title === null ||
    recipient_first_name === null ||
    recipient_last_name === null ||
    recipient_phone_number === null ||
    !PHONE_PATTERN.test(recipient_phone_number) ||
    province === null ||
    city === null ||
    address === null ||
    postal_code === null ||
    !POSTAL_CODE_PATTERN.test(postal_code)
  ) {
    return null;
  }

  return {
    title,
    recipient_first_name,
    recipient_last_name,
    recipient_phone_number,
    province,
    city,
    address,
    postal_code,
  };
}

export function parseAddressId(value: string) {
  if (!/^[1-9][0-9]*$/.test(value)) return null;
  const id = Number(value);
  return Number.isSafeInteger(id) ? id : null;
}

export function isCustomerAddress(value: unknown): value is CustomerAddress {
  if (!isRecord(value)) return false;
  return (
    Number.isSafeInteger(value.id) &&
    Number(value.id) > 0 &&
    typeof value.title === "string" &&
    typeof value.recipient_first_name === "string" &&
    typeof value.recipient_last_name === "string" &&
    typeof value.recipient_phone_number === "string" &&
    typeof value.province === "string" &&
    typeof value.city === "string" &&
    typeof value.address === "string" &&
    typeof value.postal_code === "string" &&
    typeof value.is_default === "boolean" &&
    typeof value.created_at === "string" &&
    typeof value.updated_at === "string"
  );
}

export function isCustomerAddressList(
  value: unknown,
): value is CustomerAddress[] {
  return Array.isArray(value) && value.every(isCustomerAddress);
}
