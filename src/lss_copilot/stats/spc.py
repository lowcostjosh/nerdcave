"""Statistical Process Control: control limits and Western Electric rules.

Used by the CONTROL phase to watch live metrics and raise `SPCAlert`s when a
process drifts. Pure functions — the polling loop lives in the agent layer.
"""

from __future__ import annotations

import numpy as np

from lss_copilot.state.schemas import SPCAlert


def control_limits(baseline: list[float] | np.ndarray, sigma_multiplier: float = 3.0) -> dict[str, float]:
    """Individuals (I-chart) limits from a stable baseline window.

    Sigma is estimated from the average moving range (MR-bar / 1.128), the
    standard I-MR estimator, which is robust to slow drift in the baseline.
    """
    arr = np.asarray(baseline, dtype=float)
    arr = arr[~np.isnan(arr)]
    if arr.size < 2:
        raise ValueError("control_limits requires at least 2 baseline points")
    center = float(np.mean(arr))
    mr_bar = float(np.mean(np.abs(np.diff(arr))))
    sigma = mr_bar / 1.128
    return {
        "center_line": center,
        "sigma": sigma,
        "ucl": center + sigma_multiplier * sigma,
        "lcl": center - sigma_multiplier * sigma,
    }


def evaluate_spc_rules(
    metric: str,
    observations: list[float] | np.ndarray,
    limits: dict[str, float],
) -> list[SPCAlert]:
    """Apply core Western Electric rules to a window of observations.

    Rule 1: any point beyond UCL/LCL (3 sigma).
    Rule 4: eight consecutive points on one side of the center line (drift).
    """
    arr = np.asarray(observations, dtype=float)
    center, ucl, lcl = limits["center_line"], limits["ucl"], limits["lcl"]
    alerts: list[SPCAlert] = []

    for i, x in enumerate(arr):
        if x > ucl or x < lcl:
            alerts.append(SPCAlert(
                metric=metric, rule="beyond_3_sigma", value=float(x),
                ucl=ucl, lcl=lcl, center_line=center,
                message=f"Point {i} at {x:.4g} breached {'UCL' if x > ucl else 'LCL'}",
            ))

    run = 0
    side = 0  # +1 above center, -1 below
    for i, x in enumerate(arr):
        current = 1 if x > center else (-1 if x < center else 0)
        if current != 0 and current == side:
            run += 1
        else:
            side, run = current, (1 if current != 0 else 0)
        if run == 8:
            alerts.append(SPCAlert(
                metric=metric, rule="run_of_8", value=float(x),
                ucl=ucl, lcl=lcl, center_line=center,
                message=f"8 consecutive points {'above' if side > 0 else 'below'} "
                        f"center line ending at index {i} — process mean has shifted",
            ))
            run = 0  # reset so overlapping runs alert once per 8
    return alerts
