# PRD: Agentic Setup Skill (working name: agentify)

Owner: Ravi, Agentic Studio
Status: Draft v0.1
Date: 4 September 2026

---

## 1. Summary

A free, open-source skill that a developer installs globally or in a repo. When invoked inside Claude Code or Codex — **both ship in v1** — it analyzes the codebase and the developer's local chat history with the agent, identifies repetitive work and missing guardrails, proposes a customized agentic setup (rules, hooks, permissions, skills, subagents, MCP config drafts, and the index-doc section that ties them together), gets the developer's approval on a written plan, builds it, verifies it, and hands off with a report.

**Revised 2026-09-15.** Two claims were removed from the sentence above, both of which this document
contradicted elsewhere. *Plugin packaging* stood inside the enumeration of what the setup contains,
which reinstated a retired artifact type: no run emits a plugin manifest on either target (§7.6's
banned question, §7.8's build order, §8's 2026-09-07 note removing the row, §11.1). *Codex (v1.1)*
placed Codex after v1.0; the Codex adapter ships **in v1**, fully supported, with nothing substituted
on it (§11.2, §15).

It is the self-serve entry point to Agentic Studio's "Claude Engineering System" service. The tool does a credible 20-minute version of what the agency does in 2 to 3 weeks, and every run ends with attribution and a link.

## 2. Problem

Most developers using Claude Code or Codex have a thin or empty CLAUDE.md / AGENTS.md, no skills, no hooks, and re-type the same instructions every session. The tooling exists but the setup cost is high and nobody knows what a good setup looks like for their specific repo. Generic templates don't fit. The evidence of what they need already exists in their transcripts and git history, unused.

## 3. Goals

1. Produce a setup that is specific to the repo, not a template. Every generated artifact must trace back to evidence (a transcript pattern, a script, a convention, a dependency).
2. Be safe to run on any repo: additive, reviewable, idempotent, reversible.
3. Finish in one sitting (target under 30 minutes wall-clock including the interview).
4. Generate qualified inbound leads for Agentic Studio.
5. Be extensible by contributors: new analyzers, new artifact emitters, new targets.

## 4. Non-goals (v1)

- Auto-configuring MCP servers that need credentials. The tool recommends and drafts config; the user authenticates.
- Cursor, Windsurf, Gemini CLI, or other targets. Claude Code and Codex both ship in v1 (§11); nothing else does.
- Hosted or web version. Runs entirely locally inside the agent.
- Ongoing monitoring or drift detection ("doctor" mode). Roadmap.
- Telemetry. None by default.
- Replacing an existing setup. Existing artifacts are read to de-duplicate against and are never restructured, rewritten, moved or renamed; a symlinked or vendored one is never edited at all. (This used to be a mode triggered at 5+ existing skills; it is now unconditional — §9.)

## 5. Users

Primary: solo developers and small teams (1 to 8 engineers) already using Claude Code or Codex daily, with a repo of 2k to 200k lines and at least a few sessions of history.

Secondary: developers with a fresh repo and no history. The tool still works from code and dependencies alone, with a smaller output and a note that results improve after a week of usage.

Not a target: enterprises with existing platform teams (they are the paid engagement).

## 6. Solution overview

The skill forces the model through eight phases. Each phase has a defined input, output, and stop condition.

