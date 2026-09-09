# Exact polynomial proof contracts

All three native tools record `lhs >= rhs` for **all real values of the declared symbols satisfying
every listed assumption polynomial >= 0**. An empty assumption list means all real inputs. Coefficients
are rational; write `1/3`, not decimals. There are no implicit positive weights, nonzero denominators,
integer domains or strict inequalities. Application assumptions and prose translation remain open.

## Search and proof discovery

`inequality_search` takes `lhs`, `rhs`, `symbols`, `assumptions`, `values`, `max_points`. It tests a
Cartesian grid of exact rational values in the given order, skipping infeasible points. A separately
verified feasible negative value yields `REFUTED`. No witness yields `INCONCLUSIVE`, including a
complete grid or an empty feasible grid. Grid counts are producer diagnostics, not checker-certified
exhaustiveness. The witness alone supports refutation.

`polynomial_sos` takes the same claim fields and `terms`. With empty terms and no assumptions it
automatically completes rational squares for quadratic polynomials, including affine and constant
terms. It forms the homogenized symmetric matrix and performs exact elimination; there is no floating
PSD tolerance. A failed decomposition is inconclusive. Higher degrees or constrained proofs require
model-supplied terms (except the zero identity). This is a bounded proof fragment, not a general SOS solver.

Each term is `{"weight":"1", "square":"x-y", "factors":[0,1]}`. Its mathematical value is

\[
w q(x)^2\prod_{i\in\text{factors}}g_i(x),
\]

where `weight` is a nonnegative rational number and the zero-based factors refer to the declared
nonnegative assumptions. Repeated factors are allowed. The checker reconstructs the exact sum and
requires it to equal `lhs-rhs`; it never trusts a producer's assertion that the identity holds.

## AM-GM beyond square sums

`polynomial_amgm` takes the claim fields, `addends` (2–8 terms in the same nonnegative-term format),
and polynomial `base`. For m addends it checks **both** identities:

\[
\prod_{i=1}^m a_i=b^m,\qquad \mathrm{lhs}-\mathrm{rhs}=\sum_{i=1}^m a_i-mb.
\]

Since every addend is nonnegative, AM-GM proves the latter nonnegative when b>=0. If b<0, the
nonnegative sum already exceeds mb; no unrecorded sign assumption on the base is required. This rule
checks supplied decompositions and does not discover them. For the Motzkin polynomial use squares
`x**2*y`, `x*y**2`, `1`, all weights 1, no factors, and base `x**2*y**2`.

## Boundaries and independent checking

The producer uses SymPy. `polynomial_verifier.py` instead parses a restricted arithmetic AST and
reconstructs sparse polynomials with Python `Fraction`, without importing SymPy or producer code.
Accepted proof formats use rational identities plus nonnegative squares/products or the stated AM-GM
rule. This checker is independently implemented but is **not itself formally verified**.

Limits: 1–6 symbols; 8 assumptions; 32 SOS terms; 500 characters per expression; integer literal powers
0–16; total degree 32; 2,048 monomials; 4,096-bit rational coefficients; 100,000 monomial pairs per product.
Variable denominators, even canceling ones, are rejected. The existing rational-identity tool handles
other domain-guarded expressions. Resource limits or unsupported syntax can reject an otherwise valid
mathematical proof. Agent production and checking share the existing subprocess deadline.

Certificates can be checked through `rigorous-research verify-certificate certificate.json`. A valid
certificate establishes only its recorded conditional inequality. Inconsistent assumptions can define
an empty domain, so mathematical implication alone does not establish applicability or non-vacuity.

See [actual hosted investigation and deterministic replay](../examples/polynomial-routes/README.md).
