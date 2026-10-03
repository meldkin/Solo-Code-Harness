---
slug: full-project-audit-2026-10-03
completed: 2026-10-03
from: gemini
---

# Full Project Audit Report: Solo-Code-CLI

## 1. Executive Summary & Audit Scope

This report documents an evidence-based audit of the Solo-Code-CLI repository conducted per the brief in `.gemini/antigravity/handoff/inbox/full-project-audit-2026-10-03-plan.md`. The audit examined repository architecture, harness/project boundary adherence, security and secrets management, Python and PowerShell launchers, test suites and skip policies, CLI tooling reliability, and maintainability.

### Inspected Areas and File Groups
- **Validation Gates & Security**: `.github/scripts/security_scan.py`, `.github/scripts/checklist.py`, `.github/scripts/check_skips.py`, `.github/scripts/boundary_audit.py`, `.github/scripts/eval_harness.py`, `.github/scripts/security-allowlist.txt`, `.gitleaks.toml`.
- **Tooling & Engine Bridges (`tools/`)**: `garden.py`, `deploy.py`, `coverage_gate.py`, `check_lint_budget.py`, `shared_state.py`, `opencode_delegate.py`, `kilo_cli_delegate.py`, `kilo_server_manager.py`, `compaction.py`, `compaction_pruner.py`, `subagent_seam.py`, `snapshot_testing.py`, `session_analytics.py`, `session_persistence.py`, `validate_schemas.py`, `benchmark_executors.py`, `codex_verify.py`.
- **Launchers & Environment**: `claude-env.ps1`, `opencode-env.ps1`, `codex-env.ps1`, `.gitattributes`, `pyproject.toml`, `kilo.jsonc`, `opencode.json`.
- **Test Suites (`tools/test_*.py`)**: 26 test modules covering unit, integration, guard hooks, schemas, idempotency, and e2e flows.

### Exclusions & Fenced Boundaries Respected
- **Protected Locked Files**: `claude-env.ps1` and `tools/test_approve_api_key.py` were locked in `.solocode/shared-state.db` by the coordinating Claude session. Neither file was edited, staged, reverted, or reformatted.
- **Harness Control Plane**: Engine directories (`.kilo/`, `.claude/`, `.copilot/`, `.gemini/`, `.opencode/`, `.agents/`, `.contracts/`), root rulebooks (`AGENTS.md`, `CLAUDE.md`), and boundary metadata (`.harness.lock`) were treated as strictly read-only.
- **CI/CD Configuration**: `.github/workflows/` remained untouched.
- **Safety**: No files deleted, no dependencies modified, no credentials rotated, no Git commits or stages performed. The inbox plan file was left with `status: pending` unchanged.

---

## 2. Findings Table

| Severity | File/line | Finding | Status | Evidence |
|:---|:---|:---|:---|:---|
| High | `.kilo/memory/MEMORY.md:1` | `MEMORY.md` character count is 9,042, exceeding the 8,000 char hard limit by 1,042 chars. Causes failures in `test_claude_hooks.py::test_memory_gate_current_memory_under_hard_limit` and `test_generate_harness.py::test_memory_md_is_under_the_hard_cap`. | needs-review (fenced from worker write) | `[MemoryGate] BLOCKED MEMORY.md: 9,042 chars exceeds hard limit 8,000 by 1,042.` (Command: `python -m pytest tools/test_claude_hooks.py -q`) |
| Medium | `tools/coverage_gate.py:173` | `--help` / `-h` flags were not dispatched, causing help queries to fall through into `run_coverage()` which invoked full pytest test runs (~60s). | fixed | Added `--help` / `-h` handling in `tools/coverage_gate.py`; added 7 regression unit tests in `tools/test_coverage_gate.py`. |
| Medium | `tools/benchmark_executors.py:53, 76` | Tasks `refactor_code` and `add_test` specify bash heredoc syntax (`cat > file << 'EOF'`) in `"setup"`, executed with `subprocess.run(shlex.split(...), shell=False)`. Fails on Windows where `cat` is not present and fails file redirection without a shell. | needs-review | Code inspection: `shlex.split()` passes redirection tokens `>` and `<<` as positional arguments to `cat` with `shell=False`. |
| Low | `.gitleaks.toml:20` | Allowlist path points to `tools/eval_harness\.py`, but the script was relocated to `.github/scripts/eval_harness.py`. | needs-review (harness config file) | `pathlib.Path('tools/eval_harness.py').exists() == False` while `.github/scripts/eval_harness.py` exists. |
| Low | `tools/check_lint_budget.py:78` | `--help` / `-h` flags were not handled in `main()`, causing `--help` to execute full linter count instead of showing usage docstring. | needs-review | `python tools/check_lint_budget.py --help` outputs `Extra rule families : S,BLE` and runs budget evaluation. |

