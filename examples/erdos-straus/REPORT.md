# Erdős–Straus investigation: an unresolved conjecture and a refuted proof route

**Original conjecture: INCONCLUSIVE. Novelty: NOT CLAIMED.** This investigation does not prove or disprove the Erdős–Straus conjecture. It establishes a finite collection of exact witnesses and a specific obstruction to a natural greedy proof route. It uses the project's workspace, symbolic certificates, independent checks, evidence ledger, and release validation.

中文：原猜想仍未解决。本次验证了 `3 <= n <= 10000` 的全部 9,998 个输入，严格否定了“总取最小首分母”的证明路线，并记录了几类无限解族及其未覆盖部分。这些是可复现的工具实测与已有初等数学的推导，不声称发现新的数学定理或推进了公开计算纪录。

## Claim and source coverage

For every integer `n >= 3`, do positive integers `x < y < z` exist with

\[
\frac4n=\frac1x+\frac1y+\frac1z?
\]

The [status audit](sources/status.md) records two retrieved secondary sources that still describe the problem as open, along with a limited Crossref search. The problem directory reports much larger existing verification bounds. Searching to 10,000 here tests the toolkit; it is not a new computational result. Neither a paper title nor an empty counterexample search settles public status.

## Exact finite experiment

Every integer from 3 through 10,000 has an explicit, sorted, distinct positive-integer witness in [finite-search.json](artifacts/finite-search.json). The [independent check](artifacts/independent-check.json) validates the full declared interval without missing or duplicate entries and recomputes

\[
4xyz=n(xy+xz+yz)
\]

using integer arithmetic. It does not call the search producer or trust a stored success flag. There are 9,165 witnesses from elementary constructions and 833 from divisor search. The deterministic budget counted 248,271 work units out of a 1,000,000-unit limit; these units count search operations, not CPU instructions or elapsed seconds. A separate one-unit experiment records 97 unresolved inputs and returns `INCONCLUSIVE`.

For an ordered solution, `n/4 < x <= 3n/4`. Once `x` is fixed, reduce `4/n-1/x=a/b` to lowest terms. Then

\[
\frac ab=\frac1y+\frac1z
\quad\Longleftrightarrow\quad
(ay-b)(az-b)=b^2.
\]

Both factors are positive. Enumerating divisor pairs `d <= b` of `b^2`, with `d+b` and `b^2/d+b` divisible by `a`, enumerates the possible ordered completions for that fixed `x`. The producer factors `b` by trial division, enumerates divisors of `b^2`, then checks order and distinctness. It tries at most 64 first denominators per input and shares an operation budget across the entire requested interval. An unsuccessful bounded search yields unresolved inputs, never a conjecture refutation. Every returned witness is conclusive for its particular `n`, regardless of whether the search was exhaustive.

## A rigorous obstruction to the greedy route

The attempted strengthening was: choosing `x=floor(n/4)+1` always leaves a sum of two positive unit fractions. Exact searches for `3 <= n <= 49` first fail at `n=49`, where `x=13` and

\[
\frac4{49}-\frac1{13}=\frac3{637},\qquad 637=7^2\cdot13.
\]

Suppose `3/637=1/y+1/z` for positive integers `y,z`. Each reciprocal is smaller than `3/637`, hence `3y-637` and `3z-637` are positive integers. Clearing denominators gives

\[
(3y-637)(3z-637)=637^2=7^4\cdot13^2.
\]

Every positive divisor of the right side is `1 mod 3`, since both primes are `1 mod 3`. But `3y-637` is `2 mod 3`. This contradiction proves that no such completion exists, even when repeated denominators are allowed. The [modular certificate](artifacts/greedy-obstruction.json) independently checks primality, the complete factorization, the reduced remainder, and this modular contradiction. The [symbolic reduction](artifacts/greedy-reduction.json) separately checks the algebraic expansion.

This refutes the greedy strengthening, not the original conjecture: `n=49` has the distinct witness

\[
\frac4{49}=\frac1{14}+\frac1{99}+\frac1{9702}.
\]

