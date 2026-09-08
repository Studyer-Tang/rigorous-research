"""Postprocess all frozen extension cells; no new simulation or selection."""
import json
import math
from fractions import Fraction
from pathlib import Path
from statistics import NormalDist

HERE = Path(__file__).resolve().parent
normal = NormalDist()


def wilson(p, n, z):
    scale = 1 + z*z/n
    center = (p + z*z/(2*n))/scale
    radius = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))/scale
    return [center-radius, center+radius]


rows = []
for action_id in range(10, 14):
    action = json.loads((HERE/'actions'/f'{action_id:03d}.json').read_text())
    assert action['execution'] == 'SUCCEEDED'
    args = action['proposal']['action']['arguments']
    result = action['result']['result']
    for method, estimate in result['methods'].items():
        p, n = estimate['coverage'], result['replications']
        count = round(p*n)
        assert abs(count/n-p) < 1e-12
        rows.append(dict(action=action_id, innovation=args['distribution'], lags=args['hac_lags'],
                         method=method, replications=n, covered=count, coverage=p,
                         empirical_mc_se=math.sqrt(p*(1-p)/n),
                         wilson95=wilson(p,n,normal.inv_cdf(.975)),
                         bonferroni_wilson8=wilson(p,n,normal.inv_cdf(1-.05/16))))

phi = Fraction(4,5)
limits = []
for lag in (8,25):
    ratio = 1-2*phi*(1-phi**(lag+1))/((lag+1)*(1-phi*phi))
    direct = (1+2*sum((1-Fraction(k,lag+1))*phi**k for k in range(1,lag+1)))/((1+phi)/(1-phi))
    assert ratio == direct
    limits.append(dict(lags=lag, variance_ratio_exact=str(ratio), variance_ratio=float(ratio),
                       limiting_coverage=2*normal.cdf(1.96*math.sqrt(float(ratio)))-1))
out = dict(scope='All eight marginal method-cell coverages; approximate intervals, no paired test',
           rows=rows, fixed_lag_limits=limits, iid_limit=2*normal.cdf(1.96/3)-1,
           ideal_critical_value_coverage=2*normal.cdf(1.96)-1)
(HERE/'uncertainty.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
table = ['| 创新 | L | 方法 | 覆盖率 | MC SE | 边际 95% Wilson | 八项 Bonferroni-Wilson |',
         '|---|---:|---|---:|---:|---|---|']
for row in rows:
    a,b=row['wilson95'];c,d=row['bonferroni_wilson8']
    table.append(f"| {row['innovation']} | {row['lags']} | {row['method']} | {row['coverage']:.4f} | {row['empirical_mc_se']:.4f} | [{a:.4f}, {b:.4f}] | [{c:.4f}, {d:.4f}] |")
(HERE/'uncertainty-table.md').write_text('\n'.join(table)+'\n',encoding='utf-8')
print(json.dumps(out,indent=2))
