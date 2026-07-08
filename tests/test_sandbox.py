import pytest

from lss_copilot.tools.sandbox import SandboxViolation, _static_check, run_in_sandbox


def test_simple_computation():
    out = run_in_sandbox(
        "values = data['values']\nresult = {'mean': sum(values) / len(values)}",
        input_data={"values": [1, 2, 3, 4]},
    )
    assert out.ok
    assert out.result == {"mean": 2.5}


def test_forbidden_import_blocked():
    with pytest.raises(SandboxViolation, match="import of 'os'"):
        _static_check("import os\nresult = os.listdir('/')")


def test_forbidden_call_blocked():
    with pytest.raises(SandboxViolation, match="'open'"):
        _static_check("result = open('/etc/passwd').read()")


def test_dunder_access_blocked():
    with pytest.raises(SandboxViolation, match="dunder"):
        _static_check("result = ().__class__.__bases__")


def test_missing_result_variable_fails():
    out = run_in_sandbox("x = 1 + 1")
    assert not out.ok


def test_timeout_enforced():
    # Killed either by the wall-clock timeout or the CPU rlimit, whichever fires first.
    out = run_in_sandbox("while True:\n    pass\nresult = {}", timeout_seconds=2)
    assert not out.ok
    assert out.result is None
