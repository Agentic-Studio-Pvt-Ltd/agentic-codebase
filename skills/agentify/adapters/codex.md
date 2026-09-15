---
adapter: codex
adapter-version: 2
target-id: codex
status: v1.1 — ships after the Claude Code adapter (PRD §15)
verified-against: 2026-09-05 — `codex-cli 0.152.1` at
  `/Applications/ChatGPT.app/Contents/Resources/codex` on macOS 26.5.2 (arm64), plus the current
  unversioned Codex documentation at `learn.chatgpt.com/docs/*`. See the **Verified against** block
  below for exactly how each part of this file was established.
---

# Adapter: Codex

**This file is the only place Codex paths and file formats may live** (PRD §11.3). Same contract,
same five parts, same order as `adapters/claude-code.md`: DETECT · LOCATE TRANSCRIPTS · LIST
EXISTING CONFIG · EMIT · SMOKE TEST. Where Codex genuinely has no equivalent of a Claude Code
capability, this adapter says **UNSUPPORTED — substitution:** and names what is emitted instead and
what is lost, and the plan must repeat that verbatim so the user approves the downgrade knowingly
rather than by omission. **As of 0.152.1 there is exactly one such loss** — no per-agent tool
allowlist for subagents (§4.5). Everything else Claude Code can do, Codex can do, and three earlier
claims to the contrary in this file were wrong (§0.1).

Read this file in **phase 0** (DETECT, LIST EXISTING CONFIG) and again in **phase 7** (EMIT) and
**phase 8** (SMOKE TEST). Do not read it in phases 3–6; the plan describes artifacts in
target-neutral terms and the capability notes come from `adapters/capabilities.md`.

Confidence markers:

| Marker | Meaning |
|---|---|
| **VERIFIED** | Established by running a command or reading a file on the local 0.152.1 install on 2026-09-05. Build-specific, but not a guess. |
| **DOCUMENTED** | Stated in current Codex documentation and consistent with observation, but not independently exercised here. |
| **UNVERIFIED** | Not confirmed. Each one names what would confirm it. Never state it to the user as fact; never build on it without asking first. |

---

## Verified against

| Part | How it was established on 2026-09-05 |
|---|---|
| §1 DETECT | `codex --version` (`codex-cli 0.152.1`); `command -v codex` (absent); executable probe of three install paths; `codex doctor --json` (`config.load.details`); `codex sandbox -- /usr/bin/env` for the injected environment. |
| §2 LOCATE TRANSCRIPTS | Direct read of `~/.codex/sessions/**` (240 rollouts) and `~/.codex/archived_sessions/**` (84), including the first record of the newest rollout; corroborated by the prior empirical survey of all 166,116 records. |
| §3 LIST EXISTING CONFIG | `ls`/`find` over `~/.codex` and over repo-scoped `.codex/` directories in three real repos; `codex doctor --json`; `codex features list`; section-header-only `grep` of `config.toml` (**no value was read, copied or logged**). |
| §4 EMIT | Live probes against a **scratch `CODEX_HOME` and a scratch repo**, driving the app-server RPCs `hooks/list` and `skills/list`, plus `codex debug prompt-input`, `codex execpolicy check`, and `codex --strict-config app-server`. The real `~/.codex` was never written to. Schemas cross-checked against `codex app-server generate-json-schema`. |
| §5 SMOKE TEST | Every command in the table was run at least once in the scratch environment and its output observed. |

The documentation read is the current unversioned "latest", whose changelog already lists v0.153.0
and whose updater offers 0.153.4 — **both newer than the local 0.152.1**. Where docs and local
behaviour disagree, this file records what the local build actually did.

**Re-read 2026-09-15, not re-measured.** The launch audit checked this file's contract claims against
the then-current official documentation and recorded the installed build as **`codex-cli`
0.154.0-alpha.6.2**, two minor versions past the 0.152.1 every **VERIFIED** below was taken on. No
probe was re-run on it: no generated agent was spawned through Codex and no generated hook was
activated in a live Codex session, then or before. So every version number below stands as written —
it says when a thing was true, not that it is still true — and nothing in this file has been promoted
from **DOCUMENTED** or **UNVERIFIED** to **VERIFIED** on the strength of a newer binary being present.
`adapters/capabilities.md` carries the same two dates and the same caveat, which is where phase 6
reads them.

---

## 0. Three facts that govern everything below

**0.1 Codex has a full hook system.** Earlier versions of this adapter declared hooks UNSUPPORTED
and substituted `AGENTS.md` prose plus git hooks. That was wrong. Codex has 12 hook events, regex
matchers, timeouts, a JSON stdin/stdout contract, a repo-scoped committable `hooks.json`, and a
trust gate. See §4.3. Any wording anywhere in agentify that still says otherwise is stale.

**0.2 Project trust gates almost every repo-scoped artifact — and failure is silent.**
`[projects."<abs repo path>"] trust_level` in `${CODEX_HOME}/config.toml` decides whether Codex
loads the repo's `.codex/` layer at all. Measured in the scratch environment:

| Artifact | `trust_level = "trusted"` | `trust_level = "untrusted"` | no `[projects]` entry at all |
|---|---|---|---|
| `<repo>/.codex/hooks.json` | loads | **silently absent** | **silently absent** |
| `<repo>/.codex/config.toml` | loads | **silently ignored** | not separately measured |
| `<repo>/.codex/rules/*.rules` | loads (and a syntax error is fatal, §4.2) | not loaded | not separately measured |
| `<repo>/AGENTS.md` | loads | **silently absent** | loaded (see caveat) |
| `<repo>/.agents/skills/**`, `<repo>/.codex/skills/**` | loads | **loads anyway** | loads anyway |

All **VERIFIED** by `hooks/list`, `skills/list` and `codex debug prompt-input` runs against a
scratch repo whose only difference between runs was the `trust_level` line.

> **UNVERIFIED — a first-seen project.** With **no** `[projects]` entry, `codex debug prompt-input`
> still included `AGENTS.md`. A real interactive session prompts the user to trust a new directory,
> and it is unconfirmed whether that prompt gates the same content. **What would confirm it:** open
> a fresh interactive Codex session in a directory Codex has never seen, decline the trust prompt,
> and ask the model to quote a marker line from the repo's `AGENTS.md`.

Consequence for the pipeline: **project trust is a plan item, not a footnote.** It belongs in the
plan's capability notes, in the report's needs-you section, and in the phase-8 checks. It is the
most likely reason a correctly generated Codex setup does nothing at all.

**What trust costs you at build time, measured.** Measured 2026-09-05 in a scratch `CODEX_HOME`,
changing only the trust line between runs, on **`codex-cli 0.153.1`** — the local install has moved
past the `0.152.1` in this file's frontmatter, and the §0.2 table above still holds on it. This
table is the reachability budget for §5, and every "no" in it is a needs-you step rather than a
failing check:

| Phase-8 check | No `[projects]` entry (a fresh clone) | `trust_level = "untrusted"` | `trust_level = "trusted"` |
|---|---|---|---|
| `hooks/list` sees the generated hook | **no** — `hooks: []`, `warnings: []`, `errors: []` | **no**, identically | yes (`trustStatus` still `"untrusted"`) |
| `hooks/list` reports a malformed `hooks.json` | **no** — warnings stay empty, so this proves nothing about the file | **no** | yes — names the field, line and column |
| `--strict-config app-server` validates `<repo>/.codex/config.toml` | **no** — an unknown field there does not stop the server | **no** | yes — exits 1 with `<file>:<line>:<col>: unknown configuration field …` |
| `execpolicy check --rules <file>` | **yes** — it reads the path you hand it, trust is not consulted | yes | yes |
| `skills/list` sees `<repo>/.agents/skills/**` | **yes**, `"scope":"repo"` | **yes** | yes |
| `debug prompt-input` contains the `AGENTS.md` section | **yes** — measured, a first-seen project still renders it | **no** — an explicit `untrusted` suppresses it | yes |

The three "yes on a fresh clone" rows are why the rules, skills and index-doc checks stay strict
while the hooks and repo-TOML checks cannot. The `AGENTS.md` row is also the sharpest statement of
§0.2's asymmetry: **no entry** is not the same state as an **explicit `untrusted`**, and only the
second suppresses the index doc. It does *not* close §0.2's UNVERIFIED note, which is about the
interactive trust prompt, and this was measured through `debug prompt-input` with no session open.

**0.3 agentify never sets trust, and never fakes it either.** Writing
`[projects."<repo>"] trust_level = "trusted"` into `${CODEX_HOME}/config.toml` would make every
phase-8 check above reachable in one line. agentify does not do it and must never offer to: deciding
that a directory's committed code may configure the agent, run hooks and set an exec policy is a
security decision belonging to the person whose machine it is, and agentify has no standing to make
it on their behalf. The consequence is accepted deliberately — **on a first run, "the harness loaded
it" is not a claim this tool can make** — and it is discharged by saying so, in a numbered needs-you
step with the reason, not by working around it.

The workaround is specifically off limits, and it was measured rather than assumed: pointing
`CODEX_HOME` at a scratch directory carrying a trusted entry *does* make `hooks/list` return the
hook, and it also makes Codex build a whole new home there — sqlite stores, an `installation_id`,
and `git` clones of the plugin marketplaces. One `initialize` left seven `plugins-clone-*` working
trees with packfiles. That is a **network call**, out of a phase that promises none (PRD §13). Do
not do it, and do not suggest it.

---

## 1. DETECT

### 1.1 Is Codex the running agent?

| # | Signal | Confidence | Meaning |
|---|---|---|---|
| 1 | `CODEX_SANDBOX` is set (observed value `seatbelt`) | **VERIFIED** — `codex sandbox -- /usr/bin/env` emitted `CODEX_SANDBOX=seatbelt` and `CODEX_SANDBOX_NETWORK_DISABLED=1`, neither present in the parent shell | Conclusive that the command is running inside Codex's sandbox. Absent under `danger-full-access` / `--dangerously-bypass-approvals-and-sandbox`, so absence proves nothing. |
| 2 | `CODEX_HOME` is set in the command's own environment | **VERIFIED** — exported into sandboxed commands alongside `CODEX_SANDBOX` | Strong. Also tells you which home to resolve against. |
| 3 | `${CODEX_HOME:-$HOME/.codex}/config.toml` exists | **VERIFIED** | Codex is *installed*. Not proof it is running. |
| 4 | `${CODEX_HOME:-$HOME/.codex}/sessions/` exists with recent files | **VERIFIED** | Codex has been used recently. Not proof it is running. |
| 5 | A Codex binary resolves (§1.3) | **VERIFIED** | Codex CLI is installed. Not proof it is running. |
| 6 | `<repo>/AGENTS.md` exists | **VERIFIED** as a convention | The repo is set up for *an* AGENTS.md-reading agent, of which there are several. Weak; never decide on this alone. |

```sh
# Detection probe — read-only, no network.
[ -n "${CODEX_SANDBOX:-}" ]  && echo "target=codex (sandbox=$CODEX_SANDBOX)"
CODEX_DIR="${CODEX_HOME:-$HOME/.codex}"
[ -f "$CODEX_DIR/config.toml" ] && echo "codex-installed=$CODEX_DIR"
[ -d "$CODEX_DIR/sessions" ]    && echo "codex-sessions=present"
[ -f "$REPO/AGENTS.md" ]        && echo "agents-md=present"
```

**Detection rule (do this, do not improvise).**

1. Signal 1 or 2 present ⇒ target is **codex**. Stop.
2. Claude Code's §1.1 signals 1–3 present ⇒ target is **claude-code**. Stop.
3. Otherwise, signals 3–6 prove installation only: **ask the user to confirm the target** (PRD §7.1
   permits asking when detection is ambiguous). Offer Codex / Claude Code / both.
4. Never infer "Codex" from the absence of Claude Code markers. A third agent may be running.

> **UNVERIFIED — `CODEX_THREAD_ID` / `CODEX_SESSION_ID`.** Both names exist in the 0.152.1 binary and
> would be unconditional markers (not sandbox-dependent) if exported during a live turn. Only
> `codex sandbox` could be tested here, and it exported neither. **What would confirm it:** run
> `env | grep CODEX` from inside a real Codex turn on the target build.

### 1.2 Home directory resolution

Resolve through `${CODEX_HOME:-$HOME/.codex}` **everywhere in this adapter and in every script it
drives.** Never hardcode `~/.codex`. `CODEX_HOME` was unset in the login shell on the verification
machine and set to the real home inside Codex-spawned commands; `codex doctor --json` reports the
resolved value as `checks["config.load"].details.CODEX_HOME` (**VERIFIED**).

### 1.3 Finding the Codex binary — `which codex` fails on a working install

On the verification machine `command -v codex` finds **nothing**, yet Codex 0.152.1 is installed and
in daily use: after the July 2026 merger the CLI lives inside the ChatGPT desktop bundle. A detector
that shells out to `which codex` will report Codex as absent on a perfectly healthy install.

Resolve in this order, take the first hit, and **quote the path** — never hardcode one:

```sh
codex_bin() {
  command -v codex 2>/dev/null && return 0
  for p in "$HOME/.local/bin/codex" \
           "/Applications/ChatGPT.app/Contents/Resources/codex" \
           "/Applications/Codex.app/Contents/Resources/codex"; do
    [ -x "$p" ] && { printf '%s\n' "$p"; return 0; }
  done
  return 1
}
```

- `command -v codex` — the installer (`~/.local/bin/codex`) and package-manager installs. **VERIFIED
  absent here**, which is the whole point of the fallback.
