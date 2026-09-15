# Adapter capabilities — the one table

Read this in **phase 6 (Plan)** to fill the plan's `TARGET_NAME capability notes`. It is short on
purpose: the adapters are **1,280 and 1,534 lines** (88 KB and 109 KB, measured 2026-09-15) and are
read in **phase 7 only**. This file is the single home of "what does this target support"; the
adapters own the *emit details* and defer to it for the verdict — if they disagree, the adapter is
right and this file must be corrected to match.

**This file stands alone.** Every row carries three things — the verdict, where it is emitted, and
the **basis** the verdict rests on — because phase 6 is forbidden to open an adapter to check any of
them. A verdict with no basis tag is a bug in this file, not a licence to go read the adapter.

Status: **Native** (the target loads it) · **Convention** (works only because the index doc points
at it) · **Draft** (written for the user to apply; agentify never authenticates) · **Substituted**
(unsupported — something else is emitted and the plan says what is lost) · **Not emitted**.

Basis: **[D]** documented — stated in the target's current official documentation, not exercised
here · **[M `<ver>`]** measured — established by running a command or reading a file on that build ·
**[D+M `<ver>`]** both · **[U]** untested — neither documented nor exercised. Never state a `[U]`
to the user as fact, and never build on one without asking first.

## Provenance — what was verified, when, and against which build

| Column | How the verdicts were established | Last re-measured | Build measured on | Build installed 2026-09-15 |
|---|---|---|---|---|
| Claude Code | the CLI's own bundled zod schemas, real files on disk, and **two live headless sessions** for the rules loader (`adapters/claude-code.md` frontmatter) | 2026-09-05 | Claude Code **2.1.260** | **2.1.269** — newer, not re-measured |
| Codex | scratch-`CODEX_HOME` app-server probes (`hooks/list`, `skills/list`), `codex debug prompt-input`, `codex execpolicy check`, `codex --strict-config app-server`, plus the current unversioned official docs (`adapters/codex.md`, "Verified against") | 2026-09-05; the project-trust cost table re-measured on **0.153.1** | `codex-cli` **0.152.1** | **0.154.0-alpha.6.2** — newer, not re-measured |

On **2026-09-15** the launch audit re-read every contract claim in this file against both targets'
then-current official documentation and recorded the installed build of each. **It re-read; it did
not re-measure.** No verdict here was upgraded on the strength of that pass, and nothing has been
exercised on the two builds in the last column. A row whose `[M <ver>]` names an older build than the
one installed is reporting its own age honestly — that is what the tag is for, not a defect to tidy
away.

## The table

