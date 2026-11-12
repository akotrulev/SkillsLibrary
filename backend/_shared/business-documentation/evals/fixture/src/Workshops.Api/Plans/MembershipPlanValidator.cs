using FluentValidation;
using Workshops.Api.Resources;

namespace Workshops.Api.Plans;

public record UpdatePlanRequest(string Name, int MonthlyCredits, decimal OverageRate);

public class MembershipPlanValidator : AbstractValidator<UpdatePlanRequest>
{
    public MembershipPlanValidator()
    {
        RuleFor(p => p.Name).NotEmpty().MaximumLength(100);
        RuleFor(p => p.MonthlyCredits).GreaterThanOrEqualTo(0).WithMessage(Messages.MonthlyCreditsNotNegative);
        RuleFor(p => p.OverageRate).GreaterThanOrEqualTo(0).WithMessage(Messages.OverageRateNotNegative);
    }
}
