# Proof by determinant-preserving row operations

Let \(R_i\) denote row \(i\) of \(T_n(\rho)\). Starting at \(i=n\) and proceeding downward to \(i=2\), replace

\[
R_i\longleftarrow R_i-\rho R_{i-1}.
\]

The descending order matters: when row \(i\) is changed, row \(i-1\) is still an original row. Each operation adds a polynomial multiple of another row and therefore preserves the determinant over \(\mathbb Z[\rho]\).

For a column \(j<i\), the new entry is

\[
\rho^{i-j}-\rho\rho^{i-1-j}=0.
\]

For \(j\ge i\), it is

\[
\rho^{j-i}-\rho\rho^{j-i+1}
=\rho^{j-i}(1-\rho^2).
\]

The resulting matrix is upper triangular. Its first diagonal entry is \(1\), and each of its remaining \(n-1\) diagonal entries is \(1-\rho^2\). Hence

\[
\det T_n(\rho)=1\cdot(1-\rho^2)^{n-1}.
\]

The case \(n=1\) is included: the empty exponent gives \((1-\rho^2)^0=1\). The proof never divides, so it also covers \(\rho=\pm1\), where both sides vanish for \(n>1\). This proves the identity for every \(n\ge1\) in \(\mathbb Z[\rho]\).
