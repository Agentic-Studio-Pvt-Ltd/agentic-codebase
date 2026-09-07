# Adapter capabilities — the one table

Read this in **phase 6 (Plan)** to fill the plan's `TARGET_NAME capability notes`. It is short on
purpose: the adapters are ~700 and ~580 lines and are read in **phase 7 only**. This file is the
single home of "what does this target support"; the adapters own the *emit details* and defer to it
for the verdict — if they disagree, the adapter is right and this file must be corrected to match.

Status: **Native** (the target loads it) · **Convention** (works only because the index doc points
at it) · **Draft** (written for the user to apply; agentify never authenticates) · **Substituted**
(unsupported — something else is emitted and the plan says what is lost) · **Not emitted**. Codex
column verified 2026-09-05 against **codex-cli 0.152.1** and current official docs.

## The table

| Artifact | Claude Code | Codex |
|---|---|---|
| Index doc | **Native** — `CLAUDE.md` | **Native** — `AGENTS.md` (`AGENTS.override.md` outranks it in the same directory). Codex does **not** read `CLAUDE.md` |
| Rules — prose | **Convention** — `.claude/rules/<name>.md` wired into `CLAUDE.md`; `paths:` frontmatter auto-loads | **Convention** — short rules inline in `AGENTS.md`; long ones at `<plan-dir>/rules/<name>.md` plus an `AGENTS.md` pointer |
| Rules — command policy | **Convention** — a `PreToolUse` hook on `Bash` | **Native** — `.codex/rules/<name>.rules`: Starlark `prefix_rule(pattern=[…], decision="allow"\|"prompt"\|"forbidden", justification=…)`. Experimental per the docs |
| Hooks | **Native** — `.claude/settings.json`; exit 2 blocks and feeds stderr back to the model | **Native** — `<repo>/.codex/hooks.json`, same three-level shape (event → matcher group → handler list), 12 events, regex matchers over tool names |
| Skills | **Native** — `.claude/skills/<name>/SKILL.md` | **Native** — `<repo>/.agents/skills/<name>/SKILL.md`, committable. **Not** `.codex/skills/`, which is not a load path |
| Subagents | **Native** — `.claude/agents/<name>.md` | **Native** — `<repo>/.codex/agents/<name>.toml`: `name`, `description`, `developer_instructions` required; `model`, `model_reasoning_effort`, `sandbox_mode` optional |
| MCP servers | **Draft** — `.mcp.json`, env-var placeholders only | **Draft** — `<plan-dir>/codex-mcp.toml`, a fragment for `<repo>/.codex/config.toml` the user applies |
| Permissions | **Native** — the `permissions` object in `.claude/settings.json`: `allow` / `ask` / `deny`, `deny` wins | **Native** — `.codex/rules/agentify.rules`, the same Starlark file the command-policy rows write; there is no separate permissions block |
| Plugin manifest | **Not emitted** — agentify builds one repo's personalized setup, which is not portable by construction. Both targets support plugins; agentify does not produce one | **Not emitted** — same reason |
| Reference doc | **Convention** — `<plan-dir>/*.md`, pointed at from `CLAUDE.md` | **Convention** — `<plan-dir>/*.md`, pointed at from `AGENTS.md` |

## Notes — copy the relevant ones into the plan

**Codex project trust is a prerequisite, not a footnote.** `[projects."<abs path>"] trust_level =
"trusted"` gates `AGENTS.md`, `.codex/config.toml`, `.codex/hooks.json` and `.codex/rules/`
**together**; in an untrusted repo every repo-scoped Codex artifact is inert. It is the likeliest
silent failure of a generated Codex setup — put it in the capability notes, the report's manual
checklist and phase 8; agentify never edits `config.toml` to set it.
`discovery.existing_agentic_config.codex.repo_trust_level` carries what was found.

**Codex hooks are installed, not armed.** A generated hook needs a one-time trust approval — Codex
keys trust to a hash of the definition and prompts via `/hooks`, and editing the hook re-arms it.
Phase 8 validates the JSON and dry-runs the script but must **not** claim the hook is live; never
emit or suggest `--dangerously-bypass-hook-trust`. Blocking is
`hookSpecificOutput.permissionDecision: "deny"` with exit 0; the documented exit-2-blocks path also
exists. **`[features] hooks = true` is NOT required** and agentify must never write it: hooks are on
by default at 0.152.1, verified against `codex doctor --json` on a machine whose `config.toml` has
no `hooks` key (`adapters/codex.md` §3). *UNVERIFIED: the meaning of non-zero exit codes other
than 2 is undocumented.*

