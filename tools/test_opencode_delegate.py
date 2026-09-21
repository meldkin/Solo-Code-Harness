#!/usr/bin/env python3
"""
OpenCode Delegate — unit tests
==============================
Unit coverage for tools/opencode_delegate.py helpers that need no network.

Background: on Windows, shutil.which("opencode") returns an npm `.cmd` shim
whose batch `%*` expansion truncates multi-line arguments at the first newline
and can drop trailing flags like `--format json`. That made every delegated run
return empty output. `_prefer_real_executable` points at the wrapped executable.

Usage:
    python -m pytest tools/test_opencode_delegate.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import opencode_delegate  # noqa: E402


def test_prefer_real_executable_resolves_npm_shim(tmp_path):
    shim = tmp_path / "opencode.cmd"
    shim.write_text("@echo off\n", encoding="utf-8")
    real = tmp_path / "node_modules" / "opencode-ai" / "bin" / "opencode.exe"
    real.parent.mkdir(parents=True)
    real.write_text("", encoding="utf-8")

    assert opencode_delegate._prefer_real_executable(str(shim), platform="win32") == str(real)


def test_prefer_real_executable_resolves_v2_npm_shim(tmp_path):
    shim = tmp_path / "opencode.cmd"
    shim.write_text("@echo off\n", encoding="utf-8")
    real = tmp_path / "node_modules" / "@opencode" / "cli" / "bin" / "opencode.exe"
    real.parent.mkdir(parents=True)
    real.write_text("", encoding="utf-8")

    assert opencode_delegate._prefer_real_executable(str(shim), platform="win32") == str(real)


def test_prefer_real_executable_keeps_shim_without_wrapped_exe(tmp_path):
    shim = tmp_path / "opencode.cmd"
    shim.write_text("@echo off\n", encoding="utf-8")

    assert opencode_delegate._prefer_real_executable(str(shim), platform="win32") == str(shim)


def test_prefer_real_executable_ignores_non_shim(tmp_path):
    exe = tmp_path / "opencode.exe"
    exe.write_text("", encoding="utf-8")

    assert opencode_delegate._prefer_real_executable(str(exe), platform="win32") == str(exe)


def test_prefer_real_executable_noop_on_posix(tmp_path):
    shim = tmp_path / "opencode"
    shim.write_text("", encoding="utf-8")

    assert opencode_delegate._prefer_real_executable(str(shim), platform="linux") == str(shim)


def test_parse_json_events_extracts_text_session_and_tokens():
    stream = "\n".join(
        [
            '{"type":"step_start","sessionID":"ses_abc"}',
            '{"type":"text","part":{"text":"PONG"}}',
            '{"type":"step_finish","part":{"tokens":{"total":3},"cost":0.0}}',
            "opencode banner, not json",
        ]
    )
    result = opencode_delegate.parse_json_events(stream)

    assert result["text"] == "PONG"
    assert result["session_id"] == "ses_abc"
    assert result["tokens"] == {"total": 3}
    assert result["cost"] == 0.0
    assert result["error"] is None


def test_parse_json_events_captures_error():
    stream = '{"type":"error","error":{"data":{"message":"boom"}}}'

    assert opencode_delegate.parse_json_events(stream)["error"] == "boom"
