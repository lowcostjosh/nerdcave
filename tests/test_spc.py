import numpy as np

from lss_copilot.stats.spc import control_limits, evaluate_spc_rules


def _limits():
    rng = np.random.default_rng(11)
    baseline = rng.normal(50, 2, 60)
    return control_limits(baseline)


def test_limits_bracket_the_mean():
    limits = _limits()
    assert limits["lcl"] < limits["center_line"] < limits["ucl"]
    assert limits["sigma"] > 0


def test_rule1_beyond_3_sigma():
    limits = _limits()
    obs = [limits["center_line"]] * 5 + [limits["ucl"] + 5]
    alerts = evaluate_spc_rules("cycle_time", obs, limits)
    assert any(a.rule == "beyond_3_sigma" for a in alerts)


def test_rule4_run_of_8_detects_drift():
    limits = _limits()
    obs = [limits["center_line"] + 0.5] * 9  # small but persistent shift
    alerts = evaluate_spc_rules("cycle_time", obs, limits)
    assert any(a.rule == "run_of_8" for a in alerts)


def test_in_control_process_is_quiet():
    rng = np.random.default_rng(11)
    baseline = rng.normal(50, 2, 60)
    limits = control_limits(baseline)
    obs = rng.normal(50, 2, 20)
    alerts = [a for a in evaluate_spc_rules("m", obs, limits) if a.rule == "beyond_3_sigma"]
    assert alerts == []