| Phase | What happens | Output |
|---|---|---|
| 0. Preflight | Detect target (Claude Code / Codex), repo root, existing agentic config, model class. Ask consent for transcript access. | Preflight summary |
| 1. Discover | Scan repo: languages, frameworks, package scripts, Makefile, test/lint config, folder structure, env var names (never values), CI config, existing docs. | `discovery.json` (internal) |
| 2. Mine | Run the transcript miner and git miner scripts. | `signals.json` (internal) |
| 3. Diagnose | Model reads discovery + signals and identifies: repetition, corrections, friction, missing guardrails, external systems. | Findings list with evidence |
| 4. Propose | Map findings to artifacts (section 8), walk the setup catalogue against the repo — core set first — apply the personalization test, and fill the catalogue walk table (section 9). | Catalogue walk + candidate list |
| 5. Interview | Ask the user numbered questions only where evidence is ambiguous. Sensible defaults, "accept all defaults" option. | Answers |
| 6. Plan | Write `docs/agentic-setup/plan.md`. User approves, edits, or rejects items. Hard gate. | Approved plan |
| 7. Build | Generate artifacts in dependency order on a branch. Checkpoint after each group. | Files on branch |
| 8. Verify and hand off | Smoke test each artifact, write the report, show attribution and upsell. | `docs/agentic-setup/report.md`, plus the branch or the staged diff — **never a pull request** (§7.6, §7.9) |

## 7. Detailed requirements by phase

### 7.1 Preflight

- Detect target by which agent is running the skill. If ambiguous, ask.
- Detect existing agentic config: `CLAUDE.md`, `.claude/`, `AGENTS.md`, `.codex/`, `.cursorrules`, `.cursor/rules`, `.github/copilot-instructions.md`. Classify as none / basic / mature.
- An existing setup, at any size: de-duplicate against all of it, propose additions and fixes, never restructure. Report what is already there in one line of context; do not let it reduce what is built (§9).
- Transcript consent: explain what will be read (user prompts only, from local session files for this repo), that a script pre-processes and scrubs them, and that nothing is uploaded beyond what the agent already sees. Options: yes / no / yes but only last N days.
- Model class check: warn if running on a small model that the plan quality will be lower.
- Confirm git is clean or offer to stash. Refuse to proceed on a dirty tree without explicit override.

### 7.2 Discover (repo analyzer)

A script (Node or Python, no external deps beyond stdlib where possible) that emits structured JSON. Must complete in under 10 seconds on a 200k-line repo. Collects:

- Languages and frameworks (from manifests, not file extensions alone)
- Package manager and scripts (`package.json`, `Makefile`, `justfile`, `pyproject`, etc.)
- Test, lint, format, typecheck commands and whether they currently pass
- Folder map to depth 3 with file counts, flagging conventional zones (api, db, migrations, components, tests, routes, actions, jobs, lib, hooks, state, types), with up to six sample basenames and eight subdirectory names per folder so the naming convention of a zone (`0001_init.sql`, `(protected)`) is read off the tree rather than guessed. Anything under a dot-directory other than `.github` is never a zone.
- External services: from dependencies, env var names and marker files (Stripe, Supabase, Neon, Linear, PostHog, Sentry, Playwright, and since 2026-09-07 the job runners, non-Stripe billing, model providers, storage, realtime and notification services — Trigger.dev, Inngest, Dodo, Lemon Squeezy, fal, OpenRouter, ElevenLabs, R2, Cloudinary, Pusher, Novu, …)
- Existing docs: README, CONTRIBUTING, ADRs, PR template, issue templates, and three kinds the catalogue reads by name — `design` (a `DESIGN.md`-shaped doc), `context` (a root `CONTEXT.md`), `guide` (anything under `docs/guides/` or titled "adding-…" / "how-to-…")
- Tooling on `PATH`, by name only (`agent-browser`, `gh`, `playwright`, `psql`, …): environment evidence for a generated skill's driver choice, never repo evidence, nothing executed
- CI workflows and what they run
- Git basics: age, contributor count, commit volume in last 90 days

Never reads env values. Never reads files matching secret patterns.

### 7.3 Mine (transcript and git miners)

Transcript miner:

- Locates session files for this repo (Claude Code: `~/.claude/projects/<encoded path>/`; Codex: its local sessions directory). Paths must be verified against current agent docs at build time and isolated in an adapter.
- Extracts user turns only. Drops tool output and assistant turns except for detecting corrections (a user turn following an assistant action that contains "no", "don't", "we use", "always", "never", "stop").
- Scrubs secrets with standard patterns (API keys, tokens, JWTs, connection strings) before anything is written or shown.
- Clusters prompts by normalized shape (strip file names, numbers, quoted strings) and reports: top 20 recurring request shapes with counts and example phrasing, recurring commands, corrections, and prompts that mention tools or services.
- Output is a compact report capped at roughly 3k tokens regardless of transcript volume.

