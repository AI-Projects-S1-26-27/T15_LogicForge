"""Reproducible E1–E4 on curated instances; finite search budgets reported honestly."""
import sys,json,random,csv,time,dataclasses
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from backend.services.scoped_planner import prepare,MINORS,CATALOGUE_SIGNATURE,curriculum_response
from backend.services.planning_service import make_plan
from backend.csp.solver import solve,SolverConfig
from backend.astar import solve as astar,AStarConfig
from backend.verification import verify_plan
from experiments.stats import summarize,wilcoxon_signed_rank
OUT=Path(__file__).parent/'results';OUT.mkdir(exist_ok=True)
def write(name,rows):
 (OUT/name).write_text(json.dumps(rows,indent=2))
def run():
 rng=random.Random(1718);cases=[];rows=[];abl=[];heur=[]
 for i in range(200):
  b=['cse','eee','ece','e_and_i'][i%4]; minors=['']+[m for m,v in MINORS.items() if b not in v['excluded_branches']]
  req=dict(branch=b,minor=minors[(i//4)%len(minors)],current_semester=0,target_semester=7+i%2,max_credits=rng.choice([20,22,24,25]),project_route='practice_school',allow_unconfirmed=True)
  profile=['on_track','behind_one','failed_prerequisite','late_minor','accelerated'][i%5]
  req['current_semester']=[0,2,3,4,5][(i//4)%5]
  req['completed_courses']=curriculum_response(b)['reference_completed_by_semester'][str(req['current_semester'])]
  if profile in ('behind_one','failed_prerequisite') and req['completed_courses']:
   req['completed_courses'].pop(rng.randrange(len(req['completed_courses'])))
  cases.append(dict(id=i,profile=profile,request=req))
  try:p=prepare(req)['problem']
  except Exception as e:
   rows.append(dict(id=i,status='INPUT_BLOCKED',message=str(e)));continue
  pair=[]
  for solver in ['csp','astar']:
   r=make_plan(b,req["completed_courses"],req["current_semester"],req['target_semester'],solver=solver,problem_override=p,timeout_s=.25,diagnose=False)
   row=dict(id=i,solver=solver,status=r.status,verified=bool(r.verification and r.verification.valid),**r.stats);rows.append(row);pair.append(row)
  for name,cfg in [('BT',{}),('FC',dict(forward_checking=True)),('AC3',dict(forward_checking=True,ac3=True)),('MRV_LCV',dict(forward_checking=True,ac3=True,mrv=True,degree_tiebreak=True,lcv=True))]:
   r=solve(p,SolverConfig(timeout_s=.1,**cfg));abl.append(dict(id=i,configuration=name,status=r.status,**r.stats))
  for h in ['credit_bound','critical_path','composite','learned']:
   r=astar(p,AStarConfig(heuristic=h,timeout_seconds=.15));heur.append({**r.stats,'id':i,'heuristic':h,'status':r.status,'verified':r.status=='SAT' and verify_plan(p,r.assignment).valid})
  if i%20==0:print('evaluated',i,flush=True)
 write('instances.json',cases);write('e1_e4.json',rows);write('e2.json',abl);write('e3.json',heur)
 summary={'catalogue_signature':CATALOGUE_SIGNATURE,'instances':200,'budgets_seconds':{'E1':.25,'E2':.1,'E3':.15},'note':'Timeouts are censored, not UNSAT. E3 full-size runs do not claim optimality. Synthetic profiles, not volunteer data.'}
 for solver in ['csp','astar']:
  rs=[r for r in rows if r.get('solver')==solver];sat=[r for r in rs if r['status']=='PLAN']
  summary[solver]={'statuses':{s:sum(r['status']==s for r in rs) for s in set(r['status'] for r in rs)},'returned_validity':summarize([int(r['verified']) for r in sat],iterations=2000) if sat else None,'runtime':summarize([r.get('time_s',0) for r in rs],iterations=2000)}
 paired=[(next((r for r in rows if r.get('id')==i and r.get('solver')=='csp'),None),next((r for r in rows if r.get('id')==i and r.get('solver')=='astar'),None)) for i in range(200)]
 pairs=[(a,b) for a,b in paired if a and b and a['status']==b['status']=='PLAN']
 if pairs:summary['paired_nodes_wilcoxon']=wilcoxon_signed_rank([a.get('nodes',0) for a,b in pairs],[b.get('nodes',0) for a,b in pairs])
 write('summary.json',summary);print('finished200',flush=True)
if __name__=='__main__':run()
