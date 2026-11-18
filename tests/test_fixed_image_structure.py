import pytest
from backend.services.scoped_planner import catalogue_for
from backend.services.scoped_api import plan_payload

@pytest.mark.parametrize('branch',['cse','eee','ece','e_and_i'])
@pytest.mark.parametrize('solver',['csp','astar'])
def test_image_cores_stay_exactly_fixed(branch,solver):
 r=plan_payload(dict(branch=branch,solver=solver,current_semester=0,allow_unconfirmed=True,project_route='practice_school',max_credits=22))
 assert r['status']=='PLAN' and r['verification_valid']
 cat=catalogue_for(branch)[0]
 for term,row in r['semesters'].items():
  for c in row['courses']:
   src=cat[c['code']]
   if src['category'] in ('Institutional Core','Discipline Core') and src.get('recommended_semester'):
    assert term==src['recommended_semester'],c['code']
   if src['category']=='General Awareness': assert term==4
   if 'Elective' in c['category']: assert term>=3
