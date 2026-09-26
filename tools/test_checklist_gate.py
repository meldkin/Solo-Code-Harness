#!/usr/bin/env python3
"""Checklist gate tests.

Pin the mandatory-vs-optional tool policy in `.github/scripts/checklist.py`:
a missing REQUIRED tool must fail the gate (the gate cannot verify what it
claims), while a missing OPTIONAL tool may skip cleanly. Before this policy,
`FileNotFoundError` returned `passed=True, skipped=True` for every tool,
so a machine without `ruff` reported a green gate.

Usage:
    python -m pytest tools/test_checklist_gate.py -v
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHECKLIST = ROOT / ".github" / "scripts" / "checklist.py"

# A binary name that cannot exist; used to trigger FileNotFoundError.
_MISSING = "definitely-not-a-real-binary-xyz-12345"


def _load_checklist():
    """Load checklist.py by path (it lives outside the tools/ package)."""
    spec = importlib.util.spec_from_file_location("checklist_under_test", CHECKLIST)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_missing_required_tool_fails() -> None:
    """A required tool missing from PATH must FAIL the check."""
    module = _load_checklist()
    result = module.run_check("Missing required", [_MISSING], required=True)
    assert result["passed"] is False
    assert result["skipped"] is False


def test_missing_optional_tool_is_skipped() -> None:
    """An optional tool missing from PATH may skip cleanly."""
    module = _load_checklist()
    result = module.run_check("Missing optional", [_MISSING], required=False)
    assert result["passed"] is True
    assert result["skipped"] is True


def test_failing_command_is_failure_not_skip() -> None:
    """A command that runs but exits non-zero must FAIL, not skip."""
    module = _load_checklist()
    result = module.run_check("Failing", [sys.executable, "-c", "raise SystemExit(1)"])
    assert result["passed"] is False
    assert result["skipped"] is False


def test_passing_command_passes() -> None:
    """A command that exits zero must PASS and not be marked skipped."""
    module = _load_checklist()
    result = module.run_check("Passing", [sys.executable, "-c", "raise SystemExit(0)"])
    assert result["passed"] is True
    assert result["skipped"] is False
