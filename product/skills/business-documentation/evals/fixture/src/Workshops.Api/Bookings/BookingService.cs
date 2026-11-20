using Workshops.Api.Data;
using Workshops.Api.Messaging;

namespace Workshops.Api.Bookings;

public class BookingService(WorkshopsDbContext db, TimeProvider clock)
{
    public async Task<Booking> ConfirmAsync(Guid memberId, Guid sessionId, CancellationToken cancellationToken)
    {
        var booking = new Booking
        {
            Id = Guid.NewGuid(),
            MemberId = memberId,
            SessionId = sessionId,
            Status = BookingStatus.Confirmed
        };
        db.Bookings.Add(booking);
        Outbox.Enqueue(db, new BookingConfirmed(booking.Id, memberId, sessionId));
        await db.SaveChangesAsync(cancellationToken);
        return booking;
    }

    public async Task CancelAsync(Booking booking, CancelledBy cancelledBy, CancellationToken cancellationToken)
    {
        booking.Status = BookingStatus.Cancelled;
        Outbox.Enqueue(db, new BookingCancelled(booking.Id, booking.MemberId, cancelledBy, clock.GetUtcNow()));
        await db.SaveChangesAsync(cancellationToken);
    }
}
