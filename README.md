# agentify

**agentify reads your repo and your own Claude Code transcripts, works out what you keep doing by hand, and builds the agentic setup that fits — after you approve a written plan.**

```
/plugin marketplace add PLACEHOLDER-ORG/agentify
/plugin install agentify@agentify
```

Then, inside Claude Code, in the repo you want set up:

```
run agentify on this repo
```

It produces:

- `docs/agentic-setup/plan.md` — every proposed artifact, its evidence, and what it will not do. Nothing is written until you approve this.
- A branch `agentic-setup/<yyyy-mm-dd>` containing the generated setup: path-scoped rules, guardrail hooks, a permissions allow/deny block, workflow skills (including `setup-manager`, which maintains the rest), specialist subagents, MCP config drafts, and an index-doc section in `CLAUDE.md` / `AGENTS.md` that stitches them together with a table per type.
- `docs/agentic-setup/report.md` — what was built, what was skipped and why, what still needs you (MCP auth), three things to try tomorrow, and how to remove all of it.

> **Status: pre-release (v0.1.0).** The repo is not published yet, and the name `agentify` **is taken on both registries we checked**: npm has `agentify` (v0.0.1, published by `unadlib` on 2024-06-09), and GitHub has an active organisation in the same niche, `agentify-sh`. The name used throughout this repo is therefore a working title, and the final one is not decided. Every `PLACEHOLDER-ORG` in this README and in the plugin manifests is a placeholder to be replaced when the repo is published under its final name. Expect the install commands above — and possibly the name in them — to change.

Requirements: Claude Code, and Python 3.9 or newer (standard library only, nothing to `pip install`). `git` is optional — without it you lose the commit-history evidence and the branch, the run says so, and it still reaches a plan and a build.

---

## What it does

Eight phases. Each has a defined input, output, and stop condition, so a run cannot skid from "I found some patterns" straight to writing files.

| # | Phase | What happens |
|---|---|---|
| 0 | **Preflight** | Detect the target agent, the repo root, and any existing agentic config. Ask consent for transcript access. Note a dirty tree and carry it forward — nothing is blocked yet, because nothing has been written yet. |
| 1 | **Discover** | A script scans the repo: languages, frameworks, package scripts, test and lint commands, folder zones, CI, docs, env var *names*, git basics. |
| 2 | **Mine** | Two scripts mine your local transcripts (user turns only, secrets scrubbed first) and your git history (read-only, bot commits excluded). |
| 3 | **Diagnose** | The model reads the two JSON reports and writes findings: repetition, corrections, friction, guardrail gaps, external systems. Each carries an evidence count. |
| 4 | **Propose** | Findings are mapped to artifact types, then a catalogue walks your stack — zones, services, frameworks, commands, missing guardrails — for everything the evidence supports. **Nothing is capped.** A finding with no evidence count maps to nothing. |
| 5 | **Interview** | 3 to 8 numbered questions, ceiling of 12, each with a marked default. Reply `defaults` to accept all. Never asks what discovery already answered. |
| 6 | **Shortlist, then plan** | First a one-screen shortlist in chat — every item, numbered, one line each with the count behind it — that you edit in plain words and confirm with `ok`. Then `docs/agentic-setup/plan.md` is written from it. **Hard gate.** You accept, cut items, or edit. No file is generated before written approval. |
| 7 | **Build** | The tree has to be clean or you override it explicitly. Artifacts are generated on a branch, in dependency order, with a checkpoint after each type, and committed to that branch — an empty branch deletes without undoing anything. |
| 8 | **Verify and hand off** | Every artifact goes through deterministic checks — it exists, it parses, its frontmatter is right, its evidence matches the plan, its ID is unique, no secret is in an MCP draft, no rule contradicts what the repo actually does. The report is written, and you get a branch or a staged diff. Generated hooks are scanned statically; agentify **asks** before it runs one. |

Phases 1 and 2 are deterministic scripts; 3 through 6 are model reasoning. The model never scrapes your transcripts directly — the miner pre-aggregates them to a compact report first, so a year of history costs the same context as a week of it.

**The rule that makes the output worth keeping:** every generated artifact traces to a concrete signal — a transcript pattern with a count, a package script, a dependency, a commit convention. This is not a template with your repo name substituted in. If there is no evidence, nothing gets built.

## What it generates

For Claude Code:

