"""Recheck archived certificates and reconstruct coverage without trusting report claims."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'scripts'))
from integer_certificate_verifier import verify

actions=[json.loads(p.read_text(encoding='utf-8')) for p in sorted((HERE/'actions').glob('*.json'))]
certificates=[]; windows=[];families=[]
for action in actions:
    c=action['result'].get('certificate')
    if not c:continue
    checked=verify(c)
    assert checked['status']==action['result']['status'],(action['id'],checked)
    certificates.append(action['id'])
    if c['operation']=='three-unit-fractions-window':windows.append(c)
    elif c['operation']=='three-unit-fractions-window-scan':windows.extend(c['windows'])
    elif c['operation']=='unit-fraction-polynomial-family':families.append((action['id'],c))
minimum=[]
for n in [1129,1201,246241]:
    entries=[e for c in windows if c['claim']['denominator']==n for e in c['entries']]
    witness=min((e for e in entries if e['outcome']=='witness'),key=lambda e:e['x'])
    excluded={e['x'] for e in entries if e['outcome'] in {'obstructed','nonpositive-residual'}}
    assert set(range(n//4+1,witness['x']))<=excluded
    minimum.append(dict(n=n,minimal_x=witness['x'],failed_initial_choices=witness['x']-n//4-1,y=witness['y'],z=witness['z']))
covered=set();coverage_ids=[]
for action_id,c in families:
    n=c['claim']['n']
    if len(n)!=2 or n[1] not in (24,840):continue
    base,modulus=n
    assert c['claim']['numerator']==4 and c['claim']['distinct'] is True
    assert base==next(k for k in range(3,modulus+3) if k%modulus==base%modulus)
    covered.update(r for r in range(840) if (r-base)%modulus==0)
    coverage_ids.append(action_id)
gaps=sorted(set(range(840))-covered)
assert gaps==[1,121,169,289,361,529]
short_scans=[a for a in actions if a['proposal']['action']['tool']=='egyptian_scan' and a['proposal']['action']['arguments']['width']==8]
checked_ns=set();refuted=[]
for action in short_scans:
    for c in action['result']['certificate']['windows']:
        checked_ns.add(c['claim']['denominator'])
        if verify(c)['status']=='REFUTED':refuted.append(c['claim']['denominator'])
summary=dict(original_goal='INCONCLUSIVE',certificate_actions_rechecked=certificates,
             polynomial_families=len(families),coverage_family_actions=coverage_ids,
             modulus=840,covered_residue_count=len(covered),uncovered_residues=gaps,
             coverage_scope='For every n>=3 outside these six residues, a checked distinct-denominator family applies.',
             minimal_first_denominators=minimum,eight_step_checked_inputs=len(checked_ns),eight_step_refuted_inputs=refuted,
             eight_step_complete_prefix=dict(start=25,stop=99985,step=24,count=4166),
             novelty='NOT_ASSESSED; partial modular coverage agrees with existing literature')
(HERE/'window-summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in summary.items() if k not in ('certificate_actions_rechecked','coverage_family_actions')},indent=2))
