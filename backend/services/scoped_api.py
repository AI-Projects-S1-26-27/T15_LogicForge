"""REST adapter for the screenshot-scoped planning model."""

import math
from .scoped_planner import prepare, assessment, DATA, InputError, CATALOGUE_SIGNATURE
from .planning_service import make_plan
from backend.astar.features import extract_state_features
from backend.astar.heuristics import composite, learned_prediction
from backend.ml.predict import model_info


def plan_payload(request):
    state = prepare(request)
    req = state["request"]
    cat = state["catalogue"]
    problem = state["problem"]
    result = make_plan(
        req["branch"],
        req["completed_courses"],
        req["current_semester"],
        req["target_semester"],
        solver=req["solver"],
        heuristic=req["heuristic"],
        problem_override=problem,
        timeout_s=15.0,
        diagnose=False,
    )
    attempts = []
    if (
        req["solver"] == "astar"
        and result.status in ("NO_PLAN", "TIMEOUT")
        and req["allow_solver_fallback"]
    ):
        attempts.append({"solver": "astar", "status": result.status, **result.stats})
        result = make_plan(
            req["branch"],
            req["completed_courses"],
            req["current_semester"],
            req["target_semester"],
            solver="astar",
            heuristic=req["heuristic"],
            problem_override=problem,
            timeout_s=5.0,
            diagnose=False,
            astar_bundle_limit=100,
        )
        if result.status in ("NO_PLAN", "TIMEOUT"):
            attempts.append(
                {"solver": "astar", "status": result.status, **result.stats}
            )
            result = make_plan(
                req["branch"],
                req["completed_courses"],
                req["current_semester"],
                req["target_semester"],
                solver="csp",
                problem_override=problem,
                timeout_s=5.0,
                diagnose=False,
            )
            if result.status == "PLAN":
                result.message = "A* did not find a verified schedule; CSP found and independently verified this plan for the same inputs."
        result.stats["search_attempts"] = attempts
        result.stats["total_search_time_s"] = result.stats.get("time_s", 0) + sum(
            a.get("time_s", 0) for a in attempts
        )
    from .schedule_balance import balance_schedule

    result = balance_schedule(problem, result)
    payload = render_payload(state, result)
    if result.status == "NO_PLAN":
        import time
        from dataclasses import asdict
        from backend.explanations.infeasibility_analyzer import analyze, csp_oracle
        deadline = time.perf_counter() + 1.5
        oracle = csp_oracle(timeout_s=0.02)
        def bounded(problem):
            return oracle(problem) if time.perf_counter() < deadline else "TIMEOUT"
        payload["conflict_analysis"] = asdict(analyze(problem, bounded))
        payload["planning_feedback"] += payload["conflict_analysis"]["explanations"]
        analysis = payload["conflict_analysis"]
        payload["planning_feedback"].append("Conflict checked as subset-minimal." if analysis["status"] == "infeasible" and analysis["minimal"] else "Conflict diagnosis is incomplete within its time budget; minimality is not claimed.")
        payload["planning_feedback"] += [r["description"] + (" (verified individually)" if r["fixes_alone"] is True else " (not established as sufficient alone)") for r in analysis["relaxations"]]
    return payload


