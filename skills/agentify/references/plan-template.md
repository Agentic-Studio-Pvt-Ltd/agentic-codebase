# plan-template.md — phase 6 skeleton for `PLAN_DIR/plan.md`

Read this file in **phase 6 (Plan) only**. `PLAN_DIR` is the interview's `plan_dir` answer,
default `docs/agentic-setup/`.

Phase 6 is a hard gate. Write this file, show it, and **stop**. Do not create, modify, or stage a
single artifact file until the user has approved in writing. Writing `plan.md` itself is the one
permitted write. `plan.md` has **no `agentify:begin`/`agentify:end` markers and needs none** — it
is agentify's own document, not a file shared with the user — so if a `plan.md` already exists from
an earlier run, **regenerate the file wholesale, preserving its `agentify-id`** (`agentic-setup-plan`)
and bumping nothing else. `report.md` and `build-manifest.json` follow the same rule in phase 8.
The idempotency invariant is unchanged either way: **a rerun updates in place and never duplicates.**
Never append a second plan, and never create `plan.1.md` or a dated variant.

---

## 1. Rules for filling the skeleton

1. **Replace every ALL_CAPS token.** A token left in the output is a bug. If you cannot fill one
   truthfully, delete the line or the whole section rather than guessing.
2. **Every artifact has an evidence line with a count.** No count, no artifact — cut it to
   Skipped with the reason `no evidence count`. This is the product's core claim; it is not
   negotiable and it is not satisfied by "common practice" or "best practice".
3. **Every artifact has a "Will not" line.** It is the honest boundary of the thing. Vague scope
   is what makes generated setups get deleted.
4. **Every modified file shows a diff preview.** Created files do not need one. A modification
   with no preview is not approvable.
5. **Counts must agree.** The summary table, the per-artifact blocks, and the created/modified
   table are three views of one list. Reconcile them before you print.
6. **No caps, and the word never appears.** There is no cap row, no clamp line and no sentence
   saying a limit stopped anything (`coverage.md` §1). If a type produced nothing, the note on its
   row names the field that was empty.
7. **No file is created by this phase.** Not a stub, not a placeholder, not a directory.
8. **Every phase-4 candidate ends in exactly one place** — built, or under one of the **three**
   skipped headings (`insufficient evidence` / `already covered` / `low confidence — opt in to
   build`). The three are different facts about a candidate and `coverage.md` §8 forbids conflating
   them: more usage brings back an insufficient-evidence one, nothing brings back one that is
   already covered, and a low-confidence one comes back on the user's word alone. There is no
   fourth heading; `### Skipped (over cap)` is retired and a plan that emits it is wrong. A
   candidate in none of the four states is a bug in the run, not a tidy plan.
9. **The three derived values each get a line, always.** `mode`, `services` and `team_size` were
   not asked (`interview.md` §4.2, §4.8), so the plan is the only place the user sees them. Each
   line states the derivation *and* how to overturn it. A derived value with no line is a decision
   made behind their back, and it is the thing that makes not asking safe.
10. **One section is conditional.** `## Existing setup notes` appears only when
   `discovery.existing_agentic_config` listed something; delete the whole section otherwise. A
   skipped heading with no rows is deleted too — but never merged into a neighbour.
11. **Every artifact passes `blueprint.md` §1.1 before it reaches this file.** A plan entry for a
   file that would read identically in an unrelated repo is a candidate to rewrite, not to list.
   The plan is where a generic artifact is still cheap to catch.

### 1.1 The no-history case — consent given, nothing found

`SESSION_COUNT` is `0`, but consent was **not** refused: the user said yes and
`signals.transcripts.sessions.count` came back `0`. Fresh repo, fresh clone, new machine, or a
first session. This is PRD §5's secondary user and the commonest fresh-repo run — it is a normal,
correct outcome, not a failure, and it needs its own words. `full history` over a count of `0` is
a lie; `you declined` is a different lie.

