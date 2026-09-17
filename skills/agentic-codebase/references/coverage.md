# coverage.md — completeness, ranking, and what gets skipped

Read this in **phase 4 (Propose)**, immediately after `mapping-rules.md` and `blueprint.md`, on the
ranked candidate list. This file replaces the sizing-cap table that earlier versions of agentic-codebase
applied here.

---

## 1. There are no caps

**agentic-codebase does not limit how many artifacts it builds, and never tells the user a limit stopped
it.** The words *cap*, *limit* and *quota* do not appear in a plan, a report, a question or a
summary. If a candidate is not built, the reason is always one of exactly three things, and all
three are facts about the evidence rather than about a number agentic-codebase chose:

1. **No evidence** — the field the row needs is empty or below its threshold (`mapping-rules.md` §0).
2. **Already covered** — an artifact of the **same type inside this repo** already does the same
   job (`blueprint.md` §2.1); for a hook, a CI job or repo script; for a skill, one existing repo
   command that *is* the whole procedure (A1, A2, A9). Nothing else covers anything: not the index
   doc, not a vendored guide, not a user-scope skill or plugin, not a document, not a human GUI.
3. **Low confidence** — it cleared its threshold but on thin or stale demand, so the user opts in
   (`mapping-rules.md` §6.1).

### Why the caps went

They were a proxy for quality and they measured the wrong thing. Measured on a real 268k-line
Next.js repo (2026-09-07): the repo had **0 subagents, 0 rules and 0 hooks**, a `.env.local` on
disk, two competing lockfiles, and eight external services. It also had 61 skill directories under
`.claude/skills/`, of which 48 were third-party library guides installed from a lockfile. Those 61
tripped a "mature setup" test, which clamped the run to 2 skills / 1 subagent / 3 rules / 2 hooks —
on the repo in the sample with the **most** missing. The user was then told a cap was the reason.

Fewer, sharper artifacts do get used. That is still true, and it is enforced by §2's ranking and by
`blueprint.md` §1.1's personalization tests — by making each artifact earn its file, not by
stopping at an arbitrary count. A repo with nine real zones gets nine zone rules.

---

## 2. Ranking — order, do not cut

Every surviving candidate is built unless the user removes it. Ranking still matters, for three
reasons: build order, the plan's presentation order, and which artifact the user's attention lands
on first.

1. **Merge first.** Overlapping candidates within a type — same skeleton family, same paths, same
   check — merge into one before anything else. Merging late loses the better half of a candidate.
2. **Drop zero-evidence candidates.** They were never in a pool (`mapping-rules.md` §0.1).
3. **Rank within each type** by the §6 score, descending, with §6's tie-breaks.
4. **Present in build order, ranked within type** (`SKILL.md` phase 7 owns the order: rules →
   hooks → settings → skills → subagents → MCP drafts → index doc).
5. **No trading across types.** Do not re-map a weak skill into a rule to get it built. If it is a
   rule, it was always a rule.
6. **No cutting by argument.** A sentence in the plan explaining why this repo is better served by
   fewer artifacts — "knowledge is not the gap", "these would only restate the index doc" — is
   `mapping-rules.md` A17, the rationalized cut. Delete the sentence and re-walk the rows it
   excused. The user cuts at the gate; the run does not cut for them.

### 2.1 When the total is large, say so — and still propose it

A large repo with rich history can produce twenty-plus candidates. That is a correct outcome, not a
runaway. What it changes is presentation, never content:

