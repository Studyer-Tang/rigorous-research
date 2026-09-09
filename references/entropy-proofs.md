# Exact finite entropy comparisons

Use `entropy_inequality` to check

\[
\sum_j w_j H(f_j(X))\ge c
\]

in bits, for **one recorded finite distribution**. `counts` specifies nonnegative integer atom masses;
normalize by their positive sum. Each term supplies a rational-string `coefficient` and a `labels`
array assigning every atom to a bin. The entropy is that of these aggregated bins, not of the original
counts unless every atom has a different label. Zero masses are allowed with 0 log 0 = 0.

```json
{
  "tool": "entropy_inequality",
  "arguments": {
    "counts": [9, 6, 6, 4],
    "terms": [
      {"coefficient": "1", "labels": [0, 1, 1, 1]},
      {"coefficient": "-1", "labels": [0, 0, 1, 1]}
    ],
    "constant": "0",
    "max_bits": 500000
  }
}
```

For atoms (0,0),(0,1),(1,0),(1,1), this compares H(X OR Y) with H(X) under independent Bernoulli(2/5)
inputs. The exact result is negative. It refutes the distribution-level entropy-growth claim at this
law, **not** Frankl's union-closed conjecture: the latter concerns uniform measures on families of
distinct sets, and this law is nonuniform.

## Why the comparison is exact

For marginal counts c_i with total N,
H = log2 N - sum_i (c_i/N) log2 c_i. The checker groups these logarithms across terms, subtracts
c log2 2, clears rational denominators with a positive integer L, and compares two integer products.
Their ratio is 2 raised to L times the desired difference, so its comparison with 1 gives the exact sign.
No logarithm approximation or numerical tolerance enters the verdict. The producer's approximate
difference is a diagnostic only. `computation.sign` distinguishes equality from strict positivity.

The checker accepts 1–1024 atoms, each count at most 1,000,000; 1–32 partitions; and rational coefficients
whose numerator and denominator have at most eight decimal digits. The `max_bits` budget is 1,000–500,000
for a conservative combined product size estimate. Large denominators can exceed this budget even for
a small problem, yielding `INCONCLUSIVE`. Symbolic cancellation is limited; no completeness claim is made.

## Research obligations

- Verify that atom labels encode the intended variables, unions or conditioning events.
- Check marginal preservation, independence, uniformity and support assumptions separately. Equal
  entropies do not imply equal distributions.
- Express conditional entropies as H(X,Y)-H(Y) using partitions of the same joint atoms.
- A finite checked example cannot establish tensorization, a universal entropy inequality or a
  bound over a continuous parameter region. Conversely, a negative example can refute a universal
  claim only when every required hypothesis has been verified.
- A title claiming a conjecture proof is candidate evidence. Read its derivation and seek independent
  confirmation. Recent numerical or computer-assisted bounds retain their stated qualifications.

The current [Frankl research report](../examples/frankl-frontier/README.md) documents actual use and
the next unsolved proof obligation.
