namespace Workshops.Api.Data;

public class MembershipPlan
{
    public int Id { get; set; }
    public required string Name { get; set; }
    public int MonthlyCredits { get; set; }
    public decimal OverageRate { get; set; }
}

public class Member
{
    public Guid Id { get; set; }
    public int PlanId { get; set; }
    public MembershipPlan Plan { get; set; } = null!;
    public decimal? OverageRateOverride { get; set; }
    public int CreditsUsed { get; set; }
}

public enum SessionTier
{
    Standard = 1,
    Workshop = 2,
    Masterclass = 3
}

public class Session
{
    public Guid Id { get; set; }
    public required string Title { get; set; }
    public SessionTier Tier { get; set; }
    public DateTimeOffset StartsAt { get; set; }
    public bool IsCancelled { get; set; }
}

public enum BookingStatus
{
    Confirmed,
    Cancelled
}

public class Booking
{
    public Guid Id { get; set; }
    public Guid MemberId { get; set; }
    public Guid SessionId { get; set; }
    public Session Session { get; set; } = null!;
    public BookingStatus Status { get; set; }
    public int CreditCost { get; set; }
    public int CreditsSpent { get; set; }
}

public class AccruedOverage
{
    public Guid Id { get; set; }
    public Guid MemberId { get; set; }
    public Guid BookingId { get; set; }
    public int Credits { get; set; }
    public decimal Amount { get; set; }
    public DateTimeOffset AccruedAt { get; set; }
    public bool IsPosted { get; set; }
}

public class LedgerCharge
{
    public Guid Id { get; set; }
    public Guid MemberId { get; set; }
    public decimal Amount { get; set; }
    public required string Description { get; set; }
    public DateTimeOffset PostedAt { get; set; }
}

public class OutboxMessage
{
    public Guid Id { get; set; }
    public required string Type { get; set; }
    public required string Payload { get; set; }
    public int Attempts { get; set; }
    public bool IsParked { get; set; }
    public DateTimeOffset? DeliveredAt { get; set; }
}
