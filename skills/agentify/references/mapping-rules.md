# Mapping rules — findings to artifact candidates

Read this in **phase 4 (Propose) only**. Its input is the findings list from phase 3, which was
derived from `discovery.json` (`discover.py`) and `signals.json` (`mine_transcripts.py` +
`mine_git.py`). Its output is a **ranked candidate list**, grouped by artifact type, each candidate
carrying an evidence string, a one-sentence mechanism (§0.3), and a score.

Do not build anything here. Phase 6 is the gate.

---

## 0. The three rules that outrank the rest

Apply all three to every candidate, in order, **before** anything in §1. A candidate that fails any
of them is not a weaker candidate — it is a line in a skipped list.

### 0.1 A finding with no evidence count maps to nothing

If you cannot write the evidence string in §5 for a candidate — with a real number pulled
from `signals.json` or a real path pulled from `discovery.json` — the candidate does not exist.
Delete it. Do not soften it into a "nice to have". Do not build it "because most repos want one".

Every threshold below is a **minimum**, not a target. Being over the threshold makes something
*eligible*, not *required*.

**A structural fact is evidence, and it carries a number.** A service in `external_services[]` with
its evidence strings and `confidence`; a zone in `folders[]` with its file count; a framework with
the manifest entry that declares it; a `commands` slot with its `raw_scripts["#commands"]` citation;
and an **absence** — `existing_agentic_config.counts.hooks == 0` on a repo holding `.env*` files.
Those license the structural catalogue in `blueprint.md` §§3–6, and each row there names the field
it reads. What is still forbidden is a candidate whose trigger fired on nothing you can name.
The evidence string format for the structural form is §5's path form.

### 0.2 A count is only as good as what it counts

> **Mentions are attention. Only asks are demand.**

Two records can both read `count: 16` and mean nothing like each other.
`tool_mentions: {"name": "stripe", "count": 16}` means the token "stripe" appeared in sixteen
prompts. `request_shapes[].count = 16` means the user asked for the same thing sixteen times. The
first is a topic. The second is a job. Artifacts are built for jobs.

Every signal sits in exactly one tier. Read the tier off the signal-type token that opens the
evidence string (§5) — the tier is a property of the source record, never a judgement call:

| Tier | What it proves | Signal types |
|---|---|---|
| **1 — demand** | the user *asked for* it, *corrected* it, or *got burned by* it, in their own words, more than once | `request_shape`, `commands_requested`, `slash_command`, `correction`, `pain_signal` |
| **2 — structural dependence** | the repo itself depends on it — it is wired into a manifest, a script, CI, or the commit history | `package_script`, `ci`, `env_var_name`, `external_service`, `cochange_cluster`, `hotspot`, `directory_hotspot`, `commit_conventions`, `branch_naming`, `test_discipline` |
| **3 — attention** | the word came up | `tool_mention`, `file_hotspot` |

What follows is absolute:

- **Tier 1 sets `F` (§6).** Nothing else does.
- **Tier 2 can carry a candidate only where §3 allows it** — a hook wrapping an existing command,
  the index doc, permissions, the `blueprint.md` catalogue rows (12–16), and the co-change branch of
  row 6. On tier-2 evidence alone a
  candidate's `F` is **structural** and tops out at `1`: a structural fact proves the thing exists,
  not that working on it through the agent hurts. Capped is not the same as undifferentiated —
  **§6.3** grades structural `F` in quarters from `0.25` to `1` off the git and repo counts, so a
  run with no transcripts still ranks, and a structural candidate still cannot reach the `F = 2` a
  single piece of real demand earns.

- **Every git count is over human-authored commits.** `mine_git.py` classifies each commit's author
  and, by default, excludes machines — `github-actions`, `dependabot`, `renovate`, `checkpointer`,
  any `[bot]` name or no-reply sender — from conventions, branch naming, co-change, hotspots, test
  discipline and the revert rate. It was measured excluding **40 of 49** commits on one fixture and
  **46** on a real repo. The denominator for every percentage is
  `signals.git.authorship.commits_human`, **not** `signals.git.window.commits_analyzed`, which is
  the number of commits *read*. `signals.git.authorship` is context, not a trigger: a repo where
  82% of commits are automation is a real finding about how the repo is maintained and it explains
  why the human counts are smaller than the history looks, but it justifies no artifact of its own.
  When `commits_human` is `0`, every git percentage is computed over nothing — read none of them as
  a convention.
- **Tier 3 justifies nothing, ever.** It cannot meet a threshold, cannot set `F`, and cannot be a
  candidate's primary evidence. Its only legitimate uses: raising the confidence of a candidate that
  *already* clears a threshold on tier 1 or tier 2, and breaking a tie (§6). A candidate whose
  evidence string opens with `tool_mention:` or `file_hotspot:` is dead on arrival — anti-pattern
  A11, and the autopsy in §7.5.

`file_hotspot` is tier 3 because it counts *mentions of a path in prompts*. Git's `hotspot` and
`directory_hotspot` are tier 2 because they count *commits*. They look alike and are not alike.

### 0.3 The mechanism test — state it before you score

Before any candidate is scored, write **one sentence** naming the mechanism by which the artifact
changes what happens next time:

> Next time `<the evidenced trigger>`, `<artifact>` `<does this specific thing>`, so the user stops
> `<the specific work the evidence shows them doing every time>`.

Rules for the sentence:

1. Every blank is filled from the evidence record — not from what you know about the tool, the
   framework, or the service.
2. It fits in one sentence. If it needs an "and also", you have two candidates, or none.
3. **The mechanism must act on the failure the evidence records**, not on an adjacent one. An
   artifact that cannot catch the failure it cites is not weaker, it is the wrong artifact (A12).
4. If the sentence reads just as well with a different repo's name in it, you wrote a template.

**Fails:** *"Stripe came up 16 times."* → "Next time the user mentions Stripe, the MCP server
will…" — will **what**? The record never says what the user was doing, so the blank cannot be
filled. Dropped before it is ever scored.

**Passes:** *"The user asked to add an endpoint with validation and tests 7 times, and each time
re-specified the same three steps."* → "Next time the user says *add a `<noun>` endpoint*, the skill
runs the three steps they re-type every time — zod schema, handler, test file — in this repo's
shape, so they stop re-typing them."

The sentence is not scratch work. It is carried into the candidate list as `Mechanism:` (§7.3) and
becomes the **Purpose** line of that artifact's plan entry in phase 6. A plan entry whose purpose
cannot be written this way was never a real candidate.

---

## 1. Mapping table (PRD §8, expanded with thresholds)

`count` = the `count` field on a `signals.json` record. `sessions` = the `sessions` field on a
`request_shapes[]` record (distinct session files the shape appeared in). Thresholds are AND-ed
unless stated.

| # | Finding type | Source record | Decision rule (numeric) | Artifact |
|---|---|---|---|---|
| 1 | Repeated multi-step procedure | `request_shapes[]` | `count >= 3` **and** `sessions >= 2` **and** the skeleton implies **>= 2 distinct steps** (e.g. "add endpoint + tests + docs") | **Skill** |
| 2 | Repeated single-step ask | `request_shapes[]` | `count >= 3`, `sessions >= 2`, but only **1 step** and it maps to an existing repo command | **Index-doc line** (not a skill) — see §2.5 |
| 3 | Work needing isolated context, a persona, or parallelism | `request_shapes[]` + `pain_signals[]` | `count >= 3`, `sessions >= 2`, **and** at least one of: output is a large read-only pass (review, audit, research), the ask names a role ("act as", "review as"), or the user ran it alongside other work | **Subagent** |
| 4 | Deterministic check the user keeps asking for | `commands_requested[]`, `slash_commands[]`, `pain_signals[]` | the same check is requested **`count >= 2`** times **and** it is a single non-interactive command that exits 0/1 | **Hook** |
| 5 | Correction repeated by the user | `corrections[]` | **`count >= 2`** | **Rule** (global or path-scoped — see §2.3) |
| 6 | Convention tied to specific paths | `cochange_clusters[]` **or** a tier-1 record (trigger); `directory_hotspots[]` (corroboration only — §1.3) | co-change `support >= 3` **and** `confidence >= 0.5` **and** `still_exists: true` **and** not stale (recency gate below) **and** all four gates of the **scope test in §1.2** pass (tier 2); **or** a tier-1 record at its own row threshold whose examples name paths under one directory. `directory_hotspots[]` can corroborate either branch at `commits >= 3` and never triggers on its own; `file_hotspots[]` is tier 3 — supporting evidence only, never the trigger | **Path-scoped rule** |
| 7 | Commit / branch / PR convention | `commit_conventions`, `branch_naming[]`, `pr_patterns` | `conventional_pct >= 0.6`, or `ticket_prefix_pct >= 0.6`, or a branch pattern with `count >= 5` | **Index-doc line.** A **hook** only on the terms §3 already sets for a tier-2 hook — the repo has a commit-message checker in `discovery.commands` / `raw_scripts` that no CI job runs, and the hook wraps *that command*. Cheapness is not a tier; a percentage on its own buys no hook. See the §3-outranks note below |
| 8 | External system the user does **work against, through the agent** | `discovery.external_services[]` + tier-1 records naming it | all four gates in **§1.1** pass: high-confidence structural entry, **tier-1 work evidence `count >= 3` across `>= 2` sessions**, no existing local loop, and a stated capability delta. `tool_mentions` **never** counts, at any size | **MCP recommendation + draft config** (never credentials) |
| 9 | Long-form knowledge re-derived each session | `request_shapes[]` where the skeleton is a question ("how does…", "where is…", "why do we…") | `count >= 3` **and** `sessions >= 2` **and** no procedure to run | **Reference doc** |
| 10 | Guardrail gap | `pain_signals[]` + `discovery.ci[]` + `test_discipline` | a failure the user complained about `count >= 2` that CI does **not** already catch | **Hook** (preferred) or **rule** if not mechanisable |
| 11 | Missing/thin index doc | `discovery.existing_agentic_config.index_docs[]` | absent, or `< 400 bytes`, and `discovery.commands` has **>= 2** populated commands | **Index doc** (always exactly one; always built, never ranked) |
| 12 | **Zone with a stateable convention** | `discovery.folders[].zone` (incl. `routes`, `actions`, `jobs`), **or a domain zone** — a depth-1 `folders[]` row with `zone == null`, `files >= 15`, not a dot-directory — corroborated by `signals.git.directory_hotspots[]` / `cochange_clusters[]`, a README under it, an index-doc section naming it, or a `commit_conventions` scope | the zone directory exists and holds files, **and** the convention is readable off the repo (an ORM, a validator, a test runner, a styling system, the `sample_files` naming pattern, the doc that describes it) rather than invented. **The index doc stating the convention licenses the rule; it never covers it** (`blueprint.md` §2.1) | **Path-scoped rule** — one per zone, per workspace in a monorepo (`blueprint.md` §5.1) |
| 13 | **Guardrail the repo has no protection for** | an absence: `existing_agentic_config.counts.hooks`, `.rules`, plus `discovery.env_var_names`, `.package_managers`, `.commands`, `external_services[]`; **or a doc-stated check** — a mechanically checkable rule in the index doc or a `docs[]` row of kind `design` / `style-guide` / `contributing` (a forbidden import, class, literal, command or branch) | the exposure is present in the repo (a `.env*` file, an ambiguous package manager, a destructive command this stack has, a written rule with no enforcement) **and** nothing in `ci[]` or `existing_agentic_config` already catches it. A written rule needs no transcript correction behind it | **Hook** — the `blueprint.md` §4.1 catalogue |
| 14 | **Repeated command surface the user keeps approving by hand** | `discovery.commands` (`>= 2` populated slots) + `signals.transcripts.commands_requested[]` | the target supports a permissions block | **Permissions** — one allow/deny block, `blueprint.md` §4.2 |
| 15 | **A service the user works with, in the codebase** | `discovery.external_services[]` + `frameworks[]` + the modules that use it in `folders[]` / `file_hotspots[]` | the service is `confidence >= "medium"`, **a module in the repo actually calls it**, and a `blueprint.md` §6.1 row names a workflow for it. Services are **ranked, never filtered by a question** (`interview.md` §4.8); the user drops what they do not want at the phase 6 gate | **Skill** — the integration workflow, plus its **subagent** where §3 of `blueprint.md` calls for tool restriction |
| 16 | **The setup this run just built** | the built-artifact list itself | `>= 1` artifact was built | **Skill** — `setup-manager`, unconditional (`blueprint.md` §6.3) |
| 17 | **A procedure the developer already wrote down** | a `discovery.docs[]` row of kind `guide`, or a README / index-doc section whose heading is a procedure ("Adding a tool to …", "Local Postgres for dev"), or `>= 3` `raw_scripts` sharing a prefix that a doc orders | the doc names real files and real commands that exist in `folders[]` / `raw_scripts`, and there are `>= 2` steps. **The doc never covers the skill** (`blueprint.md` §2.1, A13) — it is the skill's `references/` source | **Skill** — guide-to-skill / dev-environment (`blueprint.md` §6.2) |

