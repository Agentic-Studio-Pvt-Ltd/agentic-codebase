# report-template.md — phase 8 skeleton for `PLAN_DIR/report.md`

Read this file in **phase 8 (Verify and hand off)**, after verification has run. `PLAN_DIR` is
the interview's `plan_dir` answer, default `docs/agentic-setup/`.

The report is the record of what actually happened, not a restatement of the plan. If an
artifact was in the plan but failed verification and was removed, the report says so. A report
that disagrees with the filesystem is worse than no report.

---

## 1. Rules

1. **Report reality.** Every row comes from the build manifest and the `verify_artifacts.py`
   output, not from the plan. Cross-check the file list against the filesystem before writing.
2. **Replace every ALL_CAPS token.** A leftover token is a bug.
3. **"Needs you" items are numbered, one step per line, copy-pasteable, and each carries the reason
   agentic-codebase stopped there.** No "configure your credentials" hand-waving — name the file, the key,
   and the command. The section covers two things, not one: credentials agentic-codebase must never hold,
   **and** every check verification recorded `not tested` because it could not reach it — project
   trust, hook trust, a session that must be restarted (`verification.md` §5.3, §9 step 5). Those
   are the difference between a setup that is installed and one that is running, so they are steps,
   not footnotes, and what blocks the whole setup is numbered first. §3.2 has the shapes.
4. **"Try tomorrow" items must be derived from artifacts that were actually built** and must be
   things the user can literally type. Never generic advice.
5. **The removal section is generated from `build-manifest.json`, never copied from section 3.1
   as-is.** It names the real `mode`, the real `branch` and `base_branch`, the real
   `committed_paths` / `uncommitted_paths` partition, every real created path and directory, and
   every appended-to file with its `agentic-codebase-id`. Someone must be able to undo this run without
   reading anything else, and the commands must be the ones `verification.md` §10 actually ran.
   A static undo line is the defect this rule exists to prevent, and it has shipped in three shapes:
   a branch delete on a branch nothing was committed to succeeds, says `Deleted branch`, and removes
   nothing; a branch delete on a branch that holds only the paths `.gitignore` allowed onto it
   prints the same line, leaves plain `git status` clean, and leaves every ignored artifact on disk;
   and the marker-removal script pointed at `.claude/settings.json` prints
   `SKIP .claude/settings.json: no agentic-codebase block id=…`, **exits 0**, and removes nothing, because
   JSON cannot carry a marker comment and that file was never marked — it was structurally merged.
   The fourth shape is the same bug one level up: the un-merge script **keyed on a hardcoded pair of
   filenames** (`.claude/settings.json` and `.mcp.json`), so a Codex run's `.codex/hooks.json` and
   `.codex/config.toml` matched no rule, reached no mechanism, and the hook agentic-codebase registered in
   the user's config survived an undo that reported success — measured, §3.1.
   **`mode` alone never picks the undo. Two questions pick it, in this order: can git put this file
   back (the partition), and — when it cannot — how was the file changed?** The second question is
   answered by the manifest, from the artifact's `format` and its `merge` record
   (`build-and-verify.md` §5.3a) — **never by recognising a filename**, which is what made the same
   defect ship four times under four names. No sentence in this report may say the branch delete
   removes a file that is in `uncommitted_paths`, and no removal step may be a script that answers
   `SKIP` — or nothing at all — for the file it was handed.
6. **The footer is fixed text** (section 4). Reproduce it character for character. It is one of
   exactly three attribution placements — do not put attribution anywhere else in this file, and
   never in the runtime behavior of a generated skill or agent.
7. **Write this file even when the run went badly.** A run where 2 of 6 artifacts survived still
   gets a report; it is how the user knows what to clean up.
8. **`report.md` carries no `agentic-codebase:begin`/`agentic-codebase:end` markers and needs none.** Markers
   govern files agentic-codebase *shares* with the user; `plan.md`, `report.md` and `build-manifest.json`
   are agentic-codebase's own documents. On a rerun, **regenerate this file wholesale, preserving its
   `agentic-codebase-id`** (`agentic-setup-report`) — one report, updated in place. Never append a second
   report, never create `report.1.md`. Same rule, same wording, as `plan-template.md`'s header and
   `SKILL.md` phase 7. The idempotency invariant holds either way: a rerun updates in place and
   never duplicates.
