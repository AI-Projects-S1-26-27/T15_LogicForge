"""Additional stratified measurements from the saved raw experimental runs."""
import sys,json,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from experiments.stats import summarize
root=Path(__file__).parent/'results';rows=json.loads((root/'e1_e4.json').read_text());instances=json.loads((root/'instances.json').read_text());meta={r['id']:r for r in instances}
summary={}
for field,values in [('solver',['csp','astar']),('profile',sorted({r['profile'] for r in instances}))]:
 for value in values:
  subset=[r for r in rows if (r.get('solver') if field=='solver' else meta[r['id']]['profile'])==value]
  metrics={}
  for metric in ['nodes','backtracks','time_s']:
   data=[r[metric] for r in subset if isinstance(r.get(metric),(int,float)) and math.isfinite(r[metric])]
   if data:metrics[metric]=summarize(data,iterations=2000)
  summary[field+':'+value]={'records':len(subset),'metrics':metrics}
summary['caveats']=['36 profiles were blocked at preparation; 164 reached both solvers.','A* uses bundle breadth10; its NO_PLAN status means no plan found within this restricted search, not a proof of infeasibility.','CSP NO_PLAN is UNSAT only after complete search. TIMEOUT is unresolved.','Repeated synthetic request patterns are possible; no claim of statistical independence among all profiles. Paired comparisons use identical instances and only jointly successful runs.','Synthetic experiments do not substitute for volunteer evaluation.']
(root/'stratified_statistics.json').write_text(json.dumps(summary,indent=2))
