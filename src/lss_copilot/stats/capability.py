"""Process capability analysis: Cp and Cpk against customer spec limits."""

from __future__ import annotations

import numpy as np


def capability_analysis(
    values: list[float] | np.ndarray,
    lsl: float | None = None,
    usl: float | None = None,
) -> dict[str, float | None]:
    """Compute Cp / Cpk. At least one spec limit is required.

    Cp  = (USL - LSL) / 6σ            (requires both limits)
    Cpk = min((USL - μ) / 3σ, (μ - LSL) / 3σ)
    """
    if lsl is None and usl is None:
        raise ValueError("capability_analysis requires at least one spec limit")

    arr = np.asarray(values, dtype=float)
    arr = arr[~np.isnan(arr)]
    if arr.size < 2:
        raise ValueError("capability_analysis requires at least 2 observations")

    mu = float(np.mean(arr))
    sigma = float(np.std(arr, ddof=1))
    if sigma == 0:
        raise ValueError("capability_analysis undefined for zero-variance data")

    cp = (usl - lsl) / (6 * sigma) if (usl is not None and lsl is not None) else None
    cpu = (usl - mu) / (3 * sigma) if usl is not None else None
    cpl = (mu - lsl) / (3 * sigma) if lsl is not None else None
    cpk = min(v for v in (cpu, cpl) if v is not None)

    return {
        "mean": mu,
        "sigma": sigma,
        "cp": cp,
        "cpu": cpu,
        "cpl": cpl,
        "cpk": cpk,
    }
