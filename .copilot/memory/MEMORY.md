# Memory Index

High-signal context loaded at session start. Detailed history belongs in
`decisions-archive.md`; keep this file below the 8,000-character gate.

## Project
- [project] Branches: `feature/[task-slug]` or `fix/[bug-slug]`.
- [project] `AGENTS.md` is the root rulebook; `.harness.lock` defines boundaries.
- [project] `.kilo/` is source of truth. Claude and OpenCode are generated from
  it; Copilot/Gemini are parity-checked.

## Rules
- [rules] Read before editing; make surgical changes; verify syntax and tests.
- [rules] User input is untrusted. Parameterize SQL; keep credentials in env vars.
- [rules] Ask before destructive actions, dependency installs, CI changes, or
  deletion.
- [rules] Use `permission-guard`; executor mode is ON by default. Run the
  security scan before committing.

## Tech Stack
- [tech] Python 3.10+ stdlib runtime for `tools/` and `.github/scripts/`;
  pytest/ruff are dev tools. Kilo hooks use Node.js 18+.
- [tech] Ruff config: `.ruff.toml`; secrets: `.gitleaks.toml`.
- [tech] Codex CLI 0.154.0 (npm global) is a harness consumer: it reads
  `AGENTS.md` natively, so no `.codex/` engine mirror is generated. Launcher
  `codex-env.ps1`, metering `tools/codex_usage.py`.
- [tech] SQLite shared state: `.solocode/shared-state.db`. Only `session_log`
  actually has rows; `features` and `shared_memory_*` exist but are unused —
  git log plus this file cover task tracking and conventions. `codex` is a
  valid engine name in `tools/shared_state.py`.

## Verification
- [verify] Full Codex gate: `python tools/codex_verify.py`.
- [verify] Individual gates: security scan, schema validation, garden,
  no-skips, pytest.
- [verify] Codex has no repository hook API, so use `tools/codex_guard.py` for
  destructive-command, secret, and file-lock preflight checks, or run
  verified writes with `tools/codex_guard.py --write`.

## Gotchas
- [gotcha] Bare Codex does not load `.env`; always run via the launcher.
- [gotcha] Codex gateway needs `code_mode.enabled = false`,
  `unified_exec = false`, `wire_api = "responses"`, and a full-access sandbox.
- [gotcha] Codex base URLs do not interpolate `${VAR}`; the launcher passes a
  `-c model_providers.<id>.base_url=...` override instead.
- [gotcha] Codex CLI internal exec policy blocks `rm -f` / `-Force` patterns;
  under `approval_policy = "never"` this aborts process creation. Avoid `-Force`
  in PowerShell, or use `python tools/codex_guard.py --write`.
- [gotcha] TOML bare keys must precede the first table header.
- [gotcha] Keep loaded memory under 8,000 chars. MOVE pruned material into
  `decisions-archive.md` verbatim — never silently delete it.
- [gotcha] `.pytest_temp` cleanup can race on Windows; rerun pytest if needed.

## Decisions
- [decision] Antigravity headless `agy.exe` delegate **re-established** after
  the retirement rationale was disproven: the account lockouts were a
  Google-side update bug, not bot-traffic flags from `agy.exe`; the accounts
  were reopened and the CLI was never implicated (2026-10-06). Worker runs
  through `tools/antigravity_delegate.py` — read-only by default, writes need
  `--allow-dir` + `--auto-approve` with a shared-state directory lock and
  post-run scope audit. Model is chosen by task complexity via the distinct ids
  `gemini-3.8-flash-{low,medium,high}`. Quota rotation is manual: `agy.exe`
  uses the machine-level Antigravity Google account and has no per-run account
  flag; switch account with `/logout` then re-sign-in, check quota with `/usage`,
  and resume with `--conversation <id>` or `--continue-latest`. A Gemini API key
  (`modelProvider: "gemini"` + `GEMINI_API_KEY`) is the headless alternative.
  Auth/settings details and doc links are in `decisions-archive.md`.