1. Set `SESSION_WINDOW_DESCRIPTION` to `history (none found — no prior sessions for this repo)`.
2. Set `CONSENT_LINE` to the string `privacy.md` **§8.1** wrote for exactly this case — the one
   beginning `Transcript evidence: you consented, and there are no recorded sessions for this repo
   yet.` §8.1 offers **four** strings, and it is the third of the four as they are listed there;
   match on that opening clause rather than counting down the list, because the count is the part
   that goes stale. The rule is to pick on the consent value **and** `sessions.count`, never on
   consent alone — that is what the first two runs to hit this case got wrong. Do not reuse the
   `full history` line over a count of `0`, and do not reuse the `declined` line: the first claims
   a history was read when none was, and the second misrecords a consent answer the user gave.
3. Set `DEGRADATION_LINE_OR_DELETE` to this paragraph, which says plainly what the plan rests on:

> You consented to transcript access and I found no prior sessions for this repo, so **this plan
> is derived from your code and git history alone.** There is no usage evidence in it at all.
> That makes it smaller and more conservative than a plan built on history would be: repetition,
> corrections, friction and tool mentions are all transcript signals, and none were available.
> **Results improve after a week of normal use** — rerun me then and the candidates below in
> "Skipped (insufficient evidence)" will finally have a count to be judged on.

4. Change nothing else. The evidence rule still binds: a candidate whose `mapping-rules.md`
   threshold needs a transcript count cannot meet it on repo evidence, so it goes under **Skipped
   (insufficient evidence)** with `COUNT_FOUND` of `0` — never promoted, never softened into a
   "best practice" artifact. Two rules and nothing else is a correct plan for this run.

### Where the capability table comes from

Read `adapters/capabilities.md` — a single short table, and the only file phase 6 needs for this.
**Do not open `adapters/claude-code.md` or `adapters/codex.md` in phase 6.** They are ~700 and ~580
lines of emit detail, they cost roughly 9.6k tokens for a table you already have, and phase 7 opens
exactly one of them exactly once.

### Estimating build time

Sum these, round up to the nearest minute, and state a range of `estimate` to `estimate + 40%`.

| Artifact type | Minutes each |
|---|---|
| Index doc section (`CLAUDE.md` / `AGENTS.md`) | 2 |
| Rule | 1 |
| Hook (script + settings wiring) | 3 |
| Skill | 4 |
| Subagent | 3 |
| MCP draft config | 1 |
| Permissions block | 2 |
| Verification pass (all types) | 3 |

---

## 2. The skeleton — reproduce this structure literally

~~~markdown
---
agentify-id: agentic-setup-plan
agentify-version: 1
agentify-generated: GENERATED_DATE
agentify-evidence: EVIDENCE_ONE_LINER_WITH_COUNTS
---
<!-- Generated by agentify. Safe to delete or edit. -->

# Agentic setup plan — REPO_NAME

Target agent: TARGET_NAME · Mode: BUILD_MODE · Generated: GENERATED_DATE

## Summary

I read REPO_LOC lines across REPO_FILE_COUNT files, SESSION_COUNT sessions of your
SESSION_WINDOW_DESCRIPTION, and COMMIT_COUNT commits from the last GIT_WINDOW_DAYS days
(GIT_WINDOW_REASON).
From that I found FINDING_COUNT findings with evidence, and I propose ARTIFACT_TOTAL artifacts.

| Type | Proposed | Notes |
|---|---|---|
| Rules | RULE_COUNT | RULE_NOTE |
| Hooks | HOOK_COUNT | HOOK_NOTE |
| Permissions | PERMISSIONS_COUNT | PERMISSIONS_NOTE |
| Skills | SKILL_COUNT | SKILL_NOTE |
| Subagents | SUBAGENT_COUNT | SUBAGENT_NOTE |
| MCP drafts | MCP_COUNT | MCP_NOTE |
| Index doc | INDEX_DOC_COUNT | INDEX_DOC_NOTE |
| **Total** | **ARTIFACT_TOTAL** | |

Nothing here is being held back. Approve all of it, or name the numbers to drop; anything you drop
stays listed below so you can add it later.

