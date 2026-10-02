const WHOLE_RIAL_PATTERN = /^\d+$/;

export function formatRial(price: string) {
  if (!WHOLE_RIAL_PATTERN.test(price)) {
    return "قیمت نامعتبر";
  }

  return `${BigInt(price).toLocaleString("fa-IR")} ریال`;
}