Git miner:

- Commit message conventions (conventional commits, ticket prefixes)
- Files that change together (co-change clusters), which suggest path-scoped rules
- Churn hotspots
- PR title and body patterns if a remote and `gh` are available

### 7.4 Diagnose

The model produces a findings list. Each finding has: type (repetition / correction / guardrail gap / convention / external system), evidence (what produced it, with counts), and confidence (high / medium / low). Low-confidence findings are shown but not built unless the user opts in.

### 7.5 Propose

Apply the mapping rules (section 8), then walk the setup catalogue — starting from the **core set** (`setup-manager`, `pr-reviewer` + `review-pr`, `qa`, `db-inspector` + `query-db`, `security-auditor`, `designer` + `new-component`, `product-analyst` + the analytics skills, the three guardrail hooks, permissions, the zone and workflow rules), then every other subagent, hook, rule, skill and MCP row — against the repo, adding a candidate under the catalogue's own name for every row whose trigger field is non-empty. Run the personalization test on each one and rewrite anything that fails it. Then produce the **catalogue walk**: one table row per catalogue row with its trigger field, what was found, and an outcome from a fixed vocabulary (`built #N`, `not licensed — <field> is <value>`, `covered by <same-type artifact in this repo>`, `skipped — <one of the three reasons>`, `merged into #N`). The walk is the phase's first output and the plan's last section. De-duplication has one definition: **an artifact of the same type, inside this repo, doing the same job.** The index doc, a vendored guide, a user-scope skill or plugin, a document and a human GUI cover nothing. Output the walk, then a candidate list grouped by artifact type, each with a one-line rationale, a mechanism sentence and an evidence reference. **Nothing is cut for count, and nothing is cut by argument** — a plan sentence explaining why this repo needs less is the signal to re-walk.

### 7.6 Interview

- Ask only what evidence can't answer. Target 3 to 8 questions. Hard cap 12.
- Numbered, each with a default marked. User can reply "defaults" to accept all.
- Typical questions: branch or stage-only, whether generated hooks block or warn, which external systems are actually in daily use, team shape, target agent if both are detected, whether they run a packaged engineering workflow (compound engineering, superpowers) the setup should sit inside, which package manager the repo really uses when the lockfiles disagree, and any command slot discovery could not resolve.
- Never ask something the discovery already answered (package manager, framework, test command).
- **Four questions are banned outright** (revised 2026-09-07): offering to open a pull request — agentify never opens one and never pushes; offering to package the setup as a plugin — it is personalized to one repo and not portable; offering to raise a cap — there are none; and confirming audit-only mode — there is none.

### 7.7 Plan

**First, the shortlist — in chat, before any file.** Print every candidate grouped by type in build order, numbered continuously, one row each: name, scope or trigger, and one line saying what it does for this repo ending in the count behind it (`· 15 tasks in trigger/tasks/`), plus the rows that fired and were not built, one line each. The user drops, adds, renames or modifies in plain words and confirms with one word; an addition is built only if the evidence licenses it. The numbers assigned here are the plan's numbers, and every edit becomes a line in the plan's summary. Then write `docs/agentic-setup/plan.md` from the confirmed list, with:

- Summary: what will be built, count by type, estimated build time
- Per artifact: name, type, purpose, evidence, files it will create or modify, what it will not do
- Files that will be modified vs created (modifications always show a diff preview)
- Capability notes for the target (e.g. Codex project trust gates the repo-scoped artifacts; here is what the user must do)
- Explicitly skipped candidates and why

