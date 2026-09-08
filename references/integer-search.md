# Integer existence and finite witnesses

Use this route for `a/n = 1/x + 1/y + 1/z` with positive integer denominators. It handles finite input domains, not arbitrary Diophantine equations. The [Erdős–Straus case study](https://github.com/Studyer-Tang/rigorous-research/blob/main/examples/erdos-straus/REPORT.md) records actual use, a failed proof route, and unresolved universal obligations.

```text
rigorous-research egyptian --numerator 4 --start 3 --stop 10000 --distinct --output build/finite.json
rigorous-research verify-certificate build/finite.json --output build/finite-check.json
```

`--distinct` requires `x < y < z`; omitting it permits repeated denominators with `x <= y <= z`. These are different claims. The numerator is 1..100, input denominators are 1..1,000,000, and an invocation covers at most 10,000 inputs. The certificate records the exact inclusive interval. Larger or universal claims cannot be appended to its `claim` object and silently ignored.

## Search and work limits

Elementary explicit constructions handle several residue classes when `a=4`. Otherwise the producer tries possible first denominators and enumerates divisor pairs for the reduced residual using `(ay-b)(az-b)=b^2`. The trial factorization, candidate search, and divisor generation spend a shared deterministic work budget.

`--max-x` limits first denominators per input (default 64, maximum 10,000). `--max-work` limits counted operations across the entire invocation (default 1,000,000, maximum 10,000,000). This is not a CPU or memory sandbox. For wall-clock isolation, use `workspace run --timeout ...`. If either bound prevents finding a witness, the input stays in `unresolved`. No missing witness is reported as a counterexample, even if a particular internal search happened to exhaust its range. Nonexistence needs independently checkable evidence.

The producer returns exit code 0 if the independent check establishes all finite witnesses, 1 for an inconclusive or rejected result, and 2 for invalid input. Always inspect the independent result's `status` and `errors`. In a workspace, `--accept-returncode 1` may record a documented scientific outcome without treating it as a crashed process; the raw exit code and artifacts remain visible and no case verdict is changed.

## Independent semantics

The `exact-integer` backend has two operations, checked by `integer_certificate_verifier.py` without importing the search producer or SymPy:

- `three-unit-fractions-finite`: checks integer types (booleans and floats are rejected), positive denominators, ordering/distinctness, exact cross multiplication, and complete coverage of the finite interval by witnesses or explicit unresolved entries. It derives `ESTABLISHED` only when every input has a valid witness; otherwise `INCONCLUSIVE` or `INVALID`.
- `two-unit-fractions-obstruction`: checks one fixed first denominator. It reduces the positive residual `a/b`, validates a complete prime factorization of `b`, proves every divisor of `b^2` equals 1 modulo `a`, and requires `-b mod a != 1`. This proves the impossibility of a two-term completion for that fixed choice. Prime bases are at most 1,000,000 and are checked by trial division. Other nonexistence arguments remain unsupported.

The obstruction is an established negative statement about a restricted problem. It does not refute the original three-term existence claim; a different first denominator may work. The ordinary certificate and strict receipt commands support both operations. Their scope is always the explicit finite domain or fixed-denominator obstruction.

## Open-conjecture workflow

1. Record the precise statement, allowed repetitions, domain boundaries, source, access date, and how far public-status/novelty checks went. Metadata and self-described proof titles are candidates rather than proof evidence.
2. Separate the universal conjecture from finite claims, parameterized families, and stronger proposed proof routes. Register each result with its actual scope.
3. Independently verify returned witnesses. For symbolic families, check equality and separately justify positivity, integrality, distinctness, and exhaustive coverage. Record the uncovered residue classes or other remaining obligations.
4. Preserve useful inconclusive outcomes. An exhausted budget or failed construction is a research result about that attempt, not proof of the opposite mathematical statement. A release may honestly remain inconclusive.

Machine checks establish only the encoded subclaim. Prose translation review, general proof discovery, and novelty evaluation are separate obligations. Never fabricate human review to close them.

## Native Agent research tools

Version 1.12 shares the following typed tools between Codex-hosted, API and MCP execution. All producer
certificates pass through a separate checker process within the same wall deadline.

- `egyptian`: `numerator`, `start`, `stop`, `distinct`, `max_x`, `max_work`; the finite semantics above.
- `egyptian_window`: `numerator`, `denominator`, `start_x`, `stop_x`, `distinct`, `max_work`. At most 64
  consecutive first denominators. The claim is existence of an ordered completion in this explicit window.
- `egyptian_scan`: `numerator`, `start`, `stop`, `step`, `width`, `distinct`, `max_work`. At most 256 inputs
  in the inclusive progression and width 1..16. Each starts at floor(n/numerator)+1. Stops at the first
  refuted or unresolved window, sharing one work budget. Refutation needs one checked obstructed window;
  establishment needs a checked witness at every input in the progression. Untested suffixes remain visible.
- `egyptian_family`: `numerator`, `n`, `x`, `y`, `z`, `distinct`. Each polynomial is an array of integer
  coefficients in ascending degree, length 1..13, coefficient magnitude at most 10^18. The parameter is
  exactly an integer t>=0; n(t)>=1 and positive ordered denominators are part of the certificate claim.

For example, `n=[97,120]`, `x=[25,30]`, `y=[970,2364,1440]`, `z=[4850,11820,7200]`,
`numerator=4`, `distinct=true` describes a whole infinite arithmetic progression, not a finite grid.

For a positive reduced residual a/b, every completion satisfies `(ay-b)(az-b)=b^2` with positive factors.
Ordering y<=z restricts the first factor d to d<=b. The window verifier validates the full factorization
of b, enumerates all divisors of b^2 independently, checks both congruences and the required order.
That exhaustiveness permits `REFUTED` for the explicit window. Budget exhaustion cannot create an obstruction.
This complements the older narrow all-primes-equal-one modular certificate; it does not change its semantics.

The family producer uses SymPy. The verifier uses its own integer polynomial multiplication and addition,
checking `a*x*y*z = n*(x*y+x*z+y*z)` coefficient by coefficient. Integer inputs guarantee integrality;
nonnegative coefficients of n-1, x-1, y-x-delta and z-y-delta prove positivity and order for t>=0,
where delta=1 for distinct and 0 otherwise. A supplied counterexample parameter is evaluated exactly.
Producer booleans are not trusted. An identity or positivity claim outside this sufficient fragment remains
`INCONCLUSIVE` without a checked counterexample. Changing the parameter domain or hiding a coefficient is invalid.

The new certificate operations are `three-unit-fractions-window`, `three-unit-fractions-window-scan`
and `unit-fraction-polynomial-family`. A constant n(t) covers one input even though t ranges infinitely;
an increasing n(t) covers only its image. Neither closes the original conjecture or a prose translation gate.
