"""Tests for tools/coverage_gate.py — per-file coverage ratchet."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import coverage_gate  # noqa: E402


def test_main_help_flag(monkeypatch, capsys):
    """--help should print docstring usage and exit 0 without running coverage."""
    monkeypatch.setattr(sys, "argv", ["coverage_gate.py", "--help"])
    assert coverage_gate.main() == 0
    out = capsys.readouterr().out
    assert "Coverage Gate" in out
    assert "--update" in out


def test_main_short_help_flag(monkeypatch, capsys):
    """-h should print docstring usage and exit 0 without running coverage."""
    monkeypatch.setattr(sys, "argv", ["coverage_gate.py", "-h"])
    assert coverage_gate.main() == 0
    out = capsys.readouterr().out
    assert "Coverage Gate" in out


def test_load_budget_missing_file(tmp_path):
    """Missing budget file returns empty dict."""
    assert coverage_gate.load_budget(tmp_path / "nonexistent.json") is None


def test_load_budget_valid(tmp_path):
    """Valid budget JSON loads correctly."""
    bfile = tmp_path / "budget.json"
    bfile.write_text(json.dumps({"files": {"tools/deploy.py": 85.5}}), encoding="utf-8")
    loaded = coverage_gate.load_budget(bfile)
    assert loaded == {"tools/deploy.py": 85.5}


def test_load_budget_malformed(tmp_path):
    """Malformed budget JSON raises ValueError."""
    bfile = tmp_path / "budget.json"
    bfile.write_text("not json", encoding="utf-8")
    with pytest.raises(ValueError, match="Malformed budget file"):
        coverage_gate.load_budget(bfile)


def test_check_ratchet_maintained():
    """Ratchet passes when all files maintain coverage."""
    budget = {"a.py": 80.0, "b.py": 90.0}
    current = {"a.py": 80.0, "b.py": 95.0}
    passed, violations = coverage_gate.check_ratchet(budget, current)
    assert passed is True
    assert violations == []


def test_check_ratchet_decreased():
    """Ratchet fails when coverage drops below budget."""
    budget = {"a.py": 80.0, "b.py": 90.0}
    current = {"a.py": 75.0, "b.py": 90.0}
    passed, violations = coverage_gate.check_ratchet(budget, current)
    assert passed is False
    assert len(violations) == 1
    assert "a.py: 80.0% -> 75.0%" in violations[0]
