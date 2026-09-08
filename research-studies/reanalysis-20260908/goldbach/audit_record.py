"""Exact directed re-aggregation of legacy certificate data, without importing its producer."""
import hashlib
import json
import sys
import time
from fractions import Fraction as F
from pathlib import Path

if hasattr(sys,'set_int_max_str_digits'):
    sys.set_int_max_str_digits(500000)
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from research_io import sha256, write_json

source=ROOT/'cases/goldbach-conjecture/agent-drafts/li-equation14-d-free-positive-weight-stage1-local-smoke.json'
started=time.monotonic()
data=json.loads(source.read_text(encoding='utf-8'))
rows=data['all_triangle_contributions']
scale=1<<128


def ratio(text):
    a,separator,b=text.partition('/')
    n,d=int(a),int(b) if separator else 1
    assert d>0
    return n,d


def dyadic(text):
    n,d=ratio(text)
    return (n*scale)//d,-((-n*scale)//d)


def within(text, bounds):
    n,d=ratio(text)
    return bounds[0]*d<=n*scale<=bounds[1]*d


names=list(rows[0]['budgets_exact'])
sums={key:[0,0] for key in ['nominal','radius','lower','upper',*names]}
for row in rows:
    budget={k:F(v) for k,v in row['budgets_exact'].items()}
    assert all(v>=0 for v in budget.values())
    radius=F(row['radius_exact'])
    nominal=F(row['nominal_exact'])
    assert sum(budget.values(),F(0))==radius
    assert F(row['interval']['lower_exact'])==nominal-radius
    assert F(row['interval']['upper_exact'])==nominal+radius
    fields={'nominal':row['nominal_exact'],'radius':row['radius_exact'],
            'lower':row['interval']['lower_exact'],'upper':row['interval']['upper_exact'],**row['budgets_exact']}
    for key,value in fields.items():
        lo,hi=dyadic(value)
        sums[key][0]+=lo
        sums[key][1]+=hi
    assert 0<=F(row['g_uniform_remainder_propagated_subbudget_exact'])<=radius
identity=hashlib.sha256('\n'.join(row['identity_sha256'] for row in rows).encode('ascii')).hexdigest()
aggregate={
 'nominal_in_recomputed_enclosure':within(data['T3']['nominal_exact'],sums['nominal']),
 'radius_in_recomputed_enclosure':within(data['T3']['exact_symmetric_radius']['exact'],sums['radius']),
 'lower_in_recomputed_enclosure':within(data['T3']['exact_interval_before_accumulation_rounding']['lower_exact'],sums['lower']),
 'upper_in_recomputed_enclosure':within(data['T3']['exact_interval_before_accumulation_rounding']['upper_exact'],sums['upper']),
}
for name in names:
    aggregate[name]=within(data['error_decomposition']['additive_symmetric_radius_components'][name]['exact'],sums[name])
assert all(aggregate.values()),aggregate
assert data['geometry']['ordered_triangle_identity_digest_sha256']==identity
recorded_low=F(data['T3']['directed_accumulation_interval']['lower_exact'])
recorded_high=F(data['T3']['directed_accumulation_interval']['upper_exact'])
required=F(data['T3']['required_lower_exact'])
assert recorded_low<required<recorded_high
geometry=data['geometry']
volumes=[F(geometry[key]) for key in ('ordered_domain_volume_exact','base_fiber_volume_exact','relative_precut_volume_exact')]
assert volumes[0]==volumes[1]==volumes[2]
assert sum(F(w['declared_volume_exact']) for w in geometry['per_winner'])==volumes[0]
dependencies=[]
for name,expected in data['dependencies_sha256'].items():
    p=ROOT/'cases/goldbach-conjecture/artifacts'/name
    dependencies.append({'name':name,'matches_recorded_hash':p.is_file() and sha256(p)==expected})
program=ROOT/'cases/goldbach-conjecture/artifacts/certify_li_equation14_d_free_positive_weight_stage1.py'
dependencies.append({'name':program.name,'matches_recorded_hash':sha256(program)==data['program_sha256']})
H=sums['taylor_hessian_remainder_radius']
rad=sums['radius']
prefix=sums['g_prefix_model_radius']
shares=[F(H[0],rad[1]),F(H[1],rad[0])]
diagnostics={name:float(F(sums[name][1],scale)) for name in names}
nominal_upper=F(sums['nominal'][1],scale)
result={'scope':'Independent arithmetic/provenance audit of stored interval rows, not a new analytic integral certificate',
        'source_sha256':sha256(source),'triangles_checked':len(rows),'all_local_radius_and_interval_equalities':True,
        'aggregate_values_inside_independently_directed_sums':aggregate,'accumulation_bits':128,
        'maximum_aggregate_enclosure_width':str(F(len(rows),scale)),
        'legacy_directed_interval':[float(recorded_low),float(recorded_high)],'required_lower':float(required),
        'nominal_enclosure':[float(F(sums['nominal'][0],scale)),float(nominal_upper)],
        'nominal_upper_below_required_lower':nominal_upper<required,
        'radius_components_upper_approx':diagnostics,'hessian_radius_share_bounds_approx':[float(s) for s in shares],
        'prefix_radius_share_upper_approx':float(F(prefix[1],rad[0])),
        'recorded_volumes_equal':True,'identity_list_digest_matches':True,'dependencies':dependencies,
        'all_dependencies_match':all(d['matches_recorded_hash'] for d in dependencies),
        'original_goal':'INCONCLUSIVE','new_integral_bound_certified':False,
        'limitations':['Per-cell analytic bounds, geometric cells and g-prefix enclosures were not independently regenerated.',
                       'Aggregate agreement is certified within the stated dyadic enclosure, not asserted as exact equality of enormous global fractions.',
                       'The nominal sum is not a certified point estimate; its being below threshold does not prove the true integral below threshold.'],
        'elapsed_seconds':time.monotonic()-started,'auditor_sha256':sha256(Path(__file__))}
write_json(Path(__file__).with_name('record-audit.json'),result)
print(json.dumps(result,indent=2))
