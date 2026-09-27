#!/usr/bin/env python3
"""
opencode_delegate.py — CLI-based delegation wrapper for OpenCode workers.

ORCHESTRATION MODEL: Claude Code is ALWAYS the orchestrator.
This script uses `opencode run` to send a single stateless prompt to OpenCode
and parses the JSON events stream. The orchestrator must read and verify every result.

CLI APPROACH (OpenCode v2 `run`):
  opencode run "prompt" --format json --auto --standalone --model provider/model

OPENCODE V2 NOTES (verified 2026-09-27, @opencode/cli 2.0.18):
  - `run` keeps the v1 flags used here: --format json, --auto, -m/--model.
  - v2 `--format json` emits `step_start` and `text` events only; there is no
    `step_finish` event, so token and cost fields log as null. The parser keeps
    step_finish handling for forward compatibility with a build that restores it.
  - --standalone runs a private server, so delegation never touches the user's
    shared background OpenCode server or its sessions.
  - The provider is self-contained in opencode.json (v2 `providers`), replacing
    the retired v1 plugin `commandcode-go-opencode-provider`.

Usage:
    python tools/opencode_delegate.py "<self-contained prompt>"
    python tools/opencode_delegate.py "<prompt>" --model commandcode/deepseek-v4-pro
    python tools/opencode_delegate.py "<prompt>" --model opencode/deepseek-v4-flash-free
    python tools/opencode_delegate.py "<prompt>" --no-guardrail

Requires OpenCode CLI installed: https://opencode.ai/install
Auth: opencode providers login <url>
"""

import argparse
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── Constants ────────────────────────────────────────────────────────────────

DEFAULT_MODEL = "commandcode/deepseek-v4-pro"
# OpenCode v2 dropped `opencode/deepseek-v4-flash-free`; the free tier now
# exposes models such as opencode/mimo-v2.6-flash-free (verified 2026-09-27).
FREE_MODEL = "opencode/mimo-v2.6-flash-free"

USAGE_LOG = Path(".solocode/opencode-usage.jsonl")
USAGE_LOG.parent.mkdir(parents=True, exist_ok=True)

GUARDRAIL = """\
STRICT OPERATING CONSTRAINTS (must follow, no exceptions):
1. Modify ONLY the files explicitly named in the task below. Do not touch
   any other file, and do not refactor nearby code that wasn't asked for.
2. Do NOT add new dependencies, new files, or new abstractions unless the
   task explicitly asks for them.
3. Match the existing code style/conventions of the surrounding file
   exactly (naming, formatting, error handling patterns).
4. If the task is ambiguous or underspecified, STOP and report back what
   is missing instead of guessing or inventing scope.
5. Never run destructive commands (git push, --force, rm -rf, DB
   migrations) under any circumstance.
6. End your response with a one-line self-check: "Scope check: touched
   only <file list>; no dependencies added" (or state exactly what
   deviated and why).

Your permission scope was frozen when this task was created and cannot be expanded. If you hit a boundary beyond that scope, do not retry or work around it — stop and report exactly what is out of scope so the orchestrator can decide.

"""

# ── Helper Functions ─────────────────────────────────────────────────────────

def _stderr(msg: str) -> None:
    """Print to stderr with [opencode_delegate] prefix."""
    print(f"[opencode_delegate] {msg}", file=sys.stderr)


# npm/bun installs put a `.cmd`/`.bat` shim on PATH. Its `%*` expansion mangles
# multi-line arguments (the guardrail prompt reaches the model truncated to its
# first line) and can drop trailing flags like `--format json`. The shim wraps a
# real executable; prefer that.
# OpenCode v2 ships only as the npm package `@opencode/cli` (bins opencode,
# opencode2). The retired v1 package `opencode-ai` is deliberately not listed:
# resolving it would run the old CLI against a v2 config.
_SHIM_WRAPPED_RELATIVE_PATHS = (
    Path("node_modules") / "@opencode" / "cli" / "bin" / "opencode.exe",
    Path("node_modules") / "@opencode" / "cli" / "bin" / "opencode",
)


