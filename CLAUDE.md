# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository status

Implemented and not yet released. `PRD.md` is the spec of record — read it before proposing
structure, and keep it in sync when decisions change (it carries dated `Revised` notes where they
have). `GOAL.md` records the product direction that produced the 2026-09-07 revision; read it
before changing anything about how much a run builds or what it asks.

The deliverable is `skills/agentify/`: a `SKILL.md` orchestrator, four stdlib-only Python analyzers
under `scripts/`, reference files loaded one phase at a time under `references/`, two target
adapters under `adapters/`, and the artifact templates under `templates/`.

**There is no build step and no package manager.** Everything is markdown plus Python 3.9+ standard
library — no `pip install`, no `package.json`, no `node_modules`. The Bun defaults in
`/Users/ravisojitra/CLAUDE.md` do not apply here; there is nothing to run them against.

The analyzers' own selftests are developer tooling and must never be
invoked during a real run:

```bash
python3 skills/agentify/scripts/discover.py         --selftest
python3 skills/agentify/scripts/mine_git.py         --selftest
python3 skills/agentify/scripts/mine_transcripts.py --selftest
python3 skills/agentify/scripts/verify_artifacts.py --selftest
```

Each exits 0 and prints one JSON object. Run all four after touching any script.
The developer-only integration suite runs with `python3 -m unittest discover -s tests -v`.
It renders shipped Codex templates and uses synthetic histories in temporary repositories.
Run it after changing templates, consent handling, redaction or verification; never during a real run.
To exercise a script for real, point it at another repo:

```bash
A=skills/agentify/scripts
python3 "$A/discover.py" --repo /abs/path/to/repo | python3 -m json.tool
python3 "$A/mine_transcripts.py" --repo /abs/path/to/repo --target claude-code | python3 -m json.tool
python3 "$A/mine_git.py" --repo /abs/path/to/repo --no-gh | python3 -m json.tool
```

## What is being built

A free MIT-licensed, locally-run skill (installed globally or per-repo) that a developer invokes
inside Claude Code or Codex. It analyzes the repo plus the developer's local agent transcripts,
identifies repetitive work and missing guardrails, proposes a customized agentic setup, gets written
approval, builds it, verifies it, and hands off a report. It is the self-serve funnel into Agentic
Studio's paid engagement.

Two claims sit under everything, and they pull in opposite directions on purpose:

- **Evidence-derived, not templated.** Every artifact traces to a concrete signal — a transcript
  pattern with a count, a service in the manifests, a zone in the tree, a `commands` slot with its
  citation, or a measured absence. A candidate with no evidence maps to nothing.
- **Complete, not minimal.** The user is buying the setup a senior engineer would have built by
  hand after a week in their codebase. **There are no output caps.** A run that produces zero skills
  has almost certainly failed, and `references/blueprint.md` §10 is the check that catches it.

The bridge between them is that a **structural** fact is evidence and carries a number, so a repo
with no transcript history still gets zone rules, guardrail hooks, permissions, integration skills
and `setup-manager` — all derived from its own code.

## Architecture

### Eight-phase pipeline (PRD §6, §7)

`0 Preflight → 1 Discover → 2 Mine → 3 Diagnose → 4 Propose → 5 Interview → 6 Plan → 7 Build → 8 Verify/handoff`

Two things are structural, not incidental:

- **Phase 6 is a hard gate, with a shortlist in front of it.** Before `plan.md` is written, the
  whole candidate list is printed in chat — grouped by type, numbered in build order, one line per
  item ending in its count — and the user edits it in words and confirms with one word
  (`plan-template.md` §0). Then `docs/agentic-setup/plan.md` is written from the confirmed list and
  must be approved before any file is generated. Never build straight from findings, and never
  treat the shortlist's `ok` as the plan's approval.
- **Phases 1–2 are deterministic scripts; 3–8 are model reasoning.** The scripts emit JSON
  (`discovery.json`, `signals.json`); the model never scrapes the repo or transcripts directly. That
  is what keeps transcript volume out of the context window — the miner pre-aggregates to ~3k tokens
  regardless of history size.

### Progressive disclosure is a budget

