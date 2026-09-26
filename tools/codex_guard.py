#!/usr/bin/env python3
"""Preflight guard for commands and files invoked by Codex CLI.

Codex cannot install repository hooks, so this is an explicit fail-closed
check used by wrappers and can also be called before risky shell operations.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.claude_guard_compat import find_destructive, find_secret  # noqa: E402
from tools.shared_state import SharedState  # noqa: E402


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
    with SharedState() as state:
        if args.path and not state.acquire_lock(args.path, engine="codex", model="codex-cli"):
            print(f"BLOCKED: file lock held by another engine: {args.path}", file=sys.stderr)
            return 2
    if args.write:
        target = Path(args.path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(args.content, encoding="utf-8")
        print(f"WROTE: {args.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
