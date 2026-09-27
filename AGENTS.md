---
description: "Solo-Code AI Agent Harness — root rulebook for multi-engine (Kilo + Claude Code + Copilot + Gemini) development"
mode: primary
color: "#166534"
permissions:
    - action: read
      resource: "*"
      effect: allow
    - action: edit
      resource: "*"
      effect: allow
    - action: bash
      resource: "*"
      effect: allow
    - action: glob
      resource: "*"
      effect: allow
    - action: grep
      resource: "*"
      effect: allow
---

# Solo-Code — AI Agent Harness (Root Rulebook)

> **CRITICAL:** Read this file fully before taking any action. These rules are NON-NEGOTIABLE.

This file serves **Kilo** (reads `.kilo/` for hooks/skills/memory — source of truth), **Claude Code** (reads `.claude/` + `CLAUDE.md`, generated from `.kilo/`), **OpenCode** (reads `.opencode/` + `opencode.json`, generated from `.kilo/`; it also loads this file and the Claude-compatible `.claude/skills/` and `.agents/skills/` locations), and **GitHub Copilot** (reads `.copilot/` for agents/skills/commands, `.github/copilot-instructions.md` for rulebook). Sections referencing `.kilo/` paths are Kilo-specific; other engines ignore them and use their own generated/mirrored equivalents. (`.opencode/` was removed in v4.0.0, then reintroduced in v4.2.0 as a first-class primary engine — see `.harness.lock`.)

**OpenCode v2 + model provider (self-contained):** this repo targets OpenCode v2 (`@opencode/cli`, plugin SDK `@opencode/plugin`), not the retired v1 line (`opencode-ai` / `@opencode-ai/plugin`). `opencode.json` declares the `commandcode` provider itself under v2's `providers` key — an OpenAI-compatible endpoint at `{env:COMMANDCODE_BASE_URL}` (`https://api.commandcode.ai/provider/v1`) authenticated by `COMMANDCODE_API_KEY`, listing only the `commandcode/<id>` models the harness references (see `_PROVIDER_MODELS` in `tools/opencode_engine.py`). The v1 plugin `commandcode-go-opencode-provider` is no longer used. `opencode-env.ps1` exports the `.env` values and resolves the v2 `@opencode/cli` binary explicitly, because a stale v1 native binary can still sit on PATH. v2 loads only `AGENTS.md` (the `instructions` config array is accepted but not resolved), so `.kilo/instruction/*.md` is embedded into this file between markers by `tools/opencode_engine.py`.

## Harness Boundaries (READ FIRST)

> **DO NOT CONFUSE harness files with project source code.**

This project is powered by **Solo-Code Harness** — an AI agent discipline layer. When analyzing or modifying ANY file, first classify it:

| If the file path starts with... | Then it is... | Action |
|----------------------------------|---------------|--------|
| `.kilo/`, `.copilot/`, `.gemini/`, `.claude/`, `.claude-plugin/`, `.opencode/`, `.agents/`, `.codex/` | Harness engine | Rules/skills/hooks for AI behavior — not project logic |
| `.contracts/` | Harness sub-agent contracts | Status contracts for delegated agents |
| `.github/`, `.vscode/`, `tools/` | **Shared** — harness *and* project | The harness ships files here, but the project also keeps its own CI workflows, `CODEOWNERS`, dependabot config, editor settings and dev scripts. Only the exact paths under `[shared_files]` in `.harness.lock` are harness; **everything else here is project code**. |
| `AGENTS.md`, `agent.yaml`, `kilo.jsonc`, `opencode.json`, `.mcp.json`, `.ruff.toml`, `.gitleaks.toml`, `Makefile`, `claude-env.ps1`, `codex-env.ps1`, `opencode-env.ps1`, `init.sh`, `verify.sh`, `extensions_config.json`, `.harness.lock`, `.solocode/`, `.pre-commit-config.yaml`, `.github/pull_request_template.md`, `CLAUDE.md` | Harness config | Agent behavior configuration — not application config |
| **Everything else** | **Project code** | Your actual application — this is what you modify |

**Key rule:** Never modify harness files to fix a project bug. Never modify project files to fix a harness issue. Read `.harness.lock` for the authoritative boundary list.

## Self-Verification Handshake

When asked "Is Solo-Code Harness active?" or "What rules apply here?", answer:
`Solo-Code Harness active: behavior rules, anti-hallucination rules, security rules, prose quality rules, 52 skills, 14 agents, hooks enabled (Kilo) / guard + lifecycle hooks enabled (Claude Code). Use /verify to validate.`

## Escape Hatch (Meta-Principle)

> *"Break any of these rules sooner than say anything outright barbarous."*
> — George Orwell, "Politics and the English Language" (1946), Rule 6

Rules are guides to quality and safety, not ends in themselves. When a rule fights the task, use judgment — but document the exception.

---

## Fresh Information First (ANTI-STALENESS)

**Your training data is a snapshot. SDKs and APIs change after your cutoff.**

Before using ANY library you're not 100% certain about:
1. **Verify it exists** — Check `package.json`, `requirements.txt`, or existing imports
2. **Check for breaking changes** — API signatures change between major versions
3. **Mark uncertainty** — If unverified, tag `// VERIFY: <lib>.<symbol> against version X`
4. **Search docs first** — Use MCPs (context7) or `webfetch` to confirm current API before writing code

---

## Surgical Changes (TOUCH ONLY WHAT YOU MUST)

- **Don't "improve" adjacent code** — Your job is the requested change, not a style overhaul
- **Don't refactor things that aren't broken** — Refactoring is a separate task
- **Match existing style** — Consistency within a file beats your preference
- **Clean up only your own mess** — Remove only what YOUR changes made unused
- **Every changed line should trace to the user's request** — If you can't explain why a line changed, don't change it

---

## Request Classification (STEP 1 — BEFORE ANY TOOL)

| Type             | Trigger                                   | Action                                              |
| ---------------- | ----------------------------------------- | --------------------------------------------------- |
| **QUESTION**     | "what is", "explain", "how does"          | Text only. No tools unless reading files is essential. |
| **SIMPLE EDIT**  | Single-file fix, typo, small change       | Read → Edit → Verify                                |
| **COMPLEX TASK** | "build", "create", "refactor", multi-file | Plan → Get approval → Implement → Verify            |
| **DESTRUCTIVE**  | "delete", "rm", "drop", "force push"      | **STOP** → Ask explicit permission → Wait for "yes" |
| **REVIEW**       | "review", "audit", "check this PR"        | Load code-review-expert skill                       |

---

## Behavior Rules (MANDATORY)

### Safety

1. **BEFORE any destructive operation** (rm, delete, drop table, force push, format) → STOP. Ask explicit Yes/No. Do NOT proceed until user says "yes".
2. **BEFORE committing or pushing** → Scan the diff for secrets. Refuse to commit if secrets detected. Run `python .github/scripts/security_scan.py .` on the full diff.
3. **Never use destructive git commands** (`push --force`, `reset --hard`, or the `+` refspec like `git push origin +main`) unless user explicitly requests them. Never force-push to main/master.
4. **Do NOT use language runtimes (python, node, etc.) to bypass bash permission restrictions.** If you need to do something destructive, use the intended bash tool and go through the permission guard.

### Code Quality

