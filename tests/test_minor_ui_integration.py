import pytest
from backend.services.scoped_planner import MINORS, catalogue_for, DATA
HUMANITIES_ELECTIVES = [c for c in DATA['courses'].values() if c.get('kind') == 'humanities']
def get_minor(mid, branch): return catalogue_for(branch, mid)[1]
from backend.services.problem_builder import build_problem_for_student
from backend.services.planning_service import make_plan


def test_minors_available_across_supported_branches():
    assert len(MINORS) == 5
    for branch in ('cse', 'ece', 'eee', 'e_and_i'):
        for minor in MINORS.values():
            if branch in minor['excluded_branches']:
                with pytest.raises(ValueError):
                    get_minor(minor['id'], branch)
            else:
                assert get_minor(minor['id'], branch)['courses']


def test_bulletin_humanities_codes_and_names():
    courses = {c['code']: c for c in HUMANITIES_ELECTIVES}
    assert len(courses) > 90
    assert courses['HSS F211']['title'] == 'Introduction to Arabic'
    assert courses['HSS F221']['title'] == 'Readings from Drama'
    assert courses['GS F241']['title'] == 'Creative Writing'


def test_selected_course_is_required_and_counts_toward_original_floor():
    base = build_problem_for_student('cse', [], 0)
    code = 'CS F407'
    problem = build_problem_for_student('cse', [], 0, required_courses=[code])
    assert 'NOT_TAKEN' not in problem.initial_domains()[code]
    category = base.courses[code]['category']
    assert problem.category_minimums[category] == max(0, base.category_minimums[category] - base.courses[code]['credits'])


def test_added_minor_course_is_scheduled_once():
    item = dict(code='AN F311', title='Principles of Aerodynamics', credits=3, category='Minor Core')
    base = build_problem_for_student('cse', [], 0)
    response = make_plan('cse', list(base.courses), 3, 8, required_courses=[item['code']], additional_courses=[item])
    assert response.status == 'PLAN'
    assert response.verification.valid
    assert sum(c['code'] == item['code'] for rows in response.semesters.values() for c in rows) == 1
