# build-and-verify.md — phases 7 and 8, operational detail

**Read once, in phase 7. Keep it for phase 8.** `SKILL.md` phases 7 and 8 carry the gates, the exact
command lines and the stop conditions. This file carries what they point at: the type→template map,
the `build-manifest.json` field tables, the rationale behind each rule, the worked examples that
produced them, and the enumerated failure shapes. Every `§N` in those two phases is a section here.

**Line budget — new detail lands here, not in `SKILL.md`.** `SKILL.md` has a hard ceiling of **under
500 lines** (the skill contract), it is loaded in full on every run, and it has twice been pushed back
over that line by safety fixes appended to phases 7 and 8. So when a rule grows, split it: the gate,
the exact command line, the stop condition and the one sentence that must not be missed stay in
`SKILL.md`; the rationale, the measurements, the field tables, the worked examples and the failure
enumerations belong **here**, under a numbered `§` that the phase points at by name. Growing this file
costs nothing — phases 7 and 8 already read it — while growing `SKILL.md` costs another round of cuts.
Check with `wc -l skills/agentify/SKILL.md` before you commit an edit to it.

**One file rather than two, deliberately.** The manifest fields phase 7 writes (§5) are the exact
fields phase 8's undo reads (§8). Split across two files, the writer and the reader of one record
are documented apart — which is precisely the failure this file exists to close: an undo generated
from a remembered template line instead of from the record. Phases 7 and 8 also run back to back
inside one context, so keeping it costs one read, not two.

**Nothing here relaxes a rule in `SKILL.md`.** Where the two disagree about whether something is
*allowed*, `SKILL.md` wins. Where they disagree about a field name or a flag, run the command and
fix this file.

## 1. What is *not* in this file

| You need | Read |
|---|---|
| the path, format and frontmatter for an artifact type on this target | the **one** matched `adapters/*.md`, §4 (§2.2 here carries only the **write mode**, which the adapters do not) |
| whether a type is supported on this target at all | `adapters/capabilities.md` — the one table |
| the verifier's named checks and their severities | `references/verification.md` §2 |
| the live smoke test per artifact type (skills on a real small task from this repo, hooks against a fixture, rules for contradictions, subagents for load) | `references/verification.md` §§4–8 |
| the sections `report.md` must contain — built, skipped, needs-you, verification, three things to try tomorrow, rerun | `references/report-template.md` §2 |
| the wording of the removal section `report.md` prints | `references/report-template.md` §3.1 |
| the rehearsal that proves the undo before you publish it | `references/verification.md` §10 |

## 2. Artifact type → template

Read from `templates/` **only** the templates for types the approved plan actually contains.

| Plan artifact type | Template | On Codex |
|---|---|---|
| index doc | `index-doc-section.md.tmpl` | same body, appended to `AGENTS.md` |
| rule — prose | `rule.md.tmpl` | same |
| rule — command policy | — (no Claude Code equivalent; a `PreToolUse` hook does this job) | `codex-rules.rules.tmpl`; the `.rules` grammar and the mandatory validate-before-write are `adapters/codex.md` §4.2.2 |
| hook | `hook.sh.tmpl` **plus** `settings-hooks.json.tmpl` (script + registration) | `codex-hook.sh.tmpl` **plus** `codex-hooks.json.tmpl` — two files, not one parameterised pair, because a Codex hook decides in JSON on stdout and always exits 0 (`adapters/codex.md` §4.3) |
| skill | `skill.md.tmpl` | same file, same frontmatter |
| subagent | `subagent.md.tmpl` | `codex-agent.toml.tmpl` — TOML: `name`, `description`, `developer_instructions`, optional `model` / `model_reasoning_effort` / `sandbox_mode` (`adapters/codex.md` §4.5) |
| MCP config draft | `mcp.json.tmpl` | `codex-mcp.toml.tmpl`; the TOML draft body is `adapters/codex.md` §4.6 |
| permissions | `settings-permissions.json.tmpl` — a second merge into `.claude/settings.json` | `codex-rules.rules.tmpl` — the same file the command-policy rows write; the two are assembled once and validated once (`adapters/codex.md` §4.2.2) |
| reference doc | **none** — plain markdown; `mapping-rules.md` §3.1 gives the comment header it still carries | same |

**Every Codex artifact type now has its own template**, and this table used to say the opposite.
Confirmed by `ls templates/` on 2026-09-05: `codex-agent.toml.tmpl`, `codex-hook.sh.tmpl`,
`codex-hooks.json.tmpl`, `codex-mcp.toml.tmpl`, `codex-plugin.json.tmpl`, `codex-rules.rules.tmpl`.
The superseded paragraph said "four Codex artifact types have no template yet … built from the
adapter's §4 body instead" and named files that already exist — which sends phase 7 to a ~1300-line
adapter section for a body that has a reviewed template beside it, and loses the filling rules and
hazard notes only the template carries (`codex-rules.rules.tmpl`'s validate-before-write is the one
that matters most: a malformed `.rules` file bricks Codex in that repo). `mapping-rules.md` §3.1's
per-target template map has been correct throughout; the two now agree. **Reference docs remain the
only type with no template, on both targets, and that is deliberate** (`mapping-rules.md` §3.1).

The matched adapter's §4 is the authority on **where** each one lands on this target and on which
types it declares unsupported; §2.2 below carries the write mode, which decides the manifest fields.
`mapping-rules.md` §3.1 carries the same map from the candidate side, including the build-order note:
a reference doc is written inside the *skills* step, immediately after the skill that links it, so the
seven-step order in `SKILL.md` phase 7 step 5 still holds.