- Group the plan's `What gets built` list by type, numbered continuously, so `approved except 7,
  12 and 19` stays unambiguous.
- Put one line in the plan's summary: `N artifacts proposed across M types. Approve all, or name
  the numbers to drop.`
- **Never** pre-trim to be polite. The phase 6 gate exists precisely so the user decides.

---

## 3. Thin evidence means less output, and says why

The counterpart to "no caps" is that a thin repo genuinely produces a small setup, and the plan
must say what was missing rather than implying agentic-codebase held back.

`history_bucket` is `none` — no transcripts, or consent declined. Behavioural rows are all empty,
so `mapping-rules.md` §3's evidence requirement removes most skill and subagent candidates on its
own. That is the mechanism; there is no separate clamp. **Structural candidates still fire** — the
`blueprint.md` catalogues run off `discovery.json`, so a no-history run on a real codebase still
produces zone rules, guardrail hooks, permissions, MCP drafts and `setup-manager`.

Put this line in the plan verbatim when `history_bucket == "none"`:

```
No transcript evidence was available this run, so everything below is derived from the codebase
itself. Re-run agentic-codebase after a week of normal usage and the setup will also be shaped by what you
actually ask for.
```

And name the disagreement when the repo and the history disagree sharply — a 300k-line repo with 6
sessions, or a 4k-line repo with 400. It is a real finding about where the evidence is thin, and it
belongs in the plan's summary as one sentence. It changes nothing about what gets built.

---

## 4. What to tell the user when presenting the list

Print this verbatim when presenting the candidate list, and again in the plan summary:

```
This is the whole setup I can justify from your codebase and your history — nothing is being held
back. Every item below names the evidence it came from. Approve all of it, or tell me which numbers
to drop; anything you drop stays in the report so you can add it later.
```

---

## 5. The user's controls

The shortlist (`plan-template.md` §0) and the gate are the control surface, and they are why the
interview does not ask what they settle. Three values reach the plan **derived rather than asked**
— `mode`, `services` and `team_size` (`interview.md` §4.2, §4.8) — and each carries a line saying
how to overturn it. Overturning one is a plain sentence at the shortlist or the gate, not a
question round. The shortlist is where most edits happen — it is the whole list on one screen,
numbered, before the plan exists — and every edit made there is a line in the plan's summary.

- **They can drop anything**, at the shortlist or the phase 6 gate, by number. Honour it exactly.
- **They can overturn a derived value** in words: "stage only" sets `mode`, "we're a team" sets
  `team_size`, naming services reorders them. Never re-ask to confirm — a derived value put back as
  a question is a retired question reinvented (`interview.md` §4.1).
- **They can ask for more** — a type they want covered that produced no candidate. Take it, and
  build it **only if evidence exists**: search the JSON again for the field that would license it,
  and if there is none, say so plainly and offer the nearest thing that is evidenced. Wanting an
  artifact is not evidence for it.
- **They can cap a type at zero** ("no hooks"). Honour it exactly, and record it in the plan.
- **They can ask for fewer.** Then cut from the bottom of the §6 ranking and show what went.

Every one of these is recorded in the plan as a line naming who asked and for what.

---

## 6. Existing setups — de-duplicate hard, never throttle

A repo that already has agentic config gets the **same** treatment as an empty one, with one
addition: everything already there is de-duplicated against.

**There is no audit-only mode.** Earlier versions flipped into one at 5+ existing skills and agents
and cut the output; §1 records what that produced. What survives from it, and is unconditional in
every run:

- **Never restructure.** Do not move, rename, reorganise, split, merge or reformat an existing
  skill, agent, rule, hook or index doc. This is the additive invariant, not a mode.
- **Never rewrite the user's prose.** Existing files are read for de-duplication only. The index
  doc is appended to inside markers, always.
- **De-duplicate against artifacts of the same type inside the repo** (`blueprint.md` §2.1) — the
  team's own, tested against this repo rather than trusted; a symlinked one counts once. A
  **vendored** artifact covers nothing: it is a generic guide, and it becomes a reference the
  generated skill links to, with `provenance.vendored_artifacts` naming its source in the plan.
- **Never touch a symlinked or vendored artifact.** A symlink lives in another store and editing it
  changes every repo that links it; a vendored artifact is overwritten by its next install. If one
  is broken, that is a report line, not an edit.
- **Propose fixes, never apply them silently.** A defect in an existing artifact — a broken hook
  path, two rules contradicting each other, a duplicate skill name — is listed in the plan under
  `## Existing setup notes` with the file path and the suggested change, and applied only if the
  user approves that item by number.

