"""Screenshot-scoped curriculum, timetable evidence and deterministic elective recommendations.

This module never infers an offering from a course number. Observations come from
exact codes in the teaching portions of the two user timetables. Bulletin fallback
and individual confirmations are explicit, traceable planning assumptions.
"""

from __future__ import annotations
import copy, json, math, hashlib, re
from pathlib import Path
from backend.csp.model import Problem, extract_formula_courses

DATA_PATH = (
    Path(__file__).resolve().parents[2] / "data/curriculum/scoped_catalogue.json"
)
DATA = json.loads(DATA_PATH.read_text(encoding="utf-8"))
RULES_REVISION = "2026-11-18-minor-stage-fit-r16"
CATALOGUE_SIGNATURE = hashlib.sha256(
    DATA_PATH.read_bytes() + RULES_REVISION.encode()
).hexdigest()
BRANCHES = DATA["branches"]
MINORS = {m["id"]: m for m in DATA["minors"]}
ALIASES = {"PHYS F111": "PHY F111", "PHYS F112": "PHY F110"}


class InputError(ValueError):
    def __init__(self, message, issues=None):
        super().__init__(message)
        self.issues = issues or []


def _choose(group, branch, done, selected, catalogue):
    prefix = {"cse": "CS", "eee": "EEE", "ece": "ECE", "e_and_i": "INSTR"}[branch]
    return min(
        group,
        key=lambda c: (
            c not in done,
            c not in selected,
            not bool(catalogue[c]["offered_terms"]),
            not c.startswith(prefix + " "),
            c,
        ),
    )


def catalogue_for(branch, minor=None):
    if branch not in BRANCHES:
        raise InputError("Choose one of the four supported branches.")
    if minor and minor not in MINORS:
        raise InputError("This minor is outside the supplied screenshots.")
    if minor and branch in MINORS[minor]["excluded_branches"]:
        raise InputError(
            "Computing and Intelligence is restricted to non-CSE students."
        )
    catalogue = copy.deepcopy(DATA["courses"])
    b = BRANCHES[branch]
    common = set(DATA["common"] + DATA["institutional"])
    for code, c in catalogue.items():
        if code in common:
            category = "Institutional Core"
        elif code in b["core"] or any(
            code in group for group in b["alternative_core_groups"]
        ):
            category = "Discipline Core"
        elif code in b["electives"]:
            category = "Discipline Elective"
        elif c.get("kind") == "humanities":
            category = "Humanities Elective"
        elif c.get("kind") == "general_awareness":
            category = "General Awareness"
        elif c.get("kind") == "capstone":
            category = "Capstone"
        else:
            category = "Open Elective"
        c["cdc_branches"] = [
            name
            for name, branch_data in BRANCHES.items()
            if code in branch_data["core"]
            or any(code in group for group in branch_data["alternative_core_groups"])
        ]
        c["foreign_cdc"] = bool(c["cdc_branches"] and branch not in c["cdc_branches"])
        c["manual_open_only"] = bool(
            c["foreign_cdc"] and category != "Discipline Elective"
        )
        c["category"] = category
        c["recommended_semester"] = b["patterns"].get(
            code, c.get("recommended_semester")
        )
        c["prerequisites"] = c.get("formula")
    catalogue["ECON F211"]["recommended_semester"] = 4
    catalogue["MGTS F211"]["recommended_semester"] = 4
    # The legacy KB contains cross-listed prerequisites under another programme
    # prefix. Resolve only an identical core suffix, title and units to this branch.
    prefix = {"cse": "CS", "eee": "EEE", "ece": "ECE", "e_and_i": "INSTR"}[branch]

    def normalize_formula(formula, changes):
        if not formula:
            return
        if formula.get("kind") == "leaf":
            previous = formula["course"]
            if previous in catalogue and previous.split()[0] in (
                "CS",
                "EEE",
                "ECE",
                "INSTR",
            ):
                candidate = prefix + " " + previous.split()[1]
                if candidate != previous and candidate in b["core"]:
                    left, right = catalogue[previous], catalogue[candidate]
                    title = lambda value: re.sub(
                        r"[^a-z0-9]", "", value.lower().replace("&", "and")
                    )
                    if left["credits"] == right["credits"] and title(
                        left["title"]
                    ) == title(right["title"]):
                        formula["course"] = candidate
                        changes.append(
                            {
                                "from": previous,
                                "to": candidate,
                                "basis": "Same core suffix, title and units in the supplied programme images",
                            }
                        )
        for child in formula.get("items", []):
            normalize_formula(child, changes)

    for course in catalogue.values():
        changes = []
        normalize_formula(course.get("formula"), changes)
        course["prerequisite_normalizations"] = changes
        course["prerequisites"] = course.get("formula")
    m = copy.deepcopy(MINORS.get(minor))
    if m:
        core = set(m["core"]) | {c for group in m["core_alternatives"] for c in group}
        m["courses"] = [
            {
                **catalogue[c],
                "degree_category": catalogue[c]["category"],
                "category": "Minor Core" if c in core else "Minor Elective",
            }
            for c in list(
                dict.fromkeys(
                    [
                        *m["core"],
                        *[c for g in m["core_alternatives"] for c in g],
                        *m["electives"],
                    ]
                )
            )
        ]
        fixed_units = sum(catalogue[c]["credits"] for c in m["core"])
        m["required_core_courses"] = len(m["core"]) + len(m["core_alternatives"])
        m["required_core_credits_min"] = fixed_units + sum(
            min(catalogue[c]["credits"] for c in g) for g in m["core_alternatives"]
        )
        m["required_core_credits_max"] = fixed_units + sum(
            max(catalogue[c]["credits"] for c in g) for g in m["core_alternatives"]
        )
        m["minimum_electives_needed"] = max(
            2, m["minimum_courses"] - m["required_core_courses"]
        )
        m["minimum_elective_credits_needed"] = max(
            6, m["minimum_credits"] - m["required_core_credits_max"]
        )
        m["structure"] = (
            "Source: supplied minor image. Core alternatives are one-of groups. At least two elective courses / six elective units are required; mandatory-major overlap is capped at two courses / six units; at most one project counts toward the minor."
        )
    return catalogue, m


