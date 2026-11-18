"""Deterministic load improvement for an already verified scoped schedule.

Only strictly improving single-course moves are accepted. Every candidate is
checked by the independent verifier, including pins, programme stages, parity,
prerequisites, exclusive placements and thesis companions. This is a soft
presentation preference, not a new graduation requirement or an optimality claim.
"""
from time import perf_counter
from backend.verification import verify_plan
from backend.explanations.plan_explainer import explain_plan


def balance_schedule(problem, result):
    if result.status != "PLAN" or not result.verification.valid:
        return result
    start = perf_counter()
    assignment = dict(result.assignment)
    end = max(assignment.values(), default=problem.current_semester)
    reserved = {
        semester for code, semester in assignment.items()
        if problem.courses[code].get("exclusive_semester")
    }
    terms = [s for s in range(problem.current_semester + 1, end + 1) if s not in reserved]
    def loads_of(a):
        return {s: sum(problem.courses[c]["credits"] for c, t in a.items() if t == s) for s in terms}
    def score(loads):
        return (sum(v == 0 for v in loads.values()), sum(v * v for v in loads.values()))
    before = loads_of(assignment)
    moves = 0
    # Scores strictly decrease, and the bound keeps this optional step inexpensive.
    for _ in range(120):
        loads = loads_of(assignment)
        current = score(loads)
        choices = []
        for code, source in sorted(assignment.items()):
            if source not in loads:
                continue
            info = problem.courses[code]
            credits = info["credits"]
            for target in terms:
                if target == source or loads[target] + credits > problem.max_credits:
                    continue
                if not info.get("earliest_semester", 1) <= target <= info.get("latest_semester", end):
                    continue
                parity = info.get("parity")
                if parity in ("odd", "even") and (target % 2 == 1) != (parity == "odd"):
                    continue
                proposed = dict(loads)
                proposed[source] -= credits
                proposed[target] += credits
                cost = score(proposed)
                if cost < current:
                    choices.append((cost, code, target))
        accepted = False
        for _, code, target in sorted(choices):
            candidate = {**assignment, code: target}
            if verify_plan(problem, candidate).valid:
                assignment = candidate
                moves += 1
                accepted = True
                break
        if not accepted:
            break
    result.stats["load_balancing"] = {
        "method": "verified single-course load improvement",
        "moves": moves,
        "time_s": perf_counter() - start,
        "before": before,
        "after": loads_of(assignment),
    }
    if moves:
        result.assignment = assignment
        result.verification = verify_plan(problem, assignment)
        result.explanation = explain_plan(problem, assignment)
        result.semesters = {}
        for code, semester in sorted(assignment.items()):
            info = problem.courses[code]
            result.semesters.setdefault(semester, []).append({
                "code": code, "title": info.get("title", ""),
                "credits": info["credits"], "category": info.get("category", ""),
            })
        result.semesters = dict(sorted(result.semesters.items()))
    return result
