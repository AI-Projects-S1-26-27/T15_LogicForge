import copy
import pytest
from backend.services.scoped_planner import DATA, normalize_request, prepare, InputError
from backend.services.scoped_api import plan_payload


def test_phil_f211_is_removed_from_every_saved_input_without_modifying_the_request():
    original = dict(
        branch="e_and_i",
        current_semester=2,
        allow_unconfirmed=True,
        completed_courses=DATA["common"] + ["PHIL F211"],
        selected_electives=["PHIL F211"],
        excluded_courses=["PHIL F211"],
        minor_core_choices=["PHIL F211"],
        offering_overrides={"PHIL F211": "both"},
        elective_allocations={"PHIL F211": "humanities"},
        project_allocations={"PHIL F211": "open"},
    )
    before = copy.deepcopy(original)
    cleaned = normalize_request(original)
    for key in (
        "completed_courses",
        "selected_electives",
        "excluded_courses",
        "minor_core_choices",
    ):
        assert "PHIL F211" not in cleaned[key]
    for key in ("offering_overrides", "elective_allocations", "project_allocations"):
        assert "PHIL F211" not in cleaned[key]
    assert original == before
    result = plan_payload(original)
    assert result["verification_valid"]
    assert result["audit"]["requirements_met"]
    assert all(
        c["code"] != "PHIL F211"
        for term in result["semesters"].values()
        for c in term["courses"]
    )


def test_retired_code_variants_are_removed_but_other_unknown_codes_still_need_review():
    request = dict(
        branch="eee",
        current_semester=2,
        completed_courses=DATA["common"],
        allow_unconfirmed=True,
    )
    assert prepare(dict(request, selected_electives=[" phil  f211 "]))
    with pytest.raises(InputError, match="outside the requested image scope"):
        prepare(dict(request, selected_electives=["FAKE F999"]))
