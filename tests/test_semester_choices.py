import pytest
from backend.services.scoped_planner import curriculum_response, prepare, InputError
from backend.services.scoped_api import plan_payload
from backend.verification import verify_plan


def req(branch="cse", **extra):
    return dict(
        branch=branch,
        current_semester=4,
        target_semester=8,
        max_credits=25,
        completed_courses=curriculum_response(branch)[
            "reference_completed_by_semester"
        ]["4"],
        allow_unconfirmed=True,
        **extra
    )


@pytest.mark.parametrize("branch", ["cse", "eee", "ece", "e_and_i"])
@pytest.mark.parametrize("solver", ["csp", "astar"])
def test_huel_del_and_opel_choices_are_honoured_for_all_branches(branch, solver):
    discipline = "BITS F415" if branch == "ece" else "BITS F312"
    pins = {"HSS F221": 5, discipline: 5, "ECON F212": 5}
    result = plan_payload(req(branch, solver=solver, semester_assignments=pins))
    assert result["verification_valid"], result["message"]
    actual = {
        c["code"]: int(term)
        for term, rows in result["semesters"].items()
        for c in rows["courses"]
    }
    assert all(actual[c] == term for c, term in pins.items())
    for term, rows in result["semesters"].items():
        for c in rows["courses"]:
            if c["code"] in pins:
                assert c["assigned_semester"] == pins[c["code"]]


@pytest.mark.parametrize(
    "pins",
    [
        {"HSS F221": 4},
        {"HSS F221": 9},
        {"HSS F221": True},
        {"CS F211": 5},
        {"FIN F315": 6},
        {"FAKE F999": 5},
    ],
)
def test_bad_semester_choices_are_rejected(pins):
    with pytest.raises(InputError):
        prepare(req(semester_assignments=pins))


def test_independent_verifier_rejects_ignoring_a_semester_choice():
    request = req(solver="csp", semester_assignments={"HSS F221": 5})
    result = plan_payload(request)
    assignment = {
        c["code"]: int(term)
        for term, rows in result["semesters"].items()
        for c in rows["courses"]
    }
    assignment["HSS F221"] = 6
    assert not verify_plan(prepare(request)["problem"], assignment).valid


def test_infeasible_target_has_actionable_feedback_instead_of_an_empty_schedule():
    request = req()
    request["target_semester"] = 7
    result = plan_payload(request)
    assert not result["verification_valid"]
    assert result["planning_feedback"]
    assert any("BITS F421T" in reason for reason in result["planning_feedback"])


def test_generation_retry_is_honest_and_disabled_for_pure_solver_comparisons(
    monkeypatch,
):
    import backend.services.scoped_api as api
    from backend.services.planning_service import PlanResponse

    original = api.make_plan
    calls = []

    def failing_astar(*args, **kwargs):
        calls.append(kwargs["solver"])
        if kwargs["solver"] == "astar":
            return PlanResponse(
                status="NO_PLAN",
                solver="astar",
                message="No bounded plan",
                problem=kwargs["problem_override"],
                stats={"time_s": 0.1, "complete_search": False},
            )
        return original(*args, **kwargs)

    monkeypatch.setattr(api, "make_plan", failing_astar)
    result = api.plan_payload(req(solver="astar", allow_solver_fallback=True))
    assert result["verification_valid"] and result["solver"] == "csp"
    assert result["requested_solver"] == "astar"
    assert calls == ["astar", "astar", "csp"]
    assert len(result["stats"]["search_attempts"]) == 2
    calls.clear()
    result = api.plan_payload(req(solver="astar", allow_solver_fallback=False))
    assert not result["verification_valid"]
    assert calls == ["astar"]


def test_explicit_move_updates_a_pinned_course_preference_and_reverifies_every_course():
    from backend.services.scoped_api import edit_payload

    request = req(solver="csp", semester_assignments={"HSS F221": 5})
    result = plan_payload(request)
    assignment = {
        c["code"]: int(term)
        for term, rows in result["semesters"].items()
        for c in rows["courses"]
    }
    edited = edit_payload(
        dict(
            plan=request,
            assignment=assignment,
            move={"course": "HSS F221", "target_semester": 7},
        )
    )
    assert edited["verification_valid"]
    assert edited["request_snapshot"]["semester_assignments"]["HSS F221"] == 7
    assert request["semester_assignments"]["HSS F221"] == 5
