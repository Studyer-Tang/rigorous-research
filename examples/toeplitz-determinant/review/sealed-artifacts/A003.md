# Falsification record

The following failure modes were attacked:

- index and type errors at \(n=1\);
- accidental use of an already modified row by applying the operations in the wrong order;
- hidden division by \(1-\rho^2\), which would lose \(\rho=\pm1\);
- sign or exponent errors in the claimed polynomial;
- agreement only at numeric samples rather than as an exact identity.

The symbolic checker independently expands the Leibniz formula and collects integer polynomial coefficients for every \(n\le7\) (5913 permutations in total). A separate implementation performs exact rational elimination for \(n\le12\) at seven parameter values, including \(0\), \(\pm1\), negative values, and nonintegral values. Neither finite computation proves the all-\(n\) statement; their role is to attack errors in the general row-operation proof.
