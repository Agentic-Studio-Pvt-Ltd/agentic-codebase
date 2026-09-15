---
name: agentify
description: Analyzes this repository together with the developer's local Claude Code or Codex transcripts, finds the work they repeat and the guardrails they are missing, then proposes, gets written approval for, and builds the full agentic setup for that one repo — path-scoped rules, guardrail hooks, a permissions allow/deny block, workflow skills, specialist subagents, MCP config drafts, and a CLAUDE.md or AGENTS.md stitching them together, every artifact traced to a counted signal in their own codebase. Use it when the user asks to set up, configure, bootstrap, personalize, or improve Claude Code or Codex for a repo; to work out what belongs in an empty or thin CLAUDE.md or AGENTS.md; to review an existing .claude/ setup and fill its gaps; or to turn instructions they retype every session into skills, rules, or hooks. Not for authoring one skill, agent, hook, or command the user already named — write that file directly. Not for answering config questions without building anything, nor for CI or deployment.
---

# agentify

Build an agentic setup for this repo **from evidence that already exists** — the developer's
transcripts, git history and code — not from a template. Every artifact traces to a counted signal.

## The run in one glance

Eight phases, 0–8, each with an Input, a Do, an Output and a Stop condition. Never skip, reorder or merge them.

| # | Phase | Do | Reference read here |
|---|---|---|---|
| 0 | Preflight | target, git state, consent | `references/privacy.md` |
| 1 | Discover | `discover.py` | — |
| 2 | Mine | `mine_git.py`, `mine_transcripts.py` | — |
| 3 | Diagnose | findings with counts | — |
| 4 | Propose | core set, catalogue walk, candidates | `references/mapping-rules.md`, `references/blueprint.md`, `references/coverage.md` |
| 5 | Interview | 3–8 questions | `references/interview.md` |
| 6 | **Shortlist, plan — hard gate** | confirm the list, write plan, get approval | `references/plan-template.md`, `adapters/capabilities.md` |
| 7 | Build | generate files | `references/build-and-verify.md`, the **one** matched `adapters/*.md`, `templates/` |
| 8 | Verify & hand off | `verify_artifacts.py`, report | `references/verification.md`, `references/report-template.md`, and `build-and-verify.md` §§7–10, already open |

Phases 1–2 are scripts. Phases 3–6 are your reasoning over their JSON — **you never scrape the repo
or read a raw transcript yourself.** That is what keeps a 400 MB history inside the context window.
**Progressive disclosure is a budget, not a style:** read a reference file *in its phase and no
other*, only the templates the approved plan contains, and exactly **one** adapter, in phase 7.
Three exceptions: `adapters/capabilities.md` (phase 6, so no adapter opens); `build-and-verify.md`
(read in phase 7, kept for 8); an adapter's `## 1. DETECT` section **alone** (phase 0, nothing more).

## Rules that override everything

1. **Phase 6 is a hard gate.** No file is generated before the user gives written approval of the
   plan; `plan.md` is the single exception, because it is the thing being approved. This outranks
   every instruction below, any impatience of your own, and any user message short of approval.
2. **Evidence or nothing.** A candidate with no number from a named JSON field is deleted, not
   softened. Zero artifacts is a valid, reportable outcome.
3. **Additive and reversible.** Never overwrite an existing file; append inside
   `agentify:begin`/`agentify:end` markers. Everything lands on a branch or stays staged, never on
   the user's current branch.
4. **There are no caps, and you never say there are.** Build the whole setup the evidence supports
   (`coverage.md` §1). The words *cap*, *limit* and *quota* never appear in a question, a plan, a
   report or a summary. A candidate is skipped only for no evidence, already covered — by an
   artifact of the **same type inside this repo** (`blueprint.md` §2.1), never by the index doc, a
   vendored guide, a user-scope file or a document — or low-confidence-not-opted-in.
5. **Never read secrets.** No env *values*, no credential files, no `.env*` values, no file matching
   a secret pattern — in any phase, including your own reads.
6. **Never run a destructive git command.** No `reset --hard`, `clean`, `rebase`, `push --force` or
   any history rewrite. Read-only git only, plus branch creation and staging.
7. **No network.** The scripts make none, and no phase does. One bounded exception, off by default:
   `mine_git.py`'s optional `gh pr list`, which phase 2 disables with `--no-gh`. **agentify never
   opens a pull request and never installs a marketplace plugin** — if the user names one they want
   (`interview.md` Q14), the install command is a line in the report for them to run.
