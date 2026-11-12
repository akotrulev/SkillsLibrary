using Microsoft.EntityFrameworkCore;
using Workshops.Api.Bookings;
using Workshops.Api.Credits;
using Workshops.Api.Data;
using Workshops.Api.Messaging;
using Workshops.Api.Plans;
using Workshops.Api.Sessions;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddDbContext<WorkshopsDbContext>(o =>
    o.UseSqlServer(builder.Configuration.GetConnectionString("Workshops")));
builder.Services.AddAuthentication().AddJwtBearer();
builder.Services.AddAuthorization(o =>
{
    o.AddPolicy("credits:own", p => p.RequireClaim("scope", "credits:own"));
    o.AddPolicy("workshops:manage", p => p.RequireClaim("scope", "workshops:manage"));
});

builder.Services.AddSingleton<Outbox>();
builder.Services.AddHostedService(sp => sp.GetRequiredService<Outbox>());
builder.Services.AddScoped<IMessageHandler<BookingConfirmed>, CreditPricingService>();
builder.Services.AddScoped<IMessageHandler<BookingCancelled>, BookingCancelledHandler>();
builder.Services.AddScoped<BookingService>();
builder.Services.AddScoped<SessionService>();
builder.Services.AddScoped<MembershipPlanValidator>();
builder.Services.AddSingleton(TimeProvider.System);
builder.Services.AddHostedService<OverageChargeJob>();

var app = builder.Build();

app.UseAuthentication();
app.UseAuthorization();

app.MapCreditEndpoints();
app.MapPlanAdminEndpoints();

app.Logger.LogInformation("Workshops.Api started");

app.Run();