Notes that apply to the whole table:

- **One finding may produce more than one artifact.** The PRD example is exact: a repeated
  procedure becomes a *skill*, and the final verification step inside it becomes a *hook*. When you
  do this, both candidates carry the **same evidence string** and the plan says they come from one
  finding.
- **Tier gate.** §0.2 outranks every number in this table. A threshold met only by a tier-3 count is
  not met. Delete the tier-3 line from a candidate's evidence: if what remains clears no threshold,
  the candidate clears no threshold.
- **§3 outranks this table's Artifact column, not only its numbers.** The tier gate above is about
  *counts*; this one is about *types*. §3 sets a **minimum tier per artifact type**, and where a row
  here names an artifact the evidence's tier cannot carry, §3 wins. The row is where a finding gets
  its threshold; §3 is where an artifact gets its licence.
  **Row 7 is the case this note was written for, and it was wrong for a while.** It licensed "a
  **hook** only if a commit-msg check is cheap" off `commit_conventions`, `branch_naming[]` and
  `pr_patterns` — all **tier 2** — while §3's Hook row admits tier 2 in exactly one situation: *the
  hook wraps a command that already exists in `discovery.commands` and CI does not run*. A hook was
  therefore buildable from evidence §3 calls insufficient. **§3 wins**, and row 7 now says so.
  Read the resolution as one rule rather than an exception. A commit-message hook is admissible when
  it is the ordinary tier-2 wrapping case — a `commitlint`, a `commit-msg` script or an equivalent
  checker sits in `discovery.commands` or `discovery.raw_scripts`, no CI job runs it, and the hook
  runs *that command*. With no such command, `commit_conventions` is a **percentage over history**,
  and a percentage is not a policy: at `conventional_pct 0.6` a hook enforcing the convention rejects
  the four commits in ten this repo writes the other way. That finding's artifact is the
  **index-doc line** row 7 names first. A hook re-enters only through tier 1 — a `correction` or
  `pain_signal` about commit messages at row 5's `count >= 2` — which is the Hook row's ordinary
  route and needs no licence from row 7 at all.
- **Overlap gate.** Two records built from the *same* turns are one piece of evidence, not two.
  Never add their counts: cite the larger, carry the smaller as `Supporting:`, and say they share
  turns. See §6.2 — which is also where the "one finding, two artifacts" note above stops being a
  licence to count the finding twice.
- **Confidence gate.** A finding marked `low` confidence in phase 3 may be listed as a candidate but
  is **not built** unless the user opts in during phase 5. Mark it `opt-in` in the candidate list.
  §6.1 adds a second, mechanical source of `low-confidence`: any candidate that lands at `F = 1` on
  thin or stale tier-1 demand.
- **Recency gate — transcripts.** A `request_shapes[]` cluster whose `last_seen` is more than 90
  days old scores `F = 1` maximum (§6) even if `count` is high. Old repetition is often already
  solved.
- **Recency gate — git.** `cochange_clusters[]`, `hotspots[]` and `directory_hotspots[]` carry
  `last_seen` and `still_exists`, so the gate applies to them too and a rule can no longer be aimed
  at a directory that was refactored away two years ago.
  - `still_exists: false` ⇒ **`F = 0`, not a candidate, at any support.** The support count is real
    history and the code it describes is gone; no rule, hook or skill can target a path that is not
    there. `mine_git.py` emits a warning naming how many such rows it returned — that warning is a
    stop, not a note.
  - **Stale** ⇒ `F` capped at the bottom structural band (§6.3, `F = 0.25`). Measure staleness
    against `signals.git.window.last`, **never against today**, and call a row stale when its
    `last_seen` is older than the wider of *180 days* and *half the analysed window*
    (`window.first` → `window.last`). 180 days is the narrowest rung of the miner's adaptive ladder,
    so it is the line the miner itself would have drawn had the repo been busy enough to stay on
    rung one; the half-window arm exists because the ladder widens precisely on slow repos, where a
    flat 90 days would call a living convention dead.
- **Session-count degradation.** If `sessions.count == 0` (no transcripts, or consent declined),
  rows 1, 3, 5 and 9 have no possible evidence and produce nothing. What remains available on repo
  and git evidence alone: **row 6 through its co-change branch**, row 7, row 11, the structural
  catalogue rows **12–16**, and hooks that wrap an already-existing repo command (row 4 via
  `discovery.commands`). Rows 12–16 are why a no-history run on a real codebase still produces zone
  rules, guardrail hooks, permissions, integration skills and `setup-manager` — see `coverage.md` §3.
  Row 6 belongs on that list and was missing from it: `cochange_clusters[]` are **commits**, and a
  commit has nothing to do with whether the user consented to transcript mining. On a no-history run
  co-change is usually the strongest evidence in the whole run — dropping it was dropping the best
  thing left. Only row 6's *second* branch, the tier-1 record whose examples name paths under one
  directory, dies with the transcripts.
  Row 8 stays reachable through §1.1 gate 2's **structural alternative** — a service this run also
  built a skill or subagent for — which is what replaced the retired phase-5 confirmation.
  Every surviving candidate takes its `F` from **§6.3**, which is what stops the whole pool from
  sitting at one value on the axis the score doubles. Say so in the plan.

### 1.1 Row 8 in full — the external-system test

Row 8 is the row most easily satisfied by noise, because every repo of any size has services in its
`package.json` and every prompt about a feature names them. Four gates, in order; **stop at the
first failure** and do not average them.

**Gate 1 — structural (tier 2).** An `external_services[]` entry with `confidence == "high"`: a
direct dependency plus an env-var *name* or a config file. Lockfile-only, or a transitive
dependency, fails here (A6).

**Gate 2 — work (tier 1).** At least **3 occurrences across `>= 2` sessions** in
`request_shapes[]`, `commands_requested[]`, `corrections[]` or `pain_signals[]` whose text both
names the system **and** shows the user doing work *against* it through the agent: reading its live
state, querying it, creating or updating objects in it, or debugging a real response from it. Asks
that merely happen nearby ("fix the checkout page") do not count. `tool_mentions[]` does not count
at any size — it is tier 3.
**Gate 2's structural alternative — the coupling, not a confirmation.** *(Interview Q4 used to
supply this gate on a no-history run by asking the user which services they touch. It is retired:
`interview.md` §4.1, §4.8.)* Gate 2 is also met when **this run built a skill or a subagent for that
service** (`blueprint.md` §7). That is a real substitute rather than a softening: a skill only
exists because §6.1 named a workflow and the four conditions in §3 passed, so the draft is licensed
by an artifact that itself had to clear the personalization test — not by a dependency, and not by
an answer. A service with no skill, no subagent and no tier-1 record gets **no draft**, on any
history, and the plan says which of the three was missing.

**Gate 3 — local loop.** Search `discovery.commands`, `discovery.raw_scripts`, `discovery.folders`
(zone `scripts`), the repo's own CLIs, and
`discovery.existing_agentic_config.mcp_servers_by_source` for the service name. Search that list,
**not `.mcp.json` alone**: it carries every server found on every target and at both scopes — a
`[mcp_servers.<name>]` in `.codex/config.toml` and one in the user's `${CODEX_HOME}/config.toml`
count exactly as much as an entry in `.mcp.json`, and each row names its `target`, `scope` and
`file`. **If the repo already has a working local path to that system** — a `<service>-listen`
script, a `dev:<service>` command, a vendored CLI, an MCP server already configured on either
agent — the candidate is not an MCP draft. It goes to `### Skipped (already covered)` naming the exact script or command. "The MCP
server could do more" is not evidence that the existing path is failing; a `correction` or
`pain_signal` *about that path* is.

**Gate 4 — capability delta.** One sentence: what the MCP server lets the agent do that the local
loop cannot — almost always *read live state that does not live in the repo*. If the delta is "it
would be more convenient", stop.

Only a candidate that clears all four is an MCP draft, and its mechanism sentence (§0.3) must name
the work found in gate 2, not the service. Worked end to end, as a failure, in §7.5.

### 1.2 Row 6 in full — the scope test

**What used to be here, and why it is gone.** Row 6 required the paths in a co-change cluster to
*share a directory prefix*. Measured on real repos, that gate rejected the two most valuable
co-change conventions there are:

- **claude-code-action** — six clusters of the form `src/x.ts` + `test/x.test.ts`, support 3–5, all
  rejected. The src↔test mirror is the commonest and most useful convention in a JS/TS repo, and in
  a repo with parallel `src/` and `test/` trees it never shares a prefix below the root.
- **vercel/turborepo** — `crates/turborepo-schema-gen/src/main.rs` +
  `packages/turbo-types/src/types.ts`, rejected. A generator and the types it emits, in different
  packages: precisely the coupling a path-scoped rule exists to protect in a monorepo, and precisely
  the one a shared prefix cannot see.

And it was never reliable protection against the thing it was there for. The same turborepo run put
four `github-actions[bot]` release clusters at the top — support 134, 134, 131, 130, every one at
confidence 1.00 — and a release bump that edits sibling package manifests shares a directory prefix
as readily as any genuine convention does. Reproduced on a purpose-built fixture: 40 bot release
commits bumping `packages/a|b|c/package.json` together produce a support-41, confidence-1.00 cluster
which clears the prefix gate cleanly and outranks the human `src/parser.ts` + `test/parser.test.ts`
mirror underneath it — the mirror being the one the prefix gate throws away. One run, both errors:
the mechanical cluster admitted, the real one turned away. A shared prefix was never the
requirement. It was a proxy, and it proxied the wrong property.

**What the requirement actually is.** A path-scoped rule needs two things, neither of them a prefix:
**a scope it can be attached to for every path it names**, and **a coupling that is a decision
somebody made rather than a side effect of how the repo commits.** Four gates, in order; stop at the
first failure and do not average them.

**Gate 1 — every path gets a scope, then the scopes collapse and the cap counts what is left.**
Write one glob per path, derived from the path itself: a directory (`src/db/migrations/**`) or a
directory plus a filename pattern (`src/**/*.test.ts`). It does not have to be one prefix, and that
is the change §1.2 was written for. `**/*` is not a scope. A path that nothing narrower than the repo
can name fails here.

Then do these two things in order, because the cap is on **independent scopes, not on paths**:

1. **Collapse.** Two or more globs merge into one scope when they name the same place said more than
   once. Two mechanical tests, either is enough:
   - **Siblings under a common parent** — every glob is `<parent>/<one segment>/…` for the same
     `<parent>`.
   - **Variant segment** — the globs become identical after replacing **one** differing segment with
     `*`: a locale (`docs/es`, `docs/fr`, `docs/zh`), a platform, a version directory, a workspace
     name. The differing segment must be the *only* difference; two segments differing is two places.

   Write the collapsed scope as the wildcard form (`docs/*/**`) when the convention really is about
   the variant family — every locale of one doc tree — and the rule body then names the evidenced
   members. **Do not write a brace list in a bare `scope:` scalar.** Measured against the shipped
   verifier: `scope: docs/{es,fr,zh}/**` is split on its commas by `extract_globs()` into
   `docs/{es`, `fr`, `zh}/**` and `rule_scope` FAILs it twice for unbalanced braces. Braces survive
   only inside a YAML flow list (`scope: [docs/{es,fr,zh}/**]`), and a YAML list of one glob per line
   always works — prefer one of those two if you need the members enumerated. *(Re-verified against
   the shipped `verify_artifacts.py` on 2026-09-05: the bare scalar splits into exactly those three
   fragments and `validate_glob()` returns `unbalanced { } in glob` for the first and the third; the
   flow-list form returns the single glob intact; `docs/*/**` validates clean.)*
2. **Bound: at most three independent scopes** — that is, three after the collapse. The number of
   paths behind them is not capped. A candidate that still needs four unrelated scopes is not one
   convention: split it, or send it to §2.3 as a global rule.