def curriculum_response(branch, minor=None):
    cat, m = catalogue_for(branch, minor)
    branch_data = BRANCHES[branch]
    reference_codes = set(DATA["common"] + DATA["institutional"] + branch_data["core"])
    reference_codes.add("ECON F211")
    for group in branch_data["alternative_core_groups"]:
        reference_codes.add(_choose(group, branch, set(), set(), cat))
    reference = {
        str(semester): sorted(
            c
            for c in reference_codes
            if 1 <= (cat[c].get("recommended_semester") or 99) <= semester
        )
        for semester in range(9)
    }
    return {
        "app_revision": "2026.11.18-r17",
        "reference_completed_by_semester": reference,
        "catalogue_signature": CATALOGUE_SIGNATURE,
        "branch": branch,
        "all_courses": list(cat.values()),
        "first_year_common": [cat[c] for c in DATA["common"]],
        "institutional_courses": [cat[c] for c in DATA["institutional"]]
        + [cat[c] for c in ("ECON F211", "MGTS F211")],
        "discipline_cores": [
            cat[c] for c in cat if cat[c]["category"] == "Discipline Core"
        ],
        "discipline_electives": [cat[c] for c in BRANCHES[branch]["electives"]],
        "humanities_electives": [
            c for c in cat.values() if c["category"] == "Humanities Elective"
        ],
        "open_electives": [
            c
            for c in cat.values()
            if c["category"]
            in ("Open Elective", "Discipline Elective", "Humanities Elective")
        ],
        "degree_core_summary": {
            "course_count": len(BRANCHES[branch]["core"])
            + len(BRANCHES[branch]["alternative_core_groups"]),
            "credits_min": sum(cat[c]["credits"] for c in BRANCHES[branch]["core"])
            + sum(
                min(cat[c]["credits"] for c in g)
                for g in BRANCHES[branch]["alternative_core_groups"]
            ),
            "credits_max": sum(cat[c]["credits"] for c in BRANCHES[branch]["core"])
            + sum(
                max(cat[c]["credits"] for c in g)
                for g in BRANCHES[branch]["alternative_core_groups"]
            ),
        },
        "project_courses": [c for c in cat.values() if c.get("project_type")],
        "minors": [
            {k: m[k] for k in ("id", "name", "excluded_branches")}
            for m in MINORS.values()
        ],
        "selected_minor": m,
        "sources": DATA["sources"],
        "scope": DATA["scope"],
        "elective_pattern": BRANCHES[branch]["elective_pattern"],
        "elective_requirements": {
            "humanities": {"courses": 3, "credits": 9},
            "discipline": {"courses": 4, "credits": 12},
            "open": {"courses": 5, "credits": 15},
        },
        "patterns": {
            str(s): [
                cat[c]
                for c in cat
                if cat[c].get("recommended_semester") == s
                and cat[c]["category"]
                in ("Institutional Core", "Discipline Core", "General Awareness")
            ]
            for s in range(1, 9)
        },
        "availability_counts": {
            status: sum(c["offering_status"] == status for c in cat.values())
            for status in ("odd", "even", "both", "unconfirmed")
        },
    }