**There is no plugin-manifest row, and `plugin.json.tmpl` / `codex-plugin.json.tmpl` are never
read.** agentify does not emit a plugin manifest on either target (`adapters/capabilities.md`); the
two template files remain on disk only as reference material for `setup-manager`. A plan containing
a `plugin manifest` artifact is a phase-4 defect, not a phase-7 problem.

### 2.1 Marker spelling

`agentify:begin` / `agentify:end` is the only pair anything emits; `templates/index-doc-section.md.tmpl`
defines it. `verify_artifacts.py` also recognises `agentify:start`, **only** so that a rerun can find
and rewrite a block an older agentify wrote. That alias is backward compatibility, not a second legal
spelling — never emit it. Marker lines carry `id=<artifact-id>` and nothing else; version, date and
evidence go in the metadata comment immediately below the begin marker (§5.6). The separator between
an existing file's last line and the begin marker is **exactly one blank line** — the marker-removal
script in `report-template.md` §3.1 reclaims exactly that line, and only when the recorded SHA
proves it.

**A marker does not by itself mean block B.** The `[table]` block agentify appends to
`.codex/config.toml` carries the same `agentify:begin` / `agentify:end` pair in `#` comments, and its
undo is still block C: cutting a marked span out of TOML can silently re-bind the key below it to the
table above, which the marker script cannot see and the un-merge's TOML arm refuses (§2.4b, §5.3a).
The routing question is `merge`, not "are there markers".


### 2.2 Where each type lands, and **how** agentify writes it — per target

The matched adapter's §4 is the authority on the exact path and file body; `adapters/capabilities.md`
is the authority on whether the type is supported at all. This table is neither. It is the one thing
phase 7 needs that lives in neither place: **the write mode**, because the write mode is what decides
the manifest fields (§5.3a) and therefore the undo. Two targets today; a third adds a column and
changes no rule.

| Build step | Type | Claude Code — path · format · write mode | Codex — path · format · write mode |
|---|---|---|---|
| 1 | rule — prose | `.claude/rules/<name>.md` · markdown · **create** + an index-doc pointer | `<plan-dir>/rules/<name>.md` · markdown · **create** + an `AGENTS.md` pointer |
| 1 | rule — command policy | *(none — a `PreToolUse` hook does this job)* | `.codex/rules/agentify.rules` · Starlark · **create** |
| 2 | hook — script | `.claude/hooks/<name>.sh` · shell, `0755` · **create** | `.codex/hooks/<name>.sh` · shell, `0755` · **create** |
| 2 | hook — registration | `.claude/settings.json` · JSON · **merge** (§2.4a) | `.codex/hooks.json` · JSON · **merge** (§2.4a) |
| 3 | permissions | `.claude/settings.json` · JSON · **merge** (§2.4a), a second merge into the same file | *(none — folded into `.codex/rules/agentify.rules` at step 1)* |
| 4 | skill | `.claude/skills/<name>/SKILL.md` · markdown · **create** | `.agents/skills/<name>/SKILL.md` · markdown · **create**. Not `.codex/skills/` |
| — | skill reference doc | `.claude/skills/<name>/references/*.md` · markdown · **create** | `.agents/skills/<name>/references/*.md` · markdown · **create** |
| 5 | subagent | `.claude/agents/<name>.md` · markdown + frontmatter · **create** | `.codex/agents/<name>.toml` · TOML · **create** |
| 6 | MCP | `.mcp.json` · JSON · **merge** (§2.4a), env-var placeholders only | `<plan-dir>/codex-mcp.toml` · TOML · **draft** by default (§2.4c); **append-marked-table** into `.codex/config.toml` only on an explicit opt-in |
| 7 | index doc | `CLAUDE.md` · markdown · **append-marked** (or create) | `AGENTS.md` · markdown · **append-marked** (or create). Never `CLAUDE.md`: Codex does not read it |
| — | standalone reference doc | `<plan-dir>/*.md` · markdown · **create** | same |

**Build order is the same seven steps on both targets** — rules → hooks → permissions → skills →
subagents → MCP → **index doc last** — and the checkpoint after each type is unchanged. The index
doc moved from first to last: its tables enumerate what was written, so writing it first produced
rows pointing at files that did not exist yet (`blueprint.md` §9). On Claude Code steps 2 and 3
merge into the **same** `.claude/settings.json`, so capture `pre_existing_sha256` once, before step
2, and record two `merge` entry kinds against one modified-file entry. Codex
**substitutes nothing**: every type has a native, repo-scoped, committable home, MCP is a draft for
the same reason it is one on Claude Code (the user has to authenticate), and prose rules are a
convention wired from the index doc on both. **Any wording that still says Codex has no hooks and
gets an `AGENTS.md` instruction block plus a git hook instead is stale — Codex has 12 hook events and
a `hooks.json` (`adapters/codex.md` §4.3).** Native git hooks remain available on both targets as a
separate, opt-in, separately-approved artifact for commit-time enforcement, never as a substitute.

Three Codex facts that change what phase 7 can *claim*, all of which belong in the report rather than
in a silent assumption:

1. **Project trust gates the whole repo-scoped layer.** `AGENTS.md`, `.codex/hooks.json`,
   `.codex/config.toml` and `.codex/rules/` load only when `${CODEX_HOME}/config.toml` carries
   `[projects."<abs repo path>"] trust_level = "trusted"`. Agentify never edits that file. Untrusted
   or unlisted, every artifact above is silently inert — no error anywhere.
2. **A generated hook is installed, not armed.** Codex keys hook trust to a hash of the definition and
   the user arms it with `/hooks`. Phase 8 may prove the JSON loads and the script runs; it may not
   say the hook is live. Never emit or suggest `--dangerously-bypass-hook-trust`.