**What the old cap was protecting, and why counting paths was the wrong meter.** The rule used to
read *"up to three scopes, one per path in the cluster"*. Two problems, one on each branch of row 6:

- On the **co-change branch the number was inert.** `analyze_cochange()` emits pairs and triples
  only, so "one per path in the cluster" could never exceed three anyway. The cap never bound there
  and was never tested there.
- On the **tier-1 branch it bound arbitrarily.** Measured on the axios run: one documentation
  convention covering `docs/pages`, `docs/es`, `docs/fr` and `docs/zh` — the English source tree and
  its three translations, four siblings under one `docs/` parent, one convention — and the cap forced
  the run to drop one of the four it had evidence for and gave it no basis for choosing which. Note
  that both collapse tests fire here and either alone is enough: they are siblings under a common
  parent, **and** they become identical when the one differing segment is replaced with `*`.

The property the cap was proxying is real and is kept: **a rule that names many unrelated places is
not one convention.** It is a bag of rules, or a global rule wearing a path scope (gate 2), and a
model handed a long list of unrelated globs applies it loosely everywhere. Counting *independent*
scopes measures exactly that property, and counting paths only approximated it — four siblings under
one parent are one place named four times, and they add nothing a reader has to hold. Gate 3 is the
second half of the protection and is unchanged: one sentence naming a trigger side and an obligation
side must still be writable, and four collapsed locales sit on **one** side of it.

**Gate 2 — the scope set is narrower than the repo.** If the union of the globs covers everything a
contributor edits — `src/**` in a single-package repo, `packages/**` in a monorepo where that is all
there is — you have a global rule wearing a path scope. This is **not a skip**: send it to §2.3 and
write it as an index-doc line or an unscoped rule file, which is what it always was.

**Gate 3 — one sentence naming both sides and the direction.** *"When you change `<scope A>`, also
`<verb>` `<scope B>`, because `<what the co-change record shows>`."* If you cannot say which side is
the trigger and which is the obligation, you have a correlation, not a convention. This is §0.3's
mechanism test with both scopes filled in, and it becomes the plan entry's Purpose line.

**Gate 4 — the coupling is a decision, not a process.** This is what the prefix gate was *supposed*
to protect against, written as the thing itself instead of a proxy for it. Reject when the
co-occurrence is produced by a machine or a sweep rather than by design. Any one of these is enough:

- **the commits behind it are bot-authored.** `mine_git.py` excludes machines by default, so on a
  normal run this is already done for you; if you are reading a run made with `--include-bots`,
  gate 4 is doing that filtering by hand, and `signals.git.authorship.bot_pct` says how much there
  is to filter.
- **the paths differ only in a version, a changelog entry, or a lockfile-adjacent field.** That is a
  release bump, not a coupling.
- **it is a mass rename, a formatter sweep, or a generated-file refresh.** The miner already drops
  lockfiles, generated suffixes and commits touching more than 40 files — a 39-file sweep survives.
- **`support` is a large fraction of `signals.git.authorship.commits_human`.** Those are not files
  that change *together*; they are the files this repo always touches.

**The three shapes that pass — admit these by name.**

| Shape | Looks like | Scopes the rule carries |
|---|---|---|
| **Same zone** | both paths under one directory: `apps/web/src/components/cancellation/preview-display.ts` + `…/preview-display.test.ts` (support 7, confidence 1.00, measured) | one — the shared directory |
| **Mirror** | basenames correspond across a source↔test (or source↔story, source↔doc) transform in *parallel trees*: `src/x.ts` + `test/x.test.ts`, `foo.py` + `tests/test_foo.py`, `x.go` + `x_test.go`, `apps/triggers/src/deferred/forward-event-to-cio.ts` + `apps/triggers/tests/deferred/forward-event-to-cio.test.ts` (support 10, confidence 1.00, measured) | two — the source scope and the mirror scope, with the naming transform stated in the rule |
| **Cross-package producer / consumer** | different workspaces, one of them a source of truth (schema, proto, OpenAPI spec, migration, codegen input) and the other generated from or checked against it: `crates/turborepo-schema-gen/src/main.rs` + `packages/turbo-types/src/types.ts` | two — the source-of-truth scope and the consumer scope; the direction runs from the source of truth, and the rule must say which way |

A cluster matching none of the three but clearing all four gates is still admissible — these are the
shapes seen often enough to name, not an allow-list. A cluster that matches a shape but fails a gate
is **not**: the shapes are shorthand for gates 1–3 and never a way past gate 4.

**Corroborate the cross-package shape before trusting it.** Confirm both sides really are separate
packages using `discovery.monorepo.workspaces`, and confirm the source-of-truth reading with
something in `discovery` — a generate/codegen entry in `discovery.raw_scripts`, a CI step that runs
it, or a `scripts` zone in `discovery.folders`. Without that corroboration a cross-package cluster is
two files that moved together in one release, which is gate 4 territory.

**A rejected cluster is a line in a skipped list, and the line names the gate:**

```
### Skipped (insufficient evidence)

| Candidate | Type | Evidence | Why not built |
|---|---|---|---|
| packages-version-rule | path-scoped rule | cochange_cluster: packages/a/package.json + packages/b/package.json + packages/c/package.json (support 41, confidence 1.00, all history) | §1.2 gate 4 — every commit behind it is `github-actions[bot]` release automation; a version bump is not a convention |
```

### 1.3 Row 6 and `directory_hotspots[]` — a scope selector, never a trigger

Row 6 lists `directory_hotspots[]` among its sources and the row's numbers are for co-change and for
a tier-1 record. This section is the missing number, and it is deliberately not a trigger threshold.

**A directory hotspot cannot trigger a path-scoped rule, at any count.** `{path, commits,
first_seen, last_seen, still_exists}`, aggregated to depth 2, says *where* commits land. It does not
say what is true about that directory, so §0.3's mechanism sentence has no content to put in it —
"next time you change `src/api/**`, the rule …" **does what?** The convention has to arrive from
somewhere else. This is also what §3's table already implies: the only path-scoped-rule row there is
the co-change one, and nothing licenses a directory-hotspot-only rule.

**What it may do, and the bar for doing it.** Cite a directory hotspot only as `Supporting:`, under
a primary line that already clears row 6 on its own, and only when all three hold:

- `commits >= 3`, **and** the count is a share of `signals.git.authorship.commits_human`, not of
  `window.commits_analyzed` (§0.2);
