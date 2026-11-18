import sys,json,itertools
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from backend.csp.model import Problem
from backend.csp.solver import solve,SolverConfig
from backend.astar import solve as astar,AStarConfig
from backend.verification import verify_plan
from backend.explanations.infeasibility_analyzer import analyze,relaxed_problem
out=Path(__file__).parent/'results';out.mkdir(exist_ok=True)
proofs=json.loads(Path('backend/ml/optimal_artifacts/oracle_proofs.json').read_text());rows=[]
for v in [p for p in proofs if p['id']%4==3][:100]:
 p=Problem(courses=v['courses'],completed=set(v['completed']),current_semester=v['current_semester'],target_semester=v['current_semester']+14,max_credits=v['max_credits'])
 for h in ['credit_bound','critical_path','composite','learned','learned_direct_research']:
  r=astar(p,AStarConfig(heuristic=h,bundle_breadth_limit=None,timeout_seconds=2))
  last=max(r.assignment.values()) if r.status=='SAT' else None
  rows.append(dict(id=v['id'],heuristic=h,status=r.status,oracle_optimum=v['h_star'],terms=last-v['current_semester'] if last else None,gap=last-v['current_semester']-v['h_star'] if last else None,verified=r.status=='SAT' and verify_plan(p,r.assignment).valid,**{k:r.stats.get(k) for k in ['nodes','time_s']}))
(out/'e3_exact_optimality.json').write_text(json.dumps(rows,indent=2))
checks=[]
for i in range(20):
 courses={}
 for j in range(3+i%4):
  code=f'C{j}'
  courses[code]={'credits':1+(i+j)%3,'category':'Required Course','formula':{'kind':'leaf','course':f'C{j-1}','relation':'PRE'} if j else None,'parity':'odd' if j==0 and i%3==0 else None}
 p=Problem(courses=courses,completed=set(),current_semester=0,target_semester=1+i%2,max_credits=3+i%4)
 oracle=lambda q:solve(q,SolverConfig(mrv=True,forward_checking=True,ac3=True)).status
 r=analyze(p,oracle);assert r.status=='infeasible' and r.minimal
 subsets=[list(s) for k in range(len(r.conflict)) for s in itertools.combinations(r.conflict,k)]
 assert all(oracle(relaxed_problem(p,s))=='SAT' for s in subsets)
 checks.append(dict(case=i,conflict=r.conflict,minimal_verified=True,proper_subsets_checked=len(subsets)))
(out/'minimal_core_validation.json').write_text(json.dumps(checks,indent=2))
print('500 exact-optimality runs and20 brute-force minimal-core checks completed')
