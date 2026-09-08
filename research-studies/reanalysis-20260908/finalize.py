"""Deliver completed scoped reports without changing original claim verdicts."""
import json
import subprocess
import sys

from host import HERE, ROOT, Study, sha256, submit, write_json
from research_workspace import load, validate_workspace

notes = {
    'erdos': (
        'For n=24t+1,t>=1,x=6t+1,b=nx: greedy completion exists iff b has a prime factor q=2 mod3. '
        'Necessity: (3y-b)(3z-b)=b^2 has positive factors, the first 2 mod3; if all primes of b are 1 mod3 this is impossible. '
        'Sufficiency: y=b(q+1)/(3q),z=q*y are integral, positive, and x<y<z since n>=25 and odd b forces q>=5. '
        'The q=5 subfamily is n=120s+97, x=30s+25, y=2n(6s+5), z=10n(6s+5), s>=0. '
        'General reasoning is a written proof, not a formal certificate or human-reviewed result. '
        'Independent finite audit: 416 cases,275 greedy successes,141 obstructions,zero criterion mismatches. '
        'Unrestricted finite replay exactly matches the old artifact hash and gives 9998 witnesses. Original conjecture unresolved; novelty not audited.',
        [3,4,5,6], ['greedy-audit.json','unrestricted-replay.json','unrestricted-check.json']),
    'statistics': (
        'All six legacy result dictionaries exactly reproduce. All four frozen exploratory extension cells completed: '
        'Gaussian L8=.8566,L25=.9160; t3 L8=.8548,L25=.9172, each 5000 replications and n=2000,phi=.8. '
        'Finite-variance innovation CLT, negligible endpoints and fixed-lag ergodic covariance consistency yield '
        'coverage limit 2Phi(1.96sqrt(rho_L))-1, rho_L=1-2phi(1-phi^(L+1))/((L+1)(1-phi^2)). '
        'At phi=.8 limits are .8619119018484576 for L8 and .925769387921012 for L25. '
        'The t3 argument uses finite second moments, not nonexistent fourth moments. '
        'Empirical MC SE, marginal Wilson and approximate eight-comparison Bonferroni-Wilson intervals are in uncertainty.json. '
        'No paired indicators were retained, so no paired test is claimed. General argument remains prose; simulation does not prove applicability.',
        [1,2,3,4,5,6,7,8,9,10,11,12,13], ['replication-check.json','uncertainty.json','extension-plan.json']),
    'goldbach': (
        'Independent recorded-arithmetic audit passed on 494 rows, directed global sums and recorded dependency hashes; '
        'it does not independently validate analytic bounds or reconstruct all geometry. Hessian share=99.8989333%. '
        'The fixed-center obstruction motivates geometry refinement, not a conclusion about the true integral. '
        'Actual experiment exactly reproduced the widest triangle then split it into four and recomputed local centers and bounds: '
        'radius 10002.130374177372 -> 853.2577448645017, reduction11.722284895012258; '
        'center -.0003117596728436075 -> -.0000916746132377151. This used the same analytic producer. '
        'One-cell improvement does not imply global convergence or a valid full integral certificate. '
        'Action2 was an intentional negative control, not a discovered legacy defect. Li14 and Goldbach remain unresolved.',
        [3,4,5,6], ['record-audit.json','subdivision-probe.json'])
}

manifest = json.loads((HERE/'source-manifest.json').read_text())
source_checks = [dict(path=row['path'], matches=sha256(ROOT/row['path'])==row['sha256']) for row in manifest['sources']]
assert all(row['matches'] for row in source_checks)
assert sha256(HERE/'erdos/unrestricted-replay.json') == sha256(ROOT/'examples/erdos-straus/artifacts/finite-search.json')

checks = {}
for topic, (message, evidence, files) in notes.items():
    study = Study(HERE/topic)
    report = HERE/topic/'REPORT.zh-CN.md'
    assert report.is_file()
    if study.state()['execution'] != 'DELIVERED':
        hashes = '\nArtifacts: '+json.dumps({name:sha256(HERE/topic/name) for name in files})
        note = submit(topic,'note',{'text':message+hashes},
                      'Integrate the observed results and precise limitations into the live Agent record.',
                      'Recheck exact claims against artifacts; a changed hash, wrong domain or missing analytic assumption invalidates the associated conclusion.',evidence)
        submit(topic,'finish',{'text':f'Scoped reanalysis report delivered: {report.relative_to(HERE)}; SHA256={sha256(report)}. '
                                 +message+' Original objective status remains UNRESOLVED. No novelty claim or fabricated human review.'},
               'Deliver the completed research report and retain unresolved original goals.',
               'Delivery is not a proof verdict. General proof, analytic certificate and model applicability require their stated separate obligations.',[note['id']])
    workspace = HERE/topic/'workspace.json'
    for task in ('W001','W002'):
        subprocess.run([sys.executable,str(ROOT/'scripts/research_workspace.py'),'set-task',str(workspace),
                        '--id',task,'--status','DONE','--note','Scoped deliverable exists and was checked; original research claim remains unresolved.'],check=True,capture_output=True)
    subprocess.run([sys.executable,str(ROOT/'scripts/research_workspace.py'),'set-stage',str(workspace),'--stage','SYNTHESIS'],check=True,capture_output=True)
    path,data=load(workspace)
    errors,warnings=validate_workspace(data,path,release=False)
    assert not errors, errors
    export=study.export()
    assert export['state']['execution']=='DELIVERED'
    assert export['state']['objective_status']=='UNRESOLVED'
    write_json(HERE/topic/'ledger.json',export)
    checks[topic]=dict(workspace_errors=errors,workspace_warnings=warnings,execution=export['state']['execution'],
                       objective_status=export['state']['objective_status'],actions=len(export['actions']),
                       case_decision=json.loads((HERE/topic/'case.json').read_text()).get('decision'))

artifacts = {str(p.relative_to(HERE)):sha256(p) for p in sorted(HERE.rglob('*'))
             if p.is_file() and p.suffix in {'.json','.md','.py'} and p.name!='verification.json'}
write_json(HERE/'verification.json',dict(old_sources=source_checks,all_old_sources_unchanged=True,
           unrestricted_replay_byte_identical=True,studies=checks,artifact_sha256=artifacts,
           release_validation=False,formal_proof_or_human_review=False,publication='local only'))
print(json.dumps(checks,ensure_ascii=False,indent=2))
