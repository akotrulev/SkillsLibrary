using Microsoft.EntityFrameworkCore;
using Workshops.Api.Data;
using Workshops.Api.Messaging;

namespace Workshops.Api.Credits;

public class BookingCancelledHandler(WorkshopsDbContext db) : IMessageHandler<BookingCancelled>
{
    private static readonly TimeSpan LateCancellationCutOff = TimeSpan.FromHours(24);

    public async Task HandleAsync(BookingCancelled message, CancellationToken cancellationToken)
    {
        var booking = await db.Bookings.Include(b => b.Session)
            .SingleAsync(b => b.Id == message.BookingId, cancellationToken);

        var isLateMemberCancellation = message.CancelledBy == CancelledBy.Member
            && booking.Session.StartsAt - message.CancelledAt < LateCancellationCutOff;
        if (isLateMemberCancellation)
        {
            return;
        }

        var member = await db.Members.SingleAsync(m => m.Id == message.MemberId, cancellationToken);
        member.CreditsUsed -= booking.CreditsSpent;

        var accruals = await db.AccruedOverages
            .Where(a => a.BookingId == booking.Id && !a.IsPosted)
            .ToListAsync(cancellationToken);
        db.AccruedOverages.RemoveRange(accruals);

        await db.SaveChangesAsync(cancellationToken);
    }
}
