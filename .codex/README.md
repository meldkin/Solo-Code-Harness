# Codex CLI integration

Codex loads the root `AGENTS.md` automatically. This directory documents the
project-specific entrypoints that replace engine lifecycle hooks:

```powershell
python tools/codex_session.py start --session-id <id>
python tools/codex_verify.py
python tools/codex_session.py end --session-id <id> --summary "..."
```

Use `codex-env.ps1` from the repository root so credentials remain in `.env`.
The launcher runs the session start/end adapter for `codex` and `codex exec`.

## Write Paths and Harness Security Gates

Codex CLI provides two native file modification mechanisms and a verified harness write path:

1. **Native `apply_patch` tool**:
   Emits unified diffs to update or create files. Does not invoke shell execution policies.

2. **Verified Harness Write Guard**:
   ```powershell
   python tools/codex_guard.py --path <target-path> --content <content> --write
   ```
   Ensures fail-closed secret scanning (`find_secret`), acquires file locks in `SharedState`,
   and writes the content to disk. If secrets are detected or the lock cannot be acquired,
   it exits 2 and aborts without writing.

3. **Shell Execution & Policy Rules**:
   - Benign PowerShell file writes (e.g. `Set-Content -LiteralPath ...`) run cleanly.
   - **Important**: Avoid destructive flags like `-Force` or `rm -f` in compound shell commands.
     Codex CLI contains built-in execution policy rules (`core\src\exec_policy.rs`) that block
     destructive `rm -f` / `-Force` patterns. When `approval_policy = "never"` is configured,
     matching commands are rejected before process launch (`CreateProcess ... rejected: blocked by policy`).
   - Non-destructive removals (`Remove-Item -LiteralPath ...` without `-Force`) succeed normally.

