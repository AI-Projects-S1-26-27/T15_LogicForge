import pytest
from backend.services.scoped_planner import MINORS
from backend.services.scoped_api import plan_payload
CASES=[(b,m) for b in ['cse','eee','ece','e_and_i'] for m,v in MINORS.items() if b not in v['excluded_branches']]
@pytest.mark.parametrize('branch,minor',CASES)
@pytest.mark.parametrize('target',[7,8])
@pytest.mark.parametrize('solver',['csp','astar'])
def test_minor_with_explicit_huel_del(branch,minor,target,solver):
 req=dict(branch=branch,minor=minor,solver=solver,current_semester=0,target_semester=target,max_credits=25,project_route='practice_school',ps2_semester=target,allow_unconfirmed=True,allow_solver_fallback=True)
 baseline=plan_payload(req)
 assert baseline['status']=='PLAN'
 selected=[code for category in ['Humanities Elective','Discipline Elective'] for code in baseline['audit']['categories'][category]['course_codes']]
 result=plan_payload({**req,'selected_electives':selected})
 assert result['status']=='PLAN' and result['verification_valid'] and result['audit']['requirements_met']
 assert result['audit']['minor']['coursework_met']
 assert all(t['credits']<=25 for t in result['semesters'].values())
 scheduled={c['code'] for t in result['semesters'].values() for c in t['courses']}
 assert set(selected)<=scheduled