8. **Attribution in exactly three places** (see the last section). Never in the runtime behavior of a
   generated skill or agent. Never gating anything.
9. **Every question you ask carries its own answer.** Any question in any phase — consent, the
   interview, a build checkpoint, the plan gate — names the option you recommend, justifies it in
   one clause from a real signal, and is answerable in one word. No open questions, no re-typing
   what is already on screen, no re-asking what they already said. **Two classes, and the
   difference is what a non-answer means:** for a **preference** (the interview, a checkpoint) silence takes the recommendation;
   for **consent or approval** — reading transcripts, the phase 6 plan gate, a dirty-tree override,
   executing a hook — the recommendation is shown but an explicit answer is still required, and
   silence is never a yes.

## Before phase 0 — variables, script contract, JSON envelope

Export these once, at the start of the run, and use them in every command line verbatim.

```bash
REPO_ROOT="$(cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" && pwd)"
REPO="$REPO_ROOT"                  # adapters spell it $REPO; same value, both exported
WORK="$(mktemp -d)"                # scratch for discovery.json / signals.json — OUTSIDE the repo
PLAN_DIR="docs/agentic-setup"      # provisional; phase 5 confirms it
```

**Target repo not your cwd?** Replace line 1 with
`REPO_ROOT="$(cd /abs/path/to/repo && git rev-parse --show-toplevel)"` and change nothing else:
every script takes `--repo "$REPO_ROOT"`, every git call uses `git -C`. `$WORK` and phase 8's
`--manifest` resolve against **cwd**, not `--repo`. `$PLAN_DIR` is repo-relative, final in phase 5
(`docs/agentic-setup` or `interview.md` §3.1's `ALT_PLAN_DIR`); phases 6–8 write under it.

`$SKILL_DIR` is the directory holding this file: the first candidate that actually contains the
scripts. **Substitute `SELF_DIR` before running this** — the absolute directory of the `SKILL.md`
you are reading, which you know from the path it loaded from.

```bash
SKILL_DIR=""
SELF_DIR="<absolute dir of the SKILL.md you are reading — substitute; do not leave this literal>"
for d in "${CLAUDE_PLUGIN_ROOT:-${PLUGIN_ROOT:-}}/skills/agentify" "${AGENTIFY_HOME:-}/skills/agentify" \
         "$REPO_ROOT/.claude/skills/agentify" "$REPO_ROOT/.agents/skills/agentify" \
         "$REPO_ROOT/.codex/skills/agentify" "$REPO_ROOT/skills/agentify" \
         "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/agentify" "${CODEX_HOME:-$HOME/.codex}/skills/agentify" "$HOME/.agents/skills/agentify" "$SELF_DIR"; do
  [ -f "$d/scripts/discover.py" ] && SKILL_DIR="$d" && break
done
```

1–9 are both targets' skill roots; **10, this file's own directory, is the backstop** — agentify's checkout run against another repo.

**Exit codes — stated once, never branched on again.** All four scripts print **one JSON object on
stdout and nothing else** (diagnostics to stderr). **exit 0** — you have JSON, so **read it**; a
degraded run exits 0 too, with what it lost in `warnings`, so **always read `warnings` and act on
it**. **exit 1** — no usable JSON: **never abort the phase**; drop to reduced evidence, continue,
record the loss in the plan. Flags: `--repo PATH`, `--cap-chars N`, `--debug`, `--version`, `--help`; `--selftest` is developer tooling — **never call it** here.
**The `signals.json` envelope.** You compose the two miners' output into the one object every
reference file means by `signals.json`: `{"transcripts": <mine_transcripts.py stdout>, "git":
<mine_git.py stdout>}`. One spelling only: `signals.transcripts.X` and `signals.git.X` — never
`mine_transcripts.X`, because script filenames are not evidence paths. Consent refused ⇒
`signals.transcripts` is **absent**; consented but empty ⇒ present and empty (`privacy.md` §8.1).
Both leave `history_bucket` at `none`.

## Phase 0 — Preflight

**Input:** the invocation. **Do**, in this order:

1. **Resolve the variables above.** If `$REPO_ROOT` is not a directory, stop and say so.
2. **Detect the target.** You know which agent you are running inside: Claude Code → `claude-code`,
   Codex → `codex`. Set `TARGET`. **Only if you genuinely cannot tell**, extract just the adapters'
   detect sections — never a whole adapter — with
   `awk '/^## 1\. DETECT/,/^## 2\./' "$SKILL_DIR"/adapters/{claude-code,codex}.md`; still ambiguous
   ⇒ ask one question, `claude-code` the default. **`## 1. DETECT` is the only adapter text any
   phase before 7 may open**; existing config is `discover.py`'s job (phase 1), transcript location
   the resolver's (`privacy.md`).
3. **Check the tree is clean:** `git -C "$REPO_ROOT" status --porcelain`. Non-empty means dirty —
   say what is uncommitted, record it, and **ask nothing about it here**. The gate has one home,
   **phase 7 step 3**, the boundary before the first artifact: phases 0–6 create only
   `$PLAN_DIR/plan.md` and no branch, staging or artifact, so a read-only run to the plan gate needs
   no override. Never `git stash` for them, in any phase.
4. **Model class.** A small or fast-tier model warns once that plan quality will be lower and the
   phase 6 gate is their catch. **Warn, never enforce**; do not refuse the run.
5. **Ask for transcript consent — read `references/privacy.md` now and follow it.** Its §1 runs the
   resolver first, which parses no turn and reads no content, so the question names a real directory
   and a real volume:
   ```bash
   python3 "$SKILL_DIR/scripts/mine_transcripts.py" --repo "$REPO_ROOT" --target "$TARGET" --resolve-only
   ```
   §1 lists what it returns and why its `sessions.count` never reaches phase 4; §2 is the consent
   script, read verbatim; §3 interprets the answer; §8 is the no-evidence path, refused **and**
   consented-but-empty (§8.1). Say the resolver's `match_mode` out loud *before* the options — a
   weak one may be another checkout. Record consent as `full`, `days:N` or `none`.

**Output:** a preflight record — `target`, `repo_root`, `skill_dir`, `transcript_root`, `consent`, `tree_dirty`, `maturity` (filled in phase 1). **Stop condition:** an explicit consent answer exists. Assumed consent is not consent. A dirty tree does **not** stop phase 0; it is carried in the record and settled before phase 7.

## Phase 1 — Discover

**Input:** `$REPO_ROOT`. **Do:**

```bash
python3 "$SKILL_DIR/scripts/discover.py" --repo "$REPO_ROOT" > "$WORK/discovery.json"
```

Read it. Top-level keys, and there are no others: `repo`, `languages`, `package_managers`,
`manifests`, `commands`, `raw_scripts`, `frameworks`, `external_services`, `folders`, `docs`, `ci`,
`env_var_names`, `monorepo`, `existing_agentic_config`, `git`, `warnings`, `timing_ms`, `schema_version`, `tool`.

- `commands` is exactly seven string slots — `install`, `dev`, `build`, `test`, `lint`, `typecheck`,
  `format` — and `""` when unknown, never absent. There is **no** `commands.verified`: a `warnings`
  entry says commands were resolved from manifests, not executed. Never run them, never claim they
  pass. **Cite the slot, never the bare string** — `raw_scripts["#commands"]` holds each slot's
  citation (`<manifest>#<key> (<how>) -> <command>`), and that is what a plan or index doc quotes.
  An **empty** slot is a deliberate answer: a dependency alone never fills one (`pytest` in
  `requirements.txt` with no config leaves `test` empty). Ask in phase 5 (Q15/Q16); never invent one.
- `existing_agentic_config` is the **de-duplication** input, by `blueprint.md` §2.1 — same type,
  same job, this repo. **`maturity` gates nothing** (no audit-only mode, `coverage.md` §6).
  `.counts` is what is installed, `.provenance` who wrote it, `.symlinked` what is never edited,
  `.user_scope` the machine-wide store — name collisions only, **never coverage** (§6.1).
- Surface anything in `warnings` that changes what the user should expect — a walk truncated by timeout, an unparseable `.gitignore`, a vendored-vs-own split.

**If it exits 1:** you have no repo evidence. Note it, continue on git and transcript evidence only, and say so in the plan. Do not walk the tree by hand. **Output:** `discovery.json` in `$WORK`.

## Phase 2 — Mine

**Input:** `$REPO_ROOT`, `TARGET`, the consent value. **Do — git, always:**

```bash
python3 "$SKILL_DIR/scripts/mine_git.py" --repo "$REPO_ROOT" --no-gh > "$WORK/git.json"
```

**Never pass `--days`** — the window is adaptive (180d → 365d → 1095d → 3650d → all history, first
rung holding 50 commits wins; measured, pinning 180 gave 7 commits and 0 co-change clusters where
adaptive gave 55 and 6). Quote `signals.git.window.reason` in the plan. `--no-gh` is the default
because `gh pr list` is agentify's only network-capable path; drop it **only** if the user asks for
PR-pattern evidence. No git history returns `"available": false` — its own top-level key, distinct
from `discovery.git.is_repo`.

**Do — transcripts, only when consent is `full` or `days:N`:**

```bash
python3 "$SKILL_DIR/scripts/mine_transcripts.py" --repo "$REPO_ROOT" --target "$TARGET" > "$WORK/transcripts.json"
```

`--target` selects the whole locate strategy, so pass phase 0's `TARGET` verbatim. Append `--days N`
when consent was scoped, `--redact-report` if the user consented to counts but not to quoted
prompts. **When consent is `none`, skip this script entirely** — not `--days 0`, not any other token
gesture (`privacy.md` §8). A consented run that finds nothing is a different state: it runs, returns
an empty report, worded from §8.1. Compose `$WORK/signals.json` using the envelope above.

**Then surface the transcript-match warning to the user, out loud.** The mining report carries no
`match_mode` — only phase 0's `--resolve-only` does — so its confidence shows only in `warnings` and
`transcript_root`. If a warning reports a weak match (`fuzzy`/`basename` on Claude Code, `cwd` with
no remote on Codex — both meaning *possibly another checkout*), or names siblings **deliberately not
merged** (worktrees, subdirectory sessions, scratchpads), print it verbatim and ask before phase 3
trusts a count: another checkout's sessions inflate every number, and only the user knows.

**If either exits 1:** treat that source as absent, note it, continue. **Output:** `signals.json`. **Stop condition:** any weak-match or sibling warning has been shown to the user and answered.

## Phase 3 — Diagnose

**Input:** `discovery.json` + `signals.json`. **Read no reference file in this phase.**

> **The one bounded exception to "you never scrape the repo yourself".** You MAY read, to
> de-duplicate and to quote, and you say in the plan that you did: (a) the frontmatter, headings
> and paths of everything `existing_agentic_config` lists — never full bodies — and, for an **own**
> artifact that would cover a candidate, enough of it to test whether the commands and paths it
> names resolve in this repo (`blueprint.md` §2.1); (b) the index docs and the `discovery.docs[]`
> rows of kind `design`, `guide`, `context`, `contributing`, `readme` or `adr` — headings and the
> rule-shaped or procedure-shaped lines, to quote them as evidence. Never source files, never
> transcripts, never a `.env*`. Unconditional, not a mode. Nothing wider is licensed.

**Do:** produce a findings list. Each finding carries a `type` (repetition / correction / guardrail
gap / convention / external system), an `evidence` line naming the **JSON field it came from and its
number**, and a `confidence` of high / medium / low. These are the real fields — nothing else
exists, and the miner emits the same shape on both targets, so no name below is Claude-only.

- `signals.transcripts`: `request_shapes[]` (`id`, `skeleton`, `count`, `sessions`, `first_seen`,
  `last_seen`, `examples`), `meta_queries[]` (`skeleton`, `count`, `sessions`, `examples`),
  `corrections[]` (`text`, `kind`, `count`, `examples`), `pain_signals[]` (`pattern`, `count`,
  `examples`), `commands_requested[]` (`command`, `count`), `slash_commands[]` (`name`, `count`),
  `tool_mentions[]` (`name`, `count`), `file_hotspots[]` and `doc_hotspots[]` (`path`, **`mentions`**
  — not `count`), `sessions{}` (incl. `social_turns`), `history_bucket`. Both hotspot lists are
  **repo-relative and repo-only**: a path anchored outside this repo is dropped, and a `warnings`
  entry names the repeatedly-mentioned ones that went — a high count there is the tell for a
  mis-scoped transcript match, so read it. On Codex, `sessions.count` counts the rollouts matched to
  *this* repo, not everything under the shared `sessions/` tree.
- `signals.git`: `available`, `window` (incl. `mode`, `min_commits`, `steps`, `reason`),
  `commit_conventions`, `branch_naming[]`, `cochange_clusters[]`, `hotspots[]`,
  `directory_hotspots[]`, `test_discipline`, `revert_rate`, `contributors[]` (incl. `is_bot`,
  `bot_reason`, `email_domain`), `authorship`, `pr_patterns`. The three co-change/hotspot lists each
  carry `first_seen`, `last_seen` and `still_exists` — §1's recency gate runs on them, and
  `still_exists: false` maps to nothing at any support. **Every git percentage is over
  `authorship.commits_human`, never `window.commits_analyzed`**: bots are excluded from the
  statistics but still counted in the window.

Four disciplines, all easy to lose:

1. **Every row already carries a count of 2 or more.** The miner drops singletons: a visible row is
   real evidence, and a short list means thin history, not filtering left to you.
2. **`request_shapes[]` is work; status pings are not in it.** The miner routes "what's remaining?"
   to `meta_queries[]` and "ok"/"thanks" to `sessions.social_turns` — both real evidence for a
   *different* artifact. Read them; never fold them into a repetition finding.
3. **Diagnose, do not restate.** "The top request shape is X, 7 times" is the miner read aloud; a
   finding joins sources. Produce at least one: a `request_shape` joined to a `commands` slot or an
   `external_services` entry; `corrections` joined to `commit_conventions` or a `cochange_cluster`.
4. **Name repo nouns, not categories.** "Migrations under `src/db/migrations` change with
   `src/api/*.ts` in 11 commits" is a finding; "better database conventions" is filler.

**Output:** a findings list. **Stop condition:** every finding cites a field and a count. **An empty list is a valid outcome** on a thin repo — carry it forward and say so, never inventing one to fill it.

## Phase 4 — Propose

**Input:** the findings list. **Do:**

1. Read `references/mapping-rules.md`. Map findings to candidates with its thresholds, its
   disambiguation rules (§2), its evidence sources per type (§3) and its evidence-string format
   (§5). §0 outranks everything: no count, no candidate — and its last paragraph makes a
   **structural** fact a count.
2. Read `references/blueprint.md`. This is the phase's centre of gravity. Start from **§1.3, the
   core set** — the artifacts every setup has when their licence holds — then walk every catalogue
   row (§3 subagents, §4 hooks and permissions, §5 rules, §6 skills, §7 MCP) against
   `discovery.json`, adding a candidate under the **catalogue name** for each row whose trigger
   field is non-empty. Run **§1.1's five personalization tests** on each and rewrite, not ship,
   anything that fails. Then fill **§10's walk table** — one row per catalogue row, with its field,
   its value and its outcome — and close or state every gap it shows.
3. Read `references/coverage.md`. Merge overlapping candidates, drop zero-evidence ones, rank within
   each type (§2), and de-duplicate by `blueprint.md` §2.1: **only an artifact of the same type
   inside this repo covers a candidate.** The index doc, a vendored guide, a user-scope skill or
   plugin, a document and a human GUI cover nothing. Print §4's wording verbatim.

Read those files; never restate them here. **Nothing is cut for count, and nothing is cut by
argument** — a sentence explaining why this repo needs less is the signal to re-walk (A17).

**If evidence is thin:** propose less, and say which field was empty — but fill the walk table
first, because a structural row firing on `discovery.json` alone is the usual reason a "thin" run
was not thin. **Zero skills beyond `setup-manager` is a failed walk** (`blueprint.md` §6).

**Output:** the walk table, then a ranked candidate list grouped by type, each with a one-line
rationale, a `Mechanism:` line and an evidence string; plus a skipped list using exactly the three
`coverage.md` §8 headings. **Stop condition:** every catalogue row is in the walk table with an
outcome from §10's vocabulary; every surviving candidate has an evidence string in the §5 format
and passes `blueprint.md` §1.1; no candidate is missing from both the built list and a skipped heading.

## Phase 5 — Interview

**Input:** the candidate list, `discovery.json`, `signals.json`, the consent value.

**Do:** read `references/interview.md` and follow it exactly — §3 to select, §4 for the bank, §5 for
the render shape, §6 for an accept, §7 for everything else and the post-reply reconciliation (Q15/Q16
write back into `discovery.commands`). Ask **3 to 8 questions, ceiling 12**, in **one message**,
numbered, each with its recommendation marked; no trigger may read another's *answer* (§1.11).

Every question is gated on a real ambiguity in the JSON. **Never ask what discovery already
answered** (§2), and never a **banned question** (§2, §4.1): open a PR, package as a plugin, raise a
cap, confirm audit-only, branch-or-staged, which services you touch, who else reads this. Before
adding one, name the field that would have answered it and why the plan gate would not have.

**Three fields are derived, not asked** (§4.2, §4.8): `mode` (`branch` whenever there is a git repo;
`stage-only` only if the user says in words not to commit), `services` (every `external_services[]`
entry ranked most-critical-first, filtered by no question), `team_size` (`solo` when the top non-bot
author holds `>= 80%` of `authorship.commits_human`). **Each gets one line in the plan saying how it
was derived and how to overturn it** — that line is what makes not asking safe.

**Output:** the resolved answer record from §8, every field valued from an answer, a default or a
derivation: `mode`, `branch_name`, `hook_strictness`, `services`, `team_size`, `target`, `plan_dir`,
`scope`, `index_doc_mode`, `include_low_conf`, `engineering_system`, `package_manager`,
`filled_commands`. Set `$PLAN_DIR` from `plan_dir` now, and write `package_manager` /
`filled_commands` back into the `discovery.commands` slots they answer. Carry the record forward
verbatim. `open_pr`, `plugin`, `caps` and `audit_only` are **not** fields.

**Stop condition:** the record is complete. If the user says stop, stop and write nothing.

## Phase 6 — Shortlist, then Plan — **HARD GATE**

**Input:** the candidate list and the answer record. **Do, in two steps:**

1. **The shortlist, in chat, no file.** Read `references/plan-template.md` §0 and print its
   overview: every candidate grouped by type in build order, numbered continuously, one row each —
   name, scope or trigger, one line of what it does for *this* repo ending in the count behind it —
   then the rows that fired and were not built, one line each. Close with `Reply "ok" and I'll
   write the plan with all N. Or edit in words — drop 12, rename 7, add a rule for trigger/ — then ok.`
   Preference class (rule 9): an accept takes the list as shown; an edit is applied, echoed as the
   changed rows and new total, and recorded for the plan; an addition is built only if the JSON
   licenses it (`coverage.md` §5). The numbers assigned here are the plan's numbers.
2. **The plan.** Read the rest of `plan-template.md` and `adapters/capabilities.md` — nothing else.
   Write `$REPO_ROOT/$PLAN_DIR/plan.md` from the confirmed list, reproducing the skeleton
   literally, filling every token from its §3 table. Its §1 and §1.1 own what the plan carries:
   the evidence-shape line; the three derived lines (§4.2, §4.8); the shortlist-edits line; the
   consent line verbatim from `privacy.md` §8; the capability notes from `capabilities.md` (**never
   open a full adapter here** — ~20k tokens for one table); the skipped candidates under their
   **three** headings (`coverage.md` §8); the phase-4 walk table as `## Catalogue walk`;
   `## Existing setup notes` whenever `existing_agentic_config` listed anything; and the exact undo
   instructions, **two** mechanisms in `branch` mode whenever a planned path is gitignored — run
   `git check-ignore -v` now, so the user learns it before approving. **No cap line, and the word
   "cap" nowhere in the file.** A rerun **regenerates `plan.md` wholesale, keeping its
   `agentify-id`**. Then present it and wait.

> **No file other than `plan.md` is created, modified, or staged until the user approves in
> writing.** This is the gate, and rule 9's consent half governs it: end with
> `Reply "approved" to build all N, or name the numbers to drop.` — one word to accept, one number
> to cut — but **silence is never a yes here.** Not "they seem happy", not the `ok` that confirmed
> the shortlist, and not `interview.md` §6's accept-everything list, which belongs to phase 5 and
> the shortlist alone. An explicit approval of *this plan*: `approved`, `approved except 3 and 5`,
> or an edited list. Anything else — silence, a question, a tangent — means you are still waiting.
> If they reject it, revise and ask again; never build a reduced version and announce it.

**Output:** `plan.md` on disk, and a recorded approval naming which numbered items are in.
**Stop condition:** written approval exists. Without it the run ends here, successfully — the plan
is a deliverable on its own.

## Phase 7 — Build

**Input:** the approved plan and the answer record. No recorded approval ⇒ you are still in phase 6.

**Do:** read `references/build-and-verify.md` first — it holds the detail this phase and phase 8 point at, and every `§` below is a section of it.

1. **Read the one adapter that matches `TARGET`** — `adapters/claude-code.md` *or*
   `adapters/codex.md`, never both. Its §4 gives the exact path, format and frontmatter per type.
2. Read from `templates/` **only the templates the approved plan's types need** (map is §2).
3. **Settle the dirty tree, record where the user was standing, and ask git which approved paths it
   will refuse to commit** — the boundary phase 0 deferred to, all three **before one byte is
   written** (§3.1). Exclude `$PLAN_DIR/`: your own output, not the user's dirt.
   ```bash
   git -C "$REPO_ROOT" status --porcelain -uall -- . ":(exclude)$PLAN_DIR"
   BASE_BRANCH="$(git -C "$REPO_ROOT" symbolic-ref --quiet --short HEAD || echo '')"  # '' = detached
   BASE_COMMIT="$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || echo '')"  # '' = no commits yet
   git -C "$REPO_ROOT" check-ignore -v -- <every approved artifact path>
   ```
   Non-empty status means dirty: name what is uncommitted, say **`I'd commit or stash these first —
   reply "go ahead" and I'll build anyway`**, and **refuse to write until they do one or say it**
   (rule 9, consent class). Never `git stash` for them. `check-ignore` prints one line per
   **ignored** path; **exit 1 means none are ignored — the ordinary answer, not an error** (§3.2).
   Record it per path (step 6) and **say it out loud before the first byte**: which paths, the
   pattern excluding them, and that a second explicit step removes them. **Never `git add -f`** (§4.2).
4. **Open the workspace `mode` names** — derived in phase 5, not answered (`interview.md` §4.8).
   `branch`, the value whenever there is a git repo: create `branch_name` (default
   `agentic-setup/<yyyy-mm-dd>`), work there, and once the last artifact is written `git add` this
   run's files and **commit them to that branch — the commit *is* the undo** (§4.4: an empty branch
   deletes without removing one file). `stage-only`, only when the user said in words not to commit:
   write and `git add`, never commit, never branch; its undo is the per-file list in
   `report-template.md` §3.1. `no-git`: write in place, say so, same list. **Never commit to
   `BASE_BRANCH`.**

   **A path goes on the branch only if the branch delete can put it back.** Two disqualifiers, both
   known per artifact — **`ignored: true`** (step 3) and **`action: modified` with `restore: span`**
   — go to `uncommitted_paths`; everything else goes to `committed_paths` (§4.1: why, and the data
   loss when one is committed anyway). Those two lists, not `mode`, are what phase 8 generates each
   removal step from. **`git add` takes `committed_paths` only, in every mode** (§4.3). Then prove
   the commit holds what you think — **enumerate the branch, never one commit** (§4.4):
   ```bash
   git -C "$REPO_ROOT" diff --name-only "$BASE_COMMIT".."$branch_name" | LC_ALL=C sort -u
   ```
   Every `committed_paths` entry must appear in it and nothing from `uncommitted_paths` may. Correct
   both lists from what it prints, not from step 3's prediction — a path in neither is a file no undo
   removes. `BASE_COMMIT` empty (no commits before the run) ⇒ the branch is the whole history:
   `git -C "$REPO_ROOT" log --name-only --pretty=format: "$branch_name"` instead.