3. **Codex tool names are not Claude Code's.** A matcher ported as `^Bash$` never fires. Shell is
   `^(exec|exec_command|shell_command|run|local_shell)$`, edits are
   `^(apply_patch|Edit|Write)$`, and prompt/session/stop events take no matcher at all.

### 2.3 The four write modes — this is the spine the undo hangs on

Every byte agentify puts on disk goes in by exactly one of these, and the mode is recorded per
artifact (§5.3a) so phase 8 never has to guess from a filename.

| Write mode | What it does | Manifest | Undone by |
|---|---|---|---|
| **create** | writes a file that did not exist | `action: created`, no `merge` | `rm` (or the branch delete, when committed) |
| **append-marked** | appends one `agentify:begin` / `agentify:end` block to a text file that did exist | `action: modified`, no `merge`, `pre_existing_sha256`, `restore` | the marker script, block B |
| **merge** | splices entries into a parsed structure, or appends one marked `[table]` to a TOML file | `action` either, **`merge` present**, `pre_existing_sha256`, `restore` | the un-merge script, block C — the arm named by `format` |
| **draft** | writes a file the *user* applies by hand; nothing of theirs is touched | `action: created`, no `merge`, plus a needs-you item | `rm` |

**A type is not a write mode.** The same `hook` artifact is a *create* (the script) and a *merge* (the
registration) and they get two manifest entries. The same `mcp` type is a *merge* on Claude Code and
a *draft* on Codex. Read the mode off §2.2 for the target, never off the type.

### 2.4 Merge procedures — one per format

The adapter owns the file shapes; these are the steps phase 7 executes and the fields it must record.
All three end the same way, and that ending is not optional: **write to a temp file in the same
directory and `os.replace()` it in, record `pre_existing_sha256` (the hash *before* the change) and
`restore`, and write the `merge` record (§5.3a).** Without those three the file is changed and no
undo can find it.

**(a) JSON — `.claude/settings.json`, `.mcp.json`, `.codex/hooks.json`.**

1. Read the file. Absent: create it with the minimum shape the adapter names — `{"hooks": {}}` for
   Claude Code settings, `{"description": …, "hooks": {}}` for `.codex/hooks.json`.
2. Parse. **Does not parse ⇒ stop.** Never repair, never overwrite. Write the intended content to
   `<path>.agentify-proposed` and record a needs-you item.
3. Ensure the container exists: `hooks[<Event>]` an array, or `mcpServers` an object.
4. **Idempotency first.** Find a handler anywhere under that event whose `command` names
   `/.claude/hooks/<name>.sh` or `/.codex/hooks/<name>.sh`. Found ⇒ replace that one object in place
   and stop.
5. Otherwise append to the matcher group whose `matcher` equals yours — **groups are routinely shared
   with hooks the user wrote** — or append a new group when there is none.
6. Touch nothing else: no other event, no other group, no other top-level key. Preserve the file's
   indentation and trailing newline; the un-merge reproduces the pre-run bytes only if you do.
7. **Write no metadata key.** `templates/settings-hooks.json.tmpl` step 6 forbids merging `_agentify`
   into `settings.json`, and `.codex/hooks.json` accepts **exactly** `description` and `hooks` at the
   top level — an unknown key there made the whole file load **zero hooks, with zero warnings**
   (`adapters/codex.md` §4.3). `.mcp.json` is the one file that does carry `_agentify`. The identity
   everywhere else is the **command path**.
8. Record `merge: {"strategy": "json-entries", "entries": [["hook_command", <the registered command
   line>]]}` — or `["mcp_server", <name>]` per server — and `format: "json"`.

**(b) TOML — `.codex/config.toml`, and only on the opt-in write path.**

Default is (c): a draft. This path runs only when the interview said yes to writing the block, and it
refuses more often than it proceeds. `adapters/codex.md` §4.6 rule 3 is the contract; these are the
steps:

1. **Never `${CODEX_HOME}/config.toml`.** It is user-global, hand-maintained, and holds live
   credentials. Repo-scoped `<repo>/.codex/config.toml` only, and nothing outside the repo, ever.
2. File absent ⇒ this is a **create**, not a merge: write the block, `action: created`, and still
   record the `merge` record below, because the un-merge is what removes it if the user later adds a
   server of their own to the same file.
3. File present ⇒ **refuse and fall back to the draft** if any of: the table name already exists
   (`^\s*\[\s*mcp_servers\.<name>\b` or `…\.<name>\.`) — a duplicate header is a parse error that
   breaks their config; the file contains `"""` or `'''` — a line scan cannot then tell a real header
   from text inside a string; no Codex binary resolved, so step 6 cannot validate.
4. Normalise the file to end in exactly one newline, then append `"\n" + block`, where the block is
   **one complete `[table]` block, header first**, wrapped in `# agentify:begin id=<id>` /
   `# agentify:end id=<id>` comment markers. **Never append a bare key/value pair**: a `[table]`
   header ends the table above it, so a loose key binds to whatever table precedes it — measured, a
   `project_doc_fallback_filenames` line appended below a `[projects."…"]` header parsed clean and did
   nothing.
5. `os.replace()` it in.
6. **Validate**: `codex --strict-config app-server` parses the config and exits 1 with file, line and
   column *before* any auth or model call. Not `codex --strict-config exec`, which goes on to run a
   real turn. Fails ⇒ restore the pre-write bytes from `pre_existing_sha256` and record a needs-you
   item.