**Codex index doc.** `project_doc_max_bytes` defaults to **32768**, shared by the whole `AGENTS.md`
chain (global, root, every directory down to the cwd), and discovery **stops** at the cap — appending
to a large `AGENTS.md` can silently drop deeper files. Deeper files win on conflict; there is no
`@import`. A repo with only `CLAUDE.md` gives Codex nothing: write `AGENTS.md`, or symlink one to the
other (the only zero-config way one file serves both) and otherwise say in the plan that the two are
kept in sync by hand.

**Rules.** The two targets differ here and the difference is load-bearing. **Claude Code walks
`.claude/rules/` natively and recursively**: a rule with a `paths:` frontmatter list loads lazily
when a matching file is read, and a rule **without** one loads at session start in every session
(`adapters/claude-code.md` §4.2). The literal key is `paths:` — `scope:` is ignored outright, and a
rule emitted with `scope:` loads eagerly forever. That makes path-scoped rules essentially free and
unscoped rules the expensive form, which is why the adapter holds unscoped rules to 2. **Codex walks
no prose rules directory at all**, so there a rule and its `AGENTS.md` pointer are one artifact,
built in one step and verified together in phase 8. Codex's `.rules` files are a different thing —
a command-approval policy, this target's permission surface; most restrictive wins, and
`codex execpolicy check --pretty --rules <f> -- <cmd>` validates one.

**Subagents → Codex.** Near-direct: `name`→`name`, `description`→`description`, markdown
body→`developer_instructions`, `model`→`model`. They are real separate threads, so isolated context,
delegation and parallelism are all present. **One loss:** no found equivalent of Claude Code's
per-agent `tools` allowlist (nearest: `sandbox_mode`, `mcp_servers`) — say so when a candidate's
value depended on tool restriction. **Skills:** same `SKILL.md` format and `name` + `description`
progressive disclosure on both, so one file can serve both — practice, not a documented guarantee.
Never write a skill into a tree the user already has it in; `discovery` reports shared entries by
resolved path. *UNVERIFIED: whether `<repo>/.agents/skills` is subject to the `.codex/` trust gate.*

**Permissions.** The cheapest guardrail in the product and the one most runs skip. On Claude Code it
is a second merge into the same `.claude/settings.json` the hooks merge writes, so both follow the
same read-copy-merge-write discipline; **`deny` beats `allow`**, and a higher-precedence
enterprise/user settings file can still deny what this block allows (`adapters/claude-code.md` §1.3)
— say that rather than claiming the allow took effect. On Codex there is no second file: the
permission surface *is* `.codex/rules/agentify.rules`, so the permissions candidate and the
command-policy candidates produce one validated file. Prefix rules on both targets are prefix
matching and not shell semantics — `npm` does not catch `npx`, `pnpm`, or `npm` reached through a
package script — and the plan says so.

**MCP (both).** Drafts only; never a literal credential. Claude Code: `${VAR}` placeholders named
from `discovery.env_var_names`. Codex: the dedicated keys `bearer_token_env_var`,
`env_http_headers`, `env_vars` — **not** `${VAR}`, whose expansion in arbitrary `config.toml` values
is unverified. `default_tools_approval_mode` accepts `auto | prompt | writes | approve`.

**Plugin manifest: never built.** Both targets support plugins and both schemas are documented in
the adapters (§4.8 / §4.7) so `setup-manager` can answer a question about them — but a run emits
nothing. The shareable unit is the committed index doc, the repo-scoped config directory and
`<plan-dir>/`, which a teammate gets by cloning.

## Using it in phase 6

1. Take the column for `TARGET`; drop rows for artifact types the plan does not contain.
2. Fill the plan's capability table: `Capability` = the row, `Supported` = the status word, `What I
   do` = the cell text for that target.
3. Paste every note above that applies to a row you kept into `CAPABILITY_PROSE_NOTE`; on Codex the
   trust note applies to **every** run. A caveat the user has not read is one they did not approve.
4. Do **not** open an adapter to write this section. Phase 7 opens exactly one adapter, once.
