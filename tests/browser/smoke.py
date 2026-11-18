from playwright.sync_api import sync_playwright, expect
import argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--url", default="http://127.0.0.1:8000")
parser.add_argument("--browser-executable", default="/usr/bin/chromium")
parser.add_argument("--output", type=Path, default=Path("work/browser-checks"))
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    b = p.chromium.launch(
        executable_path=args.browser_executable, headless=True, args=["--no-sandbox"]
    )
    page = b.new_page(viewport={"width": 1440, "height": 1000})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(args.url)
    page.get_by_role("button", name="Skip intro").click()
    page.get_by_role("combobox", name="Last finished semester").select_option("2")
    page.get_by_role("button", name="Completed courses", exact=False).click()
    page.get_by_role("button", name="Mark reference cores", exact=False).click()
    page.get_by_role(
        "checkbox", name="Allow unlisted courses", exact=False
    ).check()
    page.get_by_role("combobox", name="Planning algorithm").select_option("csp")
    page.get_by_role("button", name="Generate plan (CSP)", exact=True).click()
    page.get_by_text("Schedule independently verified", exact=True).wait_for(
        timeout=25000
    )
    page.get_by_role("button", name="Rename plan", exact=True).click()
    page.get_by_role("textbox", name="Rename active plan").fill("Submission plan")
    page.get_by_role("button", name="Save name", exact=False).click()
    page.get_by_role("button", name="Learned heuristic", exact=True).click()
    page.get_by_role("button", name="Back to semester plan", exact=True).click()
    page.get_by_role("button", name="HuEl", exact=False).first.click()
    assert page.locator(".course-option").count() > 100
    assert (
        page.locator(".course-selection-grid").evaluate(
            "(el)=>getComputedStyle(el).overflowY"
        )
        == "visible"
    )
    page.get_by_role("button", name="Home — semester plan", exact=True).click()
    page.locator("#minor").select_option("finance")
    page.get_by_role("heading", name="2 required CDCs · 6 units", exact=True).wait_for()
    page.get_by_role("button", name="Home — semester plan", exact=True).click()
    page.get_by_role("button", name="Generate plan (CSP)", exact=True).click()
    page.get_by_text("Schedule independently verified", exact=True).wait_for(
        timeout=25000
    )
    page.screenshot(path=str(args.output / "desktop.png"), full_page=True)
    page.get_by_role("button", name="Move FIN F315", exact=True).click()
    page.get_by_role("dialog").wait_for()
    page.get_by_role("button", name="Cancel", exact=True).click()
    for width in [320, 390, 768, 1280]:
        page.set_viewport_size({"width": width, "height": 900})
        assert page.evaluate(
            "document.documentElement.scrollWidth <= innerWidth"
        ), width
    page.screenshot(path=str(args.output / "mobile.png"), full_page=True)
    assert not errors, errors
    print(
        "PASS: CSP generation, rename, learned navigation, expanded electives, minor CDCs, finance scheduling, move dialog, responsive widths; no browser errors"
    )
    b.close()