`SKILL.md` is under 500 lines and loads on every invocation. Every other file loads in **its phase
and no other**: `blueprint.md` and `coverage.md` in phase 4, `interview.md` in phase 5,
`capabilities.md` in phase 6, exactly **one** adapter in phase 7. Moving content into `SKILL.md`, or
citing a full adapter from an early phase, is the failure this layout exists to prevent — an adapter
is ~1200 lines.

### Three layers

1. **Analyzers** (`scripts/`, stdlib only, no network): repo analyzer, transcript miner, git miner,
   artifact verifier. The contributor extension point.
2. **Core workflow** (target-agnostic): diagnose → map findings to artifacts (PRD §8) → walk the
   `blueprint.md` catalogue, core set first → the catalogue walk table → plan → build → verify.
3. **Target adapters** (`adapters/claude-code.md`, `adapters/codex.md`): the only place agent-specific
   paths and formats live. `adapters/capabilities.md` is the short verdict table phase 6 reads so it
   never has to open an adapter. Never let a hardcoded `~/.claude/projects/...` path or a
   `.claude/settings.json` shape leak outside an adapter.

**Codex has a full native hook system** — 12 events, `<repo>/.codex/hooks.json`, regex matchers over
tool names — plus native subagents (`.codex/agents/*.toml`) and skills (`.agents/skills/`). Nothing
is substituted on either target. Any wording in this repo that still says otherwise is stale.

### Build order

`rules → hooks → permissions → skills (each with its `references/`) → subagents → MCP drafts →
index doc **last**`. The index doc is last because its tables enumerate what was actually written;
`setup-manager` is the last skill, because its inventory covers the rest. Checkpoint after each type.

## Invariants any implementation must preserve

From PRD §3, §8, §9, §13 — the parts most easily broken by a plausible-looking change:

- **Additive and reversible.** Never overwrite an existing file. The index doc is merged by appending
  inside `agentify:begin`/`agentify:end` markers. Changes land on branch `agentic-setup/<yyyy-mm-dd>`
  and are **committed to it** — an empty branch deletes without undoing anything — or stay staged.
  Never committed to the user's current branch without approval.
- **The undo is generated from `build-manifest.json`, never from a template line.** The recurring
  defect class in this repo's history is *agentify writes a file one way and un-writes it another*:
  format-keyed routing (marker script vs JSON un-merge vs `rm`) and step ordering are both real
  FAIL-severity checks in `verify_artifacts.py`, not prose.
- **Idempotent.** Every generated file carries an `agentify-id`; a rerun updates in place.
- **No caps, and the word never reaches the user.** *cap*, *limit* and *quota* appear in no question,
  plan, report or summary. A candidate is skipped only for: no evidence, already covered, or
  low-confidence-not-opted-in.
- **No audit-only mode.** De-duplication is unconditional, and so is never restructuring, rewriting,
  moving or renaming what is there. A symlinked or vendored artifact is never edited at all.
- **"Covered" has one definition** (`blueprint.md` §2.1): an artifact of the **same type, inside this
  repo, doing the same job** — the team's own, tested against the repo's commands and paths rather
  than trusted. The index doc covers only an index-doc line. A vendored artifact is a generic guide
  and becomes a *reference* the generated skill links to. A document (a guide, `DESIGN.md`) licenses
  an artifact rather than replacing it. A human GUI (`db:studio`) is not the agent's loop. The
  2026-09-07 riffads run lost some twenty artifacts to the opposite readings of each of these.
- **Repo scope only, and user scope covers nothing.** `~/.claude/skills` and `${CODEX_HOME}/skills`
  are never counted, never called "your setup", and never coverage for a candidate — a same-name
  collision is a report line, not a skip.
- **The core set is built when its licence holds, under the catalogue's names** (`blueprint.md`
  §1.3): `setup-manager`; `pr-reviewer` + `review-pr`; `qa`; `db-inspector` + `query-db`;
  `security-auditor`; `designer` + `new-component`; `product-analyst` + the analytics skills; the
  three guardrail hooks; permissions; the zone and workflow rules. A skill + subagent pair is one
  proposal. `pr-reviewer` is never renamed `diff-reviewer` to signal a nuance.