def _prefer_real_executable(binary: str, *, platform: str | None = None) -> str:
    """Return the executable a Windows `.cmd`/`.bat` shim wraps, if it exists.

    On Windows `shutil.which("opencode")` usually returns an npm shim
    (`opencode.cmd`). Running that via subprocess expands arguments through the
    batch `%*`, which truncates multi-line arguments at the first newline and can
    drop trailing flags. Pointing at the wrapped executable avoids the shim.
    Non-Windows and non-shim paths are returned unchanged.
    """
    platform = platform or sys.platform
    if platform != "win32":
        return binary
    shim = Path(binary)
    if shim.suffix.lower() not in (".cmd", ".bat"):
        return binary
    for rel in _SHIM_WRAPPED_RELATIVE_PATHS:
        candidate = shim.parent / rel
        if candidate.is_file():
            return str(candidate)
    return binary


def find_opencode_binary() -> str | None:
    """Find OpenCode CLI binary. Check PATH first, then common install locations."""
    # Check PATH (bypass a Windows npm shim if it wraps a real executable).
    opencode_path = shutil.which("opencode")
    if opencode_path:
        return _prefer_real_executable(opencode_path)

    # Fall back to the @opencode/cli binary next to the node executable, which
    # covers nvm-windows / nvm global installs whose shim is not on PATH. The
    # ~/.opencode/bin native binary is intentionally NOT used: a v1
    # self-updating install can sit there (it did on this machine as v1.18.31
    # until 2026-09-28) and would run the old CLI against a v2 config.
    node_path = shutil.which("node")
    if node_path:
        cli_dir = Path(node_path).parent / "node_modules" / "@opencode" / "cli" / "bin"
        for name in ("opencode.exe", "opencode"):
            candidate = cli_dir / name
            if candidate.is_file():
                return str(candidate)

    return None


def parse_json_events(output: str) -> dict[str, Any]:
    """Parse JSON events stream from opencode run --format json output.

    Returns dict with:
        - text: concatenated text from all text events
        - events: list of all parsed events
        - session_id: session ID from first event
        - tokens: token usage from a step_finish event, when present (v2
          `--format json` emitting only step_start/text leaves this None)
        - cost: cost from a step_finish event, when present
        - error: error message if any error event found
    """
    result: dict[str, Any] = {
        "text": "",
        "events": [],
        "session_id": None,
        "tokens": None,
        "cost": None,
        "error": None,
    }

    for line in output.strip().split("\n"):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
            result["events"].append(event)

            # Extract session ID from first event
            if result["session_id"] is None and "sessionID" in event:
                result["session_id"] = event["sessionID"]

            # Concatenate text from text events
            if event.get("type") == "text":
                part = event.get("part", {})
                text = part.get("text", "")
                result["text"] += text

            # Extract tokens/cost from step_finish
            if event.get("type") == "step_finish":
                part = event.get("part", {})
                result["tokens"] = part.get("tokens")
                result["cost"] = part.get("cost")

            # Capture errors
            if event.get("type") == "error":
                error_data = event.get("error", {})
                result["error"] = error_data.get("data", {}).get("message", "Unknown error")

        except json.JSONDecodeError:
            # Skip non-JSON lines (banner, warnings)
            continue

    return result