def render_payload(state, result):
    req = state["request"]
    cat = state["catalogue"]
    problem = state["problem"]
    minor = state["minor"]

    def minor_role(code):
        if code in state.get("minor_required", set()):
            return "Minor Core"
        if minor and code in minor["electives"]:
            return "Minor Elective"
        return None

    verified = bool(
        result.status == "PLAN" and result.verification and result.verification.valid
    )
    semesters = {}
    scheduled = set()
    if verified:
        for term, items in result.semesters.items():
            rows = []
            for row in items:
                c = cat[row["code"]]
                scheduled.add(row["code"])
                rows.append(
                    {
                        **row,
                        "placement_reasons": next((x.reasons for x in result.explanation.courses if x.course == row["code"]), []) if result.explanation else [],
                        "title": c["title"],
                        "category": c["category"],
                        "offering_basis": c["offering_basis"],
                        "offered_terms": c["effective_terms"],
                        "offering_status": c["offering_status"],
                        "recommended_semester": c.get("recommended_semester"),
                        "assigned_semester": req["semester_assignments"].get(
                            row["code"]
                        ),
                        "auto_selected": row["code"] in state["auto_selected"],
                        "minor_role": minor_role(row["code"]),
                        "cdc_branches": c["cdc_branches"],
                        "selection_reason": (
                            "Required degree core"
                            if row["code"] in state["major"]
                            else minor_role(row["code"])
                            or (
                                "Your elective selection"
                                if row["code"] in req["selected_electives"]
                                else "Suggested elective or prerequisite"
                            )
                        ),
                    }
                )
            semesters[term] = {
                "semester": term,
                "credits": sum(row["credits"] for row in rows),
                "courses": rows,
            }
        if state["summer"]:
            scheduled.add("BITS F221")
    known = set(req["completed_courses"]) | scheduled
    audit = assessment(
        cat,
        known,
        set(req["completed_courses"]),
        state["major"],
        state["minor"],
        req,
        verified,
        state["assumptions"],
        state["summer"],
    )
    if audit["blockers"]:
        audit["warning"] = " ".join(audit["blockers"][:3])
    history = {}
    grouped = set()
    for term in range(1, req["current_semester"] + 1):
        rows = [
            {**cat[c], "minor_role": minor_role(c)}
            for c in req["completed_courses"]
            if cat[c].get("recommended_semester") == term
        ]
        grouped.update(c["code"] for c in rows)
        history[term] = {
            "semester": term,
            "credits": sum(c["credits"] for c in rows),
            "courses": rows,
            "grouping": "Bulletin reference pattern; actual completion dates not recorded",
        }
    unassigned = [cat[c] for c in req["completed_courses"] if c not in grouped]
    if history and unassigned:
        history[req["current_semester"]]["unassigned_courses"] = unassigned
    finite = lambda n: n if math.isfinite(n) else None
    model = model_info()
    result.stats["heuristic_details"] = {
        "selected": req["heuristic"] if result.solver == "astar" else None,
        "model_available": model["available"],
        "model": model,
        "features": dict(
            zip(
                [
                    "Required credits",
                    "Required courses",
                    "Prerequisite chain",
                    "Parity-locked courses",
                    "Terms available",
                    "Unresolved alternatives",
                ],
                extract_state_features(problem, {}, req["current_semester"] + 1),
            )
        ),
        "learned_prediction": finite(
            learned_prediction(problem, {}, req["current_semester"] + 1)
        ),
        "used_estimate": finite(composite(problem, {}, req["current_semester"] + 1)),
        "composite_bound": finite(composite(problem, {}, req["current_semester"] + 1)),
    }
    if result.solver == "manual":
        result.stats["heuristic_details"] = None
    warnings = list(result.warnings)
    warnings.append("Image structure: future institutional cores and CDCs are fixed to their reference semesters. Conflicting timetable parity is recorded as a programme-structure planning assumption; backlogs remain flexible.")
    if result.stats.get("load_balancing", {}).get("moves"):
        warnings.append("Course loads were spread across available semesters after the solver run; every move was independently verified. Solver timing excludes this load-balancing step.")
    warnings.append(
        "Automatic electives are deterministic recommendations; neither solver searches every possible elective combination."
    )
    if state["assumptions"]:
        warnings.append(
            "This plan uses availability assumptions for unlisted courses or explicit confirmations. Inspect the offering assumptions before registration."
        )
    if state["summer"] and verified:
        warnings.append(
            "PS-I is planned as a separate five-unit summer placement, not regular-semester credit load."
        )
    traces = []
    if result.explanation:
        traces = [
            {
                "course": c.course,
                "semester": c.semester,
                "reasons": c.reasons,
                "text": c.text(),
            }
            for c in result.explanation.courses
        ]
    feedback = []
    if not verified:
        for code, domain in problem.initial_domains().items():
            if not domain:
                info = problem.courses[code]
                feedback.append(
                    f"{code} has no eligible semester between {problem.current_semester+1} and {problem.target_semester}; offering: {info.get('parity') or 'both'}, earliest semester: {info.get('earliest_semester',1)}."
                )
        remaining = sum(problem.courses[c]["credits"] for c in problem.variables)
        capacity = (
            problem.target_semester - problem.current_semester
        ) * problem.max_credits
        capacity -= sum(
            max(0, problem.max_credits - problem.courses[c]["credits"])
            for c in problem.variables
            if problem.courses[c].get("exclusive_semester")
        )
        if remaining > capacity:
            feedback.append(
                f"The remaining {remaining} units exceed the maximum {capacity} units available with this credit cap and reserved project semester."
            )
        if not feedback:
            feedback.append(
                "No verified schedule was found for this combination of selected courses, prerequisites, offerings and semester choices."
            )
        feedback.append(
            "Try a later graduation target, release fixed elective semesters, or review the credit cap and courses actually passed. The planner will not invent a valid schedule."
        )
    return {
        "catalogue_signature": CATALOGUE_SIGNATURE,
        "status": result.status,
        "solver": result.solver,
        "requested_solver": req["solver"],
        "planning_feedback": feedback,
        "message": result.message,
        "verification_valid": verified,
        "audit": audit,
        "semesters": semesters,
        "completed_by_sem": history,
        "stats": result.stats,
        "warnings": warnings,
        "explanation": traces,
        "auto_selected": state["auto_selected"],
        "effective_allocations": {
            code: {
                "Humanities Elective": "humanities",
                "Discipline Elective": "discipline",
                "Open Elective": "open",
            }[category]
            for category, values in audit["categories"].items()
            for code in values["course_codes"]
        },
        "converted_del_courses": sorted(
            code for code in known if cat[code].get("converted_to_open")
        ),
        "requirement_closure": state.get("requirement_closure"),
        "core_choices": state["choices"],
        "summer_activities": ([state["summer"]] if state["summer"] and verified else [{"code": "BITS F221", "title": "Practice School I (completed)", "credits": 5, "after_semester": 4, "completed": True}] if "BITS F221" in req["completed_courses"] and req["project_route"] == "practice_school" else []),
        "request_snapshot": req,
        "source_snapshots": DATA["sources"],
    }


