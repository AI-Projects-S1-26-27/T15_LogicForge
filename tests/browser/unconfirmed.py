import argparse
from playwright.sync_api import sync_playwright, expect

parser = argparse.ArgumentParser()
parser.add_argument("--url", default="http://127.0.0.1:8016")
args = parser.parse_args()
with sync_playwright() as p:
    b = p.chromium.launch(
        executable_path="/usr/bin/chromium", headless=True, args=["--no-sandbox"]
    )
    page = b.new_page()
    page.goto(args.url)
    page.get_by_role("button", name="Skip intro").click()
    page.get_by_role("combobox", name="Discipline branch").select_option("eee")
    page.get_by_role("combobox", name="Last finished semester").select_option("4")
    expect(
        page.get_by_role("checkbox", name="Allow unlisted courses", exact=False)
    ).to_be_checked()
    page.get_by_role("button", name="HuEl", exact=False).first.click()
    page.get_by_role("searchbox", name="Search elective pool").fill("HSS F221")
    expect(
        page.locator(".course-option").get_by_text("Assumed odd + even", exact=True)
    ).to_be_visible()
    page.get_by_role("button", name="Add HSS F221 as HuEl", exact=True).click()
    page.get_by_role("button", name="Home — semester plan", exact=True).click()
    page.get_by_role("combobox", name="Planning algorithm").select_option("csp")
    with page.expect_response(
        lambda r: "/api/plan" in r.url and r.request.method == "POST"
    ) as result:
        page.get_by_role("button", name="Generate plan (CSP)", exact=True).click()
    data = result.value.json()
    assert data["verification_valid"], data
    assert result.value.request.post_data_json["allow_unconfirmed"]
    assert any(
        a["code"] == "HSS F221" and "Planning assumption" in a["basis"]
        for a in data["audit"]["offering_assumptions"]
    )
    page.get_by_role("button", name="Catalogue & offerings", exact=True).click()
    expect(page.get_by_text("2024-25 Semester II", exact=True)).to_be_visible()
    print(
        "PASS: unconfirmed course is selectable and schedules without confirmation; assumption and new PDF snapshot are visible"
    )
    b.close()
