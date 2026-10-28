"""Boundaries of the modular monolith, as declared in `pyproject.toml` (`[tool.importlinter]`)."""

import subprocess
import sys
from pathlib import Path

# Folder with `pyproject.toml`, where import-linter reads its contracts.
BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_modules_respect_their_boundaries():
    result = subprocess.run(
        [sys.executable, "-c", "from importlinter.cli import lint_imports_command; lint_imports_command()"],
        cwd=BACKEND_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
