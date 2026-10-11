from pathlib import Path

from playwright.sync_api import expect, sync_playwright

HTML_FILE = Path("path/to/your/file.html").resolve()
OUTPUT = Path("evidence") / "static-html"


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        page.goto(HTML_FILE.as_uri())
        page.screenshot(path=OUTPUT / "static_page.png", full_page=True)

        page.get_by_role("button", name="Click Me").click()
        page.get_by_label("Name").fill("John Doe")
        page.get_by_label("Email").fill("john@example.com")
        page.get_by_role("button", name="Submit").click()
        expect(page.get_by_role("status")).to_be_visible()

        page.screenshot(path=OUTPUT / "after_submit.png", full_page=True)
        browser.close()
    print(f"Static HTML automation completed; screenshots in {OUTPUT}")


if __name__ == "__main__":
    main()