- `still_exists: true` and not stale (§1's git recency gate);
- the hotspot's directory **contains the scope the rule names, or is contained by it** — a hotspot
  somewhere else corroborates nothing.

Then it does two useful things: it confirms that the scope gate 1 produced is where work actually
happens, and it sets structural `F` through **§6.3 row 2**, which reads
`directory_hotspots[].commits` as a share of `commits_human`. Grading a candidate is the whole of
its job.

**Why `commits >= 3` and not the miner's own floor: there is no floor.** Unlike every
`signals.transcripts` list, `mine_git.py` applies no minimum here — `analyze_hotspots()` sorts by
commits and takes the top `MAX_DIRECTORY_HOTSPOTS = 15`, so a one-commit directory is emitted
whenever nothing beats it. Measured on a `--depth 1` clone of `vercel/turborepo`: **15
`directory_hotspots` rows, every one `commits: 1`**, the top row being `(root)` — which fails gate 2
outright. A row you can see is not, here, evidence that survived a filter.

---

## 2. Disambiguation — the overlapping cases

Work these in order. The first rule that matches wins; do not re-litigate downstream.

### 2.1 Skill vs subagent

| Signal | Pick |
|---|---|
| A repeatable multi-step procedure the **human triggers** and watches | **Skill** |
| Needs its **own context window** (reads many files, produces a long pass, would pollute the main thread) | **Subagent** |
| Needs a **specialist persona** or an opinionated reviewer stance | **Subagent** |
| Runs **in parallel** with the main thread, or fans out over N items | **Subagent** |
| The output is edits to the working tree that the human wants to see land step by step | **Skill** |

Default when both fit: **skill**. Subagents cost more to build and are harder to verify, so a
subagent has to earn the isolation, the persona, or the tool restriction it exists for
(`blueprint.md` §3). Never build a subagent when a skill would do.

**"Never both" forbids two artifacts that each do the whole job. It does not forbid a pair.** A
skill that is the human-facing entry point — gathers the inputs, reads the context, formats the
output — and delegates the isolated or tool-restricted part to a subagent is **one proposal with
two files**: `query-db` → `db-inspector`, `review-pr` → `pr-reviewer`, `new-component` →
`designer` (`blueprint.md` §1.3). The plan lists the pair as one numbered entry with one evidence
line. What this rule still forbids is a `query-db` skill that runs the queries itself *and* a
`db-inspector` that also runs them.

### 2.2 Rule vs hook

| Signal | Pick |
|---|---|
| A convention the **model must remember** while writing code (naming, layering, library choice at authoring time) | **Rule** |
| A check that is **deterministic and cheap** — one command, exits 0/1, under ~5s typical | **Hook** |
| Both are possible | **Hook**, and only add the rule if the hook fires too late to be useful |

> **If it can be a hook, prefer the hook.** A hook does not depend on the model remembering, does
> not consume context, and cannot be argued with. A rule that duplicates a hook is noise — do not
> write both for the same check unless the rule prevents work the hook would only reject at the end.

Hook disqualifiers (fall back to a rule): needs network, needs credentials, takes longer than ~10s,
is interactive, or would block ordinary edits.

> **Both targets have hooks.** Verified 2026-09-05 against codex-cli 0.152.1: Codex loads
> `<repo>/.codex/hooks.json` — the same three-level shape as Claude Code's `settings.json` hooks
> block, 12 events, regex matchers over tool names. A finding that maps to a hook maps to a hook on
> **both** targets, so there is no substitution for the plan to state and no reason to downgrade a
> hook candidate to a rule because the target is Codex. What the plan *must* still state on Codex is
> that the hook is **installed, not armed**: it needs project trust plus a one-time `/hooks` trust
> approval before it runs. See `adapters/capabilities.md` for the exact wording; do not open an
> adapter here.

**A forbidden-command finding on Codex has a second home.** "Never run `npm` here, the package
manager is `bun`" can be a `PreToolUse` hook on both targets, and on Codex it can instead be
`.codex/rules/<name>.rules` — `prefix_rule(pattern=["npm"], decision="forbidden",
justification="<evidence>")` — a deterministic in-session command gate rather than a script.
Either is typed as **one hook** in the plan. The rules form is experimental per the Codex docs and
is trust-gated the same way; pick it only when the check is purely "this command must not run", and
say which form the plan chose.

**Neither form is authorized here.** This section only decides *which shape* a forbidden-command
finding takes. Whether the finding may become one at all is §3's **Rule — command policy** row —
tier 1 only, the record must name the command, and there is no discovery-only form. Clear that row
before you pick a shape.

### 2.3 Rule file vs index-doc line

| Signal | Pick |
|---|---|
| Applies to **specific paths** (`src/db/**`, `app/api/**`) | **Path-scoped rule file** |
| **Global and short** — fits in one or two lines, always true everywhere | **Index-doc line** (`CLAUDE.md` / `AGENTS.md`) |
| Global but long (more than ~5 lines of explanation) | **Rule file**, linked from the index doc in one line |

A correction (row 5) whose examples all mention paths under one directory is a **path-scoped rule**.
A correction with no path context ("use bun, not npm") is an **index-doc line** if it is one
sentence, a global rule file if it needs qualification.

**The index doc never covers a rule.** This table decides where a *new* convention goes; it is not
a licence to skip a zone rule because the index doc already has a section on that zone. Those are
two different mechanisms with opposite costs — the index doc is loaded in every session whether or
not the zone is touched, a `paths:`-scoped rule is loaded only when it is — and a rule is what
`pr-reviewer` enumerates as its checklist. When the index doc already states the convention, the
rule quotes that sentence, points at the section, and adds what the code shows (`blueprint.md`
§2.1, §5.1). "It would only restate `CLAUDE.md`" is A17, not a skip reason.

### 2.4 Skill vs reference doc

| Signal | Pick |
|---|---|
| There are **steps to run**, in order, with a definition of done | **Skill** |
| It is **knowledge the model rediscovers** — how a flow works, where things live, why a decision was made | **Reference doc** |
| Steps exist, but they change every time and only the context is stable | **Reference doc** |

A reference doc is cheap and never blocks anything, so a borderline case goes to the reference doc.

**A guide the repo already has is the opposite case.** A `docs[]` row of kind `guide` — "Adding a
capability", "Local Postgres for dev" — is a procedure the developer wrote down. It is row 17's
evidence and the skill's `references/` source; it is never the reason the skill is not built
(`blueprint.md` §2.1). The knowledge half of a repo lives in its docs; the skill is what makes the
agent follow the procedure without being told to read them.

### 2.5 Skill vs "just an index-doc line"

If the entire procedure is **one command that already exists** in `discovery.commands` or
`discovery.raw_scripts`, it is not a skill. It is one line in the index doc naming the command. See
anti-pattern A1.

### 2.6 The step test — count steps from the evidence, and never count knowledge as a step

Rows 1 and 2 differ on one word: **steps**. Getting it wrong is how a template gets built with a
real count attached to it — the hardest failure to spot, because the evidence is genuinely strong.
Count steps by this procedure and no other:

1. **List** the steps from the record's `skeleton` and `examples[]`, plus any `correction` or
   `pain_signal` attached to the same finding.
2. **Keep a step only if it is evidenced**: the user spelled it out in the ask, or skipping it
   produced a correction or a redo. Steps you can imagine the task needs do not count. Steps the
   underlying command already performs do not count. A *constraint* ("don't push") is not a step.
3. **Extract the knowledge first.** A convention the artifact would *follow* — a message format, a
   naming scheme, a scope vocabulary, a house style — is not a step. It is a rule or an index-doc
   line (§2.3), and it belongs there whether or not a skill is ever built.
4. **Count what is left.** Two or more evidenced steps → row 1, **skill**. Exactly one, and it maps
   to an existing repo command or an existing slash command → row 2, **index-doc line** (A1, A7).

The trap this closes: a one-command ask *looks* multi-step because the artifact would also carry
**knowledge** — "and it should write the commit message our way". Move the knowledge into the rule
and the ask is one command again. If the user really is doing that knowledge work by hand every
time, it shows up as a `correction` or a `pain_signal` about the *output* — and that is what
promotes it back to a skill, not the mere existence of a convention.

When this test demotes a candidate, put it in the plan under `### Skipped (already covered)`, name
the command, and add one line saying what would change the answer. Worked through in §7.6.

---

## 3. Evidence sources allowed per artifact type

This closes the gap between "counts come from transcripts" and "a fresh repo has no transcripts".

| Artifact | Min. tier (§0.2) | Behavioural evidence (counts) required? | Discovery-only evidence allowed? |
|---|---|---|---|
| Skill | **1**, or **2** from a `blueprint.md` catalogue row | Yes for rows 1 and 3. **No** for rows 15, 16 and 17 — a catalogue skill is licensed by the structural fact | **Yes**, for rows 15, 16 and 17 only, under the four conditions below |
| Subagent | **1**, or **2** from `blueprint.md` §3 | Yes for row 3. **No** for a §3 catalogue subagent | **Yes**, for a `blueprint.md` §3 row only, under the same four conditions |
| Rule from a correction (any scope) | **1** | **Yes** — row 5 threshold | No |
| Rule — command policy ("never run X here") | **1**, and only from a tier-1 record that **names the command**: `correction`, `pain_signal`, `commands_requested` | **Yes** — row 5's `count >= 2`, **and** the record must quote the command token the policy will match | **No, at any strength** — see below |
| Path-scoped rule from a co-change cluster | **2** | row 6 git thresholds (`support`, `confidence`, `still_exists`) **and** the §1.2 scope test. A `directory_hotspot` corroborates such a rule and can never carry one — §1.3 | **Yes**, git-derived form — this is the row that carries a no-history run |
| Reference doc | **1** | **Yes** — row 9 | No |
| Hook | **1**, or **2** when it wraps an existing command | Yes, **or** it wraps a command that already exists in `discovery.commands` and CI does not run | **Yes**, with the path form of the evidence string |
| MCP draft | **1** | **Yes** — all four gates in §1.1. `confidence == "high"` alone is not enough, and a `tool_mention` count is not evidence at all | No |
| Permissions | **2** | No | **Yes** (row 14) |
| Index doc | **2** | No | **Yes** |

**The four conditions on a discovery-only skill or subagent.** This is the row that changed, and it
changed because the old `No` was measured producing **zero skills** on a 268k-line repo with eight
external services and 384 recorded prompts. A structural skill is allowed when all four hold, and is
deleted when any one fails:

1. **It matches a named row** in `blueprint.md` §1.3, §3, §6.1 or §6.2, and the field that row reads
   is non-empty in `discovery.json`. Not "the repo uses X so a skill about X would be nice" — the row.
2. **It passes all five personalization tests** (`blueprint.md` §1.1). In particular test 4: name the
   repo you would have to paste it into for it to become false. A skill you cannot answer that for is
   a template, which is the one thing this tool does not produce.
3. **Its steps are readable off this repo** — real directories, the real command from a `commands`
   slot, the real module that talks to the service. A step you had to invent from the vendor's
   documentation is a step that does not go in. A vendored skill already in the repo may be
   *linked* from a step as the vendor's API reference; it may not supply the step.
4. **It recurs** (`blueprint.md` §1.4). The plan can name `>= 3` existing instances of what the
   skill produces, a `request_shapes[]` count `>= 3`, a service the repo extends over time through
   a module, or a guide the developer wrote. One instance is a feature, and a feature gets no
   skill. For a subagent: it is a §3 catalogue row, or a `request_shapes[]` count `>= 3` backs it,
   and it earns its context window with a tool restriction, a reviewer stance or a many-file pass.

`setup-manager` (row 16) is licensed by the setup itself and is exempt from condition 1 only.

Everything not in this table is unchanged: a rule from a correction still needs the correction, an
MCP draft still needs all four §1.1 gates, and a command policy is still tier 1 only.

The MCP row is the one that changed, and it changed for a reason worth remembering: a draft config
for a service the user never asked to work with is a template with a JSON file attached. Having a
dependency is not a request. See §7.5.

**The command-policy row is the strictest in the table, and deliberately.** It is the only artifact
agentify builds whose normal operation is to **refuse** something. Everything else adds: a prose rule
adds a sentence the model may follow, a hook usually warns, a skill offers steps. A command policy —
`decision = "forbidden"` in `.codex/rules/agentify.rules` on Codex, a blocking `PreToolUse` hook on
`Bash` on Claude Code (§3.1) — takes a command *away*, in every session, until the user finds it and
deletes it. Three consequences, and they are the whole row:

1. **Tier 1 only, and no discovery-only form at any strength.** A structural fact says the repo
   *uses* something; it never says the agent *keeps reaching for the other thing*. A `bun.lockb` with
   no `package-lock.json` proves this repo installs with bun. It does not prove anyone ever ran `npm`
   here, and a policy built on it forbids a command no record shows being run — A4 with a Starlark
   file attached. The tier-2 licence §3 gives the **Hook** row does not reach this row: that licence
   is for a hook that *wraps a command the repo already has*, which is additive. Forbidding is not.
2. **The evidence must quote the token, not the topic.** `prefix_rule(pattern = ["npm"])` matches a
   literal command prefix, so the evidence string has to contain the literal the pattern will carry.
   `correction: "use bun, not npm" (4x, …)` writes `pattern = ["npm"]`. `correction: "stop using the
   wrong package manager" (4x, …)` writes nothing: the count is real and the artifact is unwritable,
   so that candidate is a prose rule or an index-doc line instead. This is §0.3's mechanism test with
   the blank being a command token — if the record cannot fill it, there is no policy.
3. **It spends a hooks slot, not a rules slot, on both targets** (§3.1).

**Command policy vs prose rule — the same question §2.2 asks about hooks.** A command policy is
**enforced by the harness**; a prose rule is **remembered by the model**. Choose on that difference
and on nothing else:

| The finding is | Pick |
|---|---|
| "this exact command must not run here", and the record names the command | **Command policy** — it fires before the command runs and cannot be argued out of |
| a convention the model must *apply while writing* — a layering rule, a naming scheme, a library choice | **Prose rule** — there is no command to match, so a policy has nothing to gate |
| both readings fit, because the correction names a command *and* a convention | **Split the finding**: the policy takes the command, the prose rule takes the convention. Never write the same sentence in both — A5 |

§2.2's ordering carries over intact: **if it can be enforced, prefer the enforced form**, and a prose
rule that only restates a command policy is noise. What does *not* carry over is §2.2's "add the rule
only if the hook fires too late to be useful" — a command policy never fires too late, because it
fires before the command.

**Prefix matching is not semantics, and the plan must say so.** `pattern = ["npm"]` does not catch
`npx`, `pnpm`, or `npm` reached through a package script (`adapters/codex.md` §4.2.2). Write the
mechanism sentence against what the policy actually matches; otherwise A12 catches it, because a
policy that misses the way the evidence shows the command being run is the wrong artifact rather
than a weaker one.

### 3.1 Which template emits which artifact

Every artifact type above maps to a named template **per target**. There is no other emitter, and a
candidate whose type is not in this table cannot be built.

Read the columns for the target being built. **A template column and a path column are one cell in
two halves: neither is optional.** A row whose template does not exist, or whose path the adapter
does not confirm, is a proposable artifact with no emitter — phase 4 offers it, the user approves
it, and phase 7 arrives with nothing to write. That defect has been found here twice (reference
docs, then every Codex row routing to a Claude-Code-only template), which is why the table now
names the template separately for each target instead of assuming one file serves both.

| Artifact | Template — Claude Code | Written to (Claude Code) | Template — Codex | Written to (Codex) |
|---|---|---|---|---|
| Skill | `skill.md.tmpl` | `.claude/skills/<name>/SKILL.md` | `skill.md.tmpl` — same file, same body | `.agents/skills/<name>/SKILL.md` — **not** `.codex/skills/`. The reason is *documentation, not mechanics*: `.codex/skills/` **does** load, with `scope: "repo"` (measured, codex-cli 0.152.1), but it is undocumented and unused in the wild, while `.agents/skills` is the documented cross-tool path a Claude Code install can share. Earlier wording here said `.codex/skills/` "is not a load path"; that was wrong and is retracted. The build behaviour is unchanged — still write only `.agents/skills` |
| Subagent | `subagent.md.tmpl` | `.claude/agents/<name>.md` | `codex-agent.toml.tmpl` — TOML, not markdown-with-frontmatter | `.codex/agents/<name>.toml` |
| Rule — prose convention | `rule.md.tmpl` | `.claude/rules/<name>.md` **plus** its row in the index-doc section | `rule.md.tmpl` — same file, same body | `<plan-dir>/rules/<name>.md` **plus** an `AGENTS.md` pointer; a rule of ≤ ~15 lines is inlined in the `AGENTS.md` section instead, with no file |
| Rule — command policy ("never run X") | `hook.sh.tmpl` + `settings-hooks.json.tmpl` — a `PreToolUse` hook on `Bash`; there is no policy file on this target | `.claude/hooks/<name>.sh` + a merge into `.claude/settings.json` | `codex-rules.rules.tmpl` — native Starlark policy, preferred over a hook | `.codex/rules/agentify.rules`, one agentify-owned file for the whole run. **Validate with `codex execpolicy check` before writing; a malformed file bricks Codex in that repo.** No Codex binary ⇒ draft to `<plan-dir>/` |
| Hook | `hook.sh.tmpl` + `settings-hooks.json.tmpl` | `.claude/hooks/<name>.sh` + a merge into `.claude/settings.json` | `codex-hook.sh.tmpl` + `codex-hooks.json.tmpl` | `.codex/hooks/<name>.sh` + a merge into `.codex/hooks.json` |
| Index doc | `index-doc-section.md.tmpl` | a delimited block appended to `CLAUDE.md` | `index-doc-section.md.tmpl` — same file, same body | a delimited block appended to `AGENTS.md` (or to `AGENTS.override.md` where one exists, since it outranks) |
| MCP draft | `mcp.json.tmpl` | `.mcp.json` | `codex-mcp.toml.tmpl` — TOML in `config.toml`, not a JSON file | `<plan-dir>/codex-mcp.toml`, applied by the user; writing into `<repo>/.codex/config.toml` is an interview opt-in under the §4.6 append contract |
| Permissions | `settings-permissions.json.tmpl` | a merge into `.claude/settings.json` (`permissions.allow` / `.deny`) | `codex-rules.rules.tmpl` — the Starlark policy **is** this target's permission surface | `.codex/rules/agentify.rules`, the same file the command-policy row writes |
| Reference doc | **none — see below** | `.claude/skills/<owning-skill>/references/<name>.md`, or `docs/agentic-setup/reference/<name>.md` when no skill owns it | **none — see below** | same, under `.agents/skills/<owning-skill>/references/` |

**Every artifact type has a home on both targets** (verified 2026-09-05, codex-cli 0.152.1). The
Codex column is here so nothing in phase 4 is cut for want of a path; the adapter, not this table,
is authoritative on the exact bytes, and `adapters/capabilities.md` carries the caveats — chiefly
that repo-scoped Codex artifacts are inert until the project is trusted.

**Nothing on Codex is a substitution any more.** Hooks, skills, subagents, command-policy rules and
the plugin manifest are all native there. Any wording that still says Codex has no hooks — and that
the substitution is an `AGENTS.md` instruction block plus a native git hook — is stale and wrong:
Codex has twelve hook events, a regex matcher and a JSON `permissionDecision` protocol. Do not
downgrade a candidate, and do not spend a plan line apologising for a loss that does not exist. The
one honest loss on this target is the **per-agent `tools` allowlist** on subagents (§4.5); say that,
and only that.

That loss is about which **tools** the agent may call, and it is not the same question as whether a
**remote** service is read-only. Neither a `tools` allowlist nor Codex's `sandbox_mode` reaches the
far end of a connection string, so a candidate that promises read-only access to a hosted database
or API carries the service-side obligation in `blueprint.md` §3.1 on **both** targets — it is not a
Codex downgrade, and it must not be written up as one.

**The two rule rows are different artifacts, not two spellings of one.** A finding of the form "the
agent keeps running `npm` here and gets corrected" is a *command policy*: on Codex it is a
`prefix_rule` that refuses before the command runs, on Claude Code a `PreToolUse` hook. A finding of
the form "handlers in this repo return `Result`, they do not throw" is a *prose convention* and is
the `rule.md.tmpl` row on both targets. Neither is a new artifact type, and §3's evidence table
above governs both — including the command-policy row added there for exactly this reason.

**They are not, however, the same artifact type.** A prose rule is a **rule**; a command policy is
a **hook**, on *both* targets, and the plan lists it under hooks. Read that off the Claude Code
column of this very table: there a command policy **is** a `PreToolUse` hook, written by
`hook.sh.tmpl` into `.claude/hooks/` and merged into `.claude/settings.json`. Typing it as a rule on
Codex and a hook on Claude Code would make one repo's evidence produce a differently-shaped plan on
each agent. The two differ in what they cost the user, which is why the split matters: a prose rule
is **context rent**, carried in every session, and a command policy costs none because the harness
holds it; a hook is **interference with the user's work**, and a command policy is precisely that.
Say which it is in the plan entry, and phase 5's `hook_strictness` answer sets its `decision`.
§2.2 states the same rule in one clause.

**Two artifacts in this table are written by a template but not to the repo.** `settings-hooks.json.tmpl`
and `codex-hooks.json.tmpl` are merge *fragments*: they are never written as files, and their target
file — `.claude/settings.json`, `.codex/hooks.json` — carries no agentify metadata at all, because
JSON has no comments and Codex's hooks file rejects unknown top-level keys outright (measured: an
`_agentify` key there loaded **zero** hooks, with no error the user ever sees). For both, the
artifact's identity is **the hook command path**, and the undo is the JSON un-merge script in
`references/report-template.md` §3.1, never the marker-removal script.

