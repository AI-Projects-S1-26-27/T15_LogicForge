"""Explicit elective placement and automatic Generate navigation."""

import argparse
from playwright.sync_api import sync_playwright, expect

parser = argparse.ArgumentParser()
parser.add_argument("--url", default="http://127.0.0.1:8016")
args = parser.parse_args()
with sync_playwright() as p:
    b = p.chromium.launch(
        executable_path="/usr/bin/chromium", headless=True, args=["--no-sandbox"]
    )
    page = b.new_page(viewport={"width": 1440, "height": 1000})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(args.url)
    page.get_by_role("button", name="Skip intro").click()
    page.get_by_role("combobox", name="Last finished semester").select_option("4")
    page.get_by_role("combobox", name="Planning algorithm").select_option("csp")
    page.get_by_role("button", name="HuEl", exact=False).first.click()
    page.get_by_role("searchbox", name="Search elective pool").fill("HSS F221")
    page.get_by_role(
        "combobox", name="Semester for HSS F221", exact=True
    ).select_option("5")
    with page.expect_response(
        lambda r: "/api/plan" in r.url and r.request.method == "POST"
    ) as result:
        page.get_by_role("button", name="Generate plan (CSP)", exact=True).click()
    data = result.value.json()
    assert data["verification_valid"], data
    assert result.value.request.post_data_json["semester_assignments"] == {
        "HSS F221": 5
    }
    expect(
        page.get_by_role("button", name="Semester plan", exact=True)
    ).to_have_attribute("aria-current", "page")
    semester = page.locator(".semester-card").filter(
        has=page.get_by_role("heading", name="Semester 5", exact=True)
    )
    expect(semester.get_by_text("HSS F221", exact=True)).to_be_visible()
    expect(semester.get_by_text("Fixed semester 5", exact=True)).to_be_visible()
    assert page.locator(".semester-card.is-past").count() == 0
    page.wait_for_function(
        "document.getElementById('generated-plan').getBoundingClientRect().top < 200"
    )
    page.get_by_role("button", name="Show completed semesters", exact=True).click()
    assert page.locator(".semester-card.is-past").count() == 4
    page.get_by_role("button", name="Catalogue & offerings", exact=True).click()
    page.get_by_role("combobox", name="Target semester").select_option("7")
    page.get_by_role("button", name="Generate plan (CSP)", exact=True).click()
    page.get_by_role(
        "heading", name="No verified schedule for these settings", exact=True
    ).wait_for()
    assert page.locator(".semester-card.is-future").count() == 0
    page.get_by_role("button", name="Change target to semester 8", exact=True).click()
    page.get_by_role("button", name="Generate plan (CSP)", exact=True).click()
    page.get_by_text("Schedule independently verified", exact=True).wait_for()
    page.get_by_role("button", name="Choose courses", exact=True).click()
    page.get_by_role("searchbox", name="Search elective pool").fill("HSS F221")
    page.get_by_role(
        "combobox", name="Semester for HSS F221", exact=True
    ).select_option("")
    assert page.locator("#generated-plan").count() == 0
    page.wait_for_function(
        "!JSON.parse(localStorage.getItem('graphmind_saved_plans_v2'))[0].audit"
    )
    assert not errors, errors
    print(
        "PASS: semester pin honoured; Generate opens and reveals the plan; past semesters collapse; failed targets show reasons, no blank cards; clearing pin invalidates result"
    )
    b.close()