Estimated build time: BUILD_TIME_LOW to BUILD_TIME_HIGH minutes.
Everything lands OUTPUT_LOCATION_SENTENCE.

**Evidence basis.** CONSENT_LINE
GIT_EVIDENCE_LINE
DEGRADATION_LINE_OR_DELETE

**Your answers shaping this plan.** INTERVIEW_ANSWER_SUMMARY

**What I worked out for myself.** Three things I did not ask about, each with how to change it:

- DERIVED_MODE_LINE
- DERIVED_SERVICES_LINE
- DERIVED_TEAM_LINE

## What gets built

### 1. ARTIFACT_NAME

- **Type:** ARTIFACT_TYPE
- **File:** ARTIFACT_PATH
- **Purpose:** ONE_SENTENCE_PURPOSE
- **Evidence:** EVIDENCE_WITH_COUNT
- **Creates:** CREATED_PATHS
- **Modifies:** MODIFIED_PATHS_OR_NONE
- **Will not:** EXPLICIT_NON_GOALS

MODIFIED_DIFF_PREVIEW_BLOCK_OR_DELETE

### 2. ARTIFACT_NAME

- **Type:** ARTIFACT_TYPE
- **File:** ARTIFACT_PATH
- **Purpose:** ONE_SENTENCE_PURPOSE
- **Evidence:** EVIDENCE_WITH_COUNT
- **Creates:** CREATED_PATHS
- **Modifies:** MODIFIED_PATHS_OR_NONE
- **Will not:** EXPLICIT_NON_GOALS

MODIFIED_DIFF_PREVIEW_BLOCK_OR_DELETE

REPEAT_ONE_BLOCK_PER_ARTIFACT_IN_BUILD_ORDER

## Files created vs modified

| Path | Action | Artifact | Bytes (approx) |
|---|---|---|---|
| PATH | created | ARTIFACT_NAME | BYTES |
| PATH | modified (append) | ARTIFACT_NAME | +BYTES |
| PATH | created | ARTIFACT_NAME | BYTES |

Nothing on this list is overwritten. Modifications are appends inside delimited
`agentify-id` markers, so a rerun updates them in place instead of duplicating them.

## TARGET_NAME capability notes

| Capability | Supported | What I do |
|---|---|---|
| CAPABILITY_NAME | CAPABILITY_STATUS | SUBSTITUTION_OR_DIRECT_NOTE |

CAPABILITY_PROSE_NOTE

## Existing setup notes

EXISTING_SETUP_LINE

Defects I found in the setup you already have. Each is a **proposal**. I change nothing here
unless you approve that specific numbered item, and I restructure nothing either way.

| # | Existing file | What I found | Suggested change | Evidence |
|---|---|---|---|---|
| E1 | EXISTING_FILE_PATH | EXISTING_FINDING | EXISTING_SUGGESTED_CHANGE | EXISTING_EVIDENCE |

EXISTING_DEDUPE_NOTE

## Skipped candidates

Every candidate I generated is in exactly one of these three lists or in "What gets built" above.

### Skipped (insufficient evidence)

| Candidate | Type | Count found | Threshold | Why skipped |
|---|---|---|---|---|
| CANDIDATE_NAME | CANDIDATE_TYPE | COUNT_FOUND | THRESHOLD_MISSED | below the `mapping-rules.md` threshold for this type |

More usage brings these back — rerun after a week of normal work and they may qualify.

### Skipped (already covered)

| Candidate | Type | Already covered by | Why skipped |
|---|---|---|---|
| CANDIDATE_NAME | CANDIDATE_TYPE | EXISTING_FILE_OR_COMMAND | ALREADY_COVERED_REASON |

Building these would duplicate something you already have, which is the failure mode that gets
generated setups deleted.

### Skipped (low confidence — opt in to build)

| Candidate | Type | Score | Evidence | Why not built |
|---|---|---|---|---|
| CANDIDATE_NAME | CANDIDATE_TYPE | SCORE_WITH_BREAKDOWN | EVIDENCE_WITH_COUNT | LOW_CONFIDENCE_REASON |