7. Record `format: "toml"`, `restore: span`, `pre_existing_sha256`, and
   `merge: {"strategy": "toml-table", "marker_id": "<agentify-id>", "entries": [["toml_table",
   "mcp_servers.<name>"], ["toml_table", "mcp_servers.<name>.tools.<tool>"]]}` — **one entry per
   `[table]` header inside the block**, in the order they appear. The un-merge refuses to cut a block
   that has since grown a header this list does not name.

> The markers in step 4 are what make this reversible, and they are the one requirement here that
> `adapters/codex.md` §4.6 does not yet spell out — it describes the block's `#` metadata header but
> not the begin/end pair. **Emit both.** Marking costs two comment lines that TOML ignores; not
> marking leaves the un-merge nothing to key on but a table name, which the user may also have used.

**(c) Draft — the default for MCP on Codex, and for anything needing credentials on either target.**

Write `<plan-dir>/codex-mcp.toml` (or `.mcp.json` with `${VAR}` placeholders on Claude Code), never a
literal secret, and put the exact destination path, the variables to export and the per-service auth
step in the report's needs-you section. A draft is a plain created file: no `merge` record, removed by
`rm`. On Codex use the dedicated env-var keys — `bearer_token_env_var`, `env_http_headers`,
`env_vars` — which take a variable **name**; `${VAR}` interpolation in arbitrary `config.toml` values
is unverified and unnecessary.

**(d) Marked text — every other file agentify adds to.** One `agentify:begin` / `agentify:end` block,
separated from the existing content by **exactly one blank line** (§2.1), `action: modified`, no
`merge` record, and the marker script is its undo. This is `CLAUDE.md`, `AGENTS.md`, a shell config, a
git hook — anything with a comment syntax that agentify appends to rather than merges into. **A TOML
config is the exception that proves the rule:** it has comments and it *is* marked, but it still gets
the `merge` record and block C, because cutting a marked span out of TOML can silently re-bind the key
below it (`report-template.md` §3.1 block C, measured).

## 3. Step 3 in full — the dirty tree, the pre-write capture, the ignore scan

### 3.1 Why `BASE_BRANCH` and `BASE_COMMIT` are read before the first byte

They are the only record of where the user was standing, and nothing recovers them afterwards. Phase
8 generates the undo from them: `git checkout <base_branch>` is what restores every `action: modified`
file **git had a pre-run copy of** — the `restore: head` ones in `committed_paths` — and an undo that
cannot name the user's branch cannot restore even those. The rest reach their undo through a script
(§5.3a), not through git. Read them
after the dirty-tree check and before the first artifact is written, then put both in the manifest
(§5.2).

Two shapes to carry rather than paper over. A **detached HEAD** gives an empty `BASE_BRANCH`; the
undo then says `git checkout <base_commit>` instead. A repo with **no commits yet** gives an empty
`BASE_COMMIT`; there is nothing to check out, so every artifact takes the per-file removal path.

The dirty-tree status excludes `$PLAN_DIR/` because all of it is agentify's own output — `plan.md`
was written at the phase 6 gate by design, and counting it as the user's uncommitted work would make
the gate refuse every second run. Nothing else is excluded, and **never `git stash` for the user**:
a stash is a mutation of their work, and the run has no way to prove it can put it back.

### 3.2 `git check-ignore -v` — reading the output and the exit code

One `<gitignore file>:<line>:<pattern>\t<path>` line per **ignored** path, and nothing for the rest.

| Exit | Means | Do |
|---|---|---|
| 0 | at least one path is ignored | record `ignored` + `ignored_by` per path (§5.3) |
| 1 | **no path is ignored** — the ordinary answer, not an error | record `ignored: false` for all, continue |
| >1 | a real failure (bad usage, unreadable `.gitignore`) | say so; treat every path as potentially ignored and prefer the per-file undo |

Two properties are what make the scan usable *before* the build rather than after:

- **It answers for paths that do not exist yet.** The approved plan names every path, so the scan
  can run at the boundary, and the user can be told before the first byte is written.
- **It consults the index.** A tracked path reads as not-ignored even when a pattern matches it —
  which is the right answer, because the only question being asked is *"will a plain `git add`
  commit this?"*

### 3.3 Worked example — a repo that ignores `.claude/`

Measured on a clone of `vercel/turborepo`, whose `.gitignore` line 6 is `.claude/`. On this target
that is most of the build: of 9 generated artifacts, 4 were committable and 5 — three rules, the
hook script and `settings.json` — were not. The old single-mechanism report told the user that
deleting the branch removed everything; it removed 4 of 9, and its verification sentence was false in
the same way, because `git status` reads clean when the remaining paths are ignored.

Say it out loud before the first byte: the ignored paths, the pattern excluding them, and that a
second explicit step removes them, not the branch delete. Do **not** offer to commit them anyway
(§4.2).

## 4. Step 4 in full — the commit, the partition, and `git add`

### 4.1 The two disqualifiers

**A path goes on the branch only if the branch delete can put it back.** Everything else — `created`,
or `modified` with `restore: head` — is committable and goes in `committed_paths`. Two classes go in
`uncommitted_paths` instead:

1. **`ignored: true`** (§3.2). Git will not add it, so the branch cannot hold it, so the delete
   cannot remove it.
2. **`action: modified` with `restore: span`** (§5.3). Git has no pre-run copy of that file on
   `BASE_COMMIT`, so `git checkout <base_branch>` does not *restore* it — it **deletes** it, along
   with the user's own content. Measured on a fixture: a hand-written, untracked
   `.claude/settings.json` that the run appended to was committed by phase 7 and destroyed,
   directory and all, by the undo.

A `restore: span` entry sitting in `committed_paths` is a data-loss bug, not a reporting one —
`verification.md` §10.1 stops the run on it. The two lists, not `mode`, are what phase 8 generates
each removal step from (§8).

