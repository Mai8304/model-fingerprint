from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def test_cli_module_imports() -> None:
    sys.path.insert(0, str(SRC))
    try:
        __import__("modelfingerprint.cli")
    finally:
        sys.path.pop(0)


def test_python_module_help_exits_zero() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC)

    result = subprocess.run(
        [sys.executable, "-m", "modelfingerprint.cli", "--help"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