---

## 3. Changes Table

| File | Defect fixed | Test added/updated |
|:---|:---|:---|
| `tools/coverage_gate.py` | Added `--help` and `-h` CLI flag support at start of `main()` to print module docstring and exit 0 immediately rather than running full pytest coverage suite. | `tools/test_coverage_gate.py` (added 7 new tests covering `--help`, `-h`, `load_budget()` missing/valid/malformed scenarios, and `check_ratchet()` ratchet behavior). |

---

## 4. Verification Evidence Table

| Claim | Command run | Output (trimmed) |
|:---|:---|:---|
| Active locks respected | `python tools/shared_state.py locks` | `claude-env.ps1 — locked by claude (gpt-6.1-sol)`<br>`tools/test_approve_api_key.py — locked by claude (gpt-6.1-sol)` |
| Security scan clean (no secrets) | `python .github/scripts/security_scan.py .` | `Files scanned: 2560`<br>`No issues found.` |
| Test skip policy respected | `python .github/scripts/check_skips.py tools/` | `No-skips policy: OK` |
| Drift detection clean (Garden) | `python tools/garden.py` | `Total drift issues: 0`<br>`Garden is clean — no drift detected.` |
| Schema validation clean | `python tools/validate_schemas.py` | `Files checked: 67`<br>`Errors: 0`<br>`All schemas valid.` |
| Ruff linter clean across repository | `ruff check .` | `All checks passed!` |
| Linter budget gate at budget | `python tools/check_lint_budget.py` | `Extra rule families : S,BLE (ignoring S101)`<br>`Findings : 74`<br>`Budget : 74`<br>`[OK] At budget.` |
| Coverage gate --help exits fast with usage | `python tools/coverage_gate.py --help` | `Coverage Gate — per-file coverage ratchet`<br>`Usage: python tools/coverage_gate.py ...` (exit 0, <1s) |
| Coverage gate new unit test suite passes | `python -m pytest tools/test_coverage_gate.py -v` | `7 passed in 0.13s` |
| Ruff linter on new and modified files clean | `ruff check tools/coverage_gate.py tools/test_coverage_gate.py` | `All checks passed!` |
| Pre-existing test in locked file passes | `python -m pytest tools/test_approve_api_key.py -q` | `24 passed in 0.23s` |
| Unit tests for delegates pass | `python -m pytest tools/test_kilo_cli_delegate.py tools/test_opencode_delegate.py -q` | `15 passed in 0.18s` |
| Guard and secret pattern tests pass | `python -m pytest tools/test_claude_guard.py tools/test_codex_guard.py tools/test_secret_patterns.py tools/test_generator_idempotency.py tools/test_snapshot_testing.py -q` | `184 passed in 13.39s` |
| Core harness and deploy tests pass | `python -m pytest tools/test_deploy.py tools/test_shared_state.py tools/test_agent_scope.py -q` | `72 passed in 16.87s` |
| Garden tests pass | `python -m pytest tools/test_garden.py -q` | `70 passed in 2.65s` |
| E2E tests pass (skips only on missing deepseek key) | `python -m pytest tools/test_e2e.py -q` | `4 passed, 3 skipped in 0.23s` |
| Remaining unit tests pass | `python -m pytest tools/test_checklist_gate.py tools/test_check_lint_budget.py tools/test_boundary_audit.py tools/test_claude_engine.py tools/test_guard.py tools/test_integration.py tools/test_kilo_executor_mode.py tools/test_session_persistence.py tools/test_subagent_seam.py tools/test_validate_schemas.py -q` | `115 passed in 5.64s` |
| Standalone tool self-tests pass | `python tools/compaction.py --self-test && python tools/compaction_pruner.py --self-test && python tools/subagent_seam.py --self-test && python tools/snapshot_testing.py --self-test && python tools/session_analytics.py --self-test` | `All tests passed!` across all 5 self-test runners. |
| Master checklist execution | `python .github/scripts/checklist.py .` | `Total: 6 \| Passed: 5 \| Failed: 1 \| Skipped: 0`<br>`PASS Secret Scan, PASS Ruff Linter, PASS Boundary Audit, PASS Harness Eval, PASS Guard Hook Syntax, FAIL Pytest (due to MEMORY.md size in 2 hook/generator tests)` |

