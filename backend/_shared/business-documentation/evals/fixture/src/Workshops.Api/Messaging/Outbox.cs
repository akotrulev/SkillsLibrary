using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Workshops.Api.Data;

namespace Workshops.Api.Messaging;

public class Outbox(IServiceScopeFactory scopeFactory) : BackgroundService
{
    private const int MaxAttempts = 3;
    private static readonly TimeSpan PollInterval = TimeSpan.FromSeconds(5);

    public static void Enqueue<TMessage>(WorkshopsDbContext db, TMessage message) where TMessage : notnull =>
        db.OutboxMessages.Add(new OutboxMessage
        {
            Id = Guid.NewGuid(),
            Type = typeof(TMessage).Name,
            Payload = JsonSerializer.Serialize(message)
        });

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        using var timer = new PeriodicTimer(PollInterval);
        while (await timer.WaitForNextTickAsync(stoppingToken))
        {
            await DeliverPendingAsync(stoppingToken);
        }
    }

    private async Task DeliverPendingAsync(CancellationToken cancellationToken)
    {
        using var scope = scopeFactory.CreateScope();
        var db = scope.ServiceProvider.GetRequiredService<WorkshopsDbContext>();
        var pending = await db.OutboxMessages
            .Where(m => m.DeliveredAt == null && !m.IsParked)
            .ToListAsync(cancellationToken);

        foreach (var message in pending)
        {
            try
            {
                await DispatchAsync(scope.ServiceProvider, message, cancellationToken);
                message.DeliveredAt = DateTimeOffset.UtcNow;
            }
            catch (Exception) when (!cancellationToken.IsCancellationRequested)
            {
                message.Attempts++;
                message.IsParked = message.Attempts >= MaxAttempts;
            }
            await db.SaveChangesAsync(cancellationToken);
        }
    }

    private static Task DispatchAsync(IServiceProvider services, OutboxMessage message, CancellationToken cancellationToken) =>
        message.Type switch
        {
            nameof(BookingConfirmed) => services.GetRequiredService<IMessageHandler<BookingConfirmed>>()
                .HandleAsync(JsonSerializer.Deserialize<BookingConfirmed>(message.Payload)!, cancellationToken),
            nameof(BookingCancelled) => services.GetRequiredService<IMessageHandler<BookingCancelled>>()
                .HandleAsync(JsonSerializer.Deserialize<BookingCancelled>(message.Payload)!, cancellationToken),
            _ => throw new InvalidOperationException($"Unknown outbox message type {message.Type}")
        };
}
