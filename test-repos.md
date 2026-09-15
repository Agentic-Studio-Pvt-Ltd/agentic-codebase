# Regression repos

The fixture set agentify is checked against before a release or a merged PR. Repos are **referenced by URL, never vendored** — clone them into a scratch directory, run against the clone, throw the clone away.

The set exists to cover the cases that break things, not to be comprehensive: no history, one language, a real app, a non-JS stack, a workspace monorepo, an existing index doc, and an existing agentic setup that a run must add to without touching.

> **Nothing here asserts a maximum.** The ranges this table used to carry were derived from the sizing caps in PRD §9, and **those caps were retired on 2026-09-07** — a run proposes the complete setup the evidence supports, and the user cuts at the phase 6 gate. What replaces them is a **floor plus a walk**: each row states the artifacts that repo's own structure licenses and which must therefore appear, and every row is additionally checked against the catalogue walk in step 4 below. A plan that produces *more* than its floor is not a finding. A plan that produces less than its floor, or that walks fewer rows than the catalogue has, is.
>
> **The floors below are DERIVED, not yet measured.** They are read off `blueprint.md` §1.3 — the core set and its licence fields — against what `discovery.json` reports for each repo, not off a completed run. The first contributor to run the full harness should record what was actually observed beside each floor, keep the floor where it held, correct it where the licence did not in fact fire, and delete this paragraph.

## The set

