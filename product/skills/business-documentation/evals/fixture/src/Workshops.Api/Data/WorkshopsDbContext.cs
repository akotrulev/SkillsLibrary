using Microsoft.EntityFrameworkCore;

namespace Workshops.Api.Data;

public class WorkshopsDbContext(DbContextOptions<WorkshopsDbContext> options) : DbContext(options)
{
    public DbSet<MembershipPlan> Plans => Set<MembershipPlan>();
    public DbSet<Member> Members => Set<Member>();
    public DbSet<Session> Sessions => Set<Session>();
    public DbSet<Booking> Bookings => Set<Booking>();
    public DbSet<AccruedOverage> AccruedOverages => Set<AccruedOverage>();
    public DbSet<LedgerCharge> LedgerCharges => Set<LedgerCharge>();
    public DbSet<OutboxMessage> OutboxMessages => Set<OutboxMessage>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<MembershipPlan>().HasIndex(p => p.Name).IsUnique();
        modelBuilder.Entity<MembershipPlan>().Property(p => p.OverageRate).HasPrecision(10, 2);
        modelBuilder.Entity<Member>().Property(m => m.OverageRateOverride).HasPrecision(10, 2);
        modelBuilder.Entity<AccruedOverage>().Property(a => a.Amount).HasPrecision(10, 2);
        modelBuilder.Entity<LedgerCharge>().Property(c => c.Amount).HasPrecision(10, 2);
        modelBuilder.Entity<Session>().Property(s => s.Tier).HasConversion<string>();

        modelBuilder.Entity<MembershipPlan>().HasData(
            new MembershipPlan { Id = 1, Name = "Basic", MonthlyCredits = 8, OverageRate = 6.00m },
            new MembershipPlan { Id = 2, Name = "Plus", MonthlyCredits = 16, OverageRate = 5.00m });
    }
}
