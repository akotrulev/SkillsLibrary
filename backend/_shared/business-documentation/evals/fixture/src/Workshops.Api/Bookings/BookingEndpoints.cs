using System.Security.Claims;
using Microsoft.EntityFrameworkCore;
using Workshops.Api.Data;
using Workshops.Api.Messaging;

namespace Workshops.Api.Bookings;

public static class BookingEndpoints
{
    public static void MapBookingEndpoints(this IEndpointRouteBuilder app)
    {
        app.MapPost("/sessions/{sessionId:guid}/bookings", BookAsync).RequireAuthorization("bookings:own");
        app.MapDelete("/members/me/bookings/{bookingId:guid}", CancelMyBookingAsync).RequireAuthorization("bookings:own");
    }

    private static async Task<IResult> BookAsync(
        Guid sessionId,
        ClaimsPrincipal user,
        BookingService bookings,
        CancellationToken cancellationToken)
    {
        var booking = await bookings.ConfirmAsync(MemberId(user), sessionId, cancellationToken);
        return Results.Created($"/members/me/bookings/{booking.Id}", new BookingResponse(booking.Id, booking.SessionId));
    }

    private static async Task<IResult> CancelMyBookingAsync(
        Guid bookingId,
        ClaimsPrincipal user,
        WorkshopsDbContext db,
        BookingService bookings,
        CancellationToken cancellationToken)
    {
        var memberId = MemberId(user);
        var booking = await db.Bookings.SingleOrDefaultAsync(b => b.Id == bookingId && b.MemberId == memberId, cancellationToken);
        if (booking is null)
        {
            return Results.NotFound();
        }

        await bookings.CancelAsync(booking, CancelledBy.Member, cancellationToken);
        return Results.NoContent();
    }

    private static Guid MemberId(ClaimsPrincipal user) => Guid.Parse(user.FindFirstValue(ClaimTypes.NameIdentifier)!);
}

public record BookingResponse(Guid BookingId, Guid SessionId);
