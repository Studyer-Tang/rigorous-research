# Decision-time contradiction

Let the close-to-close return for day \(t\) be

\[
r_t=P_t/P_{t-1}-1.
\]

The proposed backtest chooses \(w_t=\operatorname{sign}(r_t)\) and attributes the same return \(r_t\) to that position. This mechanically produces the gross payoff

\[
w_t r_t=|r_t|.
\]

But \(r_t\) is not known until the closing price \(P_t\) is observed. A position earning the interval return from \(P_{t-1}\) to \(P_t\) must be chosen before \(P_t\) is known. Therefore this payoff cannot be implemented under the stated decision clock. Lagging the position to \(w_t=\operatorname{sign}(r_{t-1})\) defines a different strategy and requires a new performance test.
