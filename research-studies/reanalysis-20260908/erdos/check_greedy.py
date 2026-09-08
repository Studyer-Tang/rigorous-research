"""Independent finite audit of the proposed greedy criterion; no universal promotion."""
import json
import sys
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
import egyptian_fractions as producer
from integer_certificate_verifier import verify
from research_io import sha256, write_json


def trial_factors(n):
    result=[]
    p=2
    while p*p<=n:
        power=0
        while n%p==0:
            n//=p
            power+=1
        if power:
            result.append({'prime':p,'exponent':power})
        p+=1
    if n>1:
        result.append({'prime':n,'exponent':1})
    return result


rows=[]
for t in range(1,417):
    n,x=24*t+1,6*t+1
    b=n*x
    factors=trial_factors(b)
    q=next((f['prime'] for f in factors if f['prime']%3==2),None)
    witness=producer.completion(4,n,x,True,producer.Budget(1000000))
    assert (witness is not None)==(q is not None)
    row={'n':n,'x':x,'factorization_b':factors,'criterion_predicts_success':q is not None}
    if q is not None:
        y,z=b*(q+1)//(3*q),b*(q+1)//3
        assert b*(q+1)%(3*q)==0 and b*(q+1)%3==0
        assert x<y<z and Fraction(4,n)==Fraction(1,x)+Fraction(1,y)+Fraction(1,z)
        row.update(q=q,y=y,z=z,independent_check='exact integer witness and ordering')
    else:
        certificate={'schema_version':1,'backend':'exact-integer','backend_version':'1',
                     'operation':'two-unit-fractions-obstruction',
                     'claim':{'numerator':4,'denominator':n,'first_denominator':x},
                     'denominator_factorization':factors,'recommended_evidence_role':'decisive'}
        checked=verify(certificate)
        assert checked['status']=='ESTABLISHED',checked
        row.update(certificate=certificate,independent_check=checked)
    rows.append(row)
unrestricted=producer.search(4,3,10000,True)
checked=verify(unrestricted)
assert checked['status']=='ESTABLISHED',checked
out=Path(__file__).parent
write_json(out/'unrestricted-replay.json',unrestricted)
write_json(out/'unrestricted-check.json',checked)
summary={'checked_n_range':[25,9985],'step':24,'total':len(rows),
         'greedy_success':sum(r['criterion_predicts_success'] for r in rows),
         'greedy_obstructions':sum(not r['criterion_predicts_success'] for r in rows),
         'first_obstructions':[r['n'] for r in rows if not r['criterion_predicts_success']][:12],
         'criterion_mismatches':0,'unrestricted_witnesses':len(unrestricted['witnesses']),
         'original_conjecture':'INCONCLUSIVE','novelty':'NOT_ASSESSED',
         'verification_scope':'Finite witnesses/obstructions only; the general criterion is justified separately in the written proof.',
         'script_sha256':sha256(Path(__file__)), 'rows':rows}
write_json(out/'greedy-audit.json',summary)
print(json.dumps({k:v for k,v in summary.items() if k!='rows'},indent=2))
