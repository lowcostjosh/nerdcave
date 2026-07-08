"""Descriptive statistics. Deterministic; consumed by the Statistical Engine agent."""

from __future__ import annotations

import numpy as np


def describe(values: list[float] | np.ndarray) -> dict[str, float]:
    arr = np.asarray(values, dtype=float)
    arr = arr[~np.isnan(arr)]
    if arr.size == 0:
        raise ValueError("describe() requires at least one non-NaN value")
    q1, q3 = np.percentile(arr, [25, 75])
    return {
        "n": float(arr.size),
        "mean": float(np.mean(arr)),
        "median": float(np.median(arr)),
        "std": float(np.std(arr, ddof=1)) if arr.size > 1 else 0.0,
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
        "q1": float(q1),
        "q3": float(q3),
        "iqr": float(q3 - q1),
    }
