# Cross-engine lifecycle matrix — verification artifact

This table records the lifecycle claim together with the source path and the
read-only command used to verify it. It describes registration and writers; it
does not claim that a live engine session was launched.

| Engine | Start/end mechanism | Store or side effect | Evidence path | Evidence command |
|---|---|---|---|---|
| Kilo | SessionStart/SessionEnd hooks | `.kilo/state/sessions/*.json`, tool/token state; no SQLite session writer | `.kilo/hooks/hooks.json`, `.kilo/hooks/session/session-start.js`, `.kilo/hooks/session/session-end.js` | `rg -n "SessionStart|SessionEnd|logSessionStart|SESSION_LOG_DIR" .kilo/hooks/hooks.json .kilo/hooks/session` |
| Claude Code | `SessionStart`/`SessionEnd` settings hooks; `PreCompact` hook | `.solocode/sessions.db` via `session_persistence.py`; checkpoint in shared-state DB | `.claude/settings.json`, `.claude/hooks/session_start.py`, `.claude/hooks/session_end.py`, `.claude/hooks/pre_compact.py` | `rg -n "SessionStart|SessionEnd|PreCompact|session_persistence|SharedState" .claude/settings.json .claude/hooks` |
| Codex | Manual `start`/`end` adapter; no native hook | `.solocode/shared-state.db`, `session_log` | `tools/codex_session.py` | `rg -n "def start|def end|add_session_entry|SharedState" tools/codex_session.py` |
| OpenCode | No lifecycle hook found in repository | No lifecycle writer found | `.opencode/`, repository search | `rg -n "SessionStart|SessionEnd|session_start|session_end" .opencode tools .github` |
| Copilot | No lifecycle hook found in repository | No lifecycle writer found | `.copilot/`, repository search | `rg -n "SessionStart|SessionEnd|session_start|session_end" .copilot tools .github` |
| Gemini | No lifecycle hook found in repository; handoff protocol is file based | No lifecycle writer found | `.gemini/antigravity/handoff/README.md`, repository search | `rg -n "SessionStart|SessionEnd|session_start|session_end" .gemini tools .github` |

## Scope

The matrix verifies static registration and code paths. Live Kilo and Codex
session execution remains a separate integration exercise and is not implied by
the `[Verified]` labels in the acceptance report.
