---
adapter: claude-code
adapter-version: 1
target-id: claude-code
verified-against: 2026-09-05 — Claude Code 2.1.260 on macOS (`claude --version`), config at
  `~/.claude`, binary at `~/.local/share/claude/versions/2.1.260`. How each of the five parts was
  verified this round —
  **1 DETECT:** live environment of a running session (`CLAUDECODE`, `CLAUDE_CODE_ENTRYPOINT`,
  `CLAUDE_CODE_SESSION_ID` all present) plus the settings-source list read out of the binary.
  **2 LOCATE TRANSCRIPTS:** the encoder function read out of the 2.1.260 bundle *and* exercised —
  a real headless session was run in a scratch path containing `_`, `.` and a space, and the
  directory Claude Code created was compared against it (§2.2).
  **3 LIST EXISTING CONFIG:** `ls` of the live `~/.claude` and of two real project `.claude/`
  trees, plus the config-root name list in the binary.
  **4 EMIT:** the CLI's own bundled zod schemas for hook definitions, hook events, hook stdin,
  SKILL.md frontmatter, subagent definitions and MCP server entries — these are the shapes the
  program itself validates against — cross-checked against real files on disk.
  **5 SMOKE TEST:** the rules loader was exercised end to end with two live headless sessions
  (§4.2); every other check in §5 is a local file/JSON assertion that was run as written.
  Re-verify every path and format at each release.
---

# Adapter: Claude Code

**This file is the only place Claude Code paths and file formats may live.** The core workflow
(diagnose → map → size → plan → build → verify) must never contain a `~/.claude/...` path, a
`.claude/settings.json` shape, or a frontmatter key name. If you find yourself writing one
outside this file, you are breaking PRD §11.3 — move it here instead.

Read this file in **phase 0** (DETECT, LIST EXISTING CONFIG) and again in **phase 7** (EMIT) and
**phase 8** (SMOKE TEST). Do not read it in phases 3–6; the plan describes artifacts in
target-neutral terms and the capability notes come from the tables below.

Confidence markers used throughout. The key itself used to be the weakest thing in this file —
"VERIFIED" was doing three different jobs and "UNVERIFIED" had no exit condition. Both are now
defined by **what evidence was taken**, so a reader can tell a live probe from a plausible reading:

| Marker | What it means, precisely |
|---|---|
| **VERIFIED** | Observed on the 2.1.260 install on 2026-09-05 by one of three methods, and the method is named at the claim: **(a) probe** — a command was run and its effect measured; **(b) artifact** — a real file on disk was read (a settings file, a transcript, an installed plugin); **(c) schema** — the shape was read out of the shipped CLI bundle, which is the definition the program validates against. A schema hit is stronger than a doc sentence and weaker than a probe: it proves the field is accepted, not that it behaves as described. |
| **DOCUMENTED** | Stated in Claude Code's published docs and consistent with everything observed, but not independently exercised here. Safe to build on; say "documented", not "confirmed", if the user asks. |
| **UNVERIFIED** | Not confirmed. **Every surviving UNVERIFIED must name the one check that would settle it** — otherwise it is not a marker, it is a shrug. Do not state it to the user as fact and do not make a generated artifact depend on it. |

An UNVERIFIED item is allowed to ship only when the code around it degrades safely without it.
Where that is the case, this file says so at the marker.

---

## 1. DETECT

### 1.1 Is Claude Code the running agent?

Check in this order and stop at the first hit. Environment beats filesystem: the filesystem tells
you what is *installed*, the environment tells you what is *running*.

| # | Signal | Confidence | Meaning |
|---|---|---|---|
| 1 | `CLAUDECODE=1` in the environment | **VERIFIED** (probe) | Claude Code is the running agent. Conclusive. |
| 2 | `CLAUDE_CODE_ENTRYPOINT` is set (values observed: `cli`, `claude-vscode`) | **VERIFIED** (probe) | Running agent is Claude Code; the value tells you the host surface. |
| 3 | `CLAUDE_CODE_SESSION_ID` is set | **VERIFIED** (probe) | Running agent is Claude Code. |
| 4 | `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/settings.json` exists | **VERIFIED** (artifact) for the dir, **VERIFIED** (schema) for the env override | Claude Code is *installed*. Not proof it is running. |
| 5 | `<repo>/.claude/` exists | **VERIFIED** (artifact) | The repo has been used with Claude Code before. Not proof it is running. |

Signals 1–3 were all present in the environment of the live 2.1.260 session used for this round.
Other `CLAUDE_*` variables are exported alongside them (`CLAUDE_CODE_EXECPATH`, `CLAUDE_PID`,
`CLAUDE_EFFORT`, `CLAUDE_CODE_CHILD_SESSION`, `CLAUDE_AGENT_SDK_VERSION` — **VERIFIED** (probe)).
**Do not detect on any of them.** They come and go between releases and several are set only under
the SDK or a child session; the three above are the contract.

```sh
# Detection probe — safe, read-only, no network.
[ "${CLAUDECODE:-}" = "1" ] && echo "target=claude-code (env)"
[ -n "${CLAUDE_CODE_ENTRYPOINT:-}" ] && echo "entrypoint=$CLAUDE_CODE_ENTRYPOINT"
CC_HOME="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
[ -d "$CC_HOME" ] && echo "installed=$CC_HOME"
```

**Ambiguity rule (PRD §7.1).** If signals 1–3 are absent and both `~/.claude/` and `~/.codex/`
exist, do **not** guess. Ask the user which target to build for, offer both, and record the answer
in the plan. Never emit artifacts for a target you inferred from installed-but-idle config.

### 1.2 Home directory resolution

Always resolve the user scope through `${CLAUDE_CONFIG_DIR:-$HOME/.claude}` — never hardcode
`~/.claude`. `CLAUDE_CONFIG_DIR` is **VERIFIED** (schema) as the override; it was not set on the
verification machine, so the fallback is the path actually exercised.

### 1.3 Settings precedence (needed for the "will my hook actually run" answer)

Highest wins: enterprise managed policy → CLI flags → `<repo>/.claude/settings.local.json` →
`<repo>/.claude/settings.json` → `${CLAUDE_CONFIG_DIR}/settings.json`. **VERIFIED** (schema): the
bundle carries the source list in ascending precedence order as
`["userSettings", "projectSettings", "localSettings", "flagSettings", "policySettings"]`, and its
own labels for them are user / project / "project, gitignored" / cli flag / managed. Hooks from
several scopes can all be active at once — this is why the merge rule in §4.3 is append-only.

### 1.4 Model class check (PRD §7.1 — warn, never enforce)

Read the `model` key from `${CLAUDE_CONFIG_DIR}/settings.json` if present (**VERIFIED** (artifact) to exist as
a top-level string key). If it names a small/fast model, warn once that plan quality will be lower
and continue. The contract's open decision is settled: **warn, do not enforce.**

---

## 2. LOCATE TRANSCRIPTS

The adapter never reads transcripts. It hands `mine_transcripts.py` the root and the target flag;
the miner does the reading, filtering and scrubbing, and only after phase-0 consent.

```sh
python3 "$SKILL_DIR/scripts/mine_transcripts.py" --repo "$REPO" --target claude-code
```

### 2.1 Path

```
${CLAUDE_CONFIG_DIR:-$HOME/.claude}/projects/<encoded-repo-path>/<session-uuid>.jsonl
```

**VERIFIED** (artifact). One `.jsonl` per session at the top level of the project directory, plus
sibling **directories**: one named with a session UUID holding that session's auxiliary data, and
one named `memory/` (120 UUID dirs and 19 `memory/` dirs across 115 project directories on the
verification machine). **Read only the top-level `*.jsonl` files** — `memory/` in particular is
agent memory and is on the never-read list in §2.5.

### 2.2 Path encoding — settled, and it is broader than the old rule

The directory name is the **resolved absolute** repo path with **every character outside
`[A-Za-z0-9]` replaced by `-`**, and then, only if that exceeds 200 characters, truncated to 200
with a hash suffix appended.

**VERIFIED** (schema + probe). The encoder is two functions in the 2.1.260 bundle, and it appears
twice verbatim:

```js
// character substitution
str.replace(/[^a-zA-Z0-9]/g, "-")
// length cap: 200, suffix is a base-36 Java-style string hash of the ORIGINAL path
if (encoded.length <= 200) return encoded;
return `${encoded.slice(0, 200)}-${Math.abs(hash(original)).toString(36)}`;
// hash(t): let e = 0; for each char: e = (e << 5) - e + charCode | 0
```

The probe that settles the character class: a headless session was run in
`/private/tmp/agentify_verify.enc test/sub` — a path holding an underscore, a dot **and** a space
— and Claude Code created `~/.claude/projects/-private-tmp-agentify-verify-enc-test-sub`, whose
first `user` record carries `cwd: "/private/tmp/agentify_verify.enc test/sub"`.

| Character | Becomes | Confidence |
|---|---|---|
| `/` | `-` | **VERIFIED** (artifact) |
| `.` | `-` | **VERIFIED** (artifact) — `/Users/x/.claude/plugins` → `-Users-x--claude-plugins`; the doubled dash is `/` and `.` each producing their own, not a collapse |
| `_` | `-` | **VERIFIED** (probe) — this was the long-standing UNVERIFIED marker. `agentify_verify` → `agentify-verify`. Settled. |
| ` ` (space), `(`, `)`, `+`, `@`, `,`, `#`, `&`, `~`, and every other non-alphanumeric | `-` | **VERIFIED** (probe for space, schema for the class) |

Case is preserved. The leading `/` produces a leading `-`. Consecutive specials each produce their
own `-`, so runs are **not** collapsed.

Two consequences that are easy to miss:

1. **The path is resolved first.** The probe ran in `/tmp/...` and the recorded `cwd` — and the
   directory name — were both `/private/tmp/...`. On macOS `/tmp`, `/var` and any symlinked
   checkout encode from the **real** path. Always `os.path.realpath()` the repo before encoding.
2. **Long paths are truncated and hashed.** Deep monorepo or worktree paths do exist: the longest
   directory on the verification machine is 164 characters, so the 200 cap was not hit there, but
   it is reachable. An implementation that only substitutes characters will miss those directories
   entirely.

Verified examples:

```
/Users/x/agentify
  -> -Users-x-agentify
/Users/x/Documents/projects/mobile-apps/Comic-app
  -> -Users-x-Documents-projects-mobile-apps-Comic-app
/private/tmp/agentify_verify.enc test/sub
  -> -private-tmp-agentify-verify-enc-test-sub
```