def normalize_request(req):
    if not isinstance(req, dict):
        raise InputError("Expected a JSON object.")
    req = dict(req)

    def retired(code):
        return isinstance(code, str) and re.sub(r"\s+", "", code).upper() == "PHILF211"

    # User-requested removal of this legacy, out-of-scope course from saved inputs.
    for key in (
        "completed_courses",
        "selected_electives",
        "excluded_courses",
        "minor_core_choices",
    ):
        if isinstance(req.get(key), list):
            req[key] = [code for code in req[key] if not retired(code)]
    for key in (
        "offering_overrides",
        "project_allocations",
        "elective_allocations",
        "semester_assignments",
    ):
        if isinstance(req.get(key), dict):
            req[key] = {
                code: value for code, value in req[key].items() if not retired(code)
            }
    result = dict(req)
    for key, default, allowed in [
        ("branch", "cse", tuple(BRANCHES)),
        ("degree_type", "single", ("single",)),
        ("solver", "csp", ("csp", "astar")),
        (
            "heuristic",
            "composite",
            ("composite", "credit_bound", "critical_path", "learned"),
        ),
        (
            "project_route",
            "thesis",
            ("", "thesis", "thesis_coursework", "practice_school"),
        ),
    ]:
        value = req.get(key, default)
        if not isinstance(value, str) or value not in allowed:
            raise InputError(
                f"Invalid {key}. Dual-degree planning is outside the four supplied single-degree patterns."
                if key == "degree_type"
                else f"Invalid {key}."
            )
        result[key] = value
    for key, default, minimum, maximum in [
        ("current_semester", 0, 0, 7),
        ("target_semester", 8, 1, 8),
        ("max_credits", 22, 14, 25),
    ]:
        value = req.get(key, default)
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or not minimum <= value <= maximum
        ):
            raise InputError(f"{key} must be an integer from {minimum} to {maximum}.")
        result[key] = value
    if result["target_semester"] <= result["current_semester"]:
        raise InputError("Target semester must be after the last finished semester.")
    placement = req.get("ps2_semester")
    if placement is not None and (
        type(placement) is not int or placement not in (7, 8)
    ):
        raise InputError("PS-II semester must be 7 or 8.")
    if (
        placement is not None
        and result["project_route"] == "practice_school"
        and not result["current_semester"] < placement <= result["target_semester"]
    ):
        raise InputError(
            "PS-II must be in a future semester within the graduation target."
        )
    result["ps2_semester"] = placement
    for key in ("completed_courses", "selected_electives", "excluded_courses"):
        values = req.get(key, [])
        if (
            not isinstance(values, list)
            or len(values) > 1000
            or any(not isinstance(c, str) for c in values)
        ):
            raise InputError(f"{key} must be a list of course codes.")
        clean = list(dict.fromkeys(ALIASES.get(c.strip(), c.strip()) for c in values))
        result[key] = sorted(clean) if key == "excluded_courses" else clean
    for key in (
        "auto_fill",
        "bulletin_fallback",
        "allow_unconfirmed",
        "allow_solver_fallback",
    ):
        if not isinstance(req.get(key, key == "auto_fill"), bool):
            raise InputError(f"{key} must be true or false.")
        result[key] = req.get(key, key == "auto_fill")
    minor = req.get("minor") or None
    if minor is not None and not isinstance(minor, str):
        raise InputError("Minor must be a catalogue identifier.")
    result["minor"] = minor
    overrides = req.get("offering_overrides", {})
    if not isinstance(overrides, dict) or any(
        code not in DATA["courses"] or value not in ("odd", "even", "both")
        for code, value in overrides.items()
    ):
        raise InputError(
            "Offering confirmations must use scoped course codes and odd, even or both."
        )
    result["offering_overrides"] = dict(overrides)
    allocations = req.get("project_allocations", {})
    if not isinstance(allocations, dict) or any(
        c not in DATA["courses"]
        or not DATA["courses"][c].get("project_type")
        or value not in ("discipline", "open")
        for c, value in allocations.items()
    ):
        raise InputError(
            "Project allocations must use scoped project codes and discipline or open."
        )
    result["project_allocations"] = dict(allocations)
    elective_allocations = req.get("elective_allocations", {})
    if not isinstance(elective_allocations, dict) or any(
        c not in DATA["courses"] or value not in ("humanities", "discipline", "open")
        for c, value in elective_allocations.items()
    ):
        raise InputError(
            "Elective allocations must use scoped course codes and humanities, discipline or open."
        )
    result["elective_allocations"] = dict(elective_allocations)
    pins = req.get("semester_assignments", {})
    if not isinstance(pins, dict) or any(
        code not in DATA["courses"]
        or type(term) is not int
        or not result["current_semester"] < term <= result["target_semester"]
        for code, term in pins.items()
    ):
        raise InputError(
            "Elective semester choices must name scoped courses and future semesters within your target."
        )
    result["semester_assignments"] = dict(pins)
    core_choices = req.get("minor_core_choices", [])
    groups = MINORS[result["minor"]]["core_alternatives"] if result["minor"] else []
    if (
        not isinstance(core_choices, list)
        or any(
            not isinstance(c, str) or not any(c in g for g in groups)
            for c in core_choices
        )
        or any(len(set(core_choices) & set(g)) > 1 for g in groups)
    ):
        raise InputError(
            "Choose at most one valid course per selected minor core alternative group."
        )
    result["minor_core_choices"] = sorted(set(core_choices))
    return result