| # | Repo | Why it is in the list | Floor — must appear in the plan |
|---|---|---|---|
| 1 | *(synthesized locally — see [fixture 1](#fixture-1-fresh-repo) below)* | Fresh repo, no history, no transcripts. The degenerate case: the run must still reach a plan, and the plan must be derived rather than invented — **and it must not be empty**. | `setup-manager` (licence: always); `pr-reviewer` + `review-pr` (licence: `discovery.git.is_repo`, and `git init` satisfies it); a catalogue walk carrying a row and an outcome for every catalogue row |
| 2 | https://github.com/chalk/chalk | Small single-language JS library. Tiny surface, clear scripts, real conventions. Proves a thin repo gets a setup fitted to it — neither padded out nor pre-cut. | the row-1 floor, plus permissions (`discovery.commands` has ≥ 2 populated slots) and the package-manager and destructive-command hooks |
| 3 | https://github.com/vercel/commerce | Medium JS/TS application (Next.js). Framework detection, external services from deps and env var names, folder zones (`components`, `lib`, `app`). The mainstream case. | the row-2 floor, plus `qa` (it is a web app), `designer` + `new-component`, one zone rule per depth-1 zone discovery reports, and the env-leak hook (`.env*` present) |
| 4 | https://github.com/pallets/flask | Python repo. Checks that discovery reads `pyproject.toml`, tox/pytest config, and a Makefile rather than assuming `package.json` exists. | the row-2 floor, with every generated command quoting the real Python toolchain — a plan naming `npm` or `bun` anywhere is a hard failure here |
| 5 | https://github.com/calcom/cal.com | Large monorepo with workspaces (Turborepo, `apps/` + `packages/`). Checks the <10s discovery budget and the monorepo prompt (root by default, offer per-package). | the row-3 floor, plus `db-inspector` + `query-db` (it has a database), `security-auditor`, and a zone rule per workspace the interview scoped in |
| 6 | https://github.com/mvanhorn/last30days-skill | Already ships a `CLAUDE.md` **and** an `AGENTS.md`, with no `.claude/` config. Checks the merge path: append a delimited section, never overwrite, and ask which target when both index docs exist. | the row-1 floor; the index-doc section appended inside markers with every pre-existing byte unchanged. **The existing index doc covers an index-doc line and nothing else** — a rule, hook, skill or subagent skipped as "already covered by `CLAUDE.md`" is a failure |
| 7 | https://github.com/vercel/vercel-plugin | Mature setup: `.claude/settings.json` plus 7 skills in `.claude/skills/`. What this row now regresses is that maturity changes **nothing**: there is no audit-only mode, nothing existing is restructured, and the complete setup is still proposed. | the row-2 floor **in full**, proposed alongside the existing 7 skills. A candidate may be skipped only as covered by an artifact of the **same type, in this repo, doing the same job** — each such skip names that file, and `## Existing setup notes` says in writing that the existing setup did not limit what was proposed |

Row 7 is the one most likely to regress, so read its plan rather than counting it. Five things fail it outright: any sentence proposing audit-only or additions-only mode; anything restructuring, rewriting, moving or renaming an existing artifact; any skip citing `~/.claude/skills`, a vendored guide, an index-doc section or a document as coverage; any sentence arguing that this repo needs less than the catalogue (anti-pattern A17); and a missing `setup-manager`, whose inventory is the whole reason a repo with an existing setup gets one. The words *cap*, *limit* and *quota* must appear in no plan, on any fixture.

### Fixture 1: fresh repo

No public repo can be a true fresh-repo fixture — every clone arrives with history, and none of them has transcripts on your machine. Synthesize it:

```bash
mkdir -p /tmp/agentify-regression/repos/fresh && cd /tmp/agentify-regression/repos/fresh
git init -q
printf 'console.log("hello");\n' > index.js
printf '{\n  "name": "fresh",\n  "version": "0.0.0",\n  "scripts": { "test": "node --test" }\n}\n' > package.json
git add -A && git commit -qm "init"
```

This fixture is checked from both ends, and only reading the plan catches both.

**The floor.** With one commit and zero sessions there is no behavioural evidence at all, so every transcript-gated candidate belongs under `Skipped (insufficient evidence)` with a count of `0`. That is *not* the same as an empty plan: structural facts are evidence too, so `setup-manager` is still built, the catalogue is still walked row by row with an outcome recorded for each, and the plan still says in its own words that it rests on code and git history alone (`plan-template.md` §1.1). **A plan here with no skills in it at all has failed**, and so has one whose catalogue walk is shorter than the catalogue.

**The ceiling that is not a ceiling.** What must not appear is an artifact with no evidence behind it. A skill for a workflow this repo has one instance of is a fabrication whatever the total count is, and the fix is to trace each artifact's cited evidence back to the analyzer JSON rather than to compare a number against a range.

### Alternates

Swap in if a repo above becomes unrepresentative: https://github.com/psf/requests (Python, smaller than Flask), https://github.com/excalidraw/excalidraw (large TS app, not a monorepo), https://github.com/EveryInc/compound-engineering-plugin (`CLAUDE.md` plus a large `skills/` tree — a second maturity case).

## Running the regression

### 0. Set up

```bash
export AGENTIFY=/path/to/agentify            # your checkout of this repo
export RUN=/tmp/agentify-regression
mkdir -p "$RUN/repos" "$RUN/out"
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

time python3 "$AGENTIFY/skills/agentify/scripts/discover.py" \
  --repo "$REPO" > "$OUT/discovery.json"

python3 "$AGENTIFY/skills/agentify/scripts/mine_transcripts.py" \
  --repo "$REPO" --target claude-code > "$OUT/transcripts.json"

time python3 "$AGENTIFY/skills/agentify/scripts/mine_git.py" \
  --repo "$REPO" --no-gh > "$OUT/git.json"
```

`--no-gh` is not optional here. It is what `SKILL.md` phase 2 passes on every default run, and `gh pr list` is the only network-capable path in the whole toolchain — omitting it makes step 2's "no network" assertion untestable, because the harness would be the thing making the call.

A fresh clone has no transcripts on your machine, so `mine_transcripts.py` should report `history_bucket: "none"`, a populated `warnings` array, and **exit 0**. A non-zero exit there is a bug.

### 1a. Run the selftests first — they are cheaper than a bad regression run

Before any fixture, confirm the toolchain itself is green. Every script and every shared lib
carries its own checks; a red one explains a wrong count faster than reading a plan does.

```bash
cd "$AGENTIFY/skills/agentify/scripts"
for s in discover mine_transcripts mine_git verify_artifacts; do
  python3 "$s.py" --selftest > /dev/null || echo "RED: $s.py"
done
for m in scrub textnorm emit; do
  python3 "lib/$m.py" > /dev/null || echo "RED: lib/$m.py"
done
```

Silence means green. Each script's `--selftest` prints a JSON pass/fail report and exits 1 if any
check fails; the libs print `N passed, M failed`. **Do not record the pass counts anywhere** — they
move every time a check is added, and every document that has pinned them has been stale within the
week. The exit code is the contract, not the number.

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
- **Repo untouched.** `git -C "$REPO" status --porcelain` is empty after the analyzers run. They are read-only.

### 3. Run the skill to the plan gate, and stop

Open Claude Code in the clone and invoke agentify. Answer the consent prompt, reply `defaults` at the interview, and **stop at phase 6**: read the plan, then decline approval. Nothing should be written outside `docs/agentic-setup/plan.md`, and no branch should be created.

```bash
git -C "$REPO" status --porcelain     # expect only docs/agentic-setup/plan.md
git -C "$REPO" branch --list 'agentic-setup/*'   # expect no output
```

A build that starts without approval is the most serious failure this harness can catch. It invalidates the run: fix it before looking at anything else.

### 4. Check the plan against the floor and the catalogue walk

Two checks, and neither is a count comparison.

**4a. The floor held.** Read the plan's summary section and its catalogue walk:

```bash
sed -n '1,60p' "$REPO/docs/agentic-setup/plan.md"
```

Every artifact named in that repo's **Floor** column is present, under the catalogue's own name — `pr-reviewer` is never renamed to signal a nuance, and a skill + subagent pair counts as present only when both halves are. A floor item that is missing is a failure unless the walk row for it gives an outcome from the fixed vocabulary; "it would restate `CLAUDE.md`", "a vendored guide exists", "installed at user scope" and "the procedure is documented" are none of them outcomes. **The walk has one row per catalogue row on every fixture**, including fixture 1 — a short walk is the failure mode the walk was added to catch.

**4b. Nothing was fabricated, and nothing was pre-cut.** Record what was built against what the floor asked for, plus the two failure directions:

| Repo | Skills | Subagents | Rules | Hooks | Floor met? | Walk rows = catalogue rows? | Notes |
|---|---|---|---|---|---|---|---|
| fresh | | | | | | | |
| chalk | | | | | | | |
| commerce | | | | | | | |
| flask | | | | | | | |
| cal.com | | | | | | | |
| last30days-skill | | | | | | | |
| vercel-plugin | | | | | | | |

The counts are recorded so the ranges can eventually be *described*; they are not an acceptance criterion and no run fails for being above one. Then read the plan, because only reading catches either real failure. **Fabrication:** spot-check three artifacts per repo by tracing each one's cited evidence back to the analyzer JSON it came from — an artifact citing a count that does not appear in `discovery.json`, `transcripts.json` or `git.json` is invented, and that is a release blocker. **Pre-cutting:** grep the plan for *cap*, *limit* and *quota*, which must not appear at all, and read the walk's outcomes for a sentence arguing that this repo needs less than the catalogue. The first failure makes the product untrustworthy; the second makes it useless. Both are found by reading.

### 5. Clean up

```bash
rm -rf /tmp/agentify-regression
```

## Recording results

Update the **Floor** column in [The set](#the-set) with what a real run actually produced, note the date and the agentify version you measured with, and remove the derived-not-measured paragraph once every row has a run behind it. Correct a floor when a licence turns out not to fire on that repo — with the field and the value that says why, so the next contributor can tell a corrected floor from a lowered one. Never turn an observed count back into a maximum: an over-floor run is evidence about the repo, and the only thing that fails it is an artifact whose evidence does not hold up.