- `/Applications/ChatGPT.app/Contents/Resources/codex` — **VERIFIED present**, `codex-cli 0.152.1`.
- `/Applications/Codex.app/Contents/Resources/codex` — the pre-merger location. **VERIFIED absent
  here**; probe it anyway for older installs.

Failing to resolve a binary is **not** a failure of the run. Every artifact in §4 is a file on disk;
the binary is needed only for the optional smoke tests in §5, which degrade to static checks.

### 1.4 Model class check (PRD §7.1 — warn, never enforce)

`config.toml` carries top-level `model` and `model_reasoning_effort` (**VERIFIED**). Do not parse the
file for it — `codex doctor --json` reports `model` and `model provider` in
`checks["config.load"].details` with no secret exposure (**VERIFIED**). Read for the warning only.
**Warn, do not enforce**, and never change them.

---

## 2. LOCATE TRANSCRIPTS

The adapter never reads transcripts. It supplies the root and the target flag; `mine_transcripts.py`
does the reading, filtering, scrubbing and capping, and only after phase-0 consent.

```sh
python3 "$SKILL_DIR/scripts/mine_transcripts.py" --repo "$REPO" --target codex
```

### 2.1 Paths

```
${CODEX_HOME:-$HOME/.codex}/sessions/<YYYY>/<MM>/<DD>/rollout-<ISO8601-with-dashes>-<uuid>.jsonl
${CODEX_HOME:-$HOME/.codex}/archived_sessions/<YYYY>/<MM>/<DD>/rollout-<...>.jsonl
```

**VERIFIED** — 240 live rollouts and 84 archived on the verification machine, e.g.
`sessions/2026/09/04/rollout-2026-09-04T19-01-33-01a06c9e-11f1-7730-b782-3a38fee9de45.jsonl`.

`archived_sessions/` uses the **identical** format and naming, and archiving **moves** a rollout
rather than copying it — zero id overlap between the two trees was measured, so reading both cannot
double-count. Archiving is a user action, not age eviction: the archived date range sits *inside* the
live range. **Read it whenever `--days` covers it**; skipping it silently discarded roughly a third
of one repo's history on this machine.

Also present and **explicitly out of scope**: `${CODEX_HOME}/session_index.jsonl` — records shaped
`{id, thread_name, updated_at}` with **no `cwd`**, missing 79% of live rollouts, and backfilled at a
single timestamp. It is a UI thread-name cache. **Never use it to filter, count, or detect.**

### 2.2 Sessions are NOT partitioned by repo — and this is a real cost difference

Claude Code gives every project its own directory under `~/.claude/projects/<encoded-path>/`, so
finding a repo's sessions is a directory lookup. **Codex has no such index.** Every session on the
machine lands in one date tree, and the repo association lives *inside the file*, in the first
record:

```jsonc
// first record of every rollout — VERIFIED on 240/240 live and 84/84 archived files.
// `ordinal` is NEW: a survey of all 166,116 records found exactly three top-level keys
// (timestamp/type/payload), but the newest rollout written by 0.152.1 carries a fourth.
// Read by key, never by shape, and never assume a field exists.
{"timestamp":"…","type":"session_meta","ordinal":0,"payload":{
   "session_id":"…","id":"…","timestamp":"…",
   "cwd":"/absolute/path/of/the/working/directory",     // <- filter key #2
   "git":{"repository_url":"https://github.com/org/repo.git",
          "branch":"main","commit_hash":"…"},           // <- filter key #1, when present
   "thread_source":"user",            // "subagent" / "guardian_review" / absent
   "source":"vscode",                 // or {"subagent":{"thread_spawn":{…}}}
   "parent_thread_id":null,"forked_from_id":null,
   "originator":"…","cli_version":"0.152.1","model_provider":"…",
   "history_mode":"paginated","base_instructions":"…","context_window":…
}}
```

**State this plainly in the plan when history is thin:** locating a repo's sessions on Codex means
opening the first record of every candidate rollout, not reading a directory name. That is the cost,
and it is why the miner is bounded by records examined rather than bytes on disk.

**Mining strategy the miner must follow on this target:**

1. Walk both date trees **newest first**, bounded by `--days`.
2. Read **only the first record** of each file and decide from it. Match by
   `payload.git.repository_url` **first**, falling back to a `cwd` prefix test. On this machine a
   `cwd` prefix match on one repo's canonical path found **1** session; matching on
   `repository_url` found **135** across 8 git worktrees. 39 sessions carry no `git` payload and
   need the `cwd` path. Keep the existing subdirectory-session warning, and note that a nested
   *sibling* repo is a `cwd`-prefix false positive that `repository_url` fixes.
3. **Exclude harness threads.** ~60% of rollout files on this machine are the agent's own
   subagent threads, whose "user" turns are the parent agent's prompts — the exact analogue of
   Claude Code's `isSidechain: true`. Filter by **exclusion, not inclusion**, because
   `thread_source` is absent on many older files:

   ```python
   is_harness = (
       meta.get("thread_source") in {"subagent", "guardian_review"}
       or (isinstance(meta.get("source"), dict) and "subagent" in meta["source"])
       or bool(meta.get("parent_thread_id"))
   )
   ```

   A `thread_source == "user"` *inclusion* filter would silently drop ~30% of genuine history.
   Never use the sqlite `has_user_event` column — it is `0` on every row in this build.
4. **De-duplicate forks** via `session_meta.forked_from_id` (a ~3.5% turn inflation was measured on
   non-subagent threads). `forked_from_id` and `parent_thread_id` mean different things — fork
   lineage versus subagent parentage — and must not be conflated.
5. Honour `--max-sessions` and budget by **records examined, not file bytes**: a single JSONL line
   in this corpus reaches 25 MB (a base64 image) and one 70 MB file holds only 177 records, so a
   byte budget exhausts on two image-heavy sessions before reaching the text-rich ones.
6. `base_instructions` in the meta record is long and embeds environment detail — **never retain or
   surface it.**

> **Optimization, never a contract.** `${CODEX_HOME}/state_*.sqlite` has a `threads` table carrying
> `cwd`, `rollout_path`, `thread_source`, `git_origin_url` and `archived`, which answers step 2 in
> one indexed query. Open it read-only (`sqlite3.connect("file:…?mode=ro", uri=True)`, **without**
> `immutable=1` — Codex may be writing), glob `state_*.sqlite` and take the highest version, verify
> the columns exist, catch `sqlite3.OperationalError`, and fall through to the date-tree walk. The
> schema is undocumented and version-stamped in the filename. Never make it the only path.

### 2.3 User turns — read `response_item`, not `event_msg`

```jsonc
// A. PRIMARY — the turn as it entered the model's input
{"type":"response_item","payload":{"type":"message","role":"user",
  "content":[{"type":"input_text","text":"…"}]}}

// B. CORROBORATING — the literal typed prompt, on legacy sessions only
{"type":"event_msg","payload":{"type":"user_message","message":"…","local_images":[]}}
```

Form **A is the durable source.** Sessions with `session_meta.history_mode == "paginated"` — the
newest on this machine, and the direction of travel — emit **zero** `event_msg` user records.
A miner that prefers B and falls back to A is correct only by accident, and on every new session it
reads the *polluted* stream (below) with none of the wrapper handling applied. Use B only as a
de-duplication key. 99% of B records appear verbatim in the same file's A stream.

**Form A is ~39% harness-authored and must be filtered.** Measured wrapper vocabulary:

- **Drop whole:** `<recommended_plugins>`, `<system_instruction>`, `<skill>`, `<turn_aborted>`,
  `<in-app-browser-context>`, `<subagent_notification>`, `<task-notification>`,
  `<local-command-stdout>`, and the tag-less markdown forms `# AGENTS.md instructions for …` and
  `## Referenced ChatGPT conversation:`. A tag-only stripper misses the markdown ones entirely.
- **Strip the wrapper, keep the request:** `# Files mentioned by the user:`,
  `# Files pasted by the user:`, `# Context from my IDE setup:` — split at
  `## My request for Codex:` or `## My request:` and keep the tail.
- **Slash-command marker:** `[$<plugin>:<skill>](/abs/path/SKILL.md)` — feed the name to
  `signals.note_slash` and keep the trailing human text. Same for
  `<command-message>` / `<command-name>` / `<command-args>`.
- `<environment_context>` — strip, as the miner already does for Claude Code.

**Never read:** `response_item`/`message`/`role: "developer"` (766 records, 100% harness-authored —
permissions preambles, multi-agent briefs, app context); `compacted` payloads, whose
`replacement_history` re-serialises prior turns and would double-count; `turn_context`
(`user_instructions`, `developer_instructions` — config echo); and every assistant form
(`agent_message`, `role: "assistant"`).

### 2.4 Explicitly out of scope

`${CODEX_HOME}` holds SQLite databases that contain conversation data — `logs_2.sqlite`,
`thread_history_1.sqlite`, `memories_1.sqlite`, `goals_1.sqlite`, `queue_1.sqlite`. **Agentify reads
none of them in v1.1** except the `state_*.sqlite` index path in §2.2, and that only as an
optimization. Their schemas are undocumented, their size defeats the token cap, and they are live
files an app is writing to. Same hard exclusions as Claude Code: never read `auth.json`,
`transcription-history.jsonl`, `dictation-history/`, `attachments/`, `browser/`, or
`external_agent_session_imports.json`.