### 4.2 Why never `git add -f`

`.gitignore` is the user's declared intent. Force-adding writes machine-local config into a branch
they may push or merge, and agentify may not rewrite history to take it back out (PRD §13 forbids the
destructive git commands that would be needed). The cost of not forcing is a two-step undo instead of
two lines, which `report-template.md` §3.1 generates and states plainly — a much smaller price than a
surprise in someone's PR. This is settled (`docs/DECISIONS.md` §2.15); do not re-open it per run. If
the removal steps ever feel too long, the fix is to ask the user at the **plan gate** whether to build
into an ignored directory at all — never to override their `.gitignore`.

### 4.3 Why one `git add` over a mixed list is not an option

`git add -- <all paths>` over a list holding one ignored path exits 1, prints
`The following paths are ignored`, and *stages the rest anyway*: the build looks fine while the
ignored artifacts quietly miss the commit. `git add -A` is worse — exit 0, no message at all. So `git add` takes `committed_paths`
only, in every mode.

### 4.4 Proving the commit — enumerate the branch, never one commit

Prediction is not proof, and neither is one commit. The enumeration is a **diff against the base**:

```bash
git -C "$REPO_ROOT" diff --name-only "$BASE_COMMIT".."$branch_name" | LC_ALL=C sort -u
```

Every `committed_paths` entry must appear in it and nothing from `uncommitted_paths` may. Correct both
lists from what it prints, not from the step 3 prediction — **a path in neither list is a file no undo
removes**, and that is the defect the whole partition exists to prevent.

**`git show --name-only --pretty=format: "$branch_name"` is the wrong instrument, and it shipped here
in three places.** `git show` prints one commit — the branch tip — and a branch-mode run commits
**twice**: phase 7 commits the artifacts, phase 8 commits `report.md` and the manifest. So it returns
a *partial* set, and `committed_paths` gets corrected from a partial set, which is the undo's own
bookkeeping built on a subset of the truth. Two measurements, both on a two-commit branch:

| command | what it returned |
|---|---|
| `git show --name-only --pretty=format: <branch>` | `build-manifest.json`, `report.md` — the phase 8 commit only |
| `git diff --name-only <base>..<branch>` | `.claude/skills/s1.md`, `README.md`, `build-manifest.json`, `plan.md`, `report.md` |

The axios dogfood run hit exactly this: it listed `CLAUDE.md`, `build-manifest.json` and `report.md`,
and not `plan.md`, which was in the first commit.

The second failure is worse and is the reason to stop using `git show` here rather than just adding a
range to it. **On a branch with nothing committed, `git show --name-only <branch>` prints the base
commit's file list** — verified: a fresh branch off a base holding `README.md` printed `README.md`,
exit 0. That is the §10 "branch that held nothing" failure handed a *false positive* by the very check
meant to catch it: an artifact sharing a name with a base-commit file would read as covered.
`git diff --name-only <base>..<branch>` prints nothing on that branch, exit 0, which is the truth.

Use `$BASE_COMMIT` from the manifest, not `$BASE_BRANCH`: the two agree on a healthy run, and if the
base tip has moved (a PRD §13 violation, caught in `verification.md` §10.2) the commit is the value
that still names where the branch started. Two-dot and three-dot are equivalent here because the
branch is cut from `BASE_COMMIT`, so the merge base *is* `BASE_COMMIT`; two-dot is written because it
is the form that stays correct when someone substitutes a bare commit for a ref. And if `BASE_COMMIT`
is empty — the repo had no commits before the run — there is no base to diff against and the branch is
the entire history: `git log --name-only --pretty=format: "$branch_name"` instead, verified to return
both commits' paths on a no-base fixture.

The commit itself is not optional. A branch with nothing committed to it deletes without removing a
single file: `git branch -D` prints `Deleted branch`, exits 0, and reverses nothing, because the files
were loose in the working tree the whole time. That undo shipped and was wrong twice
(`docs/DECISIONS.md` §2.14).

## 5. `build-manifest.json` in full

Phase 8 cannot run without it, and it is the only place the undo facts outlive the run. One JSON
object at `$REPO_ROOT/$PLAN_DIR/build-manifest.json`. `verify_artifacts.py` ignores every key it does
not know, so the undo record below is additive to the shape its module docstring documents — that
docstring is authoritative for the **required** fields, this section for the undo ones.

### 5.1 Top-level fields

| Field | Value |
|---|---|
| `schema_version` | `1` |
| `tool` | `"agentify"` |
| `generated` | `<yyyy-mm-dd>` |
| `target` | `claude-code` or `codex` |
| `repo_root` | absolute path |
| `plan_dir` | the confirmed `plan_dir` from the phase 5 answer record |
| `artifacts[]` | §5.3 |
| `_agentify` | §5.5 |
| the undo record | §5.2 — flat top-level keys |

### 5.2 The undo record

Flat top-level keys. Phase 8 generates every removal step from these and from nothing else.

| Field | Value |
|---|---|
| `mode` | `branch` · `stage-only` · `no-git` |
| `branch` | the branch name, or `null` |
| `base_branch` | where the user was standing; `""` when HEAD was detached |
| `base_commit` | HEAD before the run; `""` when the repo had no commits |
| `committed` | did the branch commit happen |
| `pushed` / `pr_url` | **never set.** agentify does not push and does not open a pull request (`SKILL.md` phase 8 step 6). The keys are read on a rerun so a branch an older agentify pushed can still be cleaned up; nothing in this version writes them |
| `created_dirs` | repo-relative, **deepest first**, only directories this run brought into existence |
| `committed_paths` | every artifact path the branch commit holds (§4.4 proves it) |
| `uncommitted_paths` | every artifact path it does not (§4.1) |

