# Codex Write Path Analysis and Verification Report

**Slug:** codex-write-path  
**Date:** 2026-09-25  
**Author:** Antigravity (Gemini 3.8 Flash)  
**Status:** Completed  

---

## 1. Root Cause & Exact Blocking Layer

### Analysis & Reverse-Engineering Findings
The error `exec_command failed: CreateProcess { message: "Rejected(\"...\" rejected: blocked by policy)" }` is **not** produced by Solo-Code harness hooks, Windows OS security, or PowerShell execution restrictions. 

It originates directly inside the **Codex CLI binary** (`@openai/codex` v0.157.0, specifically Rust module `core\src\exec_policy.rs`):

1. **Internal Heuristic AST Matching:**
   Before spawning processes via `exec_command`, Codex CLI parses shell commands against built-in execution policy rules. One rule explicitly matches destructive removal patterns:
   `rm -f style commands are not permitted. Use a safer approach`
   This heuristic flags destructive commands like `rm -f`, `rm -rf`, and PowerShell `Remove-Item ... -Force`.

2. **Approval Policy Trigger:**
   When a command trips an execution policy heuristic, Codex CLI marks the command as requiring user approval (`AskForApproval`).

3. **Behavior under `approval_policy = "never"`:**
   In `~/.codex/config.toml`, `approval_policy` is configured as `"never"` (required for non-interactive / headless execution so CLI commands do not stall on interactive prompts). When a command requires approval while `approval_policy = "never"`, Codex immediately rejects process creation with:
   `CreateProcess { message: "Rejected(\"`<command>`\" rejected: blocked by policy)" }`

4. **False Correlation with `Set-Content`:**
   Earlier test runs evaluated a compound command:
   `Set-Content -LiteralPath ...; Get-Content ...; Remove-Item -LiteralPath ... -Force`
   The trailing `-Force` triggered the `rm -f` heuristic in `exec_policy.rs`, causing the entire compound command to be aborted before process start.
   Empirical testing isolated each component:
   - `Set-Content -LiteralPath '.codex_test_write.tmp' ...` **succeeded in 58ms**.
   - `Remove-Item -LiteralPath '.codex_test_write.tmp'` (without `-Force`) **succeeded in 40ms**.
   - `Remove-Item -LiteralPath '.codex_test_write.tmp' -Force` **failed with blocked by policy**.

---

## 2. Files Changed & Rationale

| File | Changes Made | Rationale |
|---|---|---|
| `tools/codex_guard.py` | Added `--write` flag and safe file writing logic with directory creation | Provides an explicit, harness-verified file writing path for Codex. Validates secrets via `find_secret`, acquires locks via `SharedState`, and writes to `--path`. Fully backward-compatible with preflight `--command` and `--content`. |
| `tools/test_codex_guard.py` | Added 3 unit tests: `test_write_benign_content_creates_file`, `test_write_secret_in_content_is_blocked`, `test_write_without_path_is_rejected` | Pins verified write behavior: successful creation of target files, fail-closed blocking of credentials, and argument validation. All 14 tests pass. |
| `.codex/README.md` | Documented native write paths (`apply_patch`), verified harness write guard (`codex_guard.py --write`), and execution policy rule constraints (avoiding `-Force` / `rm -f`) | Ensures future agents and developers know how to write files cleanly without tripping internal CLI policy rejections. |

---

## 3. Global Configuration & Deployment Setup

To deploy Codex CLI on a fresh machine or environment for the Solo-Code harness:

1. **Install Codex CLI globally:**
   ```powershell
   npm install -g @openai/codex
   ```

2. **Configure `~/.codex/config.toml`:**
   ```toml
   model = "gpt-6-sol"
   model_provider = "freemodel"
   model_reasoning_effort = "medium"
   sandbox_mode = "danger-full-access"
   approval_policy = "never"

   [model_providers.freemodel]
   name = "FreeModel"
   base_url = "https://api.freemodel.dev/v1"
   env_key = "OPENAI_API_KEY"
   wire_api = "responses"

   [features]
   code_mode.enabled = false
   unified_exec = false
   ```
   *Rationale:*
   - `sandbox_mode = "danger-full-access"` allows local repository development matching Claude Code and Kilo trust models.
   - `approval_policy = "never"` allows non-interactive headless operation.
   - `code_mode.enabled = false` and `unified_exec = false` ensure models emit standard tool calls (`apply_patch`, `exec_command`) rather than unparsed JavaScript code blocks.