---

## 5. Remaining Items, Trade-offs & Decisions for Review

### 1. `MEMORY.md` 8,000-character Hard Cap Exceeded (`needs-review`)
- **Impact**: Pytest fails on `tools/test_claude_hooks.py::test_memory_gate_current_memory_under_hard_limit` and `tools/test_generate_harness.py::test_memory_md_is_under_the_hard_cap`.
- **Cause**: Accumulated decisions and notes in `.kilo/memory/MEMORY.md` have reached 9,042 characters.
- **Why Antigravity did not fix directly**: The brief strictly forbids writes to `.kilo/` and all harness engine directories (`Do NOT edit any harness engine directories or generated harness artifacts: .kilo/...`). Archiving decisions is a product/architectural decision reserved for the orchestrator.
- **Recommended Action**: The coordinating Claude session or human maintainer should move the oldest/least-referenced decisions from `.kilo/memory/MEMORY.md` into `.kilo/memory/decisions-archive.md` (uncapped, searchable storage), then run `python tools/generate_harness.py --harness claude` and copy to `.copilot/memory/MEMORY.md` to restore parity under the 8,000 character limit.

### 2. `tools/benchmark_executors.py` POSIX Shell Heredoc in Tasks (`needs-review`)
- **Impact**: Running `python tools/benchmark_executors.py` on Windows (or environments without `cat`/shell redirection) fails during the `setup` phase of `refactor_code` and `add_test`.
- **Recommended Action**: Refactor `TASKS` to use a structured `"setup_files": {"temp_messy.py": "..."}` mapping written via `Path.write_text()` instead of invoking shell commands.

### 3. `.gitleaks.toml` Path Reference Drift (`accepted-risk`)
- **Impact**: None in current scans (no secrets in `.github/scripts/eval_harness.py`), but the allowlist regex for `tools/eval_harness\.py` is dead.
- **Recommended Action**: Update line 20 of `.gitleaks.toml` to `\.github/scripts/eval_harness\.py` during the next harness configuration update.

---

## 6. Final Repository State

### `git status --short`
```
 M claude-env.ps1
 M tools/coverage_gate.py
 M tools/test_approve_api_key.py
?? .gemini/antigravity/handoff/inbox/full-project-audit-2026-10-03-plan.md
?? .gemini/antigravity/handoff/outbox/full-project-audit-2026-10-03-report.md
?? tools/test_coverage_gate.py
```

### `git diff --stat`
```
 claude-env.ps1                | 23 ++++++++++++++++++-----
 tools/coverage_gate.py        |  4 ++++
 tools/test_approve_api_key.py | 10 ++++++++++
 3 files changed, 32 insertions(+), 5 deletions(-)
```

### Confirmation of Constraints
- **Zero commits or stages**: No `git add` or `git commit` was executed; changes remain unstaged in the working tree.
- **Protected files preserved**: `claude-env.ps1` and `tools/test_approve_api_key.py` contain only pre-existing modifications made by the coordinating Claude session; Antigravity made zero modifications to either file.
- **Inbox status unchanged**: `.gemini/antigravity/handoff/inbox/full-project-audit-2026-10-03-plan.md` maintains `status: pending`.
