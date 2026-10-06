#!/usr/bin/env python3
"""Unit tests for the Antigravity headless delegation wrapper."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import antigravity_delegate, shared_state  # noqa: E402


def test_parse_ndjson_events_collects_deltas_and_result():
    stream = "\n".join(
        [
            '{"event":"init","conversation_id":"conv_1"}',
            '{"event":"step_update","step_update":{"text_delta":"HELLO "}}',
            '{"event":"step_update","step_update":{"text_delta":"WORLD"}}',
            '{"event":"result","result":{"status":"SUCCESS","response":"HELLO WORLD","usage":{"total_tokens":4}}}',
        ]
    )

    result = antigravity_delegate.parse_ndjson_events(stream)

    assert result["conversation_id"] == "conv_1"
    assert result["text"] == "HELLO WORLD"
    assert result["response"] == "HELLO WORLD"
    assert result["usage"] == {"total_tokens": 4}
    assert result["error"] is None


def test_parse_ndjson_events_uses_result_response_when_no_delta():
    result = antigravity_delegate.parse_ndjson_events(
        '{"event":"result","result":{"status":"SUCCESS","response":"DONE"}}'
    )

    assert result["text"] == "DONE"


def test_parse_ndjson_events_requires_result_event():
    result = antigravity_delegate.parse_ndjson_events('{"event":"init"}')
    assert result["error"] == "Antigravity stream ended without a result event"


def test_parse_ndjson_events_reports_unsuccessful_result():
    result = antigravity_delegate.parse_ndjson_events(
        '{"event":"result","result":{"status":"ERROR","error":"bad request"}}'
    )

    assert result["error"] == "bad request"


def test_resolve_allowed_directory_rejects_path_outside_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "src").mkdir()

    assert antigravity_delegate.resolve_allowed_directory("src", workspace) == (workspace / "src", "src")
    with pytest.raises(ValueError, match="inside --target-dir"):
        antigravity_delegate.resolve_allowed_directory("..", workspace)
    with pytest.raises(ValueError, match="narrower directory"):
        antigravity_delegate.resolve_allowed_directory(".", workspace)


def test_changed_workspace_paths_detects_create_modify_and_delete():
    before = {"a.py": "one", "gone.py": "old"}
    after = {"a.py": "two", "new.py": "new"}

    assert antigravity_delegate.changed_workspace_paths(before, after) == ["a.py", "gone.py", "new.py"]


def test_paths_outside_directory_uses_path_boundaries():
    paths = ["src/a.py", "src2/b.py", "README.md"]

    assert antigravity_delegate.paths_outside_directory(paths, "src") == ["src2/b.py", "README.md"]
    assert antigravity_delegate.paths_outside_directory(paths, ".") == []


def test_build_prompt_is_read_only_without_auto_approval():
    prompt = antigravity_delegate.build_prompt(
        "inspect project", allow_dir=None, auto_approve=False, guardrail=True
    )

    assert "READ-ONLY MODE" in prompt
    assert "Allowed write directory" not in prompt


def test_build_prompt_names_writable_directory_when_auto_approved():
    prompt = antigravity_delegate.build_prompt(
        "edit code", allow_dir="src", auto_approve=True, guardrail=True
    )

    assert "Allowed write directory: src" in prompt
    assert "STRICT OPERATING CONSTRAINTS" in prompt


def test_snapshot_ignores_root_generated_dirs(tmp_path):
    ws = tmp_path / "ws"
    (ws / "src").mkdir(parents=True)
    (ws / ".venv" / "lib").mkdir(parents=True)
    (ws / ".pytest_temp_x").mkdir()
    (ws / "src" / "a.py").write_text("a", encoding="utf-8")
    (ws / ".venv" / "lib" / "v.py").write_text("v", encoding="utf-8")
    (ws / ".pytest_temp_x" / "t.py").write_text("t", encoding="utf-8")

    assert sorted(antigravity_delegate.snapshot_workspace(ws)) == ["src/a.py"]


def test_snapshot_keeps_workspace_under_ignored_name_in_its_path(tmp_path):
    """A workspace path containing 'build' must not prune every file."""
    ws = tmp_path / "build" / "ws"
    (ws / "src").mkdir(parents=True)
    (ws / "src" / "a.py").write_text("a", encoding="utf-8")

    before = antigravity_delegate.snapshot_workspace(ws)
    (ws / "src" / "a.py").write_text("changed", encoding="utf-8")
    after = antigravity_delegate.snapshot_workspace(ws)

    assert antigravity_delegate.changed_workspace_paths(before, after) == ["src/a.py"]


def test_snapshot_detects_change_in_nested_build_dir(tmp_path):
    """Only root-level build/dist are noise; a nested one can hold real content."""
    ws = tmp_path / "ws"
    (ws / "src").mkdir(parents=True)
    (ws / "docs" / "build").mkdir(parents=True)
    (ws / "docs" / "build" / "x.py").write_text("orig", encoding="utf-8")

    before = antigravity_delegate.snapshot_workspace(ws)
    (ws / "docs" / "build" / "x.py").write_text("out of scope", encoding="utf-8")
    after = antigravity_delegate.snapshot_workspace(ws)

    changed = antigravity_delegate.changed_workspace_paths(before, after)
    assert antigravity_delegate.paths_outside_directory(changed, "src") == ["docs/build/x.py"]


def _wire_main(monkeypatch, tmp_path):
    ws = tmp_path / "ws"
    (ws / "src").mkdir(parents=True)
    (ws / "docs").mkdir()
    db = tmp_path / "state.db"
    monkeypatch.setattr(antigravity_delegate, "find_agy_binary", lambda: "dummy-agy")
    monkeypatch.setattr(
        antigravity_delegate,
        "SharedState",
        lambda *args, **kwargs: shared_state.SharedState(db),
    )
    return ws, db


def _wrapper_argv(ws: Path) -> list[str]:
    return ["task", "--target-dir", str(ws), "--allow-dir", "src", "--auto-approve"]


def _run_main(monkeypatch, ws, result):
    monkeypatch.setattr(antigravity_delegate, "run_agy_cli", lambda **kwargs: result)
    return antigravity_delegate.main(_wrapper_argv(ws))


def test_main_returns_zero_on_success(monkeypatch, tmp_path):
    ws, _ = _wire_main(monkeypatch, tmp_path)
    assert _run_main(monkeypatch, ws, ({"text": "done", "error": None}, 0)) == 0


def test_main_returns_two_on_worker_error(monkeypatch, tmp_path):
    ws, _ = _wire_main(monkeypatch, tmp_path)
    assert _run_main(monkeypatch, ws, ({"text": "", "error": "boom"}, 2)) == 2


def test_main_preserves_timeout_exit_code(monkeypatch, tmp_path):
    ws, _ = _wire_main(monkeypatch, tmp_path)
    assert _run_main(monkeypatch, ws, ({"text": "", "error": "Timeout after 1s"}, 124)) == 124


def test_main_reports_scope_violation_before_worker_error(monkeypatch, tmp_path):
    ws, _ = _wire_main(monkeypatch, tmp_path)

    def fake_run(**kwargs):
        (kwargs["target_dir"] / "docs" / "escaped.py").write_text("x", encoding="utf-8")
        return {"text": "", "error": "boom"}, 2

    monkeypatch.setattr(antigravity_delegate, "run_agy_cli", fake_run)
    assert antigravity_delegate.main(_wrapper_argv(ws)) == 4


def test_main_reports_lock_conflict(monkeypatch, tmp_path):
    ws, db = _wire_main(monkeypatch, tmp_path)
    with shared_state.SharedState(db) as state:
        assert state.acquire_directory_lock(
            "src", engine="gemini", model="m", session_id="other"
        )

    assert _run_main(monkeypatch, ws, ({"text": "", "error": None}, 0)) == 3


def test_main_rejects_whole_workspace_allow_dir(monkeypatch, tmp_path):
    ws, _ = _wire_main(monkeypatch, tmp_path)
    with pytest.raises(SystemExit):
        antigravity_delegate.main(
            ["task", "--target-dir", str(ws), "--allow-dir", ".", "--auto-approve"]
        )


def test_main_requires_allow_dir_with_auto_approve(tmp_path):
    with pytest.raises(SystemExit):
        antigravity_delegate.main(["task", "--target-dir", str(tmp_path), "--auto-approve"])


def test_main_rejects_no_guardrail_with_auto_approve(tmp_path):
    (tmp_path / "src").mkdir()
    with pytest.raises(SystemExit):
        antigravity_delegate.main(
            [
                "task",
                "--target-dir",
                str(tmp_path),
                "--allow-dir",
                "src",
                "--auto-approve",
                "--no-guardrail",
            ]
        )


def test_run_agy_cli_maps_timeout_to_124(monkeypatch, tmp_path):
    def raise_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("agy", 1)

    monkeypatch.setattr(antigravity_delegate.subprocess, "run", raise_timeout)
    result, code = antigravity_delegate.run_agy_cli(
        prompt="p", model="m", target_dir=tmp_path, agy_binary="agy", auto_approve=False, timeout_s=1
    )

    assert code == 124
    assert result["error"] == "Timeout after 1s"


def test_run_agy_cli_maps_oserror_to_one(monkeypatch, tmp_path):
    def raise_oserror(*args, **kwargs):
        raise OSError("not found")

    monkeypatch.setattr(antigravity_delegate.subprocess, "run", raise_oserror)
    _, code = antigravity_delegate.run_agy_cli(
        prompt="p", model="m", target_dir=tmp_path, agy_binary="agy", auto_approve=False, timeout_s=1
    )

    assert code == 1


def test_run_agy_cli_keeps_nonzero_exit_code(monkeypatch, tmp_path):
    class Completed:
        returncode = 3
        stdout = '{"event":"result","result":{"status":"SUCCESS","response":"ok"}}'
        stderr = ""

    monkeypatch.setattr(antigravity_delegate.subprocess, "run", lambda *a, **k: Completed())
    _, code = antigravity_delegate.run_agy_cli(
        prompt="p", model="m", target_dir=tmp_path, agy_binary="agy", auto_approve=True, timeout_s=5
    )

    assert code == 3


def test_find_agy_binary_prefers_path(monkeypatch):
    monkeypatch.setattr(antigravity_delegate.shutil, "which", lambda name: "C:/bin/agy.exe")

    assert antigravity_delegate.find_agy_binary() == "C:/bin/agy.exe"


def test_find_agy_binary_uses_local_app_data(monkeypatch, tmp_path):
    exe = tmp_path / "agy" / "bin" / "agy.exe"
    exe.parent.mkdir(parents=True)
    exe.write_text("", encoding="utf-8")
    monkeypatch.setattr(antigravity_delegate.shutil, "which", lambda name: None)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    assert antigravity_delegate.find_agy_binary() == str(exe)


def test_find_agy_binary_returns_none_when_absent(monkeypatch, tmp_path):
    monkeypatch.setattr(antigravity_delegate.shutil, "which", lambda name: None)
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    monkeypatch.setattr(antigravity_delegate.Path, "home", classmethod(lambda cls: tmp_path))

    assert antigravity_delegate.find_agy_binary() is None
