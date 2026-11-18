import pytest
from backend.services.scoped_api import plan_payload
from backend.services.scoped_planner import curriculum_response, InputError

@pytest.mark.parametrize('branch', ['cse','eee','ece','e_and_i'])
@pytest.mark.parametrize('solver', ['csp','astar'])
def test_none_can_generate(branch, solver):
    result = plan_payload(dict(branch=branch, solver=solver, current_semester=0, target_semester=8, max_credits=22, allow_unconfirmed=True, auto_fill=True))
    assert result['status'] == 'PLAN'
    assert result['verification_valid']
    assert 1 in result['semesters']

@pytest.mark.parametrize('branch', ['cse','eee','ece','e_and_i'])
@pytest.mark.parametrize('term', [7,8])
def test_explicit_ps2(branch,term):
    done = curriculum_response(branch)['reference_completed_by_semester']['4']
    result = plan_payload(dict(branch=branch, solver='csp', current_semester=4, target_semester=8, max_credits=25, completed_courses=done, project_route='practice_school', ps2_semester=term, allow_unconfirmed=True, auto_fill=True))
    assert result['status'] == 'PLAN'
    assert [c['code'] for c in result['semesters'][term]['courses']] == ['BITS F412']
    assert result['verification_valid']

@pytest.mark.parametrize('branch', ['cse','eee','ece','e_and_i'])
def test_seven_semesters_with_passed_electives(branch):
    done = curriculum_response(branch)['reference_completed_by_semester']['4']
    done += ['BITS F311','BITS F312','BITS F327','BITS F343']
    result = plan_payload(dict(branch=branch,solver='csp',current_semester=4,target_semester=7,max_credits=25,completed_courses=done,project_route='practice_school',ps2_semester=7,allow_unconfirmed=True,auto_fill=True))
    assert result['status'] == 'PLAN'
    assert set(result['semesters']) == {5,6,7}
    assert result['verification_valid']
