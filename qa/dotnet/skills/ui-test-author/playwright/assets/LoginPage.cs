using Microsoft.Playwright;

namespace Example.UiTests.Pages;

public sealed class LoginPage
{
    private readonly IPage _page;
    private readonly SignInForm _signInForm;

    public LoginPage(IPage page)
    {
        _page = page;
        var form = page.GetByTestId("Login.Form").Describe("Sign-in form");
        _signInForm = new SignInForm(form);
        Error = form.Locator(page.GetByRole(AriaRole.Alert)).Describe("Sign-in error");
    }

    public ILocator Error { get; }

    public async Task GoToAsync() => await _page.GotoAsync("/login");

    public async Task SignInAsync(Credentials credentials)
    {
        await GoToAsync();
        await _signInForm.SubmitAsync(credentials);
    }

    public sealed record Credentials(string Email, string Password);

    public sealed class SignInForm
    {
        private readonly ILocator _email;
        private readonly ILocator _password;
        private readonly ILocator _submit;

        public SignInForm(ILocator root)
        {
            _email = root.GetByTestId("Login.Email");
            _password = root.GetByTestId("Login.Password");
            _submit = root.GetByTestId("Login.Submit");
        }

        public async Task SubmitAsync(Credentials credentials)
        {
            await _email.FillAsync(credentials.Email);
            await _password.FillAsync(credentials.Password);
            await _submit.ClickAsync();
        }
    }
}
