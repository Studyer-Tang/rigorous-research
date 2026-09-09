# Frankl conjecture: ongoing entropy-route investigation

[English](README.md) | [简体中文](REPORT.zh-CN.md)

**Original objective, still unresolved:** prove or disprove that every finite union-closed family F
of distinct finite sets with nonempty union has an element occurring in at least |F|/2 members.
Completing tools, reproducing known results or proving auxiliary statements does not complete this objective.

This archive contains 15 actual host-directed Agent actions on 2026-09-09, including literature
retrieval and six independently checked finite entropy calculations. No external model API was used.
The ongoing local study is `research-studies/frankl-20260909`; it remains ready for further actions.

## Sources that changed the route

The arXiv search covered 20 relevance-ranked results for a title containing “union-closed”, submitted
from 2024-01-01 through 2026-09-09. This is bounded coverage, not an exhaustive status or novelty audit.
The initial search failed because the tool prepended a second `all:` to a fielded query. That failure
remains in action 1, including its historical incorrect candidate status; the implementation now
separates retrieval failure from a successful empty search and permits retrying a failed query.

- [Gilmer, 2211.09055v2](https://arxiv.org/abs/2211.09055v2): the first constant lower bound and the
  independent-union entropy approach. We inspected the abstract.
- [Yu, 2212.00658v2](https://arxiv.org/abs/2212.00658v2): finite-dimensional optimization and a numerical
  value around 0.38234. We inspected the abstract.
- [Liu, 2306.08824v1](https://arxiv.org/html/2306.08824v1): the approximately 0.38271 evaluation is
  stated under numerically verified hypotheses. Its introduction explains why changing couplings
  disrupts the conditional dependence argument. We inspected the introduction and relevant later statements.
- [Jiang, 2609.08291v1](https://arxiv.org/html/2609.08291v1), submitted 2026-09-08: Theorem 1.1 claims
  a computer-assisted 0.38288525 bound. Sections 10.1–10.7 give global inverse-multiplicity balancing
  and an explicit remaining quantitative question. We read those sections, but **have not reproduced
  the interval appendix or independently validated the paper's full proof**.
- [Demontis, 2405.03731v1](https://arxiv.org/abs/2405.03731v1) has a title claiming the whole conjecture.
  Only its metadata was inspected; that does not validate its argument. Later primary literature
  above still treats the general problem as unresolved.

## Checked obstruction and local repair

For independent Bernoulli(2/5) variables, the joint counts are (9,6,6,4)/25. Action 5 checks
H(X OR Y)-H(X)<0 by exact integer comparison. Thus the naive entropy-growth statement for all
distributions with marginal below 1/2 is false. This is a known route obstruction, not a Frankl counterexample.

Changing the table to [[5,1],[1,3]]/10 keeps both input marginals (3/5,2/5), while making the union
unbiased. Action 7 checks strict entropy growth. This does not solve the conditional averaging or
dimension-lifting problem: a one-bit repair cannot be applied without controlling later dependence.

## Product-family obstruction to a proposed variance bound

The following is written mathematical reasoning, not a proof-assistant artifact or a novelty claim.
For the Boolean-cube family F_d=2^[d], every frequency equals 1/2 and N=2^d. The number of ordered
representations of a set S as a union is r(S)=3^|S|. Write L=ln 3. Double-centering log r(A union B)
under independent uniform A,B gives

\[
R(A,B)=\frac L4\bigl(2|A\triangle B|-d\bigr),\qquad
V_d=\mathbb E R^2=\frac{dL^2}{16}.
\]

Indeed each coordinate contributes +L/4 if its two bits differ and -L/4 otherwise. The coordinate
contributions are independent, mean zero and have variance L²/16. Therefore

\[
\frac{V_d}{(\ln N)^2}=\frac{(\ln3)^2}{16d(\ln2)^2}\longrightarrow0.
\]

No positive uniform lower bound on this ratio holds for all union-closed families with maximum
frequency **at most** 1/2. This does **not** rule out a bound under a strict sub-half hypothesis that
depends on the frequency gap, nor does it contradict Frankl.

The weakness is in this particular estimate: the rational one-bit coupling [[2,1],[1,2]]/6 keeps
uniform marginals and produces a union with probability 2/3. Its product in dimension d gains
d(h(2/3)-h(3/4)) bits over independent sampling. Actions 10–12 check selected finite additivity
instances; action 13 verifies the positive one-bit gain exactly. General additivity follows by
independence across product coordinates, not from extrapolating these three tests.

The next proof obligation is a **frequency-gap-sensitive global entropy gain** with a justified
dimension argument. A merely positive finite gain, or an estimate that loses all strength under
products, does not supply the required universal conclusion.

## Reproduce

With `[agent,math]` installed, run `python examples/frankl-frontier/reproduce.py` from the repository
root. It checks archive hashes and six exact certificates, then reruns those six mathematical actions.
It makes no network requests and does not replay model reasoning. Source hashes identify the inspected
local snapshots; they are not a signature or proof that an external preprint is correct.
