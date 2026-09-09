"""Numerical matrix-scaling proposals, followed by independent rational certification."""

from fractions import Fraction


def coupling_entropy(kernel, labels, bound, relation, digits, max_iterations, delta):
    import mpmath as mp

    n = len(kernel)
    if any(len(row) != n for row in kernel) or len(labels) != n or any(len(row) != n for row in labels):
        raise ValueError("kernel and event labels must be equally sized square matrices")
    certificate = {
        "schema_version": 1,
        "backend": "balanced-coupling",
        "claim": dict(
            kernel=kernel,
            labels=labels,
            bound=bound,
            relation=relation,
            units="nats",
            marginals="uniform-rows-and-columns",
            objective="minimize-sum-p-log-p-over-k",
        ),
        "approximation": None,
        "diagnostic": {},
    }
    with mp.workdps(70):

        def number(text):
            q = Fraction(text)
            if q <= 0:
                raise ValueError("kernel must be positive")
            return mp.mpf(q.numerator) / q.denominator

        matrix = [[number(k) for k in row] for row in kernel]
        v = [mp.mpf(1)] * n
        for iteration in range(max_iterations):
            u = [1 / (n * sum(matrix[i][j] * v[j] for j in range(n))) for i in range(n)]
            v = [1 / (n * sum(matrix[i][j] * u[i] for i in range(n))) for j in range(n)]
            p = [[u[i] * matrix[i][j] * v[j] for j in range(n)] for i in range(n)]
            residual = max(abs(sum(row) - mp.mpf(1) / n) for row in p)
            if residual < mp.mpf(10) ** (-digits - 8):
                break
        certificate["diagnostic"] = {
            "iterations": iteration + 1,
            "marginal_residual": str(residual),
            "warning": "Numerical proposal only; independent checker decides acceptance.",
        }
        if residual >= mp.mpf(10) ** (-digits - 8):
            return certificate
        row_total = 10**digits
        counts = [[0] * n for _ in range(n)]
        for i in range(n - 1):
            for j in range(n - 1):
                counts[i][j] = int(mp.floor(p[i][j] * n * row_total))
            counts[i][-1] = row_total - sum(counts[i])
        for j in range(n - 1):
            counts[-1][j] = row_total - sum(counts[i][j] for i in range(n - 1))
        counts[-1][-1] = row_total - sum(counts[-1])
        if any(c <= 0 for row in counts for c in row):
            certificate["diagnostic"]["reason"] = "rounded positive balanced matrix unavailable; increase digits"
            return certificate
        certificate["approximation"] = {
            "counts": counts,
            "row_factors": [str(Fraction(mp.nstr(x, digits + 8))) for x in u],
            "column_factors": [str(Fraction(mp.nstr(x, digits + 8))) for x in v],
            "delta": delta,
        }
    return certificate