These cleared their thresholds but sit at the bottom of the evidence scale — two or three
occurrences, or a signal that has gone quiet. Per PRD §7.4 they are listed and not built. Say the
word and any of them is included.

## Your approval

Nothing has been created yet. This file is the only thing I have written.

Reply with one of:

- **`approved`** — build everything above.
- **`approved except N, M`** — build everything except those numbered items.
- **`approved, but ...`** — tell me what to change and I'll rewrite this plan first.
- **`no`** — I stop, and you can delete this file.

I will not create, modify, or stage any other file until you reply.

## Rerun and undo

**Rerun.** Run the skill again any time. A rerun updates in place and never duplicates. Generated
sections inside a file you already had are rewritten between their `agentify-id` markers, so
anything you edited outside those markers is left alone; my own documents — this plan, `report.md`,
`build-manifest.json` — carry no markers and are regenerated whole under the same `agentify-id`.

**Undo.** UNDO_INSTRUCTIONS_EXACT

Full removal steps, with the final file list, go in `PLAN_DIR/report.md` after the build.
~~~

---

## 3. Token reference

| Token | Fill with |
|---|---|
| `GENERATED_DATE` | today, `yyyy-mm-dd` |
| `EVIDENCE_ONE_LINER_WITH_COUNTS` | the frontmatter `agentify-evidence` line — one line with numbers describing **this file's own** contribution, e.g. `2 artifacts approved, 1 skipped`. Not a per-artifact evidence string and not `report.md`'s line. Phase 7 step 6 writes the `plan` entry into `build-manifest.json`, and `verify_artifacts.py`'s `evidence_match` requires that entry's `evidence` field to be the **same string** as what you write here, so record it now and copy it verbatim later; a drift between them is a FAIL, and missing or empty is a `metadata` FAIL on its own |
| `REPO_NAME` | `discovery.repo.name` |
| `TARGET_NAME` | `Claude Code` or `Codex` |
| `BUILD_MODE` | `branch agentic-setup/<yyyy-mm-dd>`, or `stage-only`, or `in place — this repo is not under git` |
| `REPO_LOC`, `REPO_FILE_COUNT` | `discovery.repo.loc_estimate`, `.file_count` |
| `SESSION_COUNT` | `signals.transcripts.sessions.count`, or `0` |
| `SESSION_WINDOW_DESCRIPTION` | exactly one of four: `full history` · `last N days` · `history (not read — you declined)` · `history (none found — no prior sessions for this repo)`. The fourth is the consent-given-but-zero-transcripts case in §1.1; never print `full history` above a `SESSION_COUNT` of `0`. |
| `COMMIT_COUNT`, `GIT_WINDOW_DAYS` | `signals.git.window.commits_analyzed`, `.days` |
| `GIT_WINDOW_REASON` | `signals.git.window.reason`, quoted — one sentence saying which window ran and why (`no window reached the 50-commit floor …; using all history`). The window is adaptive, so a commit count with no window attached is unreadable. Delete the token only when `signals.git.available` is false. |
| `FINDING_COUNT` | phase-3 findings that carry a count |
| `*_COUNT` | per-type proposed counts. There is no `*_CAP` token and no cap column (`coverage.md` §1) |
| `*_NOTE` | one short clause, or `—`. Name what the number rests on, or why a type is empty: `one per zone in folders[]`, `no .env* file in this repo`, `commands.format is empty — Q16 was not answered`, `unsupported on this target`. **Never** `at cap` or `capped from N` |
| `OUTPUT_LOCATION_SENTENCE` | `on branch agentic-setup/2026-09-04`, or `staged in your working tree, uncommitted`, or `in place — this repo is not under git`. When §3.1's Fact 2 or Fact 3 named a path, the branch form is not true of every file and the skeleton's `Everything lands …` sentence is the first place that shows: write `on branch agentic-setup/2026-09-04, except M files your .gitignore excludes, which land in your working tree uncommitted` (or `…, which git has no pre-run copy of`). Same partition, same reason, as `UNDO_INSTRUCTIONS_EXACT` |
| `CONSENT_LINE` | verbatim, one of the **four** strings in `privacy.md` §8.1 — never a paraphrase and never a fifth string of your own. Pick on the consent value **and** `signals.transcripts.sessions.count`, never on consent alone: `full` with sessions `> 0` → the `full history read` line; `days:N` with sessions `> 0` → the `last N days read` line; `full` or `days:N` with sessions `== 0` → the `you consented, and there are no recorded sessions for this repo yet` line (§1.1 above is the whole handling of that run); `none` → the `declined` line. Consent alone cannot distinguish rows 1–3, which is exactly how two dogfood runs came to improvise a line |
| `GIT_EVIDENCE_LINE` | e.g. `Git: 412 human commits over the last 365 days, 4 contributors, 78% conventional commit subjects.` The count is `signals.git.authorship.commits_human` and every percentage is over the same denominator — **not** `window.commits_analyzed`, which still includes the bot commits the statistics exclude. Name the window (`window.days`) because it is chosen, not fixed. When `authorship.bot_pct` is material, say so: `(a further 41 commits were automation and are excluded)`. |
| `DEGRADATION_LINE_OR_DELETE` | the "declined" paragraph from `privacy.md` §8 when consent was `none`; the **no-history paragraph** from §1.1 step 3 when consent was given and `SESSION_COUNT` is `0`; delete the line when neither applies. It sits under `CONSENT_LINE` and expands on it — the two are never the same sentence twice |
| `INTERVIEW_ANSWER_SUMMARY` | one line naming only the answers that changed the plan |
| `DERIVED_MODE_LINE` | `mode`, how it was derived, and the escape (`interview.md` §4.8): `Everything lands on branch agentic-setup/2026-09-07 and is committed there, so `git branch -D agentic-setup/2026-09-07` removes the run. Say "stage only" and I will leave the files uncommitted instead.` On a repo with no git, say that instead and name the per-file undo. |
| `DERIVED_SERVICES_LINE` | the ranked service order and what ranked it (`interview.md` §4.8's four signals), then which ones got artifacts: `Ranked by how much of this repo depends on them: PostHog (client module + 4 env names), Drizzle (schema + migrations), Better Auth, Resend, Dodo (10 env names, no module yet). The first four get artifacts below; drop any by number.` **Never** `you told me you use X` — nobody was asked. |
| `DERIVED_TEAM_LINE` | `team_size`, the numbers behind it, and the escape (`interview.md` §4.2): `Writing for a solo repo: 82 of 103 human commits (80%) are yours, and there is no CONTRIBUTING or PR-template doc. Say "team" and I will widen the rules.` |
| `ARTIFACT_TYPE` | `Skill`, `Subagent`, `Rule`, `Hook`, `Permissions`, `MCP draft`, `Index doc section`. There is no plugin-manifest type (`adapters/capabilities.md`) |
| `EVIDENCE_WITH_COUNT` | the signal and its number, cluster ID included where there is one |
| `MODIFIED_DIFF_PREVIEW_BLOCK_OR_DELETE` | a fenced ```diff block, ≤ 20 lines, `+`-prefixed; delete the token entirely when nothing is modified |
| `CAPABILITY_STATUS` | the status word from `adapters/capabilities.md`: `Native`, `Convention`, `Draft`, `Substituted`, or `Not emitted` |
| `SUBSTITUTION_OR_DIRECT_NOTE`, `CAPABILITY_PROSE_NOTE` | the target's cell text, and the substitution note for every `Substituted` row — both from `adapters/capabilities.md` |
| `EXISTING_SETUP_LINE` | one line of context, from `discovery.existing_agentic_config.provenance.maturity_basis` when `provenance.vendored` is non-zero: `12 of the 61 skills in .claude/skills/ are your own; the other 49 are installed third-party guides.` **It is context, not a mode** — it changes nothing about what gets built (`coverage.md` §6). Never quote `user_scope` here: `~/.claude/skills` is not this repo's setup. Delete the line when `vendored` is zero and there is nothing to explain. |
| `EXISTING_FILE_PATH` | the repo-relative path of the existing artifact, from `discovery.existing_agentic_config`. Every row has one; a finding with no path is not a finding about their setup. |
| `EXISTING_FINDING`, `EXISTING_SUGGESTED_CHANGE` | the concrete defect (broken hook path, two rules contradicting on the same key, duplicate skill name) and the one-line change you propose. **Never propose a change to a symlinked or vendored artifact** — editing a symlink changes every repo that links it, and a vendored file is overwritten by its next install; report those and stop. |
| `EXISTING_EVIDENCE` | how you know — the frontmatter field, heading, or path you read, named literally |
| `EXISTING_DEDUPE_NOTE` | one line naming what you read to de-duplicate and confirming the bound: `To de-duplicate I read the frontmatter, headings and paths of N existing skills, agents and rules — no bodies, no source files, no transcripts.` |
| `SCORE_WITH_BREAKDOWN` | the `mapping-rules.md` §6 score and its components, e.g. `9 (F2 C2 D2 B1)` |
| `LOW_CONFIDENCE_REASON` | why this one is `F = 1` rather than what it is — the thin count against the row threshold, or the stale `last_seen`, in the candidate's own numbers. E.g. `count 3 across 81 sessions, and the two visible examples are different phrasings`, or `last touched 2025-11-04, outside the recency gate`. A `structural` candidate (a script that exists, a convention 77% of commits follow) is **not** low-confidence and does not belong under this heading — `mapping-rules.md` §6.1 draws the line |
| `COUNT_FOUND`, `THRESHOLD_MISSED` | the number the signal actually had, and the row threshold it missed |
| `EXISTING_FILE_OR_COMMAND`, `ALREADY_COVERED_REASON` | the existing artifact, CI job, or package script that already does it, named by path or command, and which anti-pattern applies (A1, A2, A9) |
| `UNDO_INSTRUCTIONS_EXACT` | **Not a fixed line — derive it, in phase 6, from the three facts below.** A static undo string has now shipped wrong twice, so this token has no default. It must promise exactly what `report-template.md` §3.1 will produce after the build, no more. See §3.1 under this table. |

### 3.1 Filling `UNDO_INSTRUCTIONS_EXACT`

The plan is written **before** the build, so `build-manifest.json` does not exist yet and there is
nothing to read the undo out of. But the undo the user is approving here is the one
`report-template.md` §3.1 will generate afterwards, and phase 6 can predict its **shape** exactly:
§3.1 keys on the `committed_paths` / `uncommitted_paths` partition, and the three facts below are
what put a planned path on one side of it. Predict the shape, name the mechanisms and their counts,
and say plainly that the report carries the final per-file list.

**Fact 1 — where the user is standing.** `git -C REPO_ROOT symbolic-ref --quiet --short HEAD` is
`<base_branch>`; empty output means detached HEAD, in which case `git rev-parse HEAD` is
`<base_commit>` and the checkout below names that instead. Phase 7 step 3 captures the same two
values into the manifest; the plan just quotes them so the user reads a real branch name at the
gate, not a placeholder.

**Fact 2 — which approved paths git will refuse to commit.** The plan names every path, and
`git check-ignore` answers for paths that do not exist yet, so run it now:

```bash
git -C REPO_ROOT check-ignore -v -- <every planned artifact path>
```

Exit **1** (no output) is the ordinary answer. Exit **0** prints one
`<gitignore file>:<line>:<pattern>\t<path>` line per ignored path, and each of those paths will land
in `uncommitted_paths`; only `>1` is an error. `.claude/` in a `.gitignore` is common (measured:
`vercel/turborepo` line 6) and on Claude Code that is most of the build.

**Fact 3 — which approved paths git has no pre-run copy of.** Fact 2 is not the only disqualifier,
and a plan that checks only `check-ignore` makes the same false promise on a different shape. Every
planned artifact whose action is **modified** — a file that already exists and gets an appended
block — must also be tracked *and* clean, or it cannot go in the commit either: committing it makes
`git checkout <base_branch>` **delete** the user's own file instead of restoring it, because the base
branch has no version to go back to. Measured on a fixture: a hand-written untracked
`.claude/settings.json` was committed and the undo destroyed it, directory and all. Ask git, per
planned modified path:

```bash
git -C REPO_ROOT ls-files --error-unmatch -- <planned modified path>   # exit 1 = untracked
git -C REPO_ROOT status  --porcelain      -- <planned modified path>   # any output = dirty
```

An untracked exit 1, or any status output, means that path is `restore: span` and lands in
`uncommitted_paths` alongside the ignored ones. **Use `status --porcelain`, not `git diff --quiet`**:
`diff` alone exits 0 on a file whose only change is staged (measured — ` M A.md` and `M  B.md` are
both dirty, and `diff --quiet` returns 1 and **0** respectively), so it would pass a file the phase 7
clean-tree gate is about to stop on. An ignored file is almost always untracked, so Facts 2 and 3
usually name the same files — but not always, and the case where they diverge is the one that
destroys user content.

Then write one of these three, and nothing else:

- **Branch mode, Facts 2 and 3 both empty — one mechanism.** Both lines, in this order:
  `git checkout <base_branch>` then `git branch -D <branch>` (plus
  `git push origin --delete <branch>` only if a PR is opened). The checkout is not optional and
  not implied: `git branch -D` refuses to delete the branch you are standing on, so the one-line
  form fails outright — and it is also what makes the undo *true*, because the appended blocks are
  committed on `<branch>` and never on `<base_branch>`, so moving back is what restores every
  modified file. **Both lines assume phase 7 commits**, which it does: a branch with nothing
  committed to it deletes without removing a single file while reporting success.
- **Branch mode, Fact 2 or Fact 3 named something — two mechanisms.** The same two lines as
  **step 1 of 2**, plus one sentence that names the second mechanism, the reason, and both counts.
  Write it as the future tense of `report-template.md` §3.1's `REMOVAL_MODE_SENTENCE`, and take the
  wording from that token rather than inventing a parallel sentence here — the two drifted apart
  once already, and §3.1 is the one the user ends up holding. Give the Fact 2 files their
  `.gitignore` pattern as the reason and the Fact 3 files `git has no pre-run copy of it`; if both
  lists are non-empty, both reasons go in the sentence. **Never promise that deleting the branch
  removes everything.**
- **Stage-only, or no git repo.** Say that nothing is committed and no branch exists, so the undo is
  the numbered per-file list `report.md` will carry — `report-template.md` §3.1's stage-only block
  and, with no repo, its marker-removal script. **Never print a branch-delete line here**, and do
  not reproduce those steps in the plan: they are generated from paths the build has not chosen yet.

Never suggest `reset --hard`, `clean`, or any history rewrite.

**`report-template.md` §3.1 is the single source for the undo's exact commands, and this section
does not restate them.** It generates them from `build-manifest.json`, and it emits a **variable
number of blocks** — the mode's block, plus branch mode's step 2 when `uncommitted_paths` is
non-empty, plus the marker-removal script when any artifact is `restore: span` — so no fixed count
of lines or steps stated here could stay true. The plan's job is narrower and finishes at the gate:
name the mechanisms, their counts and their reasons, so the user approves the undo they are actually
going to get. Duplicating §3.1's content here is what let the two files drift into contradicting each
other; cite it instead. End `UNDO_INSTRUCTIONS_EXACT` with the sentence the skeleton already carries
below it — the final file list goes in `PLAN_DIR/report.md` after the build.

---

**Conditional sections.** `## Audit findings` is written **only** when
`discovery.existing_agentic_config.maturity == "mature"`; in every other run delete the heading and
its whole body. Any of the four `### Skipped (...)` headings whose table would be empty is deleted
with its table — never left with a placeholder row, and never folded into another heading.

Ordering: list artifacts in **build order** — index doc, rules, hooks, skills, subagents, MCP
drafts, plugin manifest — and number them sequentially so `approved except 4` is unambiguous.

---

## 4. Filled example of one artifact block

This is the target quality. Note the count in the evidence, the concrete paths, the diff preview
for the modified file, and the "Will not" line that is specific enough to hold you to it.

~~~markdown
### 4. new-endpoint

- **Type:** Skill
- **File:** `.claude/skills/new-endpoint/SKILL.md`
- **Purpose:** Scaffold a new API route the way this repo already does it — handler, zod schema,
  route test, and an entry in the OpenAPI doc — in one pass instead of four prompts.
- **Evidence:** cluster `rs-004` "add endpoint for <resource>" — 9 prompts across 6 sessions
  (2026-06-14 to 2026-08-29); `src/api/` is the top directory hotspot at 71 commits;
  `src/api/routes/*.ts` and `tests/api/*.test.ts` co-change in 14 commits (confidence 0.82);
  correction "we validate with zod, not manual checks" seen 3 times.
- **Creates:** `.claude/skills/new-endpoint/SKILL.md`,
  `.claude/skills/new-endpoint/references/route-checklist.md`
- **Modifies:** `CLAUDE.md` (one line in the agentify section pointing at the skill)
- **Will not:** touch the database schema, write migrations, edit auth middleware, or run
  `bun test` for you — it prints the command and stops.

```diff
--- CLAUDE.md
+++ CLAUDE.md
@@ agentify section @@
+### Skills
+
+- `new-endpoint` — scaffolds a route handler, zod schema, test, and OpenAPI entry.
+  Derived from 9 similar requests across 6 sessions.
```
~~~

Anti-examples, all of which you must reject before printing:

- `**Evidence:** you frequently add API endpoints` — no count, no source. Cut the artifact.
- `**Evidence:** best practice for TypeScript repos` — templated. Cut the artifact.
- `**Will not:** anything unrelated` — meaningless. Name the specific adjacent things it declines.
- A modified file with no diff preview. Add the preview or move it to created.

---

## 5. Filled example — the existing-setup sections

From a run on a repo that already had 36 skills, 8 agents and 35 rules. **The full setup was still
proposed**; these sections are what the existing files changed — one line of context, the defects
found, and the candidates that were dropped as duplicates.

~~~markdown
## Existing setup notes

30 of the 36 skills in `.claude/skills/` are your own; the other 6 are installed third-party
guides. Nothing here is restructured, and none of it limited what I propose above.

| # | Existing file | What I found | Suggested change | Evidence |
|---|---|---|---|---|
| E1 | `.claude/settings.json` | The `PreToolUse` hook points at `.claude/hooks/lint.sh`, which does not exist. | Repoint it at `scripts/lint.sh`, or drop the hook entry. | `settings.json` hook `command` field; the path is absent from the tree |
| E2 | `.claude/rules/db.md`, `.claude/rules/data-layer.md` | Both scope `src/db/**` and give opposite instructions about raw SQL. | Keep one; I suggest `db.md`, which is newer. | `paths:` frontmatter and the `# heading` of each |

To de-duplicate I read the frontmatter, headings and paths of 36 existing skills, 8 agents and 35
rules — no bodies, no transcripts, no source files.

## Skipped candidates

### Skipped (already covered)

| Candidate | Type | Already covered by | Why skipped |
|---|---|---|---|
| pr-description-writer | skill | `.claude/skills/ship-pr/SKILL.md` | A9 — same request shape, same output; the existing skill already writes PR bodies |
| typecheck-before-commit | hook | `.husky/pre-commit` | A2 — the repo already enforces this in CI and a git hook |
~~~

Three things to copy from it: every row names a **file path** and how the defect was seen; the
de-duplication note states its own bound; and the context line says explicitly that the existing
setup **did not limit** what was proposed. A finding with no path is not actionable, a
de-duplication claim with no stated bound reads as if the whole setup was read, and a context line
without that last clause reads like an apology for building less.
