"""Runs submitted code in an isolated subprocess with time/memory limits.

This is a learning tool, not a security sandbox — but the isolation below
raises the bar well above running code in the server process:
  * separate process, killed after the timeout
  * python -I  (isolated mode: ignores env vars, user site-packages, cwd on path)
  * empty stdin
  * RLIMIT_CPU / RLIMIT_AS / RLIMIT_FSIZE on Linux
  * disposable temp working directory
"""

from __future__ import annotations

import os
import resource
import subprocess
import sys
import tempfile
import time

MAX_OUTPUT = 20_000
DEFAULT_TIMEOUT = 5.0


def _limits(timeout: float):  # pragma: no cover - runs in child process
    try:
        cpu = int(timeout) + 2
        resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))
        resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024,) * 2)
        resource.setrlimit(resource.RLIMIT_FSIZE, (1024 * 1024,) * 2)
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    except Exception:
        pass  # non-POSIX or restricted container — proceed without limits


def run_code(code: str, timeout: float = DEFAULT_TIMEOUT) -> dict:
    start = time.monotonic()
    result = {
        "stdout": "",
        "stderr": "",
        "exit_code": None,
        "duration": 0.0,
        "timed_out": False,
    }
    try:
        with tempfile.TemporaryDirectory(prefix="pla_run_") as tmp:
            path = os.path.join(tmp, "main.py")
            with open(path, "w", encoding="utf-8") as f:
                f.write(code)
            try:
                proc = subprocess.run(
                    [sys.executable, "-I", path],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    stdin=subprocess.DEVNULL,
                    cwd=tmp,
                    env={"PATH": "/usr/bin:/bin", "HOME": tmp, "PYTHONDONTWRITEBYTECODE": "1"},
                    preexec_fn=lambda: _limits(timeout),
                )
                result["stdout"] = proc.stdout
                result["stderr"] = proc.stderr
                result["exit_code"] = proc.returncode
            except subprocess.TimeoutExpired as e:
                result["timed_out"] = True
                result["stdout"] = (e.stdout or b"").decode(errors="replace") \
                    if isinstance(e.stdout, bytes) else (e.stdout or "")
                result["stderr"] = (e.stderr or b"").decode(errors="replace") \
                    if isinstance(e.stderr, bytes) else (e.stderr or "")
    except Exception as e:  # noqa: BLE001 - surface anything odd to the UI
        result["stderr"] = f"runner error: {e}"
    result["duration"] = round(time.monotonic() - start, 3)
    for key in ("stdout", "stderr"):
        result[key] = result[key][:MAX_OUTPUT]
    return result
