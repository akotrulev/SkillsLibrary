namespace Workshops.Api.Data;

public static class SessionTierCredits
{
    public static int PerSeat(SessionTier tier) => tier switch
    {
        SessionTier.Standard => 1,
        SessionTier.Workshop => 2,
        SessionTier.Masterclass => 3,
        _ => throw new ArgumentOutOfRangeException(nameof(tier), tier, null)
    };
}
