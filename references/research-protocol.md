# Research protocol

Use this protocol for a full investigation. The stages are logical gates, not a rigid order; return to an earlier stage whenever later evidence changes the target.

## 1. Target record

Record:

- the exact source and version;
- the literal question or theorem;
- ambient category, base ring or field, parameter domain, conventions, and quantifiers;
- dependencies on earlier definitions and results;
- the claimed status before this investigation;
- a resolution criterion: what exact object or proof would settle it?

Mark unavailable sources and indirect quotations. A secondary source may locate a problem but should not silently replace its primary formulation.

## 2. Definition ledger

Give every important object a stable local identifier. For each, record the source locator, exact definition, dependencies, and any local restatement. Explicitly test that the definition is well-formed: generators exist, indices are legal, operations have the stated domains, quotients use elements of the parent object, and limits have compatible transition maps.

## 3. Interpretation map

When text is defective or ambiguous, create branches such as:

- `LITERAL`: the printed statement;
- `CORRECTION-A`, `CORRECTION-B`: distinct minimal repairs;
- `STABLE`: a direct-limit or stable-family reading;
- `AUTHOR-INTENT`: only when supported by author evidence, not guessed.

For each branch, list changed definitions and whether it strengthens, weakens, or is incomparable with other branches. A model or representation for one quotient is not automatically a model for another.

## 4. Obligation graph

Decompose the headline claim. Each obligation needs:

- an ID and exact statement;
- dependencies;
- evidence type: proof, symbolic computation, numerical experiment, citation, or testimony;
- status: `OPEN`, `SUPPORTED`, `FAILED`, or `NOT-APPLICABLE`;
- a falsifier or decisive test where one is known.

Critical obligations include well-definedness of constructed objects, satisfaction of all defining relations, correct parameter assumptions, and the final logical implication to the headline claim.

## 5. Adversarial pass

Before writing exposition, search for:

- an omitted relation or hypothesis;
- a map that is not defined on the claimed quotient;
- a zero divisor or exceptional specialization;
- cancellation requiring invertibility not assumed;
- finite-level evidence substituted for a stable statement, or conversely;
- equality checked only on generators when compatibility is missing;
- nonzero symbolic expressions that vanish in the actual coefficient ring;
- circular use of the target claim;
- a result about an example promoted to a universal result.

Record failed attacks too; they reveal what was genuinely tested.

## 6. Evidence matrix

Maintain separate confidence columns for correctness, scope match, reproducibility, and novelty. A correct computation can have high correctness but zero scope match. An expert's encouraging email can improve interpretation confidence while proving no theorem.

## 7. Status gate

Assign status separately for every interpretation:

- `VERIFIED`: all critical obligations are supported and no known defect survives;
- `REFUTED`: a valid counterexample or contradiction defeats the exact claim;
- `INCOMPLETE`: at least one critical obligation remains open;
- `ILL-POSED`: the statement has no definite truth value without additional choices.

Use `BLOCKED` only for an operational dependency requiring unavailable authority or external input. It is not a mathematical verdict and must not replace `INCOMPLETE` or `ILL-POSED`.

Do not use probability language to disguise an open logical gap. Confidence may supplement status, never replace it.

## 8. Release packet

The smallest credible packet contains the exact claim, source ledger, interpretation map, proof or counterexample, obligation table, assumptions, limitations, reproducibility information, and claim-safe abstract. Preserve dates and versions for external sources and computational artifacts.