**Git hooks are not in this table.** They are a secondary, opt-in artifact owned by
`adapters/codex.md` §4.3, asked as their own interview question with the default set to no, and
they have no template — the adapter carries the body, the required `AGENTIFY_DRYRUN` escape hatch
and the `core.hooksPath` rule. They are the only gate that survives outside an agent session; they
are not, and never were, a stand-in for a hook system Codex lacks.

**Reference docs have no template on purpose.** Their body is repo-specific prose, so a template
would only produce filler. Write plain markdown with an H1 title and the answer to the question the
`request_shapes[]` cluster keeps asking, and carry the same five metadata lines every other
generated file carries, in a `<!-- -->` comment header at the top:

```
<!--
agentify-id: <kebab-name>
agentify-version: 1
agentify-generated: <yyyy-mm-dd>
agentify-evidence: <the row 9 evidence string>
Safe to delete or edit.
-->
```

No attribution in the body — a reference doc is a generated artifact, and the three placements are
fixed. `verify_artifacts.py` checks it as type `reference`.

**Build order.** A reference doc is written in the *skills* step, immediately after the skill that
links it (or on its own if none does), so the seven-step order — rules → hooks → permissions →
skills → subagents → MCP drafts → **index doc last** — still holds. The index doc is last because
its tables enumerate what was actually written (`blueprint.md` §9). Link every reference doc from
its owning skill or from the index-doc section; an unlinked one never gets read.

The rows added for Codex slot into that same order and add no step: `.codex/rules/agentify.rules`
is written in the *rules* step (validated before it lands, so the whole file is written once, after
every approved command-policy rule is known), `.codex/hooks/*.sh` plus the `.codex/hooks.json`
merge in the *hooks* step, `.codex/agents/*.toml` in the *subagents* step, `<plan-dir>/codex-mcp.toml`
in the *MCP drafts* step, and the `AGENTS.md` section last. Codex has no separate permissions file:
its permissions step writes the same `.codex/rules/agentify.rules` the command-policy rows write, so
on that target the rules step and the permissions step produce one validated file, written once,
after every approved policy is known. Checkpoint after each type, as on the other target.

---

## 4. Anti-patterns — do not generate these

- **A1. A skill for something the repo already does in one command.** If `package.json` has
  `"test": "bun test"`, do not build a "run the tests" skill. Name the command in the index doc.
- **A2. A rule that restates a lint rule CI already enforces.** Cross-check every candidate rule
  against `discovery.ci[].runs`, the lint/format config, and `discovery.commands.lint`. If the
  linter fails the build on it, the rule is dead weight — the model gets the feedback from the tool.
- **A3. A subagent where a skill would do.** See §2.1. Isolated context, persona, or parallelism, or
  it is a skill.
- **A4. Any artifact whose evidence count is zero.** Including the polished, obviously-useful one.
- **A5. A rule and a hook for the same check.** Pick one, per §2.2.
- **A6. An MCP draft justified by dependencies and mentions.** A lockfile-only or transitive package
  fails §1.1 gate 1. `confidence: "high"` plus a large `tool_mentions` count still fails gate 2 —
  mentions are tier 3. It needs tier-1 work evidence, or §1.1 gate 2's structural alternative — a
  skill or subagent this run built for that same service.
- **A7. A skill that wraps a single existing slash command** already present in
  `existing_agentic_config` or in `slash_commands[]`.
- **A8. Restating framework or language documentation** in a rule or reference doc. Repo-specific
  facts only. "Next.js route handlers live in app/api" is documentation; "our route handlers must
  call `withAuth` from `src/lib/auth.ts`" is a rule. **A8 is about the vendor's docs, not the
  repo's own.** Quoting the repo's `CLAUDE.md`, `DESIGN.md` or a guide into a rule scoped to the
  paths it governs is `blueprint.md` §1.1 passing, and "it restates the index doc" is A17.
- **A9. Duplicating an existing artifact of the same type, inside this repo, that does the same
  job** — one listed in `discovery.existing_agentic_config.skills` / `.agents` / `.rules` / `.hooks`
  under `provenance.own`, and tested against this repo rather than trusted (`blueprint.md` §2.1).
  On a repo that already has a setup this is the main failure mode — add and fix, never write a
  parallel copy. It is unconditional: there is no mode that turns de-duplication on
  (`coverage.md` §6). **What A9 does not reach:** a **vendored** artifact (a generic guide — it
  becomes the generated skill's reference), a **user-scope** entry (`~/.claude/skills`,
  `${CODEX_HOME}/skills`, a user-scope plugin or MCP server — not in the repo, so a teammate never
  gets it; a same-name collision is a report line, never a skip), the **index doc** (prose covers
  only an index-doc line), and a **document** (a guide licenses a skill, §2.4). The 2026-09-07
  measurement: the old wording dropped three analytics skills, a db skill, a QA skill, an MCP draft
  and a guide-shaped skill on one repo, every one against something outside §2.1's definition.
  `.artifacts_by_target` still says which agent loads each existing artifact, and
  `.user_scope.skills_shared_with_claude_code` still names the ones that are a single file in both
  trees: never write a second copy of one of those into the other tree.
- **A10. Splitting one finding into three artifacts to look productive.** Merge overlapping
  candidates *before* they are ranked (`coverage.md` §2 step 1), not after.
- **A11. An artifact justified by a mention count.** `tool_mentions` and `file_hotspots` are tier 3
  (§0.2). The test is mechanical: strike the tier-3 line out of the candidate's evidence. If what is
  left clears no threshold, the candidate has nothing. A big number is not a small number's
  argument.
- **A12. An artifact that cannot catch the failure it cites.** If the attached pain signal is a
  React Native provider-nesting error, an MCP server for the payment API does not address it — a
  path-scoped rule does. Re-read the mechanism sentence (§0.3) and check that it acts on the
  recorded failure rather than on the same *topic*.
- **A13. Building over a working local loop.** A script, dev command, or CLI already in the repo
  that does **the agent's** job means the candidate is `### Skipped (already covered)`, naming it.
  This is A1 generalised past `package.json` scripts, and it is the one that catches MCP drafts
  (§1.1 gate 3). Only a correction or pain signal *about that loop* reopens the question. **Two
  things are not a loop:** a **human GUI** (`db:studio`, a hosted dashboard — the developer's
  window, not the agent's path to the data) and a **document** (a written procedure is row 17's
  evidence, §2.4). Measured 2026-09-07: both were taken as loops, and a `query-db` skill, a Neon
  MCP draft and a guide-shaped skill went unbuilt.
- **A14. Two counts drawn from one set of turns.** Six turns presented as twelve units of evidence,
  because one pasted instruction template fed both a `request_shapes[]` row and a `corrections[]`
  row. Both counts are real; their sum is not. §6.2.
- **A15. A path-scoped rule built out of release automation.** The highest-support, highest-
  confidence co-change cluster in a monorepo is frequently a bot bumping a version field across
  every package — measured at support 134 / confidence 1.00 on turborepo, four such clusters at the
  top of the run. `mine_git.py` excludes bot-authored commits by default, so on a normal run this
  cannot reach you; it can on a run made with `--include-bots`, and a human sweep (a formatter pass,
  a mass rename) produces the same shape with no bot involved. §1.2 gate 4. The tell is that no
  sentence of the form "when you change A, also change B" is true of it — nobody *changes* a version
  bump, a machine emits one.
- **A16. Flattening every structural candidate to one score.** On a run with no transcripts every
  candidate is structural, and writing `F = 1` on all of them hands the plan an unordered pool, so
  the user reads twenty artifacts in no meaningful order. Read the band off §6.3 and cite the row.
- **A18. A skill for a feature.** "Add the resize tool" happened once; a skill for it is a
  template with a repo noun in it, and a subagent for one directory is a skill with a persona.
  The size test (`blueprint.md` §1.4) is the gate: the shortlist row ends with the count of the
  thing the artifact produces, and a row that cannot is dropped to `Skipped (insufficient
  evidence)` with the count it had. Personalized means *this developer's workflows*, not every
  corner of their tree.
- **A17. The rationalized cut.** A plan sentence arguing that fewer artifacts is the right outcome
  for this repo — "knowledge is not the gap, enforcement is", "I skipped every rule that would only
  restate `CLAUDE.md`", "you already have 61 skills" — is not a finding; it is the run explaining
  why it stopped walking the catalogue. The tell is that the sentence is about the *setup*, not
  about a field and a number. Delete it and re-walk the rows it excused (`blueprint.md` §10, check
  9). The user cuts at the phase 6 gate, by number; the run never pre-cuts for them.

---

## 5. Evidence string format — every candidate carries one

Canonical form (use this whenever the record has a count, a session count, and dates):

```
<signal type>: <what> (<count>x across <n> sessions, <date range>)
```

Example:

```
request_shape: "add <resource> endpoint with validation + tests" (7x across 4 sessions, 2026-06-02 to 2026-08-28)
```

