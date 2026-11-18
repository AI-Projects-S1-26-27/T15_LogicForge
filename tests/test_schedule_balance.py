import pytest
from backend.services.scoped_api import plan_payload
from backend.services.scoped_planner import curriculum_response, prepare
from backend.verification import verify_plan

@pytest.mark.parametrize('branch',['cse','eee','ece','e_and_i'])
@pytest.mark.parametrize('solver',['csp','astar'])
def test_none_balanced_and_complete(branch, solver):
    req=dict(branch=branch,solver=solver,current_semester=0,target_semester=8,max_credits=22,project_route='practice_school',ps2_semester=8,allow_unconfirmed=True)
    r=plan_payload(req)
    assert r['status']=='PLAN' and r['verification_valid'] and r['audit']['requirements_met']
    assert set(r['semesters'])==set(range(1,9))
    assert all(0 < t['credits'] <= 22 for t in r['semesters'].values())
    assert r['semesters'][8]['credits']==20
    stats=r['stats']['load_balancing']
    assert sum(v*v for v in stats['after'].values()) <= sum(v*v for v in stats['before'].values())

@pytest.mark.parametrize('term',[5,6,7])
def test_balancing_preserves_elective_pin_and_prerequisites(term):
    req=dict(branch='ece',solver='csp',current_semester=4,target_semester=8,max_credits=25,completed_courses=curriculum_response('ece')['reference_completed_by_semester']['4'],selected_electives=['HSS F221'],semester_assignments={'HSS F221':term},allow_unconfirmed=True)
    result=plan_payload(req)
    assert result['status']=='PLAN'
    a={c['code']:s for s,t in result['semesters'].items() for c in t['courses']}
    assert a['HSS F221']==term
    assert verify_plan(prepare(req)['problem'],a).valid