### 6.1 Scope: this repo, never the machine

**Only artifacts inside `$REPO_ROOT` are this repo's setup.** A skill in `~/.claude/skills` or
`${CODEX_HOME}/skills` loads in every repo on the machine and says nothing about this one. Discovery
already keeps them apart: `counts` and `provenance` are repo-scoped; `user_scope` is the home store
and is reported so that **name collisions can be named**. Never sum `user_scope` into anything,
never quote it as "your setup", and never let it change what this run builds.

**Home-scope entries cover nothing — not even by de-duplication.** Measured 2026-09-07: a
user-scope PostHog plugin and a user-scope Codex MCP entry were taken as covering three analytics
skills and an MCP draft, on a run whose whole purpose was a repo-scoped setup a teammate would get
by cloning. A same-name collision (`~/.claude/skills/qa` beside a generated `.claude/skills/qa`) is
one line in the report saying both load and which the user may want to rename. It is never a skip.

### 6.2 Reading the provenance fields

| Field | Counts | Use it for |
|---|---|---|
| `counts.skills`, `counts.agents`, `counts.rules`, `counts.hooks` | every repo-level artifact found, the team's own and vendored alike | de-duplication, and telling the user what is installed |
| `provenance.own` + `provenance.ambiguous` | the artifacts this team wrote | one sentence of context in the plan — never a gate |
| `provenance.vendored` | installed from elsewhere (a `skills-lock.json` entry, a vendor or plugin-cache path, frontmatter naming a source) | naming the source when a generated skill links it as a reference; **never coverage** (`blueprint.md` §2.1) |
| `symlinked.skills`, `symlinked.agents` | entries resolving outside their directory | the never-touch list |
| `user_scope.*` | the machine-wide store (Codex home, Claude home) | name collisions in the report, §6.1; **never coverage** |

`maturity` is still emitted by `discover.py`. **It no longer gates anything.** Quote
`provenance.maturity_basis` in the plan when `provenance.vendored` is non-zero, as one line of
context — `12 of the 61 skills here are your own; the other 49 are installed third-party guides` —
so the user can see the classification. Then build the full setup regardless.

---

## 7. Zones, monorepos, and rerun accounting

- **Monorepo.** Default is one setup at the repo root. If `monorepo.is_monorepo` is true and the
  user chose per-package setups in phase 5, each package gets its own zone rules and its own index
  doc, and `blueprint.md` §5.1's per-workspace rule split applies. Say the resulting file count
  before building.
- **The index doc** is exactly one file per setup, and is always built (`mapping-rules.md` row 11).
- **A rerun** updates artifacts carrying an `agentic-codebase-id` in place and never duplicates them. An
  updated artifact is listed in the plan as `updated`, not `new`.

---

## 8. What happens to skipped candidates

Skipped candidates are **never silently dropped**. Every one appears in the plan under one of
exactly three headings, with its score and reason, so the user can pull it back before approving.

- **`### Skipped (insufficient evidence)`** — the count was below the row threshold. Show the count
  found and the threshold missed. More usage brings these back.
- **`### Skipped (already covered)`** — an artifact of the **same type inside this repo** already
  does the job, or a CI job / repo script does for a hook, or one repo command is the whole
  procedure for a skill (A1, A2, A9; `blueprint.md` §2.1). Name the file or command. Nothing
  vendored, user-scope, index-doc or documentary ever appears in this column.
- **`### Skipped (low confidence — opt in to build)`** — cleared its threshold but sits at `F = 1`
  on thin or stale demand (`mapping-rules.md` §6.1). Show the score with its breakdown and the
  number that made it thin. Only the user's yes brings these back. A `structural` `F = 1` — a script
  that exists, a convention most commits follow — is **not** low-confidence and does not belong here.

There is no fourth heading. `### Skipped (over cap)` is retired; a plan that emits it is wrong.

Every candidate produced in phase 4 ends in exactly one of: **built**, insufficient evidence,
already covered, low-confidence-opt-in. A candidate in none of those lists is a bug in the run.