`<signal type>` is the `signals.json` / `discovery.json` key the evidence came from, verbatim:
`request_shape`, `correction`, `commands_requested`, `slash_command`, `pain_signal`, `tool_mention`,
`file_hotspot`, `cochange_cluster`, `commit_conventions`, `branch_naming`, `hotspot`,
`directory_hotspot`, `test_discipline`, `external_service`, `package_script`, `ci`, `env_var_name`.
Each of these seventeen tokens has exactly one tier in §0.2 — that is the list they are drawn from.

Three degraded forms, used only when the record genuinely lacks the fields:

1. **Count but no per-record session/date fields** (`corrections[]`, `commands_requested[]`,
   `slash_commands[]`, `pain_signals[]`, `tool_mentions[]`) — fall back to the mined window from
   `sessions.first` / `sessions.last`:
   ```
   correction: "use bun, not npm" (4x, mined window 2026-05-19 to 2026-08-30)
   ```
2. **Git-derived** (`cochange_clusters[]`, `hotspots[]`, `commit_conventions`) — use support /
   confidence / percentage and the window the miner actually chose
   (`signals.git.window.days` and `.mode`), not the 180-day default. Every count is over
   human-authored commits (§0.2), so a convention percentage names its human denominator:
   ```
   cochange_cluster: src/api/*.ts + src/api/*.test.ts (support 11 commits, confidence 0.73, 180d window)
   cochange_cluster: src/**/*.ts <-> test/**/*.test.ts mirror (support 10 commits, confidence 1.00, 365d window, last seen 2026-08-30)
   cochange_cluster: crates/turborepo-schema-gen/** -> packages/turbo-types/** (support 6 commits, confidence 0.86, all-history window)
   commit_conventions: 77% conventional over 2,954 human commits (46 bot commits excluded)
   ```
   A row 6 evidence string names **both scopes**, because that is what makes it checkable against
   the rule the plan is about to write. When §1.2 gate 1 collapsed several paths into one scope, the
   string names the collapsed glob **and** the evidenced members, so the count and the glob can still
   be checked against each other:
   ```
   correction: "translate the page in every locale, not just English" (4x, mined window 2026-07-02 to 2026-08-29) — scope docs/*/** over docs/pages, docs/es, docs/fr, docs/zh (4 sibling locales, 1 scope)
   ```
3. **Discovery-only**, allowed only for the rows in §3 — cite the path, never a count:
   ```
   package_script: package.json#scripts.typecheck = "tsc --noEmit" (no CI job runs it)
   ```

Rules for the string:

- Quote the *scrubbed* skeleton or example text from `signals.json`. Never re-quote raw transcript
  text; the miner already scrubbed it and you do not have the raw text.
- **The `<signal type>` token decides the tier** (§0.2), so the primary `Evidence:` line of a
  candidate can never open with `tool_mention:` or `file_hotspot:`. Those belong on a `Supporting:`
  line, under a primary line that already clears a threshold on its own.
- **A `Supporting:` line that could be drawn from the same turns as the primary must say so** —
  append `— same turns; not added` (§6.2). Two strings stacked on one candidate must never read as
  two independent counts.
- Keep it to one line, under ~160 characters.
- The same string goes into three places: the candidate list (phase 4), the plan entry (phase 6),
  and the generated file's `agentify-evidence:` frontmatter line (phase 7). They must match.

---

## 6. Scoring rubric

Score each candidate on four axes, then rank. Ranking sets build and presentation order —
`coverage.md` §2 — and **nothing is cut for being ranked low**; there is no cap.
Nothing is scored until it has passed the mechanism test (§0.3) — scoring a candidate you could not
write a mechanism for is how a wrong artifact acquires a number that makes it look right.

**F — Frequency of demand (0–4).** How many times the user asked, and whether it is still live.
**Count tier-1 occurrences only** (§0.2). Never add a tier-3 count into this table, never average
across tiers, never sum counts from records that are not the same need — and never sum two records
that may be counting the same turns (§6.2).

| F | Condition (tier-1 occurrences) |
|---|---|
| 0 | below the row's threshold, or the only evidence is tier 3, or the git row it rests on has `still_exists: false` — not a candidate |
| **0.25 – 1** | **structural:** no tier-1 evidence at all and the type is tier-2-eligible per §3. Mark it `structural`, not `low-confidence`, and read the exact band off **§6.3** — do not write `1` by reflex. Capped at 1; it can never reach the bands below |
| 1 | **thin tier-1:** 2–3 occurrences, or `last_seen` older than 90 days → `low-confidence` (§6.1) |
| 2 | 4–6 across `>= 2` sessions |
| 3 | 7–12, or `sessions >= 4` |
| 4 | `> 12`, or seen in `>= 3` sessions within the last 30 days |

**C — Cost per occurrence (0–3).** What one occurrence costs the human today.

| C | Condition |
|---|---|
| 0 | trivial, a one-line answer |
| 1 | under ~2 minutes, single file |
| 2 | ~5–20 minutes, multi-file or multi-step |
| 3 | over ~20 minutes, or it has a `pain_signals[]` record attached (the user got it wrong and had to redo it) |

**D — Determinism fit (0–2).** How well the candidate's nature matches the artifact chosen.

| D | Condition |
|---|---|
| 2 | fully mechanical **and** mapped to a hook; or fully procedural **and** mapped to a skill; or pure judgment **and** mapped to a subagent |
| 1 | mostly matched, with judgment at the edges |
| 0 | mismatched — go back to §2 before scoring further |

**B — Blast radius (0–3).** How much breaks, or how many people are affected, when it goes wrong.

| B | Condition |
|---|---|
| 0 | one file |
| 1 | one folder |
| 2 | a zone spanning folders (`api`, `db`, `migrations`), or **3 or more non-bot rows** in `signals.git.contributors[]` — count `is_bot == false`, and **never** `discovery.git.contributors`, which is `shortlog --all` and counts machines on unmerged refs (row 12, `interview.md` §4.2) |
| 3 | repo-wide, or touches correctness, data, auth, money, or secrets |

**Score = (F × 2) + C + D + B**, range 0–16.

A structural `F` puts quarters into the score: `Fs0.75` contributes `1.5`, so the candidate reads
`9.5`, and the score line carries the band — `(Fs0.75 C2 D2 B2)`, never a bare `F1`. **Do not round
a structural score.** Rounding is the collapsed ranking walking back in through the arithmetic, and
the presentation order turns on exactly these decimals.

The doubling is deliberate, and it is only defensible under one condition: **`F` counts demand, and
demand is the single axis that is measured rather than judged.** C, D and B are all your estimates
about a repo you met an hour ago; F is a number someone else produced by counting what the user
actually typed. Doubling the measured axis is right. Doubling a *keyword frequency* is not — it hands
the run to the noisiest word in the transcript, which is precisely the failure dissected in §7.5. If
you ever find yourself sourcing `F` from anything but tier 1, the formula is not the thing that is
broken.

Ranking and ties:

1. Rank **within each artifact type pool**, because the plan is grouped by type. Also print a global
   ranking so the user sees the shape of the whole set.
2. Ties break on, in order: **tier-2 corroboration** (demand backed by a structural fact in the repo
   beats demand standing alone), then more recent `last_seen`, then lower build cost, then artifact
   type order hook > rule > skill > subagent > reference doc > MCP draft.
3. A low rank is **not** a reason to drop a candidate. Every candidate that cleared its threshold is
   proposed; the user drops what they do not want, at the phase 6 gate. See `coverage.md` §2.
4. Anything scoring `F = 0` never enters a pool at all; if it is worth mentioning, it belongs under
   "Skipped (insufficient evidence)" or, when a script or command already does the job, "Skipped
   (already covered)". `coverage.md` §8 has the three headings, and there is no fourth.
5. Never re-score to reorder a candidate, and **never re-tier a signal to raise `F`.** Re-tiering is
   editing the score with extra steps.

### 6.1 Threshold edges, low confidence, and mixed artifacts

**1. `F = 1` on thin or stale demand ⇒ `low-confidence`.** Two or three occurrences is the
difference between a habit and a coincidence, and you cannot tell which from a count that small. Per
PRD §7.4, low-confidence candidates are **listed and not built** unless the user opts in — that is
interview Q13. Do not quietly promote one because the pool has room; an unused slot is a fine
outcome. They go under their own heading, same table shape as the other skipped lists:

```
### Skipped (low confidence — opt in to build)

| Candidate | Type | Score | Evidence | Why not built |
|---|---|---|---|---|
| ask-before-commit-line | index-doc line | 7 (F1 C1 D2 B2) | correction: "do not commit or push without asking" (3x, mined window 2026-07-26 to 2026-09-04) | count 3 across 81 sessions, and the two visible examples are different phrasings — say the word and I will include it |
```

A **structural** `F` is different and is *not* low-confidence: a script that exists, a convention
77% of commits follow, a CI job that does not run a check — these are either true or false, and they
are true. Mark them `structural`. What tier-2-only evidence cannot do is outrank measured demand,
which is exactly what the ceiling of 1 enforces: a well-founded guess sits at the bottom of its pool
and is built if the pool has room — it never displaces something the user asked for repeatedly.

**Take the value from §6.3, not from reflex.** Writing `F = 1` on every structural candidate is
defensible on a repo where they are the minority, and indefensible on a run with no transcripts,
where *every* candidate is structural and the pool then sits at one value on the axis the formula
doubles. That is the run that most needs an order — twenty structural candidates presented
alphabetically is a plan nobody can read — and a rubric that cannot order its own pool produces one.

**2. Cluster-integrity check at the edge.** Before trusting a count of 2 or 3, read the record's
`examples[]` — the miner keeps at most two per cluster, each ≤160 chars. Are they the same need in
different words, or different needs the clusterer merged on a shared verb? If the two examples would
produce **different artifact text**, the cluster is over-merged: recount using only the examples that
agree, and if that drops below the row threshold, move the candidate to
`### Skipped (insufficient evidence)` showing the count found against the threshold missed. If the
two visible examples do agree, you have verified what you can see and nothing beyond it — keep the
candidate, keep the `low-confidence` mark, and say in the plan that the count could not be verified
past the examples shown. Never claim more certainty than two strings can carry.

**3. Confidence attaches to a claim, not to a file.** An index-doc section or a rule file routinely
carries lines from several findings of very different strength. Score and mark **each line
separately**. A low-confidence line is left out of the built file unless the user opts in; the rest
of the section is written normally. Never let a strong finding smuggle a weak one into the repo
because they share a file, and never lose a strong section because one of its lines is thin. The
index doc itself (row 11) is unconditional — this rule governs its *contents*, not its existence.
Worked in §7.7.

---

### 6.2 Overlap — a count only adds to another count if they count different turns

`F` counts **occurrences of a need**, and an occurrence is one thing the user typed. Two records can
be built from the *same* turns: the miner runs several detectors over every turn, and each detector
keeps its own tally. Adding those tallies manufactures demand nobody expressed. This is the
arithmetic form of A10, and it is harder to see — both numbers are real, both records can be tier 1,
and nothing in the JSON says they overlap.

**The rule.** Counts may be summed only across signals derived from **disjoint turns**. When two
records plausibly draw on the same turns, **cite the larger, carry the smaller on a `Supporting:`
line, and do not add**. When you cannot tell, they overlap — the default is not to add. On a tie,
cite the record that carries `sessions` and `first_seen` / `last_seen`, because it is the one whose
count can be checked.

Classify the pair before you sum it:

| Verdict | What you can point to | What you do |
|---|---|---|
| **Disjoint** | date ranges that do not meet; or two different acts where neither record's trigger appears anywhere in the other's `examples[]` | sum the counts |
| **Overlapping** | one record's `text` is the head, tail, or a restatement of the other's `skeleton`; or one record's `examples[]` name the other's command, path, or phrasing; or the two counts and windows match suspiciously well | cite the larger; `Supporting:` the smaller with `— same turns; not added` |
| **Unknowable** | the record type carries no `examples[]` to compare at all — `commands_requested[]`, `slash_commands[]`, `tool_mentions[]` | treat as overlapping |

Only `request_shapes[]` carries per-record `sessions` and dates. For every other transcript record
you are comparing two integers and at most four example strings, which is exactly why the default
runs the safe way.

The rule is about **turns**, not about sources. A git-derived count and a transcript count never
share turns — they are not made of turns — but they are also different tiers, so §0.2 governs that
pair and this section has nothing to say about it.

**Worked — the same six turns, counted twice.** Real run, 2026-09-04, a 57-session history. Two
tier-1 records, top of their respective lists:

