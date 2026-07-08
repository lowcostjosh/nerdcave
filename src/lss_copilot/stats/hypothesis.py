"""Hypothesis testing with automatic test selection based on data shape.

The Statistical Engine agent calls `run_hypothesis_test`; the function — not
the LLM — decides between t-test / ANOVA / chi-square / non-parametric
fallbacks, so the choice of test is auditable and reproducible.
"""

from __future__ import annotations

import numpy as np
from scipy import stats as sps

from lss_copilot.state.schemas import StatisticalFinding

ALPHA = 0.05
_NORMALITY_MIN_N = 8


def _is_normal(sample: np.ndarray) -> bool:
    if sample.size < _NORMALITY_MIN_N:
        return False  # too small to trust normality; use non-parametric
    _, p = sps.shapiro(sample[:5000])  # shapiro caps out; 5k is plenty
    return p > ALPHA


def run_hypothesis_test(
    target_metric: str,
    groups: dict[str, list[float]] | None = None,
    contingency: list[list[int]] | None = None,
    alpha: float = ALPHA,
) -> StatisticalFinding:
    """Dispatch the appropriate test.

    - `contingency` table  -> chi-square test of independence
    - 2 numeric groups     -> Welch t-test (normal) or Mann-Whitney U
    - 3+ numeric groups    -> one-way ANOVA (normal) or Kruskal-Wallis
    """
    if (groups is None) == (contingency is None):
        raise ValueError("provide exactly one of `groups` or `contingency`")

    if contingency is not None:
        table = np.asarray(contingency, dtype=float)
        chi2, p, dof, _ = sps.chi2_contingency(table)
        n = table.sum()
        cramers_v = float(np.sqrt(chi2 / (n * (min(table.shape) - 1))))
        return StatisticalFinding(
            test_name="chi_square",
            target_metric=target_metric,
            statistic=float(chi2),
            p_value=float(p),
            effect_size=cramers_v,
            significant=bool(p < alpha),
            details={"dof": int(dof), "n": int(n)},
        )

    assert groups is not None
    if len(groups) < 2:
        raise ValueError("need at least two groups to compare")
    samples = {k: np.asarray(v, dtype=float) for k, v in groups.items()}
    for name, s in samples.items():
        if s.size < 2:
            raise ValueError(f"group '{name}' needs at least 2 observations")
    arrays = list(samples.values())
    all_normal = all(_is_normal(s) for s in arrays)

    if len(arrays) == 2:
        a, b = arrays
        if all_normal:
            stat, p = sps.ttest_ind(a, b, equal_var=False)
            test_name = "welch_t_test"
            pooled = np.sqrt((np.var(a, ddof=1) + np.var(b, ddof=1)) / 2)
            effect = float((np.mean(a) - np.mean(b)) / pooled) if pooled else None  # Cohen's d
        else:
            stat, p = sps.mannwhitneyu(a, b, alternative="two-sided")
            test_name = "mann_whitney_u"
            effect = float(1 - (2 * stat) / (a.size * b.size))  # rank-biserial r
    else:
        if all_normal:
            stat, p = sps.f_oneway(*arrays)
            test_name = "one_way_anova"
            grand = np.concatenate(arrays)
            ss_between = sum(s.size * (np.mean(s) - np.mean(grand)) ** 2 for s in arrays)
            ss_total = float(np.sum((grand - np.mean(grand)) ** 2))
            effect = float(ss_between / ss_total) if ss_total else None  # eta squared
        else:
            stat, p = sps.kruskal(*arrays)
            test_name = "kruskal_wallis"
            effect = None

    return StatisticalFinding(
        test_name=test_name,
        target_metric=target_metric,
        factors=list(groups.keys()),
        statistic=float(stat),
        p_value=float(p),
        effect_size=effect,
        significant=bool(p < alpha),
        details={"group_sizes": {k: int(v.size) for k, v in samples.items()},
                 "normality_assumed": all_normal},
    )