> **Cross-file note — `scripts/mine_transcripts.py` needs this change; the fallback does not cover
> it.** `encode_project_dir()` currently substitutes `[/._]` only. That is a strict subset of the
> real class, and the gap is not benign. Measured against the miner's own `_score_candidate()` and
> its 0.55 acceptance threshold:
>
> | Repo path | Miner's encoding | Real directory | Score | Outcome |
> |---|---|---|---|---|
> | `/Users/x/Projects/acme_web_app` | `-Users-x-Projects-acme-web-app` | same | 1.00 | exact — underscores are fine |
> | `/Users/x/repos/team.core_lib` | `-Users-x-repos-team-core-lib` | same | 1.00 | exact |
> | `/private/tmp/agentify_verify.enc test/sub` | `…-enc test-sub` | `…-enc-test-sub` | 0.57 | **fuzzy** — right answer, but it emits "confirm with the user before trusting counts" |
> | `/Users/x/dev/foo bar/baz` | `-Users-x-dev-foo bar-baz` | `-Users-x-dev-foo-bar-baz` | 0.50 | **below threshold** — falls through to the basename fallback |
> | `/Users/x/work/my_app (v2)/api-server` | `…my-app (v2)-api-server` | `…my-app--v2--api-server` | 0.50 | **below threshold** |
> | `/Users/x/dev/a+b@c/svc` | `-Users-x-dev-a+b@c-svc` | `-Users-x-dev-a-b-c-svc` | 0.43 | **below threshold** |
>
> So the answer to "is the fallback sufficient?" is **no, not on its own**: for a repo path holding
> a space, a parenthesis, `+` or `@`, the exact hit is lost, the scored sweep drops under 0.55, and
> the run lands on the basename fallback — which can select a *different checkout* with the same
> basename and warns about it, or finds nothing and reports `history_bucket: "none"`. It never
> silently reports the wrong counts without a warning, which is the invariant that matters, but it
> does silently lose real evidence. The fix is one line plus the cap:
> `_ENCODE_RE = re.compile(r"[^A-Za-z0-9]")`, then apply the 200-character truncation and the
> base-36 hash suffix above. The scored fallback then goes back to being what it is for — worktrees
> and subdirectory sessions.

### 2.3 Fallback when the encoded directory is missing

Never fail the run. In order:

1. **Prefix sweep.** Sessions started in a *subdirectory* of the repo get their own directory
   (**VERIFIED** (artifact): `...-hostshare-ravisojitra` and
   `...-hostshare-ravisojitra-apps-web-src-app` both exist). Collect the exact directory **plus**
   every directory whose name begins with `<encoded>-`. Require the following character to be `-`
   so `agentify` does not swallow `agentify-web`.
2. **Confirm by `cwd`.** Every `user` record carries a `cwd` field (**VERIFIED** (artifact)), and
   it is the **resolved** path (§2.2). Read the first few records of the newest file in each
   candidate directory and keep the directory only if `cwd` is the repo root or below it. This is
   the authoritative check; the name encoding is only a fast index — and because it is
   authoritative, it is what saves the run when the encoder is wrong.
3. **Fuzzy basename match** against `projects/` entries, then confirm by `cwd` as above.
4. If nothing matches, emit `history_bucket: "none"`, populate `warnings`, exit 0, and say plainly
   in the plan that the setup is derived from code and git only.

### 2.4 Record shape (what the miner will see)

Record `type` values **VERIFIED** (artifact) in real 2.1.260 files: `user`, `assistant`,
`attachment`, `file-history-snapshot`, `last-prompt`, `queue-operation`, `atis-latch`, and — new
since the last verification round — `system`, `bridge-session`, `pr-link`. The three new types are
harness bookkeeping, not conversation; **the miner reads `type == "user"` and nothing else**, so
they need no handling beyond not crashing on an unknown type.

A `user` record's keys, **VERIFIED** (artifact) across two 2.1.260 sessions: `cwd`, `entrypoint`,
`gitBranch`, `isSidechain`, `isMeta`, `message` (`{role, content}`), `parentUuid`, `promptId`,
`sessionId`, `timestamp`, `turnCompanion`, `type`, `userType`, `uuid`, `version`, plus
`permissionMode`, `promptSource`, `origin`, `classifierMetaLines`, `queueSkipAttachments`,
`sourceToolAssistantUUID` and `toolUseResult`. **The key set is not stable and not all keys appear
on every record** — a fresh single-turn session carried 15 of them, a long one carried 22. Read
defensively: `cwd`, `isSidechain`, `isMeta`, `message` and `timestamp` are the only ones the miner
may assume, and even those should be `.get()`. `message.content` is a **string** or a **list of
blocks** (both **VERIFIED** (artifact)), and slash-command invocations arrive wrapped in
`<command-message>` / `<command-name>` / `<command-args>` tags (**VERIFIED** (artifact)).

The filtering, wrapper-stripping, clustering and size-cap rules are the miner's contract, not the
adapter's. The adapter's only job is: **root, encoding, fallback, and the `--target claude-code`
flag.**

### 2.5 Privacy obligations restated here because this is where the paths live

- User turns only. Never assistant turns, never tool output, never sidechain (subagent) traffic.
- Scrub before anything is written or displayed, not after.
- Consent every run: yes / no / yes-but-last-N-days. `no` is a first-class path — the run
  continues on code + git evidence only.
- Never read `~/.claude/history.jsonl`, `~/.claude/*.sqlite`, `~/.claude/file-history/`,
  `~/.claude/session-env/`, or `auth`/credential files. The **top-level session `*.jsonl` files
  under `projects/<encoded>/`** are the entire allowed surface.
- **Never read the `memory/` directory** that sits beside those `*.jsonl` files, nor
  `.claude/agent-memory/`, `.claude/agent-memory-local/` or `~/.claude/agent-memory/`
  (**VERIFIED** (artifact + schema): `memory/` exists in 19 of 115 project directories on the
  verification machine, and the subagent `memory` frontmatter key names those three scopes). This
  is model-written persistent memory about the user's work — it is not a transcript, agentify has
  no consent for it, and it is exactly the kind of content the scrubber was never designed for.
- Never read `~/.claude/sessions/`, `~/.claude/tasks/`, `~/.claude/teams/`, `~/.claude/paste-cache/`,
  `~/.claude/downloads/`, `~/.claude/telemetry/` or `~/.claude/debug/` (all **VERIFIED** (artifact)
  as present in a live `~/.claude`). None of them is on the allowed surface, and none of them is
  needed: everything the miner wants is in the session JSONL.

---

## 3. LIST EXISTING CONFIG

Discovery calls this list; `discover.py` owns the counting and the maturity verdict. The adapter
owns the paths.

| Scope | Path | Artifact type | Confidence |
|---|---|---|---|
| Project | `<repo>/CLAUDE.md` | index doc | **VERIFIED** (artifact) |
| Project | `<repo>/CLAUDE.local.md` | index doc (deprecated — read, never write) | **DOCUMENTED** |
| User | `${CLAUDE_CONFIG_DIR}/CLAUDE.md` | global index doc | **DOCUMENTED** |
| Project | `<repo>/.claude/CLAUDE.md` | index doc — a second project location, read alongside `<repo>/CLAUDE.md` | **VERIFIED** (schema) |
| Project | `<repo>/.claude/rules/**/*.md` | rules — **natively loaded, and the walk recurses into subdirectories**, see §4.2 | **VERIFIED** (probe) |
| User | `${CLAUDE_CONFIG_DIR}/rules/**/*.md` | rules, user scope | **VERIFIED** (schema) |
| Project | `<repo>/.claude/skills/*/SKILL.md` | skills | **VERIFIED** (artifact) |
| User | `${CLAUDE_CONFIG_DIR}/skills/*/SKILL.md` | skills | **VERIFIED** (artifact) |
| Project | `<repo>/.claude/agents/*.md` | subagents | **VERIFIED** (artifact) |
| User | `${CLAUDE_CONFIG_DIR}/agents/*.md` | subagents | **DOCUMENTED** |
| Project | `<repo>/.claude/commands/*.md` | slash commands | **DOCUMENTED** |
| Project | `<repo>/.claude/settings.json` | hooks, permissions, plugins | **VERIFIED** (artifact) |
| Project | `<repo>/.claude/settings.local.json` | uncommitted overrides | **VERIFIED** (artifact) |
| User | `${CLAUDE_CONFIG_DIR}/settings.json` | hooks, permissions, model | **VERIFIED** (artifact) |
| Project | `<repo>/.claude/hooks/*` | hook scripts | **VERIFIED** (artifact) |
| Project | `<repo>/.mcp.json` | MCP servers — **and the same filename in every directory from the repo root down to cwd**, see §4.6 | **VERIFIED** (artifact + schema) |
| User | `${CLAUDE_CONFIG_DIR}/plugins/marketplaces/*/.claude-plugin/plugin.json` | installed plugins | **VERIFIED** (artifact) |
| Project | `<repo>/.claude-plugin/plugin.json`, `<repo>/.claude-plugin/marketplace.json` | plugin packaging | **VERIFIED** (artifact) |
| Project | `<repo>/.claude/output-styles/`, `workflows/`, `monitors/`, `themes/`, `.lsp.json` | other config agentify does not emit | **VERIFIED** (schema) — list them so the report can say what exists; **never write to them** |

Read for **structure**, never for values. `settings.json` may legitimately contain tokens in a hook
command or an `env` block; scrub anything before it is surfaced, and never echo a value back to the
user or into a generated file.

**Two things changed here since the last round and both affect counting.** `.claude/rules/` is no
longer "a repo convention" — Claude Code walks it natively (§4.2), so an existing rules directory
is now *config the team relies on*, not decoration, and de-duplication must treat it like skills
and agents. And the rules walk **recurses**, so a nested `.claude/rules/api/*.md` counts too; a
flat `ls` under-counts.

**Scope — the question the old rule got wrong.** Project-scoped and user-scoped artifacts are
counted **separately** and never unioned. **Only what is inside `$REPO_ROOT` is this repo's setup.**
A `~/.claude/skills` entry loads in every repo on the machine and says nothing about this one;
`discover.py` reports it so a candidate can be de-duplicated against it, and for nothing else
(`coverage.md` §6.1).

