import numpy as np
import pytest

from lss_copilot.stats import (
    capability_analysis,
    describe,
    ols_regression,
    pareto_analysis,
    run_hypothesis_test,
)


def test_describe_basic():
    stats = describe([1, 2, 3, 4, 5])
    assert stats["mean"] == 3.0
    assert stats["median"] == 3.0
    assert stats["n"] == 5


def test_describe_rejects_empty():
    with pytest.raises(ValueError):
        describe([float("nan")])


def test_capability_centered_process():
    rng = np.random.default_rng(42)
    data = rng.normal(10, 1, 500)
    result = capability_analysis(data, lsl=7, usl=13)
    assert result["cp"] == pytest.approx(1.0, abs=0.15)
    assert result["cpk"] == pytest.approx(result["cp"], abs=0.1)  # centered => cpk ~= cp


def test_capability_requires_a_limit():
    with pytest.raises(ValueError):
        capability_analysis([1, 2, 3])


def test_hypothesis_two_groups_detects_difference():
    rng = np.random.default_rng(7)
    finding = run_hypothesis_test(
        "cycle_time",
        groups={"a": rng.normal(10, 1, 50).tolist(), "b": rng.normal(14, 1, 50).tolist()},
    )
    assert finding.test_name in {"welch_t_test", "mann_whitney_u"}
    assert finding.significant
    assert finding.p_value < 0.001


def test_hypothesis_three_groups_uses_anova_family():
    rng = np.random.default_rng(7)
    finding = run_hypothesis_test(
        "cycle_time",
        groups={k: rng.normal(10, 1, 40).tolist() for k in "abc"},
    )
    assert finding.test_name in {"one_way_anova", "kruskal_wallis"}
    assert not finding.significant  # identical distributions


def test_hypothesis_chi_square():
    finding = run_hypothesis_test("defects", contingency=[[90, 10], [60, 40]])
    assert finding.test_name == "chi_square"
    assert finding.significant


def test_regression_recovers_coefficients():
    rng = np.random.default_rng(3)
    x1 = rng.normal(0, 1, 200)
    x2 = rng.normal(0, 1, 200)
    y = 2.0 * x1 + 0.0 * x2 + 5.0 + rng.normal(0, 0.1, 200)
    finding = ols_regression("y", y.tolist(), {"x1": x1.tolist(), "x2": x2.tolist()})
    coefs = finding.details["coefficients"]
    assert coefs["x1"]["coef"] == pytest.approx(2.0, abs=0.05)
    assert coefs["x1"]["p_value"] < 0.001
    assert coefs["x2"]["p_value"] > 0.05
    assert finding.details["intercept"] == pytest.approx(5.0, abs=0.05)
    assert finding.significant


def test_pareto_vital_few():
    result = pareto_analysis({"login": 70, "billing": 15, "ui": 10, "docs": 5})
    assert result["vital_few"] == ["login", "billing"]
    assert result["rows"][0]["category"] == "login"
    assert result["rows"][-1]["cumulative_share"] == pytest.approx(1.0)