def run_opencode_cli(
    prompt: str,
    model: str,
    directory: str,
    opencode_binary: str,
    timeout_s: int = 120,
) -> dict[str, Any]:
    """Run opencode CLI, return parsed JSON events."""
    cmd = [
        opencode_binary,
        "run",
        prompt,
        "--model", model,
        "--format", "json",
        "--auto",  # auto-approve non-destructive permissions
        "--standalone",  # private server — do not touch the shared user server
    ]

    _stderr(f"Running: opencode run ... --model {model} --format json --auto")

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_s,
            check=False,
            cwd=directory,
        )

        if proc.returncode != 0 and not proc.stdout.strip():
            # No JSON output, likely binary error
            _stderr(f"opencode CLI failed with exit code {proc.returncode}")
            if proc.stderr:
                _stderr(f"stderr: {proc.stderr[:500]}")
            return {
                "text": "",
                "events": [],
                "session_id": None,
                "tokens": None,
                "cost": None,
                "error": f"opencode CLI exit code {proc.returncode}",
            }

        # Parse JSON events from stdout
        return parse_json_events(proc.stdout)

    except subprocess.TimeoutExpired:
        _stderr(f"opencode CLI timed out after {timeout_s}s")
        return {
            "text": "",
            "events": [],
            "session_id": None,
            "tokens": None,
            "cost": None,
            "error": f"Timeout after {timeout_s}s",
        }
    except Exception as exc:
        _stderr(f"opencode CLI failed: {exc}")
        return {
            "text": "",
            "events": [],
            "session_id": None,
            "tokens": None,
            "cost": None,
            "error": str(exc),
        }


def log_usage(
    model: str,
    prompt_len: int,
    elapsed: float,
    result: dict[str, Any],
) -> None:
    """Log delegation call to .solocode/opencode-usage.jsonl for auditing."""
    entry: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "prompt_chars": prompt_len,
        "elapsed_s": round(elapsed, 2),
        "session_id": result.get("session_id"),
        "usage": result.get("tokens"),
        "cost": result.get("cost"),
        "error": result.get("error"),
    }
    with USAGE_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")


# ── Main ─────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="OpenCode CLI delegation wrapper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Every call is logged to " + str(USAGE_LOG),
    )
    parser.add_argument(
        "prompt",
        help="Self-contained task prompt (inline all needed context)",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Model in provider/model format (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--directory",
        default=".",
        help="Working directory for opencode CLI (default: current dir)",
    )
    parser.add_argument(
        "--no-guardrail",
        action="store_true",
        help="Skip prepending the strict guardrail preamble",
    )
    parser.add_argument(
        "--opencode-bin",
        help="Path to opencode binary (auto-detected if not provided)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Timeout in seconds (default: 120)",
    )
    parser.add_argument(
        "--free",
        action="store_true",
        help=f"Use free model ({FREE_MODEL})",
    )

    args = parser.parse_args(argv)

    # ── Find OpenCode binary ──
    opencode_binary = args.opencode_bin or find_opencode_binary()
    if not opencode_binary:
        _stderr("OpenCode binary not found. Install from https://opencode.ai/install")
        return 1

    _stderr(f"Using OpenCode binary: {opencode_binary}")

    # ── Override model if --free ──
    model = FREE_MODEL if args.free else args.model

    # ── Prepend guardrail unless disabled ──
    prompt = args.prompt
    if not args.no_guardrail:
        prompt = GUARDRAIL + prompt

    _stderr(f"model={model}")

    # ── Run opencode CLI → parse events → log ──
    start = time.monotonic()
    result = run_opencode_cli(
        prompt=prompt,
        model=model,
        directory=args.directory,
        opencode_binary=opencode_binary,
        timeout_s=args.timeout,
    )
    elapsed = time.monotonic() - start

    log_usage(model, len(prompt), elapsed, result)

    # ── Output ──
    if result.get("error"):
        _stderr(f"Error: {result['error']}")
        return 2

    # Print the concatenated text response (handle Unicode on Windows)
    import sys
    if sys.platform == "win32":
        # Force UTF-8 output on Windows
        sys.stdout.reconfigure(encoding='utf-8')
    print(result["text"])

    _stderr(f"session={result.get('session_id')}  elapsed={elapsed:.1f}s")
    if result.get("tokens"):
        tokens = result["tokens"]
        _stderr(
            f"tokens: in={tokens.get('input')} out={tokens.get('output')} "
            f"reasoning={tokens.get('reasoning')} total={tokens.get('total')} "
            f"cache_read={tokens.get('cache', {}).get('read')} "
            f"cache_write={tokens.get('cache', {}).get('write')}"
        )
    if result.get("cost") is not None:
        _stderr(f"cost: ${result['cost']:.6f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
