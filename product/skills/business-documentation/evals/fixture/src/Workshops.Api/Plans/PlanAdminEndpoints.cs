using Microsoft.EntityFrameworkCore;
using Workshops.Api.Data;
using Workshops.Api.Resources;

namespace Workshops.Api.Plans;

public static class PlanAdminEndpoints
{
    public static void MapPlanAdminEndpoints(this IEndpointRouteBuilder app)
    {
        app.MapPut("/plans/{id:int}", UpdatePlanAsync).RequireAuthorization("workshops:manage");
    }

    private static async Task<IResult> UpdatePlanAsync(
        int id,
        UpdatePlanRequest request,
        MembershipPlanValidator validator,
        WorkshopsDbContext db,
        CancellationToken cancellationToken)
    {
        var validation = await validator.ValidateAsync(request, cancellationToken);
        if (!validation.IsValid)
        {
            return Results.Problem(
                type: "validation-failed",
                statusCode: StatusCodes.Status400BadRequest,
                extensions: new Dictionary<string, object?> { ["errors"] = validation.ToDictionary() });
        }

        var plan = await db.Plans.FindAsync([id], cancellationToken);
        if (plan is null)
        {
            return Results.NotFound();
        }

        var nameTaken = await db.Plans.AnyAsync(p => p.Id != id && p.Name == request.Name, cancellationToken);
        if (nameTaken)
        {
            return Results.Problem(
                type: "plan-name-taken",
                detail: Messages.PlanNameTaken,
                statusCode: StatusCodes.Status409Conflict);
        }

        plan.Name = request.Name;
        plan.MonthlyCredits = request.MonthlyCredits;
        plan.OverageRate = request.OverageRate;
        await db.SaveChangesAsync(cancellationToken);

        return Results.Ok(plan);
    }
}
