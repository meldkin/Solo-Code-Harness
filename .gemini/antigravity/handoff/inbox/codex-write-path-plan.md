---
slug: codex-write-path
created: 2026-09-25
from: claude
status: pending
---

# Task

Make Codex usable as a first-class Solo-Code harness engine for real project
work: it must be able to read, create, and edit files through an approved
write path, while preserving the harness security gates. The fix must be
portable for future deployments and must not be limited to this repository.

## Context

The current session can run read-only PowerShell commands, but
`functions.exec -> exec_command` rejects simple `Set-Content` commands before
PowerShell starts with `CreateProcess ... rejected: blocked by policy`.
The repository contains Codex integration files:

- `tools/codex_guard.py`
- `tools/test_codex_guard.py`
- `tools/codex_session.py`
- `tools/codex_verify.py`
- `codex-env.ps1`
- `.codex/README.md`
- root `AGENTS.md`

Inspect the actual Codex CLI configuration and execution policy available on
this machine, including user-level Codex config and launcher/tool policy. Do
not assume the repository guard is the layer that rejected the command.
Determine whether the supported fix is a Codex tool/config change, a harness
launcher change, or both. Preserve fail-closed secret scanning, file locking,
destructive-operation confirmation, and deployment portability.

## Explicit write scope

You may edit only the files required for the Codex write-path fix and its
tests/documentation. Do not modify CI workflows, security rules, unrelated
project code, or this plan file. Do not install dependencies. If the required
change is outside this repository (for example a global Codex/tool policy),
do not edit it silently; report the exact path and configuration change needed.

## Required verification

Run commands for every claim. Include the command and relevant output in the
report. At minimum verify:

1. A benign Codex file create/edit path succeeds.
2. Secret scanning still blocks credential-like content.
3. Destructive commands remain blocked or require the existing confirmation
   flow.
4. Existing Codex guard tests and relevant harness checks pass.
5. The proposed setup can be reproduced on a fresh deployment.

## Expected report format

Write the report to
`.gemini/antigravity/handoff/outbox/codex-write-path-report.md` with:

- root cause and exact blocking layer;
- files changed, with a short reason for each;
- deployment/setup steps if a global configuration is required;
- a table `Claim | Command run | Output`;
- remaining limitations or decisions that require the orchestrator.

Leave this plan file unchanged with `status: pending`.