User reviews. Accepts, removes items, or edits. Build does not start without approval — the word that confirmed the shortlist is not the approval of the plan. The plan file stays in the repo as a record.

### 7.8 Build

- Create branch `agentic-setup/<yyyy-mm-dd>` (or stage-only mode if the user prefers).
- Build order: rules → hooks → permissions → skills (each with its own `references/`) → subagents →
  MCP config drafts → **index doc last** (`CLAUDE.md` / `AGENTS.md`). **Revised 2026-09-15:** this
  line previously put the index doc *first* and ended with a plugin manifest, contradicting §9 and
  §7.9 in the same document. The index doc is last because its tables enumerate what was actually
  written — an earlier build order produced rows linking to files that did not exist yet — and
  `setup-manager` is the last skill, because its inventory covers the rest. No plugin manifest is
  emitted on either target (§9).
- Each generated file starts with a frontmatter comment: generated by, date, evidence summary, "safe to delete or edit".
- Existing files are never overwritten. CLAUDE.md is merged by appending a clearly delimited section, or by proposing a rewrite the user approves separately.
- Idempotency: generated files carry an ID. Rerunning updates in place, never duplicates.
- Checkpoint after each type: show what was written, continue or stop.

### 7.9 Verify and hand off

- Skills: invoke each on a real small task derived from the repo. Pass if the skill produces a plausible result without errors.
- Hooks: run each once against a fixture. Confirm they don't block normal work.
- Rules: check for contradictions with each other and with discovered conventions.
- Subagents: dry-run with a trivial prompt to confirm they load.
- Write `docs/agentic-setup/report.md`: built, skipped, needs-you (MCP auth steps), first three things to try tomorrow, and how to remove everything (delete branch or listed files).
- Leave the branch and print the summary. **agentify never pushes and never opens a pull request**
  (§7.6 bans offering to, and §3 makes it an invariant). **Revised 2026-09-15:** this line previously
  said to open a PR when `gh` was available and the user agreed, which contradicted both. Phase 8 has
  no PR step and `open_pr` is not a field. **Corrected again, same day:** the first repair kept a
  "push-access question" that no longer exists — the ladder behind it (`gh auth status`,
  `gh repo view --json viewerPermission`) went with Q2, and `mine_git.py` contains no push-access
  check; `gh` survives read-only in exactly one opt-in place, `pr_patterns`' `gh pr list`, which
  phase 2 disables with `--no-gh` (`docs/DECISIONS.md` §2.27, `references/interview.md` §Q2).
- Attribution and upsell (section 10).

## 8. Mapping rules (finding → artifact)

| Finding | Artifact | Example |
|---|---|---|
| Multi-step procedure the human triggers repeatedly | Skill | "Add a new API endpoint with validation, tests, and docs" asked 7 times |
| Work needing isolated context, a specialist persona, or parallelism | Subagent | PR reviewer, migration planner, test writer, research agent |
| Deterministic check that shouldn't depend on the model remembering | Hook | Run typecheck before commit, block secrets, format on write |
| Convention tied to specific paths | Path-scoped rule | "All DB access goes through repository layer in `src/db/`" |
| Correction the user made 2+ times | Rule (global or scoped) | "Use bun, not npm" |
| External system in daily use | MCP recommendation with draft config | Linear, PostHog, Neon, Sentry, Playwright |
| Long-form knowledge the model keeps rediscovering | Solution doc / reference file | "How auth flows through middleware" |
| Commands the user keeps approving by hand, and paths that must never be read | Permissions allow / ask / deny | Pre-approve `bun run test`; deny reads of `.env.local` |
| A zone in the tree with a stateable convention | Path-scoped rule, one per zone | `db/`, `app/api/`, `components/` |
| An exposure the repo has no protection for | Hook | A `.env*` on disk and zero hooks; two lockfiles and no package-manager enforcement |
| A service the repo actually integrates | Skill, plus a subagent where tool restriction matters | Linear → `create-issue`; PostHog → `add-product-analytics`, `ask-product`; Neon → a read-only `query-db` skill over a `db-inspector` subagent |
| The setup this run just built | `setup-manager` skill | Creates, extends, modifies and removes any part of the setup on request |
| A procedure the developer already wrote down | Skill (guide-to-skill / dev-environment) | `docs/guides/adding-a-capability.md` → `add-capability`; `db:push:local` → `db:seed` → `db:seed:catalog`, ordered by the index doc's own comment → `seed-local` |
| A mechanically checkable rule in the repo's own docs | Hook (doc-stated check) | `DESIGN.md` bans raw hex, `lucide-react` and `h-screen` → a `PostToolUse` grep; `CLAUDE.md` says "always work on `development`" → a branch guard |
| A domain directory with a stateable convention | Path-scoped rule | `server/generation/` (187 files, its own guide), `trigger/` (its own README), `app/` (route groups) |