> **UNVERIFIED — format migration in progress.** `codex migrate-rollouts` ("Inspect or migrate legacy
> local sessions to paginated thread history") exists at 0.152.1, its destination is
> `thread_history_1.sqlite`, `codex doctor` carries a `state.rollout_db_parity` check, and a
> `background_paginated_rollout_migration` feature flag exists. Whether paginated rollouts will
> eventually move their content out of the JSONL tree entirely is unknown, and no official schema
> documentation for the rollout file exists at all. **What would confirm it:** official
> documentation of the thread-history schema, or observing a rollout file whose user turns are
> absent from the JSONL and present only in sqlite. Until then: parse defensively, never assume a
> field exists, and degrade to `history_bucket: "none"` rather than failing.

### 2.5 Degradation

If the sessions tree is absent or unreadable, emit `history_bucket: "none"` with a populated
`warnings` array and exit 0. Say plainly in the plan that the setup was derived from code and git
evidence alone, and that results improve after a week of usage (PRD §5).

---

## 3. LIST EXISTING CONFIG

Read for **structure only.** `${CODEX_HOME}/config.toml` on the verification machine contains a
plaintext API bearer token. Read section headers and key names, never values, and scrub before
anything is surfaced. Prefer `codex doctor --json`, which is redacted by design.

| Scope | Path | Artifact type | Confidence |
|---|---|---|---|
| Project | `<repo>/AGENTS.md` | index doc | **VERIFIED** — loaded; see §4.1 |
| Project | `<repo>/AGENTS.override.md` | index doc, wins over `AGENTS.md` in the same directory | **VERIFIED** — measured precedence |
| Project | `<repo>/<subdir>/AGENTS.md` | nested index doc | **VERIFIED** — loaded *in addition to* the root file when cwd is at or below that subdir; deeper wins on conflict |
| User | `${CODEX_HOME}/AGENTS.md` | global index doc | **DOCUMENTED** as read (first non-empty of `AGENTS.override.md` then `AGENTS.md`). Absent on this machine. Agentify never writes it. |
| User | `${CODEX_HOME}/config.toml` | model, MCP servers, project trust, plugins, marketplaces | **VERIFIED** |
| Project | `<repo>/.codex/config.toml` | repo-scoped config layer | **VERIFIED** — real in 3 repos here; measured to take effect only when the project is trusted |
| Project | `<repo>/.codex/hooks.json` | hooks | **VERIFIED** — real and in production use; loads as `source: "project"` |
| User | `${CODEX_HOME}/hooks.json` | hooks | **VERIFIED** to load as `source: "user"`. Agentify never writes it (§4.3). |
| Project | `<repo>/.codex/rules/*.rules` | command-approval policy | **VERIFIED** — any `*.rules` filename is picked up, not just `default.rules` |
| User | `${CODEX_HOME}/rules/*.rules` | command-approval policy | **VERIFIED** to exist and to be auto-generated by Codex when a user approves a command prefix. Agentify never writes it. |
| Project | `<repo>/.codex/agents/<name>.toml` | subagents | **VERIFIED** as a real, in-production file format (8 files in one repo here); see the loading caveat in §4.5 |
| Project | `<repo>/.agents/skills/<name>/SKILL.md` | skills | **VERIFIED** — loads with `scope: "repo"` |
| Project | `<repo>/.codex/skills/<name>/SKILL.md` | skills | **VERIFIED** — also loads with `scope: "repo"` at 0.152.1, but it is **undocumented**; prefer `.agents/skills` (§4.4) |
| User | `${CODEX_HOME}/skills/<name>/SKILL.md` | skills | **VERIFIED** — a scanned root; same `SKILL.md` shape as Claude Code |
| User | `${CODEX_HOME}/skills/.system/` | Codex's own bundled skills | **VERIFIED** — marked by `.codex-system-skills.marker`. **Never write here; never count these.** |
| User | `${CODEX_HOME}/plugins/cache/<marketplace>/<plugin>/<version>/` | installed plugins | **VERIFIED** |
| Project | `<repo>/.codex-plugin/plugin.json` | plugin manifest | **VERIFIED** as a real schema (§4.7) |
| Project | `<repo>/.git/hooks/*`, `git config --get core.hooksPath` | native git hooks | **VERIFIED** (standard git) |

**`codex doctor --json` is the preferred detection and audit primitive** (**VERIFIED**): schema-versioned
(`schemaVersion: 1`), 23 checks, exit 0, and redacted by design. `checks["config.load"].details`
yields `CODEX_HOME`, the `config.toml` path, `config.toml parse: ok`, `cwd`, the enabled feature-flag
list, `feature flag overrides`, `model` and `model provider`. `checks["mcp.config"].details` yields
server **counts** by transport and, when a server has a problem, that **server's name with its value
`<redacted>`**. Names can therefore appear; **values never do**. That is compatible with
`discover.py`'s existing names-only behaviour — preserve it.

**config.toml sections VERIFIED on the live install** (headers only — no values were read):

```toml
model = "…"
model_reasoning_effort = "…"

[features]                       # multi_agent = true, js_repl = false
[projects."/absolute/repo/path"] # trust_level = "trusted"
[mcp_servers.<name>]             # see §4.6
[mcp_servers.<name>.env]
[marketplaces.<name>]
[plugins."<plugin>@<marketplace>"]
[desktop]                        # and a large [desktop.*] theme tree
```

**`[features] hooks` is not required.** `codex features list` reports `hooks  stable  true`, and
`codex doctor --json` reports `feature flag overrides: none` while listing `hooks` among the enabled
flags — on a machine whose `config.toml` contains **no** `hooks` key at all (**VERIFIED**). Hooks are
on by default at 0.152.1. **Agentify must not write `[features] hooks = true`**; it is unnecessary
and it would mean touching a TOML file for no reason. (One real repo on this machine sets it
explicitly; that is a leftover from when the flag was gated, not evidence that it is needed.)

> `adapters/capabilities.md` currently says a generated hook "needs `[features] hooks = true`" and
> marks that UNVERIFIED. It is verified, and the answer is no. Per §4's precedence rule that line
> should be dropped; the **trust** approval it also mentions is real and must stay.

### 3.1 Maturity counting on this target

Same resolution as the Claude Code adapter: count user-scoped and project-scoped **separately**,
never union them, and **let neither gate anything**. There is no audit-only mode (`coverage.md` §6),
and `${CODEX_HOME}` is not this repo's setup — it covers no candidate and is reported only so a
same-name collision can be named (`blueprint.md` §2.1, `coverage.md` §6.1)
(`coverage.md` §6.1). `provenance.maturity_basis` is one line of context for the plan; `counts` is
the de-duplication number. The counting traps below still matter, because a wrong count still
produces wrong de-duplication and a wrong sentence in the plan.

Three counting traps are specific to Codex and all three were measured here:

1. **Most entries under `${CODEX_HOME}/skills/` are not skills.** 63 entries; **53 are symlinks**
   into one checked-out repo's `.claude/skills` tree, 1 is an empty directory, and one entry is the
   hidden `.system/` tree of Codex's own bundled skills. `ls | wc -l` reads 63 where the honest
   count of the user's own authored skills is about 9. Count only real, non-empty directories
   containing a `SKILL.md`, and exclude `.system/`.
2. **A Codex config can be a copy of the Claude Code config.** Codex ships an external-agent config
   importer (`externalAgentConfig/detect` and `externalAgentConfig/import`, with an import-target
   enum covering AGENTS.md, config, skills, plugins, MCP servers, subagents, hooks and memory).
   Three skills present in both `~/.codex/skills/` and `~/.claude/skills/` on this machine were
   verified **byte-identical**. So: do not count the same artifact twice across two targets, and do
   not propose writing a skill the user already has via import.
3. **Plugin caches are separate stores, not shared artifacts.** Both tools use
   `<home>/plugins/cache/<marketplace>/<plugin>/<version>/`, but the installed *versions* differ, so
   no path is shared. Codex keeps its plugin state in `config.toml` (`[marketplaces.*]`,
   `[plugins."x@y"]`) rather than in the JSON registries Claude Code uses.

---

## 4. EMIT

> **Supported / unsupported verdicts live in `adapters/capabilities.md`**, which phase 6 reads to
> write the plan's capability notes without opening this file. This section owns the *emit
> mechanics* — exact paths, formats, file bodies, merge rules. **Change a verdict or a substitution
> here and you must change `capabilities.md` in the same edit**, or phase 6 promises the user
> something phase 7 does not build. Where the two disagree, this file is right about the mechanics
> and `capabilities.md` must be corrected to match.

Build order: **rules → hooks → permissions → skills → subagents → MCP → index doc last.** The index
doc is last because its tables enumerate what was written (`blueprint.md` §9). On this target the
permissions step and the rules step produce the **same file** — `.codex/rules/agentify.rules` is
both the command policy and the permission surface, so it is assembled once, validated once, and
written once after every approved policy is known (§4.2.2). There is no plugin manifest step: it is
not an artifact type (§4.7). On this target **nothing is substituted.** MCP servers are **Draft** (§4.6) and prose
conventions are a **Convention** wired from the index doc (§4.2.1) — exactly as on Claude Code.
Everything else has a native, repo-scoped, committable home. Any wording elsewhere in agentify that
still describes Codex hooks or subagents as unsupported substitutions is stale and must be fixed
rather than repeated to the user.

Universal rules: never overwrite; every generated file that has a comment syntax carries the
`agentify-id` / `agentify-version` / `agentify-generated` / `agentify-evidence` block and the line
`Safe to delete or edit.`; bodies come from `templates/*.tmpl`; everything lands on branch
`agentic-setup/<yyyy-mm-dd>` or stays staged.

`<plan-dir>` means the configured plan/report directory — `docs/agentic-setup/` by default. The
`.claude/agentic-setup/` alternative is **not offered on this target**; a `.claude/` directory in a
Codex repo is misleading.

**Never write to `${CODEX_HOME}` except where §4.4 says the user explicitly opted in.** The whole
point of the repo-scoped `.codex/` layer is that agentify never needs to.

### 4.1 Index doc — `AGENTS.md`

| | |
|---|---|
| Project path | `<repo>/AGENTS.md` |
| Global variant | `${CODEX_HOME}/AGENTS.md` — **DOCUMENTED** as read. Agentify never writes it: a global index doc applies to every repo on the machine, which contradicts evidence-derived-for-this-repo. |
| Format | Plain Markdown. No frontmatter. |

**Load semantics, all VERIFIED in the scratch environment unless noted:**

- Per directory, Codex takes **at most one** file, in the order `AGENTS.override.md` →`AGENTS.md` →
  any name in `project_doc_fallback_filenames`. An `AGENTS.override.md` at the repo root suppressed
  the sibling `AGENTS.md` entirely.
- The chain runs from the project root (`project_root_markers` defaults to `[".git"]`, **DOCUMENTED**)
  **down to the cwd**. With cwd at the root, only the root file loaded; with cwd at `<repo>/sub`,
  both `<repo>/AGENTS.md` and `<repo>/sub/AGENTS.md` loaded. Files concatenate root-downward and
  **deeper files win on conflict** (**DOCUMENTED**; the concatenation order was observed).
- Direct system/developer instructions outrank `AGENTS.md` (**DOCUMENTED**).
- **There is no import or include mechanism.** Nothing equivalent to Claude Code's `@path`. Cross-file
  composition happens only through the nested-directory chain and through prose pointers, which are
  model-followed, not loaded. Agentify's pointer approach is therefore the right one here.

**Codex does not read `CLAUDE.md` by default.** `project_doc_fallback_filenames` defaults to `[]`.
Measured: with a `CLAUDE.md` containing a marker line and no `AGENTS.md`, the marker never reached
the model; adding `project_doc_fallback_filenames = ["CLAUDE.md"]` made it appear. **A repo carrying
only `CLAUDE.md` gives Codex nothing.** Three consequences:

1. If both targets are selected, `AGENTS.md` must be written too — or the two files unified by
   symlink.
2. The symlink case is the only zero-config way one physical file serves both agents.
3. `project_doc_fallback_filenames = ["CLAUDE.md"]` may be offered in the report as a **user-applied**
   config line, never written by agentify. It is a `config.toml` key and §4.6 explains why agentify
   does not edit that file casually — including the exact way this key silently fails to apply.

**Merge — one delimited block, rewritten in place on rerun:**

```markdown
<!-- agentify:begin id=index-doc-section -->
<!--
agentify-id: index-doc-section
agentify-version: 1
agentify-generated: 2026-09-05
agentify-evidence: <one line, with counts>
Safe to delete or edit.
-->

## Agentic setup
…
<!-- agentify:end id=index-doc-section -->
```

**The marker spelling is `agentify:begin` / `agentify:end`, everywhere, with no synonym.**
`templates/index-doc-section.md.tmpl` emits exactly that, and it is what `SKILL.md` and the plan
template document. `verify_artifacts.py` also accepts `agentify:start` and a few other spellings, but
only so a rerun can still find a block written by an older agentify — never emit one.

**Symlink case (VERIFIED in the wild).** `CLAUDE.md -> AGENTS.md` symlinks are common. Resolve with
`realpath`, append to the **physical** file exactly once, and name that file in the plan. If both a
real `CLAUDE.md` and a real `AGENTS.md` exist as separate files and both targets were selected, write
the section to each — generate it once, and state in the report that the two must be kept in sync by
hand.

**Size budget — check it, because overrun is silent.** `project_doc_max_bytes` defaults to **32768**
and it is a **shared budget across the whole chain**; discovery stops adding files at the cap and the
binary's own log line is `project doc exceeds remaining budget; truncating` (**DOCUMENTED**, default
confirmed in a real repo config). Appending agentify's section to an already-large `AGENTS.md` can
therefore silently drop the tail *or* drop deeper nested files. **Phase 8 measures the post-write
byte size of every file in the chain, summed, against 32768** — not just the one file written.

The attribution footer goes here (placement 2 of 3).

### 4.2 Rules — two different things, do not conflate them

Codex has a native `rules/` directory, and it is **not** the analogue of `.claude/rules/*.md`.

#### 4.2.1 Prose conventions — **Convention.** Inline in `AGENTS.md`, or a file it points at

Codex has no prose-rules load path — nothing here walks a directory of convention documents
(**VERIFIED**, `codex debug prompt-input`). **This is a real difference from Claude Code, and an
earlier version of this paragraph got it backwards.** Claude Code walks `.claude/rules/` natively and
recursively, loading an unscoped rule at session start and a `paths:`-scoped one the moment a
matching file is read — proved there by two live headless sessions. `capabilities.md` records the
Rules-prose row as **Native** for Claude Code and **Convention** for Codex, and that split is right.
Do not describe this target's pointer mechanism as something both targets share: on Codex the
`AGENTS.md` pointer is the load path, on Claude Code it is a nicety for humans, and a plan that tells
a Claude Code user their rule only works because the index doc points at it is telling them something
untrue.

- **Short rules (≤ ~15 lines) and anything that must always apply:** inline them in the `AGENTS.md`
  agentify section under a `### Conventions` heading. The index doc is the only prose load path this
  target has, so putting the rule there is not a compromise — it is the mechanism.
- **Long or path-scoped rules:** one file per rule at `<plan-dir>/rules/<kebab-name>.md`, with the
  agentify ID block in frontmatter, **plus** a pointer line in the `AGENTS.md` section:
  ``Before changing files under `src/db/**`, read `docs/agentic-setup/rules/db-access.md`.``

Honest framing for the plan and the report, **stated for this target only**: on Codex an
unreferenced rule file does nothing at all, so the rule and its `AGENTS.md` pointer are one artifact
— built in one step, and the reference verified in phase 8, where an unreferenced file is a fail.
The reason is **not** "the format is unverified": it is that Codex's rules system governs command
permissions, not conventions. Do not generalize this sentence to Claude Code, which loads its own
rules directory without a pointer; `capabilities.md`'s Rules note carries both halves, already
separated, and phase 6 pastes the one that matches the target.

#### 4.2.2 Command policy — `<repo>/.codex/rules/<name>.rules` — **Native, and better than a git hook**

`*.rules` files are a **Starlark execution-policy language** that decides which commands Codex may
run. This is the analogue of Claude Code's permissions allowlist, not of its rules directory. The
user-global `${CODEX_HOME}/rules/default.rules` is auto-generated by Codex when the user approves a
command prefix; **agentify never writes it.** The repo-scoped file is fair game.

```starlark
# <repo>/.codex/rules/agentify.rules
# agentify-id: forbid-npm
# agentify-version: 1
# agentify-generated: 2026-09-05
# agentify-evidence: 6 corrections across 4 sessions telling the agent to use bun, not npm
# Safe to delete or edit.
prefix_rule(
    pattern = ["npm"],
    decision = "forbidden",
    justification = "This repo uses bun. Re-run the command with `bun` instead of `npm`.",
    match = ["npm install", "npm run build"],
    not_match = ["bun install"],
)
```

Grammar, **VERIFIED** by running `codex execpolicy check` against generated files:

| Element | Status |
|---|---|
| `prefix_rule(...)` | the rule constructor. `suffix_rule` does not exist (`Variable 'suffix_rule' not found`). |
| `pattern = [...]` | required; a list of command tokens. A **nested list is an alternation** — `["git","push",["--force","-f"]]` matched `git push --force`. |
| `decision = "allow" \| "prompt" \| "forbidden"` | exactly these three. `"ask"` and `"deny"` are load errors: `invalid decision: ask`. Most restrictive wins when several rules match (**DOCUMENTED**). |
| `justification = "…"` | free text, surfaced in the decision. Put the evidence sentence here. |
| `match = [...]` / `not_match = [...]` | **self-tests, and they are enforced at load time.** A `match` example that no rule matches is a hard load error (`expected every example to match at least one rule … unmatched examples: […]`). Always emit both — they turn the rule into its own regression test. |
| Filename | any `*.rules` under `<repo>/.codex/rules/`. Not filename-specific. |
| `#` comments | plain-text file, so the agentify ID block goes in header comments exactly as shown. |

