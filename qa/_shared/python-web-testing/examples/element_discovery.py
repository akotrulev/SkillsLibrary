from pathlib import Path

from playwright.sync_api import expect, sync_playwright

URL = "http://localhost:5173"
OUTPUT = Path("evidence") / "element-discovery"


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.goto(URL)
        expect(page.get_by_role("main")).to_be_visible()

        buttons = page.get_by_role("button").filter(visible=True).all_inner_texts()
        print(f"Found {len(buttons)} visible buttons:")
        for index, name in enumerate(buttons):
            print(f"  [{index}] {name.strip()}")

        links = page.get_by_role("link").filter(visible=True).all()
        print(f"\nFound {len(links)} visible links (first 5):")
        for link in links[:5]:
            print(f"  - {link.inner_text().strip()} -> {link.get_attribute('href')}")

        fields = page.locator("input, textarea, select").all()
        print(f"\nFound {len(fields)} form fields:")
        for field in fields:
            name = field.get_attribute("name") or field.get_attribute("id") or "[unnamed]"
            print(f"  - {name} ({field.get_attribute('type') or 'text'})")

        screenshot = OUTPUT / "page.png"
        page.screenshot(path=screenshot, full_page=True)
        print(f"\nScreenshot saved to {screenshot}")
        browser.close()


if __name__ == "__main__":
    main()