*(The old rule here judged maturity on the **union** of the two scopes, and the union is what a
throttle was computed from. Measured on a real repo, 2026-09-07: `.claude/skills/` held 61
directories — 48 installed third-party library guides, 18 of them symlinks into a shared store —
next to 0 rules, 0 hooks and 0 subagents. Counting them said "mature setup, propose little"; the
truth was a large codebase with no guardrails at all. Both the union and the throttle are gone.)*

**What provenance is still for.** `discover.py` classifies every skill and agent as `own`,
`vendored` (installed third-party — proven by a skills lockfile, an install command naming it, or
third-party documentation) or `ambiguous`. `provenance.maturity_basis` is a ready-to-quote sentence
for one line of context in the plan; `counts` is the de-duplication number; `symlinked` is the
never-touch list. **None of them gates anything.**

**`maturity` gates nothing.** There is no audit-only mode (`coverage.md` §6): a repo with an
existing setup gets the same full build as an empty one, minus whatever is already covered. What
`maturity` and `provenance` are for is one line of context in the plan and better de-duplication.

**De-duplicate by `blueprint.md` §2.1 — same type, same job, this repo.** The team's own artifact
of the candidate's type covers it, once it has been tested against this repo's commands and paths.
A **vendored** artifact does not count toward maturity and does not cover anything: an installed
third-party guide is generic by construction, so a generated skill links it as a reference from the
step that needs the vendor's API detail and is still built. Never restructure, never rewrite an
existing skill, and never touch a user-scoped or symlinked file — those are invariants of every
run, not a mode. **Home-scope entries (`~/.claude/skills`, `~/.claude/agents`) cover nothing**: they
are not this repo's setup, never appear in a count shown to the user, and a same-name collision
with a generated artifact is one report line, never a skip (`coverage.md` §6.1).

---

## 4. EMIT

> **Supported / unsupported verdicts live in `adapters/capabilities.md`**, which phase 6 reads to
> write the plan's capability notes without opening this file. This section owns the *emit
> mechanics* — exact paths, frontmatter, file bodies, smoke tests. **Change a verdict or a
> substitution here and you must change `capabilities.md` in the same edit**, or phase 6 promises
> the user something phase 7 does not build. Where the two disagree, this file is right about the
> mechanics and `capabilities.md` must be corrected to match.

Build order is dependency order and is not negotiable:

**rules → hooks → permissions → skills → subagents → MCP drafts → index doc last.**

The index doc is last because its tables enumerate what was actually written; an earlier order
produced rows linking to files that did not exist yet. There is no plugin manifest step — the type
is not emitted on either target (`adapters/capabilities.md`).

Checkpoint after each type. Nothing in this section runs before the phase-6 plan is approved in
writing.

> **What the 2026-09-05 verification round changed outside this file.** Recorded here because the
> rule above says a verdict change in §4 must move `capabilities.md` in the same edit, and
> `capabilities.md` has a different owner.
>
> **APPLIED 2026-09-15.** Every item below has now landed: items 1 and 2 in `capabilities.md`
> (which also gained a per-cell basis tag and a provenance table), items 3 and 4 in this file's own
> build order and sizing prose, and item 5 in the analyzers. The list is kept as the record of what
> was owed and when it was paid — it is no longer a list of outstanding work.
>
> 1. **`Rules — prose` row, Claude Code column: `Convention` → `Native`.** It currently reads
>    "*Convention* — `.claude/rules/<name>.md`, wired into `CLAUDE.md`. `paths:` frontmatter
>    auto-loads", which has the two halves backwards. Claude Code walks `.claude/rules/` itself.
>    An **unscoped** rule loads at session start with no `CLAUDE.md` reference of any kind; a
>    **`paths:`-scoped** rule is the one that does *not* load eagerly — it waits until the model
>    touches a matching file. Both proved by probe in §4.2. Suggested cell: *"**Native** —
>    `.claude/rules/**/*.md`, walked by Claude Code; no index-doc wiring needed. `paths:` frontmatter
>    defers a rule until a matching file is read."*
> 2. **The "Rules (both targets)" note is now false on the Claude Code half.** It says "Neither
>    target auto-loads a *prose* rules directory: on Claude Code the index doc points at
>    `.claude/rules/`" and "a rule and its index-doc pointer are one artifact". Claude Code does
>    auto-load one, and on this target the pointer is a nicety. The note has to be split per target
>    rather than softened — a plan that tells a Claude Code user their rule only works because the
>    index doc points at it is telling them something untrue, and it is the sentence phase 6 pastes
>    verbatim into `CAPABILITY_PROSE_NOTE`.
> 3. **Build order puts the index doc LAST**, not first: rules → hooks → permissions → skills →
>    subagents → MCP drafts → index doc. `paths:` is why the old order is now clearly wrong. A
>    path-scoped rule loads itself, so the index-doc pointer was never the dependency it was
>    described as — and the index doc's tables enumerate what was written, which cannot be known
>    before the files exist (`blueprint.md` §9).
> 4. **`paths:` is what makes an unbounded number of rules cheap.** A path-scoped rule costs nothing
>    until a matching file is read, so there is no reason to ration them: one rule per real zone is
>    the target (`blueprint.md` §5.1). **Unscoped** rules are the ones with a real cost — they load
>    in every session unconditionally — so this adapter holds unscoped rules to 2 and says so in
>    §4.2 and §5. That is a context-budget constraint on one rule *form*, not a limit on output, and
>    it is never described to the user as a cap.
> 5. **Two script changes are named in place**, with the measurement behind each: the
>    project-directory encoder in `mine_transcripts.py` (§2.2) and the `${CLAUDE_PROJECT_DIR}`
>    spelling in `templates/settings-hooks.json.tmpl` (§4.3).

Universal rules for every emitted file:

- **Never overwrite.** Create, or update strictly between agentify markers — **except for the two
  JSON configs**, `.claude/settings.json` (§4.3) and `.mcp.json` (§4.6), which hold no markers and
  can hold none. Those are changed by merging into the parsed data structure and are updated by
  matching the entry's own identity: the hook command path, or the `mcpServers` name. Same
  invariant, different mechanism — and the undo differs with it (`references/report-template.md`
  §3.1).
- Every generated file carries the ID block from the build contract:
  `agentify-id`, `agentify-version: 1`, `agentify-generated: <yyyy-mm-dd>`,
  `agentify-evidence: <one line with counts>`, and the line `Safe to delete or edit.` — again except
  `settings.json`, whose merged entry carries none of it (§4.3); `.mcp.json` carries it in a
  top-level `_agentify` object (§4.6).
- Bodies come from `templates/*.tmpl`. This adapter defines the **target-specific envelope**:
  where the file goes, what the frontmatter keys are, and how it is wired up.
- Everything lands on branch `agentic-setup/<yyyy-mm-dd>` or stays staged. Never commit to the
  user's current branch without approval.
- Write user-scoped files (`${CLAUDE_CONFIG_DIR}/...`) **only** when the user explicitly chose
  global scope in the interview. The default scope is the repo.

### 4.1 Index doc — `CLAUDE.md`

| | |
|---|---|
| Project path | `<repo>/CLAUDE.md` |
| Global variant | `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/CLAUDE.md` — applies to **every** project on the machine. Opt-in only, never the default. |
| Format | Plain Markdown. No frontmatter required or expected. A file over 4 MiB is skipped outright (**VERIFIED** (schema)) — not a limit an agentify section will reach, but it is why an oversized `CLAUDE.md` can appear to load nothing at all. |
| Loading | Read automatically at session start: managed policy, then `${CLAUDE_CONFIG_DIR}/CLAUDE.md`, then for every directory from the repo root down to cwd both `<dir>/CLAUDE.md` and `<dir>/.claude/CLAUDE.md`, then `<dir>/CLAUDE.local.md`. Deeper files are injected last. **VERIFIED** (schema). |
| Imports | `@path/to/file.md` pulls that file's contents into context. Imports inside code fences and inline code spans are skipped, and the recursion is depth-limited (constant `5` in the 2.1.260 bundle). **VERIFIED** (schema). This is **no longer** the mechanism that makes rules load — see §4.2. |

**Merge, never overwrite.** If `CLAUDE.md` exists, append one delimited block; if the block already
exists, rewrite only between the markers.

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

<!-- body from templates/index-doc-section.md.tmpl -->

<!-- agentify:end id=index-doc-section -->
```

Do not use YAML frontmatter for the markers — `CLAUDE.md` has none, and adding one changes how a
human reads the file.

**The marker spelling is `agentify:begin` / `agentify:end`, everywhere, with no synonym.**
`templates/index-doc-section.md.tmpl` emits exactly that, and it is what `SKILL.md` and the
plan template document. `verify_artifacts.py` also accepts `agentify:start` and a few other
spellings, but only so a rerun can still find a block written by an older agentify — never
emit one. An adapter that invents its own spelling produces files the templates do not
describe, and the drift is invisible until someone edits by hand.

**Symlink case (VERIFIED (artifact)).** `CLAUDE.md` is sometimes a symlink to `AGENTS.md` so one
file serves several agents. Resolve the link with `readlink`/`realpath`, append to the **real**
file, write nothing through the link, and state in the plan which physical file was modified.

**Rewrite path.** If the existing `CLAUDE.md` is large and disorganised, do not restructure it.
Propose a rewrite as a separate, separately-approved item and, if approved, write the proposal to
`<plan-dir>/CLAUDE.proposed.md` for the user to move into place themselves.

The attribution footer goes in this section (placement 2 of 3).

### 4.2 Rules — `.claude/rules/<name>.md`

| | |
|---|---|
| Path | `<repo>/.claude/rules/<kebab-name>.md` |
| Format | Markdown, with the agentify ID block in YAML frontmatter |

> **This section previously said rules are not auto-loaded. That is now wrong, and it was the
> single most consequential error in this file.** Claude Code 2.1.260 walks `.claude/rules/`
> natively. Anything built on the old claim — the "wire it or don't emit it" rule, the phase-8
> fail, the `Convention` verdict in `capabilities.md` — has to move with it.

**How rules actually load (VERIFIED (probe), twice, end to end).** A scratch repo was built with
**no `CLAUDE.md` at all** and two files under `.claude/rules/`: `unscoped.md` with no frontmatter,
and `scoped.md` with `paths: ["src/**/*.ts"]`. Two headless sessions were then run in it.

| Session | Rule with no `paths:` | Rule with `paths: ["src/**/*.ts"]` |
|---|---|---|
| Asked for its codewords, no tools | **loaded** | not loaded |
| Told to read `src/a.ts` first | **loaded** | **loaded** |

So:

1. **A rule with no `paths:` is loaded at session start, unconditionally, with no index-doc
   reference of any kind.** `.claude/rules/` is a real load path.
2. **A rule with `paths:` is loaded on demand, the moment the model touches a matching file.**
   Not at session start — which is the whole point: it costs nothing until it is relevant.

The mechanism, **VERIFIED** (schema), is one recursive `.md` walk over the rules directory run
twice per session — once collecting rules *without* globs (eager) and once collecting rules *with*
globs (matched against the file being read). It runs at Managed, User (`~/.claude/rules/`) and
Project scope, and at Project scope it checks `<dir>/.claude/rules/` for **every ancestor directory
of the session cwd**, closest last — which is why the repo root's rules still apply to a session
started in a subdirectory. The walk **recurses into subdirectories** of each rules directory, so
`.claude/rules/api/route-handlers.md` is loaded exactly like a top-level rule.

**What this changes for the emitter.**

- **Wiring is no longer required for loading.** Delete the "wire it or do not emit it" rule. A rule
  file dropped into `.claude/rules/` works.
- **`paths:` is now the primary sizing lever, not a hint.** A path-scoped rule is free until it
  fires, so the old context-rent argument that justified capping rules hard applies only to
  *unscoped* rules. **Default every emitted rule to `paths:`**, derived from the evidence that
  produced it (the directories in the request shape, the paths in the commits). Emit an unscoped
  rule only when the evidence genuinely spans the whole repo, and **cap unscoped rules at 2** —
  that is the old eager-import cap, moved to where the cost actually is.
- **Wiring is still worth doing, for a different reason.** A one-line pointer in the `CLAUDE.md`
  agentify section makes the rule *discoverable by a human* reading the repo, and it survives the
  case where a user copies the index doc to another tool. It is now a **quality item, not a
  correctness gate** — phase 8 warns, it no longer fails (§5).
- **`@import` is now the exception.** An `@.claude/rules/<name>.md` line in `CLAUDE.md` still works
  (**DOCUMENTED**), but it now *duplicates* what the native walk already did for an unscoped rule,
  and it *defeats* the on-demand behaviour of a scoped one by pulling it in every session. **Do not
  emit `@` imports for files under `.claude/rules/`.** Keep `@import` for pulling in a doc that
  lives somewhere else.

```markdown
---
paths:
  - "src/db/**"
  - "src/api/**"
