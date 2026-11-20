using Cronos;
using Microsoft.EntityFrameworkCore;
using Workshops.Api.Data;

namespace Workshops.Api.Credits;

public class OverageChargeJob(IServiceScopeFactory scopeFactory, TimeProvider clock) : BackgroundService
{
    private static readonly CronExpression Schedule = CronExpression.Parse("0 0 1 * *");

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        while (!stoppingToken.IsCancellationRequested)
        {
            var now = clock.GetUtcNow();
            var next = Schedule.GetNextOccurrence(now.UtcDateTime)!.Value;
            await Task.Delay(next - now.UtcDateTime, clock, stoppingToken);

            using var scope = scopeFactory.CreateScope();
            var db = scope.ServiceProvider.GetRequiredService<WorkshopsDbContext>();
            await PostMonthAsync(db, clock.GetUtcNow(), stoppingToken);
        }
    }

    public static async Task PostMonthAsync(WorkshopsDbContext db, DateTimeOffset postedAt, CancellationToken cancellationToken)
    {
        var unposted = await db.AccruedOverages.Where(a => !a.IsPosted).ToListAsync(cancellationToken);

        foreach (var memberAccruals in unposted.GroupBy(a => a.MemberId))
        {
            var total = memberAccruals.Sum(a => a.Amount);
            if (total > 0)
            {
                db.LedgerCharges.Add(new LedgerCharge
                {
                    Id = Guid.NewGuid(),
                    MemberId = memberAccruals.Key,
                    Amount = total,
                    Description = $"Overage {postedAt.AddMonths(-1):MMMM yyyy}",
                    PostedAt = postedAt
                });
            }

            foreach (var accrual in memberAccruals)
            {
                accrual.IsPosted = true;
            }
        }

        await db.Members.ExecuteUpdateAsync(s => s.SetProperty(m => m.CreditsUsed, 0), cancellationToken);
        await db.SaveChangesAsync(cancellationToken);
    }
}