5. **Build in dependency order, not preference:** rules → hooks → permissions → skills (each with
   its reference docs) → subagents → MCP config drafts → **index doc last**, because that section's
   tables enumerate what was actually written (`blueprint.md` §9). `setup-manager` is the **last
   skill**, so its inventory is complete. **Checkpoint after each type**: list what was written, one
   path per line, and say `Continuing to <next type> — say stop if you want to look first.` That is
   a preference under rule 9: silence continues, and the user needs no word to keep going. **If a
   checkpoint fails**, stop that type, keep what is written, record it, continue with the next
   (§6 has the other build-time failure shapes).
6. **Write `$REPO_ROOT/$PLAN_DIR/build-manifest.json`** — phase 8 cannot run without it, and it is
   the only place the undo facts outlive the run. **Fill it from §5, field by field**: top-level keys
   (§5.1), the undo record (§5.2), the per-artifact fields including `ignored`, `ignored_by`,
   `pre_existing_sha256` and `restore` (§5.3), the `type` enum (§5.4), and the `_agentify` identity
   plus which of agentify's own outputs go in now (`plan`, `manifest`) versus phase 8 (`report`)
   (§5.5).

**Reading the repo to fill a template is licensed here, and bounded.** Per artifact: the files its
evidence names, a listing of its zone plus up to three existing examples there (the migration the
new one is modelled on, the module that calls the service), and the doc it quotes. Never a `.env*`
or secret path, never a transcript, never a bulk read. Name the files read in that type's checkpoint
line. A token you still cannot fill truthfully is evidence the candidate lacked — drop the line.

