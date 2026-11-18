"""Minor alternatives never become unrelated general elective selections."""

import argparse
import json
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser()
parser.add_argument("--url", default="http://127.0.0.1:8016")
args = parser.parse_args()
with sync_playwright() as p:
    browser = p.chromium.launch(
        executable_path="/usr/bin/chromium", headless=True, args=["--no-sandbox"]
    )
    page = browser.new_page()
    page.goto(args.url)
    page.get_by_role("button", name="Skip intro").click()
    page.get_by_role("combobox", name="Last finished semester").select_option("2")
    page.get_by_role("button", name="Completed courses", exact=False).click()
    page.get_by_role("button", name="Mark reference cores", exact=False).click()
    page.get_by_role(
        "checkbox", name="Allow unlisted courses", exact=False
    ).check()
    with page.expect_response(
        lambda r: "/api/curriculum?" in r.url and "robotics_and_automation" in r.url
    ):
        page.locator("#minor").select_option("robotics_and_automation")
    page.get_by_role("combobox", name="Core alternative").select_option("INSTR F242")
    choices = page.evaluate(
        "JSON.parse(localStorage.getItem('graphmind_saved_plans_v2'))[0]"
    )
    assert choices["minorCoreChoices"]["robotics_and_automation"] == ["INSTR F242"]
    assert "INSTR F242" not in choices["selectedElectives"]
    with page.expect_response(
        lambda r: "/api/curriculum?" in r.url and "finance" in r.url
    ):
        page.locator("#minor").select_option("finance")
    page.get_by_role("button", name="Home — semester plan", exact=True).click()
    page.get_by_role("combobox", name="Planning algorithm").select_option("csp")
    with page.expect_response(
        lambda r: "/api/plan" in r.url and r.request.method == "POST"
    ) as result:
        page.get_by_role("button", name="Generate plan (CSP)", exact=True).click()
    data = result.value.json()
    assert data["verification_valid"], data
    assert not any(
        c["code"] == "INSTR F242"
        for term in data["semesters"].values()
        for c in term["courses"]
    )
    assert result.value.request.post_data_json["minor_core_choices"] == []
    print(
        "PASS: chosen minor CDC stays scoped to its minor; switching to Finance removes it from the schedule"
    )
    browser.close()
