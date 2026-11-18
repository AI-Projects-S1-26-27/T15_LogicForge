"""Exact h* labels on seeded small synthetic planning instances.
For each state, complete CSP search proves every shorter horizon UNSAT.
No timeout, bundle limit, heuristic optimum, or feasible suffix is used as a label.
"""
import random,json,csv
from pathlib import Path
from backend.csp.model import Problem
from backend.csp.solver import solve,SolverConfig
from backend.verification import verify_plan
from backend.ml.features import FEATURE_NAMES,FEATURE_VERSION,extract_features_vector
from backend.services.scoped_planner import CATALOGUE_SIGNATURE

def generate(output=Path('backend/ml/optimal_artifacts'),n=3000):
 output=Path(output);output.mkdir(parents=True,exist_ok=True);rng=random.Random(20261118);rows=[];checks=[]
 for i in range(n):
  count=rng.randint(3,7);courses={}
  for j in range(count):
   deps=rng.sample(list(courses),min(j,rng.choice([0,0,1,2])))
   formula={'kind':'and','items':[{'kind':'leaf','course':c,'relation':'PRE'} for c in deps]} if deps else None
   courses[f'SYN{j}']={'credits':rng.randint(1,4),'category':'Required Course','parity':rng.choice([None,None,'odd','even']),'formula':formula}
  cap=rng.randint(4,10);current=rng.randint(0,2);prefix=rng.randint(0,count-1);done=set(list(courses)[:prefix]);base=Problem(courses=courses,completed=done,current_semester=current,target_semester=current+14,max_credits=cap)
  label=None;unsat=0
  for length in range(1,15):
   p=Problem(courses=courses,completed=done,current_semester=current,target_semester=current+length,max_credits=cap)
   r=solve(p,SolverConfig(mrv=True,forward_checking=True,ac3=True,degree_tiebreak=True))
   if r.status=='SAT':
    assert verify_plan(p,r.assignment).valid
    label=length;break
   assert r.status=='UNSAT';unsat+=1
  assert label is not None
  family=['family_a','family_b','family_c','e_and_i'][i%4]
  rows.append(dict(zip(FEATURE_NAMES,extract_features_vector(base,{},current+1)),remaining_terms=label,episode=f'exact-{i}',branch=family))
  checks.append(dict(id=i,courses=courses,completed=sorted(done),current_semester=current,max_credits=cap,h_star=label,shorter_horizons_proved_unsat=unsat))
  if i%500==0:print('exact labels',i,flush=True)
 with (output/'training_data.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=FEATURE_NAMES+['remaining_terms','episode','branch']);w.writeheader();w.writerows(rows)
 (output/'dataset.json').write_text(json.dumps(dict(feature_version=FEATURE_VERSION,features=FEATURE_NAMES,catalogue_signature=CATALOGUE_SIGNATURE,label_kind='exact_optimal_remaining_terms_small_instances',rows=len(rows),source='3000 small synthetic states; complete CSP proofs for all shorter horizons; independent SAT verification',split_note='branch column encodes synthetic generator families, not real student branches')))
 (output/'oracle_proofs.json').write_text(json.dumps(checks))
 return rows
if __name__=='__main__':generate()
