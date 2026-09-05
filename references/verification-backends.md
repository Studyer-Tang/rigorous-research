# Verification backends and independent review

## Literature retrieval

Run `literature_search.py` with the providers relevant to the claim: Crossref, arXiv, OpenAlex, Semantic Scholar, or PubMed. Preserve provider URLs, raw normalized records, search limits, retrieval time, and every request failure. The deduplication unit is a scholarly work, but manifestations remain distinct when they carry different mathematical or publication status: preprint, accepted manuscript, version of record, correction, retraction, and supplement are not interchangeable. Provider overlap improves discovery coverage; it does not make metadata agreement independent scientific evidence.

Automatic merge is allowed only for a shared normalized DOI, a shared arXiv identifier, or a normalized title together with compatible first-author and year metadata. A fuzzy title match is a review candidate, not a duplicate. A conflict between title, author, year, DOI, or manifestation status must be marked `REVIEW_REQUIRED`.

Search hits establish discoverability, not truth or novelty. Promote a record into claim evidence only after reading the relevant statement and recording what it proves, assumes, computes, or conjectures.

## Plan seals

Create a JSON plan containing every field required by `research_seal.py seal-plan`. Seal it before the first result is inspected. The seal binds both the file bytes and a canonical semantic projection. Any change to the estimand, window, exclusions, primary method, sensitivity set, decision rule, or multiplicity family invalidates it.

If the design must change, retain the old seal, create a new protocol version, explain the reason, and label the revised analysis exploratory unless the change was independent of observed outcomes.

## Mathematical backends

`math_backend.py sympy-identity` is decisive only for rational arithmetic when the difference reduces to an exact zero polynomial, with every original denominator exceptional set stated. Restrictions survive cancellation, including `x/x`, zero numerators, both sides of the equation, and matrix entries. General `simplify` success remains diagnostic because branch cuts, domains, and modeling semantics may be absent. Check `domain_analysis_complete` before treating `exceptional_set: none` as complete domain coverage.

Expressions accept declared symbols, integer literals, explicit `+ - * / **`, and one-argument `sin`, `cos`, `tan`, `exp`, `log`, `sqrt`, and `Abs`, with constants `pi`, `E`, and `I`. Use `1/10` rather than `0.1` for exact arithmetic. Python attributes, indexing, arbitrary function calls, undeclared symbols, and reserved symbol names are rejected. Expression size, nesting, and integer powers are bounded, but expensive symbolic computations still need an external process timeout.

Use `math_backend.py sympy-counterexample --lhs "x**2" --rhs "x" --symbols x --values 0 1 1/2 --output witness.json` to find a reproducible exact witness. This command supports rational arithmetic with integer powers, filters positive/integer assumptions and original denominator restrictions, and records tested/excluded points and the search budget. The Cartesian grid is traversed in input order. Exit code 0 means a witness was found, 1 means inconclusive, and 2 means invalid input. A witness refutes the specified identity only; it does not resolve unrelated assumptions or modeling questions. A finite grid without a witness never proves the universal claim. The witness is not an established identity certificate and does not pass `verify-receipt --require-established`; register and review counterexample evidence separately under the inference case contract.

`math_backend.py lean-check` records compiler output and rejects files containing `sorry`, `admit`, or user-declared axioms as closed certificates. Lean is optional. If it is unavailable, report that the formal check was not run; never imitate a compiler transcript.

Wrap decisive SymPy or Lean output with `research_seal.py wrap-receipt`. The receipt binds claim inputs, certificate outputs, dependency locks, backend name and version, command, return code, and semantic domain. Release validation reopens the backend output and checks its decisive status; self-written text labeled “exact computation” is insufficient.

## Statistical backends

Name the uncertainty model explicitly: IID, heteroskedasticity-consistent, clustered, HAC, panel, block bootstrap, or another justified scheme. Do not substitute one for another because it yields a preferred interval.

For time series, report bandwidth or block length and show sensitivity. Use `statistics_backend.py coverage` to test finite-sample behavior under prespecified data-generating processes. A familiar estimator can under-cover severely under strong persistence, heavy tails, bandwidth mismatch, or nonstationarity.

Define the family before applying Holm family-wise error control or Benjamini-Hochberg false-discovery-rate control. Neither procedure repairs outcome selection, repeated peeking, post-selection inference, or an unidentified estimand.

## Financial data snapshots

Use `finance_data.py fetch` for supported public adapters. The manifest must state provider, dataset, exact request, retrieval time, as-of meaning, revision policy, raw hash, schema, units, timezone, calendar, identifier system, adjustment policy, and license. Keep the raw response beside the manifest so the computation can replay without a network connection.

When a provider silently revises history, create a new immutable snapshot and a vintage diff. Do not overwrite or merely rehash the earlier data. “Latest revised” data cannot establish what was knowable at a historical decision time.

## Blind independent review

Prepare the packet before contacting the reviewer. The packet removes author identity, author verdict, claim status, check outcomes, and evidence roles while retaining the question, contract, claims, assumptions, falsifiers, and hashed artifacts.

The reviewer must independently state `ACCEPT`, `REJECT`, or `REVISE`, whether the decisive step was reproduced, and fatal, major, and minor issues. The review receipt binds the exact packet. A reviewer-author identity conflict, changed packet, changed evidence, rejection, revision request, or fatal issue forces `RECONCILIATION_REQUIRED`.

Only a verified adjudication with at least one independent `ACCEPT` review clears a strict release policy. Reviewer agreement is evidence of checking, not a transfer of responsibility or proof of novelty.

The local protocol is tamper-evident, not an identity-signature system: reviewer identity and independence are self-declared. For journal, regulatory, or adversarial use, add an authenticated institutional identity or digital signature outside this repository and bind that attestation to the review-receipt hash.
