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
    dialogs = []
    page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
    page.goto(args.url)
    page.get_by_role("button", name="Skip intro").click()
    page.get_by_role("combobox", name="Last finished semester").select_option("4")
    page.get_by_role("combobox", name="Planning algorithm").select_option("csp")
    page.get_by_role("button", name="DEL", exact=False).first.click()
    selected = ["BITS F311", "BITS F312", "BITS F343", "BITS F364", "BITS F386"]
    for code in selected:
        page.get_by_role("searchbox", name="Search elective pool").fill(code)
        page.get_by_role("button", name=f"Add {code} as DEL", exact=True).click()
    card = page.locator(".course-option")
    expect(card.get_by_text("Extra DEL → OpEl", exact=True)).to_be_visible()
    expect(card.get_by_text("Counts as OpEl", exact=True)).to_be_visible()
    expect(page.get_by_text("12 / 12 credits", exact=True)).to_be_visible()
    expect(page.get_by_text("3 / 15 credits", exact=True)).to_be_visible()
    page.get_by_role("searchbox", name="Search elective pool").fill(selected[0])
    page.get_by_role("button", name=f"Remove {selected[0]} as DEL", exact=True).click()
    page.get_by_role("searchbox", name="Search elective pool").fill(selected[4])
    expect(
        page.locator(".course-option").get_by_text("Counts as DEL", exact=True)
    ).to_be_visible()
    page.get_by_role("searchbox", name="Search elective pool").fill(selected[0])
    page.get_by_role("button", name=f"Add {selected[0]} as DEL", exact=True).click()
    page.get_by_role("tab", name="HuEl", exact=False).click()
    for code in ["HSS F221", "HSS F222", "HSS F223", "HSS F224"]:
        page.get_by_role("searchbox", name="Search elective pool").fill(code)
        page.get_by_role("button", name=f"Add {code} as HuEl", exact=True).click()
    expect(page.get_by_text("12 / 9 credits", exact=True)).to_be_visible()
    assert not dialogs
    assert page.locator("dialog[open]").count() == 0
    with page.expect_response(
        lambda r: "/api/plan" in r.url and r.request.method == "POST"
    ) as response:
        page.get_by_role("button", name="Generate plan (CSP)", exact=True).click()
    data = response.value.json()
    assert data["verification_valid"], data
    assert data["audit"]["categories"]["Humanities Elective"]["credit_minimum"] == 9
    assert data["audit"]["categories"]["Discipline Elective"]["courses"] == 4
    assert data["effective_allocations"][selected[0]] == "open"
    assert not dialogs
    print(
        "PASS: fifth DEL becomes OpEl immediately, removal promotes the next DEL, HuEl exceeds nine without a popup, generated audit matches the new rules"
    )
    b.close()
