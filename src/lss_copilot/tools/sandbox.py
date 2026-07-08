"""Secure Python sandbox for the Statistical Engine agent.

The engine LLM may only *write* analysis code; execution happens here in a
separate process with:
  - CPU / memory rlimits and a wall-clock timeout,
  - an empty environment (no inherited secrets, proxies stripped),
  - an AST import allowlist (numpy/scipy/pandas/math/statistics/json only),
  - results returned exclusively via a JSON `result` variable.

This is defense-in-depth for a *cooperative* agent, not a hostile-code jail;
for untrusted multi-tenant workloads run it inside a container/gVisor too.
"""

from __future__ import annotations

import ast
import json
import resource
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ALLOWED_IMPORTS = {"numpy", "scipy", "pandas", "math", "statistics", "json"}
_FORBIDDEN_NODES = (ast.Global,)
_FORBIDDEN_CALLS = {"eval", "exec", "compile", "open", "__import__", "input", "breakpoint"}


class SandboxViolation(Exception):
    """Raised before execution when submitted code fails static checks."""


@dataclass
class SandboxResult:
    ok: bool
    result: dict | list | None
    stdout: str
    stderr: str


def _static_check(code: str) -> None:
    tree = ast.parse(code)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            module = node.names[0].name if isinstance(node, ast.Import) else (node.module or "")
            root = module.split(".")[0]
            if root not in ALLOWED_IMPORTS:
                raise SandboxViolation(f"import of '{root}' is not allowed")
        if isinstance(node, _FORBIDDEN_NODES):
            raise SandboxViolation(f"{type(node).__name__} is not allowed")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                and node.func.id in _FORBIDDEN_CALLS:
            raise SandboxViolation(f"call to '{node.func.id}' is not allowed")
        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            raise SandboxViolation("dunder attribute access is not allowed")


def _limits(memory_mb: int, cpu_seconds: int):
    def apply() -> None:
        resource.setrlimit(resource.RLIMIT_AS, (memory_mb * 1024**2,) * 2)
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds,) * 2)
        resource.setrlimit(resource.RLIMIT_NPROC, (64, 64))
        resource.setrlimit(resource.RLIMIT_FSIZE, (32 * 1024**2,) * 2)
    return apply


def run_in_sandbox(
    code: str,
    input_data: dict | None = None,
    timeout_seconds: int = 30,
    memory_mb: int = 512,
) -> SandboxResult:
    """Execute analysis code. The snippet receives `data` (parsed JSON) and
    must assign its JSON-serializable output to a variable named `result`."""
    _static_check(code)

    harness = (
        "import json, sys\n"
        "data = json.load(open(sys.argv[1]))\n" if input_data is not None
        else "import json, sys\ndata = None\n"
    )
    footer = (
        "\nif 'result' not in dict(globals()):\n"
        "    raise RuntimeError('code must assign a `result` variable')\n"
        "print('__LSS_RESULT__' + json.dumps(result))\n"
    )

    with tempfile.TemporaryDirectory(prefix="lss-sbx-") as tmp:
        script = Path(tmp) / "job.py"
        script.write_text(harness + code + footer)
        argv = [sys.executable, "-I", str(script)]
        if input_data is not None:
            payload = Path(tmp) / "data.json"
            payload.write_text(json.dumps(input_data))
            argv.append(str(payload))
        try:
            proc = subprocess.run(
                argv,
                capture_output=True, text=True, timeout=timeout_seconds,
                cwd=tmp, env={"PYTHONPATH": ""},  # no secrets, no proxy, no site cwd
                preexec_fn=_limits(memory_mb, timeout_seconds),
            )
        except subprocess.TimeoutExpired:
            return SandboxResult(False, None, "", f"timed out after {timeout_seconds}s")

    result = None
    stdout_lines = []
    for line in proc.stdout.splitlines():
        if line.startswith("__LSS_RESULT__"):
            result = json.loads(line[len("__LSS_RESULT__"):])
        else:
            stdout_lines.append(line)
    return SandboxResult(
        ok=proc.returncode == 0 and result is not None,
        result=result,
        stdout="\n".join(stdout_lines),
        stderr=proc.stderr,
    )
