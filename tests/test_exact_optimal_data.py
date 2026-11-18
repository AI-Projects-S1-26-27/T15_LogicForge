import json
from pathlib import Path
from backend.csp.model import Problem
from backend.csp.solver import solve,SolverConfig
from backend.verification import verify_plan

def test_exact_training_labels_have_complete_shorter_horizon_proofs():
 rows=json.loads(Path('backend/ml/optimal_artifacts/oracle_proofs.json').read_text())
 assert len(rows)==3000
 for row in rows[::100]:
  for length in range(1,row['h_star']+1):
   p=Problem(courses=row['courses'],completed=set(row['completed']),current_semester=row['current_semester'],target_semester=row['current_semester']+length,max_credits=row['max_credits'])
   r=solve(p,SolverConfig(mrv=True,forward_checking=True,ac3=True))
   assert r.status==('SAT' if length==row['h_star'] else 'UNSAT')
   if r.status=='SAT':assert verify_plan(p,r.assignment).valid

def test_exact_evaluation_agrees_with_oracle():
 rows=json.loads(Path('experiments/proposal/results/e3_exact_optimality.json').read_text())
 assert len(rows)==500
 assert all(r['verified'] and r['gap']>=0 for r in rows)
 assert all(r['gap']==0 for r in rows if r['heuristic']!='learned_direct_research')
