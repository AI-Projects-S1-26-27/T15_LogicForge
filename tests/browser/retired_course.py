"""Regression: hidden PHIL F211 entries cannot block saved-plan generation."""

import argparse, json
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser()
parser.add_argument("--url", default="http://127.0.0.1:8016")
args = parser.parse_args()
with sync_playwright() as p:
    b = p.chromium.launch(
        executable_path="/usr/bin/chromium", headless=True, args=["--no-sandbox"]
    )
    page = b.new_page()
    data = page.request.get(args.url + "/api/curriculum?branch=e_and_i").json()
    profile = dict(
        completedCourses=data["reference_completed_by_semester"]["4"] + ["PHIL F211"],
        selectedElectives=["PHIL F211"],
        excludedCourses=["PHIL F211"],
        offeringOverrides={"PHIL F211": "both"},
        electiveAllocations={"PHIL F211": "humanities"},
        projectAllocations={"PHIL F211": "open"},
        autoCompleteCore=False,
    )
    plan = dict(
        profile,
        id="legacy-ei",
        name="Legacy saved plan",
        branch="e_and_i",
        currentSemester=4,
        targetSemester=8,
        maxCredits=25,
        solver="astar",
        heuristic="critical_path",
        projectRoute="practice_school",
        allowUnconfirmed=True,
        branchProfiles={"cse": profile},
    )
    page.add_init_script(
        """if (!sessionStorage.getItem('legacy-seeded')) {localStorage.setItem('graphmind_saved_plans_v2',JSON.stringify(%s));sessionStorage.setItem('legacy-seeded','1');}"""
        % json.dumps([plan])
    )
    page.goto(args.url)
    page.get_by_role("button", name="Skip intro").click()
    page.wait_for_function(
        "!localStorage.getItem('graphmind_saved_plans_v2').includes('PHIL F211')"
    )
    with page.expect_response(
        lambda r: "/api/plan" in r.url and r.request.method == "POST"
    ) as response:
        page.get_by_role("button", name="Generate plan (A*)", exact=True).click()
    result = response.value.json()
    assert result["verification_valid"], result
    assert "PHIL F211" not in json.dumps(response.value.request.post_data_json)
    page.get_by_role("combobox", name="Discipline branch").select_option("cse")
    page.wait_for_function(
        "JSON.parse(localStorage.getItem('graphmind_saved_plans_v2'))[0].branch==='cse'"
    )
    assert "PHIL F211" not in page.evaluate(
        "localStorage.getItem('graphmind_saved_plans_v2')"
    )
    print(
        "PASS: legacy course removed from transcript, hidden selections, exclusions, mappings and saved branch profile; plan generates"
    )
    b.close()