5. **ALWAYS read a file before editing it.** Blind writes cause stale-read errors.
6. **Use exact string replacement** (Edit tool) over full-file rewrites. Smaller diffs = lower risk.
7. **Preserve existing patterns.** Before writing new code, analyze 3-5 nearby files to identify: naming conventions, indentation style, import ordering, error handling approach, paradigm (FP vs OOP), and test patterns. Match what you find. Never introduce new conventions. When the codebase is inconsistent, follow the most recently modified files.
8. **Never leave broken code.** After any edit, verify syntax. After any feature, run tests.

### AI Discipline (Anti-Hallucination)

These rules prevent AI from generating plausible-looking but incorrect code. Violation risks silent errors that compile but fail at runtime.

A-1. **Verify library existence before using it.** Check `package.json`, `requirements.txt`, `Cargo.toml`, or imports for the actual installed version. If you cannot verify, mark `// VERIFY: <lib>.<symbol> against version X` and flag the uncertainty.
A-2. **No invented function signatures, parameter names, or return types.** Never guess a library's API. If the library isn't in the project, propose installing it before writing code that depends on it. Silent stubs are worse than refusal.
A-3. **Compiling does not mean correct.** Confirm the code does what its name promises, not just what it returns. Before validating, list at least two failure modes: empty input, boundary values, or state assumptions.
A-4. **No restated-code comments.** Comments must explain WHY, not paraphrase WHAT the code does. A comment repeating the code is noise. Never write self-referential comments like "used by X flow" or "added for issue Y" — those belong in commit messages.
A-5. **Acknowledge uncertainty explicitly.** If you do not know something, say "I do not know" or "I need to verify X". Do not invent a plausible-sounding answer. When generating code with hidden trade-offs (new dependency, async pattern, data structure choice), name the trade-off in the response.
A-6. **Loop detection (DeerFlow threshold).** If the same tool is called 3+ times consecutively with the same parameters, change strategy immediately. At 5+ consecutive identical tool calls — stop, report the loop to the user, and wait for instruction. The `context-monitor.js` hook in `.kilo/hooks/post-tool-use/` enforces this automatically.

### Prose Quality (MANDATORY)

Inspired by *"The Elements of Agent Style"* (Zhao, 2026). These rules reduce AI-tell patterns in all technical prose output.

| # | Rule | Severity |
|---|------|----------|-------------|
| 9 | **Cut needless words** — never use "in order to" (→ "to"), "due to the fact that" (→ "because"), "at this point in time" (→ "now"), "it is important to note that" (→ delete), "may potentially" (→ "may"). | `high` |
| 10 | **Drop dying metaphors** — never use "pushes the boundaries", "paradigm shift", "state of the art", "cutting edge", "paves the way", "unlock the potential", "game changer". Replace with specific numbers or mechanisms. | `high` |
| 11 | **Use concrete terms** — replace "factors", "aspects", "considerations" with the specific items they refer to. "Performance issues" → "p95 latency rose from 120ms to 450ms". | `high` |
| 12 | **Prefer plain English** — "use" over "leverage"/"utilize"; "method" over "methodology"; "feature" over "functionality"; "because" over "due to the fact that". | `medium` |
| 13 | **No transition-word openers** — avoid "Additionally", "Furthermore", "Moreover", "In addition" at sentence start. | `medium` |
| 14 | **Varied sentence starts** — never open two consecutive sentences with the same word (especially "This", "It", "We", "The"). | `medium` |
| 15 | **Support claims with evidence** — never write "prior work shows" or "recent studies suggest" without naming the source. Never fabricate citations. Mark unverified claims `[UNVERIFIED]`. | `critical` |
| 16 | **Split long sentences** — split sentences over 30 words. Vary sentence length across paragraphs (mix short declarative with longer qualifying ones). | `high` |

#### BAD → GOOD Examples

- BAD: `This PR makes minor adjustments to fix an issue causing test failures.`
- GOOD: `Fixes a null-pointer crash in test_checkout_flow when the cart has a single item.`
- BAD: `We leverage state-of-the-art embedding models to unlock the retrieval pipeline's potential.`
- GOOD: `We use text-embedding-3-large, raising recall@10 by 7 points over ada-002.`

### Skills

Auto-loaded skills: `code-review-expert`, `file-editor-pro`, `git-workflow-master`, `permission-guard`, `systematic-debugging`, `brainstorming`, `testing-patterns`, `api-patterns`, `solo-code-harness`. Load via `kilo.json` instructions or context matching.

### Complex Tasks

17. **Socratic Gate:** For complex requests ("build X", "create Y", "refactor Z"), ask at least 2 clarifying questions before coding. Confirm approach, tradeoffs, and edge cases.
18. **Plan before implement:** Break complex tasks into steps. Present the plan. Wait for approval. Then execute.
19. **Synthesize, don't delegate blindly:** When spawning sub-agents (Task tool), read their findings and write specific implementation instructions with file paths and line numbers.

---

## Security Rules

See `.kilo/instruction/security-patterns.md` for full security rules — auto-loaded when editing auth, controllers, middleware, config, or `.env` files.

Key enforcement points:
- **ALL user input is untrusted** — validate type, length, format, and range
- **Use parameterized queries** for SQL — never string interpolation
- **Never hardcode credentials** — use environment variables
- **Passwords** must use bcrypt/scrypt/argon2 — never MD5/SHA1

---

## Session State Lifecycle (shared state)

Cross-engine session state lives in `.solocode/shared-state.db` (SQLite, local-only,
never committed). Engines read/write it via `tools/shared_state.py`'s `SharedState`
class. Claude Code hooks write to it automatically (`pre_compact.py` logs a
compaction checkpoint); engines without a lifecycle hook call `tools/shared_state.py`
directly (for example `tools/codex_session.py` for Codex).

**Feature/task tracking is NOT in SQLite.** The `features` and `shared_memory_*`
tables remain for backward compatibility but are unused: no hook or engine calls
`set_feature_status()`. Track tasks with `git log` and record conventions, gotchas
and decisions in `.kilo/memory/MEMORY.md`. `set_feature_status()` still exists as an
API but is not part of the current workflow.

### Startup

1. `session_start.py` injects a summary into context: git branch/sha/dirty count,
   recent sessions, any unseen Gemini/Antigravity handoff report, and a PreCompact
   recovery checkpoint (`.solocode/context-checkpoint.json`) if one was left.
2. Read `git log --oneline -10` and `.kilo/memory/MEMORY.md` to see what is in
   progress. Do not wait for an `in-progress` feature row — there is none.

### Wrap-Up (before ending session)

1. **Log the session**: `state.add_session_entry(engine=..., model=..., summary="...")`
   (newest entries are read first at next session start). `pre_compact.py` does this
   automatically on Claude Code; other engines call `tools/shared_state.py` directly
   if no lifecycle hook exists for that engine.
2. **Record settled decisions** in `.kilo/memory/MEMORY.md`'s `## Decisions` section
   (see the compaction section below).

### Context Compaction Continuity (CRITICAL — read this before/after any compaction)

Long sessions eventually get their context auto-summarized ("compacted"). A
compaction summary lives only in the current session's context — it is NOT
automatically written into the project's durable memory. **Any settled
architectural/scope decision must be appended to `.kilo/memory/MEMORY.md`'s
`## Decisions` section (source of truth) BEFORE it would only exist inside a
soon-to-be-compacted summary.** Do this proactively, not just when reminded:

1. Whenever a real decision is settled (not just "in progress" work) —
   architecture choice, engine/tool adoption, a fix that changes established
   behavior, a policy change — append a one-entry bullet to `.kilo/memory/MEMORY.md`
   `## Decisions` immediately, don't wait until end of session.
