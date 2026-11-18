import pytest
from backend.services.scoped_api import plan_payload
from backend.services.scoped_planner import normalize_request, InputError

@pytest.mark.parametrize('solver',['csp','astar'])
def test_seven_cse_at_25(solver):
 r=plan_payload(dict(branch='cse',solver=solver,current_semester=0,target_semester=7,max_credits=25,project_route='practice_school',ps2_semester=7,allow_unconfirmed=True))
 assert r['status']=='PLAN' and r['verification_valid'] and r['audit']['requirements_met']
 assert set(r['semesters'])==set(range(1,8))
 assert max(t['credits'] for t in r['semesters'].values())<=25

def test_over25_rejected():
 with pytest.raises(InputError,match='25'):
  normalize_request(dict(max_credits=26))
