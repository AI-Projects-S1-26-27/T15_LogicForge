import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from experiments.stats import summarize
rows=[json.loads(p.read_text()) for p in Path(sys.argv[1]).glob('*-feedback.json')]
assert len({r['participant'] for r in rows})==len(rows),'Duplicate participant codes'
assert all(r.get('consent')=='on' and 1<=r['usefulness']<=5 and 0<=r['tasks_completed']<=5 for r in rows),'Invalid or non-consenting feedback'
print(json.dumps(dict(participants=len(rows),status='complete_sample' if 6<=len(rows)<=10 else 'incomplete_sample',correctness={k:sum(r['correctness']==k for r in rows) for k in ['yes','no','unsure']},usefulness=summarize([r['usefulness'] for r in rows],iterations=5000) if rows else None,mean_tasks_completed=sum(r['tasks_completed'] for r in rows)/len(rows) if rows else None),indent=2))
