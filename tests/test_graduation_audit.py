"""Graduation feasibility is distinct from a verified course schedule."""
import pytest
from backend.services.scoped_planner import DATA, catalogue_for, assessment, normalize_request, prepare, InputError
from backend.services.problem_builder import build_problem_for_student
from backend.services.planning_service import make_plan
from backend.models.planning_problem import Problem
from backend.verification import verify_plan
from backend.astar import solve as astar_solve, AStarConfig
from backend.csp.solver import solve as csp_solve, SolverConfig


def test_first_year_complete_and_bulletin_units():
    courses=[DATA['courses'][c] for c in DATA['common']]
    assert len(courses)==15
    assert sum(c['credits'] for c in courses if c['recommended_semester']==1)==17
    assert sum(c['credits'] for c in courses if c['recommended_semester']==2)==20
    assert DATA['courses']['BITS F111']['title']=='Thermodynamics'
    assert 'MATH F213' not in DATA['courses']


def test_credit_capacity_does_not_confirm_graduation():
    cat,_=catalogue_for('cse');req=normalize_request(dict(current_semester=7,target_semester=8))
    result=assessment(cat,set(),set(),set(DATA['common']),None,req,verified=True)
    assert not result['capacity_possible']
    assert not result['is_eligible_for_graduation']
    assert result['earliest_credit_bound']==14


def test_unknown_transcript_courses_get_no_invented_credits():
    with pytest.raises(InputError,match='outside the requested image scope'):
        prepare(dict(current_semester=3,completed_courses=['UNKNOWN F999']))


def test_dual_degree_cannot_be_declared_eligible_from_one_branch():
    with pytest.raises(InputError,match='Dual-degree'):
        normalize_request(dict(degree_type='dual'))


def test_capstone_availability_and_exclusive_semester_in_both_solvers():
    courses={'THESIS':{'credits':16,'category':'Thesis','formula':None,'earliest_semester':7,'exclusive_semester':True},
             'CORE':{'credits':3,'category':'Core','formula':None}}
    problem=Problem(courses=courses,current_semester=5,target_semester=8,max_credits=22)
    assert problem.initial_domains()['THESIS']==[7,8]
    assert not verify_plan(problem,{'THESIS':6,'CORE':7}).valid
    assert not verify_plan(problem,{'THESIS':7,'CORE':7}).valid
    for solve in (lambda p:csp_solve(p,SolverConfig()),lambda p:astar_solve(p,AStarConfig(bundle_breadth_limit=None))):
        result=solve(problem)
        assert result.status=='SAT'
        assert result.assignment['THESIS']>=7
        assert result.assignment['THESIS']!=result.assignment['CORE']
        assert verify_plan(problem,result.assignment).valid


def test_learned_heuristic_can_be_selected_in_live_service():
    problem=build_problem_for_student('cse',[],0)
    completed=[c for c in problem.courses if c!='CS F211']
    result=make_plan('cse',completed,3,8,solver='astar',heuristic='learned',timeout_s=2)
    assert result.status=='PLAN'
    assert result.verification.valid
    assert result.stats['heuristic']=='learned'
