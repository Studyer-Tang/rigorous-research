# Certified entropy of a matrix-scaling optimizer

`coupling_entropy` concerns the unique minimizer P* of

\[
F(P)=\sum_{ij}P_{ij}\ln(P_{ij}/K_{ij})
\]

over square nonnegative probability matrices with every row and column sum equal to 1/n. K must
be strictly positive; it need not itself be normalized. `labels[i][j]` assigns each matrix cell to an
event bin. The claim bounds the **event entropy of P*** in **nats**, using `relation` (`>=` or `<=`)
and an exact rational `bound`. It does not claim to maximize event entropy.

The producer uses mpmath for alternating row/column scaling, then rounds to a strictly positive
integer-count matrix with exactly uniform marginals. `digits` (6–16) and `max_iterations` (1–8192)
bound this attempt. Missing convergence or a failed positive rounding gives no approximation and
therefore `INCONCLUSIVE`. A supplied approximation that fails exact checking is rejected.

The certificate carries rational scaling factors, exact counts and a chosen continuity radius
`delta` in [0,1/2]. Matrix size is 2–16. Counts are positive integers up to 10^18; rational inputs
have at most 40 digits in each numerator and denominator. These limits may exclude valid problems.
The existing worker/checker wall deadline applies.

## Mathematical justification of the checker

The following derivation is part of the method's mathematical specification; the implementation
is independently checked software, not a formally verified proof assistant.

**Existence and scaling.** The feasible polytope is compact and contains the uniform positive
matrix. The continuous objective (with 0 ln 0 = 0) is strictly convex, so it has a unique minimizer.
Mixing a boundary minimizer with the uniform matrix produces negative s ln s terms at its zeros,
which dominate the O(s) terms elsewhere; hence the minimizer is positive. Lagrange multipliers for
the row/column constraints then give P*_{ij}=a_i K_{ij} b_j with positive factors.

Let R be the supplied positive matrix with exactly uniform marginals, and u_i,v_j its proposed
scaling factors. The checker computes

\[
\rho_{ij}=R_{ij}/(u_iK_{ij}v_j),\qquad
\epsilon=\max_{ij}\{\rho_{ij}-1,\rho_{ij}^{-1}-1\}.
\]

The inequality ln t <= t-1 implies |ln rho| <= epsilon. The exact scaling equation for P* and
the equal row/column marginals give F(R)-F(P*)=D(R||P*). Convexity at R gives

\[
D(R\|P^*)\le\langle\nabla F(R),R-P^*\rangle
=\sum_{ij}(R_{ij}-P^*_{ij})\ln\rho_{ij}\le2\epsilon.
\]

Row-factor, column-factor and constant terms vanish in the equality. Pinsker's inequality in nats
gives TV(R,P*) <= sqrt(epsilon). For completeness, Pinsker follows by the log-sum inequality,
grouping cells where R>P*, and the binary bound D(Bern(p)||Bern(q))>=2(p-q)^2; the latter follows
from second derivative 1/(p(1-p))>=4 and equality of value/first derivative at p=q.

The checker requires epsilon <= delta² using exact fractions. Aggregating cells into event bins
does not increase total variation. If there are m>=2 bins, maximal coupling of the event laws
with mismatch probability t gives

\[
|H(\nu_R)-H(\nu_*)|\le h(t)+t\ln(m-1)
\le h(\delta)+\delta\ln(m-1).
\]

The first inequality follows by conditioning on the mismatch indicator: on mismatch there are
at most m-1 alternatives. The second holds because the expression is increasing up to 1-1/m,
and delta<=1/2. A single event bin has entropy zero and requires no continuity correction.

**Rational logarithms.** Write x=2^k r with 1<=r<2 and z=(r-1)/(r+1). Then

\[
\ln r=2\sum_{j=0}^{M-1}\frac{z^{2j+1}}{2j+1}+T_M,
\qquad 0\le T_M\le\frac{2z^{2M+1}}{(2M+1)(1-z^2)}.
\]

The same series at z=1/3 bounds ln 2. Negative k swaps interval endpoints. Every series evaluation
and entropy sum is rounded outward onto rational multiples of 10^-24; rounding is performed with
integer floor/ceiling. The checker uses 16 series terms, explicit tail bounds and no floating logs.

Combining the entropy interval of R with the continuity error yields an interval for the true
optimizer's event entropy. A bound entirely on the required side is established; one entirely on
the opposite side is refuted; an overlap remains inconclusive.

## Scope

The certificate verifies this optimization problem, not the host's translation from a set family
or theorem. Verify union multiplicities, event labels, logarithm units and parameter values separately.
See the [monotonicity obstruction](../examples/frankl-coupling/README.md) for a reproducible use that
checks this translation with a second set-based implementation.