def _minor_assessment(m, known, major, cat):
    if not m:
        return None
    candidates = (
        set(m["core"])
        | {c for g in m["core_alternatives"] for c in g}
        | set(m["electives"])
    )
    counted = known & candidates
    # Equivalent alternatives count once; prefer already mandatory major variants.
    for group in m["elective_alternatives"] + m["core_alternatives"]:
        taken = sorted(counted & set(group), key=lambda c: (c not in major, c))
        counted -= set(taken[1:])
    issues = []
    for c in m["core"]:
        if c not in counted:
            issues.append(f"Minor core missing: {c}.")
    for g in m["core_alternatives"]:
        if not counted & set(g):
            issues.append("Minor needs one of: " + ", ".join(g) + ".")
    overlap = counted & major
    if len(overlap) > 2 or sum(cat[c]["credits"] for c in overlap) > 6:
        # Surplus overlapping electives need not be allocated to the minor.
        fixed = set(m["core"]) | {
            c for g in m["core_alternatives"] for c in counted & set(g)
        }
        removable = sorted((overlap - fixed), key=lambda c: (-cat[c]["credits"], c))
        while removable and (
            len(overlap) > 2 or sum(cat[c]["credits"] for c in overlap) > 6
        ):
            c = removable.pop(0)
            counted.remove(c)
            overlap.remove(c)
    projects = sorted(c for c in counted if bool(cat[c].get("project_type")))
    counted -= set(projects[1:])
    core_pool = set(m["core"]) | {c for g in m["core_alternatives"] for c in g}
    electives = counted - core_pool
    credits = sum(cat[c]["credits"] for c in counted)
    if len(counted) < m["minimum_courses"] or credits < m["minimum_credits"]:
        issues.append(
            f"Minor needs {m['minimum_courses']} courses / {m['minimum_credits']} units; currently {len(counted)} / {credits}."
        )
    if len(electives) < 2 or sum(cat[c]["credits"] for c in electives) < 6:
        issues.append(
            "Minor needs at least two elective courses and six elective units."
        )
    if len(overlap) > 2 or sum(cat[c]["credits"] for c in overlap) > 6:
        issues.append("Minor mandatory-major overlap exceeds two courses / six units.")
    return {
        "name": m["name"],
        "counted_courses": sorted(counted),
        "count": len(counted),
        "credits": credits,
        "major_overlap": sorted(overlap),
        "issues": issues,
        "coursework_met": not issues,
        "gpa_requirement": 4.5,
        "certificate_status": "Coursework check only; GPA >= 4.5 and declaration/approval still required.",
    }


def apply_del_overflow(cat, known, req):
    """Keep DEL until both minima are met, then count each extra course as OpEl."""
    for course in cat.values():
        course.setdefault("base_category", course["category"])
        if course["base_category"] == "Discipline Elective":
            course["category"] = "Discipline Elective"
        course["converted_to_open"] = False
    order = list(
        dict.fromkeys(
            req.get("completed_courses", [])
            + req.get("selected_electives", [])
            + list(req.get("semester_assignments", {}))
        )
    )
    priority = {code: index for index, code in enumerate(order)}
    candidates = sorted(
        (c for c in known if cat[c]["base_category"] == "Discipline Elective"),
        key=lambda c: (priority.get(c, len(order)), c),
    )
    count = credits = 0
    for code in candidates:
        if count >= 4 and credits >= 12:
            cat[code]["category"] = "Open Elective"
            cat[code]["converted_to_open"] = True
        else:
            count += 1
            credits += cat[code]["credits"]