2. Regenerate/sync after: `python tools/generate_harness.py --harness claude`
   (updates `.claude/memory/`), then manually copy to `.copilot/memory/`
   (no auto-generator exists for Copilot; `.gemini/` has no comparable
   memory mirror — see `tools/garden.py`'s `check_gemini()`).
3. Claude Code has a `PreCompact` hook (`.claude/hooks/pre_compact.py`) that
   fires right before compaction: it logs an objective checkpoint (git
   branch/sha, trigger type, timestamp) to `.solocode/shared-state.db` and
   emits a reminder — but it CANNOT write your decision prose for you (a
   hook is a deterministic script, not the model). Treat its reminder as a
   prompt to check step 1, not a substitute for it.
4. Other engines without a compaction-specific hook should apply this rule
   manually: whenever a session naturally runs long, checkpoint decisions to
   `MEMORY.md` rather than relying on the engine's own summarization.

### Executor mode (write gate, default ON)

`.solocode/executor-mode` toggles whether the orchestrator (Claude Code or
Kilo Code) may call `Edit`/`Write`/`MultiEdit` directly. **Default is ON**:
absent or unreadable state file means the gate is active — fail closed, not
open, so a fresh clone or a deleted toggle cannot silently disable it. Bash
is never gated — the orchestrator still runs its own verification gates.

Enforced independently by each engine's own hook so neither can bypass it
by switching engines:

- Claude Code: `.claude/hooks/guard.py` (`PreToolUse`, matcher
  `Edit|Write|MultiEdit`).
- Kilo Code: `.kilo/hooks/pre-tool-use/executor-mode.js` (same matcher,
  wired into every `hooks.json` profile except `minimal`).

When ON, a write attempt is blocked (exit 2) with a reminder to verify the
result of any delegated work (`git status`/`git diff`) rather than trust a
worker's own report of what it wrote. `.gemini/antigravity/handoff/inbox/`
and `.solocode/executor-mode` itself are exempt — delegating a plan and
toggling the gate off must both stay possible from inside a gated session.

To disable: `echo off > .solocode/executor-mode`. Accepted off-values:
`off`, `0`, `disabled`, `false`, `no` (case-insensitive, trailing `#
comment` ignored). Any other value, including an empty file, keeps the
gate closed.

### Choosing a worker engine (routing table)

Three workers are available. Propose one **proactively** when the work fits —
the user should not have to remember they exist. `session_start.py` announces
each engine's availability at session start; treat that as a prompt to
consider delegation, not an instruction to always delegate.

| Work shape | Route to | Why |
|---|---|---|
| Read >5 files, then summarize/compare/audit | **Antigravity GUI handoff** | Large context through Gemini in Antigravity IDE |
| Repo-wide survey — "where else does X appear?" | **OpenCode CLI** | Headless survey with large context models |
| Independent review of a design or diff | **Antigravity GUI handoff** | A second model catches different things |
| UI verification, screenshots, recordings | **Antigravity GUI handoff** | Visual inspection in the rendered IDE UI |
| Small mechanical edit, boilerplate, one test | **OpenCode CLI** | Headless — costs the user nothing |
| Scoped code writing behind an explicit fence | **OpenCode CLI** | Requires explicit fence stated in writing |
| Architecture / product / security decisions | **Neither — do it here** | Judgment is not delegable |
| Anything needing this conversation's history | **Neither — do it here** | Workers are context-blind |

OpenCode CLI and Kilo CLI are headless executors. Antigravity GUI handoff provides
a manual relay protocol for UI verification, wide audits, or visual work via
`.gemini/antigravity/handoff/`.

**Verification is mandatory.** Every controlled test of worker engines
produced at least one error invisible in their own self-summary. Their
evidence is reliable; their self-assessment is not. Re-run their commands,
run the real gates, and mutation-test any new check they write.

Full decision guide: `.kilo/skill/gemini-delegation/SKILL.md`.

### Delegating to Antigravity GUI (manual fallback)

Use this path when GUI or visual verification is required. A human
must relay the task to the Antigravity IDE manually.
To minimize copy-paste, use the file-based handoff protocol instead of
pasting plan/result text through chat:

1. Write the plan to `.gemini/antigravity/handoff/inbox/<slug>-plan.md`
   (see `.gemini/antigravity/handoff/README.md` for the exact format).
2. Tell the user the one line to relay: *"Open Antigravity, tell Gemini to
   read `.gemini/antigravity/handoff/inbox/<slug>-plan.md` and write its
   report to `.gemini/antigravity/handoff/outbox/<slug>-report.md`."*
3. `.claude/hooks/session_start.py` auto-detects new `outbox/*-report.md`
   files at the next session start and announces them — no need to ask the
   user to paste the result back.

**Writing the brief** — four rules, each from an observed failure:

1. **Fence the scope, and predict the red gate.** If a correct result will
   make a check fail, say so explicitly ("that failure is the expected,
   correct outcome") — otherwise Gemini helpfully fixes what it was told
   only to detect.
2. **Demand evidence, not confidence.** A "Confident? Y/N" column came back
   22-for-22 "Yes", including on a wrong finding. Use `| Claim | Command run
   | Output |` and add: *"Do not write a claim you did not run a command for."*
3. **Name every writable path, including the brief itself.** The handoff
   README permits editing `status:`; a brief saying "touch nothing but the
   report" contradicts it. Say *"Do NOT edit this file. Leave `status:
   pending`."*
4. **Give the measurement, never the answer.** `ls .kilo/skill | wc -l`, not
   "there are 51". A brief that leaks the expected number cannot detect that
   the number changed.

**Before delegating a write**: take a `tools/shared_state.py` lock for the
files in scope — Gemini edits the same working tree concurrently, and
`acquire_lock()` returns `False` on a cross-engine conflict.

`agy.exe` headless execution has been retired to avoid automated traffic flags
on Google accounts. For Antigravity tasks, use the GUI handoff protocol above.

## Git Commit Convention

End commit message with: `Co-Authored-By: Solo-Code <admin@solo-code.com>`

See `.kilo/skill/git-workflow-master/SKILL.md` for full commit format, types, and style rules.

---

## Memory System

Persistent memory at `.kilo/memory/`. The AI reads `MEMORY.md` at session start. Use `/remember` to save conventions, gotchas, and preferences that should survive across sessions.

---

## Automation Scripts

| Script                             | Purpose                                           |
| ---------------------------------- | ------------------------------------------------- |
| `.github/scripts/checklist.py`     | Master validation: security → lint → test → build |
| `.github/scripts/security_scan.py` | Scan for hardcoded secrets and unsafe patterns    |

Run: `python .github/scripts/checklist.py .`

---

## Known Constraints

- **No runtime bypass**: Do not use `node`, `python` to bypass bash permission restrictions
- **Windows shell**: Commands run in PowerShell, not bash. Use `; if ($?) { }` not `&&`
- **Prefer specialized tools**: Use `Read`, `Edit`, `Glob`, `Grep` — never `Get-Content`, `Set-Content`, `Select-String`
- **Security scan required**: `python .github/scripts/security_scan.py .` must pass before any commit
- **No undocumented file creation**: Never create *.md documentation unless explicitly requested

---

## Not Allowed

These actions are prohibited regardless of permission mode:

- Modifying `.github/workflows/` or CI/CD pipeline configuration without explicit instruction
- Installing new npm/pip/cargo dependencies without explicit instruction
- Modifying `.kilo/hooks/hooks.json` hook configuration
- Editing `.kilo/instruction/security-patterns.md` security rules
- Deleting any file without explicit user approval
- Force-pushing to `main` or `master` branches
- Using `git commit --no-verify` or `git commit -n`

---

## Escalation

If the agent cannot proceed without a decision that falls outside its permitted scope:

1. **Stop** — do not make assumptions or guess.
2. **Describe the blocker** — what decision is needed, what options exist, what the trade-offs are.
3. **Wait for explicit instruction** — do not proceed until the user responds.

---

## Verification Gates

Before marking any task complete, verify:
- [ ] `python .github/scripts/security_scan.py .` passes
- [ ] `python .github/scripts/checklist.py .` passes
- [ ] `python .github/scripts/check_skips.py tools/` passes (0 unauthorized skips)
- [ ] No console.log/debug statements in production code
- [ ] Commit message follows project conventions

---

## Language

When user speaks Vietnamese → respond in Vietnamese. Code comments and variable names remain in English.

<!-- BEGIN opencode-v2-inline-instructions (generated from .kilo/instruction/*.md by tools/opencode_engine.py) -->

### api-providers.md

# API Providers — DeepSeek & CommandCode

> Auto-loaded when the agent needs to call external LLM APIs or switch between model providers.

## Overview

This project supports two external LLM API providers beyond the primary Copilot model:

| Provider | API Type | Base URL Env | Key Env |
|----------|----------|-------------|---------|
| **DeepSeek** | OpenAI-compatible | `DEEPSEEK_BASE_URL` | `DEEPSEEK_API_KEY` |
| **CommandCode** | OpenAI-compatible proxy | `COMMANDCODE_BASE_URL` | `COMMANDCODE_API_KEY` |

Both providers expose OpenAI-compatible `/v1/chat/completions` endpoints. CommandCode proxies multiple models (Claude, GPT, Gemini, DeepSeek, Qwen, Kimi, GLM, MiniMax, Step) through a single API key.

> CommandCode is the provider this repo actually configures (see `.env`). The DeepSeek direct endpoint is optional and is **not** set in this repo's `.env`.

> Model IDs drift. CommandCode adds and retires models without notice, so treat
> `GET {COMMANDCODE_BASE_URL}/models` as the source of truth and re-verify before
> using an ID this file does not list.

## Environment Configuration

Set these environment variables before use. Never hardcode keys in source files.

```powershell
# CommandCode (the provider this repo configures)
[Environment]::SetEnvironmentVariable("COMMANDCODE_BASE_URL", "https://api.commandcode.ai/provider/v1", "User")
[Environment]::SetEnvironmentVariable("COMMANDCODE_API_KEY", "cc-your-commandcode-key", "User")

# DeepSeek direct (optional — not configured in this repo)
[Environment]::SetEnvironmentVariable("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1", "User")
[Environment]::SetEnvironmentVariable("DEEPSEEK_API_KEY", "sk-your-deepseek-key", "User")
```

After setting, restart VS Code for Copilot to pick up the new variables.

## Model Selection

### Available Models via CommandCode

The ids below were verified against `GET {COMMANDCODE_BASE_URL}/models` on
2026-09-28. The catalog is larger (~80 models — Claude, GPT, Gemini, Qwen, Kimi,
GLM, MiniMax, Grok, MiMo, Step, …); enumerate it with:

```powershell
Invoke-RestMethod -Uri "$env:COMMANDCODE_BASE_URL/models" `
  -Headers @{ Authorization = "Bearer $env:COMMANDCODE_API_KEY" } |
  Select-Object -ExpandProperty data | Select-Object -ExpandProperty id | Sort-Object
```

| Model ID | Family | Best For |
|----------|--------|----------|
| `deepseek/deepseek-v4-pro` | DeepSeek | Harness default for the OpenCode CLI engine (`opencode.json`) and the Kilo orchestrator (`agent.yaml`) |
| `deepseek/deepseek-v4.1-flash` | DeepSeek | Newer flash tier — 1M context, cheaper than pro |
| `deepseek/deepseek-v4-flash` | DeepSeek | Previous flash tier. Retired for new Claude sessions (`tools/solocode_config.py`), still served by CommandCode and used by `tools/benchmark_executors.py` |
| `gpt-5.4-mini` | OpenAI | Harness `small_model` (`opencode.json`) — fast completions, simple tasks |
| `gpt-5.4` / `gpt-5.5` | OpenAI | Broad knowledge, explanations |
| `claude-opus-5` / `claude-sonnet-5` | Anthropic | Complex reasoning, architecture, code review |
| `google/gemini-3.5-flash` | Google | Large context analysis |
| `Qwen/Qwen3.7-Max` | Alibaba | Benchmarked in `tools/benchmark_executors.py` |
| `Qwen/Qwen3.6-Plus` | Alibaba | Cheaper Qwen tier |
| `zai-org/GLM-5` / `zai-org/GLM-5.1` | Z.ai | Benchmarked in `tools/benchmark_executors.py` |
| `moonshotai/Kimi-K3` | Moonshot | Long-context code review |
| `MiniMaxAI/MiniMax-M3` | MiniMax | General purpose |

Each model also exposes `context_length` in the `/models` response, so read that
rather than assuming a window size.

### Available Models via DeepSeek Direct

`[UNVERIFIED]` — the direct endpoint is not configured in this repo (no
`DEEPSEEK_*` entry in `.env`), so these ids were not checked against a live
`GET {DEEPSEEK_BASE_URL}/models`.

| Model ID | Best For |
|----------|----------|
| `deepseek-chat` | General purpose |
| `deepseek-reasoner` | Deep reasoning, chain-of-thought |

## API Usage Patterns

### Calling DeepSeek API (OpenAI-compatible)

Only usable when `DEEPSEEK_BASE_URL` / `DEEPSEEK_API_KEY` are set — they are not
set in this repo's `.env`.

```python
import os
import httpx

async def call_deepseek(prompt: str, system: str = "", model: str = "deepseek-chat") -> str:
    """Call DeepSeek chat completions API."""
    base_url = os.environ["DEEPSEEK_BASE_URL"]
    api_key = os.environ["DEEPSEEK_API_KEY"]

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 4096,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
```

### Calling CommandCode API (OpenAI-compatible proxy)

```python
import os
import httpx

async def call_commandcode(
    prompt: str,
    system: str = "",
    model: str = "deepseek/deepseek-v4-pro",
) -> str:
    """Call CommandCode API — proxies multiple model providers."""
    base_url = os.environ["COMMANDCODE_BASE_URL"]
    api_key = os.environ["COMMANDCODE_API_KEY"]

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 4096,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
```

## Copilot Chat Model Switching

When using Copilot Chat in VS Code, switch the active model via:
- **Command Palette** (`Ctrl+Shift+P`) → `GitHub Copilot: Switch Model`
- Or click the model name in the Copilot Chat header

Configured models are defined in `.vscode/settings.json` under `github.copilot.chat.models`.

## When to Use Which Provider

| Scenario | Provider | Model |
|----------|----------|-------|
| **Architecture design** | CommandCode | `claude-opus-5` or `claude-sonnet-5` |
| **Code review** | CommandCode | `claude-sonnet-5` or `gpt-5.5` |
| **Harness default (OpenCode / Kilo orchestrator)** | CommandCode | `deepseek/deepseek-v4-pro` |
| **Refactoring** | CommandCode | `deepseek/deepseek-v4-pro` |
| **Test generation** | CommandCode | `gpt-5.4` |
| **Complex algorithms / math** | CommandCode | `deepseek/deepseek-v4-pro` |
| **Quick edits / completions** | CommandCode | `deepseek/deepseek-v4.1-flash` or `gpt-5.4-mini` |
| **Cost-sensitive batch work** | CommandCode | `deepseek/deepseek-v4.1-flash` |
| **Long-context analysis** | CommandCode | `google/gemini-3.5-flash` or `moonshotai/Kimi-K3` |

## Error Handling

```python
import httpx

async def safe_api_call(fn, *args, **kwargs):
    """Wrapper with retry and error handling."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return await fn(*args, **kwargs)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                # Rate limited — exponential backoff
                await asyncio.sleep(2 ** attempt)
                continue
            if e.response.status_code == 401:
                raise RuntimeError("Invalid API key — check environment variables")
            if e.response.status_code >= 500:
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
            raise
        except httpx.TimeoutException:
            if attempt < max_retries - 1:
                continue
            raise RuntimeError("API call timed out after retries")
    raise RuntimeError("API call failed after max retries")
```

## Security Rules

- **Never hardcode API keys** — always use environment variables
- **Never log API responses** that contain generated code or sensitive data
- **Validate response structure** before accessing `choices[0].message.content`
- **Set reasonable timeouts** — 120s for chat completions, 30s for embeddings
- **Rotate keys periodically** — CommandCode keys expire; regenerate via dashboard

### custom-framework-rules.md

# Custom Framework Rules

> Quy tắc viết mã nguồn đặc thù cho các framework và kiến trúc sử dụng trong dự án này.

## Quy tắc Thiết kế & Kiến trúc

- **Separation of Concerns:** Tách biệt rõ ràng giữa logic giao diện (UI), logic nghiệp vụ (business logic/services) và truy xuất dữ liệu (DB/API).
- **Dependency Injection:** Sử dụng dependency injection (hoặc patterns tương đương của framework) để dễ dàng viết unit test.
- **Dữ liệu không thay đổi (Immutability):** Ưu tiên sử dụng hằng số (`const` trong JS/TS, `final` trong Java, hoặc immutable objects) để tránh lỗi bất đồng bộ.

## Quy ước Đặt tên (Naming Conventions)

- **Biến và Hàm:** Sử dụng `camelCase` (ví dụ: `getUserData`, `isLogged`).
- **Lớp và Type/Interface:** Sử dụng `PascalCase` (ví dụ: `UserSession`, `DatabaseConfig`).
- **Thư mục và File mã nguồn:** Sử dụng `kebab-case` (ví dụ: `user-controller.ts`, `data-source.js`).

## Xử lý lỗi (Error Handling)

- Không bao giờ nuốt lỗi (silent catch).
- Luôn ghi log lỗi chi tiết kèm ngữ cảnh bằng công cụ logger của hệ thống.
- Trả về mã lỗi thân thiện với người dùng (user-friendly error message) và mã lỗi kỹ thuật rõ ràng để debug.

```typescript
// GOOD
try {
  return await db.users.findUnique({ where: { id } });
} catch (error) {
  logger.error("Failed to fetch user from database", { userId: id, error });
  throw new AppError(ErrorCode.DATABASE_ERROR, "Không thể lấy thông tin người dùng.");
}

// BAD
try {
  return await db.users.findUnique({ where: { id } });
} catch (error) {
  // Silent catch
}
```

### harness-boundaries.md

# Harness Boundary Rules

> **CRITICAL:** File này là một phần của Solo-Code Harness infrastructure. Nó tồn tại để bảo vệ các agent khỏi nhầm lẫn giữa code harness và code dự án.

## Tại sao cần file này?

Khi triển khai bộ harness vào một dự án mới (`python tools/deploy.py deploy ./target-project`), các thư mục `.kilo/`, `.copilot/`, `.gemini/`, `.claude/`, `.opencode/`, `.contracts/` được copy nguyên khối vào project đích (dạng runtime-only, không mang theo dev tooling của Solo-Code-CLI). Riêng `.github/`, `.vscode/`, `tools/` là **thư mục dùng chung** — harness chỉ đặt thêm file vào đó, dự án vẫn giữ file riêng của mình. Các file như `AGENTS.md`, `kilo.jsonc`, `opencode.json` cũng được copy. (`.opencode/` từng bị gỡ ở v4.0.0, rồi được đưa trở lại thành engine chính ở v4.2.0 — xem `.harness.lock`.)

**Agent có thể nhầm lẫn theo CẢ HAI chiều:** thấy file harness trong project đích và tưởng là code dở dang của dự án; hoặc thấy CI workflow / script dev của chính dự án nằm trong `.github/`, `tools/` rồi tưởng là harness và không dám đụng. Tra `[shared_files]` trong `.harness.lock` để biết chính xác file nào là harness.

## Boundary Markers

### 1. `.harness.lock` — marker chính

File này tồn tại ở gốc project. Nếu có mặt → project được deploy bởi Solo-Code Harness. Đọc nó để biết chính xác thư mục/file nào là harness.

### 2. `.solocode/` — marker phụ

Thư mục này là marker dành riêng cho harness, chứa config nội bộ (không phải code dự án).

### 3. Harness Boundary Table

| Nếu file/thư mục... | Thì nó là... | Hành động |
|---------------------|-------------|----------|
| Bắt đầu bằng `.kilo/`, `.copilot/`, `.gemini/`, `.claude/`, `.opencode/`, `.agents/` | **Harness engine** | KHÔNG sửa, KHÔNG phân tích như code dự án |
| Bắt đầu bằng `.contracts/` | **Harness contracts** | Sub-agent status contracts |
| Bắt đầu bằng `.github/`, `.vscode/`, `tools/` | **DÙNG CHUNG** — harness *và* dự án | Harness có đặt file ở đây, nhưng dự án CŨNG sở hữu file riêng (CI workflow, `CODEOWNERS`, dependabot, cấu hình editor, script dev). Chỉ các đường dẫn liệt kê trong `[shared_files]` của `.harness.lock` là harness; **mọi file khác ở đây là code dự án** — đọc/sửa bình thường. |
| Là `AGENTS.md`, `kilo.jsonc`, `opencode.json`, `.mcp.json`, `.ruff.toml`, `.gitleaks.toml`, `Makefile`, `verify.sh`, `extensions_config.json`, `.harness.lock`, `.solocode/`, `.pre-commit-config.yaml`, `.github/pull_request_template.md`, `agent.yaml`, `pyproject.toml`, `eslint.config.js` | **Harness config** | File cấu hình agent — không phải config dự án |
| **Tất cả các file/thư mục khác** | **Project code** | Đây là code của dự án thực — được phép sửa |

## Quy tắc bắt buộc

1. **KHÔNG BAO GIỜ sửa file harness để fix bug dự án.**
2. **KHÔNG BAO GIỜ sửa file dự án để fix vấn đề harness.**
3. **Luôn đọc `.harness.lock` trước khi phân tích codebase.**
4. **Nếu bạn thấy file trong danh sách harness bị lỗi, báo cáo — đừng tự sửa.**
5. **Khi triển khai harness vào dự án mới, tất cả file harness được copy từ nguồn — không tự tạo.**

## Trường hợp đặc biệt: `Deploy` vs `Init`

- **Deploy:** Harness được copy từ repo nguồn vào project đích → các file harness đã tồn tại từ trước, không phải do dự án tạo ra.
- **Init:** Dự án mới được tạo → có thể có file trùng tên với harness (như `.gitignore`, `Makefile`) — đó là project config, không phải harness.

## Tự kiểm tra (Self-Check)

Khi phân tích bất kỳ file nào trong project, hãy tự hỏi:

> "File này có thể đã được copy vào từ Solo-Code Harness không?"

Nếu câu trả lời là "có thể" → kiểm tra `.harness.lock` trước khi hành động.

### harness-checklist.md

# Harness Review Checklist

> Run through this before shipping a harness to production or handing it off.
> A failing item is a blocker; a skipped item needs a written justification.

## Agent instructions (AGENTS.md)

- [ ] Project overview is accurate and up to date
- [ ] Repository structure reflects the current layout
- [ ] Tool permissions are explicit — allowed, restricted, and not-allowed are all specified
- [ ] Verification gates are defined and commands are correct
- [ ] No ambiguous instructions that could be interpreted multiple ways

## Hook system

- [ ] hooks.json is valid JSON with all lifecycle stages (PreToolUse, PostToolUse, SessionStart, SessionEnd)
- [ ] gate-guard.js blocks all destructive patterns (rm -rf, DROP TABLE, git push --force, etc.)
- [ ] secret-scan.js catches hardcoded API keys, passwords, and tokens
- [ ] config-protection.js blocks modification of linter/formatter configuration
- [ ] context-monitor.js has warning thresholds and output trim configured
- [ ] session-start.js resets state cleanly
- [ ] session-end.js emits session summary with token estimates and costs
- [ ] All hook scripts pass `node -c` syntax check

## Tool design

- [ ] Each tool has a clear, unambiguous name
- [ ] Tool schemas are minimal — no optional fields that the agent won't use
- [ ] Error messages tell the agent what to do next, not just what went wrong
- [ ] Tool return values are consistent (same shape on success and failure)
- [ ] No tool does more than one conceptual thing

## Context delivery

- [ ] Context is scoped to what the agent needs for this task — not the entire codebase
- [ ] Long-lived state (plans, decisions, progress) is in files, not in the prompt
- [ ] Context compaction strategy is defined for multi-session tasks
- [ ] Output trim thresholds are configured for high-volume tools (Bash, Grep, Glob)
- [ ] No sensitive data (secrets, credentials) in agent-accessible context
- [ ] Token logging and cost estimation enabled

## Planning artifacts

- [ ] PLAN.md exists for non-trivial tasks
- [ ] Milestones have explicit verification commands
- [ ] Scope boundaries (in-scope / out-of-scope) are written down
- [ ] IMPLEMENT.md captures decisions and deviations as they happen
- [ ] `/plan`, `/decide`, `/verify` commands are functional
- [ ] `.github/pull_request_template.md` exists and includes all verification gates

## Permissions & sandbox

- [ ] Agent runs with the minimum permissions needed for the task
- [ ] Destructive operations require explicit confirmation
- [ ] Network access is scoped if possible
- [ ] File system access is scoped to project directories
- [ ] kilo.jsonc deny rules cover all critical destructive operations

## Verification loop

- [ ] Tests exist for the agent's outputs (`tools/test_*.py`, `eval_harness.py`, `check_skips.py`, `.claude/hooks/guard.py` behavior)
- [ ] The agent can run the verification command itself (`checklist.py`)
- [ ] Verification runs automatically on task completion, not just on PR
- [ ] Eval criteria are written down before the task starts, not after
- [ ] Security scan passes before any commit
- [ ] No-skips policy enforced: `python .github/scripts/check_skips.py tools/`
- [ ] All "dangerous" calls in `security-allowlist.txt` have current, correct justifications

## Observability

- [ ] Session start/end hooks capture duration, tool calls, token estimates
- [ ] Token usage logged per tool call (.kilo/state/token-log.jsonl)
- [ ] Session logs persisted (.kilo/state/sessions/)
- [ ] Governance events captured (.kilo/logs/governance-events.jsonl)
- [ ] Cost estimates visible in session summary

## When this harness component should be removed

> Every harness component exists because the model can't do something yet.
> Document what capability improvement would make this component unnecessary.

| Component | Exists because | Can be removed when |
|---|---|---|
| gate-guard.js | Model doesn't reliably refuse destructive commands | Model has built-in safety refusal for rm -rf, DROP TABLE, force push |
| secret-scan.js | Model doesn't detect hardcoded secrets in context | Model integrates secret detection in code generation |
| context-monitor.js | No built-in context budget awareness in model | Models manage context window autonomously with compaction API |
| config-protection.js | Model may overwrite linter/formatter configs | Model respects configuration file boundaries natively |
| session-start.js | State must be initialized per session | Model runtime handles state lifecycle internally |
| session-end.js | Observability must be captured at session boundary | Runtime provides native telemetry and cost tracking |
| security_scan.py | CI must independently verify code safety | Model output is guaranteed safe by construction |
| checklist.py | Manual verification pipeline needed | Integrated CI/CD with agent-native checkpoints |
| check_skips.py | Model/developer may add skip() markers that silently degrade coverage | All test frameworks enforce skip-justification natively |
| security-allowlist.txt | Security scanner false-positives need auditable justification trail | All "dangerous" patterns detectable statically without exceptions |
| eval_harness.py | Harness behavior must be independently tested | Harness is verified by model provider's compliance testing |

---

*Last reviewed: 2026-06-06*

### rules-database.md

# Database Rules

> Auto-loaded when editing SQL, migrations, ORM models, or database config.

## Query Patterns

### Parameterized Queries (MANDATORY)

```python
# GOOD
cursor.execute("SELECT * FROM users WHERE email = ?", (email,))

# BAD — SQL Injection
cursor.execute(f"SELECT * FROM users WHERE email = '{email}'")
```

### Index Strategy

- Index ALL foreign keys
- Index columns in WHERE, JOIN, ORDER BY
- Composite index: equality columns first, then range
- Partial indexes for soft deletes: `WHERE deleted_at IS NULL`

### Pagination

```sql
-- GOOD: Cursor-based
SELECT * FROM orders WHERE id > $last_id ORDER BY id LIMIT 20;

-- BAD: Offset on large tables
SELECT * FROM orders ORDER BY id LIMIT 20 OFFSET 100000;
```

## Schema Design

- **IDs**: `bigint` (not `int`), use `IDENTITY` or UUIDv7
- **Timestamps**: `timestamptz` (not `timestamp`)
- **Money**: `numeric(19,4)` or `bigint` (cents)
- **Strings**: `text` (not `varchar(255)` unless constraint needed)
- **Booleans**: `boolean` (not `integer`)
- **Naming**: `lowercase_snake_case` — no quoted mixed-case

## Migration Rules

- Always create reversible migrations (up + down)
- Never modify existing migrations — create new ones
- Test migrations on staging before production
- Include data migrations alongside schema changes
- Run `EXPLAIN` on new queries before deploying

## Security

- Parameterized queries — NEVER string concatenation
- Least privilege: application user needs SELECT/INSERT/UPDATE/DELETE only
- Row Level Security (RLS) for multi-tenant tables
- Encrypt sensitive columns at rest (PII, credentials)
- Validate input lengths before DB insert

## Performance

- Avoid N+1 queries — use JOINs, batch queries, eager loading
- Keep transactions SHORT — no API calls inside transactions
- Use connection pooling (PgBouncer for PostgreSQL)
- Monitor slow queries with `pg_stat_statements`
- `EXPLAIN ANALYZE` before deploying complex queries

### rules-git.md

# Git Workflow Rules

> Auto-loaded for all sessions. Enforces conventional commits and safe git practices.

## Commit Format

```
<type>: <short description>

Co-Authored-By: Solo-Code <admin@solo-code.com>
```

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `ci`, `style`, `security`

### Examples

```
feat: add Stripe checkout webhook handler
fix: resolve race condition in session create
refactor: extract auth middleware to shared module
security: upgrade bcrypt to v5.0.1 to patch authentication bypass
```

## Branch Naming

```
<type>/<description>
```
- `feat/user-auth`
- `fix/login-timeout`
- `refactor/database-layer`

## PR Workflow

1. Create feature branch from `main`
2. Implement with TDD (tests first)
3. Self-review: run `verify.sh` locally
4. Create PR with summary + test plan
5. Address review comments
6. Squash merge to `main`

## Safety Rules (NON-NEGOTIABLE)

- **NEVER force push to main/master**
- **NEVER `git reset --hard` on shared branches**
- **NEVER commit secrets** — use `.env` files with `.gitignore`
- **NEVER skip hooks** (`--no-verify`) unless explicitly justified
- **ALWAYS pull before push** — rebase on latest main
- **ALWAYS scan for secrets** before committing:
  ```bash
  python .github/scripts/security_scan.py .
  ```

## Pre-Commit Checklist

- [ ] All tests pass locally
- [ ] No hardcoded secrets (run `security_scan.py`)
- [ ] Conventional commit message
- [ ] Changes are focused — one concern per commit
- [ ] No commented-out code or debug statements
- [ ] Documentation updated if API changed

### rules-python.md

# Python Coding Rules

> Auto-loaded when editing `.py` files. Enforces PEP 8, Pythonic patterns, security.

## Style (PEP 8)

- 4 spaces indentation (no tabs)
- Max 88 characters per line (Black default)
- `snake_case` for functions, variables, modules
- `PascalCase` for classes, `UPPER_CASE` for constants
- Imports: stdlib → third-party → local, each group alphabetically

## Type Hints (Mandatory)

- All public functions MUST have type annotations
- Use `Optional[X]` not `X | None` for Python < 3.10
- Use `list[X]` / `dict[K, V]` (Python 3.9+ generic syntax)
- Never use `Any` unless truly dynamic — use `Protocol`, `TypeVar`, or concrete types

## Pythonic Patterns

```python
# GOOD
squares = [x**2 for x in range(10)]           # comprehension
if isinstance(obj, MyClass):                   # isinstance, not type()
first = items[0] if items else None            # ternary
with open('file') as f:                        # context manager
    data = f.read()

# BAD
squares = []
for x in range(10): squares.append(x**2)       # C-style loop
if type(obj) == MyClass:                       # type() comparison
first = items and items[0] or None             # confusing short-circuit
f = open('file'); data = f.read(); f.close()   # manual resource mgmt
```

## Security (CRITICAL)

- **SQL**: Always parameterized queries — NEVER f-strings
  ```python
  cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))  # GOOD
  cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")     # BAD
  ```
- **Secrets**: Use `os.environ.get()` — never hardcode
- **Path traversal**: `pathlib.Path().resolve()` + validate with `.is_relative_to()`
- **Serialization**: Never `pickle.load()` untrusted data
- **YAML**: Use `yaml.safe_load()` not `yaml.load()`
- **Subprocess**: Use `subprocess.run(cmd, shell=False)` with list args

## Error Handling

```python
# GOOD
try:
    result = risky_operation()
except ValueError as e:
    logger.error("Invalid value: %s", e)
    raise
except ConnectionError:
    logger.warning("Retrying...")
    return fallback()

# BAD  
try:
    risky_operation()
except:          # bare except
    pass         # silent failure
```

## Testing

- Use `pytest` (not unittest.TestCase)
- Follow TDD: RED → GREEN → REFACTOR
- Target 80%+ coverage
- Test both happy path AND error paths
- Use `pytest.fixture` for shared setup
- Mock external dependencies (`unittest.mock` or `pytest-mock`)

## Project Structure

```
src/
├── __init__.py
├── models/       # Data models
├── services/     # Business logic
├── api/          # HTTP/routes
├── utils/        # Helper functions
└── config.py     # Configuration

tests/
├── conftest.py   # Shared fixtures
├── test_models/
├── test_services/
└── test_api/
```

### rules-typescript.md

# TypeScript/JavaScript Coding Rules

> Auto-loaded when editing `.ts`, `.tsx`, `.js`, `.jsx` files.

## Type Safety

- **No `any`** — use `unknown` + type guards, or proper types
- **Prefer type inference** — don't annotate obvious types
- **Discriminated unions** for state machines
- **`satisfies`** operator (TS 4.9+) for type-safe config objects
- **Never `@ts-ignore`** — fix the type or use `@ts-expect-error` with comment

## Code Style

- `const` by default, `let` only when reassigned (never `var`)
- Arrow functions for callbacks, `function` for top-level
- Template literals over string concatenation
- Optional chaining `?.` over nested `&&` checks
- Nullish coalescing `??` over `||` for default values
- Named exports preferred over default exports

## React Patterns

```tsx
// GOOD
const UserList = ({ users }: { users: User[] }) => (
  <ul>
    {users.map(user => <UserItem key={user.id} user={user} />)}
  </ul>
);

// BAD — index as key, inline handlers
{users.map((u, i) => <li key={i} onClick={() => delete(u.id)}>{u.name}</li>)}
```

- **Keys**: Use stable IDs, never array index
- **State**: Never mutate — use setState callback form
- **useEffect**: Always specify dependencies, cleanup subscriptions
- **Memo**: `useMemo` for expensive computations, `useCallback` for stable references
- **Avoid**: Props drilling > 3 levels — use context or composition

## Security (CRITICAL)

- **XSS**: Never use `dangerouslySetInnerHTML` without DOMPurify
- **Secrets**: No API keys in client bundle — use server-side routes
- **Input validation**: Validate ALL user input (Zod, Yup, joi)
- **Auth tokens**: Store in httpOnly cookies, not localStorage
- **URL params**: Sanitize before use in fetch/redirect

## Error Handling

```typescript
// GOOD
try {
  const data = await fetchUser(id);
  return data;
} catch (error) {
  logger.error('Failed to fetch user', { id, error });
  throw new AppError('User not found', 404);
}

// BAD
const data = await fetchUser(id); // unhandled rejection
```

- Always handle Promise rejections
- Use custom error classes with status codes
- Never expose internal errors to client

## Testing

- Use `vitest` or `jest`
- Target 80%+ coverage
- **Unit**: Test individual functions/utilities
- **Integration**: Test API routes with supertest
- **E2E**: Playwright for critical flows
- Mock external dependencies (fetch, DB, SDKs)

## Project Structure

```
src/
├── app/          # Next.js app router or routes
├── components/   # Reusable UI components
│   └── ui/       # Base UI primitives
├── lib/          # Utilities, API clients
├── hooks/        # Custom React hooks
├── types/        # Shared TypeScript types
└── server/       # Server-only code
```

### security-patterns.md

# Security Patterns

When editing auth, controllers, middleware, config, or `.env` files, follow these security rules:

## Authentication & Authorization

- Validate auth tokens BEFORE any business logic
- Never store credentials in code or config files — use environment variables or a secrets manager
- Apply principle of least privilege to all role checks
- Session tokens must use `httpOnly`, `secure`, and `SameSite=Strict` cookies
- JWT tokens must have expiration, use RS256/HS256 minimum, and never accept `alg: none`

## Input Validation

- ALL user input is untrusted — validate type, length, format, and range
- Use parameterized queries for SQL — never string interpolation
- Sanitize output for the target context (HTML encode for web, shell escape for CLI)
- File uploads: validate MIME type, size limit, and sanitize filenames

## Cryptography

- Use bcrypt/scrypt/argon2 for password hashing — never MD5/SHA1
- Use `crypto.randomBytes()` or equivalent for token generation — never `Math.random()`
- AES-256-GCM for symmetric encryption; never ECB mode
- Keys must be rotated periodically and never hardcoded

## Data Protection

- Never log PII, passwords, tokens, or full credit card numbers
- Mask sensitive data in logs and error messages
- API responses must not leak stack traces, internal IPs, or database errors

## Data Flow Tracing (Mandatory for Security Reviews)

When reviewing security-critical code, trace the complete data path:

1. **Client → Middleware**: Verify authentication choke points are correctly configured
2. **Middleware → API**: Verify authorization checks exist and are not bypassable
3. **API → Database/Admin SDK**: Verify privileged operations don't bypass security rules
4. **IDOR Prevention**: Every update/delete operation MUST verify resource ownership

## DevSecOps Checklist

- [ ] SAST/DAST integrated in CI/CD pipeline
- [ ] Dependency scanning enabled (Snyk, GitHub Security, Dependabot)
- [ ] Container images scanned before deployment
- [ ] Secrets managed via environment variables or vault (never hardcoded)
- [ ] Security headers configured (CSP, HSTS, X-Frame-Options, SameSite)

### shared-state.md

# Shared State — Cross-Engine Collaboration (Local-Only)

> Auto-loaded at session start. Tất cả engine đọc/ghi `.solocode/shared-state.db` (SQLite).
> File này KHÔNG được commit vào git — chỉ tồn tại local trên máy đang chạy các engine.

## Cái gì đang thực sự chạy (snapshot 2026-09-26)

Đừng tin mô tả, hãy tin số đo — và **đo lại** bằng
`python tools/shared_state.py show` trước khi dùng số liệu. Số dưới đây chỉ là
một snapshot, sẽ cũ theo thời gian:

| Bảng | Rows (snapshot) | Ai ghi |
|---|---:|---|
| `session_log` | 1000 | **Tự động** — `pre_compact.py` (Claude) + `codex_session.py` (Codex) |
| `active_locks` | 1 | Writer lấy lock theo path; tự hết hạn sau `LOCK_TIMEOUT_HOURS` = 2 giờ |
| `features` | 0 | Không ai — dùng git log + `MEMORY.md` thay thế |
| `shared_memory_*` | 0 | Không ai — `MEMORY.md` đã làm việc này |

Một bản mô tả "Session Protocol (MANDATORY)" 9 bước từng nằm ở đây,
trong đó **0/9 bước thực sự được chạy**. Nó đã bị gỡ: một quy trình
bắt buộc mà không gì kiểm chứng chỉ dạy agent tin vào thứ không có thật.

### Session start / end — không cần làm gì thủ công
Hook Claude lo phần này, nhưng ghi vào **hai store khác nhau** (xem bảng dưới).
`session_start.py` đọc `.solocode/sessions.db` và bơm bối cảnh; `session_end.py`
ghi vào `.solocode/sessions.db`; `pre_compact.py` ghi checkpoint vào
`.solocode/shared-state.db` và nhắc ghi `.solocode/context-checkpoint.json`.

### Hai SQLite store — đừng nhầm

Repo có hai DB SQLite local-only với tên dễ lẫn. Chúng phục vụ mục đích khác nhau
và **không** phải hai nguồn sự thật cho cùng một dữ liệu:

| Store | Bảng | Writer | Reader | Mục đích |
|---|---|---|---|---|
| `.solocode/shared-state.db` | `session_log`, `active_locks`, `shared_memory_*` | `pre_compact.py`, `codex_session.py`, `codex_guard.py` (locks) | `tools/shared_state.py` CLI, `garden.py`, `test_integration.py` | Nhật ký sự kiện đa engine + khoá file |
| `.solocode/sessions.db` | `sessions` | `.claude/hooks/session_start.py`, `session_end.py` (qua `session_persistence`) | `session_persistence.py`, `session_analytics.py`, `session_start.py` | Vòng đời phiên (start/end/duration/files/status) cho analytics |

Quyết định (2026-09-26): **giữ song song, ghi rõ vai trò**, không hợp nhất khi chưa
chứng minh consumer trùng — xem `docs/deepseek-harness-upgrade-acceptance.md`.

### Khi nào PHẢI dùng lock (còn giá trị)
`active_locks` thường rỗng; nó chỉ có row khi một writer đang giữ lock (hoặc khi
một lock rò rỉ chưa hết hạn). Trước khi giao một tác vụ **ghi** cho worker chạy
song song (Gemini/Antigravity sửa cùng cây thư mục), hãy lấy lock cho các file
trong phạm vi — xem `acquire_lock` ở phần API bên dưới. Đây là cơ chế chống ghi
đè duy nhất giữa các engine.

### `features` và `shared_memory_*` — schema còn, không dùng
Giữ lại để tương thích ngược (`garden.py` cảnh báo feature `in-progress`
quá 7 ngày nếu có ai ghi). Với dự án solo, dùng **git log** cho task và
**`MEMORY.md`** cho convention/gotcha/decision: chúng nằm trong repo,
agent đọc được, không cần đồng bộ. Chỉ dùng các bảng này nếu bạn thật
sự chạy nhiều engine song song và cần trạng thái chung.

## Nếu DB bị hỏng (corrupt)

Nếu `python tools/shared_state.py validate` báo lỗi, hoặc thao tác đọc/ghi báo `sqlite3.DatabaseError` — xoá file DB và để nó tự tái tạo schema rỗng ở lần chạy tiếp theo (KHÔNG còn nguồn migrate dự phòng từ `.opencode/state/` — đã gỡ ở v4.0.0; lịch sử feature/session trước đó sẽ mất nếu chưa backup):

```bash
cp .solocode/shared-state.db .solocode/shared-state.db.bak   # backup trước khi xoá, nếu còn dùng được
rm .solocode/shared-state.db .solocode/shared-state.db-wal .solocode/shared-state.db-shm
# SharedState() tự tạo schema rỗng ở lần mở kế tiếp — không cần script migrate riêng.
```

## CLI Quick Reference

```bash
python tools/shared_state.py show
python tools/shared_state.py features --status in-progress
python tools/shared_state.py sessions --limit 10
python tools/shared_state.py locks
python tools/shared_state.py validate
```

## Python API

```python
from tools.shared_state import SharedState

# Trường hợp dùng thật: khoá file trước khi giao việc GHI cho worker
# chạy song song, rồi trả khoá ngay sau khi xong.
with SharedState() as state:
    if state.acquire_lock("src/auth.py", engine="claude", model="sonnet", reason="Delegating edit to Gemini"):
        # ... thực hiện/uỷ quyền sửa file ...
        state.release_lock("src/auth.py", engine="claude")

# add_session_entry() do hook tự gọi — không cần gọi tay:
#   .claude/hooks/session_end.py, .claude/hooks/pre_compact.py
# set_feature_status() còn tồn tại nhưng không dùng ở repo này (xem trên).
```

<!-- END opencode-v2-inline-instructions -->