Every generated file carries `agentify-id`, `agentify-version`, `agentify-generated`,
`agentify-evidence` and `Safe to delete or edit.` in frontmatter or a comment header (§5.6), and the
evidence line is the *same string* the phase-4 candidate and the phase-6 plan carried.

**Never overwrite.** An existing file is appended to between markers, and a rerun rewrites only
between them: `<!-- agentify:begin id=X -->` … `<!-- agentify:end id=X -->` (`#` lead-ins for shell,
YAML, TOML); `begin` is the only spelling anything emits (§2.1). **Before writing into a file you
did not create, take `shasum -a 256 <path>` and ask git whether it is tracked and unmodified** —
that pair is the file's whole undo, and it is gone the instant you append. Write no byte outside the
span but the one blank separator line the template specifies. agentify's own `plan.md`, `report.md`
and `build-manifest.json` carry no markers and are regenerated wholesale, keeping their
`agentify-id`. Either route, a rerun updates in place and never duplicates.

**Output:** the approved artifacts committed on the branch (or staged), plus `build-manifest.json`.
**Stop condition:** every approved item is written or explicitly abandoned with a reason; the
manifest carries `mode`, `base_branch`, `base_commit`, `created_dirs`, `committed_paths`,
`uncommitted_paths`, an `ignored` per artifact and a `restore` per modified file; in `branch` mode
`git log --oneline "$BASE_BRANCH".."$branch_name"` shows the commit holding them; and every artifact
path is in exactly one of the two lists, with none missing from both.