def assessment(
    cat, known, completed, major, m, req, verified=False, assumptions=None, summer=None
):
    known = set(known)
    completed = set(completed)
    issues = []
    # Explicitly equivalent alternatives cannot generate duplicate degree credit.
    equivalences = [
        ["EEE F214", "ECE F214", "INSTR F214", "ECOM F214"],
        ["EEE F242", "ECE F242", "INSTR F242"],
        ["EEE F216", "ECE F216", "INSTR F216"],
        ["EEE F423", "ECE F423", "INSTR F423"],
        ["ME F221", "MF F221"],
        ["MATH F212", "ME F344"],
    ]
    for group in equivalences:
        taken = sorted(known & set(group), key=lambda c: (c not in major, c))
        duplicates = set(taken[1:])
        known -= duplicates
        completed -= duplicates
        if duplicates:
            issues.append(
                "Equivalent variants cannot both earn degree credit: "
                + ", ".join(taken)
                + "."
            )
    apply_del_overflow(cat, known, req)
    common = set(DATA["common"] + DATA["institutional"])
    missing = sorted(major - known)
    if missing:
        issues.append("Required core courses missing: " + ", ".join(missing))

    def entries(category):
        return {c for c in known if cat[c]["category"] == category}

    pools = {
        name: entries(name)
        for name in (
            "Humanities Elective",
            "Discipline Elective",
            "Open Elective",
            "General Awareness",
        )
    }
    if not pools["General Awareness"]:
        issues.append("Choose Principles of Economics or Principles of Management.")
    # Only one general-awareness course is consumed there; a second may count as open.
    if len(pools["General Awareness"]) > 1:
        pools["Open Elective"].update(sorted(pools["General Awareness"])[1:])
    project_checks = []
    del_projects = {
        c for c in pools["Discipline Elective"] if bool(cat[c].get("project_type"))
    }
    open_projects = {
        c for c in pools["Open Elective"] if bool(cat[c].get("project_type"))
    }
    if len(del_projects) > 3:
        project_checks.append(
            "At most three project courses may count as discipline electives."
        )
    if len(open_projects) > 3:
        project_checks.append(
            "At most three project courses may count as open electives."
        )
    human_projects = {
        c for c in pools["Humanities Elective"] if cat[c].get("project_type")
    }
    if len(del_projects | open_projects | human_projects) > 5:
        project_checks.append(
            "At most five project courses may count toward all electives."
        )
    for kind, limit in [("study", 1), ("laboratory", 2), ("design", 2), ("special", 1)]:
        if sum(cat[c].get("project_type") == kind for c in del_projects) > limit:
            project_checks.append(
                f"Discipline projects: maximum {limit} {kind} course(s)."
            )
    issues += project_checks
    categories = {}
    for category, credits, count in [
        ("Humanities Elective", 9, 3),
        ("Discipline Elective", 12, 4),
        ("Open Elective", 15, 5),
    ]:
        taken = pools[category]
        units = sum(cat[c]["credits"] for c in taken)
        categories[category] = {
            "credits": units,
            "credit_minimum": credits,
            "courses": len(taken),
            "course_minimum": count,
            "course_codes": sorted(taken),
        }
        if units < credits or len(taken) < count:
            issues.append(
                f"{category}: {units}/{credits} units, {len(taken)}/{count} courses."
            )
    coursework = {c for c in known if cat[c].get("kind") != "capstone"}
    coursework_credits = sum(cat[c]["credits"] for c in coursework)
    total = sum(cat[c]["credits"] for c in known)
    for value, minimum, label in [
        (coursework_credits, 129, "coursework units"),
        (len(coursework), 41, "coursework courses"),
        (total, 144, "total units"),
        (len(known), 42, "total courses"),
    ]:
        if value < minimum:
            issues.append(f"{label}: {value}/{minimum}.")
    route = req["project_route"]
    if not route:
        issues.append("Choose a thesis or Practice School route.")
    elif route == "practice_school":
        if not {"BITS F221", "BITS F412"} <= known:
            issues.append("Practice School I and II are required for the PS route.")
    elif "BITS F421T" not in known:
        issues.append("Thesis is required for this route.")
    minor = _minor_assessment(m, known, major, cat)
    if minor:
        issues += minor["issues"]
    completed_units = sum(cat[c]["credits"] for c in completed)
    capacity = (
        max(0, req["target_semester"] - req["current_semester"]) * req["max_credits"]
    )
    remaining = max(0, 144 - completed_units - (5 if summer else 0))
    if capacity < remaining:
        issues.append(
            f"Only {capacity} regular-semester units fit before the target; at least {remaining} remain after planned summer units."
        )
    met = not issues
    if not verified:
        issues.append("No independently verified schedule for these inputs.")
    return {
        "audit_version": 4,
        "degree_type": "single",
        "target_semester": req["target_semester"],
        "max_semesters_cap": 8,
        "total_credits_required": 144,
        "completed_credits": completed_units,
        "planned_credits": total - completed_units,
        "total_credits_planned": total,
        "credit_deficit": max(0, 144 - total),
        "coursework_credits": coursework_credits,
        "coursework_count": len(coursework),
        "total_course_count": len(known),
        "verification_valid": verified,
        "verification_status": "Verified" if verified else "Not verified",
        "requirements_met": met,
        "is_eligible_for_graduation": bool(met and verified and not assumptions),
        "graduation_assessment": (
            (
                "Encoded degree requirements met"
                if not assumptions
                else "Requirements planned with explicit offering assumptions"
            )
            if met and verified
            else "Graduation requirements not yet met"
        ),
        "blockers": issues,
        "categories": categories,
        "minor": minor,
        "offering_assumptions": assumptions or [],
        "project_issues": project_checks,
        "remaining_credit_capacity": capacity,
        "remaining_credits_required": remaining,
        "capacity_possible": capacity >= remaining,
        "earliest_credit_bound": req["current_semester"]
        + math.ceil(remaining / req["max_credits"]),
        "audit_source": "Screenshot-scoped bulletin rules; Hyderabad odd 2026–27 and even 2024–25 timetable snapshots. Repeated parity is a planning projection, not future registration confirmation. GPA, declaration and campus approval remain external.",
    }


