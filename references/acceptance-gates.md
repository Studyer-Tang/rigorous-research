# Acceptance gates

## Gate design

Define gates before substantial execution. Each gate needs an observable condition, command or inspection method, expected result, and evidence destination. Prefer project-native checks over invented proxies.

Common gate families:

- **scope:** delivered object matches the exact target;
- **correctness:** proof obligations or functional tests pass;
- **coverage:** intended cases were actually collected and exercised;
- **runtime:** the artifact runs in the target environment;
- **reproducibility:** a clean rerun can reproduce the decisive output;
- **artifact:** output exists, is nonempty, parseable, and loadable;
- **safety:** no secret leakage, unsafe exposure, or unauthorized mutation;
- **claim:** title, abstract, and summary stay within supported scope.

## Test-suite audit

Do not reduce validation to a final exit code. Record:

- collection exit status;
- number collected, passed, failed, skipped, deselected, and xfailed;
- warnings that affect validity;
- exact exclusions or filters;
- platform and dependency versions;
- whether tests exercise the changed or claimed behavior.

Collection failure is a failed gate. Zero collected tests is a failed gate unless zero is explicitly expected and justified. A filtered subset cannot validate the full suite; label it as targeted evidence.

## Experiments and benchmarks

Freeze dataset version, split, metric, baseline, hardware where relevant, seed policy, stopping rule, and comparison protocol. Guard against leakage, cherry-picking, repeated tuning on the test set, and incomparable hardware or budgets. Report variance or uncertainty when the procedure is stochastic.

## Reproductions

Separate:

- environment reproduction;
- code-path reproduction;
- metric reproduction;
- scientific-claim reproduction.

Success at an earlier layer does not imply success at a later one. Record deviations from the source procedure and quantify their likely effect.

## Release decision

Release may pass only when:

1. every critical obligation is `SUPPORTED` or deliberately `NOT_APPLICABLE` with justification;
2. every acceptance criterion passes with evidence;
3. no decisive artifact checksum has changed or disappeared;
4. independent review accepts the scoped claim;
5. strongest safe and strongest unsupported nearby claims are both recorded;
6. the top-level verdict is compatible with branch verdicts and failed obligations.

The ledger validator enforces structural portions of these rules. Human or agent review must judge whether the evidence is substantively adequate.

