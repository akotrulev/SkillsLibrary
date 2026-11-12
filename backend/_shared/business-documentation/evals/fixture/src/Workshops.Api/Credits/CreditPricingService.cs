using Microsoft.EntityFrameworkCore;
using Workshops.Api.Data;
using Workshops.Api.Messaging;

namespace Workshops.Api.Credits;

public class CreditPricingService(WorkshopsDbContext db, TimeProvider clock) : IMessageHandler<BookingConfirmed>
{
    public async Task HandleAsync(BookingConfirmed message, CancellationToken cancellationToken)
    {
        var booking = await db.Bookings.Include(b => b.Session)
            .SingleAsync(b => b.Id == message.BookingId, cancellationToken);
        var member = await db.Members.Include(m => m.Plan)
            .SingleAsync(m => m.Id == message.MemberId, cancellationToken);

        var price = Price(booking.Session.Tier, member);

        booking.CreditCost = price.CreditCost;
        booking.CreditsSpent = price.CreditsSpent;
        member.CreditsUsed += price.CreditsSpent;

        if (price.OverageCredits > 0)
        {
            db.AccruedOverages.Add(new AccruedOverage
            {
                Id = Guid.NewGuid(),
                MemberId = member.Id,
                BookingId = booking.Id,
                Credits = price.OverageCredits,
                Amount = price.OverageAmount,
                AccruedAt = clock.GetUtcNow()
            });
        }

        await db.SaveChangesAsync(cancellationToken);
    }

    public static BookingPrice Price(SessionTier tier, Member member)
    {
        var creditCost = SessionTierCredits.PerSeat(tier);
        var creditsRemaining = Math.Max(0, member.Plan.MonthlyCredits - member.CreditsUsed);
        if (creditsRemaining >= creditCost)
        {
            return new BookingPrice(creditCost, creditCost, 0, 0m);
        }

        var overageCredits = creditCost - creditsRemaining;
        var rate = member.OverageRateOverride ?? member.Plan.OverageRate;
        return new BookingPrice(creditCost, creditsRemaining, overageCredits, overageCredits * rate);
    }
}

public record BookingPrice(int CreditCost, int CreditsSpent, int OverageCredits, decimal OverageAmount);
