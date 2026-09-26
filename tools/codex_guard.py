#!/usr/bin/env python3
"""Preflight guard for commands and files invoked by Codex CLI.

Codex cannot install repository hooks, so this is an explicit fail-closed
check used by wrappers and can also be called before risky shell operations.
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.claude_guard_compat import find_destructive, find_secret  # noqa: E402
from tools.shared_state import SharedState  # noqa: E402


def _state() -> SharedState:
    """Open shared state, honouring an explicit DB path for tests.

    Production uses the default `.solocode/shared-state.db`. Tests may set
    `CODEX_GUARD_STATE_DB` to isolate lock assertions to a temp DB so they
    never touch (or leak into) the local production state.
    """
    override = os.environ.get("CODEX_GUARD_STATE_DB")
    return SharedState(Path(override)) if override else SharedState()


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--command")
    group.add_argument("--content")
    parser.add_argument("--path", default="")
    parser.add_argument("--write", action="store_true", help="Write content to --path after verification")
    args = parser.parse_args()
    if args.write and not args.path:
        print("ERROR: --write requires --path", file=sys.stderr)
        return 2
    if args.write and args.command is not None:
        print("ERROR: --write cannot be used with --command", file=sys.stderr)
        return 2
    value = args.command if args.command is not None else args.content
    if args.command is not None:
        hit = find_destructive(value)
        if hit:
            print(f"BLOCKED: {hit}", file=sys.stderr)
            return 2
        if find_secret(value):
            print("BLOCKED: possible secret in command", file=sys.stderr)
            return 2
    elif find_secret(value):
        print("BLOCKED: possible secret in content", file=sys.stderr)
        return 2

    # Give each guard process its own owner identity. A shared Codex session ID
    # would let overlapping guard invocations release each other's locks.
    session_id = uuid.uuid4().hex
    state = _state()
    acquired = False
    try:
        if args.path:
            acquired = state.acquire_lock(
                args.path,
                engine="codex",
                model="codex-cli",
                session_id=session_id,
                reason="codex_guard write",
            )
            if not acquired:
                print(f"BLOCKED: file lock held by another engine: {args.path}", file=sys.stderr)
                return 2
        if args.write:
            target = Path(args.path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(args.content, encoding="utf-8")
            print(f"WROTE: {args.path}")
        return 0
    finally:
        if acquired:
            try:
                state.release_lock(args.path, engine="codex", session_id=session_id)
            except sqlite3.Error as exc:
                print(f"WARNING: failed to release file lock for {args.path}: {exc}", file=sys.stderr)
        state.close()


if __name__ == "__main__":
    raise SystemExit(main())
