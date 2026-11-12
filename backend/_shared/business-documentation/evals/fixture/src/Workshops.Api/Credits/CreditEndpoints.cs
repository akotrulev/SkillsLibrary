using System.Security.Claims;
using Microsoft.EntityFrameworkCore;
using Workshops.Api.Data;

namespace Workshops.Api.Credits;

public static class CreditEndpoints
{
    public static void MapCreditEndpoints(this IEndpointRouteBuilder app)
    {
        app.MapGet("/members/me/credits", GetMyCreditsAsync).RequireAuthorization("credits:own");
    }

    private static async Task<IResult> GetMyCreditsAsync(ClaimsPrincipal user, WorkshopsDbContext db, CancellationToken cancellationToken)
    {
        var memberId = Guid.Parse(user.FindFirstValue(ClaimTypes.NameIdentifier)!);
        var member = await db.Members.Include(m => m.Plan)
            .SingleOrDefaultAsync(m => m.Id == memberId, cancellationToken);
        if (member is null)
        {
            return Results.NotFound();
        }

        var accrued = await db.AccruedOverages
            .Where(a => a.MemberId == memberId && !a.IsPosted)
            .SumAsync(a => a.Amount, cancellationToken);

        return Results.Ok(new MemberCreditsResponse(
            member.Plan.Name,
            member.Plan.MonthlyCredits,
            member.CreditsUsed,
            Math.Max(0, member.Plan.MonthlyCredits - member.CreditsUsed),
            member.OverageRateOverride ?? member.Plan.OverageRate,
            accrued));
    }
}

public record MemberCreditsResponse(
    string PlanName,
    int MonthlyCredits,
    int CreditsUsed,
    int CreditsRemaining,
    decimal OverageRate,
    decimal AccruedOverage);
