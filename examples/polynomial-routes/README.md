# Polynomial research routes — actual hosted run

[English](README.md) | [简体中文](REPORT.zh-CN.md)

On 2026-09-09, the host model submitted 17 real actions through `Study.submit`, selected subsequent
routes from observed outputs, and extended the implementation when the run exposed a missing proof
rule. `ledger.json` preserves the actions, one execution failure, seven successful mathematical
certificates, route changes and an honest final report. No external model API was called.

These are **known mathematical benchmarks**, not a solved open conjecture, novelty claim, formal
verification of the checker, or measured improvement in an underlying model. The regression replay
below is deterministic and does not reproduce the model's reasoning or demonstrate autonomous discovery.

| Actions | Question and result | What supplied the proof? |
|---|---|---|
| 2–3 | Coefficient 1/2 in the three-variable Cauchy bound fails at (-1,-1,-1). Action 2 exposed a nested-sum parsing error; action 3 succeeded after its fix. | Exact rational search and independent witness check |
| 5–6 | Coefficient 1/3 is established; a diagonal argument shows it is sharp. | Automatic quadratic square completion; optimality is separate written reasoning |
| 9–10 | Unrestricted weights admit a negative variance numerator; nonnegative weights admit a checked weighted-square identity. | Exact counterexample search; host-supplied algebraic decomposition |
| 12–15 | Quadratic discovery and a 25-point grid leave Motzkin inconclusive; a new checked AM-GM rule establishes it. | Host-supplied AM-GM decomposition, independent product and sum checks |

For the Cauchy bound the automatic tool produced

\[
x^2+y^2+z^2-\frac{(x+y+z)^2}{3}
=\frac23\left(x-\frac y2-\frac z2\right)^2+\frac12(y-z)^2.
\]

For nonnegative p,q,r, the weighted variance numerator is exactly

\[
(p+q+r)(px^2+qy^2+rz^2)-(px+qy+rz)^2
=pq(x-y)^2+pr(x-z)^2+qr(y-z)^2.
\]

Normalized weighted variance additionally requires p+q+r>0. No sampling, independence, identification
or inferential coverage conclusion follows from this identity.

For Motzkin, the three nonnegative addends x⁴y², x²y⁴ and 1 have product (x²y²)³, so AM-GM gives
x⁴y²+x²y⁴+1>=3x²y². The recorded failed quadratic route is preserved rather than rewritten as success.

## Reproduce

Install the repository's `[agent,math]` extras and run from the repository root:

```text
python examples/polynomial-routes/reproduce.py
```

This checks the archive manifest, action/result hashes and seven certificates, then reruns the seven
successful mathematical actions through fresh worker/checker subprocesses. It does not rerun the old
bug as though it still existed, fabricate a model interaction, or compare toolchain hashes from before
the implementation changed. The ledger records those historical hashes for inspection. The manifest
is a local integrity aid, not an external signature. Scientific case/release gates remain separate;
this is a capability benchmark archive, not a released theorem claim.
