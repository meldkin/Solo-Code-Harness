---
slug: full-project-audit-2026-10-03
created: 2026-10-03
from: claude
status: pending
---

# Task

Perform a broad, evidence-based audit of the entire Solo-Code-CLI repository. Fix clearly scoped, low-risk defects in project code and tests, then report all findings, changes, and verification evidence. The user authorized fixes and expects Claude Code to independently review your work before accepting it.

## Context

- Read the root `AGENTS.md`, `.harness.lock`, and this repository's Gemini rulebook before auditing. Follow the harness boundary manifest: `.kilo/`, `.copilot/`, `.gemini/`, `.claude/`, `.opencode/`, `.agents/`, and `.contracts/` are harness configuration, not ordinary project source.
- Audit all applicable areas: architecture/module boundaries, security and secrets handling, Python/PowerShell reliability, tests and skipped checks, provider/launcher flows, deploy behavior, configuration drift, performance, and maintainability. Use repository-wide inventory/search plus targeted inspection; do not claim exhaustive review of files you did not inspect.
- The working tree already has user-approved changes in `claude-env.ps1` and `tools/test_approve_api_key.py`. **Do not edit, stage, revert, or reformat these two files.** They are actively locked by the coordinating Claude session. Treat them as existing changes and report only if an independently found issue directly concerns them.
- Do not expose or reproduce any secret values. If you find a credential in a tracked file or output, report only its path and type, avoid including the value, and stop before making unrelated changes.

## Write scope and safety fences

- You may edit only clearly scoped project source code and directly related tests. Before editing a shared path, check `.solocode/shared-state.db` for an active lock using the repository's `tools/shared_state.py` API/CLI. Stop and report any conflict.
- Do NOT edit this plan file. Leave `status: pending` unchanged.
- Write your report only to `.gemini/antigravity/handoff/outbox/full-project-audit-2026-10-03-report.md`.
- Do NOT edit any harness engine directories or generated harness artifacts: `.kilo/`, `.copilot/`, `.gemini/`, `.claude/`, `.opencode/`, `.agents/`, `.contracts/`, `AGENTS.md`, `CLAUDE.md`, or `.harness.lock`. The only permitted `.gemini/` write is the report path above.
- Do NOT modify `.github/workflows/` or any CI/CD pipeline configuration.
- Do NOT delete files, install dependencies, change public APIs, rotate credentials, commit, push, or use destructive Git commands.
- Do not make broad style-only refactors. For findings needing architecture, product, security-policy, public API, dependency, or harness decisions, report options and trade-offs without implementing them.
- Preserve unrelated working-tree changes. Do not treat existing dirty files as yours.

## Workflow

1. Inspect `git status --short` and `git diff` first; record pre-existing changes without modifying them.
2. Map the repository and its tests/configuration. Inspect findings at their source before classifying them; distinguish verified defects from hypotheses and false positives.
3. List at least two relevant failure modes or boundary cases before testing each code change (for example: missing env var, wrong current directory, malformed config, empty input, Windows path behavior).
4. Implement only low-risk, well-supported fixes with focused regression tests. If the issue is ambiguous or broad, leave it for Claude review.
5. Run targeted tests, then the applicable project gates. At minimum attempt:
   - `python .github/scripts/security_scan.py .`
   - `python .github/scripts/checklist.py .`
   - `python .github/scripts/check_skips.py tools/`
   - `python tools/garden.py`
   Report failures as observed; do not weaken or bypass checks to make them pass. Do not run a deployment.
6. Review your own diff. Do not commit or stage changes.

## Expected report format

Write the report at the exact outbox path above with frontmatter (`slug`, `completed`, `from: gemini`). Include:

1. Executive summary and audit scope, with inspected directories/file groups and any exclusions.
2. Findings table: `| Severity | File/line | Finding | Status | Evidence |`.
3. Changes table: `| File | Defect fixed | Test added/updated |`.
4. Verification evidence table: `| Claim | Command run | Output (trimmed) |`, including exact commands and meaningful output for every test/gate run. **Do not state a claim without a command and output.** Clearly distinguish not-run from passed.
5. Remaining `needs-review`, `accepted-risk`, and `false-positive` items, with rationale and trade-offs.
6. Final `git status --short` and `git diff --stat` output. Confirm no commit/stage occurred and that the two protected files were left untouched.

Never include API keys, tokens, passwords, or their fingerprints in the report.
