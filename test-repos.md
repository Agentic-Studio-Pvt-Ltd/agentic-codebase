# Regression repos

The fixture set agentify is checked against before a release or a merged PR. Repos are **referenced by URL, never vendored** — clone them into a scratch directory, run against the clone, throw the clone away.

The set exists to cover the cases that break things, not to be comprehensive: no history, one language, a real app, a non-JS stack, a workspace monorepo, an existing index doc, and a setup that is already good enough to leave alone.

> **All expected artifact counts below are PROVISIONAL.** They are derived from the sizing caps (PRD §9) and from what the evidence in each repo plausibly supports, not from a measured run. The first contributor to run the full harness should replace each range with what was actually observed and delete this banner. Until then, treat a count outside the range as a prompt to investigate, not as a failure.

## The set

| # | Repo | Why it is in the list | Expected size bucket | Expected counts (skills / subagents / rules / hooks) |
|---|---|---|---|---|
| 1 | *(synthesized locally — see [fixture 1](#fixture-1-fresh-repo) below)* | Fresh repo, no history, no transcripts. The degenerate case: the run must still reach a plan, and the plan must be nearly empty rather than invented. | small | 0–1 / 0 / 1–2 / 0–1 |
| 2 | https://github.com/chalk/chalk | Small single-language JS library. Tiny surface, clear scripts, real conventions. Proves the small-bucket caps bind and that a thin repo does not get a fat setup. | small | 1–3 / 0–1 / 2–4 / 1–2 |
| 3 | https://github.com/vercel/commerce | Medium JS/TS application (Next.js). Framework detection, external services from deps and env var names, folder zones (`components`, `lib`, `app`). The mainstream case. | medium | 2–5 / 1–3 / 3–7 / 1–4 |
| 4 | https://github.com/pallets/flask | Python repo. Checks that discovery reads `pyproject.toml`, tox/pytest config, and a Makefile rather than assuming `package.json` exists. | medium | 2–5 / 1–3 / 3–8 / 1–4 |
| 5 | https://github.com/calcom/cal.com | Large monorepo with workspaces (Turborepo, `apps/` + `packages/`). Checks the <10s discovery budget, large-bucket caps, and the monorepo prompt (root by default, offer per-package). | large | 4–8 / 2–5 / 6–12 / 2–6 |
| 6 | https://github.com/mvanhorn/last30days-skill | Already ships a `CLAUDE.md` **and** an `AGENTS.md`, with no `.claude/` config. Checks the merge path: append a delimited section, never overwrite, and ask which target when both index docs exist. | small–medium (measure) | 1–4 / 0–2 / 2–6 / 1–3 |
| 7 | https://github.com/vercel/vercel-plugin | Mature setup: `.claude/settings.json` plus 7 skills in `.claude/skills/`, over the 5-artifact maturity threshold. Must switch to **audit-only** mode and propose additions and fixes only. | small (audit-only) | 0–2 new / 0–1 / 0–3 / 0–1 |

Counts for row 7 are *additions*. Audit-only mode restructuring or rewriting an existing skill is a hard failure regardless of count.

### Fixture 1: fresh repo

No public repo can be a true fresh-repo fixture — every clone arrives with history, and none of them has transcripts on your machine. Synthesize it:

```bash
mkdir -p /tmp/agentify-regression/repos/fresh && cd /tmp/agentify-regression/repos/fresh
git init -q
printf 'console.log("hello");\n' > index.js
printf '{\n  "name": "fresh",\n  "version": "0.0.0",\n  "scripts": { "test": "node --test" }\n}\n' > package.json
git add -A && git commit -qm "init"
```

What matters here is what the plan does *not* contain. With one commit and zero sessions there is almost no evidence, so the plan should be close to empty and should say why. A plan that proposes six skills for this repo means the evidence requirement is not being enforced.

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
assert size <= 12288, "miner output over the ~3k-token cap: %d bytes" % size
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

### 4. Diff the plan against the expected counts

The plan's summary section carries the count by artifact type. Compare it with the row for that repo:

```bash
sed -n '1,60p' "$REPO/docs/agentic-setup/plan.md"
```

Record actual against expected:

| Repo | Skills | Subagents | Rules | Hooks | Within range? | Notes |
|---|---|---|---|---|---|---|
| fresh | | | | | | |
| chalk | | | | | | |
| commerce | | | | | | |
| flask | | | | | | |
| cal.com | | | | | | |
| last30days-skill | | | | | | |
| vercel-plugin | | | | | | |

Then read the plan, not just the numbers. The counts catch overgeneration; only reading catches the failure that matters more — an artifact whose stated evidence does not actually support it. Spot-check three artifacts per repo by tracing each one's cited evidence back to the analyzer JSON it came from. An artifact citing an evidence count that does not appear in `discovery.json`, `transcripts.json`, or `git.json` is a fabrication, and fabrication is a bug of a different class than a bad range.

### 5. Clean up

```bash
rm -rf /tmp/agentify-regression
```

## Recording results

Update the counts table in [The set](#the-set) with measured ranges, note the date and the agentify version you measured with, and remove the provisional banner once every row has a real number behind it. Widen a range when a legitimate run falls outside it; tighten the mapping rules when an illegitimate one does.
