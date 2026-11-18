from playwright.sync_api import sync_playwright
import json, argparse

parser = argparse.ArgumentParser()
parser.add_argument("--url", default="http://127.0.0.1:8000")
args = parser.parse_args()
with sync_playwright() as p:
    b = p.chromium.launch(
        executable_path="/usr/bin/chromium", headless=True, args=["--no-sandbox"]
    )
    page = b.new_page(viewport={"width": 1440, "height": 1000})
    page.goto(args.url)
    page.get_by_role("button", name="Skip intro").click()
    page.get_by_role("combobox", name="Last finished semester").select_option("4")
    page.get_by_role("button", name="Completed courses", exact=False).click()
    for branch, prefix in [
        ("cse", "CS"),
        ("eee", "EEE"),
        ("ece", "ECE"),
        ("e_and_i", "INSTR"),
    ]:
        with page.expect_response(
            lambda r: "/api/curriculum?" in r.url and "branch=" + branch in r.url
        ) as response:
            if branch == "cse":
                page.reload()
            else:
                page.get_by_role("combobox", name="Discipline branch").select_option(
                    branch
                )
        response.value.finished()
        toggle = page.get_by_role("button", name="Completed courses", exact=False)
        if toggle.get_attribute("aria-expanded") == "false":
            toggle.click()
        page.get_by_role("button", name="Mark reference cores", exact=False).click()
        plans = page.evaluate(
            "JSON.parse(localStorage.getItem('graphmind_saved_plans_v2'))"
        )
        codes = plans[0]["completedCourses"]
        cat = response.value.json()["all_courses"]
        foreign = {c["code"] for c in cat if c["foreign_cdc"]}
        assert not (set(codes) & foreign), (branch, set(codes) & foreign)
        assert any(c.startswith(prefix + " F2") for c in codes), (branch, codes)
        page.get_by_role(
            "checkbox", name="Allow unlisted courses", exact=False
        ).check()
        page.get_by_role("combobox", name="Planning algorithm").select_option("csp")
        page.get_by_role("button", name="Generate plan (CSP)", exact=True).click()
        page.get_by_text("Schedule independently verified", exact=True).wait_for(
            timeout=25000
        )
        print(branch, "clean transcript and verified schedule", flush=True)
    b.close()