`committed_paths` and `uncommitted_paths` **partition** the artifact paths: every path is in exactly
one, and a path in neither is a file no undo removes. In `stage-only` and `no-git` mode
`committed_paths` is what was staged (nothing at all, with no git repo) and `uncommitted_paths` is the
rest — the names describe the *undo mechanism*, not the mode.

### 5.3 Per-artifact fields

Required, checked by `verify_artifacts.py`: `id` (kebab-case, unique), `type` (§5.4), `path`
(repo-relative, inside the repo), `action` (`created` or `modified`), `evidence` (non-empty, one line
with counts, byte-identical to the file's own `agentify-evidence`). `command` is required on hooks
when the registered command line differs from `path`; `name` is optional.

Added by agentify for the undo, per artifact and never once per run:

| Field | On | Value |
|---|---|---|
| `ignored` | every entry | boolean, from §3.2 |
| `ignored_by` | `ignored: true` only | the `<file>:<line>:<pattern>` `check-ignore` printed |
| `pre_existing_sha256` | every `modified` entry | `shasum -a 256` of the file **as it was before the run** |
| `restore` | every `modified` entry | `head` when git had the file tracked and unmodified at step 3, else `span` |

An ignored file is almost always untracked, so it takes `restore: span`, and its appended block
survives a branch delete until the marker-removal script takes it out.

### 5.3a `format` and `merge` — the two fields that pick the undo

`restore` answers *can git put this file back*. These two answer the other question — *how was the
file changed* — and phase 8 reads them instead of recognising a filename. That distinction is not
cosmetic: the un-merge script was keyed on the literal pair `.claude/settings.json` and `.mcp.json`,
so on a Codex run `.codex/hooks.json` and `.codex/config.toml` were matched by no rule, reached no
mechanism, and survived their own undo while the report reported success (`report-template.md` §3.1).

| Field | On | Value |
|---|---|---|
| `format` | **every** entry | `markdown` · `json` · `toml` · `shell` · `starlark` · `text`. The file's actual format, not its extension's reputation. It picks block C's arm |
| `merge` | every entry agentify **merged into** — §2.3's third row, and only that row | the object below. **Absent** on a create, a draft, and an append-marked text file: absence is what routes a file to `rm` or to the marker script |

```json
"merge": {
  "strategy": "json-entries",
  "entries": [["hook_command", "${CLAUDE_PROJECT_DIR}/.claude/hooks/enforce-bun.sh"]]
}
```

| Key | Value |
|---|---|
| `strategy` | `json-entries` — entries spliced into a parsed JSON object · `toml-table` — one marked `[table]` block appended to a TOML file. One arm of block C's script per value; a new target's new way of merging adds a value and an arm, and changes nothing else |
| `entries` | `[kind, value]` pairs, and each kind is the identity the emitter actually leaves behind: `hook_command` (the registered command line — the whole of agentify's mark in `settings.json` and in `.codex/hooks.json`, both of which forbid a metadata key), `mcp_server` (a server name under `mcpServers`), `toml_table` (one per `[table]` header inside the appended block, in file order) |
| `marker_id` | `toml-table` only: the id in the `agentify:begin` / `agentify:end` comment pair. Same string as `agentify-id` |

Three rules this record has to satisfy, all of them load-bearing:

1. **It is written by the step that does the merging, not reconstructed later.** `pre_existing_sha256`
   is only knowable before the write; `entries` is only knowable by the code that decided what to
   splice.
2. **One artifact entry per file agentify changed**, not per candidate. A hook is two entries — the
   script (`create`) and the registration (`merge`) — because they are two files with two undos.
3. **A `merge` record and `restore: head` can coexist**; a merge record and a *missing*
   `pre_existing_sha256` cannot. The un-merge prints its byte proof from that hash, and without it the
   most it can say is "entries removed", which proves the file changed and not that it is correct.

### 5.4 The `type` enum

`skill`, `subagent`, `rule`, `hook`, `index-doc`, `settings`, `mcp`, `plugin`, `command`, `reference`,
`plan`, `report`, `manifest`, `other`. A type outside the list is checked as `other` and warned about.
Common synonyms are accepted (`agent` → `subagent`, `build-manifest` → `manifest`, **`permissions` →
`settings`**). `manifest` is a JSON type and is exempt from the markdown-only checks exactly as
`settings`, `mcp` and `plugin` are.

**A permissions artifact is a `settings` entry, not a type of its own.** The plan calls it
`permissions`, because it is a distinct proposal the user approves or drops by number. The manifest
does not: `permissions` and the hook registrations merge into the **same** `.claude/settings.json`,
and §5.3 rule 2 is one artifact entry per *file*. So that file gets **one** entry — `type: settings`,
`format: json`, `action: modified`, `restore: span`, one `pre_existing_sha256` captured before the
first of the two merges — whose `merge.entries` carries both kinds:

```
("hook_command",     "<the hook artifact's manifest `command`>")
("permission_entry", "allow:Bash(bun run test:*)")
("permission_entry", "deny:Read(./.env.local)")
```

The un-merge script removes exactly those and leaves every sibling key and every entry the user
wrote by hand (`report-template.md` §3.1 block C). Getting this wrong in the other direction — two
manifest entries for one file — makes the un-merge run twice against the same path and the second
run report entries it cannot find.

**`plugin` stays in the enum and nothing emits it.** agentify no longer builds a plugin manifest
(`adapters/capabilities.md`); the value is kept so a rerun over a repo an older agentify wrote into
can still read that manifest and undo it.

**The enum is target-agnostic and Codex artifacts map onto it without a new value:**

| Codex file | `type` | `format` | Why |
|---|---|---|---|
| `AGENTS.md` | `index-doc` | `markdown` | same role as `CLAUDE.md` |
| `.codex/hooks.json` | `settings` | `json` | it is the hook **registration** file — `settings` is what routes it to the un-merge script, exactly as `.claude/settings.json` is routed |
| `.codex/hooks/<name>.sh` | `hook` | `shell` | the script itself |
| `.codex/config.toml` | `mcp` | `toml` | the only thing agentify ever writes into it is an MCP block |
| `<plan-dir>/codex-mcp.toml` | `mcp` | `toml` | the draft — a created file, no `merge` record |
| `.codex/rules/<name>.rules` | `rule` | `starlark` | a command-approval policy; the prose rules are `rule` + `markdown` |
| `.codex/agents/<name>.toml` | `subagent` | `toml` | |
| `.agents/skills/<name>/SKILL.md` | `skill` | `markdown` | |
| `.codex/rules/agentify.rules` (permissions) | `rule` | `starlark` | on Codex the permission surface **is** the command policy — one file, one entry, never a second `settings` row |

Two of those rows are ahead of `verify_artifacts.py` today and will read as failures until it catches
up — say so in the run rather than mistyping the artifact to dodge the check:

- **A `type: mcp` artifact whose `format` is `toml`.** `MERGED_JSON_TYPES` routes it to the un-merge
  script, which is right, and then the checker tries `json.loads` on it and reports *"routed to the
  JSON un-merge script but it is not valid JSON"*. The fix is one condition — read `format` before
  parsing — not a different `type`.
- **A non-markdown artifact typed `rule` or `subagent`.** `JSON_TYPES` exempts JSON from the
  markdown-only checks; a Starlark `.rules` file and a TOML `.codex/agents/*.toml` need the same
  exemption, keyed on `format` rather than on a widening list of type names.

### 5.5 agentify's own three entries, and when each is added

`plan.md`, `report.md` and the manifest are generated files like any other and are verified like any
other. Ordering matters:

- **`plan` and `manifest` are written now, at build time.** Without them the undo leaves both behind,
  and a manifest nothing checks is how a run once shipped with no `agentify-id` in it at all.
- **The manifest may list itself.** Its own checks are existence, non-emptiness, valid JSON and the
  `_agentify` identity — none of which depends on its content — so appending an entry afterwards does
  not invalidate the earlier pass.
- **`report` is appended in phase 8**, after the report exists (`verification.md` §9 step 6). Listing
  it at build time is a guaranteed `file_exists` FAIL.

`_agentify` is the inert top-level identity object, carrying `agentify-id: build-manifest`,
`agentify-version`, `agentify-generated`, `agentify-evidence` and a `note` ending
`Safe to delete or edit.` JSON cannot hold a comment header, so this is how the manifest carries its
own identity; omit the note and the `metadata` check warns.

### 5.6 The metadata every generated file carries

`agentify-id: <kebab-name>`, `agentify-version: 1`, `agentify-generated: <yyyy-mm-dd>`,
`agentify-evidence: <one line with counts>`, and the line `Safe to delete or edit.` — in frontmatter,
or in a comment header for non-markdown, or in the metadata comment directly below a begin marker.
The evidence line is the *same string* the candidate carried in phase 4 and the plan carried in phase
6; `evidence_match` is a FAIL when the three differ. A rerun matches on `agentify-id` and rewrites in
place, never appending a second copy.

## 6. Build-time failure shapes

| Shape | Do |
|---|---|
| a checkpoint fails | stop that type, keep what is written, record it, continue with the next type |
| a template is missing for an approved type | skip that artifact, record it as abandoned with the reason, continue |
| the adapter declares the type unsupported on this target | it should have been cut in phase 4; do not improvise a substitute — record and skip |
| a path would land outside the repo | never write it; `path_containment` would FAIL it in phase 8 anyway |
| the user says stop at a checkpoint | stop building, keep the manifest accurate for what exists, and go to phase 8 with what was built |
| a config agentify merged into has no `merge` record | fix it before phase 8 — an entry with no `format`/`merge` reaches `rm` or the marker script, and both are wrong for it (§5.3a) |

Five more that are Codex-only, and every one of them is silent unless phase 7 says it out loud:

| Shape | Do |
|---|---|
| the repo is not trusted — `discovery.existing_agentic_config.codex.repo_trust_level` is missing or `untrusted` | build anyway; the artifacts are correct and committable. Put the `trust_level = "trusted"` line, and the fact that **nothing loads without it**, in the plan's capability notes and at the top of the report's needs-you. Never edit `${CODEX_HOME}/config.toml` to set it |
| `.codex/hooks.json` does not parse, or holds an unknown top-level key | stop on that file (§2.4a step 2). An unknown top-level key makes Codex load **zero hooks with zero warnings**, so never add one — not `_agentify`, not anything |
| the `config.toml` append contract refuses (table exists, multi-line string, no binary to validate with) | fall back to the draft, and say **in the plan, before the build** which servers took which path and why. A silent downgrade is a promise the report then has to break |
| a hook matcher was written with Claude Code tool names (`^Bash$`, `^Write$`) | fix it to the Codex vocabulary (§2.2). It parses, loads, and never fires — a real repo on this machine ships that mistake |
| `codex` did not resolve (§1.3 of the adapter) | build; skip the smoke tests that need it, skip the `config.toml` write path entirely, and record both in the report |

A build that stops early is still a run that must reach phase 8: the manifest and the report are what
make a partial build removable.

## 7. Phase 8 — the static pass, in detail

`verification.md` §2 owns the check table and every severity; read each `checks[]` row by its literal
`name` against it. What `SKILL.md` phase 8 step 1's command line is doing:

- **`--manifest` resolves against the process's cwd, not against `--repo`.** A repo-relative value
  exits 1 with `manifest not found: <cwd>/<value>`, which reads as "the build is broken" when it
  means "the path was relative". Pass the absolute `"$REPO_ROOT/$PLAN_DIR/build-manifest.json"`
  (`verification.md` §2.1 spells it the same way). `--manifest -` reads the manifest from stdin.
- **`--discovery` is optional to the script and mandatory to this phase.** It turns on the half of
  `rule_contradiction` that compares each rule against what the repo demonstrably does — the only
  half that can FAIL. A rule saying "use npm" in a repo with `bun.lock` is caught by nothing else, so
  a run without the flag ships that rule and reports clean. Without it the PASS row says
  `…conventions NOT checked`, in as many words.
- **It executes nothing** unless `--exec-hooks` is passed, and that needs the explicit yes described
  in `verification.md` §5.1 — never inferred from an earlier answer. `--no-exec` is the default and
  wins if both are given.

A failed check is data, not a crash: a manifest full of failures still exits 0, and `summary` is what
phase 8 reports. Exit 1 means the manifest could not be read at all, and then `checks` is `[]` and
`summary` is all zeros — which is *not* the same thing as everything passing.

## 8. Phase 8 — generating the undo from the manifest

`mode`, `branch`, `base_branch`, `base_commit`, `created_dirs`, `committed_paths`,
`uncommitted_paths`, and each artifact's `path`, `ignored`, `restore`, `pre_existing_sha256`,
`format` and `merge` all come out of `build-manifest.json` — never from a remembered command line,
never from a fixed template line, **and never from recognising a path**. **`mode` alone does not
choose the undo; `mode` plus the partition does** — and for everything the partition sends to a
script, `format` plus `merge` choose which script and which arm (§5.3a, `report-template.md` §3.1).

| `mode` | `uncommitted_paths` | Undo block in `report-template.md` §3.1 |
|---|---|---|
| `branch` | empty | the two-line branch delete, and nothing else |
| `branch` | non-empty | the branch delete **plus** the explicit per-file removal for what it cannot reach |
| `stage-only` | (all paths) | the numbered per-file list: unstage, delete, `rmdir` deepest first, restore appended files |
| `no-git` | (all paths) | the same list without the git steps, plus the marker-block script |

Blocks B and C are chosen per artifact, not per target: a run is `merge`-free and prints neither, or
it merged into a config and prints C, or it appended to a text file and prints B, or both. **On both
targets, every run that builds a hook prints block C**, because registering a hook is a merge into
`.claude/settings.json` or `.codex/hooks.json`.

Then run `verification.md` §10, which *exercises* the removal steps rather than describing them, and
whose §10.2 (still `verification.md`) fails the run when any manifest artifact is in neither the branch commit nor the report's
per-file list.

## 9. The final summary — the three exact wordings

Phase 8 step 7 says the undo out loud, worded for the mode and naming which files each mechanism
removes.

- **Branch, `uncommitted_paths` empty:**
  `Everything is committed on <branch>; you are back on <base_branch>, which was never committed to.
  To undo the run: git checkout <base_branch> && git branch -D <branch>.`
- **Branch, `uncommitted_paths` non-empty:**
  `<N> files are committed on <branch> and go away with git checkout <base_branch> && git branch -D
  <branch>. <M> more were never committed — <reason> — so the branch delete does not touch them;
  report.md step 2 removes those by name.`
- **Stage-only and no-git:**
  `Nothing was committed and no branch exists — the undo is the numbered list under "How to remove
  everything" in report.md.`

On Codex, add one sentence to whichever of the three you print, because without it the user will
reasonably believe the setup is running: `Codex loads this repo's .codex/ layer only if the project is
trusted, and hooks are installed but not armed until you run /hooks — both steps are in report.md.`
Do not soften it and do not offer a bypass flag.

`<reason>` is the honest one from the manifest: `gitignored` for `ignored: true`, or
`git had no pre-run copy to restore` for `restore: span`. The checkout half is not optional in either
branch wording: `git branch -D` refuses to delete the branch you are standing on, and moving back to
`<base_branch>` is what restores every `action: modified` file. Detached HEAD before the run means
`git checkout <base_commit>` instead.

## 10. Phase 8 failure shapes

| Shape | Do |
|---|---|
| `verify_artifacts.py` exits 1 | the manifest is missing or unparseable — fix the manifest and rerun it; never hand off an unverified build and never fake results |
| a check `fail` on an artifact | fix and re-test it, or remove it and move it to the report's Skipped table with `failed verification and was removed` |
| a live test hangs past ~60s | `warn`, not a hang — kill it, record it, move on |
| `verification.md` §10.2 finds a path in neither mechanism | the manifest is wrong, not the report — go back and fix the partition before writing the removal section |
| the report is written but not committed in `branch` mode | commit it; whatever is left uncommitted outlives the branch delete and makes "removes everything" false again |
| a Codex hook does not come back from `hooks/list` | check, in order: the event name's exact CamelCase (a wrong one loads zero hooks silently), an unknown top-level key in `hooks.json` (same silence), and project trust. Report which; never claim the hook is live |
| a Codex artifact's un-merge cannot be rehearsed because `codex` is absent | `warn`, and say the JSON was validated structurally but not by the binary. Never skip block C over it — the un-merge is plain Python and needs no Codex |