```json
"request_shapes": [
  {"skeleton": "read fully especially numbered decisions build", "count": 6, "sessions": 6,
   "first_seen": "2026-08-09", "last_seen": "2026-08-10",
   "examples": ["Read docs/plans/second-phase.md fully, especially the numbered decisions and the build order. Implement slice 8 exactly as the build order row says, honoring e…"]}
],
"corrections": [
  {"text": "Do not start the next slice.", "kind": "tooling", "count": 6, "examples": []}
]
```

`6 + 6` reads as twelve units of evidence. It is **six turns**. The user pastes one instruction
template every time, and *"Do not start the next slice."* is the closing line of that template — not
something they said in addition to the request, but part of it. The tell is available without the
raw transcript: identical counts, the same two-day window on both, and a correction that reads as a
clause rather than as an interruption.

What the double-count costs, in order of how much it matters:

1. **Two candidates where there is one finding.** Scored on its own, the correction becomes a row-5
   rule candidate at `F2` and outranks corrections drawn from *different* turns — so a restatement
   is presented above a real finding. Handled correctly this is one
   finding that may still produce two artifacts (the skill, and the constraint written into it),
   both carrying the **same** evidence string — §1, first note.
2. **`F` goes wrong without leaving a mark.** Here the inflation happens not to move the band: 6
   across 6 sessions is already `F3` (`sessions >= 4`), and 12 is `F3` too. That is precisely why
   the rule has to be written down rather than left to arithmetic — nothing in the score shows the
   error. Had the shape been seen in two sessions instead of six, 6 would be `F2` and 12 would be
   `F3`, and the doubling would have handed the candidate two points nobody asked for.

Correct handling — `F` from the request shape alone, the correction carried but not added:

```
Evidence: request_shape: "read fully especially numbered decisions build" (6x across 6 sessions, 2026-08-09 to 2026-08-10)
Supporting: correction: "Do not start the next slice." (6x, mined window 2026-08-02 to 2026-08-29) — closing line of the same template; same turns, not added
```

Six turns cannot fund two independent artifacts. They can fund one artifact with a constraint
written into it — which is what §2.6 step 2 already says about constraints, arriving from the other
direction.

---

### 6.3 Structural `F` — the scale a run with no demand evidence is ranked on

`F` is doubled because it is measured rather than judged. Tier-2 evidence is **also** measured — it
just measures the *repo* instead of the *demand*, which is why it is capped below tier 1 and not why
it should be flattened. Flattening it is what broke: on a repo with no transcripts every candidate
took `F = 1` from the structural clause, every score reduced to `2 + C + D + B`, and the pool tied on
the one axis worth double. Ranking collapsed exactly where the plan needed it most.

So structural `F` is computed, in quarters, from counts the miners already emit. Find the row that
describes your candidate's primary evidence and read the band.

| # | Signal | Read from | `1.00` | `0.75` | `0.50` | `0.25` |
|---|---|---|---|---|---|---|
| 1 | **Co-change support** | `signals.git.cochange_clusters[]` | support `>= 10` and confidence `>= 0.7` | support `>= 6` and confidence `>= 0.6` | support `>= 4` and confidence `>= 0.5` | support `3` and confidence `>= 0.5` |
| 2 | **Git frequency** | `signals.git.hotspots[].commits` or `directory_hotspots[].commits`, as a share of `signals.git.authorship.commits_human` | `>= 25%` | `10–25%` | `5–10%` | `< 5%`, and at least 3 commits |
| 3 | **Convention share** | `signals.git.commit_conventions.conventional_pct` / `.ticket_prefix_pct`, `test_discipline.commits_touching_tests_pct`, or a `branch_naming[]` pattern count | `>= 0.90` over `>= 200` human commits (branch pattern `count >= 20`) | `>= 0.75` over `>= 50` (branch `count >= 10`) | `>= 0.60` over `>= 50` (branch `count >= 5`) | `>= 0.60` over `< 50` human commits — and the evidence string says the sample is small |
| 4 | **Command / CI gap** | `discovery.commands`, `discovery.ci[].runs`, `discovery.raw_scripts` | the command exists, no CI job runs it, and `>= 2` other scripts or CI steps depend on it | exists, no CI job runs it, and it is a correctness gate (test / typecheck / lint / migrate) | exists and no CI job runs it | exists, and CI runs it only on a schedule or on one branch |
| 5 | **Breadth** | `discovery.monorepo.workspaces`, `discovery.folders[].zone`, files under the scope | `>= 5` workspaces, or repo-wide | `2–4` workspaces, or a zone spanning `>= 3` folders | one zone or one workspace | one file |

**Row 4 has one more band the table cannot show — zero.** When CI already runs the command on every
push and PR, the candidate is not weak, it is **dead**: anti-pattern A2. Score nothing, and put it
under `### Skipped (already covered)` naming the CI job that covers it.

Combining the rows:

1. **`F` is the highest band any applicable row reaches. Never sum, never average.** Summing
   structural rows is the same mistake as summing overlapping tier-1 counts (§6.2), and it is easier
   to make here, because rows 1, 2 and 5 can all be restating one fact about one directory.
2. **Breadth alone caps at `0.50`.** Row 5 is also the input to `B` (blast radius). Letting it set a
   top `F` *and* a top `B` counts one property twice. Use row 5 only when no other row applies.
3. **Recency and liveness apply afterwards** (§1, recency gate — git): `still_exists: false` ⇒
   `F = 0` and no candidate at all; stale ⇒ `F` **capped** at `0.25`, whatever band the table gave.
4. **The ceiling of 1 is absolute** (§0.2). No combination of structural rows reaches `F = 2`. The
   best structural candidate therefore scores exactly what a *thin* tier-1 candidate scores, and two
   full points below one with four or more occurrences behind it — which is the ordering the ceiling
   exists to protect. Grading changes who wins inside the structural pool and nothing else.
5. **Cite the row.** The candidate's score line names which row and band it used —
   `Fs0.75 (§6.3 row 3: 82% conventional over 288 human commits)` — so the number can be checked
   against `signals.json` instead of taken on trust.

**Worked — a fresh clone, no transcripts.** `history_bucket: none`, `signals.git.window.mode:
adaptive`, `days: 365`, `authorship.commits_human: 288`, 41 bot commits excluded.

```
  1. mirror-rule-src-test         Fs1.00 C2 D2 B2   score 8.0
     §6.3 row 1: cochange_cluster src/**/*.ts <-> test/**/*.test.ts (support 12, confidence 0.80)
  2. index-doc-commit-convention  Fs0.75 C1 D2 B3   score 7.5
     §6.3 row 3: 82% conventional over 288 human commits
  3. pre-commit-typecheck         Fs0.50 C2 D2 B2   score 7.0
     §6.3 row 4: package.json#scripts.typecheck exists, no CI job runs it
  4. rule-migrations-zone         Fs0.25 C1 D1 B2   score 4.5
     §6.3 row 1: cochange_cluster src/db/migrations/** + src/db/schema.ts (support 3, confidence 0.60)
```

Under the flat rule all four read `F1` and scored **8 / 8 / 8 / 6** — a three-way tie at the top, on
a run where the plan has to put something first. Graded, they score **8.0 / 7.5 / 7.0 / 4.5** and the
order lands on evidence. Nothing about the tier ordering moved: a single tier-1 record at `F2` would score
`4 + C + D + B` and still clear every one of them.

---

## 7. Worked examples

§7.1–7.4 is a run that works. §7.5–7.7 are three candidates from a real run against a 918k-LOC
monorepo with 81 sessions of history, and they are the reason §0.2, §0.3, §1.1, §2.6 and §6.1 exist
(§6.2 carries its own, from a different run).
Read them. **A worked negative is worth more than another rule** — the failures below all had strong
evidence strings, correct arithmetic, and passed every check the rubric had at the time.

### 7.1 Input — three records from `signals.json`

```json
{
  "sessions": {"files": 31, "count": 31, "first": "2026-05-19", "last": "2026-08-30",
               "user_turns_total": 1840, "user_turns_analyzed": 1512},
  "history_bucket": "medium",
  "request_shapes": [
    {
      "id": "rs-004",
      "skeleton": "add <noun> endpoint with validation and tests",
      "count": 7, "sessions": 4,
      "first_seen": "2026-06-02", "last_seen": "2026-08-28",
      "examples": [
        "add a bookings endpoint with zod validation and tests",
        "new endpoint for payouts, same validation pattern as listings, plus tests"
      ]
    }
  ],
  "corrections": [
    {
      "text": "use bun, not npm",
      "kind": "tooling",
      "count": 4,
      "examples": ["no, use bun install", "we use bun here, not npm run dev"]
    }
  ],
  "commands_requested": [
    {"command": "bun run typecheck", "count": 5}
  ],
  "pain_signals": [
    {"pattern": "type error found after commit", "count": 2,
     "examples": ["ci failed again on types, please run typecheck before you commit"]}
  ]
}
```

Relevant `discovery.json` facts: `commands.typecheck = "bun run typecheck"`,
`ci[0].runs = ["bun test", "bun run lint"]` (typecheck is **not** in CI), `package_managers = ["bun"]`,
`repo.size_bucket = "medium"`. Team size for the `B` axis comes from `signals.git`, not from
discovery: **2 non-bot rows** in `signals.git.contributors[]` — below the `B = 2` threshold of 3.
`discovery.git.contributors` is deliberately not quoted here; it is `shortlog --all` and counts
machines on unmerged refs, and a worked example is exactly where a reader picks up the wrong field.

### 7.2 Mapping decisions

All three records are **tier 1** (`request_shape`, `correction`, `commands_requested` +
`pain_signal`), so all three can set `F`. Each one's mechanism sentence is written before scoring;
they appear as the `Mechanism:` lines in §7.3.

**Record 1 — `request_shapes[rs-004]`.** `count 7 >= 3`, `sessions 4 >= 2`, skeleton implies three
steps (endpoint + validation + tests). Row 1 → **skill**. §2.1: the human triggers it and wants the
edits landing step by step, no persona, no parallelism → skill, not subagent. §2.5/§2.6: it is not
one existing command, and the three steps are *evidenced* — both examples spell out validation and
tests explicitly, so they survive the step test rather than being steps you assumed. Per PRD §8, the
*final check* inside the procedure ("and tests pass") is a separate deterministic step — but it is the same check as record 3, so it merges into that hook
rather than becoming a second one (anti-pattern A5/A10).

**Record 2 — `corrections[0]`.** `count 4 >= 2` → row 5 → **rule**. §2.3: no path context, one
sentence, globally true → **index-doc line**, not a rule file. §2.2 check: could a hook enforce
"never run npm"? A hook could block `npm ` in a Bash command — cheap, deterministic, exits 0/1. It
qualifies, but it fires *after* the model has already chosen the wrong tool, and the correction is
about authoring choice. Decision: index-doc line now, and note the optional hook as an opt-in in the
plan rather than building both (A5).

**Record 3 — `commands_requested[0]` + `pain_signals[0]`.** The same check requested 5 times, with 2
pain records about it, so row 4's `count >= 2` is cleared several times over → **hook**. It is one
non-interactive command (`bun run typecheck`), it exits 0/1, and `discovery.ci` does **not** run it,
so anti-pattern A2 does not apply. Pre-commit is the right trigger point because the pain signal is
"found after commit". Run §6.2 before combining the two records: the pain example *names the check*
("please run typecheck before you commit") and `commands_requested[]` carries no `examples[]` to
compare it against, so the pair is **overlapping** — 5 and 2 are not added. `F` comes from the 5
requests alone; the pain record rides along as `Supporting:`, which is also where it earns the C3.

### 7.3 Output — the candidate list

