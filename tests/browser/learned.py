"""Live API/browser acceptance for the corrected uploaded ML backend."""

import argparse
from playwright.sync_api import sync_playwright, expect

parser = argparse.ArgumentParser()
parser.add_argument("--url", default="http://127.0.0.1:8016")
args = parser.parse_args()
with sync_playwright() as p:
    browser = p.chromium.launch(
        executable_path="/usr/bin/chromium", headless=True, args=["--no-sandbox"]
    )
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(args.url)
    page.get_by_role("button", name="Skip intro").click()
    page.get_by_role("button", name="Learned heuristic", exact=True).click()
    page.get_by_role("heading", name="No measured run yet.", exact=True).wait_for()
    page.get_by_role("button", name="Use learned A*", exact=True).click()

    page.get_by_role("combobox", name="Last finished semester").select_option("2")
    page.get_by_role("button", name="Completed courses", exact=False).click()
    page.get_by_role("button", name="Mark reference cores", exact=False).click()
    page.get_by_role(
        "checkbox", name="Allow unlisted courses", exact=False
    ).check()
    with page.expect_response(
        lambda r: "/api/plan" in r.url and r.request.method == "POST"
    ) as response:
        page.get_by_role("button", name="Generate plan (A*)", exact=True).click()
    payload = response.value.json()
    assert payload["verification_valid"]
    assert payload["stats"]["heuristic_details"]["model_available"]
    assert (
        payload["stats"]["heuristic_details"]["model"]["metadata"]["dataset_size"]
        == 224
    )
    page.get_by_text("Schedule independently verified", exact=True).wait_for()
    page.get_by_role("button", name="Learned heuristic", exact=True).click()
    page.get_by_text("Training & validation", exact=True).wait_for()
    expect(page.get_by_text("224 states", exact=False)).to_be_visible()
    page.get_by_role("button", name="Back to semester plan", exact=True).click()
    page.get_by_role("heading", name="Semester plan", exact=True).wait_for()
    assert not errors, errors
    print(
        "PASS: empty heuristic page, model selection, real learned-A* generation, verification, model provenance and Home navigation"
    )
    browser.close()