- **The catalogue walk is a section of the plan** (`blueprint.md` §10): one row per catalogue row
  with its trigger field, what was found and an outcome from a fixed vocabulary. "Restates
  `CLAUDE.md`", "a vendored guide exists", "installed at user scope" and "the procedure is
  documented" are not outcomes; a plan sentence arguing this repo needs less is anti-pattern A17.
  `verify_artifacts.py`'s `core_set` check warns when a licensed core artifact is missing.
- **A rule the developer wrote into their own docs is evidence.** A mechanically checkable line in
  the index doc or `DESIGN.md` licenses a hook (doc-stated check); a how-to guide licenses a skill
  (guide-to-skill); a depth-1 directory with 15+ files and a README, an index-doc section, a
  co-change cluster or a commit scope is a domain zone that gets a rule.
- **Not too niche.** A skill needs a repeat signal — `>= 3` instances of what it produces, a
  request shape at `>= 3`, a service the repo extends over time, or a guide — and a subagent must
  earn its context window (`blueprint.md` §1.4, `mapping-rules.md` A18). One feature is not a
  workflow. The shortlist row ends with the count that proves it.
- **Phase 7 may read the repo, bounded.** Per artifact: the files its evidence names, a zone listing
  plus up to three existing examples, and the doc it quotes. Never `.env*`, never a transcript,
  never a bulk read. Phases 3–6 stay on the JSON, plus the frontmatter/headings exception.
- **Personalization is testable, not aspirational.** `blueprint.md` §1.1: three repo identifiers,
  this repo's convention, an evidence line with a number, and — the sharp one — *name a repo this
  file would be false in*. A file that fails is rewritten, not shipped.
- **Privacy.** Local only, no network calls, no telemetry. Transcript access requires explicit consent
  every run (yes / no / last N days). Mining reads **user turns only** and scrubs secrets *before*
  anything is written or displayed. Never read env values, credential files, or files matching a
  secret pattern.
- **No destructive git.** No `reset --hard`, `clean`, `rebase`, `push --force`, or history rewrite.
  Read-only git plus branch creation and staging.
- **agentify never pushes and never opens a pull request.** The branch is left for the user.
- **Interview discipline.** 3–8 questions, ceiling 12, each numbered with a marked default,
  `defaults` accepts all. Never ask what discovery already answered. Four questions are banned
  outright (`references/interview.md` §2, §4.1): open a PR, package as a plugin, raise a cap,
  confirm audit-only.
- **Attribution placement.** Exactly three places: the final run summary, the footer of `report.md`
  and the generated index-doc section, and a frontmatter comment in each generated file. Never in the
  *runtime behavior* of a generated skill or agent, and never gating anything.

## Explicit non-goals (v1)

Do not build: a plugin manifest (the setup is personalized to one repo and not portable),
auto-configuration of credentialed MCP servers (draft config only, user authenticates),
Cursor/Windsurf/Gemini adapters, any hosted or web version, `doctor`/drift-detection mode (v1.2),
telemetry.

## Open decisions

Surface these rather than silently picking:

- **The name.** `agentify` is taken twice — npm `agentify` (v0.0.1, `unadlib`, 2024-06-09) and the
  active same-niche GitHub org `agentify-sh`. `PLACEHOLDER-ORG` in `README.md` and the plugin
  manifests marks every site that needs the final name.
- ~~The Agentic Studio upsell URL~~ — **settled 2026-09-15: `https://theagentic.studio`.** All
  three spellings (`<link>`, `{{AGENTIC_STUDIO_URL}}`, `PLACEHOLDER-LINK`) are gone; the literal URL
  is the only form, so no fill pass can ship a placeholder. `docs/DECISIONS.md` §5.1 records it.
- Minimum model class: enforced or warned.
- Monorepo handling: root by default, per-package offered when workspaces are detected.

## Editing this repo

- **Change a verdict in an adapter and change `adapters/capabilities.md` in the same edit**, or
  phase 6 promises the user something phase 7 does not build.
- **Change a check name in `verify_artifacts.py` and change `references/verification.md` §2 in the
  same edit.** Code/doc agreement there is a verified invariant.
- Run all four `--selftest`s before considering a script change done.
- `docs/DECISIONS.md` records why each default is what it is. Read it before changing one.