```
CANDIDATES (repo medium, history medium — 3 proposed, all built unless you drop one)

SKILLS (1)
  1. add-api-endpoint                                            score 12  (F3 C2 D2 B2)  tier 1
     Mechanism: next time the user says "add a <noun> endpoint", the skill runs the three steps they
       re-type every time — zod schema, handler, test file — so they stop re-typing them.
     Evidence: request_shape: "add <noun> endpoint with validation and tests" (7x across 4 sessions, 2026-06-02 to 2026-08-28)
     Will not: invent business logic, or touch auth middleware.

HOOKS (1)
  2. pre-commit-typecheck                                        score 11  (F2 C3 D2 B2)  tier 1
     Mechanism: next time a commit is about to land with a type error, the hook runs
       `bun run typecheck` and reports it before the commit, so the user stops finding it in CI.
     Evidence: commands_requested: "bun run typecheck" (5x, mined window 2026-05-19 to 2026-08-30)
     Supporting: pain_signal: "type error found after commit" (2x, mined window 2026-05-19 to 2026-08-30) — same turns; not added (§6.2)
     Note: CI runs `bun test` and `bun run lint` only — this check exists nowhere else.

INDEX DOC (1, always built)
  3. index-doc-toolchain-line                                    score 10  (F2 C1 D2 B3)  tier 1
     Mechanism: next time the agent reaches for a package manager, the index doc has already told it
       bun, so the user stops issuing the same correction.
     Evidence: correction: "use bun, not npm" (4x, mined window 2026-05-19 to 2026-08-30)
     Opt-in extra (not built by default): a PreToolUse hook that blocks `npm `/`yarn ` in Bash calls.

NOT PROPOSED
  - "run the tests" skill — anti-pattern A1: `package.json#scripts.test` already does it in one command.
  - Linear MCP draft — §1.1 gate 1 (A6): `@linear/sdk` appears only in the lockfile, and there is no
    tier-1 record of work against Linear. tool_mentions would not have helped it either (tier 3).
```

Score arithmetic, shown so it can be checked. Candidate 1: `count 7` and `sessions 4` give F3 (not
F4 — `count` is not `> 12` and there is no proof of 3 sessions inside the last 30 days); multi-step
authoring work is C2; procedure mapped to a skill is D2; the `api` zone spans folders so B2 →
6 + 2 + 2 + 2 = **12**. Candidate 2: 5 requests, and the 2 pain records are *not*
added to them because they plausibly describe the same turns (§6.2), so F2 on the 5 alone; a type
error caught after commit costs a redo, and a pain record is attached, so C3; mechanical check
mapped to a hook is D2; it gates every commit in the repo so B2 → 4 + 3 + 2 + 2 = **11**.
Candidate 3: `count 4` is F2; one wrong command costs a minute, C1; global convention as an
index-doc line is D2; toolchain choice is repo-wide, B3 → 4 + 1 + 2 + 3 = **10**.

Every `F` above came from a tier-1 record. Had any of these three leaned on a `tool_mention` or a
`file_hotspot` count, `F` would be 0 and there would be no candidate to score.

Reproduce this arithmetic in the plan for every candidate. Never round, average, or hand-wave a
score, and never adjust one after the fact to reorder a candidate.

### 7.4 What carries forward

Each of these three lines becomes one plan entry in phase 6 with the **same evidence string**, and
in phase 7 that same string becomes the `agentify-evidence:` frontmatter value of the generated
file. If you cannot carry the string all the way through, the candidate was never real. The
`Mechanism:` line travels with it and becomes the plan entry's **Purpose**.

### 7.5 Worked negative — `stripe-mcp-draft`, the candidate that scored highest and was wrong

Real run, 2026-09-04: a payments-heavy monorepo, 918k LOC, 81 sessions, in what was then
audit-only mode (since retired — PRD §9; this is a record of a past run, not an instruction). This
candidate scored **15 of a possible 16 — the top score in the run** — and should never have been
proposed. It is the reason this file has tiers.

**The real input:**

```
external_services[]  {"name": "stripe", "confidence": "high",
                      "evidence": ["dep:@stripe/stripe-react-native", "dep:stripe",
                                   "env:STRIPE_API_KEY", "env:STRIPE_QA_API_KEY"]}
tool_mentions[]      {"name": "stripe", "count": 16}          # rank 3 of all tools mentioned
pain_signals[]       one example: "usestripeboundary must be used inside stripeboundary"
raw_scripts          packages/payments#stripe-listen, root dev:stripe, scripts/stripe/ (4 files)
.mcp.json            linear-server, neon, posthog, expect — already configured
```

**What the old rubric did.** Row 8 read `confidence == "high"` **and** `tool_mentions.count >= 2`.
16 ≥ 2, so the row passed. `F` came straight off that 16: `count > 12` → **F4**, doubled to 8. A
pain example was attached → C3. External system → MCP draft is a partial determinism match → D1.
Payments touches money → B3. **Score 15**, ranked above a path-scoped rule backed by 48 pain records
and a skill backed by 15 asks across 10 sessions.

**Why it is wrong — not weak, wrong:**

- `tool_mentions.stripe = 16` counts the token "stripe" in prompts. It measures that Stripe *came
  up*. Sixteen mentions of a payment integration inside a payments app is what a healthy repo sounds
  like; it is not a request for anything. The rubric read attention as demand.
- The single attached pain example is a **React Native provider-nesting bug**. An MCP server that
  talks to the Stripe API cannot catch a hook called outside its provider. The artifact could not act
  on its own evidence (A12); the path-scoped mobile rule in the same plan was the actual fix.
- The repo already drives Stripe locally — `scripts/stripe/`, `stripe-listen`, `dev:stripe` — and
  nothing in 81 sessions records that loop failing (A13).
- Because `F` is doubled, a keyword count contributed 8 of the 15 points. **The noisiest word in the
  transcript won the run.**

**What happens now.** It dies three separate times, and the first is enough:

| Gate | Result |
|---|---|
| §0.3 mechanism test | *"Next time the user mentions Stripe, the MCP server …"* — the blank cannot be filled, because no record says what the user was *doing*. **Dropped before scoring.** |
| §0.2 tier rule | Its only sizeable evidence is `tool_mention` — tier 3, which cannot meet a threshold or set `F`. Tier-1 evidence naming Stripe: one pain example. §1.1 gate 2 needs ≥ 3 across ≥ 2 sessions. **`F = 0`; never enters a pool.** |
| §1.1 gate 3 | `stripe-listen`, `dev:stripe` and `scripts/stripe/` already exist, with no correction or pain signal against them. **`Skipped (already covered)`.** |

New score: **none**. It never earns one — the mechanism test runs before scoring, which is the whole
point of putting it there. The plan entry becomes:

```
### Skipped (already covered)

| Candidate | Type | Score | Evidence | Why skipped |
|---|---|---|---|---|
| stripe-mcp-draft | MCP draft | — (F0) | external_service: stripe (confidence high; dep + env-name) | `tool_mentions` is tier 3 and justifies nothing; the only tier-1 record naming Stripe is one pain example about a React Native provider boundary, which an MCP server cannot catch. `packages/payments#stripe-listen`, `dev:stripe` and `scripts/stripe/` already drive Stripe locally. Reopens if: a correction or pain signal about that local loop, or 3+ asks that need live Stripe state. |
```

That last clause — *what would change the answer* — is required on every skipped entry a user might
reasonably argue with. Being cut is a finding, not a silence.

### 7.6 Worked negative — `commit-hostshare`, the right count on the wrong artifact

Same run. Evidence, all real:
`request_shape: "commit staged changes" (15x across 10 sessions, 2026-08-18 to 2026-09-04)` — the
**highest-count tier-1 record in the entire run** — supported by
`correction: "Do not commit, stage, push or change branch without asking me first." (3x)` and
`commit_conventions: conventional_pct 0.77 of 2,954 human commits (46 bot commits excluded); scopes
web 366 / database 124 / api 88; imperative_pct 0.96; subject_median_len 75`.

Note the denominator: **2,954, not the 3,000** in `signals.git.window.commits_analyzed`. That field
is the number of commits *read*; `signals.git.authorship.commits_human` is what every percentage is
computed over (§1). Quoting 3,000 here would put a number the tool does not compute into an evidence
string that gets copied verbatim into `plan.md`, `report.md` and an `agentify-evidence:` line — the
same string in all four places, which is what makes them checkable against each other.

The count is not the problem. The count is the best in the run. The **type** was the guess: proposed
as a skill at `.claude/skills/commit-hostshare/SKILL.md`, score 13.

Run §2.6 on it:

1. **List:** read the staged diff; write a subject in this repo's convention; show it; do not stage,
   push, or switch branch.
2. **Keep only evidenced steps:** "don't stage/push/switch" comes from the *correction* — a
   constraint, not a step. "Read the staged diff" is what `git commit` already does. Remaining:
   write the message.
3. **Extract the knowledge:** the convention (conventional type, that measured scope vocabulary,
   imperative, ~75 chars) is something the artifact would *follow*, not a step it would *run*. Under
   §2.3 it is an index-doc line — which is where the same plan had already put it, in the same run.
4. **Count what is left:** **one** step, mapping to `git commit`, which exists → row 2,
   **index-doc line**.

So the default flips: the convention and the ask-before-committing policy go into the index doc, and
the skill goes under `### Skipped (already covered)` naming `git commit` and the index-doc line that
now carries the convention, with one line saying what would change the answer — *"if you are
rewriting the generated message by hand most times, that shows up as a correction on the message
text, and this becomes a skill."*

The general form: **a repeated one-command ask plus a convention is a rule, not a skill.** Only
evidenced steps promote it. The original plan half-sensed this and offered the user an "approved
except 3" escape hatch; an escape hatch is not a rubric. The rubric decides now, and the user can
still overrule it at the phase 6 gate.

### 7.7 Worked edge — `agentify-conventions`, a count sitting exactly on the line

Same run. `correction: "Do not commit, stage, push or change branch without asking me first." (3x,
mined window 2026-07-26 to 2026-09-04)`, drawn from 81 sessions. Row 5 needs `count >= 2`, so it
passes; `count 3` lands in the F1 band and the run scored it 7 (F1 C1 D2 B2) — arithmetically
correct. Two things the old rubric had no rule for:

**Cluster integrity (§6.1.2).** The two visible examples were *"continue work here, don't commit."*
and *"do not commit and push"*. Same instruction in two shapes — plausibly one need, but the third
occurrence is not visible and the skeleton is broad enough to have swept in a one-off. Three
occurrences across **81 sessions** is one every twenty-seven sessions. Verdict: keep it, but the
count is unverified beyond the two examples shown, so the line is `low-confidence` — listed, and
**not built unless the user opts in** (interview Q13).

**Per-claim confidence (§6.1.3).** This artifact is one index-doc section carrying two claims of very
different strength:

| Claim | Evidence | Tier | Mark |
|---|---|---|---|
| commit subjects are conventional, imperative, ~75 chars, scoped to a workspace | `commit_conventions`: 77% of 3,000 human-authored commits, scopes measured — **and zero of the repo's 35 existing rule files contain "conventional commit", "commit message", "feat(" or "fix("** | 2 | `structural`, **Fs0.75** (§6.3 row 3) — build it |
| ask before commit / stage / push / branch | `correction` ×3 across 81 sessions; visible examples are different phrasings | 1 | `low-confidence`, F1 — offer it |

Under §6.1.3 the section ships with the first claim, and the second is offered as an opt-in line —
instead of both riding into the repo on one score. The index doc itself is still written; row 11 is
unconditional.

Worth noticing what makes the strong claim strong: it is **tier 2 with a verified negative**. The
convention is followed by 77% of 3,000 commits and written down in none of the 35 rule files. "The
repo does X consistently and documents it nowhere" is one of the few tier-2 findings that stands on
its own, because the gap *is* the evidence.

It is still capped below tier 1. §6.3 row 3 puts `0.77` over 3,000 human commits in the `0.75` band,
so it scores `(0.75 × 2) + C1 + D2 + B2 = 6.5` — not the `13` the same C/D/B would reach on top-band
demand — and it sits at the bottom of its pool and gets built anyway. Note what the graded scale
buys even here, on a run that *had* 81 sessions of transcripts: `Fs0.75` and the `Fs0.50` of a
script CI does not run are now different numbers, where the flat rule made them the same one.


---

## 8. Handoff to coverage

Once the candidate list is ranked, read `coverage.md` in the same phase: §2 for merge-and-order, §6
for de-duplication against what already exists (by `blueprint.md` §2.1's definition — same type,
same job, this repo), §10 of `blueprint.md` for the catalogue walk table the plan must carry, and
§8 for how skipped candidates are presented. **Nothing is cut for count** — the only reasons a
candidate is not built are no evidence, already covered, or low-confidence-not-opted-in.

Two things must survive into the plan:

- The `Mechanism:` line (§0.3), which becomes the plan entry's **Purpose**.
- The `low-confidence` / `structural` marks (§6.1). A low-confidence candidate is still not built
  without the user's yes, and is listed under `### Skipped (low confidence — opt in to build)`.
  Every phase-4 candidate ends in exactly one bucket: built, insufficient evidence, already
  covered, or low-confidence-opt-in.