A finding can map to more than one artifact (a procedure becomes a skill and its final check becomes a hook). A finding with no evidence count maps to nothing — and a **structural** fact carries a count too: a service with its confidence, a zone with its file count, a command with its manifest citation, and an absence such as zero hooks in a repo holding `.env*` files.

**Revised 2026-09-07.** The plugin-manifest row is removed: the setup is derived from one repo's evidence and personalized to it, so a portable copy would be wrong wherever it landed. Rows 12 to 16 above are new, and are what makes a run on a repo with no transcript history still produce a real setup. **Revised again the same day** after a run on that repo built 16 artifacts and skipped some twenty: the last three rows were added, and a **core set** was named — the artifacts every setup has when their licence holds, built under the catalogue's own names (`pr-reviewer`, never `diff-reviewer`), and never skipped as "covered" by anything but an artifact of the same type inside the repo.

## 9. Coverage — **revised 2026-09-07, replacing the sizing-cap table**

**There are no caps.** agentify proposes the complete setup the evidence supports; the user cuts what they do not want at the phase 6 gate. The words *cap*, *limit* and *quota* never appear in the tool's output. A candidate is not built for exactly one of three reasons, all of them facts about the evidence: no counted signal, already covered by an existing artifact, or low confidence and not opted into.

### What the caps used to be, and why they went

| Repo size / history | Max skills | Max subagents | Max rules | Max hooks |
|---|---|---|---|---|
| Small (<10k LOC, <20 sessions) | 3 | 1 | 4 | 2 |
| Medium (10k to 80k, 20 to 100 sessions) | 6 | 3 | 8 | 4 |
| Large (>80k, >100 sessions) | 10 | 5 | 15 | 6 |

They were a proxy for quality and measured the wrong thing. Measured on a real 268k-line Next.js repo: **0 subagents, 0 rules, 0 hooks**, a `.env.local` on disk, two competing lockfiles, eight external services — and 61 skill directories under `.claude/skills/`, of which 48 were third-party library guides installed from a lockfile. Those 61 tripped the "5+ existing skills ⇒ audit-only" test, which clamped the run to 2/1/3/2 on the repo in the sample with the most missing, and told the user a cap was the reason.

### What replaced them

