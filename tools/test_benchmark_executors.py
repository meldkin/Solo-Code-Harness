"""Tests for tools/benchmark_executors.py — task setup and structure."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import benchmark_executors as bm  # noqa: E402


def test_tasks_do_not_contain_shell_heredocs():
    """Tasks must not use bash heredocs ('cat > ... << EOF') which fail on Windows."""
    for name, task in bm.TASKS.items():
        setup = task.get("setup")
        if isinstance(setup, str):
            assert "cat >" not in setup, f"Task {name} contains shell heredoc 'cat >'"
            assert "<<" not in setup, f"Task {name} contains redirection '<<'"


def test_setup_task_dict_writes_files(tmp_path, monkeypatch):
    """setup_task with a dict writes files directly without shell execution."""
    monkeypatch.chdir(tmp_path)
    task = {
        "setup": {
            "test_file.py": "x = 42\n",
            "nested/file.txt": "hello\n",
        }
    }
    (tmp_path / "nested").mkdir()
    bm.setup_task(task)

    assert (tmp_path / "test_file.py").read_text(encoding="utf-8") == "x = 42\n"
    assert (tmp_path / "nested" / "file.txt").read_text(encoding="utf-8") == "hello\n"


def test_refactor_code_setup(tmp_path, monkeypatch):
    """refactor_code task creates temp_messy.py with valid python code."""
    monkeypatch.chdir(tmp_path)
    bm.setup_task(bm.TASKS["refactor_code"])

    target = tmp_path / "temp_messy.py"
    assert target.is_file()
    content = target.read_text(encoding="utf-8")
    assert "def calc(a,b,op):" in content


def test_add_test_setup(tmp_path, monkeypatch):
    """add_test task creates temp_util.py with valid python code."""
    monkeypatch.chdir(tmp_path)
    bm.setup_task(bm.TASKS["add_test"])

    target = tmp_path / "temp_util.py"
    assert target.is_file()
    content = target.read_text(encoding="utf-8")
    assert "def parse_version(ver: str)" in content
