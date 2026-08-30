# Dependence-aware interval coverage stress test

This experiment asks a narrower and more useful question than “does Newey–West work?”: how often do nominal 95% mean intervals actually cover the true mean in six preregistered data-generating processes?

The design crosses AR(1) coefficients \(\phi\in\{0,0.4,0.8\}\) with Gaussian and variance-standardized Student-\(t_3\) innovations. Every cell uses 5,000 replications, 120 post-burn-in observations, an IID normal interval, and a Newey–West normal interval with eight Bartlett lags. The plan was sealed before the grid was run.

| Innovations | \(\phi\) | IID coverage | HAC coverage |
|---|---:|---:|---:|
| Gaussian | 0.0 | 94.40% | 92.38% |
| Gaussian | 0.4 | 79.18% | 90.02% |
| Gaussian | 0.8 | 48.58% | 82.08% |
| Student-\(t_3\) | 0.0 | 94.84% | 92.94% |
| Student-\(t_3\) | 0.4 | 78.34% | 90.38% |
| Student-\(t_3\) | 0.8 | 46.36% | 81.22% |

At the 95% target, the Monte Carlo standard error is approximately 0.31 percentage points. The IID shortfall under positive dependence is therefore far beyond simulation noise. HAC materially improves coverage when dependence is present, but the fixed eight-lag, normal-critical-value implementation still under-covers in these finite samples. At \(\phi=0\), estimating unnecessary autocovariances slightly worsens coverage.

The result is diagnostic, not a universal ranking of standard-error estimators. It does not cover nonstationarity, conditional heteroskedasticity, clustering, long memory, bandwidth selection, fixed-\(b\) asymptotics, or bootstrap HAC intervals. Its main value is to force a statistical method to demonstrate data-generating-process coverage rather than pass merely because a familiar estimator name appears in the code.

Reproduce with:

```text
python examples/dependence-coverage/run_grid.py --replications 5000 --output examples/dependence-coverage/coverage-grid.json
```