- **The core set** (`blueprint.md` §1.3): `setup-manager`; `pr-reviewer` with `review-pr`; `qa` for any web app; `db-inspector` with `query-db` for any database; `security-auditor`; `designer` with `new-component`; `product-analyst` with the analytics skills; the env-leak, destructive-command and package-manager hooks; permissions; the zone and workflow rules. Each has a licence field; each is built when it holds, under the catalogue's name.
- **The catalogue walk**, a table in the plan with one row per catalogue row — trigger field, what was found, outcome — so the user reads what was *considered*, not only what was built. "Restates the index doc", "a vendored guide exists", "installed at user scope" and "the procedure is documented" are not outcomes. `verify_artifacts.py`'s `core_set` check warns in phase 8 when a licensed core artifact is missing from the manifest.
- **A personalization test on every generated file**: at least three concrete identifiers from this repo; this repo's convention rather than a best practice; an evidence line naming a field and a number; and the sharp one — *name a repo this file would be false in*. A file that would read identically elsewhere is rewritten, not shipped.
- **Unconditional de-duplication, with one definition of "covered".** A candidate is covered only by an artifact of the **same type, inside this repo, doing the same job** — the team's own, tested against the repo's commands and paths rather than trusted. A vendored artifact is a generic guide and becomes a reference the generated skill links to; the index doc covers only an index-doc line; a document licenses a skill rather than replacing it; a human GUI (`db:studio`) is not the agent's loop. Nothing existing is ever restructured, rewritten, moved or renamed. **There is no audit-only mode.**
- **Repo scope only.** Artifacts in `~/.claude/skills` or `${CODEX_HOME}/skills` load in every repo on the machine and are not this repo's setup. They are never counted, never quoted as "your setup", and — since 2026-09-07 — **never coverage for anything**: a same-name collision is a report line, not a skip. Measured: a user-scope PostHog plugin and a user-scope MCP entry had silently removed three skills and a draft from a repo-scoped setup.

Fewer, sharper artifacts still get used and sprawling ones still get ignored — enforced by the evidence requirement and the personalization test, which make each artifact earn its file, rather than by stopping at a number.

## 10. Attribution and lead generation

Attribution appears in exactly three places:

1. The final run summary printed in the agent.
2. The footer of `docs/agentic-setup/report.md` and the generated index doc.
3. A frontmatter comment in each generated file.

Text: "This work was brought to you by Agentic Studio." followed by one upsell line: "Bigger codebase or a team? Agentic Studio builds the full engineering system in 2 to 3 weeks: https://theagentic.studio."

Rules: never inject attribution into the runtime behavior of generated skills or agents. Never gate features on it. License is MIT; attribution is requested, not required.

Optional, off by default: a "share your setup" prompt that prints a stats card (artifacts built, minutes taken) for posting.

## 11. Target support

### 11.1 Claude Code

Emits: `.claude/rules/` (`paths:`-scoped), hooks in `.claude/hooks/` registered in `.claude/settings.json`, a `permissions` allow / ask / deny block in the same file, `.claude/skills/` (each with its own `references/`), `.claude/agents/`, an MCP draft in `.mcp.json`, and last a delimited section appended to `CLAUDE.md` that tabulates all of it. **No plugin manifest** (§9).

### 11.2 Codex

