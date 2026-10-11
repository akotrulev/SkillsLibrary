using OpenQA.Selenium.Appium;

namespace AppiumTests.Pages;

public sealed class OrderRow
{
    private const string RowId = "OrderRow";
    private const string NumberId = "OrderRow.Number";
    private const string TitleId = "OrderRow.Title";
    private const string StatusId = "OrderRow.Status";

    private readonly AppiumDriver _driver;
    private readonly string _orderNumber;

    internal OrderRow(AppiumDriver driver, string orderNumber)
    {
        _driver = driver;
        _orderNumber = orderNumber;
    }

    public string Title() => TextOf(TitleId);

    public string Status() => TextOf(StatusId);

    public void Open() => Root().Click();

    private string TextOf(string id) => Root().FindElement(BaseAppiumPage.TestId(_driver, id)).Text;

    private AppiumElement Root() =>
        BaseAppiumPage.Wait(_driver, $"No {RowId} shows order {_orderNumber}").Until(_ =>
            _driver.FindElements(BaseAppiumPage.TestId(_driver, RowId))
                .FirstOrDefault(row => row.FindElement(BaseAppiumPage.TestId(_driver, NumberId)).Text == _orderNumber))!;
}
