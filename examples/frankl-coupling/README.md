# A certified obstruction to monotone inverse-multiplicity coupling

[English](README.md) | [简体中文](REPORT.zh-CN.md)

**Frankl remains unresolved.** This continuation refutes an auxiliary hypothesis proposed during
the investigation: that stronger inverse-union-multiplicity weighting always increases union entropy.
It does not refute Frankl, establish a new frequency bound, or contradict the fixed-exponent result
in [Jiang, Section 10](https://arxiv.org/html/2609.08291v1). No novelty claim is made.

The archive contains actual hosted actions 16–23, following the checksum-linked
[earlier 15-action record](../frankl-frontier/README.md). The local study remains ready to continue.

## Finite certified counterexample

Let F contain every subset of {1,2,3}, together with T={1,2,3,4}. It has nine distinct members and
is union-closed. In bit-mask order [0,1,2,3,4,5,6,7,15], the ordered union multiplicities are
[1,3,3,9,3,9,9,27,17]. Its maximum element frequency is 5/9.

For theta>=0 define P_theta as the unique minimizer of

\[
\sum_{A,B}P(A,B)\ln\frac{P(A,B)}{r(A\cup B)^{-\theta}}
\]

with both marginals uniform on F. Let H_theta be the entropy of A union B, in nats. Actual actions
17 and 18 independently certify

\[
H_4\ge107/50=2.14,\qquad H_8\le53/25=2.12.
\]

The bounds are disjoint. They are bounds for the **true minimizers**, not just numerically balanced
matrices: the checker uses exact rational marginal constraints, an optimality-error estimate and
entropy continuity, with outward rational logarithm bounds. The implementation is not itself
formally verified. Its mathematical specification is in [coupling certificates](../../references/coupling-certificates.md).

This example has maximum frequency above 1/2. It does not settle a monotonicity statement restricted
to sub-half frequencies. The failed general monotonicity route is preserved as abandoned, while
the original frequency-gap research route remains open.

## A family approaching the half-frequency boundary

This section is a written proof draft, not formalized code or a claim of originality.
For k>=3 let F_k=2^[k] union {T}, T=[k+1], U=[k], and N=2^k+1. Then

\[
r(S)=3^{|S|}\quad(S\subseteq[k]),\qquad r(T)=2N-1,\qquad
p_{\max}=\frac{N+1}{2N}.
\]

Consider the linear cost c(A,B)=ln r(A union B). A permutation cycle inside the cube has cost at
least its diagonal cost, with equality only for fixed points: every union contains its first set,
and equality throughout a cycle forces all its sets to coincide.

A nontrivial cycle T,A_1,...,A_m,T has excess over diagonal cost

\[
\ln(2N-1)-|A_1|\ln3+
\sum_{i=1}^{m-1}|A_i\setminus A_{i+1}|\ln3
\ge\ln(2N-1)-k\ln3.
\]

Equality forces A_1=U and successive inclusions A_i subseteq A_{i+1}; distinctness then forces m=1.
For k>=3, 3^k>2N-1. Thus the unique minimum-cost permutation exchanges U and T and fixes every
other member. Birkhoff decomposition makes its uniform permutation matrix the unique minimum
linear-cost coupling.

Comparison of the entropically regularized objective at P_theta and at this permutation coupling
bounds the excess linear cost by ln(N)/theta, because joint entropy with uniform marginals lies
between ln N and 2 ln N. Compactness and uniqueness imply convergence to that permutation coupling.
Consequently the limiting union law has mass 0 at U, 2/N at T and 1/N elsewhere, giving

\[
\lim_{\theta\to\infty}H_\theta=\ln N-\frac{2\ln2}{N}.
\]

Writing delta=p_max-1/2=1/(2N), its deficit from ln N is exactly 4 delta ln 2. This is a useful
boundary check for candidate gap-dependent inequalities, not such an inequality for arbitrary families.

For k=3, all 9!=362,880 permutations were evaluated using integer products rather than floating
logs. The unique minimizer is the transposition above; its product is 5,688,387. The replay checks
this using a different subset dynamic program. Action 22 also exactly checks that the limiting
law's entropy is below 2.95 bits. Neither finite check substitutes for the general argument.

## Reproduce

Install `[agent,math]`, then run `python examples/frankl-coupling/reproduce.py` from the repository root.
The replay verifies the archive chain, reconstructs all unions with Python sets, checks kernel and
event-label translation, rechecks three certificates, reruns both optimizer tools and independently
solves the finite assignment problem. No network or model calls occur during replay.

The remaining target is a rigorously justified frequency-gap-sensitive coupling argument sufficient
for the full Frankl conjecture. Simply increasing theta is no longer a valid general strategy.
