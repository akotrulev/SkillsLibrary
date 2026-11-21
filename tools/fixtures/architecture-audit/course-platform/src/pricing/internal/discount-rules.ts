const PERCENT_OFF_BY_CODE: ReadonlyMap<string, number> = new Map([
  ['LAUNCH10', 10],
  ['SPRING25', 25],
]);

export function percentOffFor(discountCode: string | undefined): number {
  if (discountCode === undefined) {
    return 0;
  }
  return PERCENT_OFF_BY_CODE.get(discountCode.trim().toUpperCase()) ?? 0;
}

export function applyDiscount(priceCents: number, percentOff: number): number {
  return (priceCents * (100 - percentOff)) / 100;
}