| Artifact | Where it lands | Comes from |
|---|---|---|
| Index doc section | Appended to `CLAUDE.md` in a delimited block | Discovered commands, conventions, and repeated corrections |
| Path-scoped rules | `.claude/rules/` | Conventions tied to specific paths, and corrections you made 2+ times |
| Hooks | `.claude/settings.json` plus scripts | Deterministic checks that should not depend on the model remembering |
| Skills | `.claude/skills/` | Multi-step procedures you triggered repeatedly |
| Subagents | `.claude/agents/` | Work that needs isolated context, a specialist persona, or parallelism |
| Permissions | `permissions.allow` / `.ask` / `.deny` in `.claude/settings.json` | Your repo's own commands, pre-approved; your `.env*` files and the package managers you don't use, blocked |
| MCP config drafts | `.mcp.json` | External services your deps, env var names, and prompts show you actually use |

For Codex: `AGENTS.md`, `.codex/hooks.json` (12 events, native), `.codex/rules/*.rules` (Starlark command policy, which is also that target's permission surface), `.codex/agents/*.toml` subagents, `.agents/skills/` skills, and a TOML MCP draft. **Nothing is substituted on either target.** Codex does have a full hook system — earlier versions of this README said it did not, and that was wrong.

agentify does **not** produce a plugin manifest. The setup is derived from one repo's evidence and personalized to it, so a portable copy would be wrong wherever it landed.

Every generated file starts with an ID, a date, a one-line evidence summary, and the line *"Safe to delete or edit."*

## How much it builds

**There are no caps.** agentify proposes the whole setup your codebase and history support, and you cut what you do not want at the plan gate. If something is not built, the reason is always one of three, and all three are facts about the evidence: no counted signal, already covered by something you have, or low confidence and waiting on your yes.

Earlier versions capped output by repo size and switched to an "audit-only" mode above five existing skills. Both are gone, and the measurement is why: on a 268k-line repo with **zero** rules, hooks and subagents, 61 skill directories — 48 of them third-party library guides installed from a lockfile — tripped the maturity test and throttled the run to 2 skills / 1 subagent / 3 rules / 2 hooks. The repo with the most missing got the smallest build, and the user was told a cap was the reason.

What replaced them:

- **A core set, and a catalogue walk you can read.** Every setup gets `setup-manager`, a `pr-reviewer` subagent with a `review-pr` skill, a `qa` skill for any web app, a read-only `db-inspector` with `query-db` for any database, a `security-auditor`, a `designer` with `new-component`, a `product-analyst` with the analytics skills, the env-leak / destructive-command / package-manager hooks, a permissions block, and a rule per zone — each when its licence holds. The plan ends with a table showing every catalogue row that was considered, what was found, and why it was or was not built.
- **A personalization test on every file.** Five checks, and the sharp one is: *name a repo this file would be false in.* A file that would read identically in an unrelated project is a template, and it gets rewritten rather than shipped.
- **De-duplication, unconditionally — against the right thing.** A candidate is skipped as "already covered" only by an artifact of the same type, inside your repo, that does the same job — your own, and checked against your actual commands and paths rather than trusted. A third-party library guide you installed is generic by construction, so it becomes a reference the generated skill links to, not a reason to skip it. Your `CLAUDE.md` stating a convention is the reason to scope a rule to that zone, not the reason to skip the rule. Nothing existing is ever restructured, rewritten or moved.

**Only what is in the repo counts as the repo's setup.** Skills in `~/.claude/skills` or `~/.codex/skills` load everywhere on your machine and in nobody else's clone; they say nothing about this project and never stand in for an artifact here. If a generated skill shares a name with one of them, the report says so and both load.

## Safety and privacy

- **Local only, with two named exceptions and no others.** The analyzer scripts open no sockets, and the default run makes no network call at all. There are exactly two paths that can, both read-only, both through your own already-authenticated GitHub CLI, and both disclosed here rather than buried: `mine_git.py` can run `gh pr list` to learn your PR conventions — a default run passes `--no-gh` and skips it, giving that evidence up on purpose — and if agentify is about to offer you a pull request, it asks `gh` whether you can actually push to the remote first, so it cannot offer to open a PR against a repo you only have read access to. Neither sends any repo content. Nothing else, anywhere in the tool, opens a connection.
- **Python standard library only.** No dependencies to audit, nothing to `pip install`.
- **No telemetry.** None, by default or otherwise. There is nothing to opt out of.
- **Consent every run.** Transcript access is asked for each time: yes, no, or yes but only the last N days. Answering no still produces a setup, derived from code and git alone, and the plan says so.
- **User turns only.** The transcript miner reads your prompts. It does not mine assistant output or tool results.
- **Scrubbed before anything is written.** API keys, tokens, JWTs, connection strings, and home paths are redacted inside the miner, before any text reaches a file, the model, or your screen. Quotes from your own prompts get copied into the plan, the report, and a line of frontmatter — so swearing in one is masked to `[expletive]` on the way out. The sentence is kept, and the counts are computed before masking, so nothing is silently dropped for having been said in frustration.
- **Never reads secrets.** No env values (env var *names* only), no credential files, nothing matching a secret pattern.
- **Additive and reversible.** No existing file is ever overwritten. `CLAUDE.md` is merged by appending a clearly delimited section, or by proposing a separate rewrite you approve on its own.
- **Idempotent.** Generated files carry a stable ID. Rerunning updates them in place instead of stacking up duplicates.
- **Branch or stage-only.** Changes land on `agentic-setup/<yyyy-mm-dd>` or stay staged. Nothing is committed to your current branch, ever.
- **Your `.gitignore` is respected, not overridden.** If a path agentify would write is ignored, it stays out of the commit — agentify never force-adds it — and `report.md` lists those files by name so the undo still covers them.
- **Read-only git while it is looking at your history.** The git miner can run seven subcommands and nothing else: `log`, `rev-list`, `rev-parse`, `shortlog`, `for-each-ref`, `show --stat`, `config --get`. Every call is checked against that allow-list *and* against a list of mutating verbs, wherever they appear — as a subcommand or as an argument. The only git that writes anything is the build in phase 7, after you approved the plan: it creates the branch and commits to it. Never a destructive command, never a history rewrite, never a force push, never `git stash` on your behalf.
- **Generated hooks are not executed unless you say yes.** They get static checks by default — file exists, execute bit, shebang, and a scan for network calls. Running one is a separate question in phase 8, and a hook whose scan finds a network call is failed and never run at all.
- Every report ends with the uninstall path.

## What it will not do

From the v1 non-goals, stated plainly so you know what you are getting:

- **It will not auto-configure MCP servers that need credentials.** It recommends servers and drafts the config; you authenticate.
- **It does not support Cursor, Windsurf, or Gemini CLI.** Claude Code first, Codex second. The adapter layer exists so those can be contributed.
- **There is no hosted or web version.** It runs entirely inside your agent, on your machine.
- **It does not monitor or detect drift.** A `doctor` mode that reruns monthly is on the roadmap, not in v1.
- **It collects no telemetry.**
- **It will not replace a setup you already built.** Existing artifacts are read to de-duplicate against and never restructured, rewritten, moved or renamed. A symlinked or vendored artifact is never edited at all.
- **It will not open a pull request and never pushes.** The branch is left for you.

## Install

Three routes. Pick one.

### 1. Plugin marketplace (recommended)

```
/plugin marketplace add PLACEHOLDER-ORG/agentify
/plugin install agentify@agentify
```

Updates arrive with `/plugin marketplace update agentify`.

### 2. Global skill, manual copy

Available in every repo on your machine.

```bash
git clone https://github.com/PLACEHOLDER-ORG/agentify.git /tmp/agentify
mkdir -p ~/.claude/skills
cp -R /tmp/agentify/skills/agentify ~/.claude/skills/agentify
```

### 3. Per-repo skill

Checked into one repo, so a team shares the same version.

```bash
git clone https://github.com/PLACEHOLDER-ORG/agentify.git /tmp/agentify
mkdir -p .claude/skills
cp -R /tmp/agentify/skills/agentify .claude/skills/agentify
```

Verify any route with `python3 ~/.claude/skills/agentify/scripts/discover.py --help` (adjust the path for route 3).

## Uninstall

Removing the tool:

```
/plugin uninstall agentify@agentify          # route 1
rm -rf ~/.claude/skills/agentify             # route 2
rm -rf .claude/skills/agentify               # route 3
```

Removing what it generated — **`report.md` generates the exact commands for your run; do not copy them from here.** The shape depends on what the build could commit:

```bash
git checkout <your-branch> && git branch -D agentic-setup/<yyyy-mm-dd>
```

Both lines, in that order: `git branch -D` refuses to delete the branch you are standing on, and moving back to your own branch is what restores any file agentify appended to, because the appended block was committed on the agentify branch and never on yours.

That is enough only when the branch actually holds everything. If your `.gitignore` excludes a path agentify wrote to — `.claude/` is a common one — git would not commit it, so the branch delete does not touch it, and `report.md` lists those files by name as a second step. It also tells you before you approve, at the plan gate, rather than after the build.

Same for a file you wrote yourself that git never tracked: git has no pre-run copy to restore, so the whole undo for it is a script that takes agentify's own contribution back out — and **which script depends on the file's format, not on how git sees it.** A text file (`CLAUDE.md`, a rule, a shell config) was appended to inside `agentify:begin` / `agentify:end` markers, and the marker-removal script cuts exactly that block. A JSON config (`.claude/settings.json`, `.mcp.json`) has no comment syntax, so it never carried a marker and never can: it was merged into structurally, and the JSON un-merge script removes the entries this run added — deleting the file only when nothing but agentify's entries remain, and keeping it when you have since added keys of your own. `report.md` emits the right one per file; neither is a `rm`, and neither destroys your content.

In stage-only mode and in a repo with no git, nothing is committed and no branch exists: the undo is the numbered file list in `report.md`, and there is no branch to delete.

Generated files are individually deletable either way: each is marked *"Safe to delete or edit,"* and the `CLAUDE.md` addition is a single delimited block you can cut out.

## Contributing

The codebase is three layers, and which layer your change belongs in is usually obvious:

1. **Analyzers** — `skills/agentify/scripts/`. Deterministic, stdlib-only, no network. They emit JSON; they never reason.
2. **Core workflow** — `skills/agentify/SKILL.md` and `skills/agentify/references/`. Target-agnostic: diagnose, map, size, plan, build, verify.
3. **Target adapters** — `skills/agentify/adapters/`. The only place agent-specific paths and file formats are allowed to live.

That third boundary is the one to respect. A hardcoded `~/.claude/projects/...` path or a `.claude/settings.json` shape outside an adapter is a bug, even when it works. Formats change; the workflow does not.

**Read [`docs/DECISIONS.md`](docs/DECISIONS.md) before changing a default.** Every default in this repo — the clustering threshold, the sizing caps, hook execution being opt-in, `--no-gh`, where the plan is written — is recorded there with the question it answers, why it was chosen, what changing it costs, and whether it is decided, provisional, or still open. A change that contradicts an entry there is not necessarily wrong, but it needs to update that entry in the same pass.

### Adding an analyzer

New evidence sources are the highest-value contribution. An analyzer is a Python script in `skills/agentify/scripts/` that:

- uses the standard library only, targets Python 3.9+, and makes no network calls;
- accepts `--repo <path>` and `--help`;
- prints exactly one JSON object to stdout and nothing else, with diagnostics on stderr;
- includes `schema_version`, `tool`, `warnings`, and `timing_ms` in that object;
- follows the two-value exit contract: **exit 0** for success *and* every degraded run (a missing repo path, no git, no transcripts, a timeout — valid JSON with the loss explained in `warnings`), **exit 1** only when no JSON could be produced at all. Exit 2 is reserved and never emitted; even a usage error prints JSON and exits 1;
- ships a `--selftest` flag that prints a JSON pass/fail report and exits 1 if any check fails, so a broken analyzer fails CI;
- caps its own output, so a large input cannot blow the context window.

Then add a mapping in `skills/agentify/references/mapping-rules.md` explaining what finding your signal produces and what artifact that finding justifies. A signal that maps to nothing is dead weight.

### Adding a target adapter

Adapters live in `skills/agentify/adapters/` (`claude-code.md` is the reference implementation). Every adapter implements the same five things:

1. **Detect** — how to tell this agent is the one running.
2. **Locate transcripts** — where session files live, and how a repo path maps to a session directory.
3. **List existing config** — index docs, skills, agents, rules, hooks, MCP servers, and enough provenance to tell what the team wrote from what it installed, because only the first drives maturity classification.
4. **Emit each artifact type, or declare it unsupported.** Declaring it unsupported is a first-class answer. Codex has no hooks, so its adapter names the substitution and the plan tells the user about it. Silently dropping an artifact type is not acceptable; a stated substitution is.
5. **Run smoke tests** — how to verify each emitted artifact type actually loads in this agent.

Pin the paths and formats you verified, and note the agent version you verified them against.

### Testing a change

`test-repos.md` is the regression list: public repos spanning a fresh repo, a small single-language repo, a medium JS/TS app, a Python repo, a large workspace monorepo, a repo that already has a `CLAUDE.md`, and a repo with a mature `.claude/` setup. Run your change against it to the plan gate and diff the plan against the expected counts before opening a PR.

## License and attribution

MIT. See [LICENSE](LICENSE).

Attribution is **requested, not required**. agentify puts its own attribution in exactly three places: the final run summary, the footer of `report.md` and of the generated index doc section, and one frontmatter comment per generated file. It never injects attribution into the runtime behavior of a generated skill or agent, and it never gates a feature on it. If you strip all of it, everything still works — that is the license, and it is deliberate.

---

This work was brought to you by Agentic Studio.

Bigger codebase or a team? Agentic Studio builds the full engineering system in 2 to 3 weeks: https://theagentic.studio.