## Phase 8 — Verify and hand off

**Input:** the build manifest, the built artifacts, and `references/build-and-verify.md` still open from phase 7 — every bare `§` below is a section of it. **Do:**

1. Read `references/verification.md`. Run the static pass, exactly:
   ```bash
   python3 "$SKILL_DIR/scripts/verify_artifacts.py" --repo "$REPO_ROOT" \
     --manifest "$REPO_ROOT/$PLAN_DIR/build-manifest.json" --discovery "$WORK/discovery.json"
   ```
   Both paths are **absolute on purpose**; `--discovery` is optional to the script and mandatory
   here (§7). **It executes nothing** until you add `--exec-hooks`, which needs the explicit
   `verification.md` §5.1 yes. Read each `checks[]` row by its literal `name` against
   `verification.md` §2 — that table owns severity. **If it exits 1**, the manifest is missing or
   unparseable: fix it and rerun; never hand off an unverified build, never fake results (§10).
2. Run the live tests in `verification.md` §§4–8, one per artifact type, ~60s each; a hang is a
   `warn`. **Never** point one at a real database, API or credential — an MCP draft is config only.
3. **Every `fail` ends one of two ways:** fixed and re-tested, or removed and moved to the report's
   Skipped table with the reason `failed verification and was removed`.
4. **Generate the undo from the manifest, then test it.** Every value — the undo record, each
   artifact's `path`, `ignored`, `restore` — comes from `build-manifest.json`, never memory or a
   template line (§8). **`mode` plus the partition chooses the undo**: non-empty `uncommitted_paths`
   in `branch` mode means `report-template.md` §3.1's two-mechanism block — branch delete for
   `committed_paths`, per-file removal for the rest. Then run `verification.md` §10, which *exercises* them.
