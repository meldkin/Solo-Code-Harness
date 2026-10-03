---
slug: followup-fixes-2026-10-03
created: 2026-10-03
from: claude
status: pending
---

# Task

Apply only the four follow-up fixes approved after the full repository audit, then report exact evidence. The approved scope is: reduce loaded memory below the hard cap while preserving old decisions in an archive and synchronizing Claude/Copilot mirrors; make benchmark setup portable on Windows; add proper `--help`/`-h` handling to the lint-budget CLI; and correct the stale gitleaks allowlist path.

## Context

- Read `AGENTS.md`, `.harness.lock`, `.gemini/antigravity/AGENTS.md`, and the previous report at `.gemini/antigravity/handoff/outbox/full-project-audit-2026-10-03-report.md` before editing.
- Current full pytest is red only because `.kilo/memory/MEMORY.md` is 9,042 characters while the hard cap is 8,000. The source of truth is `.kilo/memory/`; Claude and Copilot mirrors must remain synchronized.
- Existing uncommitted changes are present in `claude-env.ps1`, `tools/coverage_gate.py`, and `tools/test_approve_api_key.py`, plus the previous handoff artifacts and `tools/test_coverage_gate.py`. Preserve all of them. The first and third files are actively locked by Claude Code.
- Do not reproduce API keys, tokens, passwords, or fingerprints in code, command output, or the report.

## Exact approved write scope

You may write only these paths:

- `.kilo/memory/MEMORY.md`
- `.kilo/memory/decisions-archive.md` (create or append; never delete existing content)
- `.claude/memory/MEMORY.md`
- `.copilot/memory/MEMORY.md`
- `tools/benchmark_executors.py`
- `tools/test_benchmark_executors.py` only if an existing focused test module is absent and a regression test is needed
- `tools/check_lint_budget.py`
- `tools/test_check_lint_budget.py`
- `.gitleaks.toml`
- `.gemini/antigravity/handoff/outbox/followup-fixes-2026-10-03-report.md`

Before writing any shared path, inspect `.solocode/shared-state.db` with `tools/shared_state.py` and stop on a conflicting active lock. Do not edit the plan file; leave `status: pending` unchanged.

## Fences

- Do NOT edit, stage, revert, reformat, or regenerate `claude-env.ps1` or `tools/test_approve_api_key.py`.
- Do NOT edit `tools/coverage_gate.py`, `tools/test_coverage_gate.py`, the previous inbox/outbox handoff, or any path not listed in the approved write scope.
- Do NOT edit any harness engine rules, generated artifacts, `.harness.lock`, `AGENTS.md`, `CLAUDE.md`, `.github/workflows/`, or CI configuration.
- Do NOT delete files, install dependencies, rotate credentials, commit, push, or use destructive Git commands.
- Do not fix or refactor findings outside the four approved items. Report newly discovered issues as `needs-review` only.
- Preserve archive content verbatim if the archive already exists. Move only clearly old/low-signal entries from loaded `MEMORY.md`; do not silently discard decisions. Keep the resulting source and mirrors below 8,000 characters and synchronized using the project's documented generation process.

## Required fixes

### 1. Memory cap and parity

Move enough old, low-signal decision material from `.kilo/memory/MEMORY.md` to `.kilo/memory/decisions-archive.md` to get the loaded source below 8,000 characters. Preserve the moved text. Then synchronize `.claude/memory/MEMORY.md` and `.copilot/memory/MEMORY.md` according to the repository's established source-of-truth workflow. Verify byte/text parity and the hard cap for all three copies. Do not archive current rules, gotchas, or active decisions merely to meet the number.

### 2. Windows-safe benchmark setup

Replace the POSIX heredoc setup strings used by `refactor_code` and `add_test` in `tools/benchmark_executors.py` with the smallest compatible structured setup representation and execution path. Preserve existing task behavior and avoid shell interpolation. Add or update focused tests only if needed to prove setup works on Windows and does not pass redirection tokens as arguments. Do not run paid model benchmarks.

### 3. Lint-budget help

Make `python tools/check_lint_budget.py --help` and `-h` print the module usage text and return 0 without running Ruff. Preserve `--list` and default enforcement behavior. Add focused tests for both help forms, including a guard that the expensive linter path is not called.

### 4. Gitleaks allowlist path

Update only the stale `tools/eval_harness.py` allowlist entry to match the current `.github/scripts/eval_harness.py` location. Verify the resulting TOML and security scan. Do not broaden the allowlist or add unrelated exclusions.

## Verification requirements

Before reporting completion, run the focused tests and all applicable gates:

- `python -m pytest tools/test_check_lint_budget.py -q`
- focused benchmark tests, if present
- `python -m pytest tools/test_claude_hooks.py tools/test_generate_harness.py -q`
- `python .github/scripts/security_scan.py .`
- `python .github/scripts/check_skips.py tools/`
- `python tools/garden.py`
- `python .github/scripts/checklist.py .`
- `python -m pytest -q`

If a gate fails, report the exact failure and do not hide it by weakening tests or checks. Review `git diff --check`, `git diff --stat`, and `git status --short` at the end. Do not stage or commit.

## Expected report format

Write only `.gemini/antigravity/handoff/outbox/followup-fixes-2026-10-03-report.md` with frontmatter (`slug`, `completed`, `from: gemini`). Include:

1. Scope and protected paths.
2. Findings/fixes table: `| Severity | File/line | Finding | Status |`.
3. Memory archive and mirror-parity details, including character counts, without exposing secrets.
4. Verification table: `| Claim | Command run | Output (trimmed) |`. Every claim must have a command and observed output; do not use confidence statements.
5. Any approved item not fixed, with exact blocker.
6. Any newly discovered out-of-scope issues as `needs-review`, without changing them.
7. Final status/diff output and confirmation that no commit or stage occurred.