Emits: `<plan-dir>/rules/` prose rules pointed at from `AGENTS.md`, `.codex/rules/agentify.rules` (Starlark command policy, which is also this target's permission surface), `.codex/hooks/` scripts registered in `.codex/hooks.json`, `.agents/skills/`, `.codex/agents/*.toml` subagents, a TOML MCP draft, and last the `AGENTS.md` section.

**Revised 2026-09-05: nothing is substituted on this target.** Codex has a full native hook system — 12 events, `<repo>/.codex/hooks.json`, regex matchers over tool names — plus native subagents and skills. The earlier claim that "Codex has no hooks, so `AGENTS.md` instructions plus native git hooks are substituted" was verified false against codex-cli 0.152.1. The one real prerequisite is project trust: `[projects."<abs path>"] trust_level = "trusted"` gates every repo-scoped Codex artifact together, agentify never sets it, and it is a "needs you" item in the report.

### 11.3 Adapter contract

Every target implements: detect, locate transcripts, list existing config, emit each artifact type or declare unsupported, run smoke tests. Formats and paths are pinned in the adapter and verified against current agent documentation at each release. Formats change; the core workflow doesn't.

## 12. Distribution

- GitHub repo, also registered as a Claude Code plugin marketplace. (agentify is distributed *as* a plugin; it does not *produce* one — §9.) On Codex the install is a file copy, and the reason is about agentify rather than about Codex: Codex has its own plugins and marketplaces — `[marketplaces.*]` and `[plugins."<plugin>@<marketplace>"]` in `${CODEX_HOME}/config.toml`, installs cached under `${CODEX_HOME}/plugins/cache/<marketplace>/<plugin>/<version>/`, and a real `.codex-plugin/plugin.json` manifest schema, all three **VERIFIED** in `adapters/codex.md` (§3's paths table and §4.7) — but this repo ships only the Claude Code manifest (`.claude-plugin/plugin.json`) and no Codex one, so that route has nothing to install yet.
- `npx agentify` (or chosen name) installer: installs the skill globally or into the current repo, for the chosen target.
- Landing page: one page, SEO focused, Hostshare case study numbers as proof, install command above the fold, link to Agentic Studio services.
- Shared template repo with the agentic boilerplate generator over time: the boilerplate injects a setup for a known stack; this tool derives one for an unknown stack.

## 13. Safety and privacy

- Local only. No network calls by the skill's scripts.
- Transcript access requires explicit consent every run.
- Secret scrubbing before any transcript content is surfaced.
- Never reads env values, credential files, or files matching secret patterns.
- Never runs destructive git commands. Never rewrites history. Never force pushes.
- All changes on a branch or staged; never committed to the user's current branch without approval.
- Uninstall path documented in every report.

## 14. Success metrics

Adoption: installs (npm + marketplace), completed runs (report file written), completion rate from invoke to report.

Quality: percentage of generated artifacts still present in the repo 30 days later (measured via voluntary follow-up, not telemetry), GitHub issues tagged "bad suggestion" per 100 runs.

Business: inbound inquiries citing the tool, conversion to discovery call, revenue attributed.

Targets for first 90 days after launch: 1,000 installs, 40% completion rate, 10 inbound inquiries.

## 15. Roadmap

v1.0: **Claude Code and Codex**, all eight phases, three analyzers, the setup catalogue with its core set and catalogue walk, plan gate, verification, report.
v1.2: `doctor` mode, rerun monthly to detect drift and new repetition; interactive plan editing.
v1.3: Team mode, reads transcripts from multiple contributors' machines via exported summaries.
Later: Cursor and Gemini CLI adapters, boilerplate integration, community analyzer plugins.

## 16. Open questions

1. Name. **Checked, and it is taken twice**: npm has `agentify` (v0.0.1, `unadlib`, 2024-06-09), and GitHub has an active same-niche organisation `agentify-sh`. A final name is still undecided; `PLACEHOLDER-ORG` in the README and manifests marks every site that needs it.
2. Should the tool write the plan and report under `docs/agentic-setup/` or under `.claude/`? Visible docs favor adoption; hidden dirs favor tidiness.
3. Minimum model class to enforce vs warn.
4. Whether the installer should also offer to install the agentic boilerplate's starter skills for known stacks.
5. How to handle monorepos: one setup at root, or per package. Proposal: root by default, offer per-package if workspaces detected.

## 17. Risks

| Risk | Mitigation |
|---|---|
| Overgeneration, repo feels spammed | Plan gate, evidence requirement, the personalization test that rewrites any file which would read the same in another repo, and per-type grouping so the user can drop items by number |
| Undergeneration, setup feels generic or thin | The core set and the catalogue walk in the plan, the one-definition rule for "already covered", the structural catalogue that fires on the codebase alone, the `core_set` verifier warning, and the removal of every output cap (§9) |
| Transcript reads blow the context window | Miner script pre-aggregates to ~3k tokens |
| Agent config formats change | Versioned adapters, release checklist verifies against docs |
| Secrets surfaced from transcripts | Scrub before surfacing, user-turns only, consent every run |
| Low quality on small models | Model class warning, plan gate lets user catch it |
| Attribution reads as spam | Three placements only, never at runtime, MIT |
| Users run once and forget | `doctor` mode in v1.2, stats card for sharing |

---

This work was brought to you by Agentic Studio.
