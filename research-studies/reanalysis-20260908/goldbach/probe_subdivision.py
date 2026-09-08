"""Bounded live probe: recompute the widest recorded triangle, then split it into four."""
import json
import sys
import time
from fractions import Fraction as Q
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'cases/goldbach-conjecture/artifacts'))
import certify_li_equation14_d_free_positive_weight_stage1 as backend
from research_io import sha256, write_json

start=time.monotonic()
out=Path(__file__).parent
old_path=ROOT/'cases/goldbach-conjecture/agent-drafts/li-equation14-d-free-positive-weight-stage1-local-smoke.json'
old=json.loads(old_path.read_text())
row=old['widest_triangle_details'][0]
g=row['geometry_identity']
triangle=tuple(tuple(Q(v) for v in vertex) for vertex in g['triangle'])


def affine(key):
    return backend.Affine(*(Q(g[key][field]) for field in ('constant','x','y','z')))


lower,upper,theta=affine('lower'),affine('upper'),affine('theta')
assert backend.geometry_identity(g['winner'],theta,lower,upper,triangle)[0]==row['identity_sha256']
print('Building inherited delay and prefix objects',flush=True)
delay=backend.G.FixedDelayTaylor(8,16,300,96)
evaluator=backend.D2.FastARatioDerivatives(delay)
prefix=backend.StrictGPrefix(delay,Q(1,2))
print('Recomputing the old widest triangle',flush=True)
base,_=backend.triangle_stage1(triangle,lower,upper,theta,prefix,evaluator,16,0)
assert base.nominal==Q(row['nominal_exact'])
assert sum(base.budgets.values(),Q(0))==Q(row['radius_exact'])
check={'scope':'one-triangle subdivision probe using the existing analytic producer; not independently validated analytic bounds',
       'source_sha256':sha256(old_path),'baseline_identity':row['identity_sha256'],'baseline_exact_reproduction':True,
       'baseline_radius':float(sum(base.budgets.values(),Q(0))),'baseline_nominal':float(base.nominal),
       'baseline_hessian':float(base.budgets['taylor_hessian_remainder_radius']), 'children':[]}
write_json(out/'subdivision-checkpoint.json',check)
a,b,c=triangle
ab=tuple((x+y)/2 for x,y in zip(a,b));bc=tuple((x+y)/2 for x,y in zip(b,c));ca=tuple((x+y)/2 for x,y in zip(c,a))
children=[(a,ab,ca),(ab,b,bc),(ca,bc,c),(ab,bc,ca)]
results=[]
for index,tri in enumerate(children):
    print('Child',index+1,flush=True)
    result,_=backend.triangle_stage1(tri,lower,upper,theta,prefix,evaluator,16,0)
    results.append(result)
    check['children'].append({'index':index,'triangle':[[str(v) for v in vertex] for vertex in tri],
                             'nominal_exact':str(result.nominal), 'radius_exact':str(sum(result.budgets.values(),Q(0))),
                             'hessian_exact':str(result.budgets['taylor_hessian_remainder_radius'])})
    write_json(out/'subdivision-checkpoint.json',check)
new_radius=sum((sum(r.budgets.values(),Q(0)) for r in results),Q(0))
new_nominal=sum((r.nominal for r in results),Q(0))
new_hessian=sum((r.budgets['taylor_hessian_remainder_radius'] for r in results),Q(0))
old_radius=sum(base.budgets.values(),Q(0))
check.update(children_radius=float(new_radius),children_nominal=float(new_nominal),children_hessian=float(new_hessian),
             radius_reduction_factor=float(old_radius/new_radius),
             hessian_reduction_factor=float(base.budgets['taylor_hessian_remainder_radius']/new_hessian),
             parent_and_children_intervals_overlap=max(base.interval[0],new_nominal-new_radius)<=min(base.interval[1],new_nominal+new_radius),
             elapsed_seconds=time.monotonic()-start,original_goal='INCONCLUSIVE',new_global_certificate=False,
             script_sha256=sha256(Path(__file__)))
write_json(out/'subdivision-probe.json',check)
print(json.dumps({k:v for k,v in check.items() if k!='children'},indent=2))
