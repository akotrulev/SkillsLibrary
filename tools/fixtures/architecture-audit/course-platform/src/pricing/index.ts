import { applyDiscount, percentOffFor } from './internal/discount-rules';
import { applyFloor } from './internal/price-floor';
import { roundToCents } from './internal/rounding';
import { addTax } from './internal/tax-rules';

export function quote(listPriceCents: number, discountCode?: string): number {
  const discounted = applyDiscount(listPriceCents, percentOffFor(discountCode));
  const floored = applyFloor(discounted);
  return roundToCents(addTax(floored));
}
