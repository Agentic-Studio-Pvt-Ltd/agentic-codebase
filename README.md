<div align="center">

# agentic-codebase

**Reads your repo + your agent history. Builds the Claude Code or Codex setup you'd write by hand.**

You approve the plan. Then it builds.

[![skills.sh](https://skills.sh/b/Agentic-Studio-Pvt-Ltd/agentic-codebase)](https://skills.sh/Agentic-Studio-Pvt-Ltd/agentic-codebase)

[Install](#install) · [Before / After](#before--after) · [What it generates](#what-it-generates) · [Safety](#safety)

</div>

## What it builds for you

- **Turns your WTFs into guardrails.**
- **Every "no, not like that" becomes a rule.**
- **Turns "why did you do that?!" into a hook that stops it.**
- **Every `.env` your agent peeked at becomes a guardrail.**
- **Every prompt you typed three times becomes a skill.**
- **Every PR you reviewed by hand becomes a reviewer agent.**
- **Every "yes, run it" you clicked becomes a permission.**
- **Everything you re-explain each session lands in `CLAUDE.md`.**
- **Every service you keep mentioning becomes an MCP draft.**
- **Your f-bombs, refactored into rules.**

It read every time you yelled at your agent. Then fixed why.

> [!IMPORTANT]
> ### 🔒 Runs 100% on your machine
>
> - **This tool sends nothing, anywhere.** No servers. No account. No telemetry.
> - **Zero network calls.** Python standard library only. Nothing to `pip install`.
> - **Transcripts need your yes, every run.** Your prompts only. Secrets scrubbed before anything is written.
> - **Never reads secrets.** No `.env` values. No credential files.
> - **Never touches your branch.** Builds on `agentic-setup/<date>`. Never pushes.
>
> Your agent still talks to its own model, same as always. This tool adds nothing on top.

---

## Install

One command. Works for both.

```bash
npx skills add Agentic-Studio-Pvt-Ltd/agentic-codebase
```

Then, in your agent:

```
run agentic-codebase on this repo
```

**Needs:** Python 3.9+. `git` optional.

<details>
<summary>Claude Code plugin instead</summary>

```
/plugin marketplace add Agentic-Studio-Pvt-Ltd/agentic-codebase
/plugin install agentic-codebase@agentic-codebase
```

</details>

> [!WARNING]
> **Codex: trust the repo first.** Untrusted repo → `AGENTS.md`, hooks and rules silently don't load.
> Set `trust_level = "trusted"` for the repo in `${CODEX_HOME:-~/.codex}/config.toml`.

---

## Before / After

```
BEFORE                         AFTER
my-app/                        my-app/
├── CLAUDE.md                  ├── CLAUDE.md             + indexed section
└── src/                       ├── .claude/
                               │   ├── rules/            one per code zone
                               │   ├── skills/           setup-manager, review-pr, qa …
                               │   ├── agents/           pr-reviewer, db-inspector …
                               │   └── settings.json     hooks + permissions
                               ├── .mcp.json             drafts, you authenticate
                               ├── docs/agentic-setup/   plan.md · report.md
                               └── src/
```

<sub>Example on Claude Code. Codex gets the same shape. See the table below.</sub>

---

## What it generates

| | Claude Code | Codex |
|---|---|---|
| **Index doc** | `CLAUDE.md` section | `AGENTS.md` section |
| **Rules** | `.claude/rules/*.md` | `AGENTS.md` + `docs/agentic-setup/rules/` |
| **Hooks** | `.claude/settings.json` + scripts | `.codex/hooks.json` + scripts |
| **Permissions** | `.claude/settings.json` → `permissions` | `.codex/rules/agentic-codebase.rules` |
| **Skills** | `.claude/skills/` | `.agents/skills/` |
| **Subagents** | `.claude/agents/*.md` | `.codex/agents/*.toml` |
| **MCP drafts** | `.mcp.json` | `docs/agentic-setup/codex-mcp.toml` |
| **Plan + report** | `docs/agentic-setup/` | `docs/agentic-setup/` |

Every file: an ID · a date · the evidence behind it · *"Safe to delete or edit."*

---

## How much it builds

- **No caps.** Everything your code and history support.
- **You cut at the plan.** Nothing written before you approve.
- **Every file traces to a count.** No evidence → not built.
- **Skipped only if:** no evidence · already covered · low confidence.
- **`setup-manager`**: keeps the setup current
- **`pr-reviewer` + `review-pr`**: PR review
- **`qa`**: any web app
- **`db-inspector` + `query-db`**: any database, read-only
- **`security-auditor`**: security review
- **`designer` + `new-component`**: UI repos
- **`product-analyst` + analytics skills**: repos with analytics
- **3 guardrail hooks**: env leak · destructive commands · wrong package manager
- **Permissions**: your commands allowed, `.env*` denied
- **Rules**: one per code zone
- **Workflow skills**: anything you ask for 3+ times

---

## How it works

| # | Phase | Does |
|:-:|---|---|
| 0 | Preflight | Detect agent. Ask transcript consent. |
| 1 | Discover | Scan repo: stack, commands, zones. |
| 2 | Mine | Your prompts + git history → compact JSON. |
| 3 | Diagnose | Find repetition, friction, gaps. |
| 4 | Propose | Map findings → artifacts. |
| 5 | Interview | 3 to 8 questions. `defaults` accepts all. |
| 6 | **Plan** | **You approve. Hard gate.** |
| 7 | Build | On a branch, in order. |
| 8 | Verify | Check every file. Write report. |

---

## Safety

| | |
|---|---|
| **Network** | None. One optional read-only `gh pr list`, off by default. |
| **Telemetry** | None. Nothing to opt out of. |
| **Consent** | Asked every run: yes · no · last N days. "No" still builds from code + git. |
| **Transcripts** | Your prompts only. Never assistant output or tool results. |
| **Secrets** | Keys, tokens, JWTs, connection strings, home paths. Scrubbed first. |
| **Env vars** | Names only. Never values. |
| **Your files** | Never overwritten. Appends inside `agentic-codebase:begin` / `:end` markers. |
| **Reruns** | Update in place. No duplicates. |
| **Git** | Read-only while mining. Writes only a branch, after you approve. |
| **Push / PR** | Never. |
| **Hooks** | Never run without your yes. A hook making network calls fails. |
| **`.gitignore`** | Respected. Never force-adds. |

---

## Won't do

- Set up credentialed MCP servers. Drafts only, you authenticate
- Cursor, Windsurf, Gemini CLI
- Hosted or web version
- Drift detection (on the roadmap)
- Rewrite, move or rename your existing setup
- Push or open a PR

---

## Uninstall

| | Claude Code | Codex |
|---|---|---|
| **The tool** | `rm -rf .claude/skills/agentic-codebase` | `rm -rf .agents/skills/agentic-codebase` |
| **Plugin** | `/plugin uninstall agentic-codebase@agentic-codebase` | n/a |
| **What it built** | Commands in your `report.md` | Commands in your `report.md` |

> [!NOTE]
> **Undo from `report.md`, not from here.** It's written for your exact run, including gitignored and untracked files a branch delete won't touch.

---

## Contributing

- **Read [`CLAUDE.md`](CLAUDE.md) first.**
- **`scripts/`**: analyzers. Stdlib only. No network. JSON out.
- **`SKILL.md` + `references/`**: the workflow. Agent-agnostic.
- **`adapters/`**: the **only** place agent-specific paths and formats live.

```bash
for s in discover mine_git mine_transcripts verify_artifacts; do
  python3 skills/agentic-codebase/scripts/$s.py --selftest
done
python3 -m unittest discover -s tests -v
```

---

## License

MIT. Attribution welcome, never required. Strip it and everything still works.

<div align="center">

---

Built by **[Agentic Studio](https://theagentic.studio/?utm_source=github&utm_medium=readme&utm_campaign=oss)**

Bigger codebase or a team? We make your team AI-native in 4 weeks: agents, reviews, guardrails, CI.

</div>