**The hazard, and it is severe: a malformed `.rules` file is a fatal startup error, not a skipped
file.** Measured — with a bad `decision` value in `<repo>/.codex/rules/broken.rules`, `codex exec`
refused to start at all: `Error loading rules: … invalid decision: ask`. A generated rules file that
does not parse **bricks the user's Codex sessions in that repo.** Therefore:

1. **Validate before writing into the repo.** Write to a temp path, run
   `codex execpolicy check --rules <temp> -- <a command the rule should catch>`, require exit 0 and
   a `matchedRules` entry with the expected `decision`, then `os.replace()` into place. If no Codex
   binary resolved (§1.3), **do not write the file** — emit it to `<plan-dir>/` as a draft with a
   needs-you item instead. This is the one artifact type where "write it and let the user find out"
   is not acceptable.
2. **One agentify-owned file, never a merge.** Write `<repo>/.codex/rules/agentify.rules` and own it
   whole. If a file of that name exists without the agentify ID block, do not touch it — write
   `agentify.rules.proposed` and record a needs-you item.
3. **Trust-gated** (§0.2) and, per the docs, **experimental and subject to change**. Say both in the
   plan.
4. **Prefix matching only, not semantics.** `prefix_rule(pattern=["npm"])` does not catch
   `npx`, `pnpm`, or `npm` invoked through a script. Say what it does and does not cover.

This is the right home for forbidden-command evidence — an in-session gate that fires before the
command runs, which is strictly better than a commit-time git hook for that class of rule.

### 4.3 Hooks — **Native.** `<repo>/.codex/hooks.json`

Codex has a first-class hook system. It is a near-superset of Claude Code's.

| | |
|---|---|
| Config path | `<repo>/.codex/hooks.json` — repo-scoped, committable, JSON (stdlib-writable), reversible by deleting the file |
| Script path | `<repo>/.codex/hooks/<kebab-name>.sh`, mode `0755` |
| Never write | `${CODEX_HOME}/hooks.json` — a user-global hook fires in every repo, is not evidenced by this repo, and the project layer removes any need for it |

**Exact shape (the three-level structure is VERIFIED — this file loaded and was reported back by
`hooks/list`. The `matcher` VALUE below was updated 2026-09-15 to the documented tool name and has
not been re-run against a live build; see "Matchers"):**

```json
{
  "description": "Agentify-generated Codex lifecycle hooks.",
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "^(Bash|exec_command|shell_command|local_shell|exec|run)$",
        "hooks": [
          {
            "type": "command",
            "command": "\"$(git rev-parse --show-toplevel)/.codex/hooks/enforce-bun.sh\"",
            "timeout": 5,
            "statusMessage": "Checking package manager"
          }
        ]
      }
    ]
  }
}
```

Three levels, exactly as in Claude Code's `settings.json`: **event → array of matcher groups → each
group's own `hooks` array of handlers.** Two levels named `hooks`. Getting this wrong produces a file
that parses and does nothing.

#### Event names — all 12 VERIFIED as loadable

`PreToolUse` · `PermissionRequest` · `PostToolUse` · `PreCompact` · `PostCompact` · `SessionStart` ·
`SessionEnd` · `UserPromptSubmit` · `SubagentStart` · `SubagentStop` · `Stop` · `Interrupt`

All twelve were written into a `hooks.json` and all twelve came back from `hooks/list`. Four have no
Claude Code equivalent: `PermissionRequest`, `PostCompact`, `SubagentStart`, `Interrupt`. **For every
hook agentify would emit on Claude Code, Codex has an equivalent event.**

**Spelling is exact CamelCase and a wrong name fails silently.** A `hooks.json` whose only event was
`NotAnEvent` loaded with **zero hooks, zero warnings and zero errors** — no diagnostic anywhere.
Emit only from the list above, and let phase 8 confirm the hook came back from `hooks/list`.

#### Matchers

`matcher` is a **regex over the tool name** (**DOCUMENTED**; corroborated by production files here
using `^Bash$` and `^(apply_patch|Edit|Write)$`, which are only meaningful as regexes) and may be
omitted or `null`, meaning "all". **Omit the key** for events that have no tool rather than emitting
`""` — the schema types it as nullable, and an omitted matcher was **VERIFIED** to come back as
`matcher: null`. For `SessionStart` the matcher is documented to match the start source
(`startup` / `resume` / `clear` / `compact`) and for `PreCompact` / `PostCompact` the trigger
(`manual` / `auto`); `UserPromptSubmit`, `Stop` and `Interrupt` ignore it (**DOCUMENTED**).

**The canonical tool names are `Bash` and `apply_patch` (DOCUMENTED).** Codex's hook documentation
(`https://learn.chatgpt.com/docs/hooks`) names `Bash` for shell execution and `apply_patch` / `Edit` /
`Write` for file edits, and that is what a current build dispatches a hook under.

**Two different lists, and conflating them is a real defect this file shipped.** The names in this
machine's own *rollout and conversation records*, by frequency, are `exec`, `exec_command`,
`apply_patch`, `shell_command`, `send_message`, `js`, `run`, `update_plan`, `request_user_input`,
`write_stdin`, `view_image`, plus the multi-agent tools (`spawn_agent`, `wait_agent`, `list_agents`,
`followup_task`, `interrupt_agent`). Those are tool names **as a transcript records them**. Earlier
revisions of this section read that list as the hook dispatch vocabulary and stated outright that
there is no `Bash` — so agentify emitted shell matchers that excluded the one name a current Codex
actually sends, and every generated shell guardrail was inert. Corrected 2026-09-15.

Emit one matcher that accepts **both** vocabularies, canonical name first, and say in the plan that
the vocabulary beyond the canonical names is build-dependent:

| Intent | Matcher to emit |
|---|---|
| Any shell command | `^(Bash\|exec_command\|shell_command\|local_shell\|exec\|run)$` |
| Any file edit | `^(apply_patch\|Edit\|Write)$` (the last two are harmless and cover imported/dual-target setups) |
| Prompt-, session- and stop-time events | omit `matcher` entirely |

Keep the regex **anchored**: `^(…)$`, so `Bashful` or `prebash` cannot match as a substring. The
generated script's own `case` filter must carry the **same alternation** minus the anchors — a `case`
pattern is whole-string, so the two stay equivalent. Over-matching a name that is never sent costs
one no-op `case` arm; under-matching the name that is sent costs the entire guardrail.

> **UNVERIFIED — the exhaustive tool-name list, and live dispatch.** Beyond `Bash` and `apply_patch`
> the list is empirical, not a published enum, and no tool-name enum exists in the binary's generated
> schemas. Separately: that the matcher above **selects a real tool call in a running session** has
> **not** been observed here — what has been established is that it matches the documented name and
> that the generated script returns the expected decision on a fixture (§8). **What would confirm the
> rest:** an official tool reference for the target build, `payload.name` of `function_call` /
> `custom_tool_call` records across fresh sessions on that build, or a `PreToolUse` hook that dumps
> its stdin during a live turn. Because the list is open, **the hook script must also check
> `tool_name` from its stdin and exit 0 quietly when it does not recognise the shape.** A permissive
> matcher plus a defensive script is correct; a narrow matcher that silently never fires is the
> failure mode to avoid.

#### Handler keys — and the one that silently does nothing

| Key | Status |
|---|---|
| `type` | required. `"command"` (**VERIFIED**) and `"mcp_tool"` (**VERIFIED** to load, reported back as `handlerType: "mcpTool"`, requires `server`, `tool`, `input`). The protocol schema also names `prompt` and `agent` handler types. **Agentify emits `"command"` only** — it is the simplest, the most portable, and the only one testable from a shell. |
| `command` | required for command handlers. |
| `timeout` | **seconds.** `"timeout": 5` was reported back as `timeoutSec: 5`. |
| `timeoutSec` | **do not emit — it is silently ignored.** A handler written with `"timeoutSec": 5` came back with `timeoutSec: 600`, the default. The documentation lists both spellings; only `timeout` actually applies at 0.152.1. |
| `statusMessage` | **VERIFIED** — a short progress line shown in the UI. Emit it; it is how the user sees the hook working. |
| `async` | **VERIFIED** to load (`"async": true` → `async: true`). Not emitted by agentify in v1.1: an async hook cannot block, which is the whole point of the hooks agentify builds. |
| `additionalContextLimit`, `commandWindows`, `if`, `shell` | present in the schema; not emitted. |
| Default timeout | **600 seconds** when `timeout` is absent (**VERIFIED**). Always emit an explicit `timeout`. |

#### Hook I/O contract

**stdin** is a JSON event object carrying (from the binary and corroborated by a production hook's
own `jq` reads): `session_id`, `turn_id`, `cwd`, `transcript_path`, `agent_transcript_path`,
`hook_event_name`, `model`, `permission_mode`, `trigger`, `reason`, `tool_name`, `tool_input`,
`tool_use_id`, `tool_response`, `agent_id`, `agent_type`, `last_assistant_message`, `prompt`,
`stop_hook_active`. Generated scripts must read stdin defensively and must never crash on an
unexpected shape — an exception in a hook is a broken session.

**`tool_input` and the one field that carries two languages (DOCUMENTED).** `tool_input` is typed
`true` — i.e. ANY — in the pre-tool-use / post-tool-use / permission-request schemas, so its shape is
the tool's own arguments; it is **not** Claude Code's `{file_path: …}`. The documentation states that
**`Bash` and `apply_patch` both use `tool_input.command`**: for `Bash` it is the shell string, and for
`apply_patch` it is **the raw patch text**. MCP and other local function tools pass their arguments
directly inside `tool_input`.

So the same field name means shell for one tool and a patch for another, and **`tool_name` is what
disambiguates them.** A hook that reads `tool_input.command` as shell text unconditionally extracts
zero file paths from every patch — which is exactly what `templates/codex-hook.sh.tmpl` did before
2026-09-15, and it silently un-scoped every file-scoped guardrail (a rule like "never edit
`db/migrations/`" stopped being tied to the files being edited, and the empty-path fallback then ran
the check against *everything*, denying edits outside the guarded scope as well as missing edits
inside it).

For `apply_patch`, parse `tool_input.command` with the patch grammar and collect **every** affected
path: `*** Add File:`, `*** Update File:`, `*** Delete File:` and `*** Move to:`. A rename is the
`Update File:` / `Move to:` **pair** and both sides count. Paths are relative to the session's
top-level **`cwd`** (older object payloads also carry a per-call `workdir`); resolve against it so a
repo-root glob still matches a patch authored from a subdirectory, and keep the as-sent spelling too.
The freeform spelling — `tool_input` being the bare patch string, as the rollouts record it — must
keep working alongside the documented object form.

**Blocking is expressed in JSON on stdout, and this is the difference from Claude Code that matters
most.** A production `PreToolUse` hook on this machine blocks by printing

```json
{ "hookSpecificOutput": { "hookEventName": "PreToolUse",
                          "permissionDecision": "deny",
                          "permissionDecisionReason": "BLOCKED: …use bun, not npm. Run: bun install" } }
```

and **exiting 0**. `permissionDecision` accepts `allow` / `deny` / `ask`. Other stdout fields:
`continue`, `stopReason`, `systemMessage`, `additionalContext`, `decision`, `reason`,
`suppressOutput`, and per-event `updatedInput` / `updatedPermissions` / `updatedMCPToolOutput`.
`permissionDecisionReason` is the text the model acts on — **write it as an instruction, not a log
line.**

Exit codes: **0** = success, stdout parsed as JSON if it parses and otherwise as text (for
`UserPromptSubmit`, plain-text stdout becomes `additionalContext`); **2** = blocking with stderr as
the reason (**DOCUMENTED**, the same contract as Claude Code). **Emit the JSON form, not exit 2** —
it is what production Codex hooks on this machine actually do, and it carries a structured reason.

> **UNVERIFIED — exit codes other than 0 and 2, and the `SessionEnd` matcher target.** The docs
> specify only 0 and 2, and their matcher table omits `SessionEnd`. Claude Code treats other non-zero
> codes as a non-blocking error; whether Codex does is unconfirmed. **What would confirm it:** a hook
> that exits 1 and 3 in a live session, and a `SessionEnd` hook with a deliberately non-matching
> matcher. Agentify's generated scripts therefore **only ever exit 0**, and express every decision in
> JSON.

#### A generated hook is INSTALLED, not ACTIVE — the trust gate