The argument is presented as an elementary rediscovery and a test of the project. Its originality has not been established. The correspondence from the machine-scoped obstruction to this prose remains an explicit review obligation; no human review was fabricated.

## Infinite families and the remaining gap

Let `t` be a positive integer. Direct substitution gives these distinct positive-integer solutions:

| Input | x | y | z |
|---|---|---|---|
| `n=2t+2` | `t+1` | `t+2` | `(t+1)(t+2)` |
| `n=4t-1` | `t` | `(4t-1)t+1` | `(4t-1)t((4t-1)t+1)` |
| `n=3t+2` | `t+1` | `3t+2` | `(t+1)(3t+2)` |
| `n=8t-3` | `2t` | `(8t-3)t` | `2(8t-3)t` |

The [symbolic certificates](artifacts/residue-families.json) independently establish the rational equalities. Integrality follows from the integer polynomial formulas. For the first family `t+1 >= 2`, so the product exceeds `t+2`. For the second, put `m=(4t-1)t >= 3`; then `t < m+1 < m(m+1)`. For the third, `t+1 < 3t+2` and `t+1 >= 2`. For the fourth, `8t-3 >= 5 > 2` and `t > 0`, so `2t < (8t-3)t < 2(8t-3)t`. These inequalities establish positivity and strict order in each family. Symbolic equality checks alone do not certify those prose arguments.

If `m` has a distinct solution, multiplying all three denominators by a positive integer `k` gives one for `km`, preserving order. Even inputs are covered by the first family; every odd composite has an odd prime divisor. The second family includes `n=3`. For primes greater than 3, the possible residues modulo 24 are `1,5,7,11,13,17,19,23`; the displayed families cover all except residue 1. Thus this elementary route leaves primes `p=1 mod 24` unresolved. Infinitely many such primes exist; no finite search or mere increase in the search budget closes the missing argument. The public source reports stronger known reductions, so this one is not a new result.

## What using the project revealed

| Observed behavior | Strength or weakness | Change in this version |
|---|---|---|
| Search results included a title claiming a complete proof | Candidate labeling correctly avoided treating metadata as mathematical evidence | Preserve the candidate matrix and explicitly document status uncertainty |
| Symbolic tools checked residue identities | Exact arithmetic and retained domains were useful | Reuse those tools instead of adding a second symbolic engine |
| Existing mathematics commands could not express an interval of integer existential claims | Needed typed integer witnesses, distinctness, and explicit quantifier coverage | Add a standard-library integer search and a separate independent checker |
| Greedy failure could be confused with failure of the full conjecture | Needed a fixed-first-denominator obstruction with narrower semantics | Add a checked modular obstruction and keep the original claim inconclusive |
| An inconclusive tool exits with code 1 | Workspace previously treated a documented scientific outcome as a failed program | Record explicitly accepted exit codes while preserving actual codes; timeouts, launch failures, and missing outputs still fail |
| A positive finite certificate could be overinterpreted in prose | Proof and translation obligations remain essential | Store universal and finite claims separately; leave translation review open |

The new integer checker uses no SymPy and does not import the producer. Its trusted assumptions are Python's exact integer arithmetic and the implemented finite-check/modular argument. It is not a formally verified proof-assistant kernel. General Diophantine nonexistence, autonomous discovery of proof strategies, authenticated reviewer identities, and automatic checking of arbitrary prose remain unsupported.

## Reproduce

From a repository checkout with `.[math]` installed:

```text
python examples/erdos-straus/reproduce.py --output build/erdos-straus-replay
rigorous-research verify-certificate build/erdos-straus-replay/finite-search.json
rigorous-research verify-certificate build/erdos-straus-replay/greedy-obstruction.json
rigorous-research workspace validate examples/erdos-straus/workspace.json --release
```

Use a separate output directory: regenerating timestamped symbolic certificates inside the released example intentionally invalidates recorded hashes. The original run log records its actual Windows interpreter path; the commands above are the portable replay route. An inconclusive report can pass release validation when it documents evidence and open obligations; release success does not mean the conjecture was solved.