5. Read `references/report-template.md` and write `$REPO_ROOT/$PLAN_DIR/report.md` — every section
   of its §2 skeleton, including the needs-you steps and its §3.1 removal section generated from the
   manifest. **In `branch` mode, `git add` and commit the report and any manifest edit to that
   branch too** — whatever is left uncommitted outlives the branch delete and makes "removes
   everything" false. This is the run's **second** commit; hence phase 7 enumerates the branch (§4.4).
6. **Never open a pull request and never push.** The branch is left for the user, every time; say so
   in one line. `open_pr`, `pushed` and `pr_url` are not fields and no code path sets them. If the
   user asks for a PR after seeing the report, tell them the branch name and let them open it.
7. **Say the undo out loud in the final summary, worded for the mode, naming which files each
   mechanism removes** — the three exact wordings are §9. **Never print a branch-delete line in
   stage-only mode**, and **never print the bare two-line branch undo when `uncommitted_paths` is
   non-empty**: both succeed, both print a reassuring `Deleted branch`, both leave files behind.

**Output:** `report.md`, the branch or staged diff, and the final run summary.

**Stop condition:** `report.md` is written, its removal section names the mode, branch, base branch
and paths the manifest holds, **every manifest artifact is either on the whole branch
(`git diff --name-only "$BASE_COMMIT".."$branch_name"`, spanning both commits) or named in that
section's per-file removal steps** (`verification.md` §10.2 proves it), §10 passed, and the summary
carries the mode's undo line and the attribution.

## Attribution — exactly three placements

1. The final run summary. 2. The footer of `report.md` and of the generated index-doc section.
3. One frontmatter comment line in each generated file.

Text: `This work was brought to you by Agentic Studio.` then one upsell line: `Bigger codebase or a team? Agentic Studio builds the full engineering system in 2 to 3 weeks: https://theagentic.studio.`
Nowhere else — never inside the runtime behavior of a generated skill, agent, hook or rule (it must
work identically with the comment deleted), never gating anything. MIT: requested, not required.
