"""Explore constant-divisor polynomial completions on the 35 hard residue classes mod840."""
import json
import math
from pathlib import Path

import sympy as sp

HERE = Path(__file__).resolve().parent
t = sp.Symbol('t')
found, gaps = [], []
for residue in range(1, 840, 24):
    base = 841 if residue == 1 else residue
    n = sp.Poly(840*t+base, t, domain=sp.QQ)
    accepted = None
    for k in range(1, 65):
        r = 4*k-1
        x = sp.Poly(210*t+(base+r)//4,t,domain=sp.QQ)
        b=n*x
        if any(int(b.nth(i)) % r for i in (1,2)):
            continue
        square=b*b
        common=math.gcd(*(int(c) for c in square.all_coeffs()))
        for d in sp.divisors(common):
            if d > int(b.nth(0)):
                continue
            y=(b+sp.Poly(d,t)).mul_ground(sp.Rational(1,r))
            z=(b+square.mul_ground(sp.Rational(1,d))).mul_ground(sp.Rational(1,r))
            polys=dict(n=n,x=x,y=y,z=z)
            if any(c.q!=1 for p in polys.values() for c in p.all_coeffs()):
                continue
            if any(c<0 for p in (n-sp.Poly(3,t),x-sp.Poly(1,t),y-x-sp.Poly(1,t),z-y-sp.Poly(1,t)) for c in p.all_coeffs()):
                continue
            accepted=dict(residue=residue,offset=k,residual_numerator=r,divisor=int(d),
                          arguments=dict(numerator=4,distinct=True,**{key:[int(p.nth(i)) for i in range(p.degree()+1)] for key,p in polys.items()}))
            break
        if accepted:break
    if accepted:found.append(accepted)
    else:gaps.append(residue)
out=dict(modulus=840,universe='n>=3,n=1 mod24',method='x=(n+4k-1)/4,k=1..64; positive constant divisor of gcd(coefficients((nx)^2))',
         families=found,uncovered=gaps,coverage_is_not_universal=True)
(HERE/'family-candidates.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(found=len(found),uncovered=gaps)))
