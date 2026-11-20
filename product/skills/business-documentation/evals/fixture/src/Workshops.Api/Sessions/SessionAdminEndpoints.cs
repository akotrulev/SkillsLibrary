namespace Workshops.Api.Sessions;

public static class SessionAdminEndpoints
{
    public static void MapSessionAdminEndpoints(this IEndpointRouteBuilder app)
    {
        app.MapPost("/sessions/{sessionId:guid}/cancel", CancelSessionAsync).RequireAuthorization("workshops:manage");
    }

    private static async Task<IResult> CancelSessionAsync(
        Guid sessionId,
        SessionService sessions,
        CancellationToken cancellationToken)
    {
        await sessions.CancelSessionAsync(sessionId, cancellationToken);
        return Results.NoContent();
    }
}
