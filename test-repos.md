# Regression repos

The fixture set agentify is checked against before a release or a merged PR. Repos are **referenced by URL, never vendored** — clone them into a scratch directory, run against the clone, throw the clone away. Fixtures that no public repo can supply are **synthesized locally**, from the recipes below.

The set exists to cover the cases that break things, not to be comprehensive: no history, one language, a real app, a non-JS stack, a workspace monorepo, an existing index doc, an existing agentic setup that a run must add to without touching, a Codex history, linked instruction files, invalid configuration, and a setup whose hooks share a matcher group with the ones agentify is about to write.

## What this document has and has not been run through

**Read this first; it decides what any result recorded here is worth.**

| Stage | Status on the revision this file was last edited at |
|---|---|
| §1a selftests, both interpreters | **exercised** — see the counts in `CLAUDE.md`; they are the gate every script change passes |
| §1 analyzers against fixtures 1 and 8–11 | **exercised at the script level**, 2026-09-16, on the synthesized fixtures only. Every number quoted inside a fixture section below was observed by running that fixture's own recipe |
| §1–2 against the seven public repos in the table | **not exercised** in the run that wrote this procedure |
| §3 plan gate, §4 plan checks | **never exercised end to end** by the author of this procedure |
| §5 build, §6 verify, §7 rerun, §8 undo | **written, not run.** §7 and §8 have been exercised *at the script level* against fixture 11 — the merge, the rerun merge and `report-template.md` §3.1's block C, run verbatim — but **no leg below has been driven by a live agent run of the skill.** The numbers in §8 are from that script-level run and say so |
| The §4b results table | **empty and unmeasured.** Nothing in it has been observed |

**Nothing in this file may be upgraded from "written" to "verified" without a run behind it.** If you run a leg, say which fixture, which target, which date and which agentify revision, beside the leg. A leg run on one target is evidence about that target and about no other one.

**Gate 4 (`docs/reviews/2026-09-15-launch-audit.md`) needs an evidence record for *both* claimed targets.** Every leg from §3 to §8 is therefore run twice — once inside Claude Code with `TARGET=claude-code`, once inside Codex with `TARGET=codex` — and the record names which. A leg run on Claude Code alone closes half of gate 4.

## The set

