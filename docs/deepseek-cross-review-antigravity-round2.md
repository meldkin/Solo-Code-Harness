# DeepSeek cross-review: Antigravity headless worker — round 2

Do not edit files. Review the current uncommitted working tree for correctness,
security, scope isolation, concurrency, deployment, and Windows behavior.
Report only findings supported by a command or concrete code path. For each
finding give severity, exact file/line, reproducer, impact, and minimal fix.
Do not repeat a closed finding without a new reproducer.

## Current policy and fixes from round one

- Read-only is the default.
- Writes require both `--auto-approve` and `--allow-dir <directory>`.
- `--auto-approve` sends `--dangerously-skip-permissions` to `agy.exe`.
- `--no-guardrail` is rejected with `--auto-approve`.
- `--allow-dir .` is rejected; callers must select a narrower directory.
- Directory locks conflict with file locks and nested directory locks.
- Root directory locks conflict with every workspace path.
- Lock conflicts include a different `session_id` even when the engine name is
  the same. Same-session re-entry remains allowed.
- A successful stream must contain a `result` event.
- Scope checks run before returning worker errors and preserve timeout exit `124`.
- Snapshot ignores `.venv`, `venv`, `node_modules`, caches, build/dist, and
  `.pytest_temp*` in addition to `.git` and `.solocode`.
- OpenCode permission for the wrapper is `ask`, not `allow`.
- `.solocode` is classified as local runtime state by `security_scan.py`.
- GUI inbox/outbox remains a fallback for rendered UI verification.

## Files to inspect

| File | Focus |
|---|---|
| `tools/antigravity_delegate.py` | validation, parser, subprocess, snapshot, scope check, exit codes, lock ownership |
| `tools/shared_state.py` | normalization and file/directory/session conflict semantics |
| `tools/test_antigravity_delegate.py` | boundary/error-path coverage |
| `tools/test_shared_state.py` | root/nested/same-engine lock coverage |
| `tools/opencode_engine.py`, `opencode.json` | generated permission parity (`ask`) |
| `tools/deploy.py`, `.harness.lock` | deployment boundary |
| `.github/scripts/security_scan.py` | `.solocode` runtime-state policy |
| generated Claude/Copilot/Gemini mirrors | stale routing/frontmatter |

## Required second-round checks

1. Verify `_lock_paths_conflict("dir:.", "src/auth.py")` and nested variants,
   including `.` normalization and Windows slash/case behavior.
2. Verify same-engine re-entry with empty versus non-empty `session_id`. Is an
   empty session ID accidentally shared by unrelated callers?
3. Verify a worker with an old session cannot release a newer lock for the same
   engine/path.
4. Verify `main()` returns `4` when a failed/timeout worker changes an outside
   path, and returns `124` for a timeout without scope violation.
5. Verify `init` without `result` is an error even when process exit code is 0.
6. Verify ignored-directory pruning does not hide a changed file inside the
   declared `--allow-dir` and does not create false scope failures.
7. Test symlink/junction behavior explicitly. State whether the current design
   is only an audit check or a security boundary; do not call it a sandbox.
8. Confirm generated OpenCode config retains the `ask` rule and deploy includes
   the wrapper but not test-only files.
9. Confirm skipping `.solocode` in `security_scan.py` is justified by the
   harness boundary and backed by an appropriate test or existing invariant.

## Verified gates after round-one fixes

```text
python -m pytest tools/ -q --basetemp .pytest_temp_review_final
538 passed, 3 skipped in 63.01s

ruff check .
All checks passed

python .github/scripts/security_scan.py .
No issues found

python .github/scripts/checklist.py .
All checks PASSED
```

## Residual risks to assess explicitly

- `--dangerously-skip-permissions` is not an OS sandbox.
- A symlink/junction inside the allowed directory may point outside the
  workspace; post-run hashing can classify the link path as in-scope.
- Snapshot hashing is an audit mechanism, not prevention against writes outside
  `--target-dir`, Git metadata changes, or process races.
- The working tree also contains pre-existing edits in `opencode-env.ps1`,
  `tools/opencode_delegate.py`, and `tools/test_opencode_delegate.py`; do not
  attribute them to this integration without checking history.

## Required response format

1. Closed findings from round one (F1–F11), each with command/evidence.
2. New findings with severity, exact location, reproducer, impact, and fix.
3. Residual risks, separating audit limitations from security boundaries.
4. Gate status with commands actually run and their outputs.
