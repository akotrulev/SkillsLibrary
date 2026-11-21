const MINIMUM_PAID_PRICE_CENTS = 99;

export function applyFloor(priceCents: number): number {
  if (priceCents === 0) {
    return 0;
  }
  return Math.max(priceCents, MINIMUM_PAID_PRICE_CENTS);
}