10. **Suggestions are not artifacts, and they get their own section.** Two things the catalogue
   walk surfaces are never built and always reported, one line each, under `## Suggestions I did
   not build`: an index-doc section that is zone-specific and would be cheaper as a path-scoped
   rule (name the heading and the rule that would take it — `setup-manager` can move it on request;
   agentic-codebase never moves the user's prose), and a same-name collision between a generated artifact
   and one at user scope (`~/.claude/skills/qa` beside `.claude/skills/qa` — both load; say which
   the user may want to rename). Delete the section when there is nothing to say; never fill it
   with generic advice, and never let a suggestion here stand in for an artifact the walk licensed.
9. **Add this file's `artifacts[]` entry to the manifest after writing it, then re-run the static
   pass** (`verification.md` §9 step 6). That entry cannot exist earlier — `file_exists` would fail
   on a file that is written *from* the results of that pass. **Its `path` is a separate thing and
   is already in `committed_paths` / `uncommitted_paths` before you start writing**, reserved at
   `verification.md` §9 step 4a. Every count in this file — `N` and `M` in
   `REMOVAL_MODE_SENTENCE`, the `uninstall` row's totals, the created-files listing — is derived
   from those lists, so a report whose own path is not yet in them is off by one at the moment it
   is rendered. Do not re-add the path at step 6: a path in both lists is an `undo_partition` FAIL.

---

## 2. The skeleton — reproduce this structure literally

~~~markdown
---
agentic-codebase-id: agentic-setup-report
agentic-codebase-version: 1
agentic-codebase-generated: GENERATED_DATE
agentic-codebase-evidence: EVIDENCE_ONE_LINER_WITH_COUNTS
---
<!-- Generated by agentic-codebase. Safe to delete or edit. -->

# Agentic setup report — REPO_NAME

Target agent: TARGET_NAME · Built: GENERATED_DATE · Location: OUTPUT_LOCATION_SENTENCE
Plan of record: [plan.md](./plan.md)

## What got built

BUILT_COUNT artifacts, RUN_MINUTES minutes.

| # | Artifact | Type | Path | Evidence |
|---|---|---|---|---|
| 1 | ARTIFACT_NAME | ARTIFACT_TYPE | ARTIFACT_PATH | EVIDENCE_WITH_COUNT |
| 2 | ARTIFACT_NAME | ARTIFACT_TYPE | ARTIFACT_PATH | EVIDENCE_WITH_COUNT |

Files modified (appended inside `agentic-codebase-id` markers, never overwritten):

| Path | Change |
|---|---|
| MODIFIED_PATH | MODIFIED_SUMMARY |

## What got skipped

| Candidate | Type | Why |
|---|---|---|
| CANDIDATE_NAME | CANDIDATE_TYPE | SKIP_REASON |

SKIPPED_PROSE_NOTE_OR_DELETE

## Needs you

These are the things I deliberately did not do for you: some need credentials I must not touch,
and some are decisions about your machine that are yours to make, not mine.

### 1. NEEDS_YOU_TITLE

Why this is yours: NEEDS_YOU_REASON

1. NEEDS_YOU_STEP
2. NEEDS_YOU_STEP
3. NEEDS_YOU_STEP

### 2. NEEDS_YOU_TITLE

Why this is yours: NEEDS_YOU_REASON

1. NEEDS_YOU_STEP
2. NEEDS_YOU_STEP

NEEDS_YOU_NONE_LINE_OR_DELETE

## Suggestions I did not build

SUGGESTIONS_OR_DELETE

## Verification

`verify_artifacts.py` plus a live smoke test of each artifact. VERIFY_SUMMARY_LINE

| Artifact | Check | Result | Detail |
|---|---|---|---|
| ARTIFACT_NAME | CHECK_NAME | pass / warn / fail | CHECK_DETAIL |

VERIFY_FAILURE_ACTION_NOTE_OR_DELETE

## Three things to try tomorrow

1. **TRY_TITLE** — TRY_INSTRUCTION
   `TRY_LITERAL_COMMAND_OR_PROMPT`
   What should happen: TRY_EXPECTED_RESULT

2. **TRY_TITLE** — TRY_INSTRUCTION
   `TRY_LITERAL_COMMAND_OR_PROMPT`
   What should happen: TRY_EXPECTED_RESULT

3. **TRY_TITLE** — TRY_INSTRUCTION
   `TRY_LITERAL_COMMAND_OR_PROMPT`
   What should happen: TRY_EXPECTED_RESULT

If one of these does something you did not want, edit the file it came from — every generated
file says `Safe to delete or edit` at the top and nothing here is load-bearing for your repo.

## Rerun

Run the skill again whenever. Each generated file carries an `agentic-codebase-id`; a rerun updates the
content between that file's markers in place. It never appends a duplicate and never touches
your edits outside the markers. New evidence since this run — more sessions, new dependencies —
produces new candidates, and they go through the same plan-and-approve gate.

## How to remove everything

REMOVAL_MODE_SENTENCE

```bash
REMOVAL_COMMANDS
```

REMOVAL_EXTRA_BLOCKS_OR_DELETE

REMOVAL_VERIFY_SENTENCE

Files this run created, in full:

```
CREATED_PATH
CREATED_PATH
CREATED_PATH
```

Directories this run created, and removed by the commands above:

```
CREATED_DIR
CREATED_DIR
```

Files this run added to. These existed before the run and are **never deleted** — the commands above
take out only what agentic-codebase put in: the block between the `agentic-codebase:begin` / `agentic-codebase:end` markers
in a text file, the entries agentic-codebase merged into a JSON config, which carries no markers because JSON
has no comments, or the one marked `[table]` block agentic-codebase appended to a TOML config. Rerunning
agentic-codebase updates that same block or entry in place instead of adding a second one.

| Path | Marker id | Reverted by |
|---|---|---|
| MODIFIED_PATH | MODIFIED_ID | MODIFIED_RESTORE_SENTENCE |

REMOVAL_PR_NOTE_OR_DELETE

---

This work was brought to you by Agentic Studio.

Bigger codebase or a team? Agentic Studio makes your team AI-native in 4 weeks: agents, reviews, guardrails, CI. https://theagentic.studio/?utm_source=agentic-codebase&utm_campaign=oss&utm_medium=report
~~~

---

## 3. Token reference

| Token | Fill with |
|---|---|
| `GENERATED_DATE` | today, `yyyy-mm-dd` |
| `EVIDENCE_ONE_LINER_WITH_COUNTS` | the frontmatter `agentic-codebase-evidence` line — one line with numbers describing **this file's own** contribution, e.g. `handoff for the 12 artifacts built and 4 skipped`. It is not the run's evidence summary and not `plan.md`'s line: `verify_artifacts.py`'s `evidence_match` requires it to be the **same string** as the `evidence` field on `report.md`'s own manifest entry (`verification.md` §9 step 6 shows that entry), and a drift between them is a FAIL. Missing or empty is a `metadata` FAIL on its own |
| `REPO_NAME`, `TARGET_NAME` | as in the plan |
| `OUTPUT_LOCATION_SENTENCE` | **branch, `manifest.uncommitted_paths` empty**: `committed on branch agentic-setup/2026-09-04; your master branch was not touched`. **branch, `uncommitted_paths` non-empty**: `N files committed on branch agentic-setup/2026-09-04, M written into your working tree and not committed (IGNORED_BY_PATTERN); your master branch was not touched`. This is the third line of the report and the first thing anyone reads, so it may not say `committed on branch` about files that are not on the branch — same partition, same reason, as `REMOVAL_MODE_SENTENCE`. stage-only: `staged in your working tree, uncommitted`. no git repo: `written in place; this repo is not under git` |
| `BUILT_COUNT` | artifacts that exist on disk **and** did not fail verification |
| `RUN_MINUTES` | wall-clock from invoke to now, rounded |
| `EVIDENCE_WITH_COUNT` | the same evidence string as the plan, shortened to one clause |
| `SKIP_REASON` | one of: `no evidence count`, `you removed it at approval`, `not in daily use`, `unsupported on TARGET_NAME`, `failed verification and was removed`, `low confidence, not opted in` |
| `NEEDS_YOU_TITLE` | e.g. `Trust this project in Codex`, `Authenticate the Linear MCP server` |
| `NEEDS_YOU_REASON` | one sentence, in the report's own voice, saying **why agentic-codebase stopped here** — a credential it must never hold, a security decision that belongs to the user, or a session it cannot restart. Never omit it and never replace it with a restatement of the step: a numbered instruction with no reason reads as a tool that could not finish, and the user's next move is to look for the bug instead of doing the step. §3.2 has the wording for each recurring case |
| `NEEDS_YOU_STEP` | one action, imperative, with the literal path or command |
| `NEEDS_YOU_NONE_LINE_OR_DELETE` | `Nothing. Everything built here works as-is.` when the section is empty. **Check this against the verification table before you write it**: every `not tested — <reason>` row must have a numbered step here, so a table carrying one and a section saying `Nothing` contradict each other (`verification.md` §9 step 5) |
| `VERIFY_SUMMARY_LINE` | `N pass, N warn, N fail.` from the `verify_artifacts.py` `summary` object plus the smoke tests |
| `VERIFY_FAILURE_ACTION_NOTE_OR_DELETE` | for each fail: what you did — fixed it, or removed the artifact and moved it to Skipped |
| `BASE_BRANCH`, `BASE_COMMIT`, `BRANCH_NAME`, `PLAN_DIR` | `manifest.base_branch` (empty means detached HEAD — use `base_commit`), `manifest.base_commit`, `manifest.branch`, `manifest.plan_dir`. Never a remembered value: the manifest is the only place they survive |
| `CREATED_PATHS`, `CREATED_DIRS_DEEPEST_FIRST` | every `action: created` path, **plus `PLAN_DIR/report.md` itself**, and every `manifest.created_dirs` entry deepest-first, space-separated on one line each. Both are the **whole** created set, ignored or not: `rm` and `rmdir` do not consult `.gitignore`, so these two never take the `committed_paths` / `uncommitted_paths` split — only `git restore --staged` does. In the skeleton's "Files this run created, in full" listing the same set is written one path per line as `CREATED_PATH`. **The `rm -f` operand list drops `UNMERGE_PATHS`** — a config agentic-codebase merged into is removed by the un-merge script, not by `rm` — while the listing keeps them. The report's *artifact entry* is appended to the manifest only after the report is written (`verification.md` §9 step 6), so it is not among the `action: created` entries you are reading and you add it by hand; its *path* is already in the partition lists, reserved before this section was rendered (`verification.md` §9 step 4a), which is what makes the counts below final. Omitting it is how an undo strands the one file that explains the run |
| `SUGGESTIONS_OR_DELETE` | rule 10: one bullet per suggestion — an index-doc section named by heading with the path-scoped rule it could become, or a user-scope name collision with the two paths that both load. Delete the whole section when there is none |
| `MODIFIED_PATH`, `MODIFIED_ID`, `PRE_EXISTING_SHA256` | one set per `action: modified` artifact — its `path`, its `id`, and its `pre_existing_sha256` |
| `REMOVAL_MODE_SENTENCE` | **One mechanism per sentence, each with the count of files it removes.** Choose on `manifest.mode` **and** on whether `manifest.uncommitted_paths` is empty — never on `mode` alone. **branch, `uncommitted_paths` empty**: `All N of this run's files are committed on BRANCH_NAME, and nothing was committed to BASE_BRANCH. Deleting the branch removes all N.` **branch, `uncommitted_paths` non-empty**: `N of this run's files are committed on BRANCH_NAME, and nothing was committed to BASE_BRANCH. Deleting the branch removes those N. The other M were never committed — IGNORED_BY_PATTERN — so the branch delete does not touch them and step 2 removes them by name.` `N` is `len(manifest.committed_paths)`, `M` is `len(manifest.uncommitted_paths)`, and `N + M` is every artifact in the manifest — if it is not, `verification.md` §10.2 has already failed the run. Never print the first sentence when the second applies: it is the exact false claim measured on `vercel/turborepo`, where 4 of 9 artifacts were on the branch and 5 were not, and the branch delete removed 4 of them while reporting success. **stage-only**: `Nothing was committed and no branch was created, so there is no branch to delete. The numbered steps below remove N files and D directories and take K appended-to files back to their pre-run bytes.` Say `the numbered steps below`, never a fixed number of them — §3.1 emits its steps across two, three or four blocks, blocks B and C appear only when a `restore: span` file's format calls for them, and any step whose token resolves to an empty list is omitted and the rest renumbered. Add one sentence after it: `Run them top to bottom, in the order printed — step 1 saves a copy of this file, because the last block deletes it.` **no git repo**: `This repo is not under git, so nothing was staged or committed. The steps below delete N files and D directories and remove the marked block from K files that were appended to.` |
| `REMOVAL_COMMANDS` | §3.1's **block A** for `manifest.mode`, and only block A: the save-a-copy step, then the mode's git steps — `git show`/`cp` + `git checkout` + `git branch -D` in branch mode, `cp` + the two `git restore` steps in stage-only, the `cp` alone with no git repo. **Nothing in block A deletes anything**; every `rm`, `rmdir` and script is a later block. Never another mode's block |
| `REMOVAL_EXTRA_BLOCKS_OR_DELETE` | every §3.1 block after A, **in this order and no other**: **B**, the marker-removal `python3` script, when any artifact is a **marked text file** agentic-codebase appended to; **C**, the un-merge `python3` script, when any artifact carries a `merge` record — a **structurally merged JSON config** (`.claude/settings.json`, `.mcp.json`, `.codex/hooks.json`) or a **marked `[table]` block appended to a TOML config** (`.codex/config.toml`); then **D**, the mode's closing block — `rm -f`, the `rmdir` loop, the `shasum` confirmation — which is emitted on **every** run, because `report.md` is always a created path. B and C are not alternatives: a run that appended to a pre-existing `CLAUDE.md` *and* merged a hook into `.claude/settings.json` — or, on Codex, into `.codex/hooks.json` or `.codex/config.toml` — prints both. **The order is the correctness property, not a preference** — D deletes the file B and C are printed in, so D is last, and the token is never `DELETE`d on a run that built anything. Give each block the introductory sentence §3.1 gives it, and number the steps consecutively across A, B, C and D |
| `REMOVAL_VERIFY_SENTENCE` | what proves it worked, and it has to be checkable on **this** run. **Two checks, and the created / modified split decides which one covers a given file.** (a) Created files are gone — `git -C REPO_ROOT status --porcelain -uall --ignored=traditional -- CREATED_PATHS` prints **nothing**. This is the same flag set `verification.md` §10.2 runs, scoped by pathspec to this run's own created paths so a repo full of ignored `node_modules` cannot drown it; a pathspec naming a path that no longer exists is not an error here (exit 0, no output — measured), which is exactly what makes an empty result the proof. (b) Appended-to files are back to their pre-run bytes — `shasum -a 256 MODIFIED_PATH` prints `PRE_EXISTING_SHA256`. (b) covers an un-merged JSON or TOML config unchanged, and **the removal scripts' own printed lines are part of the proof**: `restored byte-for-byte` is the pass, and a `FAIL … nothing was removed` or `SKIP` line means the undo did not complete even though every command in the block exited 0 — the exact way the shipped defect passed its own verification. **Never fold a `MODIFIED_PATH` into check (a).** A pre-existing *ignored* file that either script restored perfectly still exists and is still ignored, so it prints `!! .claude/settings.json` forever (measured) — putting it in (a) makes a correct undo look failed and trains the next reader to ignore the check. **branch, `uncommitted_paths` empty** — (a) prints nothing, (b) matches, and the generated directories are gone. **branch, `uncommitted_paths` non-empty** — run (a) *after the closing block's `rm -f`*, not after the branch delete: at that point it still prints one `!!` line per `IGNORED_CREATED_PATHS` entry, and those lines going away is the only thing that proves the closing block ran. Both checks are run after the **last** block in every mode, never between blocks — and never before block D, which is the one that deletes `report.md` itself. **stage-only/no-git** — the same two checks, unchanged. **All three flags in (a) are load-bearing and none may be dropped for brevity.** Plain `git status` is not the proof and must never be offered as one: a gitignored path is invisible to it, so the tree reads clean while `.claude/` is still on disk — measured on the turborepo shape, and precisely how the shipped defect passed its own verification. `--ignored=matching` is no better: it collapses the whole tree to a single `!! .claude/` directory line that names no artifact and cannot be compared against the manifest. Only `--ignored=traditional` lists one line per path, and only `-uall` reaches inside an untracked directory to do it |
| `CREATED_DIR` | one per `manifest.created_dirs` entry, deepest first — one `[ -d … ] && rmdir … || true` line each in block D, and one line each in the report's listing of created directories. Omit both if the list is empty. Never collapse the lines into a single `rmdir` with several operands: one non-empty directory would then hide the rest of the line's outcome, and `verify_artifacts.py` reads these operands to prove every `created_dirs` entry is named |
| `MODIFIED_ID` | the artifact's `agentic-codebase-id`, the same string in its begin/end markers |
| `MODIFIED_RESTORE_SENTENCE` | **Two questions, in order, per file — never `manifest.mode`.** First, which list is its `path` in? In `manifest.committed_paths`: branch mode → `the branch delete in block A above`, stage-only → `the git restore from BASE_COMMIT in block A above`. Name the block, not a step number: step numbers shift with which of B and C a run emits, and a row pointing at a number the reader has to count out is the same defect as an out-of-order step. In `manifest.uncommitted_paths`, ask the second question — **what is the file's format and how was it merged?**, and read the answer off the artifact's `format` and `merge` fields (`build-and-verify.md` §5.3a), never off its name. `merge` absent, a marked text file (`CLAUDE.md`, a rule, a shell config) → `the marker-block script above`. `merge.strategy: json-entries` (`.claude/settings.json`, `.mcp.json`, `.codex/hooks.json`) → `the un-merge script above`, because JSON holds no markers and the marker script answers `SKIP` on it and exits 0. `merge.strategy: toml-table` (`.codex/config.toml`) → `the un-merge script above` as well: the block *is* marked, but only the un-merge script asks the question TOML makes load-bearing — whether cutting the block re-binds the key below it (§3.1 block C). In **every** mode, for both: such a file is `restore: span`, git has no pre-run copy of it, and neither the branch delete nor `git restore` touches it. Writing `the branch delete above` for every row of a branch-mode run is the same false claim `REMOVAL_MODE_SENTENCE` guards against, arriving one table lower — and writing `the marker-block script above` for a JSON or TOML row is that claim again, arriving one question later |
| `REMOVAL_PR_NOTE_OR_DELETE` | **always delete this token.** agentic-codebase never opens a pull request and never pushes (`SKILL.md` phase 8 step 6, `interview.md` §4.1), so there is never a remote branch for the removal steps to reach. The token is kept only so a rerun over a repo an older agentic-codebase pushed from can still emit the `git push origin --delete BRANCH_NAME` line; on any run of this version it is deleted, with nothing left in its place. |

### 3.1 Removal commands — generated, never pasted

Every value below comes out of `build-manifest.json`: `mode`, `branch`, `base_branch`,
`base_commit`, `created_dirs`, `committed_paths`, `uncommitted_paths`, and each artifact's `path`,
`action`, `type`, `ignored`, `ignored_by`, `restore`, `pre_existing_sha256`, **`format`** and
**`merge`** (`build-and-verify.md` §5.3a). The last two are what make this section target-agnostic:
`format` says what kind of file it is, `merge` says what agentic-codebase put into it and how, and every
mechanism below is chosen from those two rather than from a filename. A target that arrives next
year with a fifth config format adds a `merge.strategy` and one arm to block C's script — it does
not add a filename to a list here. **The three modes have
three different undos and they are not interchangeable.** Emit the blocks for `manifest.mode` and
**never a line from another mode's block** — but "one mode" does not mean "one block": every mode
emits an **ordered sequence** of them, and the order is part of the answer.

**The sequence is executed top to bottom by a human pasting it, in the order this section prints
it.** No reader reorders steps, skips ahead to a block below, or comes back to one above. That makes
an ordering constraint a correctness constraint: **any step that destroys a later step's input is a
defect, not a style problem** — and so is any step whose comment tells the reader to run it after
something printed below it, because by the time they read the comment they have already run it. Four
rules follow, and the block layout below exists to satisfy them.

1. **Nothing a later step reads may be removed before that step runs.** `PLAN_DIR/report.md` is one
   of the created files *and* the file every step is printed in, so the `rm -f` that deletes it is
   the **last** deleting step of the **last** block, and the **first** step of the **first** block
   saves a copy of the report outside the repo.
2. **Ordering is expressed by position, never by an instruction.** "Run this after the two scripts
   below" is the same defect wearing a warning label.
3. **A directory is emptied before it is `rmdir`-ed.** The un-merge script deletes a created
   config, so `rmdir` comes after both scripts, never before them.
4. **Every step tolerates what an earlier step already did** — `rm -f`, never bare `rm`; an `rmdir`
   that skips a directory already gone.

The worked example is measured, and it is why rule 1 is first. The stage-only block used to run
`rm -f CREATED_PATHS` as its step 2 of six, with the marker script and the un-merge script
printed as steps 5 and 6 — *inside `report.md`*, which `CREATED_PATHS` contains. Pasted top to
bottom, step 2 deleted `docs/agentic-setup/report.md` and with it the only copy of steps 5 and 6, so
the user's appended-to `CLAUDE.md` and merged `.claude/settings.json` were left changed and the
instructions for changing them back were gone. Every command exited 0. The one run that came out
clean had been executed 1, 2, 4, 5, 3, 6 by an agent that noticed and said so; a user pasting the
block gets no such reordering. The same block printed `rmdir` as step 3 and told the reader, in step
3's own comment, to run it after step 5: pasted in order it left an empty `.claude/` behind, so the
tree was not byte-identical and the undo under-delivered while every step reported success.

**The block sequence — the same four slots in every mode.**

| | Block | Emitted |
|---|---|---|
| **A** | the mode's **opening** block: save the report first, then the git steps that put tracked files back | always — this is `REMOVAL_COMMANDS` |
| **B** | the **marker script** | when a **marked text file** needs it |
| **C** | the **un-merge script** — one script, one arm per `merge.strategy` | when a `UNMERGE_PATHS` entry needs it |
| **D** | the mode's **closing** block: `rm -f`, then `rmdir`, then the `shasum` confirmation | always — `report.md` is a created path in every run |

B, C and D go into `REMOVAL_EXTRA_BLOCKS_OR_DELETE` in that order, and the report prints them in
that order with nothing between them but their introductory sentences. A run needs two, three or all
four; only B and C are optional. **Number the steps consecutively across the blocks, 1..n in printed
order**, so the numbers a reader follows never skip: stage-only with both scripts is 1–3 in A, 4 in
B, 5 in C, 6–8 in D; stage-only with neither is 1–3 then 4–6. Omit any line whose token resolves to
an empty list and renumber — never leave a gap for a step that was not printed.

**Two questions choose a file's mechanism, and they are asked in this order.**

1. **Can git put this file back?** That is the partition phase 7 step 4 already computed —
   `committed_paths` versus `uncommitted_paths`. Read it; do not re-derive it here.
2. **When git cannot: how was the file changed?** **Read the answer off the artifact's `format` and
   `merge` fields. Never off its path.** A file agentic-codebase *created* and did not merge into is removed
   with `rm`. A text file agentic-codebase *appended a marked block to* (`merge` absent) is un-appended with
   the marker script. Anything carrying a `merge` record goes to the un-merge script, which picks its
   arm from `merge.strategy`: `json-entries` for a config agentic-codebase merged into a data structure
   (`.claude/settings.json`, `.mcp.json`, `.codex/hooks.json` — JSON cannot hold a comment, so such a
   file never carried a marker and never can), `toml-table` for the one marked `[table]` block
   agentic-codebase appended to `.codex/config.toml`. `restore: span` names the git half of the problem; it
   does not name the mechanism, and reading it as though it did is what shipped the defect measured
   below. **A filename does not name it either** — that is the same defect at one remove, and it is
   how a run whose merged config was `.codex/hooks.json` got an undo that matched nothing.

**The routing is `merge` first, then `action`** — a config agentic-codebase merged into is never removed by
`rm`, whether agentic-codebase created it or found it.

| How agentic-codebase changed the file | `manifest` fields | `manifest` list | Removed by |
|---|---|---|---|
| committable — `created`, or `modified` with `restore: head`, and not gitignored | any | `committed_paths` | the branch delete in block A (branch mode); block A's `git restore` plus block D's `rm -f` (stage-only) |
| `created`, no `merge` record | `merge` absent | `uncommitted_paths` | an explicit `rm -f` |
| `created`, **and** merged into afterwards (agentic-codebase wrote the file *and* the entries in it) | `merge.strategy` set | `uncommitted_paths` | the **un-merge script**, which deletes the file when nothing but agentic-codebase's entries remain and keeps it when the user has since added their own; **never** a blind `rm -f` |
| `modified` — a marked text file (`CLAUDE.md`, a rule, a shell config, a git hook) | `merge` absent, markers present | `uncommitted_paths` | the **marker script**, **never** `rm` |
| `modified` — a config merged into a data structure (`.claude/settings.json`, `.mcp.json`, `.codex/hooks.json`) | `format: json`, `merge.strategy: json-entries` | `uncommitted_paths` | the **un-merge script**'s JSON arm, **never** `rm`, **never** the marker script |
| `modified` — a marked `[table]` block appended to a TOML config (`.codex/config.toml`) | `format: toml`, `merge.strategy: toml-table` | `uncommitted_paths` | the **un-merge script**'s TOML arm, **never** `rm`, and **never** the marker script even though the block *is* marked |

Every artifact lands in exactly one row. `verification.md` §10.2 fails the run when one lands in
neither — which is what a single-mechanism undo does to every path below row one.

The last three rows are the quiet ones and they are the same shape: a file the user wrote, git never
tracked, and this run added to. No git command reverts any of them — there is no pre-run blob to
restore, and deleting the file would destroy their content — so the entire undo for it is the script
that takes agentic-codebase's own contribution back out. **Which script, and which arm of it, is decided by
`format` and `merge`, and choosing wrong fails silently rather than loudly.** Three measurements,
each one a shipped or reproduced defect:

- **A JSON config handed to the marker script.** Measured on the axios dogfood run: the marker script
  was handed `.claude/settings.json`, found no `agentic-codebase:begin` in a file that can never contain one,
  printed `SKIP .claude/settings.json: no agentic-codebase block id=…`, **exited 0**, and left the merged hook
  registration in the user's settings for good — while the report called the undo a success.
- **A Codex config in no list at all.** The un-merge script's own rule used to name
  `.claude/settings.json` and `.mcp.json` — two filenames, not a format — so on a Codex run
  `.codex/hooks.json` matched no rule and reached no mechanism. Reproduced on a fixture whose
  pre-existing `.codex/hooks.json` held the user's `audit-shell.sh` and `notify.sh` with agentic-codebase's
  `enforce-bun.sh` merged into the user's own `PreToolUse` group: the marker script printed
  `SKIP  .codex/hooks.json: no agentic-codebase block id=enforce-bun`, exit 0, the file byte-identical, and
  `enforce-bun.sh` still registered.
- **A TOML config handed to the marker script — the one that does damage rather than nothing.** TOML
  *does* have `#` comments, so the marker script finds the block and cuts it, prints a reassuring
  `WARNING: … only the agentic-codebase block was removed`, and exits 0. On a fixture where the user had
  appended `approval_mode = "auto"` below agentic-codebase's block, cutting the block re-bound that key from
  `[mcp_servers.linear.tools.create_issue]` to the table above it,
  `[mcp_servers.playwright.tools.browser_navigate]`, which already had an `approval_mode` — and the
  user's `config.toml` **stopped parsing**: `Cannot overwrite a value (at line 14, column 23)`. An
  undo that reports success and leaves the user's agent unable to read its own config is worse than
  one that removes nothing. Block C's TOML arm refuses this case; block B cannot see it.

Eight tokens below come from the partition, the format and the merge record, and from nowhere else.
§3's table owns the rest.

| Token | Fill with |
|---|---|
| `COMMITTED_CREATED_PATHS` | `manifest.committed_paths` entries whose `action` is `created`, space-separated |
| `COMMITTED_MODIFIED_PATHS` | `manifest.committed_paths` entries whose `action` is `modified` |
| `IGNORED_CREATED_PATHS` | `manifest.uncommitted_paths` entries whose `action` is `created`, **minus `UNMERGE_PATHS`** — those are the un-merge script's, not `rm`'s |
| `UNMERGE_PATHS` | every artifact carrying a **`merge` record** — whatever its `action`, whatever its name. (Superseded spelling: `UNMERGE_JSON_PATHS`, which named a format instead of asking the manifest and is why a Codex run's merged configs reached no mechanism.) The un-merge script removes these, and every `rm -f` operand list in this section excludes them, in every mode: the script deletes such a file when agentic-codebase created it and nothing but agentic-codebase's entries remain, and **keeps it** when the user has added entries of their own since the run — which a blind `rm -f` would destroy. They stay in the report's *listing* of created files; only the `rm -f` line loses them |
| `UNMERGE_FORMAT` | the artifact's `format`, which picks the script's arm: `json` or `toml`. It is a manifest field, never a guess from the extension — a `.json` file agentic-codebase only *appended a marked block to* is block B's, not block C's |
| `UNMERGE_ENTRIES` | per `UNMERGE_PATHS` artifact, `manifest.merge.entries` verbatim — the entries this run merged into that file, as `(kind, value)` pairs, except `hook_command`, which is `(kind, value, event)`. Four kinds, and each one is the identity the emitter actually leaves behind: `("hook_command", <the hook artifact's manifest `command`>, <the event it was registered under>)` for each hook registered in a `settings.json` or a `.codex/hooks.json`; `("permission_entry", "<list>:<exact rule string>")` — `list` being `allow`, `ask` or `deny` — for each string added to `.claude/settings.json`'s `permissions` arrays; `("mcp_server", <server name>)` for each server added to a `.mcp.json`; `("toml_table", <table name, e.g. `mcp_servers.linear`>)` for each `[table]` header inside the marked block appended to `.codex/config.toml`. **`hook_command` and `permission_entry` routinely appear on the same artifact**, because the hook registrations and the permissions block merge into the same `.claude/settings.json` and that file gets exactly one manifest entry (`build-and-verify.md` §5.4). `templates/settings-hooks.json.tmpl` step 6 forbids merging its `_agentic-codebase` key into `settings.json`, and `adapters/codex.md` §4.3 forbids **any** unknown top-level key in `hooks.json` — it makes the whole file load zero hooks — so in both of those the command path is the only mark agentic-codebase leaves. `.mcp.json` does carry `_agentic-codebase`, and the script drops it too when its `agentic-codebase-id` matches |
| `IGNORED_CREATED_DIRS_DEEPEST_FIRST`, `IGNORED_CREATED_DIR` | `manifest.created_dirs` entries with an `uncommitted_paths` entry beneath them, deepest first. Block D emits **one `[ -d … ] && rmdir … || true` line per entry**, in that order, and `IGNORED_CREATED_DIR` is one entry — never a space-separated list on a single `rmdir`. One line each is what makes a directory that is already gone cost nothing and a directory that is not empty say so on its own line, and it is the form `verify_artifacts.py`'s `uninstall` check reads its operands out of |
| `IGNORED_BY_PATTERN` | the artifacts' `ignored_by`, shortened to the pattern the user will recognise — `.claude/` from `.gitignore:6:.claude/`. Name the `.gitignore` file too when more than one contributed. When the path is in `uncommitted_paths` for the `restore: span` reason instead, say `git had no pre-run copy of it` and name no pattern |

**Omit any line whose token resolves to an empty list, and renumber the steps that remain** — a bare
`rm -f` or `rmdir` with no operands is a confusing no-op. In branch mode an empty
`manifest.uncommitted_paths` empties the three `IGNORED_*` tokens — never the two `COMMITTED_*` ones,
which then hold every artifact — so block D collapses to its `shasum` confirmation and blocks B and C
are usually absent, which is the common case and must stay unchanged. **In stage-only and no-git,
block D never collapses to nothing:** `CREATED_PATHS` always holds at least `PLAN_DIR/report.md`, so
the `rm -f` line is always printed and always last. **`UNMERGE_PATHS` is empty on most runs too, and non-empty is not rare:** on **both** targets it is
non-empty for every run that builds a hook, because registering a hook means merging into
`.claude/settings.json` on Claude Code and into `.codex/hooks.json` on Codex. On Codex it also holds
`.codex/config.toml` — but only on a run where the user opted in to writing the MCP block rather than
taking the default draft (`adapters/codex.md` §4.6 rules 2 and 3), which is why most Codex runs have
one entry here and not two.

Check the mode's precondition first. A failed precondition is a build bug, not a wording problem —
fix the build, then write the report (`verification.md` §10 runs these checks for you).

#### Branch mode — block A, the opening block

Precondition: **phase 7 committed.** `git -C REPO_ROOT log --oneline BASE_BRANCH..BRANCH_NAME` must
list at least one commit. If it lists none, the generated files are loose in the working tree, the
branch delete will remove nothing, and this block is a lie — use the stage-only blocks instead and
say in the report that the build did not commit.

Step 1 is not optional and not a convenience. `git checkout BASE_BRANCH` takes every committed file
off the working tree, and `PLAN_DIR/report.md` is normally one of them: without step 1 the reader
loses blocks B, C and D at step 2, which is rule 1 above. Emit the `git show` form when
`PLAN_DIR/report.md` is in `manifest.committed_paths`, and the `cp` form when it is in
`uncommitted_paths` — a user who chose `.claude/agentic-setup/` on a repo whose `.gitignore` holds
`.claude/` puts `plan.md`, `report.md` and the manifest there, and `git show` then answers
`fatal: path '…' exists on disk, but not in 'BRANCH_NAME'` (measured, exit 128).

```bash
# 1. Save these instructions. Step 2 takes report.md off your working tree along
#    with the rest of the branch; every step below is in this copy too.
git show BRANCH_NAME:PLAN_DIR/report.md > ~/agentic-codebase-removal-steps.md

# 2. Delete the branch. Detached HEAD before the run: git checkout BASE_COMMIT
git checkout BASE_BRANCH
git branch -D BRANCH_NAME
```

Step 2 is enough precisely because the run committed, and only for the paths it committed. Every
created file in `committed_paths` goes away with the branch; every appended-to file in it returns to
its pre-run bytes, because the appended block was committed on `BRANCH_NAME` and never on
`BASE_BRANCH`. Nothing on `BASE_BRANCH` was ever touched, so nothing there is at risk. It takes
`plan.md`, `report.md` and `build-manifest.json` with it — **but only when they are in
`committed_paths`**, which is the usual case and not a guaranteed one; when they are not, they stay
on disk until block D deletes them by name.

When `manifest.uncommitted_paths` is empty, blocks B and C are usually empty too and D is just the
`shasum` confirmation. When it is non-empty, introduce D in the report with one plain sentence naming
both mechanisms and both counts, so the user is never told "delete the branch and it is gone" about a
file that is still on disk:

> `Step 2 removes the N files committed on BRANCH_NAME. The other M were never committed —
> IGNORED_BY_PATTERN — so the last block removes those by name.`

#### Branch mode — block D, the closing block

Emit it after blocks B and C, always last. These files were written into the working tree and then
kept out of the commit — because the user's `.gitignore` excludes them, or because committing them
would have made the checkout delete a file git had no pre-run copy of. Either way the branch never
held them and `git branch -D` does not touch them. A repo that ignores `.claude/` puts most of a
Claude Code setup here: measured on `vercel/turborepo`, whose `.gitignore` line 6 is `.claude/`, 4 of
9 artifacts were on the branch and 5 outside it.

```bash
# 5. Delete the files that never reached the branch. Step 2 did not touch these.
rm -f IGNORED_CREATED_PATHS

# 6. Remove the directories this run created that still held one of them, one
#    line each, deepest first. Directories holding only committed files were
#    emptied and removed by the checkout in step 2. These are empty now that
#    every step above has run; one you have since put something else in survives
#    and rmdir says so, and one already gone is skipped in silence.
[ -d IGNORED_CREATED_DIR ] && rmdir IGNORED_CREATED_DIR || true
[ -d IGNORED_CREATED_DIR ] && rmdir IGNORED_CREATED_DIR || true

# 7. Confirm every appended-to file is exact. These files are never deleted.
shasum -a 256 MODIFIED_PATH
# expected: PRE_EXISTING_SHA256

# rm ~/agentic-codebase-removal-steps.md    # when you no longer want the record
```

`IGNORED_CREATED_PATHS` is every `uncommitted_paths` entry whose `action` is `created`, minus
`UNMERGE_PATHS` — those went to block C, which is why they are not in the `rm -f` line.
`IGNORED_CREATED_DIRS_DEEPEST_FIRST` is every `manifest.created_dirs` entry that has an
`uncommitted_paths` entry beneath it, deepest first; a directory whose whole contents were committed
is emptied and removed by step 2's checkout, so a line for it here is a step that does nothing — the
`[ -d … ]` guard makes it silent rather than an error, which is worse, not better: it reads as a step
that removed something. Every line is omitted when its list is empty.

**Never `rm` a file the user wrote:** agentic-codebase only added to it. That case has no other exit —
untracked so `restore: head` is impossible, outside the commit so the branch delete skips it, and
when it is also ignored, invisible to plain `git status` as well. Every remaining `uncommitted_paths`
entry reaches the undo through block B or block C instead, by format: a **marked text file** that
existed before the run gets one `BLOCKS` entry in B; every **`UNMERGE_PATHS`** entry gets one
`UNMERGE` entry in C, including the ones whose `action` is `created`.

**Never `git add -f` to avoid block D.** It would make the two-line undo true again, at the cost of
writing paths the user deliberately excluded into a branch they may push or merge — and agentic-codebase
cannot rewrite history to take them back out. Two honest blocks beat one clean-looking block that
smuggles machine-local config into their history. That trade is settled in SKILL.md phase 7 step 4;
this section only reports it.

#### Stage-only mode

Precondition: **nothing was committed**, so every path below is staged or untracked. The `git
restore` steps take `manifest.committed_paths` **only** — a gitignored path was never staged, git
does not know it, and naming it there breaks the step for every path listed with it (measured:
`git restore --staged -- docs/agentic-setup/plan.md .claude/rules/no-npm.md` prints
`error: pathspec … did not match any file(s) known to git`, exits 1, and unstages neither). The `rm`
and `rmdir` steps in block D take every created path and directory, ignored or not, because they do
not consult `.gitignore`.

Block A — nothing here deletes anything, which is what lets blocks B and C still be on disk when the
reader reaches them:

```bash
# 1. Save these instructions. The last block deletes PLAN_DIR/report.md, the file
#    you are reading them from; every step below is in this copy too.
cp PLAN_DIR/report.md ~/agentic-codebase-removal-steps.md

# 2. Unstage what this run staged. Only these paths were staged; the gitignored
#    ones never were. Nothing is deleted here — the files stay on disk.
git restore --staged -- COMMITTED_CREATED_PATHS COMMITTED_MODIFIED_PATHS

# 3. Put each appended-to file git had tracked back, byte for byte, from the
#    commit you were on. git older than 2.23: git checkout BASE_COMMIT -- PATH
git restore --source=BASE_COMMIT --staged --worktree -- COMMITTED_MODIFIED_PATHS
```

Step 3 is scoped to named paths and is not a destructive git command — it is not `reset --hard`, it
touches nothing else, and it is safe only because `restore: head` records that git held those exact
files, unmodified, when the build started. An ignored or untracked appended-to file can never carry
`restore: head`, so it never appears in step 3; it goes to block B or block C, by format.

Then blocks B and C, whichever formats this run touched — a run that appended to a `CLAUDE.md` *and*
merged a hook into `.claude/settings.json` prints both, and prints them here, before anything is
deleted.

Block D, last:

```bash
# 6. Delete the files this run created — staged and gitignored alike, but NOT
#    UNMERGE_PATHS: a merged-into config is the un-merge script's, not rm's. This is
#    the last step that deletes anything, because PLAN_DIR/report.md is in the
#    list: after it, step 1's copy is the only copy of these instructions.
rm -f CREATED_PATHS

# 7. Remove the directories this run created, one line each, deepest first. They
#    are empty now that every step above has run. One you have since put
#    something else in survives and rmdir says so; one already gone is skipped in
#    silence, and neither stops the line after it.
[ -d CREATED_DIR ] && rmdir CREATED_DIR || true
[ -d CREATED_DIR ] && rmdir CREATED_DIR || true

# 8. Confirm every appended-to file is exact. These files are never deleted.
shasum -a 256 MODIFIED_PATH
# expected: PRE_EXISTING_SHA256

# rm ~/agentic-codebase-removal-steps.md    # when you no longer want the record
```

#### No git repo

The same four slots with the two git steps gone. Block A is the `cp` line alone — it is still the
first thing printed, for the same reason it is in the other two modes. Blocks B and C are unchanged,
and block D is unchanged: `rm -f CREATED_PATHS`, one guarded `rmdir` line per
`CREATED_DIRS_DEEPEST_FIRST` entry, then the `shasum` confirmation. Every appended-to file is
`restore: span` here by definition, so every one of them is block B's or block C's, and the
numbering runs 1, then 2 and 3 for the scripts,
then 4–6.
#### Block B — the marker script, for a `restore: span` file with **no `merge` record**

`restore: span` means git had no clean pre-run copy of that file — it was untracked, **or it is
gitignored**, or it was already dirty when the user waived the clean-tree gate, or the repo is not
under git at all. `span` says only that git is out of the running; the artifact's **`format` and `merge`** fields say
what takes agentic-codebase's contribution back out. This subsection is the mechanism for a **marked text
file agentic-codebase appended to and did not merge into** — `merge` absent on its manifest entry. The next
is the mechanism for **everything carrying a `merge` record**, and handing a file to the wrong one of
the two either removes nothing and exits 0 (JSON) or removes the block and silently corrupts the file
(TOML). Both were measured; both are above. Both are printed **between block A and block D** in
every mode, in the order B then C, and both are printed before anything is deleted. Block A's `git
restore` would fail or overwrite the user's own uncommitted work for either of these files.
One `BLOCKS` entry per marked text file, filled from the manifest:

```bash
python3 - <<'PY'
import hashlib, io, os, re

# (path, agentic-codebase-id, sha256 of the file as it was before this run)
BLOCKS = [
    ("MODIFIED_PATH", "MODIFIED_ID", "PRE_EXISTING_SHA256"),
]

LEAD = r"^[ \t]*(?:<!--|//|/\*|\#|--|;|%|\*)?[ \t]*agentic-codebase[ :_-]{0,3}"

for path, aid, want in BLOCKS:
    if not os.path.exists(path):
        print("SKIP  %s: not present" % path); continue
    src = io.open(path, encoding="utf-8", newline="").read()
    tag = r"\b[^\n]*(?<![\w-])" + re.escape(aid) + r"(?![\w-])[^\n]*"
    m = re.compile(LEAD + "(?:begin|start)" + tag + r"\n.*?" + LEAD + "end" + tag + r"(?:\n|\Z)",
                   re.S | re.M).search(src)
    if not m:
        print("SKIP  %s: no agentic-codebase block id=%s (already removed by hand?)" % (path, aid)); continue
    head, tail = src[:m.start()], src[m.end():]
    tight = head + tail                                           # the block
    loose = head[:-1] + tail if head.endswith("\n\n") else tight  # the block and its blank separator
    sha = lambda t: hashlib.sha256(t.encode("utf-8")).hexdigest()
    if sha(loose) == want:   out, note = loose, "restored byte-for-byte"
    elif sha(tight) == want: out, note = tight, "restored byte-for-byte"
    else:                    out, note = tight, ("WARNING: %s was edited after the run, so only the "
                                                 "agentic-codebase block was removed; the rest of the file "
                                                 "is your version, untouched." % path)
    io.open(path, "w", encoding="utf-8", newline="").write(out)
    print("%s: %s (id=%s)" % (path, note, aid))
PY
```

Block C follows immediately when this run also touched a JSON config, and block D — the `rm -f`,
the `rmdir` loop and the `shasum` confirmation — is printed after both, never before. Three
properties of the marker script are load-bearing:

- **The marker match is line-anchored**, the same anchor `verify_artifacts.py` uses. The generated
  index-doc section quotes both marker strings inside its own "Removing this" bullet; an unanchored
  search finds that quoted `end` first, truncates the removal, and leaves an orphaned end marker
  behind in the user's file.
- **It takes back the blank separator line only when the SHA proves that is what the run added**,
  so it can never eat a blank line the user wrote.
- **It never guesses.** If the file changed after the run, it removes the agentic-codebase block, leaves
  every other byte alone, and says so, rather than restoring stale bytes over the user's edits.

#### Block C — the un-merge script, for any `restore: span` file carrying a `merge` record

**Some files agentic-codebase changes by *merging into a structure* rather than by appending a block a
marker script can cut back out.** Which files those are is not a list of names — it is
`manifest.merge`, written by whichever adapter did the merging (`build-and-verify.md` §5.3a). Emit
**this** block for every `UNMERGE_PATHS` entry, one `UNMERGE` tuple each, filled from the manifest.
Two strategies exist today and the script has one arm for each:

| `format` / `merge.strategy` | Files today | Why the marker script cannot do it |
|---|---|---|
| `json` / `json-entries` | `.claude/settings.json`, `.mcp.json`, `.codex/hooks.json` | JSON has no comment syntax, so there is nothing to mark: handed one, the marker script prints `SKIP <path>: no agentic-codebase block id=…`, exits 0, and leaves the merged hook registered forever — the measured axios defect, reproduced on `.codex/hooks.json` |
| `toml` / `toml-table` | `.codex/config.toml`, on the opt-in write path only (`adapters/codex.md` §4.6 rule 3) | TOML *does* have `#` comments, so the marker script cuts the block happily — and never asks whether a bare key below the block re-binds to the table above it once the block is gone. Measured: it did, and the user's config stopped parsing |

**What each arm keys on is what the emitters actually leave behind, and it differs per file.**
`templates/settings-hooks.json.tmpl` step 6 forbids merging its `_agentic-codebase` key into
`settings.json`, and `adapters/codex.md` §4.3 forbids **every** unknown top-level key in
`hooks.json` — one made the whole file load zero hooks, with no error the user ever sees — so in both
of those the **command path** is the only mark agentic-codebase leaves, and the key is the hook artifact's
manifest `command`. `templates/mcp.json.tmpl` does write `_agentic-codebase`, and its servers are keyed by
**name** under `mcpServers`. The TOML arm keys on the `agentic-codebase:begin` / `agentic-codebase:end` comment pair
plus the recorded `[table]` names: TOML can carry a marker, so agentic-codebase writes one, and the arm still
refuses to cut a block that is no longer only agentic-codebase's.

```bash
python3 - <<'PY'
import hashlib, io, json, os, re

# (path, agentic-codebase-id, format, action, sha256 of the file as it was before this run
#  or "", entries this run merged in)
# format: "json" -- a structural merge into a JSON object: .claude/settings.json,
#                   .mcp.json, .codex/hooks.json
#         "toml" -- one whole marked [table] block appended to a TOML file:
#                   <repo>/.codex/config.toml
# entry kinds: ("hook_command",     "<the hook artifact's manifest `command`>", "<Event>")
#              ("permission_entry", "<allow|ask|deny>:<exact rule string>")
#              ("mcp_server",       "<server name under mcpServers>")
#              ("toml_table",       "<table name, e.g. mcp_servers.linear>")
# A hook_command entry carries a THIRD element, the event it was registered under, because the
# event is half of a handler's identity: the same script the user wired into a second event is
# their wiring, not this run's. Older manifests wrote two elements; then the command must resolve
# to exactly one registration or the arm stops rather than guess. Identity is the whole normalised
# command path either way -- never a basename.
UNMERGE = [
    ("MODIFIED_PATH", "MODIFIED_ID", "UNMERGE_FORMAT", "modified", "PRE_EXISTING_SHA256",
     [("hook_command", "${CLAUDE_PROJECT_DIR}/.claude/hooks/HOOK_FILE_NAME", "HOOK_EVENT")]),
]

def key(value):
    """Command identity: the whole NORMALISED path of the command, and never its basename.
    Takes the last non-comment line (tolerating an older '# agentic-codebase:<id>' + newline + '<path>'
    spelling), unquotes it, rewrites every spelling of "this repo's root" that agentic-codebase actually
    emits -- ${CLAUDE_PROJECT_DIR}, the bare $CLAUDE_PROJECT_DIR, Codex's
    '$(git rev-parse --show-toplevel)', a literal absolute path into the directory these steps run
    from -- to one '<repo>' token, and normalises the remainder. Nothing else is rewritten:
    ${CLAUDE_PLUGIN_ROOT} is a DIFFERENT root, so folding it in here would invent the same false
    identity this function exists to stop. Two commands are the same handler only when this whole
    string is equal. The user's own tools/block-npm.sh and agentic-codebase's .codex/hooks/block-npm.sh
    share a basename and are NOT the same hook; matching on the basename deleted both of them."""
    lines = [l.strip() for l in str(value).splitlines() if l.strip() and not l.strip().startswith("#")]
    text = (lines[-1] if lines else str(value).strip()).strip("\"'").strip()
    here = os.path.abspath(".")
    for root in ("${CLAUDE_PROJECT_DIR}", "$CLAUDE_PROJECT_DIR",
                 '"$(git rev-parse --show-toplevel)"', "$(git rev-parse --show-toplevel)",
                 here if here not in ("", os.sep) else ""):
        if root and (text == root or text.startswith(root + "/")):
            text = "<repo>" + text[len(root):]
            break
    if not text.startswith("<repo>") and not os.path.isabs(text) and not text.startswith("$"):
        text = "<repo>/" + (text[2:] if text.startswith("./") else text)
    return os.path.normpath(text).replace("\\", "/")

def entry_parts(entry):
    """One `merge.entries` item -> (kind, value, event). The event is None on the two-element
    spelling an older manifest wrote, and then it constrains nothing."""
    parts = list(entry)
    kind = parts[0] if parts else ""
    value = parts[1] if len(parts) > 1 else ""
    event = parts[2] if len(parts) > 2 and parts[2] else None
    return kind, value, event

def owns_handler(handler, event, wanted):
    """True only for a handler THIS run registered: the whole normalised command path is equal
    AND, when the manifest recorded the event, it is that event. Never a basename, never a
    substring -- both of those take the user's hooks out with agentic-codebase's."""
    if not isinstance(handler, dict):
        return False
    got = key(handler.get("command", ""))
    return any(got == want and (scope is None or scope == event) for want, scope in wanted)

def inventory(data):
    """Every entry the JSON arm could conceivably remove, as a set of identity strings. The
    preservation check compares this before and after: anything that disappeared and is not one
    of this run's own recorded entries is a bug in the undo, and nothing is written."""
    found = set()
    if not isinstance(data, dict):
        return found
    for name in data:
        found.add("top:%s" % name)
    hooks = data.get("hooks")
    if isinstance(hooks, dict):
        for event, groups in hooks.items():
            if not isinstance(groups, list):
                continue
            for group in groups:
                inner = group.get("hooks") if isinstance(group, dict) else None
                if not isinstance(inner, list):
                    continue
                for handler in inner:
                    if isinstance(handler, dict):
                        found.add("hook:%s:%s" % (event, key(handler.get("command", ""))))
    mcp = data.get("mcpServers")
    if isinstance(mcp, dict):
        for name in mcp:
            found.add("mcp:%s" % name)
    block = data.get("permissions")
    if isinstance(block, dict):
        for listname, arr in block.items():
            if isinstance(arr, list):
                for item in arr:
                    found.add("perm:%s:%s" % (listname, item))
    return found

def outside_repo(path):
    """True for anything not under the directory these steps are run from. agentic-codebase never
    merges into a file outside the repo -- ${CODEX_HOME}/config.toml holds live credentials
    and is never touched -- so such an entry is a bug, not a file to edit."""
    here = os.path.abspath(".")
    return os.path.relpath(os.path.abspath(os.path.expanduser(path)), here).split(os.sep)[0] == ".."

def unmerge_json(path, aid, action, want, entries, raw):
    """Remove this run's entries from a JSON object. Returns (status, removed, out, empty, msg)."""
    try:
        data, before = json.loads(raw), json.loads(raw)   # `before` stays untouched, for the
                                                          # preservation check at the end
    except ValueError as exc:
        return ("stop", 0, "", False,
                "STOP  %s: not valid JSON (%s) -- nothing removed, edit it by hand" % (path, exc))
    if not isinstance(data, dict):
        return ("stop", 0, "", False,
                "STOP  %s: top level is not an object -- nothing removed, edit it by hand" % path)

    parts = [entry_parts(e) for e in entries]
    wanted = [(key(v), ev) for k, v, ev in parts if k == "hook_command"]
    servers = [v for k, v, _ev in parts if k == "mcp_server"]
    perms = [v.split(":", 1) for k, v, _ev in parts if k == "permission_entry" and ":" in v]
    removed = 0
    before_ids = inventory(before)

    # An entry that records no event cannot say WHICH registration of that command is this run's.
    # One is unambiguous; two is a question the manifest did not answer, and guessing takes the
    # user's own wiring of the same script out with agentic-codebase's.  Stop instead.
    for want, scope in wanted:
        if scope is not None:
            continue
        events = sorted(set(ident.split(":", 2)[1] for ident in before_ids
                            if ident.startswith("hook:") and ident.split(":", 2)[2] == want))
        if len(events) > 1:
            return ("stop", 0, "", False,
                    "STOP  %s: `%s` is registered under %s and this run's manifest entry records "
                    "no event, so which registration is agentic-codebase's cannot be decided -- nothing "
                    "removed. Delete the one under the event the report names, by hand."
                    % (path, want, " and ".join(events)))

    hooks = data.get("hooks")
    if wanted and isinstance(hooks, dict):
        for event in list(hooks):
            groups = hooks.get(event)
            if not isinstance(groups, list):
                continue
            kept_groups = []
            for group in groups:
                inner = group.get("hooks") if isinstance(group, dict) else None
                if not isinstance(inner, list):
                    kept_groups.append(group); continue
                keep = [h for h in inner if not owns_handler(h, event, wanted)]
                removed += len(inner) - len(keep)
                if inner and not keep:
                    continue                      # a matcher group this run created: drop it
                group["hooks"] = keep
                kept_groups.append(group)
            if kept_groups:
                hooks[event] = kept_groups
            else:
                del hooks[event]                  # an event array this run created: drop it
        if not hooks:
            data.pop("hooks", None)

    mcp = data.get("mcpServers")
    if servers and isinstance(mcp, dict):
        for name in servers:
            if mcp.pop(name, None) is not None:
                removed += 1
        if not mcp:
            data.pop("mcpServers", None)

    # permissions: remove exactly the strings this run added, by equality, and never touch a
    # sibling.  The user's own rules live in these same arrays; a `deny` of theirs that looks like
    # one of ours is still theirs, so the match is the full string, not a prefix.
    block = data.get("permissions")
    if perms and isinstance(block, dict):
        for listname, rule in perms:
            arr = block.get(listname)
            if not isinstance(arr, list):
                continue
            kept = []
            dropped = False
            for item in arr:
                if not dropped and item == rule:   # one occurrence per recorded entry
                    dropped = True
                    removed += 1
                    continue
                kept.append(item)
            if kept:
                block[listname] = kept
            else:
                del block[listname]                # an array this run created: drop it
        if not block:
            data.pop("permissions", None)

    meta = data.get("_agentic-codebase")
    owned_meta = isinstance(meta, dict) and meta.get("agentic-codebase-id") == aid
    if owned_meta:
        data.pop("_agentic-codebase"); removed += 1

    if action == "created":
        # adapters/codex.md 4.3: agentic-codebase sets `description` only in a hooks.json it CREATED, so
        # on a created file that key is agentic-codebase's own and goes back out with the rest of it. On a
        # file the user already had, the description is theirs and is never touched.
        data.pop("description", None)

    # Preservation check, BEFORE anything is returned to be written. Everything that vanished
    # between `before` and `data` has to be something this run recorded; if one entry is not, the
    # identity is wrong and the user's file is left exactly as it is rather than half-repaired.
    # This is the guard the basename match had no answer to.
    allowed = set(["top:hooks", "top:mcpServers", "top:permissions"])
    for ident in before_ids:
        if ident.startswith("hook:"):
            _kind, ev, command = ident.split(":", 2)
            if any(command == w and (scope is None or scope == ev) for w, scope in wanted):
                allowed.add(ident)
    allowed.update("mcp:%s" % name for name in servers)
    allowed.update("perm:%s:%s" % (listname, rule) for listname, rule in perms)
    if owned_meta:
        allowed.add("top:_agentic-codebase")
    if action == "created":
        allowed.add("top:description")
    lost = sorted(before_ids - inventory(data) - allowed)
    if lost:
        return ("stop", 0, "", False,
                "STOP  %s: removing this run's entries would also drop %d entry(s) it does not "
                "own (%s) -- nothing was written and your file is untouched. This is a bug in the "
                "undo's identity, not in your file; report it and remove the entries by hand."
                % (path, len(lost), ", ".join(lost[:4])))
    return ("ok", removed, json.dumps(data, indent=2, ensure_ascii=False) + "\n", not data, "")

def unmerge_toml(path, aid, action, want, entries, raw):
    """Cut the one marked [table] block this run appended to a TOML file. Never parses or
    re-serialises TOML: it removes a byte range agentic-codebase wrote and can still prove it wrote."""
    tables = [v for k, v in entries if k == "toml_table"]
    if '"""' in raw or "'''" in raw:
        return ("stop", 0, "", False,
                "STOP  %s: holds a multi-line TOML string, so a line scan cannot tell a real "
                "[table] header from text inside one -- nothing removed, cut the block between "
                "the agentic-codebase markers by hand" % path)
    tag = r"\b[^\n]*(?<![\w-])" + re.escape(aid) + r"(?![\w-])[^\n]*"
    beg = re.compile(r"^[ \t]*#[ \t]*agentic-codebase[ :_-]{0,3}(?:begin|start)" + tag + r"\n", re.M).search(raw)
    end = re.compile(r"^[ \t]*#[ \t]*agentic-codebase[ :_-]{0,3}end" + tag + r"(?:\n|\Z)", re.M).search(raw, beg.end()) if beg else None
    if not beg or not end:
        return ("ok", 0, raw, False, "")           # -> the FAIL line below
    span = raw[beg.start():end.end()]

    strays = [t.strip() for t in re.findall(r"^[ \t]*\[\[?[ \t]*([^\]\n]+?)[ \t]*\]\]?[ \t]*$", span, re.M)
              if t.strip() not in tables]
    if strays:
        return ("stop", 0, "", False,
                "STOP  %s: the marked block now holds a table agentic-codebase did not write (%s) -- "
                "nothing removed, cut it by hand" % (path, ", ".join(strays)))

    for line in raw[end.end():].splitlines():     # the TOML-only guard: a [table] header ends
        s = line.strip()                          # the table above it, so a bare key BELOW the
        if not s or s.startswith("#"):            # block would silently re-bind to the table
            continue                              # ABOVE it once the block is gone.
        if not s.startswith("["):
            return ("stop", 0, "", False,
                    "STOP  %s: the first key after agentic-codebase's block (%s) is not under a [table] "
                    "header of its own, so removing the block would silently re-bind it to the "
                    "table above. Nothing removed -- move that line, then rerun this step"
                    % (path, s[:60]))
        break

    head, rest = raw[:beg.start()], raw[end.end():]
    # The merge appended exactly `"\n" + block` to a file rule 3.4 had already made end in a
    # newline, so those bytes are what comes back out -- the blank separator included, and only
    # when the merge is the one that put it there. `want` below proves it; it does not guess it.
    out = head[:-1] + rest if head.endswith("\n\n") else head + rest
    return ("ok", len(tables) or 1, out, not out.strip(), "")

for path, aid, fmt, action, want, entries in UNMERGE:
    if outside_repo(path):
        print("STOP  %s: outside this repo -- agentic-codebase never merges into a file outside it, so "
              "this entry is wrong; nothing removed" % path); continue
    if not os.path.exists(path):
        print("SKIP  %s: not present" % path); continue
    raw = io.open(path, encoding="utf-8", newline="").read()
    status, removed, out, empty, msg = (unmerge_toml if fmt == "toml" else unmerge_json)(
        path, aid, action, want, entries, raw)
    if status != "ok":
        print(msg); continue
    if removed == 0:
        print("FAIL  %s: none of this run's entries are in this file, so nothing was removed. "
              "Check it by hand -- the undo did NOT complete (id=%s)" % (path, aid)); continue
    if empty and action == "created":
        os.remove(path)
        print("%s: deleted (agentic-codebase created it and it now holds nothing else)" % path); continue
    # The pre-run hash is compared BEFORE the file is written, not after: a check that fires
    # once the bytes are already on disk reports a loss instead of preventing one.
    got = hashlib.sha256(out.encode("utf-8")).hexdigest()
    if want and got == want:
        note = "%s: %d entry(s) removed, restored byte-for-byte (id=%s)" % (path, removed, aid)
    elif want:
        note = ("%s: %d entry(s) removed; every entry this run does not own is still there, but "
                "the bytes differ from the pre-run file (%s...). Expected only if you edited it "
                "after the run, or it was not written in the convention agentic-codebase found. Diff it "
                "before assuming a problem." % (path, removed, got[:12]))
    else:
        note = "%s: %d entry(s) removed (id=%s)" % (path, removed, aid)
    io.open(path, "w", encoding="utf-8", newline="").write(out)
    print(note)
PY
```

Nine properties are load-bearing, and each one is a failure that was measured while writing this:

- **It dispatches on the manifest, not on the path.** `format` picks the arm; `merge.entries` fills
  the tuple. Adding a target that merges into a fifth kind of file is one new arm and one new
  `merge.strategy` — not a filename appended to a rule somewhere in this file. Four shipped defects
  in this project have been the same shape: agentic-codebase wrote a file one way and un-wrote it another,
  and the fourth was this script keyed on `.claude/settings.json` and `.mcp.json` while a Codex run
  merged into `.codex/hooks.json`.
- **It never touches a file outside the repo.** The first guard refuses any entry that does not
  resolve under the directory the steps are run from. `${CODEX_HOME}/config.toml` is hand-maintained,
  holds live credentials, and is never written by agentic-codebase in the first place (`adapters/codex.md`
  §4.6 rule 1) — so an entry naming it is a bug in the manifest, and the undo says so rather than
  editing it.
- **The JSON arm removes the command object, then prunes only what it emptied.** Both adapters merge
  agentic-codebase's hook into an existing matcher group when one matches, so the group is usually **shared
  with the user's own hooks**. Deleting the group, the event array or the `hooks` key wholesale takes
  the user's hooks with it. A group that was already empty before the run is left exactly as it was.
- **A handler's identity is its whole normalised command path plus the event it sits under — never
  its basename.** `key()` rewrites `${CLAUDE_PROJECT_DIR}`, the bare `$CLAUDE_PROJECT_DIR`, Codex's
  quoted `"$(git rev-parse --show-toplevel)/…"` and a literal absolute path into the repo to one
  `<repo>` token, and the match is equality on the result. Measured: handed agentic-codebase's
  `/repo/.codex/hooks/block-npm.sh` while the user's own `/repo/tools/block-npm.sh` sat in the same
  matcher group, a basename fallback removed **both** and returned `{}` — and the loop then printed
  a byte comparison over the damage, because it had already written the file. Two things follow and
  both are in the script: the event travels in the `hook_command` entry, so the same script the user
  wired into a *second* event stays wired — and an entry that records no event, from a manifest an
  older agentic-codebase wrote, stops rather than guess as soon as that command resolves to more than one
  registration; and before it returns anything to be written, the arm
  compares an inventory of the file's hooks, servers, permission strings and top-level keys against
  the same inventory afterwards and **stops without writing** if one entry disappeared that this run
  did not record. Zero risk of a silent loss is what that check buys; a `STOP` the user can read is
  what it costs.
- **The TOML arm never parses or re-serialises TOML.** It removes a byte range agentic-codebase appended and
  can still prove it appended — nothing else. That is what makes it implementable at all: agentic-codebase is
  stdlib-only and targets Python 3.9, where `tomllib` does not exist (it is 3.11+, and read-only even
  there), and there is no TOML *writer* in the standard library at any version. A hand-rolled writer
  that preserves comments, ordering and quoting is exactly the plausible-looking change that corrupts
  a config file. Cutting a marked span is not that, and it is safe **only** because the merge
  contract (`adapters/codex.md` §4.6 rule 3) makes the span self-contained: one complete `[table]`
  block, appended at end-of-file, refused if the table name already exists, refused if the file holds
  a multi-line string, and written only after the file was normalised to end in a newline. The
  un-merge re-checks the same guards rather than trusting that they still hold.
- **The TOML arm refuses to re-bind a key it did not write.** A `[table]` header ends the table above
  it, so a bare `key = value` line *below* agentic-codebase's block belongs to agentic-codebase's last table — and
  cutting the block silently moves it to whatever table precedes the block. The arm stops instead,
  names the line, and removes nothing.
- **It never silently succeeds.** Zero removals prints `FAIL … the undo did NOT complete` instead of
  the marker script's reassuring `SKIP`, because on a merged config a no-op *is* the bug. Read the
  script's output — that line is part of `REMOVAL_VERIFY_SENTENCE`'s proof.
- **`action: created` is deleted only when nothing else is left.** A settings file agentic-codebase created
  and the user has since added `"model"` or `"permissions"` to keeps those keys and stays on disk,
  with the removal counted; so does a `config.toml` agentic-codebase created and the user has since added a
  server of their own to. This is why `UNMERGE_PATHS` is excluded from every `rm -f` line: a blind
  `rm` of a created config destroys whatever the user added to it afterwards. On a **created**
  `hooks.json` the `description` key is agentic-codebase's own — `adapters/codex.md` §4.3 lets agentic-codebase set it
  only in a file it created — so it goes back out with the rest; on a file the user already had, the
  description is theirs and is never touched.
- **A file it cannot read safely stops rather than repairs.** JSON that does not parse, a top level
  that is not an object, a TOML file that has since grown a multi-line string, a marked block that has
  since grown a table agentic-codebase did not write: nothing is written, the user is told exactly what to do
  by hand, and no other entry in the list is affected. Same rule as the merge (`adapters/claude-code.md`
  §4.3 step 2, `adapters/codex.md` §4.3 step 2 and §4.6 rule 3).
- **It reports the byte comparison rather than assuming it.** The merge rewrote a JSON file with
  2-space indentation and a trailing newline, and appended to a TOML file only after normalising its
  trailing newline, so the un-merge reproduces the pre-run bytes exactly when the user's file already
  used that convention — and says plainly when it does not, instead of claiming a restore it cannot
  prove. Only `PRE_EXISTING_SHA256` decides which line is printed — and it is compared **before**
  the file is written, not after, so the hash is a decision the loop takes about bytes it is holding
  rather than a verdict it pronounces over bytes it has already committed to disk.

**Re-measured by extracting this exact block from this file and running it** against fixtures built
by running each adapter's merge procedure first, so the "before" and "after" are the real ones.

*Claude Code, six shapes, all unchanged by the generalisation:* a pre-existing `.claude/settings.json`
holding the user's `permissions`, `model`, `env`, a `PreToolUse`/`Bash` group and a `Stop` group, with
agentic-codebase's `enforce-bun` merged into that same `Bash` group → `1 entry(s) removed, restored
byte-for-byte`, byte-identical to pristine, the user's `audit-bash.sh`, `user-format-guard.sh` and
`notify.sh` all still there; agentic-codebase merged as a **new** matcher group under a new event → group and
event array both pruned, byte-identical; agentic-codebase **created** the file → `deleted (agentic-codebase created it
and it now holds nothing else)`; created, then the user added `"model": "opus"` → `1 entry(s)
removed`, file kept holding `{"model": "opus"}`; `.mcp.json` with the user's `playwright` server plus
agentic-codebase's `linear` and `_agentic-codebase` → `2 entry(s) removed, restored byte-for-byte`, `playwright`
intact; a `settings.json` that does not parse → `STOP … nothing removed`, not a byte written.

*Codex, the two files this block exists to cover:* a pre-existing `.codex/hooks.json` holding the
user's own `audit-shell.sh` in a `PreToolUse` group and `notify.sh` in a `SessionEnd` group, with
agentic-codebase's `enforce-bun.sh` merged into the user's own group, **and** a pre-existing
`.codex/config.toml` holding their `model`, `[mcp_servers.playwright]` and
`[mcp_servers.playwright.tools.browser_navigate]`, with agentic-codebase's marked `[mcp_servers.linear]` block
appended → `1 entry(s) removed, restored byte-for-byte (id=enforce-bun)` and `2 entry(s) removed,
restored byte-for-byte (id=mcp-linear)`, and `diff -ru` against the pristine tree **empty**. The same
two files with `action: created` → both `deleted (agentic-codebase created it and it now holds nothing else)`,
leaving only the empty `.codex/` that block D's `rmdir` takes. Created and then added to by the user →
both kept, holding the user's `SessionEnd` hook and their `[mcp_servers.sentry]` and nothing of
agentic-codebase's. Run twice → `FAIL … the undo did NOT complete`. A bare `approval_mode = "auto"` appended
below the block → `STOP … would silently re-bind it to the table above`, nothing removed. A
multi-line string added to the file → `STOP … a line scan cannot tell a real [table] header from text
inside one`. An entry naming `~/.codex/config.toml` → `STOP … outside this repo`.

**Digests and diffs are fixture-specific — re-run the block, do not quote these numbers.**

#### What this section is claiming

`CLAUDE.md` goal 2 promises `reversible` and `CLAUDE.md` promises an uninstall path in every report — the
same two clauses `verification.md` §10 opens with. This section is the only place the user ever sees
either promise cashed.
`verification.md` §10 runs the exact blocks you are about to quote before the report quotes them —
the same rendered text, in the same order, which is what §10.4 was changed to guarantee. Eight failure
shapes it exists to catch, all of which read as correct on the page:

- **A branch that was created but never committed to.** `git branch -D` prints `Deleted branch
  agentic-setup/… (was <sha>)` where `<sha>` is the base branch's own tip, and every generated file
  is still sitting in the working tree, untouched.
- **A section appended to a pre-existing `CLAUDE.md`.** No file deletion removes it, and no branch
  delete removes it either unless the append was committed on that branch.
- **A branch that holds only the artifacts `.gitignore` allowed onto it.** Same `Deleted branch`
  line, same clean `git status` — because `git status` does not list ignored files — and every
  artifact under the ignored prefix still on disk. Measured: 4 of 9 removed, 5 left.
- **A `git restore --staged` list containing a path git never staged.** It exits 1 and unstages
  nothing at all, so the whole undo stalls on its first line while looking like a typo.
- **The marker script handed a JSON config.** `SKIP .claude/settings.json: no agentic-codebase block id=…`,
  exit 0, nothing removed — the hook agentic-codebase registered in the user's settings stays registered
  forever, and every other step in the block succeeds around it. Measured on the axios run.
- **The marker script handed a TOML config.** It *works*, which is why it is the worst of them:
  TOML has `#` comments, so the block is found and cut, `WARNING: … only the agentic-codebase block was
  removed` is printed, exit 0. On a fixture the cut re-bound a key the user had added below the
  block to the table above it, and the resulting `config.toml` no longer parsed —
  `Cannot overwrite a value (at line 14, column 23)`. Removing the right bytes is not the same as
  leaving a valid file behind, and only the arm that knows the format can tell.
- **A merged config no mechanism names at all.** The un-merge rule keyed on two filenames, so a run
  whose merged configs were `.codex/hooks.json` and `.codex/config.toml` emitted a block C that
  matched neither. Not a `SKIP`, not a `FAIL` — no line at all, because nothing was handed to
  anything. Reproduced on a fixture: the hook stayed registered in the user's `hooks.json` and the
  undo reported success. This is the class the `format` + `merge` dispatch closes.
- **A step that deletes the file the next step is printed in.** `rm -f CREATED_PATHS` includes
  `PLAN_DIR/report.md`, and the two scripts live inside `report.md`. Run in printed order it removed
  the report at step 2 of 6 and the user had no steps 5 and 6 to run; every command exited 0 and the
  tree kept a merged `.claude/settings.json` and an appended `CLAUDE.md`. Measured on a real run,
  which came out clean only because the agent executing it reordered the steps and said so.

The first two are about *whether a mechanism ran*. The next two are about *whether every file is
covered by one*. The fifth and sixth are about *whether the mechanism a file was assigned can act on
that file at all* — coverage is necessary and not sufficient, because a step that names the path and
then no-ops reads as covered in every enumeration, and a step that acts on the wrong assumption about
the format reads as covered too. The seventh is about *whether the routing can see the file in the
first place*, which is the same question asked of the rule rather than of the step. The eighth is
about *whether the reader can still reach the mechanism when their turn comes*: an undo that is
correct as a set of steps and wrong as a sequence. Ask all five, in that order, and these shapes
cannot recur under a new name; the last two are why §10.4's rehearsal runs the rendered text block by
block, re-reading each block from the file the reader would be reading it from, and compares bytes
rather than lists — the only check that cannot pass for the wrong reason.

Never emit `git reset --hard`, `git clean -fd`, `git checkout -f`, `git push --force`, or any
history rewrite in this section, even as an alternative. The user's other work is not yours to
discard.

### 3.2 "Needs you" content

**Three sources, and the last two are the ones that get forgotten.**

1. **Credentials.** Every MCP draft: the file, the variable names, the auth steps.
2. **Everything verification recorded `not tested`** because the run could not reach it — project
   trust, hook trust, a session that has to be restarted, a subagent with no runtime check. These
   are not failures and not omissions; they are the parts of "installed" that only the user can turn
   into "running" (`verification.md` §5.3, `adapters/codex.md` §5.0). One numbered step each. A
   `not tested` row in the verification table with no step here is a bug, and so is a step here
   with no row.
3. **An engineering system the user asked for and does not have yet** — `interview.md` Q14 answered
   `c`. agentic-codebase never installs a marketplace plugin, so this is a step with the exact install
   command for their agent, plus one line saying the setup above works without it. If the user named
   something you do not recognise, say so plainly, put **their words** in the step as the thing to
   install, and invent no command. When Q14 answered `a` or `b`, there is no item here at all.

**Order: what blocks the whole setup comes first.** Not "credentials first" — on Codex the trust
steps gate every other artifact, so an MCP step printed above them tells the user to authenticate a
server in a repo where nothing agentic-codebase built is loaded yet.

**Every item states its reason.** A numbered instruction with no reason reads as a tool that gave
up; the reason is what makes it read as a boundary agentic-codebase chose not to cross. The four recurring
reasons, and only one of them is "it needs credentials":

| Case | Reason to state |
|---|---|
| project trust (Codex) | deciding that a repo's committed files may configure the agent, run hooks and set an exec policy is a security decision about your machine — mine to explain, not to make |
| hook trust (Codex `/hooks`) | same, one level down: Codex asks *you* to approve each hook's exact contents, and it re-asks whenever one changes |
| a new session (both targets) | agentic-codebase runs inside your current session and cannot restart it; the harness fixed its hook and config set when that session started |
| an engineering system you asked for (Q14 `c`) | installing a marketplace plugin reaches the network and changes what loads in every session in this repo, so it is your call and your command to run, not something a setup run does on your behalf |
| MCP auth (both targets) | the key must never be written into a repo file, pasted into this conversation, or held by agentic-codebase |

Good shape for an MCP draft on **Claude Code**:

```
### 1. Authenticate the Linear MCP server

Why this is yours: the API key must never land in a repo file or in this conversation, so the
draft references it by variable name and you supply the value.

1. Open `.mcp.json` — the `linear` entry is drafted but has no credentials.
2. Create a personal API key at Linear, under Settings, API, Personal API keys.
3. Export it: `export LINEAR_API_KEY=...` (add it to your shell profile, not to `.mcp.json`).
4. Restart Claude Code and run `/mcp` to confirm `linear` connects.
```

And the Claude Code restart item, which is easy to forget precisely because nothing failed:

```
### 2. Start a new session so the hook and the new files load

Why this is yours: Claude Code fixes its hook set when a session starts, so the hook I just wrote
is not in this one. I cannot restart your session, and re-reading the file would not change it.

1. Start a new Claude Code session in this repo.
2. Run `/hooks` and confirm `block-npm` is listed under `PreToolUse`.
3. Run `/memory` and confirm the `Agentic setup` section of `CLAUDE.md` is loaded.
4. Ask for one of the new skills by name and confirm it is offered.
```

On **Codex** the trust steps come first, because until they are done the rest of the setup is inert:

```
### 1. Trust this project in Codex

Why this is yours: Codex only loads a repo's `.codex/` layer for directories you have marked
trusted, and marking one is a security decision about your machine. Everything I built here is
installed and correct, and none of it runs until this is set — silently, with no error.

1. Open Codex in this repo: `codex` from the repo root.
2. Accept the trust prompt for this directory.
3. Confirm it took: `~/.codex/config.toml` now has a `[projects."<abs repo path>"]` entry with
   `trust_level = "trusted"`. I never edit that file.
4. Without it, `.codex/hooks.json`, `.codex/rules/agentic-codebase.rules` and `.codex/config.toml` do
   nothing. `AGENTS.md` is the exception — it loads either way, unless the entry says
   `trust_level = "untrusted"`.

### 2. Trust the new hooks

Why this is yours: Codex shows you each hook's exact contents and asks you to approve it, and
asks again whenever one changes. It is installed, not armed.

1. Run `/hooks` in a Codex session in this repo.
2. Approve `block-npm`. Until you do, it is listed and does not run.
3. Do not use `--dangerously-bypass-hook-trust`. It disarms the check for everything, not just
   for the files I wrote.

### 3. Apply the Linear MCP block

Why this is yours: the API key must never land in a config file or in this conversation, so the
block references it by variable name and you supply the value. I never connect to a server.

1. Open `docs/agentic-setup/codex-mcp.toml` — it is a draft; nothing was written to your config.
2. Append it to `<repo>/.codex/config.toml` (create the file if it is not there). If you prefer it
   available in every repo, append it to `~/.codex/config.toml` instead — I do not write to either.
3. Create a personal API key at Linear, under Settings, API, Personal API keys.
4. Export it: `export LINEAR_API_KEY=...` (add it to your shell profile; the value never goes in a
   file).
5. Restart Codex, then run `codex doctor --json` — it names any server whose environment variables
   are missing.

### 4. Confirm what I could not

Why this is yours: these need a session that started after this run, which I cannot arrange from
inside it.

1. Start a new Codex session in this repo and ask "what package manager does this repo use?" —
   the answer is in the `AGENTS.md` section I added.
2. Ask the model to use the `pr-reviewer` agent by name and confirm it spawns. There is no
   programmatic check for a Codex subagent yet.
```

Two paths, one rule: **the MCP destination is the target's own config format** — `.mcp.json` on
Claude Code, a TOML block appended to `config.toml` on Codex — and the step names the literal file.
Never write the key into a repo file, never ask the user to paste a key into this conversation,
never draft a config with a real value in it, and never suggest `--dangerously-bypass-hook-trust`.

### 3.3 "Three things to try tomorrow"

Derive each item from an artifact that was actually built and passed verification. Each item is
a literal thing to type. Prefer one per artifact type so the user sees the range of what changed.

Good:

```
1. **Scaffold your next route with the skill** — you asked for this 9 times by hand.
   `add a POST /invoices endpoint using the new-endpoint skill`
   What should happen: handler, zod schema, route test, and an OpenAPI entry, all four at once.

2. **Watch the pre-commit hook catch a typecheck error** — it warns, it does not block.
   `git commit -m "wip"` with a deliberate type error staged
   What should happen: the hook prints the failing file and the commit still goes through.

3. **Ask the review subagent for a second pass** — it reads the diff in its own context.
   `use the pr-reviewer subagent on my current branch`
   What should happen: a findings list scoped to your diff, using the rules in .claude/rules/.
```

Bad, and to be rejected: `Try using your new skills.` `Explore the CLAUDE.md.` `Consider adding
more rules.` If fewer than three artifacts survived, write only as many items as you can write
truthfully, and say `Only N artifacts were built, so here are N.`

---

## 4. The footer — fixed text

Reproduce exactly, as the last two paragraphs of the file, after a `---` rule:

```
This work was brought to you by Agentic Studio.

Bigger codebase or a team? Agentic Studio makes your team AI-native in 4 weeks: agents, reviews, guardrails, CI. https://theagentic.studio/?utm_source=agentic-codebase&utm_campaign=oss&utm_medium=report
```

- The upsell URL is owned by the repo and is `https://theagentic.studio/?utm_source=agentic-codebase&utm_campaign=oss&utm_medium=report`. Reproduce it exactly, query string included. If a fork has
  removed it and no URL is configured, drop the whole upsell sentence and keep only the first
  line. Never invent a URL, and never leave a placeholder token in a shipped report.
- The same two lines go in the footer of the generated index-doc section, with `utm_medium=index-doc`
  in place of `utm_medium=report` (the index-doc template already carries it). That plus
  the final run summary printed in the conversation makes exactly three placements.
- Do not add attribution to the top of the report, to section headers, to the "try tomorrow"
  items, or anywhere inside a generated skill, subagent, rule, or hook.
