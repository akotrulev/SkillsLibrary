using Microsoft.EntityFrameworkCore;
using Workshops.Api.Bookings;
using Workshops.Api.Data;
using Workshops.Api.Messaging;

namespace Workshops.Api.Sessions;

public class SessionService(WorkshopsDbContext db, BookingService bookings)
{
    public async Task CancelSessionAsync(Guid sessionId, CancellationToken cancellationToken)
    {
        var session = await db.Sessions.SingleAsync(s => s.Id == sessionId, cancellationToken);
        session.IsCancelled = true;

        var confirmed = await db.Bookings
            .Where(b => b.SessionId == sessionId && b.Status == BookingStatus.Confirmed)
            .ToListAsync(cancellationToken);

        foreach (var booking in confirmed)
        {
            await bookings.CancelAsync(booking, CancelledBy.Staff, cancellationToken);
        }

        await db.SaveChangesAsync(cancellationToken);
    }
}
