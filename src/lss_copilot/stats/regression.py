"""OLS regression for root-cause screening: which X's actually move the Y."""

from __future__ import annotations

import numpy as np
from scipy import stats as sps

from lss_copilot.state.schemas import StatisticalFinding


def ols_regression(
    target_metric: str,
    y: list[float] | np.ndarray,
    X: dict[str, list[float]],
    alpha: float = 0.05,
) -> StatisticalFinding:
    """Ordinary least squares with per-coefficient t-tests.

    Returns the overall model F-test as the finding; per-factor coefficients,
    p-values and standardized betas ride in `details` so the orchestrator can
    rank candidate root causes.
    """
    y_arr = np.asarray(y, dtype=float)
    names = list(X.keys())
    X_arr = np.column_stack([np.asarray(X[k], dtype=float) for k in names])
    n, k = X_arr.shape
    if y_arr.size != n:
        raise ValueError("y and X row counts differ")
    if n <= k + 1:
        raise ValueError(f"need more than {k + 1} rows to fit {k} predictors")

    design = np.column_stack([np.ones(n), X_arr])
    beta, _, rank, _ = np.linalg.lstsq(design, y_arr, rcond=None)
    if rank < design.shape[1]:
        raise ValueError("design matrix is rank-deficient (collinear predictors)")

    residuals = y_arr - design @ beta
    dof = n - k - 1
    sse = float(residuals @ residuals)
    sst = float(np.sum((y_arr - y_arr.mean()) ** 2))
    r2 = 1 - sse / sst if sst else 0.0
    adj_r2 = 1 - (1 - r2) * (n - 1) / dof

    mse = sse / dof
    cov = mse * np.linalg.inv(design.T @ design)
    se = np.sqrt(np.diag(cov))
    t_stats = beta / se
    p_values = 2 * sps.t.sf(np.abs(t_stats), dof)

    f_stat = (r2 / k) / ((1 - r2) / dof) if r2 < 1 else float("inf")
    f_p = float(sps.f.sf(f_stat, k, dof))

    y_std = y_arr.std(ddof=1)
    coefficients = {
        name: {
            "coef": float(beta[i + 1]),
            "std_err": float(se[i + 1]),
            "t": float(t_stats[i + 1]),
            "p_value": float(p_values[i + 1]),
            "standardized_beta": float(beta[i + 1] * X_arr[:, i].std(ddof=1) / y_std)
            if y_std else 0.0,
        }
        for i, name in enumerate(names)
    }

    return StatisticalFinding(
        test_name="ols",
        target_metric=target_metric,
        factors=names,
        statistic=float(f_stat),
        p_value=f_p,
        effect_size=float(r2),
        significant=bool(f_p < alpha),
        details={
            "intercept": float(beta[0]),
            "r2": float(r2),
            "adj_r2": float(adj_r2),
            "n": int(n),
            "coefficients": coefficients,
        },
    )