3. **Provide API Key in `.env`:**
   Set `OPENAI_API_KEY` and optional `OPENAI_BASE_URL` in `.env`. Launch Codex through `.\codex-env.ps1`.

---

## 4. Verification Evidence

All verification claims have been tested with actual command runs:

| Claim | Command run | Output |
|---|---|---|
| Benign file creation via Codex `exec_command` PowerShell succeeds | `python run_codex_test.py "Create a file named .codex_test_write.tmp containing the text 'hello from codex file write'."` | `exec powershell.exe -Command "Set-Content -LiteralPath '.codex_test_write.tmp' ..."` **succeeded in 58ms**, RC: 0 |
| Destructive `-Force` command is rejected by Codex CLI `exec_policy.rs` | `python run_codex_test.py "Run this exact command using powershell: Remove-Item -LiteralPath '.codex_test_write.tmp' -Force"` | `ERROR codex_core::tools::router: exec_command failed: CreateProcess ... Rejected(\"... -Force\" rejected: blocked by policy)` |
| Non-destructive removal succeeds in Codex CLI | `python run_codex_test.py "Run this exact command using powershell: Remove-Item -LiteralPath '.codex_test_write.tmp'"` | `exec powershell.exe -Command "Remove-Item -LiteralPath '.codex_test_write.tmp'"` **succeeded in 40ms**, RC: 0 |
| Verified file write through `tools/codex_guard.py` succeeds | `python tools/codex_guard.py --path .codex_guard_test.tmp --content "test content" --write` | `WROTE: .codex_guard_test.tmp` (Exit: 0, file verified) |
| Codex CLI can write files via verified harness write guard | `python run_codex_test.py "Use powershell to run: python tools/codex_guard.py --path .codex_via_guard.tmp --content 'hello via guard' --write"` | `exec powershell.exe -Command "python tools/codex_guard.py ..."` **succeeded in 165ms**, output: `WROTE: .codex_via_guard.tmp` |
| Secret scanning blocks credential-like content on write | `python tools/codex_guard.py --path .codex_guard_secret.tmp --content "api_key = \"sk-ant-api03-dummy\"" --write` | `BLOCKED: possible secret in content` (Exit: 2, file not created) |
| Codex guard unit tests pass (14/14) | `python -m pytest tools/test_codex_guard.py -v` | `14 passed in 2.11s` |
| Security scan clean across repo | `python .github/scripts/security_scan.py .` | `Files scanned: 2515. No issues found.` |
| Full Codex verification gates pass | `python tools/codex_verify.py` | `562 passed, 3 skipped in 56.33s. All Codex verification gates passed.` |

---

## 5. Remaining Limitations & Orchestrator Decisions

1. **Absence of Native Project Pre-Tool Hooks in Codex CLI:**
   Unlike Claude Code (`PreToolUse`) and Kilo Code (`pre-tool-use/`), Codex CLI v0.157.0 does not provide extensible project-level pre-tool hooks. Therefore, gate enforcement relies on:
   - Calling `python tools/codex_guard.py --write` for verified writes.
   - Post-run verification via `python tools/codex_verify.py` (which runs secret scanning, schema validation, garden drift detection, and full pytest test suite).
2. **Stdin handling in non-interactive pipeline contexts:**
   When calling `codex exec` in automated wrappers where standard input is an unclosed pipe, Codex CLI attempts to consume stdin until EOF before processing the prompt. Automated callers should pass `stdin=subprocess.DEVNULL` (in Python) or ensure stdin is explicitly redirected.
3. **Plan File State:**
   In compliance with task instructions, `.gemini/antigravity/handoff/inbox/codex-write-path-plan.md` has been left unchanged with `status: pending`.
