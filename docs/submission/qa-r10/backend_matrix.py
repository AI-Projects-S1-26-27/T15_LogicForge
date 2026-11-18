"""Live deterministic regression matrix; run from project root with Python 3.10+."""
import json,sys,time
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from backend.services.scoped_planner import curriculum_response, InputError, DATA, CATALOGUE_SIGNATURE, MINORS
from backend.services.scoped_api import plan_payload

def check(out, req):
    issues=[]
    if out['status']!='PLAN': return issues
    if not out['verification_valid']: issues.append('PLAN without independent verification')
    if not out['audit']['requirements_met']: issues.append('PLAN does not meet graduation audit')
    allcodes=[]
    for term,row in out['semesters'].items():
        if row['credits']>req['max_credits']: issues.append('Credit cap exceeded')
        if not req['current_semester']<int(term)<=req['target_semester']: issues.append('Out of horizon')
        codes=[c['code'] for c in row['courses']]
        allcodes+=codes
        if 'BITS F412' in codes and (len(codes)!=1 or int(term)!=req.get('ps2_semester',int(term))): issues.append('PS2 placement/exclusivity')
        for c in row['courses']:
            if c['category']=='Discipline Core' and req['branch'] not in c['cdc_branches']: issues.append('Foreign CDC')
    if len(allcodes)!=len(set(allcodes)): issues.append('Duplicate course')
    if set(allcodes)&set(req['completed_courses']): issues.append('Passed course scheduled again')
    for cat,courses,units in [('Humanities Elective',3,9),('Discipline Elective',4,12),('Open Elective',5,15)]:
        x=out['audit']['categories'][cat]
        if x['courses']<courses or x['credits']<units: issues.append(cat+' below minimum')
    return issues

def main():
    records=[]
    for branch in ['cse','eee','ece','e_and_i']:
      for current in [0,2,4]:
       for target,route,ps in [(8,'thesis',None),(7,'thesis',None),(8,'practice_school',7),(8,'practice_school',8),(7,'practice_school',7)]:
        for cap in [22,26]:
         for solver in ['csp','astar']:
          req=dict(branch=branch,current_semester=current,target_semester=target,project_route=route,ps2_semester=ps,max_credits=cap,solver=solver,allow_unconfirmed=True,auto_fill=True,completed_courses=curriculum_response(branch)['reference_completed_by_semester'][str(current)])
          records.append(run(req))
    for branch in ['cse','eee','ece','e_and_i']:
     for minor in MINORS:
      if branch in MINORS[minor]['excluded_branches']: continue
      for solver in ['csp','astar']:
       req=dict(branch=branch,current_semester=0,target_semester=8,project_route='thesis',max_credits=26,solver=solver,minor=minor,allow_unconfirmed=True,auto_fill=True,completed_courses=[])
       records.append(run(req))
    dest=Path(__file__).with_name('backend_matrix_results.json')
    dest.write_text(json.dumps(dict(catalogue_signature=CATALOGUE_SIGNATURE,rows=records,counts=dict(Counter(r['status'] for r in records))),indent=2))
    print('SUMMARY',len(records),dict(Counter(r['status'] for r in records)), 'invariant failures',sum(bool(r['issues']) for r in records),flush=True)

def run(req):
    started=time.monotonic()
    try:
        out=plan_payload(req)
        record=dict(request=req,status=out['status'],issues=check(out,req),feedback=out.get('planning_feedback'),loads={str(k):v['credits'] for k,v in out['semesters'].items()},empty_future_terms=[s for s in range(req['current_semester']+1,req['target_semester']+1) if s not in out['semesters']] if out['status']=='PLAN' else [],verified=out['verification_valid'])
    except InputError as exc:
        record=dict(request=req,status='INPUT_ERROR',issues=[],feedback=[str(exc)]+exc.issues)
    except Exception as exc:
        record=dict(request=req,status='EXCEPTION',issues=[repr(exc)])
    record['wall_seconds']=round(time.monotonic()-started,4)
    print(req['branch'],req['current_semester'],req['target_semester'],req['project_route'],req.get('ps2_semester'),req['max_credits'],req['solver'],req.get('minor','-'),record['status'],record['wall_seconds'],record['issues'],flush=True)
    return record
if __name__=='__main__':main()
