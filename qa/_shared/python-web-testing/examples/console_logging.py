from pathlib import Path

from playwright.sync_api import expect, sync_playwright

URL = "http://localhost:5173"
OUTPUT = Path("evidence") / "console"


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    messages: list[str] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        page.on("console", lambda message: messages.append(f"[{message.type}] {message.text}"))

        page.goto(URL)
        page.get_by_role("link", name="Dashboard").click()
        expect(page.get_by_role("heading", name="Dashboard")).to_be_visible()

        browser.close()

    log_file = OUTPUT / "console.log"
    log_file.write_text("\n".join(messages), encoding="utf-8")
    print(f"Captured {len(messages)} console messages in {log_file}")


if __name__ == "__main__":
    main()
