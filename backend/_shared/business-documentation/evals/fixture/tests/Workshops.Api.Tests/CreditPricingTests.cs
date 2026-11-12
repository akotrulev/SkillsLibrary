using Workshops.Api.Credits;
using Workshops.Api.Data;

namespace Workshops.Api.Tests;

public class CreditPricingTests
{
    private static Member BasicMember(int creditsUsed, decimal? overrideRate = null) => new()
    {
        Id = Guid.NewGuid(),
        Plan = new MembershipPlan { Id = 1, Name = "Basic", MonthlyCredits = 8, OverageRate = 6.00m },
        CreditsUsed = creditsUsed,
        OverageRateOverride = overrideRate
    };

    [Test]
    public void Should_SpendCreditsOnly_When_AllowanceCoversTier()
    {
        var price = CreditPricingService.Price(SessionTier.Workshop, BasicMember(creditsUsed: 3));

        Assert.That(price, Is.EqualTo(new BookingPrice(2, 2, 0, 0m)));
    }

    [Test]
    public void Should_ChargeShortfallAtPlanRate_When_AllowanceRunsOut()
    {
        var price = CreditPricingService.Price(SessionTier.Masterclass, BasicMember(creditsUsed: 6));

        Assert.That(price, Is.EqualTo(new BookingPrice(3, 2, 1, 6.00m)));
    }

    [Test]
    public void Should_UseMemberRate_When_OverrideIsSet()
    {
        var price = CreditPricingService.Price(SessionTier.Masterclass, BasicMember(creditsUsed: 8, overrideRate: 4.50m));

        Assert.That(price.OverageAmount, Is.EqualTo(13.50m));
    }
}
