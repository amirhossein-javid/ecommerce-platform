const WHOLE_RIAL_PATTERN = /^\d+$/;

/** Formats an authoritative whole-rial string as toman without losing remainders. */
export function formatToman(priceInRials: string) {
  if (!WHOLE_RIAL_PATTERN.test(priceInRials)) {
    return "قیمت نامعتبر";
  }

  const rials = BigInt(priceInRials);
  const ten = BigInt(10);
  const tomans = rials / ten;
  const remainingRials = rials % ten;
  const formattedTomans = tomans.toLocaleString("fa-IR");

  if (remainingRials === BigInt(0)) {
    return `${formattedTomans} تومان`;
  }

  return `${formattedTomans} تومان و ${remainingRials.toLocaleString("fa-IR")} ریال`;
}

/** Multiplies a whole-rial price for presentation without binary floating point. */
export function multiplyWholeRialPrice(
  priceInRials: string,
  quantity: number,
) {
  if (
    !WHOLE_RIAL_PATTERN.test(priceInRials) ||
    !Number.isSafeInteger(quantity) ||
    quantity < 1
  ) {
    return null;
  }

  return (BigInt(priceInRials) * BigInt(quantity)).toString();
}
