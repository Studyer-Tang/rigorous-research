"""Change the ansatz after constant-divisor search leaves twelve gaps."""
import json
import math
from pathlib import Path

import sympy as sp

HERE = Path(__file__).resolve().parent
t = sp.Symbol('t')
old = json.loads((HERE/'family-candidates.json').read_text())
families = old['families'][:]
gaps = []
for residue in old['uncovered']:
    base = 841 if residue == 1 else residue
    n = sp.Poly(840*t+base,t,domain=sp.QQ)
    accepted = None
    for k in range(1,65):
        r = 4*k-1
        x = sp.Poly(210*t+(base+r)//4,t,domain=sp.QQ)
        b = n*x
        for q in sp.divisors(math.gcd(*(int(c) for c in b.all_coeffs()))):
            if (q+1) % r:continue
            y=b.mul_ground(sp.Rational(q+1,r*q));z=y.mul_ground(q)
            if all(c>=0 and c.q==1 for p in (y-x-sp.Poly(1,t),z-y-sp.Poly(1,t)) for c in p.all_coeffs()):
                accepted=(dict(n=n,x=x,y=y,z=z),dict(method='proportional divisor',offset=k,q=int(q)))
                break
        if accepted:break
    if accepted is None and base%7==5:
        c=(n+sp.Poly(2,t)).mul_ground(sp.Rational(1,7))
        accepted=(dict(n=n,x=c.mul_ground(2),y=n.mul_ground(2),z=c*n),dict(method='varying residual: n=7c-2'))
    if accepted:
        polys,meta=accepted
        assert all(c.q==1 for p in polys.values() for c in p.all_coeffs())
        families.append(dict(residue=residue,**meta,arguments=dict(numerator=4,distinct=True,
                        **{key:[int(p.nth(i)) for i in range(p.degree()+1)] for key,p in polys.items()})))
    else:gaps.append(residue)
out=dict(modulus=840,universe=old['universe'],families=sorted(families,key=lambda r:r['residue']),
         uncovered=gaps,coverage_is_not_universal=True,previous_uncovered=old['uncovered'])
(HERE/'family-candidates-v2.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(found=len(families),uncovered=gaps)))
