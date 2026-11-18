"""Automatic transcript follows branch/semester; manual backlog edits persist."""

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
    page.get_by_role("combobox", name="Last finished semester").select_option("4")
    page.get_by_role("button", name="Completed courses", exact=False).click()
    page.get_by_role("button", name="Show all transcript courses", exact=True).click()
    for branch, prefix in [
        ("cse", "CS"),
        ("eee", "EEE"),
        ("ece", "ECE"),
        ("e_and_i", "INSTR"),
    ]:
        if branch == "cse":
            data = page.request.get(args.url + "/api/curriculum?branch=cse").json()
        else:
            with page.expect_response(
                lambda r: "/api/curriculum?" in r.url and "branch=" + branch in r.url
            ) as response:
                page.get_by_role("combobox", name="Discipline branch").select_option(
                    branch
                )
            data = response.value.json()
        expected = data["reference_completed_by_semester"]["4"]
        page.wait_for_function(
            "expected=>JSON.stringify(JSON.parse(localStorage.getItem('graphmind_saved_plans_v2'))[0].completedCourses.slice().sort())===JSON.stringify(expected.slice().sort())",
            arg=expected,
        )
        expect(
            page.locator(".transcript-course")
            .filter(has_text="CS F111")
            .locator("input")
        ).to_be_checked()
        if branch != "cse":
            assert (
                page.locator(".transcript-course").filter(has_text="CS F213").count()
                == 0
            )
        own = (
            page.locator(".transcript-course")
            .filter(has_text=prefix + " F211")
            .locator("input")
        )
        if branch != "cse":
            expect(own).to_be_checked()
        print(branch, "automatically selects only current branch CDCs", flush=True)
    own = (
        page.locator(".transcript-course")
        .filter(has_text="INSTR F211")
        .locator("input")
    )
    own.uncheck()
    expect(
        page.get_by_role("checkbox", name="Auto-select this branch", exact=False)
    ).not_to_be_checked()
    page.reload()
    page.get_by_role("button", name="Completed courses", exact=False).click()
    page.get_by_role("button", name="Show all transcript courses", exact=True).click()
    expect(
        page.locator(".transcript-course")
        .filter(has_text="INSTR F211")
        .locator("input")
    ).not_to_be_checked()
    page.get_by_role("checkbox", name="Auto-select this branch", exact=False).check()
    expect(
        page.locator(".transcript-course")
        .filter(has_text="INSTR F211")
        .locator("input")
    ).to_be_checked()
    print("Manual backlog survives reload; automatic mode can be restored")
    b.close()