def edit_payload(body):
    """Move or swap courses, then independently verify the entire assignment."""
    from backend.verification import verify_plan
    from backend.services.planning_service import PlanResponse

    if not isinstance(body, dict):
        raise InputError("Expected an edit request object.")
    state = prepare(body.get("plan"))
    problem = state["problem"]
    assignment = body.get("assignment")
    if not isinstance(assignment, dict) or set(assignment) != set(problem.variables):
        raise InputError(
            "The schedule no longer matches these plan inputs. Generate a fresh plan before editing."
        )
    if any(
        isinstance(term, bool) or not isinstance(term, int)
        for term in assignment.values()
    ):
        raise InputError("Each scheduled semester must be an integer.")
    before = verify_plan(problem, assignment)
    if not before.valid:
        raise InputError(
            "The starting schedule is not valid for these inputs.",
            [v.message for v in before.violations],
        )
    move = body.get("move")
    if not isinstance(move, dict):
        raise InputError("Choose a course and target semester.")
    code = move.get("course")
    target = move.get("target_semester")
    swap = move.get("swap_with") or None
    if code not in assignment:
        raise InputError("Only future scheduled courses can be moved.")
    if (
        isinstance(target, bool)
        or not isinstance(target, int)
        or not problem.current_semester < target <= problem.target_semester
    ):
        raise InputError("Choose a future semester within the graduation target.")
    if target == assignment[code]:
        raise InputError("Choose a different semester.")
    updated = dict(assignment)
    if swap:
        if swap == code or swap not in assignment or assignment[swap] != target:
            raise InputError("The swap course must belong to the target semester.")
        updated[swap] = assignment[code]
    updated[code] = target
    pins = dict(state["request"]["semester_assignments"])
    if code in pins:
        pins[code] = target
    if swap in pins:
        pins[swap] = assignment[code]
    if pins != state["request"]["semester_assignments"]:
        state = prepare({**state["request"], "semester_assignments": pins})
        problem = state["problem"]
    report = verify_plan(problem, updated)
    if not report.valid:
        raise InputError(
            "This change breaks the schedule. Your existing plan has been kept.",
            [v.message for v in report.violations],
        )
    terms = {}
    for c, term in sorted(updated.items()):
        info = problem.courses[c]
        terms.setdefault(term, []).append(
            {
                "code": c,
                "title": info["title"],
                "credits": info["credits"],
                "category": info["category"],
            }
        )
    result = PlanResponse(
        status="PLAN",
        solver="manual",
        message="Semester change applied; the entire schedule passed independent verification.",
        problem=problem,
        assignment=updated,
        semesters=terms,
        verification=report,
    )
    payload = render_payload(state, result)
    payload["edit"] = {
        "course": code,
        "from": assignment[code],
        "to": target,
        "swap_with": swap,
    }
    return payload
