# Mathematical claims

## Contract fields

Fill all four fields before releasing a mathematical result:

- `ambient_object`: the group, ring, scheme, probability space, category, or other universe;
- `coefficient_domain`: base field or ring and every localization or completion used;
- `quantifiers`: variables, index ranges, genericity, and exceptional loci;
- `equality_semantics`: literal equality, equality in a quotient, almost-everywhere equality, isomorphism, or numerical tolerance.

## Definition and type audit

Trace every target expression back to its definitions. Verify that generators exist at the stated level, indices are legal, maps have matching domains and codomains, quotients use elements of their parent object, and transition maps are defined.

A repair of a malformed definition creates a new claim. Label the literal statement and every correction separately; apparent naturalness does not identify authorial intent.

Use a triggered `specification` check for the literal malformed statement. Use a counterexample or failed proof obligation for a well-defined but false statement. A hypothesis that does not hold means the conditional theorem is inapplicable; it does not refute the conditional theorem.

## Required checks for a supported claim

The default gate requires cleared checks of kinds:

- `typecheck`: all objects and operations are well-defined;
- `proof`: a derivation closes the headline implication;
- `counterexample`: boundary and adversarial witnesses fail to defeat the scoped claim.

Add `relation` when a representation must descend to a presented quotient, `formal` when a proof assistant artifact is claimed, and `exact-computation` when computer algebra carries a decisive step.

## Proof and construction audit

For a representation or constructed witness, verify in order:

1. source and target objects;
2. parameter and invertibility assumptions;
3. every defining relation;
4. descent through each quotient;
5. translation of the target expression under the chosen convention;
6. the final equality, nonvanishing, injectivity, or universality claim in the actual domain.

For stable families or direct limits, prove compatibility and persistence. Nonvanishing at each inspected finite level does not imply nonvanishing in a limit when later relations may kill the element.

## Computation

Prefer exact arithmetic, normal forms, certified intervals, or modular images with a proved lifting argument. Floating-point separation from zero is numerical evidence, not exact nonvanishing, unless an error bound excludes zero.

When exhaustive search is decisive, prove that the search space is complete and record excluded symmetries or normalizations.

## Refutation

A counterexample must satisfy every hypothesis and live in the required category. Minimize it when feasible. Record which assumption it violates if it attacks only a strengthened or repaired version of the claim.