agentify-id: db-access-through-repository
agentify-version: 1
agentify-generated: 2026-09-05
agentify-evidence: corrected 4 times across 3 sessions; 61 commits touch src/db/
---
<!-- Safe to delete or edit. -->

# All database access goes through the repository layer

**Scope:** `src/db/**`, `src/api/**`
...
```

**The `paths:` key — settled, with its exact semantics (VERIFIED (probe + schema)).**

- The literal YAML key is **`paths`**. It takes a string or a list of glob patterns.
- Matching is **gitignore-style against the repo-relative path of the file the model touches**. A
  trailing `/**` is stripped before matching, so `"src/api/**"` and `"src/api"` are the same rule
  and both cover everything under `src/api/`.
- **`paths: ["**"]` is treated as no scope at all** — an all-globs list is discarded and the rule
  loads eagerly. So it is a legal way to write "everywhere", and it is not a way to trick the
  loader into lazy-loading a repo-wide rule.
- An empty list is likewise discarded. A rule whose globs match nothing simply never loads: there
  is no error, no warning, and nothing in the transcript. **A typo in `paths:` is a silent
  no-op** — which is why §5 checks each glob against the repo's real files.
- Unknown frontmatter keys are ignored, so the `agentify-*` ID block sits in the same frontmatter
  block as `paths:` without interfering. Put `paths:` first; it is the key a human will look for.

Still **also** state the scope in prose in the rule body. The key controls *loading*; the prose
tells the model what the rule governs once it is loaded, and it survives being read out of context
by a human or another tool.

`paths:` is in heavy production use in the wild — 28 of 35 rule files in one real repo on the
verification machine carry it (**VERIFIED** (artifact)), including one that uses `paths: ["**"]` as
its "applies to everything" base rule.

### 4.3 Hooks — `.claude/settings.json`

Hooks are the one artifact type that is configuration, not a file drop. Get the shape exactly right.

**Exact shape (VERIFIED (artifact + schema)):**

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/block-destructive.sh",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

Note the nesting: **event → array of matcher groups → each group has `matcher` + its own `hooks`
array of commands.** Two levels named `hooks`. Getting this wrong is the single most common way to
produce a settings file that parses and does nothing.

**Event names.** 2.1.260 accepts **33** hook events (**VERIFIED** (schema) — the full enum, in the
bundle's own order):

`PreToolUse` · `PostToolUse` · `PostToolUseFailure` · `PostToolBatch` · `Notification` ·
`UserPromptSubmit` · `UserPromptExpansion` · `SessionStart` · `SessionEnd` · `Stop` ·
`StopFailure` · `SubagentStart` · `SubagentStop` · `PreCompact` · `PostCompact` ·
`PreModelSwitch` · `PostModelSwitch` · `PermissionRequest` · `PermissionDenied` · `Setup` ·
`TeammateIdle` · `TaskCreated` · `TaskCompleted` · `Elicitation` · `ElicitationResult` ·
`ConfigChange` · `WorktreeCreate` · `WorktreeRemove` · `InstructionsLoaded` · `CwdChanged` ·
`FileChanged` · `DirectoryAdded` · `MessageDisplay`

**Agentify emits only the eight below.** The rest exist, are legal, and must be *preserved* on
merge — but a setup generator has no evidence-backed reason to reach for `Elicitation` or
`TeammateIdle`, and a hook on an event nobody understands is a support burden, not a guardrail.

| Event | Fires | `matcher` | Default timeout |
|---|---|---|---|
| `PreToolUse` | before a tool call; **can block** | tool name pattern (e.g. `Bash`, `Edit\|Write`) | 15s |
| `PostToolUse` | after a tool call completes | tool name pattern | 15s |
| `UserPromptSubmit` | when the user submits a prompt; can inject context | ignored — emit `""` | 30s |
| `SessionStart` | at session start | `startup`, `resume`, `clear`, `compact`, `fork` | — |
| `Stop` | when the main agent finishes responding | ignored — emit `""` | 120s |
| `SubagentStop` | when a subagent finishes | ignored — emit `""` | 120s |
| `PreCompact` | before context compaction | ignored — emit `""` | — |
| `Notification` | when Claude Code raises a notification | notification kind | — |

`matcher` is matched against the tool name and **is a regular expression**. Three spellings mean
"everything": `""`, `"*"`, and omitting the key (**VERIFIED** (schema)). Alternation (`Edit|Write`)
and comma-separated lists are both accepted, and the bundle calls that form a "plain list" —
distinguishing it from a "pattern matcher", which some execution surfaces refuse to carry. **Emit
the plain-list form** (`Edit|Write`), never a character class or an anchor. For events with no
tool, always emit `"matcher": ""` rather than omitting the key — it keeps the merge logic uniform.

The default timeouts above are **VERIFIED** (schema) and are the reason an explicit `timeout` is
usually unnecessary: a `PreToolUse` hook already gets 15 seconds. Emit `timeout` only to *shorten*
it.

`TaskCompleted` and `SessionEnd` used to be marked UNVERIFIED here. **Both are official**
(**VERIFIED** (schema), and `TaskCompleted` is live in a real `~/.claude/settings.json` on the
verification machine). Preserve them on merge, as before; agentify still does not emit them,
now as a scope decision rather than a doubt.

**Hook definition keys** (the object inside a matcher group's `hooks` array). Five `type` values
exist — `command`, `prompt`, `mcp_tool`, `http`, `agent` (**VERIFIED** (schema)). **Agentify emits
`type: "command"` only**: it is the one that runs with no model call, no network, and no MCP
dependency, and it is the one a user can test from a shell. For that type:

| Key | Notes |
|---|---|
| `type` | `"command"`. Required. |
| `command` | The shell command. Runs through a shell unless `args` is present. Required. |
| `args` | **NEW, and worth knowing.** An argument list. When present, `command` is resolved as an executable and spawned **directly, with no shell**, and path placeholders are substituted per element as plain strings — so a path containing a quote, `$` or a backtick never reaches a shell parser. Agentify does not emit it in v1 (the shell form is what every existing hook in the wild uses), but it is the correct answer if a generated hook ever needs to take a filename as an argument. |
| `timeout` | **Seconds** (**VERIFIED** (schema)). See the default table above. |
| `statusMessage` | **No longer UNVERIFIED** — it is an official optional key, "Custom status message to display in spinner while hook runs" (**VERIFIED** (schema)). Agentify still omits it: it is cosmetic, and every character of it is context the user pays for on every fire. |
| `if` | A permission-rule pattern (e.g. `Bash(git *)`) that gates whether the hook process is spawned at all. Cheap and precise. Agentify does not emit it in v1 — the matcher plus an early exit in the script covers the same ground and is visible in one file — but note it in the plan if a user asks why their hook runs on every Bash call. |
| `once` | Runs once, then removes itself. Never emit this from a generated setup: a hook that deletes itself is not reversible and not idempotent. |
| `async` | Runs in the background without blocking. Never emit it for a *blocking* hook — an async hook cannot deny a tool call. |
| `shell` | `bash` or `powershell`. Omit; the default is bash on POSIX. |

**Exit-code semantics** (**VERIFIED** (schema) — the bundle maps a hook process exiting `2` to the
literal outcome `"blocked"` and builds the block reason from its stderr):

| Exit code | Effect |
|---|---|
| `0` | Success. The tool call proceeds. stdout may be parsed as the JSON protocol below; a plain-text stdout is not control flow. |
| `2` | **Blocks.** The tool call does not run, and **stderr is fed back to the model** as the reason. This is the whole mechanism: your stderr message is the instruction the model acts on, so write it as an instruction ("Use `bun`, not `npm`. Re-run as: bun install"), not as a log line. |
| any other non-zero | Non-blocking error. stderr goes to the user, not the model. The tool call proceeds. |

**The JSON-on-stdout control protocol is no longer unverified.** Its field set (**VERIFIED**
(schema)) is: top-level `continue`, `stopReason`, `systemMessage`, `suppressOutput`, `decision`
(the legacy `approve`/`block` pair) and `hookSpecificOutput`; inside `hookSpecificOutput`,
`hookEventName` (**required** — the bundle errors with "hookSpecificOutput is missing required
field \"hookEventName\"" without it), plus per event `permissionDecision`
(`allow` | `deny` | `ask` | `defer`), `permissionDecisionReason`, `additionalContext`,
`updatedInput`, `updatedPermissions` and `updatedMCPToolOutput`.

**Agentify still emits exit-code hooks only**, and the reason is now a choice rather than an
unknown: exit codes are a two-line contract a user can test with `echo $?`, the JSON protocol is a
versioned schema that a generated file would silently outgrow. Say that in the plan if asked.

**Hook input.** The hook receives a JSON event object on **stdin**. Base fields, present on every
event (**VERIFIED** (schema)): `session_id`, `transcript_path`, `cwd`, `hook_event_name`, and
optionally `prompt_id`, `permission_mode`, `agent_id`, `agent_type`. Tool events add `tool_name`,
`tool_input`, `tool_use_id`, and `PostToolUse` adds `tool_response`. `agent_id` is the documented
way to tell a subagent's tool call from the main thread's. Generated hook scripts must read stdin
defensively and must not crash on an unexpected shape — an exception in a hook is a broken session.

**Hook script files.**

- Path: `<repo>/.claude/hooks/<kebab-name>.sh`, mode `0755`.
- First lines: `#!/usr/bin/env bash` then `set -euo pipefail`.
- Reference it from settings as **`"${CLAUDE_PROJECT_DIR}/.claude/hooks/<name>.sh"` — with the
  braces.** Both `$CLAUDE_PROJECT_DIR` and `${CLAUDE_PROJECT_DIR}` are recognised by the expander
  (**VERIFIED** (schema)), and the bare form is what most configs in the wild use, but the bundle
  carries a diagnostic for exactly this: PowerShell reads `$CLAUDE_PROJECT_DIR` as an undefined
  variable and substitutes nothing. **The braced form is the portable spelling and is what agentify
  emits.** Never write an absolute `/Users/...` path into a committed settings file.
- Inside a plugin, use `"${CLAUDE_PLUGIN_ROOT}/hooks/<name>.sh"` instead — **VERIFIED** (artifact).
  `${CLAUDE_PLUGIN_DATA}` and `${CLAUDE_SESSION_ID}` also expand; `${CLAUDE_SKILL_DIR}` expands
  inside a skill. Nothing else does: the expander recognises exactly these names and leaves every
  other `$…` to the shell.
- `timeout` is in **seconds** (**VERIFIED** (schema): "Timeout in seconds for this specific
  command"). Real-world configs contain `"timeout": 5000` written by authors who assumed
  milliseconds; that is an 83-minute timeout, not 5 seconds. **Emit seconds**, or omit the key and
  take the per-event default from the table above. If you find an existing `timeout` over 300 while
  merging, leave it alone but note it in the report.

**Merge rule — the important one.**

1. Read `<repo>/.claude/settings.json`. If it does not exist, create it with a single top-level
   `hooks` key and nothing else.
2. Parse it as JSON. **If it does not parse, stop.** Do not repair it, do not overwrite it. Write
   the intended content to `<repo>/.claude/settings.json.agentify-proposed` and record a
   needs-you item in the report.
3. Ensure `hooks` exists; ensure `hooks[<Event>]` is an array.
4. **Idempotency first.** Look for a command object anywhere under that event whose `command` ends
   with `/.claude/hooks/<name>.sh` — the key below. Found: replace **that one object** in place and
   stop. Never append a second copy.
5. Only when step 4 found nothing: find a matcher group whose `matcher` equals yours. If found,
   **append your command object to that group's `hooks` array** — so the group is usually **shared
   with hooks the user wrote**, which is why the undo removes the object and prunes the group only
   when it emptied it. If there is no such group, **append a new matcher group** to the event array.
6. Never touch `permissions`, `model`, `enabledPlugins`, or any other top-level key. Never
   reserialise in a way that drops unknown keys. Preserve 2-space indentation and end the file with
   a trailing newline — the un-merge reproduces the pre-run bytes exactly only when the merge wrote
   the file back in the convention it found.
7. Record `pre_existing_sha256` (the file's hash **before** this merge) and `restore: span` on the
   artifact's manifest entry, and write the `merge` record's hook entry as
   `["hook_command", "<the command line you wrote>", "<Event>"]` — **the event is half of the
   handler's identity**, because the same script the user wired into a second event is their wiring
   and not this run's, and the un-merge removes the handler only from the event recorded here
   (`report-template.md` §3.1 block C). Nothing else recovers them, and the un-merge script's byte
   proof is built from them.
8. Write to a temp file in the same directory and `os.replace()` it into place, so an interrupted
   run cannot leave a truncated settings file.

**Idempotency without frontmatter — the identity is the whole command path plus its event, and never a basename.**

JSON has no comment syntax, so this file carries **no `agentify:begin` / `agentify:end` markers and
no `# agentify:<id>` line**, and it never can. What agentify emits into it is one command object and
one command object only — `templates/settings-hooks.json.tmpl` is the authority and this is what it
writes:

```json
{ "type": "command", "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/enforce-bun.sh", "timeout": 5 }
```

The idempotency key is the one the template's merge procedure step 4 names: **a nested
`hooks[].command` that ends with `/.claude/hooks/<name>.sh`**. On a rerun, find the command object
whose `command` ends with that suffix and replace that object in place. Never append a second copy.

> **Cross-file note — both spellings of the project-root variable are in the wild, and both
> resolve.** `templates/settings-hooks.json.tmpl` writes the braced `${CLAUDE_PROJECT_DIR}` (the
> PowerShell reason is in the bullet list above), but a setup built by an older agentify carries the
> unbraced `$CLAUDE_PROJECT_DIR`, and a user may have written either by hand. A rerun still finds
> its own hook either way: the un-merge script normalises both spellings — and the quoted and
> unquoted `$(git rev-parse --show-toplevel)` forms, and a literal absolute path — to the same
> `<repo>/.claude/hooks/<name>.sh` before comparing the **whole** path, under the recorded event.
> **A basename is never an identity there** (`report-template.md` §3.1 block C): matching one is
> what made an undo delete a user's unrelated script of the same name. `${CLAUDE_PLUGIN_ROOT}` is
> deliberately *not* folded in — it is a different root, and folding it would invent exactly that
> false identity.

**Do not merge the fragment's `_agentify` key into `settings.json`** (template step 6). It is inert
metadata describing the fragment, not settings, and this is the one `_agentify` block that is never
written to a generated file. Provenance in the merged file lives in the command path and in the
header of the hook script it points at. `settings.json` therefore gets no `agentify-id`, no
frontmatter, no marker and no attribution — and `verify_artifacts.py` knows it: `markers` exempts
JSON entirely, and `metadata` is a warn rather than a fail for JSON artifacts.

**What this costs the undo, which is where getting it wrong has already bitten.** A `settings.json`
agentify merged into is `restore: span` — the user wrote it, git never tracked it — and it is
`action: modified`, which past wording routed to the marker-removal script. That script looks for a
marker this file cannot contain: it prints `SKIP .claude/settings.json: no agentify block id=…`,
**exits 0**, and leaves the hook registered forever while the report calls the undo a success.
Measured on the axios dogfood run and reproduced on a fixture. The undo for this file is the **JSON
un-merge script** in `references/report-template.md` §3.1, which keys on exactly the identity above —
the hook artifact's manifest `command` — deletes the whole command object, prunes the matcher group
and the event array **only if this run created them**, and leaves every hook the user wrote alone.
Anything that changes the shape of what is merged here must change that script's key in the same
edit.

An older agentify wrote `"# agentify:<id>\n<path>"` as the command. Nothing emits that any more —
**never emit it** — but the un-merge script's `key()` still reduces a command to its last
non-comment line so an undo run against a setup built by that version still matches. That is
backward compatibility, exactly like the `agentify:start` marker alias, and not a second legal
spelling.

**Scope.** Default to `<repo>/.claude/settings.json` (committed, shared with the team). Offer
`settings.local.json` if the user wants the hooks private and uncommitted. **Never write hooks to
`${CLAUDE_CONFIG_DIR}/settings.json`** — a global hook fires in every repo the user opens, which is
neither reversible-in-spirit nor evidenced by this repo.

### 4.4 Skills — `.claude/skills/<name>/SKILL.md`

| | |
|---|---|
| Project path | `<repo>/.claude/skills/<kebab-name>/SKILL.md` |
| User path | `${CLAUDE_CONFIG_DIR}/skills/<kebab-name>/SKILL.md` (opt-in only) |
| Directory name | Must equal the frontmatter `name`. |

**Frontmatter (VERIFIED (artifact + schema)):**

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

**What agentify emits** — three keys and the ID block, and that is the whole list:

| Key | Required | Notes |
|---|---|---|
| `name` | yes | kebab-case, must match the directory name. **VERIFIED** (artifact). |
| `description` | yes | One paragraph, third person. **Hard limit 1024 characters, and the CLI's own guidance is "aim for under 200"** (**VERIFIED** (schema)). See §4.4.1 — this is the highest-leverage field in the whole build. |
| `allowed-tools` | no | **Settled — this was UNVERIFIED and is not any more.** The bundle's schema describes it as "Tools available to the model while this file is active. **Comma-separated string or YAML list.**" Both spellings are canonical (**VERIFIED** (schema)); the space-separated form seen in the wild is not. Agentify **omits it by default** (the skill inherits the session's tools). Emit it only if the interview asked for tool restriction, and then use the **comma-separated string** form. The "spelling is unverified" caveat comes out of the plan. |
| `version` | no | **VERIFIED** (artifact) in the wild as an optional string; the bundle marks it internal bookkeeping. Agentify omits it; `agentify-version` covers it. |

**What 2.1.260 also accepts, and why agentify does not emit it.** The frontmatter surface has grown
a lot since the last verification round. All of the following are real (**VERIFIED** (schema)):
`when_to_use`, `paths`, `hooks`, `context` (`inline` | `fork`), `agent`, `background`,
`disallowed-tools`, `model`, `effort`, `shell`, `argument-hint`, `disable-model-invocation`,
`user-invocable`. Two are worth a sentence in the plan when a candidate is close to them:

- **`paths`** — glob patterns; "the skill only loads when the model touches matching files". The
  same mechanism as rules (§4.2). A genuinely path-bound skill is a better fit for a **rule** in
  v1, which is why agentify does not reach for this yet, but it is the obvious v1.1 sharpening.
- **`context: fork`** — runs the skill in a subagent instead of inline. This is the seam between a
  skill and a subagent, and a candidate whose value is context isolation may belong here rather
  than in `.claude/agents/`.

**Do not emit any of them in v1.** Every one is a field the user did not ask for, on a file they
have to maintain, and several (`hooks`, `model`, `effort`) change session behaviour in ways an
evidence-derived setup has no evidence for.

**Body:** Markdown. Keep `SKILL.md` under ~500 lines and push detail into sibling files
(`references/`, `scripts/`, `assets/`) referenced by relative path. The body is **not loaded until
the skill is invoked** — which is exactly why the description does all the work. `skill.md.tmpl`
rule 9 names the four reference files that recur and what each holds.

#### 4.4.2 `setup-manager` — the one skill every run builds

`blueprint.md` §6.3 owns why it exists and what it must contain. This is what it must know about
**this** target, and the adapter is where those facts live — so when it is written, they are copied
into `.claude/skills/setup-manager/references/config-surface.md` rather than left as a pointer to a
file the user does not have:

| Surface | Path | Format |
|---|---|---|
| Index doc | `CLAUDE.md` | markdown; agentify's part lives between `agentify:begin`/`agentify:end` |
| Rules | `.claude/rules/<name>.md` | markdown + frontmatter. **The key is `paths:`, never `scope:`** — a rule with `scope:` loads eagerly in every session forever (§4.2). No `paths:` at all is the deliberate way to write a repo-wide rule |
| Hooks | `.claude/hooks/<name>.sh` + `.claude/settings.json` | shell `0755`; registration is `hooks.<Event>[].hooks[].command`, `${CLAUDE_PROJECT_DIR}`-relative. Exit 2 blocks and feeds stderr back (§4.3) |
| Permissions | `.claude/settings.json` | `permissions.allow` / `.ask` / `.deny`; `deny` wins (§4.7) |
| Skills | `.claude/skills/<name>/SKILL.md` (+ `references/`) | markdown + frontmatter; `name`, `description`, optional `allowed-tools` (§4.4) |
| Subagents | `.claude/agents/<name>.md` | markdown + frontmatter; `name`, `description`, `tools`, `model` (§4.5) |
| MCP | `.mcp.json` | JSON, `mcpServers`, env-var placeholders only (§4.6) |

Plus the four things it must refuse to do, which are the invariants of the whole product and the
reason the user can trust it with their config: never delete or reword the user's own instructions;
never touch a symlinked or vendored artifact; keep the index-doc tables in step with the files; and
re-verify after every change. It also carries **the inventory of what this run built** — path,
`agentify-id`, and what each artifact governs — which is why it is the **last** skill written.


#### 4.4.1 The description-writing rule (this is what drives invocation accuracy)

The `description` is the only part of a skill the model sees when deciding whether to use it. A
perfect skill body with a vague description is never invoked; a mediocre body with a precise
description gets used every day. Treat description authoring as the deliverable, not the label.

**The formula:**

```
<What it does: concrete verb + concrete object, naming this repo's real nouns>.
Use when <trigger condition>, or when the user says "<exact phrase>", "<exact phrase>", "<exact phrase>".
Not for <the nearest adjacent task that must NOT trigger this>.
```

**The rules:**

1. **Third person, one paragraph, under 1024 chars.** No "I", no "you", no "this skill".
2. **Use the user's literal words.** Pull the trigger phrases from `signals.json` —
   `request_shapes[].skeleton` and `request_shapes[].examples`, plus `slash_commands[].name` and
   `commands_requested[].command`. If the phrases are not traceable to a request shape with
   `count >= 3`, **the skill fails the evidence requirement and must not be built** — three is the
   skill bar (`mapping-rules.md` row 1, `blueprint.md` §1.4); `count >= 2` is the rule and hook bar
   (rows 5 and 4) and was mistakenly applied here. This gate is about *phrasing*, not about whether
   the skill is licensed at all: structural evidence licenses a skill on its own, so a repo with no
   transcript history is not thereby a repo with no skills — it is a repo whose skill descriptions
   are built from its code rather than from quoted requests. This is the link between the mining
   phase and invocation accuracy; it is not decoration.
3. **Name this repo's nouns.** "Adds an endpoint" is generic. "Adds a route under `src/api/` with a
   Zod schema, a service call and a Vitest integration test" is specific enough that the model can
   tell whether the user's request is this or something else.
4. **Include a negative boundary** whenever another skill, subagent, or plain editing is adjacent.
   "Not for X; that is Y." Mis-fires between two similar skills are the most common failure mode,
   and one clause fixes them.
5. **State the trigger conditions, not the implementation.** The body explains how; the description
   explains when.
6. **Never restate the name.** `description: Add API endpoint skill` carries zero information.
7. Avoid "helps you", "assists with", "utility for", and any phrasing that describes a category
   rather than an action.

**Naming:** kebab-case, verb-object (`add-api-endpoint`, `run-migration`, `review-pr`). Directory
name, `name`, and `agentify-id` are all the same string.

### 4.5 Subagents — `.claude/agents/<name>.md`

| | |
|---|---|
| Project path | `<repo>/.claude/agents/<kebab-name>.md` |
| User path | `${CLAUDE_CONFIG_DIR}/agents/<kebab-name>.md` (opt-in only) |
| Filename stem | Must equal the frontmatter `name`. |

**Frontmatter (VERIFIED (artifact + schema)):**

```markdown
---
name: pr-reviewer
description: |
  Reviews a diff for correctness, missing tests, and violations of this repo's conventions in
  .claude/rules/. Returns a severity-ranked finding list with file:line anchors. Delegate when
  the user asks to review a branch, a PR, or "the changes". Does not edit code.
tools: [Read, Grep, Glob, Bash]
model: inherit
agentify-id: pr-reviewer
agentify-version: 1
agentify-generated: 2026-09-05
agentify-evidence: 11 review requests across 8 sessions; 34% of commits touch no test file
---
<!-- Safe to delete or edit. -->

You are a code reviewer for this repository.
...
```

| Key | Required | Notes |
|---|---|---|
| `name` | yes | kebab-case, matches the filename stem. Lowercase and hyphens only — no `:`. **VERIFIED** (artifact). |
| `description` | yes | Drives **automatic delegation** — same authoring rule as §4.4.1, but the trigger is "when should the main agent hand this off", and it must state **what the subagent returns**. If the agent should never auto-trigger, say so explicitly ("Only invoked by `/x`. Never invoked by users directly." — a **VERIFIED** (artifact) pattern in the wild). |
| `tools` | no | **VERIFIED** (artifact) in two YAML spellings: a block list and an inline array (`[Read, Edit]`). Both are valid YAML; either parses. **Omit the key to inherit every tool.** Emit it only to restrict, and prefer the inline array. Note the bundle's own deprecation: **passing `Skill` in `tools` is deprecated — use the `skills` key instead** (**VERIFIED** (schema)), so never put `Skill` in an emitted `tools` list. |
| `model` | no | **Settled — the value set was UNVERIFIED and is not any more.** The bundle documents it as: a model alias (`fable`, `opus`, `sonnet`, `haiku`), a full model ID (e.g. `claude-fable-5`), or `inherit`; **if the key is omitted** the agent uses the configured default subagent model, and failing that the main model (**VERIFIED** (schema)). Agentify emits `inherit`, or omits the key entirely. Do not pin a named model in a generated file — it goes stale and it silently downgrades the user's session. |

**What 2.1.260 also accepts, and why agentify does not emit it.** `disallowedTools`,
`permissionMode`, `maxTurns`, `skills` (preload a named skill into the agent's context),
`mcpServers`, `memory` (`user` | `project` | `local` — auto-loaded agent memory under
`.claude/agent-memory/<agentType>/`), `effort`, `background`, `initialPrompt`, `observer`,
`observerMessage` (all **VERIFIED** (schema)). Two carry real risk in a generated file and are
worth naming so nobody adds them casually: **`memory`** turns on persistent state that agentify's
undo cannot reverse (the memory directory outlives the agent file), and **`permissionMode`** can
weaken the user's permission posture from a file they did not write. **Neither is ever emitted.**

**Body** is the subagent's system prompt: second person ("You are ..."), a narrow charter, and an
explicit output contract (what it returns and in what shape). A subagent runs in its own context
window, so it must be told what it does *not* have access to from the parent conversation.

### 4.6 MCP server drafts — `.mcp.json`

| | |
|---|---|
| Path | `<repo>/.mcp.json` (project-scoped, committed, shared with the team) |
| Format | JSON, single top-level `mcpServers` object |

**Exact shape (VERIFIED (artifact) — both transports observed in a real file):**

```json
{
  "mcpServers": {
    "playwright": {
      "command": "bunx",
      "args": ["@playwright/mcp@latest"],
      "env": { "PLAYWRIGHT_BROWSERS_PATH": "${PLAYWRIGHT_BROWSERS_PATH}" }
    },
    "linear-server": {
      "type": "http",
      "url": "https://mcp.linear.app/mcp"
    }
  }
}
```

- **stdio server:** `command` + `args`, optional `env`. `"type": "stdio"` is optional.
- **remote server:** `"type": "http"` + `url` (**VERIFIED** (artifact)), optional `headers`.
- `"type": "sse"` and `"type": "ws"` both exist in the schema (**VERIFIED** (schema) — no longer
  unverified) alongside internal-only `sse-ide` / `ws-ide` / `sdk` transports. `sse` is legacy and
  `ws` has no evidence-derived use case. **Emit `http` for remote servers and nothing else.**

**`.mcp.json` is discovered along the whole path, not just at the repo root** (**VERIFIED**
(schema)): Claude Code walks from the filesystem root down to the session cwd and merges an
`.mcp.json` from **every** directory on the way, closest-wins. Two consequences for the emitter: a
server name agentify adds at the repo root can be shadowed by a nested `.mcp.json` the user
already has, and the merge rule below must check the repo root file only — never rewrite a nested
one it did not create.

**Credential placeholder convention — no exceptions:**

1. **Never write a literal secret into `.mcp.json`.** Not a token, not a key, not a connection
   string. This file is committed.
2. Reference an environment variable: `"${LINEAR_API_KEY}"` in `env`, `headers`, or `args`.
   **Expansion is settled and this was the UNVERIFIED marker.** The expander's own pattern is
   `\$\{([A-Za-z_][A-Za-z0-9_]*(?::-[^}]*)?)\}` (**VERIFIED** (schema)), so exactly two forms work:
   **`${VAR}`** and **`${VAR:-default}`**. Bare `$VAR` does **not** expand in `.mcp.json`; always
   write the braces. Expansion runs for project, user and local scope (it is deliberately disabled
   for enterprise-managed config).
   **What happens when the variable is unset is the part the report must carry:** the reference
   expands to an **empty string**, the run logs `Missing environment variables: <NAME>`, and for a
   `url` specifically the server is marked with the error *"'url' … expanded to an empty string.
   Set the referenced environment variable, or update the server's config and reconnect."* It does
   not fail loudly at the point the user cares about. So the report still lists every variable and
   the exact `export` line — not because expansion is doubtful, but because a missing variable
   fails quietly.
3. Variable **names** come from `discovery.env_var_names` — names only. The analyzer never
   read the values and neither does the emitter.
4. **Never copy a credential you found in another config file.** Real `settings.json` and
   `config.toml` files in the wild contain live bearer tokens. Reading one is not permission to
   move it. If you encounter one, do not echo it, do not store it, and do not mention its value.

**The user authenticates — the tool never does.** Agentify does not run `claude mcp add`, does not
start an OAuth flow, does not launch the server, and does not verify connectivity (PRD §4). It
writes a draft and a checklist. Claude Code prompts the user to approve project-scoped servers from
`.mcp.json` on first use (**DOCUMENTED**); the report says so, lists each server, the exact env vars
to export, and the auth step per service.

**Merge rule.** If `.mcp.json` exists, parse it, add only **new** keys under `mcpServers`, and never
modify or remove an existing entry. On a name collision, skip, and record it as a skipped candidate
with the reason. If the file does not parse, do not touch it — write
`<plan-dir>/mcp.proposed.json` instead.

**Idempotency — no markers here either, and the placement is exact.** JSON has no comments, so this
file carries no `agentify:begin` / `agentify:end` pair and never can. **A key inside `mcpServers`
would be parsed as a server definition, so never put one there.** A key at the **top level**, beside
`mcpServers`, is not a server and is safe: `templates/mcp.json.tmpl` writes exactly one —
`_agentify`, carrying `agentify-id`, `agentify-version`, `agentify-generated`, `agentify-evidence`,
a `note` ending `Safe to delete or edit.`, `status`, `needs_you` and `remove`. Emit it, at the top
level only. *(An earlier version of this section banned `_agentify` outright while the template
emitted it; the template is the authority and the ban was over-broad — it was arguing against a key
inside `mcpServers`, which is still forbidden.)*

Rerun matches on the **server name** under `mcpServers`, cross-checked against the names recorded in
`<plan-dir>/build-manifest.json` (which `verify_artifacts.py` already consumes), and rewrites the
`_agentify` block whose `agentify-id` matches. List the servers in the `CLAUDE.md` agentify section
as well.

**Those two keys are the identity the undo removes.** `.mcp.json` is a structurally merged JSON
config, so it goes to the **JSON un-merge script** in `references/report-template.md` §3.1 and never
to the marker script — which would find no block, print `SKIP`, and exit 0. The script drops each
`mcpServers` name this run added and drops the `_agentify` object only when its `agentify-id` matches
the artifact's, leaving every server the user added by hand untouched; it deletes the file outright
only when agentify created it and nothing else is left in it. Note the asymmetry with §4.3 and keep
it straight: **`.mcp.json` carries `_agentify`; `settings.json` does not**, so the un-merge keys on a
server name here and on a command path there.

### 4.7 Permissions — the `permissions` block in `.claude/settings.json`

**Template:** `templates/settings-permissions.json.tmpl`, which owns the merge procedure, the rule
syntax and the manifest record. This section owns the target facts.

`permissions` is a top-level object in `.claude/settings.json` — the same user-owned file the hook
merge writes into, so both merges follow the same read-copy-merge-write discipline and the same
`pre_existing_sha256` capture. Three arrays, and **`deny` wins over `allow`** wherever the two
overlap; `ask` sits between them.

```json
{
  "permissions": {
    "allow": ["Bash(bun run test:*)", "Bash(git diff:*)"],
    "ask":   ["Bash(bun run db:migrate:*)"],
    "deny":  ["Read(./.env.local)", "Bash(npm install:*)"]
  }
}
```

Rule forms: `Bash(<prefix>:*)` for a command prefix, `Bash(<exact>)` for one literal command,
`Read(<glob>)` / `Edit(<glob>)` / `Write(<glob>)` for path access, `WebFetch(domain:<host>)` for a
host. `Bash` prefix rules are prefix matching and not shell semantics — `Bash(npm:*)` does not
catch `npx`, `pnpm`, or `npm` reached through a package script — and the plan entry says so rather
than implying the rule is airtight.

Four things this adapter will not do, and they are the difference between a useful block and one
the user deletes:

1. **Never allow a command the repo does not define.** Every `allow` entry cites a populated
   `discovery.commands` slot or a `commands_requested[]` row.
2. **Never allow anything that reads a secret** — no `.env*` glob, no credential path, and no
   wildcard wide enough to match one.
3. **Never deny a command the developer's own transcripts show them running successfully.**
4. **Never remove or reorder an entry agentify did not add.** If a user `allow` conflicts with a
   generated `deny`, keep both and say so in `report.md` — `deny` wins, so their entry silently
   stopped working and that is their call to resolve.

Precedence still applies (§1.3): an enterprise or user-level `settings.json` can already deny
something this block allows, and the higher level wins. Say it in the report rather than claiming
the allow took effect.

### 4.8 Plugin packaging — **not an artifact type**

agentify does **not** emit a plugin manifest. The setup it builds is derived from one repo's
evidence and personalized to it (`blueprint.md` §1.1 test 4), so a portable copy would be wrong
wherever it landed; the interview question that offered it is retired (`interview.md` §4.1).

What follows is kept because **`setup-manager` must know how this target's plugin system works** in
order to answer a user who asks about one — and because the facts were expensive to verify. None of
it is emitted by a run.

**Manifest (VERIFIED (artifact) fields, from real installed plugins):**

```json
{
  "name": "acme-agentic-setup",
  "version": "0.1.0",
  "description": "Repo-derived skills, agents and hooks for the acme monorepo.",
  "author": { "name": "Acme Engineering", "url": "https://github.com/acme" },
  "homepage": "https://github.com/acme/agentic-setup",
  "repository": "https://github.com/acme/agentic-setup",
  "license": "MIT",
  "keywords": ["acme", "internal"],
  "hooks": {
    "SessionStart": [
      { "hooks": [ { "type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/hooks/session-start.sh", "timeout": 5 } ] }
    ]
  }
}
```

`name` is the only required field (**VERIFIED** (artifact): a real manifest exists with just
`name`/`description`/`author`/`hooks`). `author` is **VERIFIED** (artifact) as an object with `name`/`url`, and
also **observed** as a plain string; emit the object. The `hooks` block uses the **same shape as
`settings.json`** (**VERIFIED** (artifact + schema)) — note that plugin hook groups in the wild omit
`matcher`, and that a plugin may declare the same block in `hooks/hooks.json` instead.

**Directory layout a plugin expects (VERIFIED (artifact + schema) against installed plugins):**

```
<plugin-root>/
  .claude-plugin/
    plugin.json          # manifest — required
    marketplace.json     # only if this repo also serves as a marketplace
  skills/<name>/SKILL.md # NOT under .claude/ — top level of the plugin root
  agents/<name>.md
  commands/<name>.md
  hooks/hooks.json       # a plugin may declare hooks here instead of in the manifest
  hooks/<name>.sh        # referenced from the manifest via ${CLAUDE_PLUGIN_ROOT}
  .mcp.json              # loaded — see below
```

The flattening is the part people get wrong: inside a plugin the directories are `skills/`,
`agents/`, `commands/` at the plugin root — **not** `.claude/skills/`. The bundle's own
"is this a plugin?" check looks for `.claude-plugin/` or any of
`commands/`, `skills/`, `agents/`, `hooks/`, `themes/`, `output-styles/`, `monitors/`,
`workflows/`, `SKILL.md`, `.mcp.json`, `.lsp.json` at the top level (**VERIFIED** (schema)).

**A plugin-level `.mcp.json` *is* loaded — this was the last UNVERIFIED marker in the file and it
is now settled the other way.** The bundle carries a plugin-loading flag whose own description is:
*"When true, the engine loads skills/hooks/agents/commands from this plugin but does NOT read its
`.mcp.json` or manifest `mcpServers`"* (**VERIFIED** (schema)). An opt-**out** only exists because
the default is to read it. So both a plugin `.mcp.json` and a manifest `mcpServers` block reach the
session.

That resolves the question but does not change what agentify builds: **a packaged plugin still
carries no MCP servers.** The reason is unchanged and is a policy, not a doubt — an MCP draft needs
the user to authenticate, and shipping one inside a distributable plugin moves that obligation onto
whoever installs it, in a file they did not review. MCP stays in the repo's own `.mcp.json` (§4.6),
where the person who has to export the variables is the person reading the report.

**Marketplace registration (VERIFIED (artifact)):** `.claude-plugin/marketplace.json` with `name`,
`owner: {name, url}`, and a `plugins` array whose entries carry `name`, `source`, `description`,
`version`, `author`, `homepage`, `repository`, `category`. `source` is **VERIFIED** (artifact) in two forms: a
relative path string (`"./plugin"`) and an object (`{"source": "url", "url": "https://....git"}`).

`${CLAUDE_PLUGIN_ROOT}` resolves to the plugin's installed root and is **VERIFIED** (artifact +
schema) as the correct way to reference files from inside a plugin manifest.

**Again: none of §4.8 is built by a run.** If a user asks for their setup to be packaged, that is a
`setup-manager` job with them in the loop, and the first thing it should tell them is which of the
generated artifacts name paths and conventions that exist only in this repo.

---

## 5. SMOKE TEST

Phase 8 runs these. Every check is local, read-only, and non-destructive. Two limits are real and
must be stated honestly rather than papered over:

- **Newly written project skills, agents and rules may not be visible in the session that wrote
  them.** Static validation runs now; live invocation is best-effort, and anything that cannot be
  exercised becomes an explicit "try this after restarting" line in `report.md`.
- **A hook added to `settings.json` does not apply to the current session.** Fixture-run the script
  directly; never try to trigger it through the live agent.

One check moved from "manual, after restart" to "runnable here" this round. **Rule loading can be
proved end to end without a restart**, because it is exactly the probe that settled §4.2: run a
fresh headless session in the repo and ask it to name a token that only the rule contains.

```sh
# Unscoped rule — must come back loaded.
claude -p "Print any codewords you see in your loaded context, else NONE. Do not use any tools."
# Path-scoped rule — must come back loaded only after a matching file is read.
claude -p "Read <a file matching the rule's paths:>. Then print every codeword you see."
```

This costs one model call each and is the only live confirmation in the whole verify phase. Run it
when a rule was built; skip it and record the manual version in the report when the user has asked
for no model calls during verification.

| Artifact | Command / invocation that proves it loads | Pass condition |
|---|---|---|
| Index doc | `test -f "$REPO/CLAUDE.md" && grep -cE '^[ \t]*<!--[ \t]*agentify:begin' "$REPO/CLAUDE.md"` | file exists; marker count is exactly `1`. **The grep must be line-anchored.** `index-doc-section.md.tmpl` quotes both marker strings inside backticks in the section's own "Removing this" instructions, so a plain `grep -c 'agentify:begin'` counts **2** on a correctly emitted block and this check fails on every run — measured 2026-09-05 on the Codex adapter's identical row. `verify_artifacts.py`'s `_MARKER` regex is line-anchored for the same reason. **Count the `end` marker the same anchored way and require `1` too** — `grep -cE '^[ \t]*<!--[ \t]*agentify:end' "$REPO/CLAUDE.md"` — and require the begin line to come first. Anchoring makes both counts right, but the two markers are not protected by the same thing, and only one of them is safe by construction: the quoted `begin` sits mid-sentence after `- This section: delete everything from `, so the anchor rejects it however the bullet is formatted; the quoted `end` **opens** its line and is rejected only because the template wraps it in a backtick. Measured 2026-09-05 on a rendered block — strip the backticks out of that bullet and the anchored `begin` count stays `1` while the anchored `end` count goes to `2`. Those backticks in `index-doc-section.md.tmpl`'s "Removing this" bullet are therefore load-bearing for this row *and* for `verify_artifacts.py`'s `marker_block()`, which would truncate the block at the quoted marker; if that bullet is ever reflowed or unquoted, both break together. On the same fixture `find_markers()` returns exactly two markers, one `begin` and one `end` — that is the count this row has to agree with. Then every `@import` and relative link target **inside the block** resolves — extract the block first, the same bounded way the Codex adapter's inline-rules row does, and only then scan it: `awk '/^[ \t]*<!--[ \t]*agentify:begin/{f=1} f{print} /^[ \t]*<!--[ \t]*agentify:end/{if(f)exit}' "$REPO/CLAUDE.md" \| grep -oE '@[^ ]+\.md' \| sed 's/^@//' \| xargs -I{} test -f "$REPO/{}"`. **Scanning the whole file is a false failure waiting to happen**: a dangling `@import` the user wrote above the block is not agentify's, and it fails this row on an otherwise correct build — measured 2026-09-05 on a fixture with one user-authored `@notes/missing.md` above a correctly emitted block, where the unbounded pipeline exits non-zero. Bound every marker-keyed check to the block, on both adapters. Manual follow-up in the report: open a new session and run `/memory` to confirm the section is loaded. |
| Rules | for each rule: `test -f "$REPO/.claude/rules/<name>.md"`; frontmatter parses; **every glob in `paths:` matches at least one real file in the repo** (`git ls-files '<glob>' \| head -1`); count the unscoped rules this run added | file exists and frontmatter parses. **A `paths:` glob that matches nothing is a fail** — the rule will never load and nothing will say so (§4.2). **More than 2 unscoped rules is a fail** — that is the context-rent cap. Missing from the `CLAUDE.md` index is now a **warning**, not a fail: the rule loads natively, the pointer is only for humans. Cross-rule contradiction checking belongs to `verify_artifacts.py`. |
| Hooks (config) | `python3 -c "import json;json.load(open('.claude/settings.json'))"` | exits 0; the pre-existing top-level keys are all still present (compare against the pre-build copy). |
| Hooks (script) | `test -x "<script>"` then `bash -n "<script>"` then a fixture run (below) | executable, parses, exits `0` on the benign fixture and `2` on the blocking fixture, and prints an actionable instruction on stderr when it blocks. |
| Skills | `test -f .claude/skills/<n>/SKILL.md`; frontmatter `name` equals the directory name; `len(description) < 1024`; description contains at least one trigger phrase traceable to `signals.json` | all static checks pass. Then, if the skill is already visible to this session, invoke it on one small real task from this repo (PRD §7.9) and require a plausible, error-free result; if it is not visible, record a manual check in the report. |
| Subagents | `test -f .claude/agents/<n>.md`; `name` equals the filename stem; frontmatter parses | static checks pass. Then, if visible, a `Task` dry-run with `subagent_type: <name>` and a trivial prompt, requiring only that it loads and returns; otherwise a manual check in the report. |
| MCP drafts | `python3 -m json.tool .mcp.json > /dev/null`; scan the file with `lib/scrub.py` patterns; check every `${VAR}` appears in the report's needs-you list | valid JSON, **zero scrub hits**, every placeholder documented. **Never attempt to connect to the server.** |
| Plugin manifest | `python3 -m json.tool .claude-plugin/plugin.json > /dev/null`; `name` present; every path referenced in `hooks` exists after `${CLAUDE_PLUGIN_ROOT}` substitution | valid JSON, required field present, no dangling script reference. |

**Hook fixtures.** Feed the event JSON on stdin, exactly as Claude Code would:

```sh
# Benign — must exit 0 and stay silent.
echo '{"session_id":"smoke","cwd":"'"$REPO"'","hook_event_name":"PreToolUse",
"tool_name":"Bash","tool_input":{"command":"git status"}}' | .claude/hooks/<name>.sh; echo "exit=$?"

# Blocking — must exit 2 and print an actionable instruction on stderr.
echo '{"session_id":"smoke","cwd":"'"$REPO"'","hook_event_name":"PreToolUse",
"tool_name":"Bash","tool_input":{"command":"npm install left-pad"}}' | .claude/hooks/<name>.sh; echo "exit=$?"
```

A hook that blocks the benign fixture is a **build failure**, not a warning: it will block the
user's normal work on their next session. Remove it, record it in the report, and continue.

Everything that could not be exercised goes into `report.md` under "verify these yourself", each
with the one command or action that verifies it, plus the removal instruction for the whole setup
(delete the branch, or delete the listed files and the `agentify:begin`/`agentify:end` blocks).

---

## Release checklist — re-verify before every release

Formats change; this file is the blast radius. Before tagging a release, re-verify each item below
against the **current** Claude Code documentation and a **fresh** install, then update the
`verified-against` date in the frontmatter. Do not fetch documentation at runtime — the analyzer
scripts make no network calls, and neither does this adapter.

Two mechanical shortcuts make this cheap, and both were used for the 2026-09-05 round. **Read the
shipped bundle**: the CLI is a single self-contained executable
(`~/.local/share/claude/versions/<version>`, or follow `$(which claude)`), its JavaScript is
embedded in plain text, and every schema in this file — hook events, hook definition keys, hook
stdin, SKILL.md frontmatter, subagent fields, MCP transports, the project-directory encoder — can
be read out of it with `strings` and a regex. That is the definition the program validates against,
so it settles "is this key real" outright. **Then probe the two things a schema cannot show**: the
path encoder (run a headless session in a scratch path full of odd characters, §2.2) and rule
loading (§4.2). Everything else is a file on disk.

- [ ] Detection env vars still exist (`CLAUDECODE`, `CLAUDE_CODE_ENTRYPOINT`, `CLAUDE_CONFIG_DIR`).
- [ ] `~/.claude/projects/<encoded>` encoding: confirm the substitution class is still
      `[^a-zA-Z0-9] → -`, that the length cap is still 200 with a base-36 hash suffix, and that the
      path is still resolved before encoding. *(Settled 2026-09-05 by probe; re-probe, do not
      assume.)*
- [ ] Session JSONL record types and the `user` record key set — both grew this round and neither
      is stable; the check is that the miner still reads only `type == "user"` and still `.get()`s
      every key.
- [ ] `CLAUDE.md` load behaviour and `@import` syntax, and the `.claude/CLAUDE.md` second location.
- [ ] **Rules still load natively** from `.claude/rules/` with no index-doc reference, and `paths:`
      still gates on-demand loading. Re-run the two-session probe in §5 — if this ever reverts, §4.2
      and the `capabilities.md` Rules row both have to move back.
- [ ] `SKILL.md` frontmatter keys, and whether `paths:` / `context: fork` should be promoted from
      "known, not emitted" to emitted.
- [ ] Agent frontmatter keys; re-check that `memory` and `permissionMode` are still on the
      never-emit list for the reasons in §4.5.
- [ ] Hook event list (33 as of 2.1.260), the matcher-group shape, the five hook `type` values, the
      per-event default timeouts, the exit-code table, the stdin field set, and that `timeout` is
      still seconds.
- [ ] `.mcp.json` transports and that the expansion pattern still accepts `${VAR}` and
      `${VAR:-default}` and still expands an unset variable to an empty string.
- [ ] `plugin.json` and `marketplace.json` field sets, the plugin directory layout, and
      `${CLAUDE_PLUGIN_ROOT}`.
- [ ] Settings precedence order.
- [ ] Run the full pipeline end-to-end against the repos in `test-repos.md` and diff the artifact
      counts against the expected values.

**Still open after this round.** These are the only two **UNVERIFIED** items left in this file, and
per the confidence key each names the one check that settles it and the guard that holds until then.

- [ ] **UNVERIFIED — is a `paths:` glob on a rule case-sensitive?** The match is gitignore-style
      against a computed repo-relative path, which is settled; case folding on a
      case-insensitive filesystem is not. A rule whose glob is wrong is a silent no-op, so this
      matters. **Check:** two rules in one repo, one scoped `SRC/**` and one `src/**`, then read a
      file under `src/`, and see which codeword comes back. **Guard until then:** §5 fails the
      build if a glob matches no tracked file, and agentify derives globs from real repo paths
      rather than writing them by hand, so the case always matches what is on disk.
- [ ] **UNVERIFIED — is a hook `matcher` a full match or a search?** i.e. does `matcher: "Edit"`
      also fire on `EditNotebook`. **Check:** a `PostToolUse` hook that appends to a file, plus one
      call to each tool. **Guard until then:** agentify only ever emits exact tool names and plain
      alternations (`Edit|Write`), so a false positive would over-fire a hook rather than miss one,
      and the benign fixture in §5 would catch an over-fire that blocks. This changes nothing
      agentify builds — it changes what the report may promise about a hook the *user* writes.
