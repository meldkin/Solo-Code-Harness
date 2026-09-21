# Cross-review brief: Antigravity headless worker

## Review request

Review the uncommitted Antigravity headless-worker integration for correctness,
security, scope isolation, concurrency, deployment, and Windows behavior. Do
not edit files. Report findings with severity, file and line, evidence, and a
minimal fix. Do not claim a finding without a command or code path that proves
it.

## Goal and policy

`agy.exe` is now a headless worker behind Codex/OpenCode/Claude orchestration.
The orchestrator must verify the diff and real quality gates afterward.

- Read-only is the default.
- A write requires both `--auto-approve` and `--allow-dir <directory>`.
- `--auto-approve` sends `--dangerously-skip-permissions` to `agy.exe`.
- `--no-guardrail` is rejected with `--auto-approve`.
- The wrapper locks the allowed directory in SQLite before the run, releases it
  in `finally`, then hashes the workspace before and after to detect changed
  paths outside the allowed directory.
- GUI inbox/outbox remains a fallback for rendered UI verification.

## Primary files to inspect

| File | Review focus |
|---|---|
| `tools/antigravity_delegate.py` | Argument validation, binary discovery, NDJSON parser, subprocess invocation, guardrail, workspace snapshot, scope check, lock release and exit codes. |
| `tools/shared_state.py` | File-vs-directory lock-key normalization and conflict semantics. |
| `tools/test_antigravity_delegate.py` | Missing boundary/error-path test coverage. |
| `tools/test_shared_state.py` | Directory-lock conflict coverage. |
| `AGENTS.md` | Worker-routing and verification policy. |
| `tools/claude_engine.py` and `.claude/hooks/session_start.py` | Generated Claude guidance and headless availability detection. |
| `tools/opencode_engine.py` and `opencode.json` | Generated allowlist parity. |
| `tools/deploy.py` and `.harness.lock` | Whether the new runtime wrapper is deployed and declared correctly. |

## Verified `agy.exe` contract

On this machine, `C:\Users\Giang_PC\AppData\Local\agy\bin\agy.exe` version
`1.1.27` works with:

```powershell
agy.exe --print "<prompt>" --output-format stream-json --add-dir <workspace> --model <model>
```

With opt-in write approval it additionally uses:

```text
--dangerously-skip-permissions
```

Observed NDJSON fields:

```json
{"event":"init","conversation_id":"...","init":{"model":"..."}}
{"event":"step_update","step_update":{"text_delta":"..."}}
{"event":"result","result":{"status":"SUCCESS","response":"...","usage":{}}}
```

## Expected behavior to challenge

1. Does `resolve_allowed_directory()` prevent absolute or relative escape from
   `--target-dir`, including Windows path edge cases and symlinks/junctions?
2. Can `snapshot_workspace()` be bypassed, made impractical, or produce false
   scope violations through generated files, links, race conditions, `.git`, or
   `.solocode` exclusions?
3. Is a post-run scope check sufficient, or is there an uncovered destructive
   action that needs a stronger pre-execution control?
4. Do `dir:` lock keys conflict correctly with file locks and nested directory
   locks across Windows slash variants? Is re-entry by the same engine safe?
5. Can lock release fail or remove another worker's lock? Check timeout and
   abnormal process exit paths.
6. Does the wrapper safely handle malformed NDJSON, missing `result`, nonzero
   exit codes with stdout, subprocess timeout, and Unicode/multiline prompts?
7. Is `--allow-dir .` acceptable as an explicit full-workspace grant, or should
   it be rejected? State the trade-off rather than assuming.
8. Does generated `opencode.json` retain the wrapper allowlist after
   `python tools/generate_harness.py --harness all`?
9. Does deploy copy the wrapper but avoid shipping test-only files as intended?
10. Are any generated/mirrored files edited in the wrong source location?

## Known environment facts

- The `googlecloudtools.datacloud_telemetry` Antigravity hook was disabled in
  the local user configuration because invalid quoting blocked every tool call.
  This is deliberately not a deployed harness setting. See
  `docs/antigravity-telemetry-hook.md`.
- The default pytest base directory `.pytest_temp` is currently locked on this
  Windows machine. Direct removal was blocked by local policy. The complete
  suite passed when run with a fresh project-local base temp:

```powershell
python -m pytest tools/ -q --basetemp .pytest_temp_verify_full
# 535 passed, 3 skipped
```

- Do not recommend removing `.pytest_temp` as a code fix. It is a local
  cleanup issue; pytest needs project-local temp storage here because system
  `%LOCALAPPDATA%\Temp\pytest-of-Giang_PC` denies access.

## Evidence already run

```text
python -m pytest tools/ -q --basetemp .pytest_temp_verify_full
535 passed, 3 skipped

python -m pytest tools/test_claude_hooks.py tools/test_claude_engine.py \
  tools/test_antigravity_delegate.py tools/test_shared_state.py -q
74 passed

ruff check .
All checks passed

python .github/scripts/security_scan.py .
No issues found

python .github/scripts/checklist.py .
All checks PASSED
```

## Scope warning

The working tree also contains pre-existing edits in `opencode-env.ps1`,
`tools/opencode_delegate.py`, and `tools/test_opencode_delegate.py`. Do not
attribute those changes to the Antigravity integration without checking the
diff and history.
