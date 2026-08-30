# Frozen empirical design

## Question

For the published U.S. monthly momentum factor, is the arithmetic mean from January 1993 through December 2024 positive under a weak-dependence interpretation?

## Estimand and sample

- Population/time scope: the fixed 384-month sequence from 1993-01 through 2024-12.
- Sampling unit: calendar month; serial dependence is permitted.
- Outcome: Kenneth French Data Library monthly momentum-factor return, converted from percent to decimal units.
- Descriptive estimand: the arithmetic mean of those 384 observations.
- Inferential extension: a long-run monthly mean under a conditionally imposed weak-stationarity and weak-dependence interpretation.

The start, end, Newey–West lag count (6), circular block length (12), bootstrap replications (10,000), and random seed (20260830) are fixed in the executable before looking at the result.

## Falsifiers

The inferential claim fails the release condition if any of the following occurs:

- the HAC 95% lower endpoint is nonpositive;
- the circular block-bootstrap 95% lower endpoint is nonpositive;
- the 1% symmetrically trimmed mean is nonpositive;
- any leave-one-calendar-year-out mean is nonpositive;
- the source file lacks any month in the frozen interval.

Subperiod estimates for 1993–2008 and 2009–2024 diagnose instability but are not silently substituted for the frozen headline estimand.
