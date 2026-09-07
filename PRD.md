# PRD: Agentic Setup Skill (working name: agentify)

Owner: Ravi, Agentic Studio
Status: Draft v0.1
Date: 4 September 2026

---

## 1. Summary

A free, open-source skill that a developer installs globally or in a repo. When invoked inside Claude Code (v1) or Codex (v1.1), it analyzes the codebase and the developer's local chat history with the agent, identifies repetitive work and missing guardrails, proposes a customized agentic setup (skills, subagents, hooks, rules, MCP recommendations, plugin packaging), gets the developer's approval on a written plan, builds it, verifies it, and hands off with a report.

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
- Cursor, Windsurf, Gemini CLI, or other targets. Claude Code first, Codex second.
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
| 4. Propose | Map findings to artifacts (section 8), walk the setup catalogue against the repo, apply the personalization test, then the completeness check (section 9). | Candidate list |
| 5. Interview | Ask the user numbered questions only where evidence is ambiguous. Sensible defaults, "accept all defaults" option. | Answers |
| 6. Plan | Write `docs/agentic-setup/plan.md`. User approves, edits, or rejects items. Hard gate. | Approved plan |
| 7. Build | Generate artifacts in dependency order on a branch. Checkpoint after each group. | Files on branch |
| 8. Verify and hand off | Smoke test each artifact, write the report, show attribution and upsell. | `docs/agentic-setup/report.md`, PR or staged diff |

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
- Folder map to depth 3 with file counts, flagging conventional zones (api, db, migrations, components, tests)
- External services: from dependencies and env var names (Stripe, Supabase, Neon, Linear, PostHog, Sentry, Playwright, etc.)
- Existing docs: README, CONTRIBUTING, ADRs, PR template, issue templates
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

Apply the mapping rules (section 8), then walk the setup catalogue — subagents, guardrail hooks, permissions, zone and workflow rules, integration and practice skills, MCP drafts — against the repo, adding a candidate for every entry whose trigger field is non-empty. Run the personalization test on each one and rewrite anything that fails it. Then run the completeness check (section 9) and close or state every gap. Output a candidate list grouped by artifact type, each with a one-line rationale, a mechanism sentence and an evidence reference. **Nothing is cut for count.**

### 7.6 Interview

- Ask only what evidence can't answer. Target 3 to 8 questions. Hard cap 12.
- Numbered, each with a default marked. User can reply "defaults" to accept all.
- Typical questions: branch or stage-only, whether generated hooks block or warn, which external systems are actually in daily use, team shape, target agent if both are detected, whether they run a packaged engineering workflow (compound engineering, superpowers) the setup should sit inside, which package manager the repo really uses when the lockfiles disagree, and any command slot discovery could not resolve.
- Never ask something the discovery already answered (package manager, framework, test command).
- **Four questions are banned outright** (revised 2026-09-07): offering to open a pull request — agentify never opens one and never pushes; offering to package the setup as a plugin — it is personalized to one repo and not portable; offering to raise a cap — there are none; and confirming audit-only mode — there is none.

### 7.7 Plan

Write `docs/agentic-setup/plan.md` with:

- Summary: what will be built, count by type, estimated build time
- Per artifact: name, type, purpose, evidence, files it will create or modify, what it will not do
- Files that will be modified vs created (modifications always show a diff preview)
- Capability notes for the target (e.g. Codex has no hooks; here is the substitution)
- Explicitly skipped candidates and why

User reviews. Accepts, removes items, or edits. Build does not start without approval. The plan file stays in the repo as a record.

### 7.8 Build

- Create branch `agentic-setup/<yyyy-mm-dd>` (or stage-only mode if the user prefers).
- Build order: index doc (CLAUDE.md / AGENTS.md) → rules → hooks → skills → subagents → MCP config drafts → plugin manifest.
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
- Open a PR if `gh` is available and the user agreed; else leave the branch and print the summary.
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

A finding can map to more than one artifact (a procedure becomes a skill and its final check becomes a hook). A finding with no evidence count maps to nothing — and a **structural** fact carries a count too: a service with its confidence, a zone with its file count, a command with its manifest citation, and an absence such as zero hooks in a repo holding `.env*` files.

**Revised 2026-09-07.** The plugin-manifest row is removed: the setup is derived from one repo's evidence and personalized to it, so a portable copy would be wrong wherever it landed. Rows 12 to 16 above are new, and are what makes a run on a repo with no transcript history still produce a real setup.

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