def prepare(req):
    req = normalize_request(req)
    cat, m = catalogue_for(req["branch"], req["minor"])
    b = BRANCHES[req["branch"]]
    for code, value in req["elective_allocations"].items():
        original = cat[code]["category"]
        if original in (
            "Institutional Core",
            "Discipline Core",
            "General Awareness",
            "Capstone",
        ):
            raise InputError(
                "A required core or route course cannot be reclassified as an elective.",
                [code],
            )
        if value == "discipline" and code not in b["electives"]:
            raise InputError(
                "This course is not in the selected branch's approved DEL list.", [code]
            )
        if value == "humanities" and cat[code].get("kind") != "humanities":
            raise InputError(
                "This course is not in the supplied humanities pool.", [code]
            )
        cat[code]["category"] = {
            "humanities": "Humanities Elective",
            "discipline": "Discipline Elective",
            "open": "Open Elective",
        }[value]
    for code, value in req["project_allocations"].items():
        if value == "discipline" and cat[code].get("project_branch") != req["branch"]:
            raise InputError(
                "Discipline project allocations must be within your own branch; allied-branch approvals are not encoded."
            )
        cat[code]["category"] = (
            "Discipline Elective" if value == "discipline" else "Open Elective"
        )
    if req["project_route"] == "practice_school" and req["current_semester"] >= 5 and "BITS F221" not in req["completed_courses"]:
        req["completed_courses"].append("BITS F221")
    done = set(req["completed_courses"])
    selected = set(req["selected_electives"]) | set(req["semester_assignments"])
    excluded = set(req["excluded_courses"])
    unknown = (done | selected | excluded) - cat.keys()
    if unknown:
        raise InputError(
            "Some saved courses are outside the requested image scope. Remove them or import a compatible transcript.",
            sorted(unknown),
        )
    if req["current_semester"] == 0 and done:
        raise InputError(
            "A nonempty transcript needs a last finished semester of at least 1."
        )
    major = set(DATA["common"] + DATA["institutional"] + b["core"])
    choices = []
    for group in b["alternative_core_groups"]:
        c = _choose(group, req["branch"], done, selected, cat)
        major.add(c)
        choices.append({"group": group, "chosen": c})
    # Confirmed overrides outrank observations; source fallback only affects mandatory core patterns.
    assumptions = []
    for code, c in cat.items():
        terms = c["offered_terms"][:]
        if code in req["offering_overrides"]:
            value = req["offering_overrides"][code]
            terms = ["odd", "even"] if value == "both" else [value]
            c["offering_basis"] = "User-confirmed offering"
        elif not terms and req["allow_unconfirmed"]:
            terms = ["odd", "even"]
            c["offering_basis"] = (
                "Planning assumption: unlisted course allowed in either semester"
            )
        elif (
            not terms
            and req["bulletin_fallback"]
            and c.get("recommended_semester")
            and code in major
        ):
            terms = ["odd" if c["recommended_semester"] % 2 else "even"]
            c["offering_basis"] = "Bulletin reference fallback"
        else:
            c["offering_basis"] = (
                "Uploaded teaching timetable"
                if terms
                else "Unconfirmed in both uploaded timetables"
            )
        stage = 4 if c["category"] == "General Awareness" else c.get("recommended_semester")
        if stage and stage > req["current_semester"] and c["category"] in ("Institutional Core", "Discipline Core", "General Awareness"):
            c["fixed_pattern_semester"] = stage
            parity = "odd" if stage % 2 else "even"
            if parity not in terms:
                terms = [parity]
                c["offering_basis"] = "Image programme structure assumption: fixed core semester"
        if code in ("CS F407", "BITS F232"):
            terms = ["odd"]
            c["offering_basis"] = "User-required offering: semester 5 or 7"
        c["effective_terms"] = terms
    for code, term in req["semester_assignments"].items():
        course = cat[code]
        if code in done:
            raise InputError(
                f"{code} is already passed. Remove its future semester choice."
            )
        if course["category"] not in (
            "Humanities Elective",
            "Discipline Elective",
            "Open Elective",
        ):
            raise InputError(
                f"{code} is a required degree course; only electives can be assigned here."
            )
        parity = "odd" if term % 2 else "even"
        if parity not in course["effective_terms"]:
            raise InputError(
                f"{code} cannot be placed in semester {term} under its recorded availability.",
                [
                    f"Allowed semesters: {', '.join(course['effective_terms']) or 'none confirmed'}; choose another semester or confirm an unlisted offering."
                ],
            )
    if selected & excluded:
        raise InputError(
            "A course cannot be both selected and excluded.",
            sorted(selected & excluded),
        )
    active = {
        s % 2 and "odd" or "even"
        for s in range(req["current_semester"] + 1, req["target_semester"] + 1)
    }

    def available(c):
        return bool(set(cat[c]["effective_terms"]) & active)

    if major & excluded:
        raise InputError(
            "Required degree cores cannot be excluded.", sorted(major & excluded)
        )
    chosen = major | selected | done
    general = sorted(done & {"ECON F211", "MGTS F211"})
    if not general:
        chosen.add(
            _choose(["ECON F211", "MGTS F211"], req["branch"], done, selected, cat)
        )
    minor_required = set()
    if m:
        chosen.update(m["core"])
        minor_required.update(m["core"])
        for group in m["core_alternatives"]:
            explicit = next((c for c in req["minor_core_choices"] if c in group), None)
            c = (
                _choose(group, req["branch"], done, selected, cat)
                if done & set(group) or not explicit
                else explicit
            )
            chosen.add(c)
            minor_required.add(c)
            choices.append({"group": group, "chosen": c})
    summer = None
    if req["project_route"] == "practice_school":
        chosen.update(["BITS F221", "BITS F412"])
        if "BITS F221" not in done:
            if req["current_semester"] > 4:
                raise InputError(
                    "PS-I is not recorded as completed. After semester 4, confirm the summer placement in the transcript or choose a thesis route."
                )
            if req["current_semester"] == 4 and not set(DATA["common"]) <= done:
                raise InputError(
                    "Complete the first-year foundation before the PS-I summer placement."
                )
            summer = {
                "code": "BITS F221",
                "title": "Practice School I",
                "credits": 5,
                "after_semester": 4,
                "source": "Programme summer pattern",
            }
    elif req["project_route"] in ("thesis", "thesis_coursework"):
        chosen.add("BITS F421T")
    if req["project_route"] == "thesis_coursework":
        cat["BITS F421T"]["credits"] = 9
        cat["BITS F421T"]["title"] = "Thesis with concurrent coursework"
    if cat["BITS F412"]["offered_terms"]:
        cat["BITS F412"][
            "offering_basis"
        ] = "Uploaded academic calendar + programme placement route"

    # Auto-fill a concrete recommendation set, then run the chosen search. It is not exhaustive elective optimization.
    def rank(code):
        c = cat[code]
        dependencies = extract_formula_courses(c.get("formula")) - chosen
        return (
            bool(dependencies),
            c.get("kind") == "project",
            len(dependencies),
            c["credits"] < 3,
            -len(c["effective_terms"]),
            abs(c["credits"] - 3),
            code,
        )

    auto = set()
    if req["auto_fill"]:
        if m:
            for _ in range(len(m["electives"])):
                status = _minor_assessment(m, chosen, major, cat)
                if not status["issues"]:
                    break
                pool = [
                    c
                    for c in m["electives"]
                    if c not in chosen and c not in excluded and available(c)
                ]
                # Avoid adding a second equivalent variant or surplus mandatory-major overlap.
                pool = [
                    c
                    for c in pool
                    if c not in major
                    and not any(
                        c in g and chosen & set(g) for g in m["elective_alternatives"]
                    )
                ]
                if not pool:
                    break
                c = min(pool, key=rank)
                chosen.add(c)
                auto.add(c)
        for category, units, count in [
            ("Humanities Elective", 9, 3),
            ("Discipline Elective", 12, 4),
            ("Open Elective", 15, 5),
        ]:
            while True:
                apply_del_overflow(cat, chosen, req)
                taken = [c for c in chosen if cat[c]["category"] == category]
                if (
                    len(taken) >= count
                    and sum(cat[c]["credits"] for c in taken) >= units
                ):
                    break
                pool = [
                    c
                    for c in cat
                    if c not in chosen
                    and c not in excluded
                    and cat[c]["category"] == category
                    and available(c)
                    and not cat[c].get("project_type")
                    and not cat[c].get("manual_open_only")
                ]
                if not pool:
                    break
                c = min(pool, key=rank)
                chosen.add(c)
                auto.add(c)
        while True:
            a = assessment(
                cat, chosen, done, major, m, req, verified=True, summer=summer
            )
            if (
                a["coursework_credits"] >= 129
                and a["coursework_count"] >= 41
                and a["total_credits_planned"] >= 144
                and a["total_course_count"] >= 42
            ):
                break
            pool = [
                c
                for c in cat
                if c not in chosen
                and c not in excluded
                and cat[c]["category"] == "Open Elective"
                and available(c)
                and not cat[c].get("project_type")
                and not cat[c].get("manual_open_only")
            ]
            if not pool:
                break
            c = min(pool, key=rank)
            chosen.add(c)
            auto.add(c)

    # Include prerequisite closure for the chosen recommendation set without treating missing codes as passed.
    def satisfy(formula):
        if not formula:
            return
        if formula["kind"] == "leaf":
            code = formula["course"]
            if code not in chosen:
                if code in excluded:
                    raise InputError(
                        "An excluded course is an encoded prerequisite for a chosen course.",
                        [code],
                    )
                if code not in cat:
                    raise InputError(
                        "An encoded prerequisite lies outside the image-scoped catalogue.",
                        [code],
                    )
                if cat[code].get("manual_open_only") and code not in minor_required:
                    raise InputError(
                        "This choice requires a CDC from another programme. Select it explicitly as an open elective or choose another course.",
                        [code],
                    )
                chosen.add(code)
                satisfy(cat[code].get("formula"))
        elif formula["kind"] == "and":
            for child in formula.get("items", []):
                satisfy(child)
        else:

            def cost(f):
                refs = extract_formula_courses(f)
                return (
                    not refs <= chosen,
                    len(refs - cat.keys()),
                    sum(not available(c) for c in refs if c in cat),
                    len(refs - chosen),
                    str(f),
                )

            options = formula.get("items", [])
            if options:
                satisfy(min(options, key=cost))

    for code in sorted(chosen.copy()):
        satisfy(cat[code].get("formula"))
    blocked = [
        {
            "code": c,
            "title": cat[c]["title"],
            "reason": (
                "Not offered in the remaining parity window"
                if cat[c]["effective_terms"]
                else "Not found in either teaching timetable"
            ),
            "evidence": cat[c]["offering_evidence"],
        }
        for c in sorted(chosen - done - ({"BITS F221"} if summer else set()))
        if not available(c)
    ]
    if blocked:
        raise InputError(
            "Required courses have no confirmed offering in this horizon. Review the catalogue, confirm an offering, or enable planning assumptions for unlisted courses.",
            blocked,
        )
    # Project choices and minor rules are assessed on the complete fixed candidate set, not silently relaxed.
    pre = assessment(cat, chosen, done, major, m, req, verified=True, summer=summer)
    if pre["project_issues"]:
        raise InputError(
            "Project allocation exceeds the supplied rules.", pre["project_issues"]
        )
    if req["auto_fill"] and pre["blockers"]:
        raise InputError(
            "The selected scope and confirmed offerings cannot satisfy every graduation requirement with these recommendations.",
            pre["blockers"],
        )
    for c in sorted(chosen - done):
        if cat[c]["offering_basis"] in (
            "User-confirmed offering",
            "Image programme structure assumption: fixed core semester",
            "Bulletin reference fallback",
            "Planning assumption: unlisted course allowed in either semester",
        ):
            assumptions.append(
                {
                    "code": c,
                    "basis": cat[c]["offering_basis"],
                    "terms": cat[c]["effective_terms"],
                }
            )
    model = {}
    for code in sorted(chosen):
        c = cat[code]
        terms = c["effective_terms"]
        parity = None if len(terms) == 2 else terms[0] if terms else "unavailable"
        model[code] = {
            "credits": c["credits"],
            "title": c["title"],
            "category": c["category"],
            "formula": c.get("formula"),
            "parity": parity,
            "recommended_semester": c.get("recommended_semester") or 9,
            "eligible_companion": "Elective" in c["category"],
        }
        # Treat the supplied programme pattern as a scheduling policy, not as
        # a prerequisite assertion. A fresh plan must not take year-three CDCs
        # in year one simply because the source has no prerequisite formula.
        if c["category"] in (
            "Institutional Core",
            "Discipline Core",
            "General Awareness",
        ) and c.get("recommended_semester"):
            model[code]["earliest_semester"] = c["recommended_semester"]
            model[code]["stage_basis"] = "Programme reference stage (planning policy)"
        if c.get("fixed_pattern_semester"):
            model[code]["earliest_semester"] = c["fixed_pattern_semester"]
            model[code]["latest_semester"] = c["fixed_pattern_semester"]
        elif req["current_semester"] == 0 and "Elective" in c["category"]:
            model[code]["earliest_semester"] = 3 if c["category"] == "Humanities Elective" or (m and (code in minor_required or code in m["electives"])) else 5
        if code in ("CS F407", "BITS F232"):
            model[code]["earliest_semester"] = 5
            model[code]["latest_semester"] = min(7, req["target_semester"])
        # Every chosen candidate is explicit; there are no optional variables to swamp A*.
        if code not in done:
            model[code]["category"] = "Required Course"
    for c in ("BITS F421T", "BITS F412"):
        if c in model:
            model[c].update(
                earliest_semester=7,
                latest_semester=req["target_semester"],
                must_be_last=c != "BITS F412" or not req.get("ps2_semester"),
                exclusive_semester=not (
                    c == "BITS F421T" and req["project_route"] == "thesis_coursework"
                ),
            )
    if "BITS F412" in model and req.get("ps2_semester"):
        model["BITS F412"].update(
            earliest_semester=req["ps2_semester"], latest_semester=req["ps2_semester"]
        )
    if "BITS F421T" in model and req["project_route"] == "thesis_coursework":
        model["BITS F421T"].update(
            companion_minimum=6, companion_maximum=9, companion_count=2
        )
    for code, term in req["semester_assignments"].items():
        model[code]["earliest_semester"] = term
        model[code]["latest_semester"] = term
    effective_done = done.copy()
    if summer:
        effective_done.add("BITS F221")
        for c in DATA["common"]:
            if c in model:
                model[c]["latest_semester"] = min(4, model[c].get("latest_semester", 4))
        if "BITS F412" in model:
            model["BITS F412"]["formula"] = {
                "kind": "and",
                "items": [
                    {"kind": "leaf", "course": c, "relation": "PRE"}
                    for c in DATA["common"]
                ],
            }
    # Forward chaining derives potential prerequisite reachability, never passed credit.
    # CO leaves are optimistic here; simultaneous feasibility stays with the solver.
    from types import SimpleNamespace
    from backend.logic.forward_chaining import compute_fixpoint_reachable, compute_category_credits
    def reach_formula(f):
        if not f: return None
        if f["kind"] == "leaf":
            return None if f.get("relation") == "CO" else {**f, "relation": "PRE"}
        return {"kind": f["kind"], "items": [reach_formula(x) for x in f["items"]]}
    closure_curriculum = SimpleNamespace(courses={code: SimpleNamespace(code=code,credits=info["credits"],category=cat[code]["category"],parsed_prerequisites=reach_formula(info.get("formula"))) for code,info in model.items()})
    reachable, passes, unlocks = compute_fixpoint_reachable(closure_curriculum, effective_done, set(model) | effective_done)
    unreachable = set(model) - reachable
    if unreachable:
        raise InputError("Required course dependencies cannot be reached from this transcript.", sorted(unreachable))
    closure_trace = {"passes": passes, "unlocked_by_pass": unlocks, "completed_category_credits": compute_category_credits(closure_curriculum, effective_done), "note": "Reachability is potential eligibility, not passed coursework; temporal and CO constraints are verified separately."}
    problem = Problem(
        courses=model,
        completed=effective_done,
        current_semester=req["current_semester"],
        target_semester=req["target_semester"],
        max_credits=req["max_credits"],
        category_minimums={},
        assume_out_of_scope_satisfied=False,
    )
    return {
        "request": req,
        "requirement_closure": closure_trace,
        "catalogue": cat,
        "minor": m,
        "major": major,
        "problem": problem,
        "auto_selected": sorted(auto),
        "assumptions": assumptions,
        "summer": summer,
        "choices": choices,
        "selected": chosen,
        "minor_required": minor_required,
    }