- [decision] Antigravity headless permission behavior (measured 2026-10-06 on
  `agy.exe` 1.2.9): a plain read-only run cannot answer the `command` permission
  prompt, so `run_command` is auto-denied while `result.status` still says
  `SUCCESS` with `denied_actions` populated. The wrapper now inspects
  `denied_actions` and per-tool `ERROR` events and exits **5** (empty output
  exits **2**) instead of a silent success. New `--allow-tools` flag grants
  read/execute tool use without a write scope (no directory lock, no scope
  audit); it is mutually exclusive with `--auto-approve`, `--allow-dir`, and
  `--no-guardrail`. `view_file` works read-only with an absolute path;
  `grep_search`/`list_dir` usage was unreliable at the low model tier.
- [decision] Claude launchers default to full mode; `--bare` is explicit
  degraded mode.
- [decision] OpenCode avoids duplicate skill mirrors and uses Claude-compatible
  skills.
- [decision] Codex lifecycle and guard behavior is launcher-based, because Codex
  has no project hooks. Of the gateway's aliases only `gpt-5.6-terra` routes
  reproducibly; the rest are unstable or dead — measurements and traps are in
  `decisions-archive.md` (2026-09-14).
- [decision] Codex write path: verified that `Set-Content` is not blocked by
  Codex CLI; earlier failure was caused by compound commands ending in
  `Remove-Item -Force` triggering `exec_policy.rs` `rm -f` heuristic under
  `approval_policy = "never"`. Added verified write path to `tools/codex_guard.py`
  (`--write` flag with secret scanning and shared state file locking) alongside
  native `apply_patch` (2026-09-25).
- [decision] CommandCode model ids are verified against
  `GET {COMMANDCODE_BASE_URL}/models`, never from memory: the catalog drifts and
  the old `api-providers.md` advertised nine ids that no longer resolve. Each
  CommandCode consumer declares models separately, so a new model needs one entry
  in `tools/opencode_engine.py` `_PROVIDER_MODELS` (OpenCode), `.vscode/settings.json`
  (Copilot), and `~/.config/kilo/kilo.jsonc` (Kilo). Kilo refs use the full
  upstream id (`commandcode/deepseek/deepseek-v4-pro`) while OpenCode refs use the
  harness key (`commandcode/deepseek-v4-pro`) — both correct for their dialect.
  `context_length` comes from the `/models` response, not the file. (2026-09-28)
- [decision] The OpenCode `freemodel` provider was broken on three independent
  layers, each measured 2026-10-03 by experiment:
  1. `settings.baseURL` was `${OPENAI_BASE_URL}`, but `opencode-env.ps1` strips
     `/v1` from that var, so the provider POSTed to `.../chat/completions` and
     got `Error: not found`. The generator now emits `${OPENAI_BASE_URL}/v1`.
  2. Auth used `env: ["OPENAI_API_KEY"]`, which the built-in OpenAI provider also
     claims, and a FreeModel credential in OpenCode's own store overrides the
     provider env var: a stale stored key shadowed `.env` and returned
     `Unauthorized - Invalid token` while the same `.env` key worked via curl.
     The provider now reads a dedicated `FREEMODEL_API_KEY`, and the launcher
     clears the stored credential each launch
     (`opencode auth logout freemodel "API key"`, idempotent — with nothing
     stored it just reports the `FREEMODEL_API_KEY` fallback and exits non-zero).
  3. `opencode-env.ps1` set `$ErrorActionPreference = "Stop"`, which turns a
     native command's stderr into a terminating error in Windows PowerShell 5.1:
     every `opencode-env.ps1 run ...` exited 1 with an empty `Write-Error`, for
     every provider. Lowered to `Continue` around the native call and success is
     read from `$LASTEXITCODE`.
  Debug technique worth reusing: `opencode run --standalone` bypasses the
  background server, and a local echo HTTP server reveals the exact request
  line, headers and `Authorization` header OpenCode sends.
  Model catalog: FreeModel's `/v1/models` is stale (lists dead `gpt-6-luna`,
  which answers 404, and omits `gpt-6.1-sol`). Declared models are `gpt-6-sol`,
  `gpt-6-astra`, `gpt-6.1-sol`; every other name routes to `gpt-6-sol`
  server-side, so extra aliases add no capability.

