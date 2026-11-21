import { describe, expect, it } from 'vitest';
import { applyDiscount, percentOffFor } from '../../src/pricing/internal/discount-rules';

describe('discount rules', () => {
  it('Should_ReturnTenPercent_When_CodeIsLaunch10', () => {
    expect(percentOffFor('LAUNCH10')).toBe(10);
  });

  it('Should_IgnoreLetterCase_When_CodeIsLowercase', () => {
    expect(percentOffFor('spring25')).toBe(25);
  });

  it('Should_ReturnZero_When_CodeIsUnknown', () => {
    expect(percentOffFor('NOSUCHCODE')).toBe(0);
  });

  it('Should_ReturnZero_When_NoCodeIsGiven', () => {
    expect(percentOffFor(undefined)).toBe(0);
  });

  it('Should_ReducePrice_When_PercentIsApplied', () => {
    expect(applyDiscount(10000, 25)).toBe(7500);
  });
});