| # | Repo | Why it is in the list | Floor — must appear in the plan |
|---|---|---|---|
| 1 | *(synthesized locally — see [fixture 1](#fixture-1-fresh-repo) below)* | Fresh repo, no history, no transcripts. The degenerate case: the run must still reach a plan, and the plan must be derived rather than invented — **and it must not be empty**. | `setup-manager` (licence: always); `pr-reviewer` + `review-pr` (licence: `discovery.git.is_repo`, and `git init` satisfies it); a catalogue walk carrying a row and an outcome for every catalogue row |
| 2 | https://github.com/chalk/chalk | Small single-language JS library. Tiny surface, clear scripts, real conventions. Proves a thin repo gets a setup fitted to it — neither padded out nor pre-cut. | the row-1 floor, plus permissions (`discovery.commands` has ≥ 2 populated slots) and the package-manager and destructive-command hooks |
| 3 | https://github.com/vercel/commerce | Medium JS/TS application (Next.js). Framework detection, external services from deps and env var names, folder zones (`components`, `lib`, `app`). The mainstream case. | the row-2 floor, plus `qa` (it is a web app), `designer` + `new-component`, one zone rule per depth-1 zone discovery reports, and the env-leak hook (`.env*` present) |
| 4 | https://github.com/pallets/flask | Python repo. Checks that discovery reads `pyproject.toml`, tox/pytest config, and a Makefile rather than assuming `package.json` exists. | the row-2 floor, with every generated command quoting the real Python toolchain — a plan naming `npm` or `bun` anywhere is a hard failure here |
| 5 | https://github.com/calcom/cal.com | Large monorepo with workspaces (Turborepo, `apps/` + `packages/`). Checks the <10s discovery budget and the monorepo prompt (root by default, offer per-package). | the row-3 floor, plus `db-inspector` + `query-db` (it has a database), `security-auditor`, and a zone rule per workspace the interview scoped in |
| 6 | https://github.com/mvanhorn/last30days-skill | Already ships a `CLAUDE.md` **and** an `AGENTS.md`, with no `.claude/` config. Checks the merge path: append a delimited section, never overwrite, and ask which target when both index docs exist. | the row-1 floor; the index-doc section appended inside markers with every pre-existing byte unchanged. **The existing index doc covers an index-doc line and nothing else** — a rule, hook, skill or subagent skipped as "already covered by `CLAUDE.md`" is a failure |
| 7 | https://github.com/vercel/vercel-plugin | Mature setup: `.claude/settings.json` plus 7 skills in `.claude/skills/`. What this row now regresses is that maturity changes **nothing**: there is no audit-only mode, nothing existing is restructured, and the complete setup is still proposed. **It does not cover shared hook groups — row 11 does.** | the row-2 floor **in full**, proposed alongside the existing 7 skills. A candidate may be skipped only as covered by an artifact of the **same type, in this repo, doing the same job** — each such skip names that file, and `## Existing setup notes` says in writing that the existing setup did not limit what was proposed |
| 8 | *(synthesized — [fixture 8](#fixture-8-codex-history-repeats-and-an-old-resumed-thread))* | **Codex history**, with three identical repeated turns and an 80-day-old thread resumed an hour ago. The only fixture that runs `--target codex` at all, and the one that regresses audit findings F05, F10 and F11. | the row-2 floor, built through `adapters/codex.md` paths: `.agents/skills/`, `.codex/agents/*.toml`, `.codex/hooks.json`, `.codex/rules/`, `AGENTS.md`. Plus `## Needs you` items for **project trust** and **arming the hooks with `/hooks`** — both are mandatory on this target and neither is something a run may claim to have done |
| 9 | *(synthesized — [fixture 9](#fixture-9-linked-instruction-files))* | **Linked instruction files.** A shared in-repo store linked into `.agents/skills/`, `.claude/skills/`, `.codex/agents/` and `.codex/rules/`; `CLAUDE.md` a symlink to `AGENTS.md`; one link out of the repo entirely. F14's subject, and the do-not-edit list the plan reads. | the row-1 floor, plus: every linked artifact appears in `existing_agentic_config.symlinked`, **no symlinked file is edited, moved or renamed**, and the index-doc section is written **once**, to the real file |
| 10 | *(synthesized — [fixture 10](#fixture-10-invalid-configuration))* | **Invalid configuration**: a `.claude/settings.json` truncated mid-object, and two generated Codex TOML artifacts that do not parse. F13's subject. A verifier-facing fixture — it does not need a full plan run. | the merge **refuses** the unparseable config, writes `<path>.agentify-proposed` and records a needs-you item (`build-and-verify.md` §2.4a step 2); `verify_artifacts.py` reports the malformed TOML as `fail` where it has a parser and `unverified` where it does not — **never `pass`** |
| 11 | *(synthesized — [fixture 11](#fixture-11-mature-setup-with-a-shared-matcher-group))* | **Mature setup with shared hooks.** The user's own hook sits in the matcher group agentify is about to append to, and a second user script shares a **basename** with the hook agentify generates, at a different path. F06 and F07's subject, and the fixture the whole undo leg turns on. | the row-2 floor proposed in full alongside the existing setup; and, across §5–§8, **every** user entry survives: the shared group, the same-basename script, the other event, the user's permission strings, and an unrelated dirty file |

Row 7 is the one most likely to regress, so read its plan rather than counting it. Five things fail it outright: any sentence proposing audit-only or additions-only mode; anything restructuring, rewriting, moving or renaming an existing artifact; any skip citing `~/.claude/skills`, a vendored guide, an index-doc section or a document as coverage; any sentence arguing that this repo needs less than the catalogue (anti-pattern A17); and a missing `setup-manager`, whose inventory is the whole reason a repo with an existing setup gets one. The words *cap*, *limit* and *quota* must appear in no plan, on any fixture.

> **Nothing here asserts a maximum.** The ranges this table used to carry were derived from the sizing caps in PRD §9, and **those caps were retired on 2026-09-07** — a run proposes the complete setup the evidence supports, and the user cuts at the phase 6 gate. What replaces them is a **floor plus a walk**: each row states the artifacts that repo's own structure licenses and which must therefore appear, and every row is additionally checked against the catalogue walk in step 4 below. A plan that produces *more* than its floor is not a finding. A plan that produces less than its floor, or that walks fewer rows than the catalogue has, is.
>
> **The floors above are DERIVED, not yet measured.** They are read off `blueprint.md` §1.3 — the core set and its licence fields — against what `discovery.json` reports for each repo, not off a completed run. The first contributor to run the full harness should record what was actually observed beside each floor, keep the floor where it held, correct it where the licence did not in fact fire, and delete this paragraph.

### Fixture 1: fresh repo

No public repo can be a true fresh-repo fixture — every clone arrives with history, and none of them has transcripts on your machine. Synthesize it:

```bash
mkdir -p "$RUN/repos/fresh" && cd "$RUN/repos/fresh"
git init -q
printf 'console.log("hello");\n' > index.js
printf '{\n  "name": "fresh",\n  "version": "0.0.0",\n  "scripts": { "test": "node --test" }\n}\n' > package.json
git add -A && git commit -qm "init"
```

This fixture is checked from both ends, and only reading the plan catches both.

**The floor.** With one commit and zero sessions there is no behavioural evidence at all, so every transcript-gated candidate belongs under `Skipped (insufficient evidence)` with a count of `0`. That is *not* the same as an empty plan: structural facts are evidence too, so `setup-manager` is still built, the catalogue is still walked row by row with an outcome recorded for each, and the plan still says in its own words that it rests on code and git history alone (`plan-template.md` §1.1). **A plan here with no skills in it at all has failed**, and so has one whose catalogue walk is shorter than the catalogue.

**The ceiling that is not a ceiling.** What must not appear is an artifact with no evidence behind it. A skill for a workflow this repo has one instance of is a fabrication whatever the total count is, and the fix is to trace each artifact's cited evidence back to the analyzer JSON rather than to compare a number against a range.

### Fixture 8: Codex history, repeats and an old resumed thread

No public repo carries a Codex history, and a real one on your machine is someone's private transcript — so this fixture is synthetic, and **it must stay synthetic**: no real rollout is ever copied into `$RUN`, and nothing below contains a credential, a real path or a real prompt.

It plants three things that were each a separate audit finding:

1. **Three identical user turns at three timestamps.** They are genuine repeated work, not three copies of one record, and they must survive de-duplication as three (F10).
2. **One turn present in both record shapes** — `response_item` *and* `event_msg`, same text, one second apart. That is one turn, and de-duplication must collapse it to one.
3. **A thread started 80 days ago and appended to an hour ago**, filed under its *creation* date directory. Under `--days 7` the file must be read, because the directory name is not a timestamp; the turn *inside* it that is 80 days old must still be excluded, because the consent window is about content, not files (F11, and F05 from the other direction).

```bash
SLUG=codex-history
mkdir -p "$RUN/repos/$SLUG" "$RUN/home/codex"
cd "$RUN/repos/$SLUG"
git init -q
printf '{"name":"cdx","scripts":{"test":"node --test","lint":"eslint ."}}\n' > package.json
printf 'export const x = 1;\n' > index.js
git add -A && git commit -qm "init"
git remote add origin git@github.com:acme/cdx.git

python3 - "$RUN/repos/$SLUG" "$RUN/home/codex" <<'PY'
import datetime as dt, json, os, sys, time
repo, codex_home = sys.argv[1], sys.argv[2]
now = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)      # 3.9-safe, no deprecation

def iso(delta):  return (now - delta).strftime("%Y-%m-%dT%H:%M:%S.000Z")
def rec(k, p, s): return json.dumps({"timestamp": s, "type": k, "payload": p})
def meta(sid, cwd, s, **extra):
    p = {"id": sid, "cwd": cwd, "timestamp": s}; p.update(extra); return rec("session_meta", p, s)
def u(text, s):
    return rec("response_item",
               {"type": "message", "role": "user",
                "content": [{"type": "input_text", "text": text}]}, s)
def e(text, s):  return rec("event_msg", {"type": "user_message", "message": text}, s)

REPEAT = "run npm test and fix the failing suite"
recent, old = now - dt.timedelta(days=1), now - dt.timedelta(days=80)

live = [meta("t-live", repo, iso(dt.timedelta(days=1)),
             git={"repository_url": "git@github.com:acme/cdx.git"})]
for i in range(3):                                   # (1) three genuine repeats
    live.append(u(REPEAT, iso(dt.timedelta(days=1, minutes=-i))))
for name in ("users", "orders", "invoices"):         # a request shape with a count behind it
    live.append(u("add an api endpoint for /%s with zod validation" % name,
                  iso(dt.timedelta(days=1, minutes=-10))))
live.append(u("deploy the worker to staging please", iso(dt.timedelta(days=1, minutes=-20))))
live.append(e("deploy the worker to staging please", iso(dt.timedelta(days=1, minutes=-20))))  # (2)

resumed = [meta("t-resumed", repo, iso(dt.timedelta(days=80))),                                 # (3)
           u("why is the deploy script still using npm here?", iso(dt.timedelta(days=80))),
           u("add an api endpoint for /refunds with zod validation", iso(dt.timedelta(hours=1)))]

os.makedirs(os.path.join(codex_home, "archived_sessions"), exist_ok=True)
for when, lines, age in ((recent, live, None), (old, resumed, time.time() - 3600)):
    path = os.path.join(codex_home, "sessions", when.strftime("%Y/%m/%d"),
                        "rollout-%s-%s.jsonl" % (when.strftime("%Y-%m-%dT%H-%M-%S"),
                                                 "live" if age is None else "resumed"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w").write("\n".join(lines) + "\n")
    if age:
        os.utime(path, (age, age))                   # last write an hour ago, dir 80 days old
    print("wrote", path)
PY
```

Point the miner at it with `CODEX_HOME`, never at your own `~/.codex`:

```bash
mkdir -p "$RUN/out/codex-history"
CODEX_HOME="$RUN/home/codex" python3 "$AGENTIFY/skills/agentify/scripts/mine_transcripts.py" \
  --repo "$RUN/repos/codex-history" --target codex --days 7 > "$RUN/out/codex-history/transcripts.json"
```

**Pass conditions**, all four read off that one JSON — *measured 2026-09-16 by running this recipe at the current revision, at the script level; no live skill run stands behind them:*

| Field | Expected | Why it is the assertion |
|---|---|---|
| `sessions.count` | `2` | the 80-day-old *directory* was still read under `--days 7` (F11) |
| `sessions.user_turns_total` | `8` | 9 planted human turns, minus the one `event_msg` copy, minus the one turn dated outside the window — the consent window filters content, not files (F05) |
| `commands_requested` | `[{"command": "npm test", "count": 3}]` | the three identical turns stayed three. A count of `1` here is F10, returned |
| `request_shapes[0]` | skeleton `add api endpoint with validation`, `count` 4, `sessions` 2 | the shape crosses both sessions, including the resumed one |

Re-running the same command with `--days 365` must lift `user_turns_total` to `9` and move `sessions.first` back 80 days. If the two windows return the same number, the window is not being enforced — that is F05, and it is a release blocker rather than a curiosity.

### Fixture 9: linked instruction files

A shared store linked into both trees is how a real team keeps one copy of a skill, and every link is a file agentify must **count once and never edit**. The audit found the identity map missing `.agents/skills`, mis-stemming `.codex/agents/*.toml` and lacking `.codex/rules` (F14), so the fixture links one artifact into each of those roots and one out of the repo entirely.

```bash
SLUG=linked
R="$RUN/repos/$SLUG"
mkdir -p "$R"/{shared/agent-store/{skills/qa,agents,rules},.agents/skills,.codex/{agents,rules},.claude/skills,src}
mkdir -p "$RUN/outside/skills/leaked"

cat > "$R/shared/agent-store/skills/qa/SKILL.md" <<'EOF'
---
name: qa
description: Shared QA skill kept in one in-repo store and linked into both trees.
---
Run the suite.
EOF
cat > "$R/shared/agent-store/agents/qa.toml" <<'EOF'
name = "qa"
description = "Shared reviewer agent."
developer_instructions = "Review the diff."
EOF
cat > "$R/shared/agent-store/rules/house.rules" <<'EOF'
# shared command policy
def on_command(cmd):
    return "ask"
EOF
cat > "$RUN/outside/skills/leaked/SKILL.md" <<'EOF'
---
name: leaked
description: A store outside the repo and outside HOME.
---
Nothing.
EOF

ln -s ../../shared/agent-store/skills/qa        "$R/.agents/skills/qa"
ln -s ../../shared/agent-store/skills/qa        "$R/.claude/skills/qa"
ln -s ../../shared/agent-store/agents/qa.toml   "$R/.codex/agents/qa.toml"
ln -s ../../shared/agent-store/rules/house.rules "$R/.codex/rules/house.rules"
ln -s "$RUN/outside/skills/leaked"              "$R/.claude/skills/leaked"

printf 'export const x = 1;\n' > "$R/src/index.ts"
printf '{"name":"linked","scripts":{"test":"node --test"}}\n' > "$R/package.json"
printf '# Linked\n' > "$R/AGENTS.md"
ln -s AGENTS.md "$R/CLAUDE.md"          # one file, two names
git -C "$R" init -q && git -C "$R" add -A && git -C "$R" commit -qm "init"
```

**Pass conditions on `discovery.json`** — *measured 2026-09-16 by running this recipe; script level only:*

- `existing_agentic_config.counts` is `{"skills": 1, "agents": 1, "rules": 1, "hooks": 0}`. One skill, not two: the two links resolve to the same store and are counted once.
- `existing_agentic_config.symlinked` names **all four in-repo links**, under the spelling the count list uses:
  `skills` → `.agents/skills/qa -> shared/agent-store/skills/qa` and `.claude/skills/qa -> …`;
  `agents` → `.codex/agents/qa.toml -> shared/agent-store/agents/qa.toml` (the counted name is `qa`, not `qa.toml`);
  `rules` → `.codex/rules/house.rules -> shared/agent-store/rules/house.rules`.
  **A link that is counted and missing from `symlinked` is F14 returning**, and it is the list the plan reads to know what it must never edit.
- One warning says `1 symlink(s) under the agent config directories resolved outside the repo and your home directory and were not followed` — the out-of-repo store is refused, not followed.
- One warning says `CLAUDE.md and AGENTS.md are the SAME file … write the index-doc section exactly once`. In §5 the index-doc step must honour it: **one** appended block, in `AGENTS.md`.
- After §5 and §8, `git -C "$R" status --porcelain` shows nothing under `shared/agent-store/`, and every link is still a link (`test -L`). A symlinked or vendored artifact is never edited at all.

### Fixture 10: invalid configuration

Two different failures share this fixture: a config the user broke, which agentify must refuse rather than repair, and an artifact agentify itself generated badly, which the verifier must not wave through (F13).

```bash
SLUG=invalid
R="$RUN/repos/$SLUG"
mkdir -p "$R"/{.codex/agents,.claude,docs/agentic-setup,src}
printf 'console.log(1)\n' > "$R/src/index.js"
printf '{"name":"invalid","scripts":{"test":"node --test"}}\n' > "$R/package.json"

# (a) the USER's settings.json, truncated mid-object
printf '{\n  "hooks": {\n    "PreToolUse": [\n' > "$R/.claude/settings.json"

# (b) a generated Codex subagent whose TOML does not parse (unterminated string)
cat > "$R/.codex/agents/qa.toml" <<'EOF'
# agentify-id: qa
# agentify-version: 0.1.0
# agentify-generated: 2026-09-16
# Safe to delete or edit.
# agentify-evidence: 3 review requests in 2 sessions
name = "qa
description = "Runs the suite and reads the failures."
developer_instructions = "Run node --test and report."
EOF

# (c) a generated Codex MCP draft whose TOML does not parse (duplicate key)
cat > "$R/docs/agentic-setup/codex-mcp.toml" <<'EOF'
# agentify-id: mcp-draft
# agentify-version: 0.1.0
# agentify-generated: 2026-09-16
# Safe to delete or edit.
# agentify-evidence: 1 service named in the manifests
[mcp_servers.linear]
command = "npx"
command = "uvx"
EOF
git -C "$R" init -q && git -C "$R" add -A && git -C "$R" commit -qm "init"
```

Write a `build-manifest.json` beside them, exactly as phase 7 would have (`build-and-verify.md` §5): (b) is `{"type": "subagent", "format": "toml"}`, (c) is `{"type": "mcp", "format": "toml"}`, both `action: created`, `created_dirs` holds `.codex/agents` and `.codex`, and `uncommitted_paths` holds both paths.

```bash
python3 - "$R" <<'PY'
import json, os, sys
R = sys.argv[1]
manifest = {
    "schema_version": 1, "tool": "agentify", "generated": "2026-09-16", "target": "codex",
    "repo_root": R, "plan_dir": "docs/agentic-setup",
    "mode": "stage-only", "branch": None, "base_branch": "main", "base_commit": "",
    "committed": False,
    "created_dirs": [".codex/agents", ".codex"],
    "committed_paths": [],
    "uncommitted_paths": [".codex/agents/qa.toml", "docs/agentic-setup/codex-mcp.toml"],
    "artifacts": [
        {"id": "qa", "type": "subagent", "path": ".codex/agents/qa.toml",
         "action": "created", "format": "toml", "ignored": False,
         "evidence": "3 review requests in 2 sessions"},
        {"id": "mcp-draft", "type": "mcp", "path": "docs/agentic-setup/codex-mcp.toml",
         "action": "created", "format": "toml", "ignored": False,
         "evidence": "1 service named in the manifests"},
    ],
    "_agentify": {"agentify-id": "build-manifest", "agentify-version": "0.1.0",
                  "agentify-generated": "2026-09-16",
                  "agentify-evidence": "synthetic malformed-artifact fixture"},
}
path = os.path.join(R, "docs", "agentic-setup", "build-manifest.json")
json.dump(manifest, open(path, "w"), indent=2)
print("wrote", path)
PY
```

Then run the verifier on **both interpreters**:

```bash
mkdir -p "$RUN/out/invalid"
for P in /usr/bin/python3 python3; do
  V="$($P -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
  $P "$AGENTIFY/skills/agentify/scripts/verify_artifacts.py" \
     --repo "$R" --manifest "$R/docs/agentic-setup/build-manifest.json" \
     > "$RUN/out/invalid/verify-$V.json"
  echo "$P ($V) exit=$?"
done
```

**Pass conditions.** The two interpreters are *expected to differ*, and the difference is the finding's repair rather than a bug — `tomllib` is 3.11+, there is no stdlib TOML parser below it, and the third outcome is `unverified`, said out loud. *Measured 2026-09-16 by running this recipe:*

| Check | Python 3.14 | Python 3.9.6 |
|---|---|---|
| `subagent_frontmatter` | `fail` — `TOML does not parse (TOMLDecodeError: Illegal character …)` | `fail` — on the name/stem mismatch, with `TOML syntax NOT verified: this interpreter is Python 3.9 and tomllib is 3.11+` appended |
| `mcp_json` | `fail` — `TOML does not parse (TOMLDecodeError: Cannot overwrite a value …)` | **`unverified`** — `… found by a partial scan (linear), but TOML syntax NOT verified …` |
| `summary` | `{"pass": 17, "fail": 2, "warn": 1, "unverified": 0}` | `{"pass": 17, "fail": 1, "warn": 1, "unverified": 1}` |
| exit code | `0` | `0` |

**A `pass` on either row, on either interpreter, is F13 returning** — a partial scan reporting a parse success. An `unverified` row is a correct answer on 3.9 and a wrong one on 3.11+; a `fail` on 3.9's `mcp_json` means something is claiming a parse it cannot have done. The surviving `warn` on `core_set` (`zero skills …`) is expected: this fixture builds two artifacts and no skill, and the check is telling the truth about them.

Then the other half, which needs a real run: invoke the skill against this repo with a plan containing any hook, and let §5 reach the registration merge. `build-and-verify.md` §2.4a step 2 is the assertion — **the merge stops**: `.claude/settings.json` is byte-identical afterwards, `.claude/settings.json.agentify-proposed` exists holding the intended content, and `report.md`'s `## Needs you` carries an item naming the file. A settings file that parses afterwards has been repaired or overwritten, and both are forbidden.

### Fixture 11: mature setup with a shared matcher group

This is the fixture the undo leg turns on, and the one no public repo supplies. It plants the exact shape of both preservation findings:

- **F07 — a shared matcher group.** The user's `tools/fmt.sh` and `tools/block-npm.sh` are already registered. Agentify's hook appends *into* the `Bash` group rather than replacing it, and a rerun must replace only its own nested handler.
- **F06 — a same-basename user script.** `tools/block-npm.sh` (the user's) and `.claude/hooks/block-npm.sh` (generated) share a basename and share a matcher group. An undo keyed on the basename removes both.

```bash
SLUG=mature-shared
R="$RUN/repos/$SLUG"
mkdir -p "$R"/{.claude/hooks,.claude/skills/deploy,tools,src,docs/agentic-setup}
printf '{"name":"mature","scripts":{"test":"bun test","lint":"eslint ."}}\n' > "$R/package.json"
: > "$R/bun.lock"
printf 'export const x = 1;\n' > "$R/src/index.ts"
printf -- '---\nname: deploy\ndescription: The team'"'"'s own deploy skill.\n---\nShip it.\n' \
  > "$R/.claude/skills/deploy/SKILL.md"
printf '#!/bin/sh\n# The USER OWNS THIS. Same basename as the hook agentify generates.\nexit 0\n' \
  > "$R/tools/block-npm.sh"
printf '#!/bin/sh\nexit 0\n' > "$R/tools/fmt.sh"
chmod +x "$R/tools/block-npm.sh" "$R/tools/fmt.sh"

cat > "$R/.claude/settings.json" <<'EOF'
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PROJECT_DIR}/tools/block-npm.sh"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PROJECT_DIR}/tools/fmt.sh"
          }
        ]
      }
    ]
  },
  "permissions": {
    "allow": [
      "Bash(bun run test:*)"
    ],
    "deny": [
      "Read(./.env)"
    ]
  }
}
EOF
git -C "$R" init -q && git -C "$R" add -A && git -C "$R" commit -qm "init"

# One unrelated edit left dirty on purpose: gate 4 requires unrelated changes to be preserved.
printf 'export const y = 2;\n' >> "$R/src/index.ts"
```

The Codex half of this fixture is the same shape one directory over: `.codex/hooks.json` with the user's handler under `PreToolUse`, matcher `^(Bash|exec_command|shell_command|local_shell|exec|run)$`, and `.codex/hooks/` for the generated script. Build it when running the Codex pass; the assertions in §7 and §8 are written against whichever file the manifest names, not against a filename.

**Record the pre-run truth before invoking anything**, because nothing recovers it afterwards:

```bash
mkdir -p "$RUN/evidence/$SLUG"
shasum -a 256 "$R/.claude/settings.json" > "$RUN/evidence/$SLUG/settings.pre"
git -C "$R" status --porcelain -uall           > "$RUN/evidence/$SLUG/status.pre"
( cd "$R" && { find . -path ./.git -prune -o -type d -print | sed 's|^|DIR  |'
               find . -path ./.git -prune -o -type f -print0 \
                 | xargs -0 shasum -a 256 2>/dev/null | sed 's|^|FILE |'; } \
             | LC_ALL=C sort ) > "$RUN/evidence/$SLUG/tree.pre"
```

### Alternates

Swap in if a repo above becomes unrepresentative: https://github.com/psf/requests (Python, smaller than Flask), https://github.com/excalidraw/excalidraw (large TS app, not a monorepo), https://github.com/EveryInc/compound-engineering-plugin (`CLAUDE.md` plus a large `skills/` tree — a second maturity case).

## Running the regression

### 0. Set up

```bash
export AGENTIFY=/path/to/agentify            # your checkout of this repo
export RUN=/tmp/agentify-regression
mkdir -p "$RUN/repos" "$RUN/out" "$RUN/evidence"
```

**Clone in full. No `--depth`, and no `--filter` unless you read the trade-off below and accept it.**

```bash
cd "$RUN/repos"
git clone https://github.com/chalk/chalk.git
git clone https://github.com/vercel/commerce.git
git clone https://github.com/pallets/flask.git
git clone https://github.com/calcom/cal.com.git
git clone https://github.com/mvanhorn/last30days-skill.git
git clone https://github.com/vercel/vercel-plugin.git
```

Then build fixtures 1 and 8–11 from their recipes above. They need no network at all.

**Not `--depth 1`.** `mine_git.py` has no fixed window any more: with no `--days` it widens 180d → 365d → 1095d → 3650d → all history and stops at the first rung holding 50 commits. A shallow clone therefore does not *fail* — it reports `window.mode: adaptive` and a `window.reason` saying no rung cleared the floor — but it measures a repo that does not exist, and it does so quietly. Read `window.reason` on every run before trusting a co-change cluster.

**Not `--filter=blob:none` by default, and this file used to say the opposite.** A blobless clone has every commit and every tree and almost no blobs. `git log --numstat` has to read blob *content* to count lines, so on that clone git fetches the blobs back from the promisor remote one at a time — network traffic, inside a tool whose contract (PRD §13) is that it makes none. Measured on blobless clones before `mine_git.py` handled it: **61–79 seconds** on chalk and commander.js, each run ending in `available: false` with every git statistic empty. The documented harness produced **no git evidence at all, slowly**, on every fixture in the table.

That is fixed on the tool side — `mine_git.py` now classifies the clone before the log pass and reads path evidence with `git log --name-only --no-renames`, which needs no blobs (re-measured 2026-09-05 through the script: chalk 0.19s, commander.js 0.13s, axios 0.14s, all `available: true`, against 0.17s for a full clone of chalk). **So a blobless clone works now.** What it still costs, and why it is not the default here:

- `hotspots[].churn` is **0 on every row**. Rank by `commits`; never quote churn from such a run, and never compare churn between two fixtures cloned differently.
- Renames read as a delete plus an add rather than one move, so a renamed path carries one extra commit. Measured on chalk, blobless against full at the same window: 3 of 20 `hotspots` rows off by one, two `directory_hotspots` rows off by one, 1 of 15 co-change clusters at support 8 instead of 7. No row appeared or vanished.
- Every such run carries a `partial clone detected (...)` warning naming the cause and the fix. **If you see that warning in a run whose numbers you are about to record in the table, you cloned with a filter** — note it in the row or re-clone.

`--filter=blob:none` is a legitimate choice for `cal.com`, the one fixture where a full clone is a heavy download, provided you record that the row was measured that way. It is not a blanket optimization: apply it to the whole set and every churn figure in this document becomes 0 and every rename-touched count shifts, with nothing but a warning to say why.

### 1. Run the three analyzers

For each repo:

```bash
SLUG=chalk
REPO="$RUN/repos/$SLUG"
OUT="$RUN/out/$SLUG"; mkdir -p "$OUT"
TARGET=claude-code                # codex on the Codex pass, and on fixture 8 always

time python3 "$AGENTIFY/skills/agentify/scripts/discover.py" \
  --repo "$REPO" > "$OUT/discovery.json"

python3 "$AGENTIFY/skills/agentify/scripts/mine_transcripts.py" \
  --repo "$REPO" --target "$TARGET" > "$OUT/transcripts.json"

time python3 "$AGENTIFY/skills/agentify/scripts/mine_git.py" \
  --repo "$REPO" --no-gh > "$OUT/git.json"
```

**Run the miner once per target, not once per harness.** `--target claude-code` and `--target codex` read different trees and answer different questions, and until fixture 8 existed this file only ever ran the first — which is how a release harness came to contain no Codex coverage at all. On fixture 8, set `CODEX_HOME="$RUN/home/codex"` so the miner reads the synthetic history and never your own.

`--no-gh` is not optional here. It is what `SKILL.md` phase 2 passes on every default run, and `gh pr list` is the only network-capable path in the whole toolchain — omitting it makes step 2's "no network" assertion untestable, because the harness would be the thing making the call.

A fresh clone has no transcripts on your machine, so `mine_transcripts.py` should report `history_bucket: "none"`, a populated `warnings` array, and **exit 0**. A non-zero exit there is a bug.

### 1a. Run the selftests first — they are cheaper than a bad regression run

Before any fixture, confirm the toolchain itself is green. Every script and every shared lib
carries its own checks; a red one explains a wrong count faster than reading a plan does.

**Both interpreters, every time.** A recent defect passed on 3.11+ and failed on the documented 3.9 floor, so a single-interpreter run proves half of what it looks like it proves.

```bash
cd "$AGENTIFY/skills/agentify/scripts"
for P in /usr/bin/python3 python3; do          # the 3.9 floor, then your current python3
  for s in discover mine_transcripts mine_git verify_artifacts; do
    $P "$s.py" --selftest > /dev/null || echo "RED: $P $s.py"
  done
  for m in scrub textnorm emit; do
    $P "lib/$m.py" > /dev/null || echo "RED: $P lib/$m.py"
  done
done
```

Silence means green. Each script's `--selftest` prints a JSON pass/fail report and exits 1 if any
check fails; the libs print `N passed, M failed`. **Do not record the pass counts anywhere** — they
move every time a check is added, and every document that has pinned them has been stale within the
week. The exit code is the contract, not the number. **A check that can only pass on one interpreter is a bug**, in the check or in the script, and never a property of the fixture.

### 2. Assertions that must hold for every repo

Independent of the counts, and cheap enough to run every time:

```bash
python3 - "$OUT" <<'PY'
import json, os, sys
out = sys.argv[1]
for name in ("discovery.json", "transcripts.json", "git.json"):
    path = os.path.join(out, name)
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)                       # stdout is exactly one JSON object
    assert doc["schema_version"] == 1, name
    assert "warnings" in doc and isinstance(doc["warnings"], list), name
    print("%-18s ok  %6d bytes  warnings=%d" % (name, os.path.getsize(path), len(doc["warnings"])))
    if name == "git.json":
        # available:false on a repo that has a git history means the miner gave up.
        # It is what a blobless clone used to return, after 61-79s of network fetches.
        assert doc["available"], "mine_git.py: available is false -- read git.json warnings"
        assert doc["window"]["commits_analyzed"] > 0, "mine_git.py: no commits analyzed"
        partial = [w for w in doc["warnings"] if w.startswith("partial clone detected")]
        if partial:
            print("%-18s NOTE partial clone: churn is 0 on every hotspot row" % "")
size = os.path.getsize(os.path.join(out, "transcripts.json"))
assert size <= 12288, "miner output over the ~3k-token context budget: %d bytes" % size
PY
```

- `discover.py` finishes in **under 10 seconds**, including on `cal.com`. That is the budget the `time` above is checking.
- `mine_git.py` finishes in **under 5 seconds** on every fixture, full clone or blobless, and reports `available: true`. Both halves matter and they fail together: the pre-fix blobless behaviour was 61–79s *and* `available: false`. A run that takes tens of seconds is the tool fetching objects over the network, which is a release blocker on its own, so time this one — do not just read its JSON.
- `transcripts.json` stays **at or under ~12 KB (~3k tokens)** no matter how much history fed it. Test this on a repo where you personally have heavy history, not just on fresh clones.
- **No network.** Run the analyzers with networking disabled (or watch them under `lsof`/a proxy) and confirm nothing changes. Any outbound call is a release blocker.
- **No secrets.** Grep every output for `AKIA`, `sk-`, `ghp_`, `eyJ`, `BEGIN * PRIVATE KEY`, and your own home directory path. Hits should appear only as `[REDACTED:<kind>]` or `~`.
- **Repo untouched.** `git -C "$REPO" status --porcelain` is empty after the analyzers run — except on fixture 11, where it must still show exactly the one unrelated edit you left there and nothing else. They are read-only.

### 3. Run the skill to the plan gate

Open the agent in the clone and invoke agentify. Answer the consent prompt, reply `defaults` at the interview, `ok` at the shortlist, and **stop at phase 6 the first time**: read the plan, then decline approval. Nothing should be written outside `docs/agentic-setup/plan.md`, and no branch should be created.

```bash
git -C "$REPO" status --porcelain     # expect only docs/agentic-setup/plan.md (plus fixture 11's one unrelated edit)
git -C "$REPO" branch --list 'agentic-setup/*'   # expect no output
```

A build that starts without approval is the most serious failure this harness can catch. It invalidates the run: fix it before looking at anything else.

**The shortlist is a gate of its own and its `ok` is not the plan's approval** (`SKILL.md` phase 6). A run that went straight from the shortlist to writing files has failed this step even if the plan looks right.

Then invoke again and, this time, approve: `approved`. **Everything from §5 onward assumes that approval exists and was recorded.** Approving is also what makes §7's rerun a rerun rather than a first run.

### 4. Check the plan against the floor and the catalogue walk

Two checks, and neither is a count comparison.

**4a. The floor held.** Read the plan's summary section and its catalogue walk:

```bash
sed -n '1,60p' "$REPO/docs/agentic-setup/plan.md"
```

Every artifact named in that repo's **Floor** column is present, under the catalogue's own name — `pr-reviewer` is never renamed to signal a nuance, and a skill + subagent pair counts as present only when both halves are. A floor item that is missing is a failure unless the walk row for it gives an outcome from the fixed vocabulary; "it would restate `CLAUDE.md`", "a vendored guide exists", "installed at user scope" and "the procedure is documented" are none of them outcomes. **The walk has one row per catalogue row on every fixture**, including fixture 1 — a short walk is the failure mode the walk was added to catch.

**4b. Nothing was fabricated, and nothing was pre-cut.** Record what was built against what the floor asked for, plus the two failure directions.

> **This table is empty because nobody has run it.** Every cell below is unmeasured. Do not fill one from a plan you skimmed, from a floor you read off `blueprint.md`, or from another contributor's recollection — a number here means *this row was run on this date at this revision*. Put the date and the revision in `Notes` when you fill a row, and leave the rest empty until someone runs them. **Delete this paragraph when every row has a run behind it, and not before.**

| Repo | Skills | Subagents | Rules | Hooks | Floor met? | Walk rows = catalogue rows? | Notes |
|---|---|---|---|---|---|---|---|
| fresh | | | | | | | |
| chalk | | | | | | | |
| commerce | | | | | | | |
| flask | | | | | | | |
| cal.com | | | | | | | |
| last30days-skill | | | | | | | |
| vercel-plugin | | | | | | | |
| codex-history | | | | | | | |
| linked | | | | | | | |
| invalid | | | | | | | |
| mature-shared | | | | | | | |

The counts are recorded so the ranges can eventually be *described*; they are not an acceptance criterion and no run fails for being above one. Then read the plan, because only reading catches either real failure. **Fabrication:** spot-check three artifacts per repo by tracing each one's cited evidence back to the analyzer JSON it came from — an artifact citing a count that does not appear in `discovery.json`, `transcripts.json` or `git.json` is invented, and that is a release blocker. **Pre-cutting:** grep the plan for *cap*, *limit* and *quota*, which must not appear at all, and read the walk's outcomes for a sentence arguing that this repo needs less than the catalogue. The first failure makes the product untrustworthy; the second makes it useless. Both are found by reading.

### 5. The build leg

Phase 7 runs from the approval recorded in §3. Let it run to its own stop condition — every approved item written or abandoned with a reason — then check the build without reading a single template line: **every assertion below is read off `build-manifest.json`**, because that file is the only place the undo facts outlive the run (`build-and-verify.md` §5).

```bash
M="$REPO/docs/agentic-setup/build-manifest.json"
python3 - "$REPO" "$M" <<'PY'
import json, os, subprocess, sys
repo, path = sys.argv[1], sys.argv[2]
m = json.load(open(path, encoding="utf-8"))

# (1) the manifest is complete enough to generate an undo from
for field in ("mode", "branch", "base_branch", "base_commit", "committed",
              "created_dirs", "committed_paths", "uncommitted_paths", "artifacts"):
    assert field in m, "manifest is missing %s -- phase 8 cannot generate an undo" % field
assert m["mode"] in ("branch", "stage-only", "no-git"), m["mode"]
assert not m.get("pushed") and not m.get("pr_url"), "agentify never pushes and never opens a PR"

# (2) every artifact carries what picks its undo
paths = set()
for a in m["artifacts"]:
    for field in ("id", "type", "path", "action", "evidence", "format", "ignored"):
        assert field in a, "%s is missing %s" % (a.get("path"), field)
    assert a["evidence"].strip(), "%s has an empty evidence line" % a["path"]
    assert not os.path.isabs(a["path"]) and ".." not in a["path"].split("/"), a["path"]
    if a["action"] == "modified":
        assert a.get("pre_existing_sha256"), "%s: no pre-run hash, so no undo can prove itself" % a["path"]
        assert a.get("restore") in ("head", "span"), a["path"]
    if a.get("merge"):
        assert a["merge"]["strategy"] in ("json-entries", "toml-table"), a["path"]
        assert a.get("pre_existing_sha256"), "%s: merge record without a pre-run hash" % a["path"]
        for entry in a["merge"]["entries"]:
            if entry[0] == "hook_command":
                assert len(entry) == 3, "hook_command must carry its event: %r" % (entry,)
    paths.add(a["path"])

# (3) the partition covers every artifact exactly once -- a path in neither is a file no undo removes
c, u = set(m["committed_paths"]), set(m["uncommitted_paths"])
assert not (c & u), "a path is in both lists: %s" % sorted(c & u)
assert paths <= (c | u), "in neither list: %s" % sorted(paths - (c | u))

# (4) a restore:span entry on the branch is data loss, not a reporting problem
for a in m["artifacts"]:
    if a.get("restore") == "span":
        assert a["path"] not in c, "%s is restore:span and committed -- the undo DELETES the user's file" % a["path"]

# (5) branch mode really committed something, and it committed what it says.
#     Enumerate the whole branch, never one commit -- the report is the run's SECOND commit.
#     With no BASE_COMMIT (a repo with no commits before the run) the branch IS the history,
#     so `git diff` has nothing to diff against and `git log` is the only form that answers.
if m["mode"] == "branch":
    if m["base_commit"]:
        argv = ["diff", "--name-only", "%s..%s" % (m["base_commit"], m["branch"])]
    else:
        argv = ["log", "--name-only", "--pretty=format:", m["branch"]]
    out = subprocess.run(["git", "-C", repo] + argv, capture_output=True, text=True).stdout.split()
    on_branch = set(out)
    assert on_branch, "branch mode but the branch holds nothing -- the delete would remove no file"
    assert c <= on_branch, "claimed committed but not on the branch: %s" % sorted(c - on_branch)
    assert not (u & on_branch), "claimed uncommitted but on the branch: %s" % sorted(u & on_branch)
print("build manifest OK: mode=%s artifacts=%d committed=%d uncommitted=%d"
      % (m["mode"], len(m["artifacts"]), len(c), len(u)))
PY
```

Then the four checks a script cannot make:

- **Nothing was overwritten.** Every `action: modified` file is a file that already existed, and the bytes outside agentify's markers or merged entries are unchanged. On fixture 11, `.claude/settings.json` has legitimately changed — so read its *entries*, not its hash: `python3 -c "import json;d=json.load(open('$REPO/.claude/settings.json'));print(json.dumps(d,indent=1))"` and confirm every pre-existing handler, group, event and permission string is still there and still spelled the same, with agentify's appended beside them.
- **Nothing was restructured, moved or renamed.** `git -C "$REPO" status --porcelain -uall` shows additions and the modifications the manifest names. An `R` line is a failure on any fixture. On fixture 9, no file under `shared/agent-store/` appears at all, and every link is still a link (`test -L`).
- **The unrelated dirty edit survived.** On fixture 11 the one line appended to `src/index.ts` before the run is still the only change to that file: `git -C "$REPO" diff --stat -- src/index.ts` reads `1 +`, and `grep -c 'agentify' "$REPO/src/index.ts"` is `0`. A run that staged, reverted or absorbed that edit has failed gate 4's "unrelated changes are preserved" outright.
- **The build order was rules → hooks → permissions → skills → subagents → MCP → index doc**, with a checkpoint after each type, and the index-doc section's tables name files that exist. An index doc written first is `blueprint.md` §9's defect returning.

On Codex, one more, and it is a claim rather than a check: the run may say the hooks are **installed**, and may not say they are live. Project trust and `/hooks` arming are the user's steps and belong in `## Needs you`. A run that says the guardrails are active has overclaimed (`adapters/codex.md` §4.3; `verification.md` §5.3).

### 6. The verify leg

Phase 8's static pass, with both paths absolute and `--discovery` supplied — it is optional to the script and mandatory here, because it turns on the only half of `rule_contradiction` that can FAIL:

```bash
python3 "$AGENTIFY/skills/agentify/scripts/verify_artifacts.py" \
  --repo "$REPO" \
  --manifest "$REPO/docs/agentic-setup/build-manifest.json" \
  --discovery "$RUN/out/$SLUG/discovery.json" > "$RUN/out/$SLUG/verify.json"
echo "exit=$?"
```

**Pass conditions:**

- **Exit 0.** Exit 1 means the manifest could not be read at all, and then `checks` is `[]` and `summary` is all zeros — *not* the same thing as everything passing, and the difference has been missed before. Check `summary`, never the exit code alone.
- **No `fail` row survives the hand-off.** A `fail` ends one of exactly two ways (`SKILL.md` phase 8 step 3): fixed and re-tested, or removed and moved to the report's Skipped table with the reason `failed verification and was removed`. A `fail` still sitting in the report at hand-off is the failure.
- **`rule_contradiction` does not say `conventions NOT checked`.** If it does, `--discovery` was not passed and the run is not a verify leg. On fixture 11 this is the row that catches a generated rule saying `npm` in a repo holding `bun.lock`.
- **`core_set` is read, not skimmed.** It warns when a licensed core artifact is missing; on any fixture but 10 a `zero skills` warning means §5 built nothing and the catalogue walk failed upstream.
- **`unverified` is a real outcome and is counted separately.** On Python 3.9/3.10 every TOML syntax row comes back `unverified` with the interpreter named. Record which interpreter the leg ran on; an evidence record that does not name it cannot be read later.
- Run the live tests in `verification.md` §§4–8 and record each one's result, including the ones that did not run. `--exec-hooks` is off by default and needs the explicit §5.1 yes; a leg run without it has **statically** checked the hooks and must say so rather than implying the hook was exercised.

### 7. The rerun leg — idempotency

Invoke the skill again, in the same repo, immediately, and approve the same plan. A rerun updates in place; it never duplicates and never touches the user's edits (`SKILL.md` phase 7, "Never overwrite").

```bash
( cd "$REPO" && { find . -path ./.git -prune -o -type f -print0 \
    | xargs -0 shasum -a 256 2>/dev/null; } | LC_ALL=C sort ) > "$RUN/evidence/$SLUG/tree.after-build"
# ... rerun the skill, approve the same plan ...
( cd "$REPO" && { find . -path ./.git -prune -o -type f -print0 \
    | xargs -0 shasum -a 256 2>/dev/null; } | LC_ALL=C sort ) > "$RUN/evidence/$SLUG/tree.after-rerun"
diff "$RUN/evidence/$SLUG/tree.after-build" "$RUN/evidence/$SLUG/tree.after-rerun"
```

**Pass conditions:**

- **No new file appeared** whose name is a variant of one already there — no `qa-2`, no `block-npm.1.sh`, no second `.claude/rules/api.md`.
- **The index doc holds exactly one `agentify:begin` for each id.** `grep -c 'agentify:begin' CLAUDE.md` (or `AGENTS.md`) equals the number of distinct ids, and the bytes outside the markers are unchanged. Two blocks with the same id is the append-instead-of-rewrite defect.
- **The hook registration still holds exactly one handler per generated hook, and the user's are all still there.** On fixture 11, after the rerun the `PreToolUse`/`Bash` group holds **two** handlers — the user's `tools/block-npm.sh` and agentify's `.claude/hooks/block-npm.sh` — in that order, and `PostToolUse` is untouched. Three handlers means the merge appended instead of replacing in place; one means it replaced the wrong one, which is F07.

  *Measured 2026-09-16 at the script level, driving `build-and-verify.md` §2.4a steps 4–5 directly against fixture 11 rather than through a live run:* first merge `appended`, second merge `replaced-in-place`, the group holding the same two handlers both times. **This has not been observed through the skill itself.**
- **`plan.md`, `report.md` and `build-manifest.json` were regenerated wholesale and kept their `agentify-id`.** They carry no markers by design; a second copy of any of them is a defect.
- **Every `pre_existing_sha256` in the new manifest still names the pre-*first*-run bytes**, not the bytes the first run left. A rerun that re-baselines its own output makes the undo restore the built state instead of the original — the single most dangerous way this leg can pass while being wrong.
- **The rerun is verified too.** Re-run §6 against the new manifest; a rerun that silently drops a check is not covered by the first run's evidence.

### 8. The undo leg — and it is the user's files that are on trial

Take the removal section out of `report.md` and **paste it top to bottom, in printed order, changing nothing**. Not the commands you remember, not a reordering that looks safer: the sequence is executed by a human reading down the page, so an ordering defect is a correctness defect (`report-template.md` §3.1). `verification.md` §10.4 rehearses this on a copy first and is mandatory whenever the mode is `stage-only` or `no-git`, whenever `uncommitted_paths` is non-empty, whenever the run appended to a pre-existing file, and whenever it merged into a JSON config — which is **every run that builds a hook, on both targets**.

```bash
# after pasting the report's "How to remove everything", in order
( cd "$REPO" && { find . -path ./.git -prune -o -type d -print | sed 's|^|DIR  |'
                  find . -path ./.git -prune -o -type f -print0 \
                    | xargs -0 shasum -a 256 2>/dev/null | sed 's|^|FILE |'; } \
                | LC_ALL=C sort ) > "$RUN/evidence/$SLUG/tree.post"
diff "$RUN/evidence/$SLUG/tree.pre" "$RUN/evidence/$SLUG/tree.post"     # expect: no output
git -C "$REPO" branch --list 'agentic-setup/*'                          # expect: no output

git -C "$REPO" status --porcelain -uall > "$RUN/evidence/$SLUG/status.post"
diff "$RUN/evidence/$SLUG/status.pre" "$RUN/evidence/$SLUG/status.post" # expect: no output
diff <(shasum -a 256 "$REPO/.claude/settings.json") \
     "$RUN/evidence/$SLUG/settings.pre"                                 # expect: no output
```

`diff tree.pre tree.post` is the whole assertion in one line, and it is the only check here that cannot pass for the wrong reason: it compares every file's **hash** and every directory's presence against what was on disk before the skill was ever invoked. The three lines under it say *which* thing went wrong when it fails.

**The four assertions, in the order they are most often lost:**

1. **A hook sharing a matcher group with a generated one survives.** After the undo, fixture 11's `PreToolUse`/`Bash` group still exists and still holds `${CLAUDE_PROJECT_DIR}/tools/block-npm.sh`. A group that vanished took the user's hook with it; that is F07, and it succeeds loudly — `Deleted branch`, exit 0, every step reporting success.
2. **A user script sharing a BASENAME with a generated one, at a different path, survives.** `tools/block-npm.sh` is still on disk, still executable, and still registered. This is F06 exactly: identity is the whole normalised command path **plus the event**, never a basename.
3. **Everything unrelated survives.** The other event (`PostToolUse`/`Write|Edit` → `tools/fmt.sh`), the user's permission strings (`Bash(bun run test:*)`, `Read(./.env)`), the user's own `deploy` skill, the ignored config the run never touched, and the one unrelated dirty edit in `src/index.ts`. `diff tree.pre tree.post` covers all of them in one line, which is why it is the check.
4. **Every path is covered by a mechanism, and every mechanism did something.** `verification.md` §10.2 fails the run when a manifest artifact is in neither the branch commit nor the report's per-file list. Coverage is necessary and not sufficient: a step that names a path and then no-ops reads as covered in every enumeration.

> **Do not accept the un-merge script's own success line as proof.** *Measured 2026-09-16:* run verbatim against fixture 11, `report-template.md` §3.1 block C printed `.claude/settings.json: 3 entry(s) removed, restored byte-for-byte (id=block-npm)`, left the user's handler, the other event and both permission strings intact, and restored the file to the pre-run hash — correct, on Python 3.9.6 and 3.14 alike. Then the same script with `key()` mutated to fall back to a **basename** — the F06 defect, re-injected as a negative control — removed **4** entries, deleted the user's `tools/block-npm.sh` registration *and* the whole `PreToolUse` group, **exited 0**, and printed `every entry this run does not own is still there, but the bytes differ from the pre-run file`. The script's built-in preservation check could not catch it, because that check builds "what I own" with the same identity function it is checking. The byte diff caught it immediately. **`diff tree.pre tree.post` is the assertion; the script's printed line is not.**
>
> That negative control is worth re-running whenever the undo changes: mutate `key()`, confirm the fixture goes red, restore it. A fixture that stays green under the mutation is not testing anything.

**Modes are not interchangeable.** A `stage-only` run's undo is the numbered per-file list and contains no branch delete; a `branch` run with a non-empty `uncommitted_paths` prints the branch delete **and** the per-file removal, and printing only the first is a report that reads as complete while leaving files behind. Check the wording against `build-and-verify.md` §9, which gives the three exact sentences.

**On Codex**, the summary must also carry the trust-and-arming sentence, and the undo must reach `.codex/hooks.json` — a Codex run whose un-merge matched nothing is the measured defect where the script was keyed on two Claude Code filenames. `SKIP … no agentify block id=…` on a JSON config, exit 0, is that failure wearing a success message.

### 9. What this harness cannot prove, and must therefore label

Gate 4 requires that any untested live feature be labeled. These are the ones, and the labels belong in the run's evidence record and in `report.md` — not quietly omitted:

| Feature | What the harness can say | What it may never say |
|---|---|---|
| Codex hooks | the JSON loads, the script runs under the smoke test, the file is in the right place | that the hook is **live**. Codex keys hook trust to a hash and the user arms it with `/hooks` (`adapters/codex.md` §4.3). Never emit or suggest `--dangerously-bypass-hook-trust` |
| Codex repo-scoped layer | the files were written | that they load. Everything under `.codex/` plus `AGENTS.md` is inert until the project is trusted, with no error anywhere |
| Codex subagents | the TOML parses (3.11+) or was **not parsed** (3.9/3.10), and the fields are present | that Codex loaded the agent, unless a `codex` binary was actually run and its output recorded |
| TOML syntax on Python 3.9/3.10 | `unverified`, with the interpreter named | `pass`. That was F13 |
| MCP drafts | the draft is well-formed config with env-var placeholders | that the server works. Nothing here authenticates, and no leg may be pointed at a real database, API or credential |
| Hook behaviour without `--exec-hooks` | statically checked | smoke-tested. The flag needs the explicit `verification.md` §5.1 yes |
| Anything a leg did not run | nothing | anything |

### 10. Clean up

```bash
rm -rf /tmp/agentify-regression
```

Keep `$RUN/evidence/` if you are recording a gate-4 result; copy it out before the `rm`.

## Recording results

Update the **Floor** column in [The set](#the-set) with what a real run actually produced, note the date and the agentify version you measured with, and remove the derived-not-measured paragraph once every row has a run behind it. Correct a floor when a licence turns out not to fire on that repo — with the field and the value that says why, so the next contributor can tell a corrected floor from a lowered one. Never turn an observed count back into a maximum: an over-floor run is evidence about the repo, and the only thing that fails it is an artifact whose evidence does not hold up.

For §§5–8, record per leg, per fixture, per target: the date, the agentify revision, the interpreter, the mode the run chose, and the four undo assertions as observed rather than expected. Then update [What this document has and has not been run through](#what-this-document-has-and-has-not-been-run-through) — a leg moves from "written" to "exercised" only there, and only with that record beside it. **A leg nobody ran stays "written", however confident the reading.**
