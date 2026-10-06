#!/usr/bin/env python3
"""
Kilo CLI Delegate — unit tests
==============================
Unit coverage for tools/kilo_cli_delegate.py helpers that need no network.

Background: on Windows an npm install puts `kilo.cmd` on PATH. Its batch `%*`
expansion destroys multi-line arguments (the guardrail reaches the model
truncated or empty). `find_kilo_binary` must prefer a real executable.

Usage:
    python -m pytest tools/test_kilo_cli_delegate.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import kilo_cli_delegate  # noqa: E402


def test_is_batch_shim_detects_cmd_and_bat_on_windows():
    assert kilo_cli_delegate._is_batch_shim("C:/x/kilo.cmd", platform="win32")
    assert kilo_cli_delegate._is_batch_shim("C:/x/kilo.bat", platform="win32")


def test_is_batch_shim_ignores_exe_and_posix():
    assert not kilo_cli_delegate._is_batch_shim("C:/x/kilo.exe", platform="win32")
    assert not kilo_cli_delegate._is_batch_shim("/usr/bin/kilo.cmd", platform="linux")


def test_wrapped_executable_finds_node_modules_exe(tmp_path):
    shim = tmp_path / "kilo.cmd"
    shim.write_text("@echo off\n", encoding="utf-8")
    real = tmp_path / "node_modules" / "@kilocode" / "cli" / "bin" / "kilo.exe"
    real.parent.mkdir(parents=True)
    real.write_text("", encoding="utf-8")

    assert kilo_cli_delegate._wrapped_executable(str(shim)) == str(real)


def test_wrapped_executable_is_none_when_absent(tmp_path):
    shim = tmp_path / "kilo.cmd"
    shim.write_text("@echo off\n", encoding="utf-8")

    assert kilo_cli_delegate._wrapped_executable(str(shim)) is None


def test_find_kilo_binary_prefers_real_candidate_over_shim(tmp_path, monkeypatch):
    shim = tmp_path / "kilo.cmd"
    shim.write_text("", encoding="utf-8")
    real = tmp_path / "kilo.exe"
    real.write_text("", encoding="utf-8")

    monkeypatch.setattr(kilo_cli_delegate.shutil, "which", lambda name: str(shim))
    monkeypatch.setattr(kilo_cli_delegate, "_real_kilo_candidates", lambda: [real])

    assert kilo_cli_delegate.find_kilo_binary(platform="win32") == str(real)


def test_find_kilo_binary_uses_wrapped_exe_when_no_candidate(tmp_path, monkeypatch):
    shim = tmp_path / "kilo.cmd"
    shim.write_text("", encoding="utf-8")
    real = tmp_path / "node_modules" / "kilo" / "bin" / "kilo.exe"
    real.parent.mkdir(parents=True)
    real.write_text("", encoding="utf-8")

    monkeypatch.setattr(kilo_cli_delegate.shutil, "which", lambda name: str(shim))
    monkeypatch.setattr(kilo_cli_delegate, "_real_kilo_candidates", list)

    assert kilo_cli_delegate.find_kilo_binary(platform="win32") == str(real)


def test_find_kilo_binary_returns_real_path_directly(monkeypatch):
    monkeypatch.setattr(kilo_cli_delegate.shutil, "which", lambda name: "/usr/bin/kilo")

    assert kilo_cli_delegate.find_kilo_binary(platform="linux") == "/usr/bin/kilo"


def test_parse_json_events_extracts_text_and_session():
    stream = "\n".join(
        [
            '{"type":"step_start","sessionID":"ses_kilo"}',
            '{"type":"text","part":{"text":"PONG"}}',
            '{"type":"step_finish","part":{"tokens":{"total":5}}}',
        ]
    )
    result = kilo_cli_delegate.parse_json_events(stream)

    assert result["text"] == "PONG"
    assert result["session_id"] == "ses_kilo"
    assert result["tokens"] == {"total": 5}


def test_make_streams_encoding_safe_relaxes_errors(monkeypatch):
    calls = {}

    class FakeStream:
        def reconfigure(self, **kwargs):
            calls.update(kwargs)

    monkeypatch.setattr(kilo_cli_delegate.sys, "stdout", FakeStream())
    monkeypatch.setattr(kilo_cli_delegate.sys, "stderr", FakeStream())

    kilo_cli_delegate._make_streams_encoding_safe()

    assert calls.get("encoding") == "utf-8"
    assert calls.get("errors") == "replace"


def test_make_streams_encoding_safe_tolerates_missing_reconfigure(monkeypatch):
    class Bare:
        pass

    monkeypatch.setattr(kilo_cli_delegate.sys, "stdout", Bare())
    monkeypatch.setattr(kilo_cli_delegate.sys, "stderr", Bare())

    kilo_cli_delegate._make_streams_encoding_safe()