- **A completeness check** run before the plan: every zone gets a rule or a stated reason, every `.env*` gets a guardrail, every confirmed service gets a skill / subagent / MCP draft or a stated reason, and `setup-manager` is unconditional.
- **A personalization test on every generated file**: at least three concrete identifiers from this repo; this repo's convention rather than a best practice; an evidence line naming a field and a number; and the sharp one — *name a repo this file would be false in*. A file that would read identically elsewhere is rewritten, not shipped.
- **Unconditional de-duplication.** Everything already in the repo, third-party and symlinked included, is de-duplicated against; nothing existing is ever restructured, rewritten, moved or renamed. That was the useful half of audit-only mode and is now simply how every run works. **There is no audit-only mode.**
- **Repo scope only.** Artifacts in `~/.claude/skills` or `${CODEX_HOME}/skills` load in every repo on the machine and are not this repo's setup. They are read for de-duplication and never counted, never quoted as "your setup", and never allowed to change what a run builds.

Fewer, sharper artifacts still get used and sprawling ones still get ignored — enforced by the evidence requirement and the personalization test, which make each artifact earn its file, rather than by stopping at a number.

## 10. Attribution and lead generation

Attribution appears in exactly three places:

1. The final run summary printed in the agent.
2. The footer of `docs/agentic-setup/report.md` and the generated index doc.
3. A frontmatter comment in each generated file.

Text: "This work was brought to you by Agentic Studio." followed by one upsell line: "Bigger codebase or a team? Agentic Studio builds the full engineering system in 2 to 3 weeks: <link>."

Rules: never inject attribution into the runtime behavior of generated skills or agents. Never gate features on it. License is MIT; attribution is requested, not required.

Optional, off by default: a "share your setup" prompt that prints a stats card (artifacts built, minutes taken) for posting.

## 11. Target support

### 11.1 Claude Code (v1)

Emits: `.claude/rules/` (`paths:`-scoped), hooks in `.claude/hooks/` registered in `.claude/settings.json`, a `permissions` allow / ask / deny block in the same file, `.claude/skills/` (each with its own `references/`), `.claude/agents/`, an MCP draft in `.mcp.json`, and last a delimited section appended to `CLAUDE.md` that tabulates all of it. **No plugin manifest** (§9).

### 11.2 Codex

Emits: `<plan-dir>/rules/` prose rules pointed at from `AGENTS.md`, `.codex/rules/agentify.rules` (Starlark command policy, which is also this target's permission surface), `.codex/hooks/` scripts registered in `.codex/hooks.json`, `.agents/skills/`, `.codex/agents/*.toml` subagents, a TOML MCP draft, and last the `AGENTS.md` section.

**Revised 2026-09-05: nothing is substituted on this target.** Codex has a full native hook system — 12 events, `<repo>/.codex/hooks.json`, regex matchers over tool names — plus native subagents and skills. The earlier claim that "Codex has no hooks, so `AGENTS.md` instructions plus native git hooks are substituted" was verified false against codex-cli 0.152.1. The one real prerequisite is project trust: `[projects."<abs path>"] trust_level = "trusted"` gates every repo-scoped Codex artifact together, agentify never sets it, and it is a "needs you" item in the report.

### 11.3 Adapter contract

Every target implements: detect, locate transcripts, list existing config, emit each artifact type or declare unsupported, run smoke tests. Formats and paths are pinned in the adapter and verified against current agent documentation at each release. Formats change; the core workflow doesn't.

## 12. Distribution

- GitHub repo, also registered as a Claude Code plugin marketplace. (agentify is distributed *as* a plugin; it does not *produce* one — §9.)
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

v1.0: Claude Code, all eight phases, three analyzers, the setup catalogue and completeness check, plan gate, verification, report.
v1.1: Codex adapter.
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
| Undergeneration, setup feels generic or thin | The completeness check before the plan, the structural catalogue that fires on the codebase alone, and the removal of every output cap (§9) |
| Transcript reads blow the context window | Miner script pre-aggregates to ~3k tokens |
| Agent config formats change | Versioned adapters, release checklist verifies against docs |
| Secrets surfaced from transcripts | Scrub before surfacing, user-turns only, consent every run |
| Low quality on small models | Model class warning, plan gate lets user catch it |
| Attribution reads as spam | Three placements only, never at runtime, MIT |
| Users run once and forget | `doctor` mode in v1.2, stats card for sharing |

---

This work was brought to you by Agentic Studio.