Every hook written by the scratch probe came back from `hooks/list` with
**`"trustStatus": "untrusted"`** and `"enabled": true`. Codex tracks trust by a **hash of the hook
definition** (`currentHash` is part of each hook's metadata), so editing a trusted hook re-arms the
prompt. The user reviews and trusts hooks with the in-session **`/hooks`** command.

This changes the verification story and both the plan and the report must say so:

- Phase 8 can prove the JSON loads, the event is recognised, and the script runs on a fixture. It
  **cannot** prove the hook is armed. Never claim it is live.
- The report's manual checklist must carry: *"Run `/hooks` in Codex and trust the new hooks; until
  you do, they are installed but do not run."*
- **Never emit or suggest `--dangerously-bypass-hook-trust`.**
- On a managed/enterprise machine, `allow_managed_hooks_only` makes Codex skip user, project, session
  and plugin hooks entirely (**DOCUMENTED**). If a hook never appears in `hooks/list` despite being
  present and the project being trusted, say this is the likely cause rather than guessing.

#### Merge rule — read, splice, rewrite. Never replace.

1. Read `<repo>/.codex/hooks.json`. If absent, create it with `description` and `hooks` and nothing
   else.
2. Parse as JSON. **If it does not parse, stop.** Do not repair, do not overwrite. Write the intended
   content to `<repo>/.codex/hooks.json.agentify-proposed` and record a needs-you item.
3. Ensure `hooks` exists and `hooks[<Event>]` is an array.
4. **Idempotency first.** Look for a handler object anywhere under that event whose `command`
   contains `/.codex/hooks/<name>.sh`. Found: replace **that one object** in place and stop. Never
   append a second copy.
5. Only if step 4 found nothing: find a matcher group whose `matcher` equals yours and **append your
   handler to that group's `hooks` array** — groups are routinely shared with hooks the user wrote.
   If there is no such group, **append a new matcher group** to the event array.
6. Never touch another event, another group, another handler, or the top-level `description` if the
   user wrote one. Preserve the file's existing indentation and trailing newline.
7. Record `pre_existing_sha256` (the hash **before** the merge) and `restore: span` on the artifact's
   manifest entry, and record the merge as
   `["hook_command", "<the command line you wrote>", "<Event>"]` — **three elements.** The event is
   half of the identity: the same script can be registered under more than one event, so the command
   alone does not say which registration is agentify's, and the undo refuses to guess rather than
   removing the wrong one. `references/build-and-verify.md` §5.3a.
8. Write to a temp file in the same directory and `os.replace()` it into place.

#### Idempotency without markers — the identity is the whole command path plus the event, and adding metadata will break the file

**`hooks.json` rejects unknown keys at the top level.** Measured, with a `_agentify` object added
beside `hooks`:

```
failed to parse hooks config …/.codex/hooks.json: unknown field `_agentify`,
expected `description` or `hooks` at line 3 column 13
```

and **the entire file then loaded zero hooks** — surfaced only as a `warnings` entry in `hooks/list`,
never as an error the user sees. The accepted top-level keys are exactly **`description`** and
**`hooks`**. So:

- **Never write an `_agentify` block into `hooks.json`.** Unlike `.mcp.json` on Claude Code, there is
  no safe top-level home for it. This is the single easiest way to silently disable every hook in a
  repo.
- Unknown keys *inside a handler object* were tolerated at 0.152.1 (a handler carrying
  `"_agentify_id"` loaded normally). **Do not rely on that** — the top level is strict, the asymmetry
  is undocumented, and a future build tightening it would brick the file. Agentify emits no metadata
  key anywhere in `hooks.json`.
- **The identity is the whole command path, plus the event it is registered under**, exactly as in
  `adapters/claude-code.md` §4.3: a nested `hooks[].command` resolving to `/.codex/hooks/<name>.sh`
  under a named event. **A basename is never an identity** — an unrelated `tools/block-npm.sh` the
  user wrote shares its basename with a generated `.codex/hooks/block-npm.sh`, and an undo that
  matched on basename removed both. The un-merge normalizes the repo-root spellings agentify emits
  and compares the whole string. Provenance lives in the hook script's own header comments and in
  `<plan-dir>/build-manifest.json`.
- `description` is an accepted key and agentify may set it **only when it created the file**. If the
  file already exists, leave whatever `description` is there alone.
- The undo for this file is the **JSON un-merge script** in `references/report-template.md` §3.1,
  keyed on the normalized command path and the event — the same key as the Claude Code settings merge. The marker-removal
  script would find no marker, print `SKIP`, exit 0, and leave the hook registered forever.

#### The hook script

```bash
#!/usr/bin/env bash
set -euo pipefail
# agentify-id: enforce-bun
# agentify-version: 1
# agentify-generated: 2026-09-05
# agentify-evidence: 6 corrections across 4 sessions telling the agent to use bun, not npm
# Safe to delete or edit.

input="$(cat)"
tool="$(printf '%s' "$input" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("tool_name") or "")' 2>/dev/null || true)"

# tool_input.command is the shell string for Bash and the PATCH TEXT for apply_patch, so a
# command hook must check the tool name first or it will read a patch as a command.
case "$tool" in
  Bash|exec_command|shell_command|local_shell|exec|run) ;;
  *) exit 0 ;;
esac

cmd="$(printf '%s' "$input" | python3 -c 'import json,sys;print((json.load(sys.stdin).get("tool_input") or {}).get("command",""))' 2>/dev/null || true)"

case "$cmd" in
  npm\ *|*\ npm\ *)
    printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"This repo uses bun. Re-run as: bun install"}}'
    exit 0 ;;
esac
exit 0
```

Rules for every generated hook script:

- `#!/usr/bin/env bash`, then `set -euo pipefail`, then `chmod 0755`.
- Reference it from `hooks.json` as `"$(git rev-parse --show-toplevel)/.codex/hooks/<name>.sh"`,
  quoted — **VERIFIED in production use on this machine**, and it is what makes the hook work
  regardless of the process's cwd. Never write an absolute `/Users/...` path into a committed file.
- **Always exit 0.** Express every decision in JSON (see the exit-code UNVERIFIED note above).
- Unknown or unexpected stdin ⇒ print nothing, exit 0. Never let a hook break a session.
- Fast: target under 2 seconds, and always set an explicit `timeout`.
- Never destructive: never amend, reset, stash, rewrite history, or push.

#### Native git hooks — a secondary, opt-in artifact

Repo hooks now cover in-session enforcement, so git hooks are no longer the substitution. They remain
worth offering for one reason: they are the only gate that survives **outside** a Codex session. Emit
them only when the evidence is specifically commit-time and the user opts in. All of the following
rules are mandatory and unchanged:

1. **Explicit approval, asked separately.** Git hooks run on every commit, forever, outside the
   agent. Ask as its own interview question with the default set to **no**. Approving the plan is not
   consent for this.
2. **Never overwrite an existing hook.** If `.git/hooks/pre-commit` exists without an agentify
   marker, do not touch it: write `.git/hooks/pre-commit.agentify` (non-executable) and put the
   two-line snippet in the report's needs-you section. If it exists **with** the marker, rewrite only
   between the markers.
3. `#!/usr/bin/env bash`, `set -euo pipefail`, `chmod 0755`.
4. **Idempotent markers**, since shell has no frontmatter, and the dry-run escape hatch:
   ```bash
   # agentify:begin id=pre-commit-typecheck
   # agentify-id: pre-commit-typecheck
   # agentify-version: 1
   # agentify-generated: 2026-09-05
   # agentify-evidence: 9 sessions ended with a failing typecheck; "run typecheck" asked 5 times
   # Safe to delete or edit.
   [ -n "${AGENTIFY_DRYRUN:-}" ] && exit 0     # required: makes the hook smoke-testable
   bun run typecheck
   # agentify:end id=pre-commit-typecheck
   ```
   The `AGENTIFY_DRYRUN` early exit is **required in every generated git hook** — it is what lets
   phase 8 prove the hook runs without running the user's build.
5. **Respect `core.hooksPath`.** Run `git config --get core.hooksPath` first; if set (husky, lefthook
   and similar set it), write into **that** directory following its conventions and say so in the
   plan. Writing to `.git/hooks/` when `core.hooksPath` is set produces a hook that silently never
   runs.
6. **`.git/hooks/` is not committed and not shared.** Say so in the report: teammates get nothing.
   Prefer an existing hook manager so the team benefits.
7. Git exit-code semantics: non-zero **aborts** the operation, and the message goes to the **human**,
   not the model. Write failure messages for a human, with the exact fix command.
8. Uninstall path in the report: `rm .git/hooks/<name>`, or delete between the markers.

### 4.4 Skills — **Native.** `<repo>/.agents/skills/<name>/SKILL.md`

| | |
|---|---|
| Project path | `<repo>/.agents/skills/<kebab-name>/SKILL.md` — committable, repo-scoped, team-shared |
| User path | `${CODEX_HOME}/skills/<kebab-name>/SKILL.md` — **opt-in only** |
| Directory name | Must equal the frontmatter `name`. |

`skills/list` against a scratch repo returned a skill written to `<repo>/.agents/skills/` with
`"scope": "repo"`, **and it loaded whether or not the project was trusted** — repo skills are not
behind the trust gate at 0.152.1 (**VERIFIED**; the docs do not state this either way, so treat the
trust-independence as build-specific rather than a promise).

**Skill roots that are scanned** (in the order Codex itself reported them in a live session's
`world_state`): `${CODEX_HOME}/skills`, `$HOME/.agents/skills`, `${CODEX_HOME}/skills/.system`, every
installed plugin's `skills` directory, and the repo-level `.agents/skills`. `/etc/codex/skills` is
**DOCUMENTED** as an admin root.

`<repo>/.codex/skills/<name>/SKILL.md` **also** loaded with `scope: "repo"` in the scratch probe
(**VERIFIED** — both probe skills came back from `skills/list` in the same call), but it does not
appear in the published scope table and no repo on this machine uses it. **Prefer `.agents/skills`
and write only there** — it is the documented, cross-tool path, and it is the one a Claude Code
install can share.

> **Two corrections to `adapters/capabilities.md`, applied 2026-09-15** under the precedence rule at
> the top of §4. (a) It said `.codex/skills/` "is not a load path" — wrong on the mechanics; the
> Skills row now says *not the path agentify writes*, and gives the real reason (undocumented, unused
> in the wild). The build behaviour is unchanged either way, but the reason stated to the user has to
> be true. (b) It marked *"whether `<repo>/.agents/skills` is subject to the `.codex/` project-trust
> gate"* as UNVERIFIED — it is verified, and the answer is **no**: repo skills loaded under
> `trusted`, under `untrusted`, and with no `[projects]` entry at all. Its trust note now states that
> exception instead of saying the repo-scoped layer is gated "together".

**Frontmatter — exactly two required fields:**

```markdown
---
name: add-api-endpoint
description: Scaffolds a new API endpoint in this repo — route file, Zod request/response schemas, service call, integration test, and OpenAPI entry — following the existing pattern in src/api/. Use when the user asks to "add an endpoint", "add a route", "new API for X", or "expose X over the API". Not for editing an existing endpoint's logic; that is ordinary editing.
agentify-id: add-api-endpoint
agentify-version: 1
agentify-generated: 2026-09-05
agentify-evidence: 7 requests across 5 sessions matching "add endpoint <resource>"
---
<!-- Safe to delete or edit. -->
```

| Key | Required | Notes |
|---|---|---|
| `name` | yes | kebab-case, must equal the directory name. **VERIFIED.** |
| `description` | yes | One paragraph, third person, under 1024 chars. See below — the highest-leverage field in the build. |
| `version`, `allowed-tools`, `user-invocable` | no | **VERIFIED in the wild** on this machine's skills. Agentify omits them. |

Optional sibling directories `scripts/`, `references/`, `assets/`, and an optional
`agents/openai.yaml` for UI metadata and invocation policy, are **DOCUMENTED** and **VERIFIED in the
wild**. Keep `SKILL.md` under ~500 lines and push detail into siblings.

Loading is progressive disclosure: at startup Codex reads only `name` + `description` from every
installed skill, under a budget (`skills.max_context_tokens`, **DOCUMENTED** as 2% of the context
window capped at 10,000). The body loads only when the skill is selected — which is exactly why
**description authoring is the deliverable**.

**Description authoring — the formula, in full, because phase 7 opens exactly one adapter.** It is
identical on both targets (Codex uses the same name+description progressive-disclosure loading), but
**do not go and read `adapters/claude-code.md` §4.4.1 to get it.** That file is 1,280 lines; opening
it here doubles the adapter cost of the build phase for a formula that fits in a paragraph, and the
one-adapter rule is what the whole progressive-disclosure layout exists to protect.

```
<What it does: concrete verb + concrete object, naming this repo's real nouns>.
Use when <trigger condition>, or when the user says "<exact phrase>", "<exact phrase>", "<exact phrase>".
Not for <the nearest adjacent task that must NOT trigger this>.
```

1. **Third person, one paragraph, under 1024 chars.** No "I", no "you", no "this skill".
2. **Use the user's literal words**, pulled from `signals.json` — `request_shapes[].skeleton` and
   `.examples`, plus `slash_commands[].name` and `commands_requested[].command`.
3. **Name this repo's nouns.** "Adds an endpoint" is generic; "adds a route under `src/api/` with a
   Zod schema, a service call and a Vitest integration test" is specific enough that the model can
   tell whether the user's request is this or something else.
4. **Include a negative boundary** whenever another skill, subagent or plain editing is adjacent.
   "Not for X; that is Y." Mis-fires between two similar skills are the commonest failure mode.
5. **State the trigger conditions, not the implementation.** The body explains how; the description
   explains when. Never restate the name, and avoid "helps you", "assists with", "utility for".

**Naming:** kebab-case, verb-object (`add-api-endpoint`, `run-migration`, `review-pr`). Directory
name, `name` and `agentify-id` are all the same string.

**The evidence requirement is the size test, not a transcript test.** A skill is licensed by any one
of the four things `blueprint.md` §1.4 lists: `>= 3` existing instances of the thing it produces, a
`request_shapes[]` row with **`count >= 3`** (`mapping-rules.md` row 1, which also wants
`sessions >= 2` and a skeleton implying `>= 2` steps), a service the repo extends over time through a
module, or a guide the developer wrote. **Structural evidence licenses a skill on its own** — a repo
with no transcript history still gets its integration skills and `setup-manager` — and the licence,
whichever it is, ends the shortlist row as a number. Two earlier readings of this paragraph were both
wrong and are both retired: that a skill needs transcript repetition at all, and that the bar is
`count >= 2`. Two is the **rule** and **hook** bar (`mapping-rules.md` rows 4 and 5); for a skill it
is three.

**Two Codex-specific notes:**

- A `description` may be a YAML block scalar (`description: |`) in the wild. A frontmatter parser
  that assumes a single-line scalar will mis-read real skills on both targets.
- **Opt-in global writes.** If the user explicitly chooses global Codex skills in the interview,
  write `${CODEX_HOME}/skills/<name>/SKILL.md`, never overwriting an existing directory, and list
  every path written in the report's uninstall section. Because a global skill is visible in every
  repo, its description must name the repo or stack it applies to. This should be rare: the
  repo-scoped path is committable and reversible, and the global one is neither.

#### 4.4.1 `setup-manager` — the one skill every run builds

`blueprint.md` §6.3 owns why it exists and what it must contain. This is what it must know about
**this** target; copy the table into `.agents/skills/setup-manager/references/config-surface.md`
when the skill is written, rather than pointing at a file the user does not have:

| Surface | Path | Format |
|---|---|---|
| Index doc | `AGENTS.md` (`AGENTS.override.md` outranks it) | markdown; 32768-byte `project_doc_max_bytes` across the whole chain (§4.1) |
| Rules — prose | `<plan-dir>/rules/<name>.md` + an `AGENTS.md` pointer | markdown. Nothing walks a prose rules directory on this target, so the pointer **is** the mechanism (§4.2.1) |
| Rules — command policy / permissions | `.codex/rules/agentify.rules` | Starlark `prefix_rule(...)`. **Validate with `codex execpolicy check` before writing — a malformed file bricks Codex in this repo** (§4.2.2) |
| Hooks | `.codex/hooks/<name>.sh` + `.codex/hooks.json` | shell; JSON decision on stdout, **always exit 0**. `hooks.json` accepts only `description` and `hooks` — one unknown top-level key loads zero hooks (§4.3) |
| Skills | `.agents/skills/<name>/SKILL.md` (+ `references/`) | markdown + frontmatter. `.codex/skills/` loads too but is undocumented, so it is **not the path agentify writes** (§4.4) |
| Subagents | `.codex/agents/<name>.toml` | TOML; `name`, `description`, `developer_instructions` required (§4.5) |
| MCP | `.codex/config.toml` `[mcp_servers.<name>]` | TOML; `bearer_token_env_var` / `env_http_headers` / `env_vars`, never `${VAR}` (§4.6) |

Two target facts it must state up front, because they are the likeliest reason a change appears to
do nothing: **project trust** gates the entire repo-scoped layer, and **a new or edited hook is
re-armed** and needs approval through `/hooks`. Never suggest `--dangerously-bypass-hook-trust`.

Plus the four refusals — never delete or reword the user's own instructions, never touch a
symlinked or vendored artifact, keep the `AGENTS.md` tables in step with the files, re-verify after
every change — and **the inventory of what this run built**, which is why it is the **last** skill
written.

### 4.5 Subagents — **Native.** `<repo>/.codex/agents/<name>.toml`

| | |
|---|---|
| Project path | `<repo>/.codex/agents/<kebab-name>.toml` |
| Format | TOML, one agent per file, authored whole by agentify — no round-trip, no merge (§4.6 does not apply) |
| Filename stem | Should equal `name`. |

**VERIFIED as a real, in-production format:** eight such files exist in one repo on this machine, and
all eight use exactly the same six keys.

```toml
name = "pr-reviewer"
description = """
Reviews a diff for correctness, missing tests, and violations of this repo's conventions.
Returns a severity-ranked finding list with file:line anchors. Delegate when the user asks to
review a branch, a PR, or "the changes". Does not edit code.
"""
model_reasoning_effort = "high"
sandbox_mode = "read-only"
developer_instructions = '''
You are a code reviewer for this repository.
…
'''
# agentify-id: pr-reviewer
# agentify-version: 1
# agentify-generated: 2026-09-05
# agentify-evidence: 11 review requests across 8 sessions; 34% of commits touch no test file
# Safe to delete or edit.
```

| Key | Required | Notes |
|---|---|---|
| `name` | yes | The agent's identity. **DOCUMENTED** as required; **VERIFIED** present in all 8 real files. |
| `description` | yes | Drives delegation — the same authoring formula spelled out in §4.4, with the trigger being "when should the main agent hand this off", and it must state **what the subagent returns**. |
| `developer_instructions` | yes | The system prompt. Use a `'''` multi-line literal string so nothing needs escaping. |
| `model` | no | **VERIFIED in the wild.** Agentify **omits it** — a pinned model goes stale and silently changes the user's session. |
| `model_reasoning_effort` | no | **VERIFIED in the wild** (`high` observed). Emit only if the interview asked for it. |
| `sandbox_mode` | no | **VERIFIED in the wild**: `read-only`, `workspace-write` observed; the binary's enum also has `danger-full-access` and `external-sandbox`. **Emit `read-only` for any review/analysis agent** — it is the closest thing Codex has to Claude Code's `tools` restriction. Never emit `danger-full-access`. |

Mapping from a Claude Code subagent is near-direct: frontmatter `name` → `name`, `description` →
`description`, markdown body → `developer_instructions`, `model` → `model`.

**Comments.** TOML has `#` comments, so the agentify ID block goes in the file as shown. It is a
whole-file artifact agentify owns; a rerun rewrites it, and a file of that name without the ID block
is never touched (write `<name>.toml.proposed` and record a needs-you item).

**One honest caveat, and it is the only thing genuinely lost versus Claude Code: there is no
per-agent tool allowlist.** `sandbox_mode` and `mcp_servers` are the nearest equivalents. State that
in the plan. Everything the previous version of this adapter listed as lost — isolated context
window, automatic delegation, parallelism — is in fact **present**: Codex subagents run as separate
threads (60% of the rollout files on this machine *are* subagent threads), gated by
`[features] multi_agent`, which is enabled here. **A candidate whose value is context isolation no
longer fails the evidence test on this target.**

> **UNVERIFIED — that a written `.codex/agents/*.toml` is actually loaded.** The format is verified
> from eight production files and the published subagent docs, and the runtime existence of subagent
> threads is verified from the rollout corpus — but subagents are exposed through a spawn tool at
> turn time, not in the base prompt, so no read-only probe here could confirm that a *newly written*
> file is picked up (`codex debug prompt-input` does not mention it, and there is no agents-list RPC).
> **What would confirm it:** in a live Codex session in the repo, ask the model to list available
> agents or to spawn the generated one by name, then check the child rollout's `session_meta` for
> `source.subagent.thread_spawn.agent_path` pointing at the generated file. **Phase 8 must therefore
> treat the subagent as statically validated only**, and the report's manual checklist must carry
> that live check. Also unconfirmed: whether `${CODEX_HOME}/agents/` is read as a user-scoped
> location (the directory does not exist here), and whether `config_file` and `nickname_candidates`
> — names present in the binary's agent struct — are accepted in this same TOML.

### 4.6 MCP servers — TOML, and this is where stdlib-only Python runs out of road

Codex MCP configuration lives in `config.toml`. **VERIFIED shapes**, validated by writing them into a
scratch `<repo>/.codex/config.toml` and validating it with `codex --strict-config app-server`, which
parses the config and errors **before** any auth or model call (§5):

```toml
# remote / streamable HTTP
[mcp_servers.linear]
url = "https://mcp.linear.app/mcp"
bearer_token_env_var = "LINEAR_API_KEY"        # token supplied by env-var NAME
env_http_headers = { "X-Auth" = "SOME_AUTH_ENV" }
http_headers = { "X-Example" = "non-secret-value" }

[mcp_servers.linear.tools.create_issue]
approval_mode = "approve"

# local / stdio
[mcp_servers.playwright]
command = "bunx"
args = ["@playwright/mcp@latest"]
env_vars = ["PLAYWRIGHT_BROWSERS_PATH"]        # forward named env vars, values never written
startup_timeout_sec = 30
```

- `command`, `args`, `env`, `env_vars`, `url`, `http_headers`, `env_http_headers`,
  `bearer_token_env_var`, `startup_timeout_sec`, `tool_timeout_sec`, `enabled`, `enabled_tools`,
  `disabled_tools`, and `tools.<tool>.approval_mode` are **VERIFIED** as accepted keys.
- **`approval_mode` accepts exactly `auto`, `prompt`, `writes`, `approve`.** VERIFIED by the parser's
  own error on a bad value: ``unknown variant `bogus`, expected one of `auto`, `prompt`, `writes`,
  `approve` ``.
- **Use the dedicated env-var keys, never `${VAR}` interpolation.** `bearer_token_env_var`,
  `env_http_headers` and `env_vars` are documented, first-class, and take a variable **name**.
  Whether generic `${VAR}` expansion works in arbitrary `config.toml` strings is **UNVERIFIED**, and
  with these keys the question is moot. Deleting the old "if your Codex build does not expand
  environment variables here" caveat from the report is the point.

#### Can agentify merge a block into `config.toml` programmatically? Mostly no — here is the precise line

Agentify is **stdlib-only and targets Python 3.9**. `tomllib` is read-only *and* 3.11+. **There is no
TOML writer in the standard library at any version.** Hand-rolling one that preserves comments,
ordering, quoting and multi-line strings is exactly the kind of plausible-looking change that
corrupts a config file. So:

**Rule 1 — `${CODEX_HOME}/config.toml` is never modified. No exceptions.** It is user-global and
hand-maintained (15+ `[projects]` entries, marketplaces, plugins and a whole `[desktop]` theme tree on
this machine), and it **contains live credentials** — a plaintext bearer token was present. Parsing,
rewriting and re-serialising it risks relocating or leaking a secret. Encountering someone's token is
not permission to move it: never echo it, never store it, never copy it into a generated file.

**Rule 2 — the default is a draft, not a write. MCP is the one draft-only artifact on this target.**
Emit `<plan-dir>/codex-mcp.toml`, copy-paste ready, with the agentify ID block in `#` comments, and a
needs-you entry in `report.md` naming the exact destination file, the environment variables to
export, and the auth step per service. `adapters/capabilities.md` records this row as **Draft**, and
that is the verdict phase 6 puts in the plan. The reason is not squeamishness about TOML alone: the
user has to authenticate and restart Codex regardless, so writing the block finishes nothing and
buys no reversibility the draft does not already have.

```toml
# agentify-id: mcp-linear
# agentify-version: 1
# agentify-generated: 2026-09-05
# agentify-evidence: "linear" mentioned in 12 user turns across 7 sessions
# Safe to delete or edit.
# Append to <repo>/.codex/config.toml (create it if absent), then restart Codex.
# Export LINEAR_API_KEY in your shell first.

[mcp_servers.linear]
url = "https://mcp.linear.app/mcp"
bearer_token_env_var = "LINEAR_API_KEY"
```

**Rule 3 — writing the block into `<repo>/.codex/config.toml` is an explicit opt-in**, offered in the
interview and never the default, and only under the contract below. It splits in two:

- **The file does not exist.** Writing it is creating a whole file from a template, not editing one —
  repo-scoped, committable, reversible by deleting the file, holding no pre-existing secret. This is
  the safe case, and the only TOML file agentify ever authors from nothing besides
  `.codex/agents/*.toml`.
- **The file exists.** Then it is an append, and the contract is narrow, checkable, and refuses more
  often than it proceeds. TOML has one property that makes a constrained append well-defined: **a
`[table]` header ends the previous table**, so a complete table block appended at end-of-file is
self-contained. The trap is the opposite case, and it is silent. Measured:

```toml
# This DOES NOT DO WHAT IT LOOKS LIKE.
[projects."/path/to/repo"]
trust_level = "trusted"
project_doc_fallback_filenames = ["CLAUDE.md"]   # parsed as projects."…".project_doc_fallback_…
```

That file loads without complaint and the setting has **no effect**; moving the same line above the
first table header made it work. A naive "append the key to the end of the file" is therefore wrong
in the general case. So the contract:

1. **Only ever append a complete `[table]` block**, header first, keys under it. **Never append a
   bare key/value pair** to an existing file — it binds to whatever table precedes it.
2. **Refuse if the table name already exists.** Scan for `^\s*\[\s*mcp_servers\.<name>\b` and for
   `^\s*\[\s*mcp_servers\.<name>\.` — a duplicate table header is a TOML parse error, which would
   break the user's config. On collision, skip and record a skipped candidate with the reason.
3. **Refuse if the file contains a multi-line string delimiter** (`"""` or `'''`). Line-based
   scanning cannot tell a table header inside a multi-line string from a real one. Fall back to
   draft-only.
4. **Refuse if the file does not end in a newline**, or normalise it first, then append
   `"\n" + block + "\n"`.
5. **Write to a temp file in the same directory and `os.replace()`.**
6. **Validate after writing** — see §5. `codex --strict-config app-server` reports
   `unknown configuration field …` with a file, line and column and exits 1, before any auth or
   model call; on a valid config it starts and answers `initialize`. Do **not** use
   `codex --strict-config exec` for this: it validates first, but on a *valid* config it goes on to
   run a real turn. If validation fails, restore the pre-write bytes from `pre_existing_sha256` and
   record a needs-you item. **If no Codex binary resolved (§1.3), do not write at all** — go
   draft-only.
7. Record `pre_existing_sha256` and `restore: span` on the manifest entry, exactly as for
   `hooks.json`.

**Rule 4 — any refusal in Rule 3 falls back to Rule 2's draft, silently to the user but explicitly in
the plan.** The plan must name, per server, which path was taken and why, before the build starts.
There is no third option: agentify never hand-edits an existing TOML file beyond appending a whole
table under this contract, and never at all outside the repo.

**Credential convention — no exceptions:**

- **Never a literal secret.** Variable **names** only, taken from `discovery.env_var_names` — the
  analyzer never read a value and neither does the emitter.
- **The user authenticates.** Agentify never runs an auth flow, never launches a server, never tests
  connectivity (PRD §4).
- MCP server names may contain `:`, `@`, `/` and `.` as of v0.152.0 (**DOCUMENTED**) — do not
  over-validate a name the user already uses.

### 4.7 Plugin manifest — **not an artifact type**

agentify does **not** emit a plugin manifest on either target. The setup is derived from one repo's
evidence and personalized to it (`blueprint.md` §1.1 test 4), so a portable copy would be wrong
wherever it landed; the interview question that offered it is retired (`interview.md` §4.1).

The schema is kept below because **`setup-manager` must be able to answer a user who asks about
packaging**, and because it was expensive to verify — a real manifest was read from the local plugin
cache. **None of it is emitted by a run.**

```json
{
  "name": "acme-agentic-setup",
  "version": "0.1.0",
  "description": "Repo-derived skills and agents for the acme monorepo.",
  "author": { "name": "Acme Engineering", "url": "https://github.com/acme" },
  "homepage": "https://github.com/acme/agentic-setup",
  "repository": "https://github.com/acme/agentic-setup",
  "license": "MIT",
  "keywords": ["acme", "internal"],
  "skills": "./skills/"
}
```

It is the `.claude-plugin/plugin.json` schema (`name`, `version`, `description`, `author`, `homepage`,
`repository`, `license`, `keywords`) plus two Codex-specific keys, both **VERIFIED** in real
manifests: **`skills`** (a path to the plugin's skills directory) and **`interface`** (store-listing
metadata: `displayName`, `shortDescription`, `longDescription`, `developerName`, `category`,
`capabilities[]`, `websiteURL`, `defaultPrompt[]`, and policy URLs). Agentify emits the minimal form
above and **omits `interface`** — it is store-listing copy, not configuration, and whether it is
required for a non-marketplace plugin is unconfirmed.

Plugin-shipped hooks live at `<plugin>/hooks.json`, `<plugin>/hooks/hooks.json`, or
`<plugin>/.codex/hooks.json` — **all three forms VERIFIED** in the local plugin cache. Codex exports
both `$PLUGIN_ROOT`/`$PLUGIN_DATA` and `$CLAUDE_PLUGIN_ROOT`/`$CLAUDE_PLUGIN_DATA`, which is why real
cross-tool plugins reference `${CLAUDE_PLUGIN_ROOT:-$PLUGIN_ROOT}`.

Two facts to hand a user who asks about packaging, before anything else: cross-tool plugins
dual-ship `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json` from one source tree; and the
binary logs *"repository-scoped plugin migration is not allowed"*, so a manifest committed to a repo
may not be installable directly from there. **The reliably shareable unit is the committed
`AGENTS.md`, `.codex/` and `.agents/skills/` files, which a teammate gets by cloning** — which is
also what a run already produces.

---

## 5. SMOKE TEST

Phase 8 runs these. Every check is local, read-only where possible, and non-destructive. Three limits
are real and must be stated in the report rather than papered over:

- **A hook is installed, not armed** until the user trusts it via `/hooks` (§4.3).
- **A repo-scoped artifact is inert until the project is trusted** (§0.2), and the failure is silent.
- **Agentify cannot restart the user's Codex session**, so anything that needs a fresh session is a
  manual checklist item.

### 5.0 Installed, loaded, armed — assert only the first

Every row below asserts exactly one of three claims. The first is always reachable; the second is
reachable for some artifact types and not others; the third never is:

| Claim | Reachable at build time? |
|---|---|
| **installed correctly** — the file is well-formed, the script runs, the registration is where the harness will look | **always.** This is what a pass condition may assert. |
| **loaded** — Codex has it in its live registry for this repo | **per artifact, not per run** (§0.2's reachability table). Skills, the `AGENTS.md` section and a `.rules` file can be proved loaded on a fresh clone; hooks and `<repo>/.codex/config.toml` cannot, because they sit behind the trust gate. |
| **armed** — Codex will execute it | **never.** `trustStatus` comes back `"untrusted"` on everything agentify writes, in every project, always. |

A check that cannot reach its claim is recorded **`not tested — <reason>`** and becomes a numbered
needs-you step in `report.md` carrying that reason (`report-template.md` §3.2). It is never a
`fail`, it is never quietly upgraded to `pass`, and it is never made reachable by setting trust
(§0.3). A row below marked **trust-gated** is one of these.

The defect this section exists to prevent was measured: a full, correct phase 0–8 run on a fresh
clone of `unjs/h3` produced a well-formed `.codex/hooks.json` and a working hook script, and
`hooks/list` returned **zero** repo-scoped hooks — because a fresh clone has no `[projects]` entry.
Every artifact was right and the pass condition was unreachable. The contract was wrong, not the
build.

Commands below assume `CODEX="$(codex_bin)"` from §1.3. **Every check has a static fallback when no
binary resolves** — say in the report which mode ran.

| Artifact | Command / invocation that proves it loads | Pass condition |
|---|---|---|
| Project trust | `grep -F "$(printf '[projects."%s"]' "$REPO")" "${CODEX_HOME:-$HOME/.codex}/config.toml"` and read `trust_level` on the following line | **Run this first — it decides how every trust-gated row below is read.** An entry that exists and is not `"untrusted"` means those rows can assert `loaded`; missing or `"untrusted"` means they record `not tested — project not trusted` instead. Either way this is a **report item, not a build failure** — agentify never edits that file (§0.3). It is needs-you step 1, ahead of the MCP steps, because nothing else in the setup runs until it is done. |
| Index doc | `test -f "$REPO/AGENTS.md"` (resolve symlinks with `realpath` first) → `grep -cE '^[ \t]*<!--[ \t]*agentify:begin' "$REPO/AGENTS.md"` → every relative link target in the section exists → `"$CODEX" debug prompt-input` from the repo root contains a distinctive line from the section | physical file exists; marker count exactly `1`; the marker line appears in the prompt input; and **every link resolves except `<plan-dir>/report.md`, which is written later and is expected to dangle here** (`verification.md` §9.0) — re-check that one link after the report is written, and never delete it to make this check pass. `debug prompt-input` is reachable on a fresh clone (measured: a project with **no** `[projects]` entry still renders `AGENTS.md`) and only an explicit `trust_level = "untrusted"` suppresses it, which turns this row into `not tested — project explicitly untrusted`. **The grep must be line-anchored.** `index-doc-section.md.tmpl` deliberately quotes both marker strings inside backticks in the section's own "Removing this" instructions, so a plain `grep -c 'agentify:begin'` counts **2** on a correctly emitted block and this check fails on every run — measured 2026-09-05. `verify_artifacts.py`'s `_MARKER` regex is line-anchored for the same reason; match what it matches. **Count the `end` marker the same anchored way and require `1` too** — `grep -cE '^[ \t]*<!--[ \t]*agentify:end' "$REPO/AGENTS.md"` — and require the begin line to come first. Anchoring makes both counts right, but the two markers are not protected by the same thing, and only one of them is safe by construction: the quoted `begin` sits mid-sentence after `- This section: delete everything from `, so the anchor rejects it however the bullet is formatted; the quoted `end` **opens** its line and is rejected only because the template wraps it in a backtick. Measured 2026-09-05 on a rendered block — strip the backticks out of that bullet and the anchored `begin` count stays `1` while the anchored `end` count goes to `2`. Those backticks in `index-doc-section.md.tmpl`'s "Removing this" bullet are therefore load-bearing for this row *and* for `verify_artifacts.py`'s `marker_block()`, which would truncate the block at the quoted marker; if that bullet is ever reflowed or unquoted, both break together. On the same fixture `find_markers()` returns exactly two markers, one `begin` and one `end` — that is the count this row has to agree with. **VERIFIED** that `debug prompt-input` renders the AGENTS.md chain and makes no model call. |
| Index doc size | sum the byte size of every file in the chain (`${CODEX_HOME}/AGENTS.md`, repo root, and each directory down to cwd) | total **< 32768**. Over budget is a **fail**: the tail is silently truncated (§4.1). |
| Rules (prose, inline) | extract the block first, then count inside it: `awk '/^[ \t]*<!--[ \t]*agentify:begin/{f=1} f{print} /^[ \t]*<!--[ \t]*agentify:end/{if(f)exit}' "$REPO/AGENTS.md" \| grep -c '^### Conventions'` | present exactly once. **Never `grep -A400 'agentify:begin'`**, which was the old form and is wrong twice over: the pattern is unanchored, so it matches the quoted marker in the "Removing this" bullet as well as the real one, and `-A400` then runs straight past `agentify:end` into the user's own prose. Measured 2026-09-05 on a rendered `AGENTS.md` whose author keeps their own `### Conventions` heading below the agentify block: the old form counts **2** and fails a correct build; the bounded form above counts **1**. Same family as the index-doc row — a check keyed on a marker string must be both line-anchored **and** bounded by the closing marker. |
| Rules (prose, files) | for each: `test -f "<plan-dir>/rules/<name>.md"`, frontmatter parses, and `grep -F "<name>.md" "$REPO/AGENTS.md"` | exists, parses, **and is referenced from `AGENTS.md`**. Unreferenced is a **fail** — nothing loads it (§4.2.1) |
| Rules (command policy) | `"$CODEX" execpolicy check --pretty --rules "$REPO/.codex/rules/agentify.rules" -- <a command the rule targets>` and again with a command it must not catch | exit 0 both times; the first returns a `matchedRules` entry with the expected `decision`; the second returns `{"matchedRules":[]}`. **Not trust-gated, so this stays a hard pass condition on a first run** — measured: `execpolicy check` reads the `--rules` path it is handed and never consults `[projects]`. Capture the exit status directly, not through a pipe: `cmd | head` reports `head`'s status and a parse error reads as exit 0. **A parse error here means the file would break every Codex session in this repo — remove it, do not ship it.** With no binary: do not ship the file at all (§4.2.2 rule 1). |
| Hooks (config) | `python3 -c "import json;json.load(open('.codex/hooks.json'))"`; then confirm the top-level keys are a subset of `{"description","hooks"}`; then confirm every pre-existing event, group and handler survived the merge | valid JSON; **no unknown top-level key** (one silently disables the whole file, §4.3); nothing pre-existing lost |
| Hooks (installed) | `test -x "<script>"`; the registration resolves to that script; `hooks.json` parses with a top-level key subset of `{"description","hooks"}`; every `eventName` is one of the 12 spelled events; every `matcher` is anchored and, for a tool-scoped event, contains the canonical name for its intent — `Bash` for shell, `apply_patch` for edits (§4.3) | **this is the pass condition, and it is always reachable.** All four hold ⇒ pass. A shell matcher with no `Bash` alternative is a **fail**, not a warning: it registers and never fires. This is what "the hook is installed" means and it is the strongest claim a first run may make — it says nothing about the hook being loaded or armed. |
| Hooks (loaded) — **trust-gated** | drive `hooks/list` over the app-server (below), having already read the Project trust row | **Trusted project:** the hook appears with the expected `matcher` and `sourcePath`, `source` is `"project"`, and `warnings` is empty ⇒ pass. Compare `eventName` **case-insensitively** — a hook declared `"PreToolUse"` is reported `"preToolUse"` (measured). **Untrusted or no entry:** `hooks: []`, `warnings: []`, `errors: []` is the **expected** result ⇒ `not tested — project not trusted`, plus needs-you step 1. Never a fail. **`warnings` non-empty in a trusted project** ⇒ fail; it names the offending field, line and column. **In an untrusted project `warnings` is empty even for a file Codex would reject** (measured), so this row can neither confirm nor deny the file's validity there — the Hooks (config) row is the only authority on that. The reason surfaces on the app-server's **stderr**, not in the JSON: capture it and match `Project-local config, hooks, and exec policies are disabled … until the project is trusted`, so the report states which case it was instead of guessing. |
| Hooks (script) | `test -x "<script>"` → `bash -n "<script>"` → the stdin fixtures below, **including the canonical one** (`"tool_name":"Bash"` for a shell hook, `"tool_name":"apply_patch"` with the patch on `tool_input.command` for a file-scoped one) | executable; syntax valid; benign fixture exits 0 and prints nothing; blocking fixture exits 0 and prints JSON whose `hookSpecificOutput.permissionDecision` is `deny` with an actionable `permissionDecisionReason`; **the canonical fixture produces the same verdict as the legacy spelling** — a hook that denies `exec_command` and allows `Bash` is inert on a current build and is a fail; a file-scoped hook's paths come out of the payload, so the `UNFILTERED` stderr line must not appear |
| Skills | `test -f "$REPO/.agents/skills/<n>/SKILL.md"`; frontmatter `name` equals the directory name; `len(description) < 1024`; description contains a trigger phrase traceable to `signals.json`; then drive `skills/list` | static checks pass **and** the skill comes back from `skills/list` with `"scope": "repo"` and the expected `path`. **Not trust-gated either** — measured: an untrusted project's `<repo>/.agents/skills/**` still loads with `"scope":"repo"`, which is why this row asserts `loaded` where the hooks row cannot |
| Subagents | `test -f "$REPO/.codex/agents/<n>.toml"`; the file parses as TOML if a parser is available, otherwise `name`, `description` and `developer_instructions` are each present at the start of a line; `name` matches the filename stem | static checks pass. **No runtime check exists** (§4.5) — the report must carry the live check as a manual item. |
| MCP (draft) | `test -f "<plan-dir>/codex-mcp.toml"`; scan with `lib/scrub.py` patterns; every env-var name appears in the report's needs-you list | file exists; **zero scrub hits**; every variable documented. **Never connect, never authenticate.** |
| MCP / any TOML agentify wrote — syntax | parse it with `python3 -c "import tomllib,sys;tomllib.load(open(sys.argv[1],'rb'))" <file>` | parses ⇒ pass. **Always reachable, and on a first run it is the only TOML check that is** — so it is the pass condition. A parse failure ⇒ restore the pre-write bytes from `pre_existing_sha256` and record a needs-you item. |
| MCP / any TOML agentify wrote — field names — **trust-gated** | start `"$CODEX" --strict-config app-server` from the repo (the same process the probe below already starts) and send `initialize` | **VERIFIED** on a trusted project: with a valid config it stays alive and answers `initialize`; with an unknown field it exits 1 and prints `Error: <file>:<line>:<col>: unknown configuration field …` on stderr. It makes no model call and needs no auth. **But the repo-scoped `<repo>/.codex/config.toml` is behind the same trust gate as everything else** — measured: with no `[projects]` entry, an unknown field in it does **not** stop the server. So on an untrusted project a clean start proves nothing about the file agentify just wrote: record `not tested — project not trusted` and do **not** report it as validated. A failure in a trusted project ⇒ restore `pre_existing_sha256` and record a needs-you item. |
| Plugin manifest | **never runs** — agentify emits no plugin manifest on either target (§4.7), so no run produces one to check. The row is kept only so that a repo where the *user* already has a `.codex-plugin/plugin.json` is not mistaken for agentify's output: that file belongs to them and phase 8 leaves it alone | n/a — the artifact type does not exist in a build manifest |
| `${CODEX_HOME}/config.toml` not modified **by agentify** | hash it before and after the build; **on a mismatch, diff the section headers and key names** (never the values) | the set of section headers and keys is unchanged. **A plain hash comparison is not a valid check on its own**: the ChatGPT desktop app and a background `codex app-server` daemon write to this file on their own — its mtime changed twice during verification with no write from here. A structural mismatch is a build failure (§4.6 rule 1); an mtime or hash change with identical structure is the desktop app, not agentify. |

**Hook stdin fixtures** — feed the event JSON exactly as Codex does. **The canonical fixture is the
pass condition**, and it is the one that catches a matcher written against the transcript vocabulary
only: a shell hook that ignores `"tool_name":"Bash"` is inert on a current build, whatever it does
with `exec_command`.

```sh
# 1. Canonical + blocking — REQUIRED. Must exit 0 and print a permissionDecision of "deny".
echo '{"session_id":"smoke","cwd":"'"$REPO"'","hook_event_name":"PreToolUse",
"tool_name":"Bash","tool_input":{"command":"npm install left-pad"}}' | .codex/hooks/<name>.sh; echo "exit=$?"

# 2. Canonical + benign — must exit 0 and print nothing.
echo '{"session_id":"smoke","cwd":"'"$REPO"'","hook_event_name":"PreToolUse",
"tool_name":"Bash","tool_input":{"command":"git status"}}' | .codex/hooks/<name>.sh; echo "exit=$?"

# 3. Legacy spelling — the same blocking verdict as 1, on an older build's tool name.
echo '{"session_id":"smoke","cwd":"'"$REPO"'","hook_event_name":"PreToolUse",
"tool_name":"exec_command","tool_input":{"command":"npm install left-pad"}}' | .codex/hooks/<name>.sh; echo "exit=$?"

# 4. Unrelated tool — must exit 0, print nothing, and print nothing on stderr either.
echo '{"session_id":"smoke","cwd":"'"$REPO"'","hook_event_name":"PreToolUse",
"tool_name":"update_plan","tool_input":{"plan":[]}}' | .codex/hooks/<name>.sh; echo "exit=$?"
```

For a **file-scoped** hook (one with a `PATH_GLOB` filter), fixtures 1–3 are replaced by a patch on
`tool_input.command`, one path inside the guarded scope and one outside:

```sh
# 5. Inside the guarded scope — must deny, and must NOT print the "UNFILTERED" stderr line.
printf '%s' '{"session_id":"smoke","cwd":"'"$REPO"'","hook_event_name":"PreToolUse",
"tool_name":"apply_patch","tool_input":{"command":"*** Begin Patch\n*** Update File: <guarded path>\n@@\n-a\n+b\n*** End Patch\n"}}' \
  | .codex/hooks/<name>.sh; echo "exit=$?"

# 6. Outside it — must exit 0, print nothing, and print nothing on stderr.
printf '%s' '{"session_id":"smoke","cwd":"'"$REPO"'","hook_event_name":"PreToolUse",
"tool_name":"apply_patch","tool_input":{"command":"*** Begin Patch\n*** Update File: <unguarded path>\n@@\n-a\n+b\n*** End Patch\n"}}' \
  | .codex/hooks/<name>.sh; echo "exit=$?"
```

**Stderr is part of the pass condition on 4, 5 and 6.** The `no file path in tool_input …
running the check UNFILTERED` line means the payload's paths were not extracted, so the path filter
did nothing and the check ran against everything. A deny that comes with that line on stderr is not a
pass — it is the filter failing open, and it denies work outside the guarded scope too.

A hook that blocks the benign fixture is a **build failure**, not a warning: it will block the user's
normal work in their next session. Remove it, record it in the report, and continue.

**Driving `hooks/list` and `skills/list`** — the only way to prove a hook or skill actually loaded.
The app-server speaks newline-delimited JSON-RPC on stdio; `initialize` must come first.
**VERIFIED** working, and it makes no model call:

```python
# phase 8 helper — read-only, no network, no model call, no session created.
# --strict-config makes this the config validator too: an unknown field exits 1 on stderr.
import json, os, subprocess, threading, time
proc = subprocess.Popen([CODEX, "--strict-config", "app-server"], cwd=REPO, text=True,
                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
out, err = [], []
threading.Thread(target=lambda: [out.append(l) for l in proc.stdout], daemon=True).start()
threading.Thread(target=lambda: [err.append(l) for l in proc.stderr], daemon=True).start()
send = lambda o: (proc.stdin.write(json.dumps(o) + "\n"), proc.stdin.flush())
send({"id": 1, "method": "initialize",
      "params": {"clientInfo": {"name": "agentify", "version": "1"}}})
time.sleep(1.0)
if proc.poll() is not None:          # config is invalid — err[0] names the file, line and column
    raise SystemExit("".join(err))
send({"id": 2, "method": "hooks/list",  "params": {"cwds": [REPO]}})
send({"id": 3, "method": "skills/list", "params": {"cwds": [REPO], "forceReload": True}})
time.sleep(4.0)
proc.kill()
# id 2 -> result.data[0] = {cwd, hooks[], warnings[], errors[]}
#   each hook: {eventName, matcher, handlerType, timeoutSec, source, sourcePath,
#               trustStatus, enabled, statusMessage, async, currentHash, key}
# id 3 -> result.data[0] = {cwd, skills[]}
#   each skill: {name, description, path, scope, enabled, pluginId}
```

Interpreting the result, and read the trust state before you read the JSON:

- **`hooks: []` with `warnings: []` and `errors: []`** — check trust first. In an untrusted project
  (or one with no `[projects]` entry) this is the **expected** result and means nothing about your
  file; the explanation is on **stderr**, so capture it. In a *trusted* project it means the hook
  genuinely did not load: wrong event spelling, or a matcher that never matches.
- **`warnings` non-empty** — a rejected `hooks.json`, named with field, line and column. Only ever
  seen in a trusted project.
- **`trustStatus": "untrusted"`** on everything agentify wrote — expected, always, in every project.
  It is the *armed* question (§5.0), not a failure.
- **`source`** should be `"project"`; `"user"` means something wrote to the global file, which
  agentify must never do.
- **`eventName`** comes back camelCased: `"PreToolUse"` in the file is `"preToolUse"` here. Compare
  case-insensitively.

**Manual checklist that must appear in `report.md`** — these cannot be proven from inside the run,
and each one is a numbered needs-you step carrying its reason, in this order
(`report-template.md` §3.2). The order is not cosmetic: steps 1 and 2 are what make the rest of the
setup do anything at all, so they come before the MCP steps even though only MCP involves a
credential.

1. **Trust the project.** If `${CODEX_HOME}/config.toml` has no `[projects."<abs repo path>"]` entry
   with `trust_level = "trusted"`, open Codex in this repo and accept the trust prompt. Reason to
   state: without it `.codex/hooks.json`, `.codex/rules/` and `<repo>/.codex/config.toml` do
   nothing, silently, and agentify does not set it because whether a repo's committed files may
   configure the agent is the user's security decision, not the tool's (§0.3).
2. **Trust the hooks.** Run `/hooks` in a Codex session and approve the new hooks. Reason: they are
   installed but not armed — `hooks/list` reports `"trustStatus":"untrusted"` for everything
   agentify writes, in every project. Editing a hook re-arms this prompt. Never suggest
   `--dangerously-bypass-hook-trust`.
3. **Confirm the index doc is being followed.** Start a **new** session in this repo and ask a
   question whose answer is in the agentify section (e.g. "what package manager does this repo
   use?"). Reason: agentify cannot restart the user's session, so this is the first turn that can
   show the section in context.
4. **Confirm the subagent loads.** Ask the model to use the generated agent by name and check it
   spawns. Reason: no runtime check for `.codex/agents/*.toml` exists (§4.5).
5. **MCP.** Export the listed environment variables, append the server block from
   `<plan-dir>/codex-mcp.toml` to `<repo>/.codex/config.toml` if agentify did not, restart Codex,
   and confirm the server's tools appear. Reason: the block references each variable **by name** and
   the value never goes in a file; agentify never authenticates a server (PRD §7.9, §13).
   `codex doctor --json` reports a warning naming any server whose environment variables are
   missing.
6. **Removal.** Delete the branch, or delete the listed files, the `agentify:begin`/`agentify:end`
   blocks in `AGENTS.md`, the agentify handler objects in `.codex/hooks.json`, and any `.git/hooks/`
   entries between agentify markers.

Steps 1 through 4 are the four checks §5.0 says a build-time run cannot make. Each one must appear
here **and** as a `not tested — <reason>` row in the verification table; a `not tested` row with no
matching numbered step, or a step with no row, means one of the two was written from memory.

---

## Open questions — re-verify before every release

Update the `verified-against` date and version in the frontmatter when you work this list. Verify
against a CLI install **and** a desktop-bundle install; they diverge (§1.3).

- [ ] **Tool-name vocabulary for hook matchers** (§4.3). `Bash` and `apply_patch` are documented; the
      rest of the list is empirical, not published, and it drifts by build. Re-derive from a fresh
      corpus or from an official tool reference.
- [ ] **Live activation of a generated hook** (§4.3, §8). The matcher and the `tool_input.command`
      payload contract are checked against the documentation and against fixtures; **that a generated
      hook fires on a real tool call has never been observed here.** Confirm by trusting a hook via
      `/hooks` and dumping stdin from a live turn. Until then the report says *installed*, never
      *working*.
- [ ] **Does a written `.codex/agents/<name>.toml` load?** (§4.5) Spawn the generated agent in a live
      session and check the child rollout's `source.subagent.thread_spawn.agent_path`.
- [ ] **Trust behaviour for a first-seen project** (§0.2): does declining the interactive trust prompt
      suppress `AGENTS.md` the way an explicit `trust_level = "untrusted"` does?
- [ ] **Exit codes other than 0 and 2, and the `SessionEnd` matcher target** (§4.3).
- [ ] **`CODEX_THREAD_ID` / `CODEX_SESSION_ID` in a live turn** (§1.1) — a sandbox-independent
      detection marker would let §1.1 stop asking the user in more cases.
- [ ] **Rollout format migration** (§2.4): will paginated sessions move their content out of the JSONL
      tree into `thread_history_1.sqlite`? This is the single biggest forward-compatibility risk for
      the miner.
- [ ] Does `hooks.json` still reject unknown **top-level** keys, and does it still tolerate unknown
      **handler** keys? The asymmetry is undocumented; agentify relies on neither, but a change to the
      first would break existing files.
- [ ] Is `<repo>/.codex/skills/` still a loaded root, and is `<repo>/.agents/skills/` still outside the
      trust gate?
- [ ] Is `${CODEX_HOME}/agents/` read as a user-scoped subagent location? Are `config_file` and
      `nickname_candidates` accepted keys?
- [ ] Does `${CODEX_HOME}/prompts/` exist as a supported custom-prompt location? It does not exist on
      the verification machine and agentify never writes there.
- [ ] Can hooks also be declared in TOML (`[hooks]` in `config.toml`)? **DOCUMENTED** as using the same
      event schema; agentify prefers `hooks.json` because JSON is stdlib-writable and TOML is not.
- [ ] Anything introduced after 0.152.1 — the changelog already lists v0.153.0 and the updater offered
      0.153.4 on the verification machine.
- [ ] Run the full pipeline against the repos in `test-repos.md` with `--target codex` and diff the
      artifact counts against the expected values.
