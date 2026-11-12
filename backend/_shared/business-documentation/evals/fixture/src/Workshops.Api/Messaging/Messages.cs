namespace Workshops.Api.Messaging;

public enum CancelledBy
{
    Member,
    Staff
}

public record BookingConfirmed(Guid BookingId, Guid MemberId, Guid SessionId);

public record BookingCancelled(Guid BookingId, Guid MemberId, CancelledBy CancelledBy, DateTimeOffset CancelledAt);

public interface IMessageHandler<in TMessage>
{
    Task HandleAsync(TMessage message, CancellationToken cancellationToken);
}
