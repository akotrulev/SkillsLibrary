const VAT_RATE = 0.2;

export function addTax(priceCents: number): number {
  return priceCents * (1 + VAT_RATE);
}