| Artifact | Claude Code | Codex |
|---|---|---|
| Index doc | **Native** — `CLAUDE.md` **[D+M 2.1.260]** | **Native** — `AGENTS.md` (`AGENTS.override.md` outranks it in the same directory). Codex does **not** read `CLAUDE.md` **[D+M 0.152.1]** |
| Rules — prose | **Native** — `.claude/rules/**/*.md`, walked by Claude Code itself; **no index-doc wiring needed**. A rule with **no** `paths:` loads at session start in every session; a `paths:`-scoped rule defers until the model reads a matching file **[M 2.1.260]** | **Convention** — short rules inline in `AGENTS.md`; long ones at `<plan-dir>/rules/<name>.md` plus an `AGENTS.md` pointer. Nothing walks a prose rules directory here, so the pointer **is** the load path **[M 0.152.1]** |
| Rules — command policy | **Convention** — a `PreToolUse` hook on `Bash` **[D+M 2.1.260]** | **Native** — `.codex/rules/<name>.rules`: Starlark `prefix_rule(pattern=[…], decision="allow"\|"prompt"\|"forbidden", justification=…)`. Documented as experimental **[D+M 0.152.1]** |
| Hooks | **Native** — `.claude/settings.json`; exit 2 blocks and feeds stderr back to the model **[D+M 2.1.260]** | **Native** — `<repo>/.codex/hooks.json`, same three-level shape (event → matcher group → handler list), 12 events, anchored regex matchers over tool names. Canonical names are `Bash` (shell) and `apply_patch` (edits); the emitted matcher also accepts the older spellings `exec_command` / `shell_command` / `local_shell` / `exec` / `run` **[D+M 0.152.1]** |
| Skills | **Native** — `.claude/skills/<name>/SKILL.md` **[D+M 2.1.260]** | **Native** — `<repo>/.agents/skills/<name>/SKILL.md`, committable. `<repo>/.codex/skills/` **also** loads with `scope: "repo"` **[M 0.152.1]**, but it is undocumented and unused in the wild, so it is **not the path agentify writes** — `.agents/skills` is the documented cross-tool one a Claude Code install can share |
| Subagents | **Native** — `.claude/agents/<name>.md` **[D+M 2.1.260]** | **Native** — `<repo>/.codex/agents/<name>.toml`: `name`, `description`, `developer_instructions` required; `model`, `model_reasoning_effort`, `sandbox_mode` optional **[D+M 0.152.1]**. That a *newly written* one is loaded is **[U]** — see the subagents note |
| MCP servers | **Draft** — `.mcp.json`, env-var placeholders only **[D+M 2.1.260]** | **Draft** — `<plan-dir>/codex-mcp.toml`, a fragment for `<repo>/.codex/config.toml` the user applies **[D+M 0.152.1]** |
| Permissions | **Native** — the `permissions` object in `.claude/settings.json`: `allow` / `ask` / `deny`, `deny` wins **[D+M 2.1.260]** | **Native** — `.codex/rules/agentify.rules`, the same Starlark file the command-policy rows write; there is no separate permissions block **[D+M 0.152.1]** |
| Plugin manifest | **Not emitted** — agentify builds one repo's personalized setup, which is not portable by construction. Both targets support plugins; agentify does not produce one **[D]** | **Not emitted** — same reason **[D]** |
| Reference doc | **Convention** — `<plan-dir>/*.md`, pointed at from `CLAUDE.md` **[D+M 2.1.260]** | **Convention** — `<plan-dir>/*.md`, pointed at from `AGENTS.md` **[D+M 0.152.1]** |

## Notes — copy the relevant ones into the plan

**Codex project trust is a prerequisite, not a footnote — and it does not gate quite everything.**
`[projects."<abs path>"] trust_level = "trusted"` gates `AGENTS.md`, `.codex/config.toml`,
`.codex/hooks.json` and `.codex/rules/`; in an untrusted repo each of those is **silently absent**,
and that is the likeliest silent failure of a generated Codex setup. **Skills are the exception:**
`<repo>/.agents/skills/**` loaded under `trusted`, under `untrusted`, and with **no `[projects]`
entry at all** (**[M 0.152.1]**, `adapters/codex.md` §0.2 and §4.4 — the docs state it neither way,
so treat the trust-independence as build-specific rather than a promise). One more asymmetry belongs
in the plan: **no `[projects]` entry is not the same state as an explicit `untrusted`** — a
first-seen project still rendered the `AGENTS.md` section, and only an explicit `untrusted`
suppressed it (**[M 0.153.1]**). Put trust in the capability notes, the report's manual checklist and
phase 8; agentify never edits `config.toml` to set it.
`discovery.existing_agentic_config.codex.repo_trust_level` carries what was found.

**Codex hooks are installed, not armed.** A generated hook needs a one-time trust approval — Codex
keys trust to a hash of the definition and prompts via `/hooks`, and editing the hook re-arms it.
Phase 8 validates the JSON and dry-runs the script but must **not** claim the hook is live; never
emit or suggest `--dangerously-bypass-hook-trust`. Blocking is
`hookSpecificOutput.permissionDecision: "deny"` with exit 0; the documented exit-2-blocks path also
exists. **`[features] hooks = true` is NOT required** and agentify must never write it: hooks are on
by default (**[M 0.152.1]** — `codex doctor --json` on a machine whose `config.toml` has no `hooks`
key, `adapters/codex.md` §3). **[U]** the meaning of non-zero exit codes other than 2 is
undocumented. **[U]** that a generated hook fires on a real tool call: the matcher and the
`tool_input.command` payload contract match the current documentation and are exercised by fixtures,
but live activation has never been observed. Say "installed", never "working".

**Codex index doc.** `project_doc_max_bytes` defaults to **32768** (**[D+M 0.152.1]**), shared by the
whole `AGENTS.md` chain (global, root, every directory down to the cwd), and discovery **stops** when
the budget runs out — appending to a large `AGENTS.md` can silently drop deeper files. Deeper files
win on conflict; there is no `@import`. A repo with only `CLAUDE.md` gives Codex nothing: write
`AGENTS.md`, or symlink one to the other (the only zero-config way one file serves both) and
otherwise say in the plan that the two are kept in sync by hand.

**Rules — the two targets differ, and the difference is load-bearing. There is no sentence that is
true of both; write the target's own.** **Claude Code walks `.claude/rules/` natively and
recursively** (**[M 2.1.260]**, two live headless sessions, `adapters/claude-code.md` §4.2): a rule
with a `paths:` frontmatter list loads lazily when a matching file is read, and a rule **without**
one loads at session start in every session. Neither needs an index-doc pointer in order to load; the
pointer is for humans. The literal key is `paths:` — `scope:` is ignored outright, and a rule emitted
with `scope:` loads eagerly forever. That makes path-scoped rules essentially free and unscoped rules
the expensive form, which is why the adapter holds **unscoped** rules to 2. That is a context-budget
constraint on one rule *form* — path-scoped rules stay unbounded, one per real zone — and it is never
put to the user in those terms. **Codex walks no prose rules directory at all** (**[M 0.152.1]**), so
there a rule and its `AGENTS.md` pointer are one artifact, built in one step and verified together in
phase 8, and an unreferenced rule file is inert. Telling a Claude Code user their rule only works
because the index doc points at it is telling them something untrue, so never paste the Codex half
into a Claude Code plan or the reverse. Codex's `.rules` files are a different thing again — a
command-approval policy, this target's permission surface; most restrictive wins, and `codex
execpolicy check --pretty --rules <f> -- <cmd>` validates one.

**Subagents → Codex.** Near-direct: `name`→`name`, `description`→`description`, markdown
body→`developer_instructions`, `model`→`model` (**[D+M 0.152.1]**, cross-checked against eight
production files). They are real separate threads, so isolated context, delegation and parallelism
are all present. **One loss:** no found equivalent of Claude Code's per-agent `tools` allowlist
(nearest: `sandbox_mode`, `mcp_servers`) — say so when a candidate's value depended on tool
restriction. **[U] that a newly written `.codex/agents/*.toml` is actually loaded**: subagents are
exposed through a spawn tool at turn time rather than in the base prompt, so no read-only probe can
confirm it (`adapters/codex.md` §4.5). Phase 8 therefore validates a Codex subagent **statically
only**, and the live check is a numbered manual step in the report — say "written and statically
valid", never "working". **Skills:** same `SKILL.md` format and `name` + `description` progressive
disclosure on both, so one file can serve both — **[U]**, observed practice rather than a documented
guarantee. Never write a skill into a tree the user already has it in; `discovery` reports shared
entries by resolved path.

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
is **[U]**. `default_tools_approval_mode` accepts `auto | prompt | writes | approve`.

**Plugin manifest: never built.** Both targets support plugins and both schemas are documented in
the adapters (§4.8 / §4.7) so `setup-manager` can answer a question about them — but a run emits
nothing, on either target, under any answer the interview can produce. `templates/plugin.json.tmpl`
and `templates/codex-plugin.json.tmpl` still ship as reference copies of those schemas and are never
read by a build (`references/build-and-verify.md`). Keep two things apart when the user asks:
**packaging the customer's generated setup as a plugin** is the v1 non-goal this row states, while
**agentify itself being distributed as a Claude Code plugin** is how its own install route 1 works
and is unaffected by any of it. The shareable unit of a *setup* is the committed index doc, the
repo-scoped config directory and `<plan-dir>/`, which a teammate gets by cloning.

## Using it in phase 6

1. Take the column for `TARGET`; drop rows for artifact types the plan does not contain.
2. Fill the plan's capability table: `Capability` = the row, `Supported` = the status word, `What I
   do` = the cell text for that target. **Drop the basis tag from the user-facing cell** — it is
   working provenance — but keep what it implies: a `[U]` row is described as untested wherever it
   reaches the user, in the plan's notes and again in the report.
3. Paste every note above that applies to a row you kept into `CAPABILITY_PROSE_NOTE`; on Codex the
   trust note applies to **every** run. A caveat the user has not read is one they did not approve.
4. Do **not** open an adapter to write this section. Phase 7 opens exactly one adapter, once. If a
   verdict you need is missing or tagless here, that is a bug to report — fixing it is an edit to
   this file, never a phase-6 read of a 1,280- or 1,534-line adapter.
