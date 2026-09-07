# verification.md — phase 8 smoke tests

Read this file in **phase 8 (Verify and hand off)**, immediately after the build finishes and
before you write `report.md`. Verification is what separates a generated setup from a plausible
one. An artifact that has not been exercised has not been built.

Run the static pass (§2) first, then the per-type live tests (§4–§8), then write the results
table into the report using `report-template.md`.

---

## 1. Safety rules for this phase

These bind every command in this file. Verification is the phase most likely to damage the
user's repo, because it is the one that executes things.

1. **Never modify a user file outside the build branch.** Every write during verification goes
   to the branch created in phase 7, or to a scratch directory outside the repo. If the run is
   in stage-only mode, verification writes **nothing** to the working tree — use scratch
   fixtures only.
2. **Fixtures live outside the repo.** Create them under a temp directory (e.g.
   `$(mktemp -d)/agentify-verify`). Never create a fixture file inside `src/`, `tests/`, or any
   tracked directory. Delete the temp directory when the phase ends, pass or fail.
3. **Never commit, stash, reset, clean, rebase, amend, or push during verification.** If a test
   would need a commit to be meaningful, simulate it (§5) instead.
4. **Never leave staged state behind.** If a test stages a fixture, unstage it in the same step,
   before the next test. Record the pre-test `git status --porcelain` and confirm it matches
   afterwards.
5. **Never run a generated artifact against production-shaped inputs.** No test touches a real
   database, a real API, or anything requiring a credential. An MCP draft is verified as *config*,
   never by connecting.
6. **Time-box every live test to about 60 seconds.** A hang is a `warn`, not a reason to wait.
7. **A failing test never silently disappears.** Every fail ends in exactly one of two outcomes:
   the artifact is fixed and re-tested, or the artifact is removed and moved to the report's
   Skipped table with the reason `failed verification and was removed`.
8. **Never execute a hook without asking first, and never execute one agentify did not write.**
   Hook execution is opt-in for the user and off by default — §5.1 is binding, not advisory.

---

## 2. Static pass — `verify_artifacts.py`

### 2.0 Before you run it: agentify's own output belongs in the manifest

`plan.md`, `build-manifest.json` and `report.md` are generated files exactly like the rules and
skills around them, and until they are named in the manifest **nothing checks them** — the
verifier only ever reads what the manifest lists. The 2026-09-04 dogfood run shipped a manifest
that carried no `agentify-id` anywhere in it and no check noticed, because the file describing
every artifact was not itself an artifact.

So, before the first static pass, make the manifest describe all of the run's output:

1. **The manifest carries its own identity.** Add one inert top-level key, the same shape
   `mcp.json.tmpl` and `plugin.json.tmpl` already emit. Nothing reads it at runtime; it is what
   lets a rerun recognise its own manifest.

   ```json
   "_agentify": {
     "agentify-id": "build-manifest",
     "agentify-version": 1,
     "agentify-generated": "2026-09-04",
     "agentify-evidence": "index of the 12 artifacts this run built",
     "note": "Inert metadata. Nothing reads this key. Safe to delete or edit."
   }
   ```

2. **Add two entries now**, using the types `plan` and `manifest`:

   ```json
   {"id": "agentic-setup-plan", "type": "plan",
    "path": "docs/agentic-setup/plan.md", "action": "created",
    "evidence": "approved plan of record: 12 artifacts, 4 skipped"},
   {"id": "build-manifest", "type": "manifest",
    "path": "docs/agentic-setup/build-manifest.json", "action": "created",
    "evidence": "index of the 12 artifacts this run built"}
   ```

   Keep `action: created` for all three, **including on a rerun**. agentify owns these three files
   end to end and rewrites them whole; there is no pre-existing user content in them to delimit, so
   there are no begin/end markers to find. `modified` is for files the user owns, and using it here
   would fail `markers` on a file that is correct.

   `plan` and `report` are markdown types and are checked as markdown; `manifest` is a JSON type,
   so it is exempt from the markdown-only checks (`frontmatter`, `markers`) exactly as `settings`,
   `mcp` and `plugin` are, and its `metadata` check reads the `_agentify` object above. The ids
   are the ones `plan-template.md` and `report-template.md` already put in their frontmatter —
   `agentic-setup-plan` and `agentic-setup-report` — so `metadata` matches without any new writing.

3. **Do not add the `report` entry yet.** `report.md` does not exist during the first static pass;
   it is written *from* that pass's results. Listing it now is a guaranteed `file_exists` FAIL.
   §9 says exactly when it goes in.

4. **Check the undo record is there before you run the pass, because the pass now reads it.**
   Phase 7 step 6 wrote `mode`, `base_branch`, `base_commit`, `created_dirs`, `committed_paths`
   and `uncommitted_paths`, plus `ignored` (and `ignored_by`) per artifact and `restore` on every
   `modified` one. `undo_partition` and `undo_created_dirs` check them, which is the mechanical
   half of §10.2 and §10.3 — every artifact covered by exactly one removal mechanism — and
   `uninstall` then reads the same fields to ask whether the mechanism each artifact is covered by
   can actually act on that file, which is the half no list can answer. A manifest with neither
   path list does not fail; it produces **one warn** from each of `undo_partition` and `uninstall`,
   saying phase 8 cannot generate the removal section from it, which is the same thing said earlier
   and more cheaply. If you see those warns, go back to phase 7 step 4 and record what the commit
   actually holds — do not write a removal section from memory.

**The manifest listing itself is not a chicken-and-egg problem, and it is not skipped.** Its four
checks — `path_containment`, `file_exists`, `markers` (exempt, JSON), `metadata` — depend on the
file existing, being non-empty, parsing as JSON, and carrying `_agentify`. None of them depends on
the manifest's *contents*, and nothing hashes it. So appending the `report` entry after the
manifest has been verified does not invalidate the earlier result; it only means the last static
pass covers one more file. If you ever add a check that does depend on manifest contents, that
reasoning stops holding — say so rather than leaving the self-entry in place.

### 2.1 Running it

Run once, after the last artifact is written.

```bash
python3 "$SKILL_DIR/scripts/verify_artifacts.py" \
  --repo "$REPO_ROOT" \
  --manifest "$REPO_ROOT/$PLAN_DIR/build-manifest.json" \
  --discovery "$WORK/discovery.json"
```

`$SKILL_DIR` is the directory containing `SKILL.md`. `$PLAN_DIR` is the interview's `plan_dir`
answer (default `docs/agentic-setup`), which is where phase 7 wrote `build-manifest.json`.
`$WORK` is the scratch directory holding phase 1's `discovery.json`.

**`--manifest` resolves against your cwd, not against `--repo` — pass the absolute path.**
`"$REPO_ROOT/$PLAN_DIR/..."`, never the bare `"$PLAN_DIR/..."`. The relative form works only when
you happen to be standing in the repo root, and agentify is often invoked from somewhere else;
run it from anywhere else and it exits **1** with `manifest not found: <cwd>/<value>`, which
SKILL.md phase 8 reads as "the manifest is missing" — a build that verified fine looks broken.
Measured both ways. `--repo` and `--discovery` have no such trap: `--repo` is the anchor every
artifact path is resolved under, and `$WORK` is already absolute.

**Always pass `--discovery`.** It is optional to the script and mandatory to this phase: without
it, `rule_contradiction` compares rules only with each other, and PRD §7.9's other half — "check
for contradictions … with discovered conventions" — silently does not run. The check's PASS row
says which of the two happened, in as many words, so a report that claims full coverage after a
run without `--discovery` is a report that is wrong. A missing or unreadable `discovery.json` is
degraded, not fatal: the script warns and continues rule-against-rule.

What you lose by omitting it is not a nicety. `contradicts-convention` is the only kind of
`rule_contradiction` that **fails** — §6's own Fail example, a rule saying "use npm" in a repo
with `bun.lock` and `bun install` in CI, is caught by nothing else. Without `--discovery` that
rule is built, shipped, and reported as verified.

**This command does not execute anything.** Hook execution is opt-in — see §5.1 before you
consider adding `--exec-hooks`.

### What it checks

These are the literal `checks[].name` values the script emits — nothing else appears. Use this
table to read a row; the name goes into the report's Check column unchanged.

| `name` | Meaning | Worst severity |
|---|---|---|
| `manifest_loaded` | the manifest was read; `target` names it and `detail` gives the artifact count | warn |
| `manifest_entry` | the entry has `id`, `type`, `path`, `action` and a non-empty `evidence`. A missing `id` / `path` / `action`, **and an empty `evidence`**, are each a fail; only the softer problems (an unrecognised `type`) are a warn | fail |
| `path_containment` | the path resolves inside the repo root, with no `..` or symlink escape | fail |
| `file_exists` | the file is on disk and non-empty | fail |
| `id_unique` | no two manifest entries share an `agentify-id` | fail |
| `markers` | a `modified` file carries exactly one begin/end pair for its id (**JSON** files are exempt — they cannot hold comments; the exemption is keyed on the file really being `.json`, not on its manifest `type`, because a Codex `mcp` artifact is TOML and TOML *does* take `#` comments) | fail |
| `frontmatter` | the hand-rolled frontmatter reader can read the file | fail |
| `metadata` | `agentify-id` / `-version` / `-generated` / `-evidence` present, the id matches the manifest, and the file says `Safe to delete or edit.` | fail (warn for JSON and for `modified` files) |
| `evidence_match` | the file's `agentify-evidence` line is the **same string** as its manifest entry's `evidence`. Quoting, spacing, smart punctuation and case do not count as a difference; a truncation (one side a prefix of the other, both ≥ 20 chars) is a warn; anything else is drift and a fail. Not reported when either side is absent — `manifest_entry` and `metadata` already own those | fail |
| `name_unique` | no two skills, and no two subagents, share a frontmatter `name` | fail |
| `skill_frontmatter` | `name` matches the skill directory; `description` is non-empty and under 1024 chars | fail |
| `subagent_frontmatter` | the subagent's identity, read **in its own format**. Claude Code (`.claude/agents/<name>.md`): `name` and `description` in YAML frontmatter. Codex (`.codex/agents/<name>.toml`): `name`, `description` and `developer_instructions` as TOML keys, and the filename stem must equal `name` — the static contract `codex-agent.toml.tmpl` §10 states. Until 2026-09-05 this asked a TOML file for YAML frontmatter and failed every correct Codex subagent | fail |
| `subagent_tools` | Claude Code: the declared tools look like real tool names (warn). Codex: there is **no per-agent tool allowlist**, so the check is that none was invented (warn if a `tools` key appears, because the restriction is silently lost) and that `sandbox_mode` is not `danger-full-access` (**fail** — a generated agent is never granted it). A pinned `model` is a warn: it goes stale and silently changes the user's session | fail |
| `rule_scope` | **prose rules only** — `scope` is present and its globs parse | fail |
| `rule_body` | **prose rules only** — the rule body is not empty | fail |
| `rule_wired` | **prose rules only** — the rule is referenced from an index doc, so something actually loads it. A **prose** rules directory is a repo convention, not a load path on either target — Claude Code reads `CLAUDE.md`, Codex reads `AGENTS.md`, and neither walks one — so an unreferenced rule is a dead file (`adapters/claude-code.md` §4.2, `adapters/codex.md` §4.2). The search is the adapters' own `grep -F "<name>.md"` over the whole index doc, so a rule the user wired by hand in their own prose counts. Falls back to `CLAUDE.md` / `AGENTS.md` on disk when the manifest names no index doc (the rerun case); an index doc that exists but cannot be read is a warn, never a fail. **A Codex command policy is exempt and passes with a note:** `.codex/rules/*.rules` *is* a native load path — Codex reads the directory itself, gated only on the project being trusted — so nothing needs to point at it | fail |
| `rule_contradiction` | three kinds. `opposing-polarity` (one rule asserts what another forbids) and `exclusive-choice` (two rules pick different members of one exclusive category — bun/npm, jest/vitest, tabs/spaces) are **warn**: they read one piece of generated prose against another. `contradicts-convention` (a rule asserts something `discovery.json` says the repo does not do — **only with `--discovery`**) is a **fail** when the convention is a hard fact, from `discovery.package_managers` or a `discovery.commands.*` line, and a warn when it is soft, from the `frameworks` / `languages` name scans. A rule worded as intent (`we are moving to X`) is exempt entirely. Rules are read clause by clause, so "Always use bun, never npm" counts as two directives; scopes must overlap, and a narrower rule that calls itself the exception is exempt | fail |
| `rule_policy_syntax` | **command policies only** — `.codex/rules/*.rules` parses as Starlark and declares at least one policy rule. Starlark is a Python dialect and a rules file is top-level keyword-only calls, so `ast` reaches the same verdict Codex's loader does on the thing that matters. An unrecognised policy function is a **warn**, never a fail: the language is documented as experimental and subject to change | fail |
| `rule_policy_decision` | every block's `decision` is exactly one of `allow` / `prompt` / `forbidden`. Anything else is a **fail**, and it is the most consequential row in the table: measured, `decision = "ask"` produces `Error loading rules: … invalid decision: ask` and `codex exec` then **refuses to start in that repo at all**. A malformed `.rules` file is a fatal startup error, not a skipped file | fail |
| `rule_policy_pattern` | every block's command prefix (`pattern`, or `prefix` / `program`) is present and non-empty — a rule with no prefix matches nothing, or everything | fail |
| `rule_policy_examples` | `match` is declared for every rule and every declared example behaves as written: each `match` is caught by some rule in the file, no `not_match` is caught by its own rule. Codex enforces the first at load time (`expected every example to match at least one rule`), so this finds the fatal error before the user's next session does. A `not_match` violation is a **warn**, and so is a `match` miss when any pattern in the file uses a construct this checker cannot fully read — a matcher stricter than Codex's would fail a correct file, which is the defect this whole path exists to remove. A rule with no `not_match` is a warn: prefix matching has no semantics, and `npm` does not catch `npx`, `pnpm`, or npm inside `bash -c` | fail |
| `rule_policy_execpolicy` | Codex's own loader asked for a second opinion — `codex execpolicy check --rules <file> -- <a match example>`. Runs only when a `codex` binary resolves **and** `--exec-hooks` was passed, because this script's default posture is to execute nothing; otherwise it passes with a row that says plainly it was not consulted and prints the command to run by hand | fail |
| `hook_script` | the hook command resolves, is executable, and starts with a shebang | fail |
| `hook_static_scan` | no network call in the hook script or its command line — `curl`, `wget`, `nc`, `ssh`, `/dev/tcp`, a python/node http client, a package install, a remote `git` or `gh` call. A hit names the offending line, and that hook is never executed. Text a hook **prints** is not a call a hook **makes**: a match inside a quoted-delimiter heredoc (`<<'EOF'` — how both hook templates carry their block message) or inside a single-quoted `printf`/`echo` argument is downgraded to a warn, because the message a package-manager hook exists to print is, of course, *"Fix: run `bun install`"*. A body piped into a shell (`cat <<'EOF' \| sh`) is still live, and still a fail | fail |
| `hook_smoke` | the hook was executed and exited 0 inside the timeout. Only runs with `--exec-hooks`, and only for a hook this run generated inside the repo. A hang is a fail; a non-zero exit is a warn (see §5.1); not being executed is a warn | fail |
| `hook_wired` | something actually registers the hook — the reverse of `settings_hook_command`, and the reason both exist. **Two** registrations exist, and the target profile in `verify_artifacts.py` says which files count on this build. A **config-registered** hook must be named by a hook command in the target's own registry: `.claude/settings.json`, `.claude/settings.local.json` or a plugin manifest on Claude Code; `.codex/hooks.json` on Codex; plus either target's user-scoped file (`${CLAUDE_CONFIG_DIR:-~/.claude}/settings.json`, `${CODEX_HOME:-~/.codex}/hooks.json`), resolved through the environment variable and never a hardcoded home. Every one of those files carries the same three-level `hooks` shape — event → matcher group → the group's own `hooks` array — so one reader covers all of them. Matching is as permissive as `rule_wired`'s, so a hook the user wired by hand counts; the one narrowing is a **user-scoped** registry, which is shared by every repo on the machine, so there a bare file name proves nothing and a path must match. A **native git hook** is registered by its name and its location instead: it must sit in the directory git actually runs hooks from (`core.hooksPath` when set, else `.git/hooks/`) under a real git hook name, so a hook written to `.git/hooks/` while `core.hooksPath` points elsewhere is a fail. It is a secondary, opt-in artifact on **either** target (`adapters/codex.md` §4.3), never a substitute for a hook. **There is no target on which a hook artifact fails by construction** — both targets have a full native hook system, Codex's with 12 events, regex matchers over tool names and a JSON `permissionDecision` protocol. Until 2026-09-05 this check hard-failed every hook whenever the manifest said `target: codex`, which told the model to remove a hook that was correctly written *and* correctly registered. A `.agentify` side-file written beside a hook that already existed is a warn — it is inert on purpose until the user merges it (`adapters/codex.md` §4.3 rule 2) | fail |
| `settings_json` | the target's hook registry parses — `.claude/settings.json` on Claude Code, `.codex/hooks.json` on Codex — and, on a target whose registry rejects unknown top-level keys, carries none. Codex's accepts exactly `description` and `hooks`: one unknown key (an `_agentify` block, say) makes it reject the **whole file** and load **zero hooks**, surfaced only as a `hooks/list` warning nobody sees, so that is a fail here rather than a silent nothing later | fail |
| `settings_hook_command` | every hook command in it resolves to an existing executable file, or a binary on `PATH` | fail |
| `mcp_json` | the MCP config is valid **in its own format**. Claude Code: `.mcp.json`, valid JSON, `mcpServers`. Codex: `[mcp_servers.<name>]` TOML tables — at least one complete table, and no bare key/value pair above the first `[table]` header (measured: such a pair binds to whatever table precedes it once pasted into `config.toml`, the file loads without complaint, and the setting has no effect). The two are not interchangeable and writing `.mcp.json` for a Codex target configures nothing; until 2026-09-05 this ran `json.loads` on the TOML draft and failed a correct artifact with `invalid JSON: Expecting value: line 1 column 1` | fail |
| `mcp_secrets` | no literal-looking secret in it — `${VAR}` and placeholders are fine. Format-independent: it scans raw text as well as parsed structure, so it covers both shapes | fail |
| `plugin_paths` | every path-valued key in a plugin manifest (Codex `skills`/`apps`, the Claude manifest's component directories) resolves on disk. Paths resolve against the **plugin root** — the manifest's grandparent when it sits in a `.*-plugin/` directory — not against the manifest's own directory and not against the repo root. The manifest is written *after* the copy step that populates those directories, so a skipped copy leaves a manifest that parses cleanly and points at nothing. Keys starting with `_` and non-relative values are ignored | fail |
| `undo_committed_clean` | every path in `committed_paths` matches what the branch holds. `undo_partition` proves an artifact is in one of the two lists; this proves the CONTENT of a committed one, because the branch delete restores the committed bytes and silently discards an edit made after the commit — and the tree diff taken afterwards comes back empty, since the file is back to a version that once existed. agentify's own `report`/`manifest` are exempt at WARN: §9 writes them after this check runs | fail |
| `undo_partition` | the manifest's `committed_paths` and `uncommitted_paths` cover every artifact **exactly once**. A path in neither is a file no undo removes (§10.2); a path in both means `ignored` and the commit disagree. An artifact with `ignored: true` may only be in `uncommitted_paths` — `git add` refuses it, so the branch never held it — and so may an `action: modified` artifact with `restore: span`, because committing one of those makes `git checkout <base_branch>` **delete** the user's own file instead of restoring it. A manifest carrying neither list is one warn, saying phase 8 cannot generate the removal section from it | fail |
| `undo_created_dirs` | `created_dirs` is repo-relative, inside the repo, and deepest-first — a parent listed before a directory it contains is a fail, because the undo's `rmdir` would hit a non-empty directory. An entry that is not on disk is a warn. No row at all when the manifest has no `created_dirs` | fail |
| `uninstall` | the undo this run is about to publish, proved rather than described — the three questions `undo_partition` cannot ask, because coverage is necessary and not sufficient. **Format:** every artifact must be reachable by a mechanism its file's format allows — a marked text file by the marker script, a `settings` / `mcp` **JSON** config by the JSON un-merge script, a created file by `rm`, a created directory by `rmdir`. **The routing keys on the file's real format, never on its manifest `type`:** a Codex `mcp` artifact is TOML — `<plan-dir>/codex-mcp.toml` is a draft agentify created whole, so `rm` removes it exactly, and an opt-in append into `<repo>/.codex/config.toml` is a marked block the marker script can take back out. The JSON un-merge script can do neither, and there is no TOML writer in the standard library at any version. Routing the draft to it made a correct removal block fail with *the removal block `rm`s this JSON config*. A JSON config routed to the marker script is a fail (it finds nothing, exits 0 and removes nothing — measured), and a file that existed before the run routed to `rm` is a fail (it deletes the user's file). **Branch:** in `branch` mode every `committed_paths` entry must be in `git diff --name-only <base_commit>..<branch>`, which spans **all** the branch's commits — `report.md` and the manifest are exempt, phase 8 step 5 commits them after this runs — and no `uncommitted_paths` entry may be on it; every `restore: head` entry is checked against `git show <base_commit>:<path>`. **Order:** once `report.md` exists, the rendered removal block is parsed into an ordered list of steps, each recorded by what it *does* — what it reads, writes, deletes, hashes, and whether it copies the instructions out of the repo — never by how it is worded, so a reworded block is read correctly and a reordered one still fails. No template placeholder may survive, and six things must hold. **(a)** The step that copies the instructions out of the repo is step 1 — recognised by its destination resolving to no repo-relative path, whatever it is called. **(b)** No step deletes what a later step reads; `report.md` counts as an input to *every* step until step (a) has run, because that is the file each one is read out of. **(c)** The `rm` that deletes `report.md` is the last step that deletes a file — `rmdir` and the digests may follow it. **(d)** Both scripts are printed above that `rm`: they are printed *inside* the file it deletes. **(e)** An `rmdir` is below every step that takes something out of that directory, the JSON un-merge script's deletion of a config it created included — otherwise it prints `Directory not empty` and leaves the directory behind while exiting 0. **(f)** A `shasum` / `sha256sum` confirmation is below the step that restores the file it hashes, or it confirms the bytes the run left and matches the `expected:` line by accident. A step whose own comment says when to run it is exempt from all six and counted as `deferred` in the summary row instead. Each defect is its own row, up to four, then a count; the summary row says `N ordering defect(s)` rather than `order consistent`. **(b) alone is what the check used to be, and (a) and (c)–(f) are what it missed**: a closing block printed ahead of the two scripts leaves every artifact reachable by exactly one mechanism, so every coverage assertion above passes on a sequence that destroys itself (measured — the A,D,C reordering). The passing row is the one §10.5 publishes verbatim. The only warns are inputs that could not be *read* — a manifest with no undo record (one warn, exactly as `undo_partition`), or git unusable — and each names which half went unchecked | fail |

### How to read the output

It prints one JSON object to stdout. Diagnostics go to stderr — read them only when the JSON is
missing or unparseable.

```json
{"schema_version":1,"tool":"verify_artifacts.py",
 "checks":[{"name":"","target":"","status":"pass|fail|warn","detail":""}],
 "summary":{"pass":0,"fail":0,"warn":0},"warnings":[],"timing_ms":0}
```

Those seven keys are the whole object — there are no others. The manifest that was read and the
number of artifacts in it come back as the `manifest_loaded` row in `checks[]`, not as top-level
keys.

- **Judge by `summary.fail`, not by the exit code.** The script exits non-zero only on an
  unrecoverable error; a run with failing checks still exits 0 with a populated JSON. A non-zero
  exit means the script itself broke — treat it as "static pass unavailable", note it in the
  report, and continue with the live tests.
- `status: "fail"` → the artifact named in `target` is broken. Fix or remove it (§9).
- `status: "warn"` → record it in the report's Detail column and move on. Warnings do not block
  the handoff.
- **Read the `rule_contradiction` PASS row, do not skim it.** Its detail says whether conventions
  were compared at all: `…and none conflicts with the N discovered convention(s) in <path>` means
  both halves ran; `…conventions NOT checked` means `--discovery` was missing and half of PRD §7.9
  did not happen. Never copy the first into the report after a run that produced the second.
- **`rule_contradiction` is now mixed severity, so read the status per row, not per name.** A
  `contradicts-convention` row against a hard fact is a `fail` and goes through §9's fix-or-remove
  loop; the two rule-against-rule kinds are `warn` and are recorded, not acted on.
- A populated top-level `warnings` array means the script degraded (for example, it could not
  read the manifest). Say so in the report rather than implying full coverage.
- Copy `checks[]` rows straight into the report's verification table — `target` becomes the
  Artifact column, `name` becomes Check, `status` becomes Result, `detail` becomes Detail.
- **The `uninstall` row is one of those rows, and it is never written by hand.** §10.5 publishes it
  verbatim; a hand-authored one is the product's core safety claim resting on the model's summary of
  its own work. Its detail is a generated tally that adds up to every artifact in the manifest.
- **`uninstall` is not complete until the pass that runs after `report.md` exists.** The half of it
  that reads the rendered removal block has nothing to read on the first pass and says so in the
  detail (`report.md: not written yet, ...`); §9 step 6's re-run is the one that sees the block.

Re-run the static pass after any fix, so the reported numbers describe the final state.

---

## 3. Live tests — general shape

For each artifact type below: run the test, classify pass / warn / fail, and record one row.
Test artifacts in build order (index doc, rules, hooks, skills, subagents, MCP drafts, plugin
manifest) so a broken dependency surfaces before the thing that depends on it.

---

## 4. Skills

**Test.** Invoke each generated skill on one small, real task derived from this repo. Derive the
task from the same evidence that justified the skill: if the skill exists because of cluster
"add endpoint for <resource>" (9 prompts), invoke it on a real resource name from
`discovery.folders` or a file hotspot. Do not invent a fictional domain, and do not use a task so
large that the test becomes the work.

Prefer a read-only or scratch-output form of the task: ask the skill to produce its plan and its
first file into the scratch fixture directory rather than into `src/`. If the skill cannot be
exercised without writing into the repo, run it on the build branch and revert the working tree
to the branch's committed state afterwards.

**Pass.** The skill loads; its instructions are followed; it produces a plausible, repo-shaped
result — correct paths, the repo's real commands, the repo's real conventions — with no errors
and no missing reference file.

**Fail.** Any of: the skill file does not load (frontmatter or name problem); it references a
file, script, or command that does not exist in this repo; it produces output for a different
stack (npm in a bun repo, jest in a vitest repo); it contradicts a generated rule; it tries to
run a destructive command; it produces nothing.

**Warn.** It loads and runs but the output is thin, or it needs one clarifying question that the
skill should have answered from the repo.

**Remediation.**
- Wrong command or wrong path → fix the skill file from `discovery.commands` / `discovery.folders`
  and re-test once.
- Missing reference file → create it if it was in the plan; otherwise remove the reference.
- Contradicts a rule → the rule wins. Amend the skill.
- Still failing after one fix, or fails for a reason you cannot fix from evidence → **remove the
  skill directory**, and list it in the report's Skipped table as
  `failed verification and was removed`. Do not ship a skill you could not run.

---

## 5. Hooks

**Both targets have a full, native hook system.** Codex's is a near-superset of Claude Code's: 12
events, regex matchers over tool names, a JSON stdin/stdout contract and a repo-scoped, committable
`.codex/hooks.json` whose shape is the same three levels as `settings.json` (`adapters/codex.md`
§4.3, verified against `codex-cli 0.152.1`). Nothing about a hook is substituted on Codex. Any
statement anywhere that Codex has no hooks — and any check, plan sentence or report line built on
one — is stale and wrong; a native git hook is a **secondary, opt-in** artifact on either target,
not a stand-in.

What *is* different is the protocol, and §5.2 turns on it: Claude Code blocks with **exit 2** and
stderr; Codex **always exits 0** and blocks by printing `hookSpecificOutput.permissionDecision`.
Judge a hook against its own target's contract, never the other's.

**Before any of this, read the `hook_wired` row.** It is to a hook what `rule_wired` is to a rule:
the answer to "does this file do anything at all". A hook script nothing registers is not a weak
hook, it is an inert one — the harness runs the hooks it is *told about* in the target's registry
(`.claude/settings.json` / `settings.local.json` / a plugin manifest, or `.codex/hooks.json`), never
a script it happens to find in a hooks directory, and a native git hook runs only from the directory
git actually reads (`core.hooksPath` when set, else `.git/hooks/`) under a name git knows. A fail
there is settled before you spend a minute on behaviour: register it, or delete it.

### 5.1 Executing a hook needs the user's word first

Hooks are the only generated artifact that is a *program*. Running one is the single place in the
whole tool where code agentify wrote gets executed on the user's machine, and therefore the only
remaining route to the network in a tool that promises "local only, no network calls" (PRD §13).
So it is opt-in, and the opt-in is the user's, not yours.

**The static pass does not execute hooks.** Run it as written in §2 and it performs static checks
only. To smoke-test hooks you must add `--exec-hooks`, and you may only add it after asking:

> I built N hook script(s). I can smoke-test them by actually running each one with empty input,
> in a throwaway directory outside your repo, with your environment variables stripped and a
> 5-second timeout. Nothing else on your machine is touched. Want me to? (yes / no — no is fine,
> I will report them as statically checked only.)

Rules around that question:

- Ask it in phase 8, in your own turn, and wait for an answer. Never infer consent from the
  phase-0 transcript consent, from `hook_strictness`, or from a general "go ahead".
- A no, a silent skip, or any ambiguity means you do **not** pass `--exec-hooks`. There is no
  retry and no rephrasing to get a better answer.
- Never pass `--exec-hooks` on a rerun without asking again.
- Only ask when the build actually produced hooks. No hooks, no question.

```bash
# only after an explicit yes
python3 "$SKILL_DIR/scripts/verify_artifacts.py" \
  --repo "$REPO_ROOT" \
  --manifest "$REPO_ROOT/$PLAN_DIR/build-manifest.json" \
  --discovery "$WORK/discovery.json" \
  --exec-hooks --hook-timeout-s 5
```

`--no-exec` still works and is now simply the default spelled out loud; if both flags are given,
`--no-exec` wins and the script says so in `warnings`.

**agentify never executes a hook it did not write.** Even with `--exec-hooks`, a hook runs only
when its resolved script path is *both* inside the repo root *and* named in this run's
`build-manifest.json`. A pre-existing hook, a wrapper that lands on `/usr/local/bin/something`,
a script the user wrote by hand — each reports
`hook_smoke: warn — not executed: hook not generated by this run`. That is correct behaviour, not
a gap: auditing someone else's hook is not the same as smoke-testing your own, and you were not
given permission to run theirs. Do not "fix" it by inlining their script into a generated one.

A hook that fails `hook_static_scan` is never executed either, whatever the flags say.

**What the static-only fallback proves**, and it is worth saying plainly in the report:

| Proven without `--exec-hooks` | NOT proven without `--exec-hooks` |
|---|---|
| the file exists and is non-empty | that it runs at all |
| the execute bit is set | that it terminates |
| it starts with a shebang | that it exits 0 on ordinary work |
| the registry points at a path that resolves | that it catches what it was built to catch |
| something registers it, so it is reachable at all | that the event it is registered for is the right one |
| it contains no network call | that its exit codes match `hook_strictness` |
| — | that the harness **loaded** it — and on a first run nothing can prove that (§5.3) |
| — | on Codex, that the user has **trusted** it; on either target, that a session started since (§5.3) |

So a statically-checked-only hook is **`not tested`** in the report, with the reason
`hook execution declined` — never `pass`. Say in the "Three things to try tomorrow" section that
the user can run the hook themselves once against a real change to confirm it behaves.

Two more things the executed smoke test deliberately does *not* prove, because of how it is
sandboxed — the hook runs with `cwd` and `HOME` in an empty scratch directory, and with the
environment cut down to `PATH`, `HOME`, `TMPDIR`, `AGENTIFY_VERIFY` and **the variables its own
target sets**: `CLAUDE_PROJECT_DIR` on Claude Code, `CODEX_HOME` on Codex (pointed at a scratch
directory, never the real one). A Codex hook is never given `CLAUDE_PROJECT_DIR` and a Claude Code
hook is never given `CODEX_HOME` — a hook tested in the other agent's environment is a test of
something the user will never run. Nothing else from the parent environment survives:

- A **non-zero exit** there is a `warn`, not a `fail`. The hook may simply be reacting to the
  missing repo (`no package.json`, `nothing staged`). Settle it with the §5.2 fixture test below
  before you remove anything. On **Codex** read it differently: a correct Codex hook exits 0 on
  *everything*, so a non-zero exit is the hook's own error path and worth reading the stderr for.
- A hook that needs the real repo on disk, a tool from the user's shell profile, or a credential
  will behave differently under the sandbox than in real use. That is the point of the sandbox; the
  §5.2 fixture test is the authority on behaviour.

A **timeout** is still a `fail` with no caveat. A hook that hangs on empty input hangs the user's
session, whatever directory it hangs in.

### 5.2 Behavioural test

**Test.** Three checks per hook, in this order.

1. **Runs at all.** Execute the hook script directly once, with the same environment the harness
   would give it, against a fixture: `bash <hook path>` with the fixture staged or its input
   piped in. It must terminate inside the time box.
2. **Does not block normal work.** Run it against a *clean, conventional* fixture — a small file
   that fully satisfies the repo's conventions. The hook must exit `0`. This is the most
   important hook check: a hook that fires on ordinary work will be deleted by the user within a
   day, and it will take the rest of the setup's credibility with it.
3. **Reacts only to a real violation, in its own target's protocol.** Run it against a fixture that
   deliberately violates the exact thing the hook exists to catch (a hardcoded `sk-` string for a
   secret hook, a file with a type error for a typecheck hook), then judge the reaction against the
   contract of the target the manifest names — never the other one's. The two contracts differ in
   kind, not in detail, and the table below is what "correct" means for each.

Never test a commit hook by making a commit. Stage the fixture, run the hook script directly,
unstage. Never test a hook against the user's actual staged changes.

**The two hook protocols.** Judge every reaction against the row for the manifest's target.

| | **Claude Code** | **Codex** |
|---|---|---|
| Blocks by | **exit 2**, with the reason on **stderr** — that text is what the model acts on | **exit 0** and a JSON object on **stdout**: `{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"…"}}` |
| `hook_strictness: blocking` | non-zero (2) on the violating fixture | exit 0, `permissionDecision` is `"deny"`, and `permissionDecisionReason` reads as an instruction ("This repo uses bun. Re-run as: `bun install`"), not a log line |
| `hook_strictness: warn` | **exit 0**, violation printed to stderr. Non-zero is a fail, not a bonus | **exit 0** with no `deny` — print the note as plain stdout / `additionalContext` |
| A **non-zero exit at all** | 2 blocks; other non-zero codes are a non-blocking error | **a fail.** Only 0 and 2 are specified, agentify's generated Codex scripts exit 0 always and express every decision in JSON (`adapters/codex.md` §4.3) |
| Benign fixture | exit 0, silent | exit 0, **prints nothing** |

The stdin fixtures, fed exactly as each harness feeds them — note that the tool names differ, and a
hook ported across with `"tool_name":"Bash"` will never fire on Codex:

```sh
# Claude Code — benign, then blocking.
echo '{"session_id":"smoke","cwd":"'"$REPO"'","hook_event_name":"PreToolUse",
"tool_name":"Bash","tool_input":{"command":"git status"}}' | .claude/hooks/<name>.sh; echo "exit=$?"
echo '{"session_id":"smoke","cwd":"'"$REPO"'","hook_event_name":"PreToolUse",
"tool_name":"Bash","tool_input":{"command":"npm install left-pad"}}' | .claude/hooks/<name>.sh; echo "exit=$?"

# Codex — benign, then blocking.  Tool names here are `exec` / `exec_command` /
# `shell_command` / `apply_patch`, never `Bash` / `Edit` / `Write`.
echo '{"session_id":"smoke","cwd":"'"$REPO"'","hook_event_name":"PreToolUse",
"tool_name":"exec","tool_input":{"command":"git status"}}' | .codex/hooks/<name>.sh; echo "exit=$?"
echo '{"session_id":"smoke","cwd":"'"$REPO"'","hook_event_name":"PreToolUse",
"tool_name":"exec","tool_input":{"command":"npm install left-pad"}}' | .codex/hooks/<name>.sh; echo "exit=$?"
```

A hook that blocks the **benign** fixture is a build failure on either target, not a warning: it
will block the user's ordinary work in their next session. Remove it, record it, continue.

**Pass.** Exits 0 on the clean fixture, behaves as configured on the violating fixture, finishes
inside the time box, writes nothing outside the fixture directory.

**Fail.** Non-zero on the clean fixture (blocks normal work); no reaction at all to the violating
fixture (does nothing); hangs; writes to or deletes a repo file; references an interpreter or
binary not present (`discovery.commands` and `discovery.package_managers` are the source of truth
for what exists); is not executable; the target's registry points at a path that does not exist; or
nothing registers the script at all — the static pass catches the last three first (`hook_script`,
`settings_hook_command`, `hook_wired`), and the last one makes the rest moot. On Codex, add one
more: **any** non-zero exit, and a blocking reaction that is not the `permissionDecision` JSON.

Run these only if the user agreed to hook execution in §5.1 — they execute the hook just as
`--exec-hooks` does. If the user declined, skip §5.2 entirely and record every hook as
`not tested — hook execution declined`.

**Remediation.**
- Not executable → `chmod +x` the script, re-run the static pass.
- `hook_wired` fail → add the command to the target's own registry under the event the plan named,
  by that adapter's merge rule (find the matching matcher group, append to its `hooks` array, never
  reserialise the file): `.claude/settings.json` (`adapters/claude-code.md` §4.3) or
  `.codex/hooks.json` (`adapters/codex.md` §4.3, where the command is
  `"$(git rev-parse --show-toplevel)/.codex/hooks/<name>.sh"` because Codex sets no project-root
  variable). Then re-run the static pass. For a native git hook, move it into the directory
  `core.hooksPath` names, under a real git hook name. If it does not earn a registration, it does
  not earn a file: delete it and list it skipped. Never "fix" it by leaving the script in place and
  telling the user it is there.
- `hook_static_scan` found a network call → the hook is wrong, not the check. agentify never
  generates a hook that calls out. Rewrite it against a local command, or remove it and report it
  skipped. Never pass `--exec-hooks` to "see what it does".
- Fires on clean work → narrow the pattern or the path scope, re-test once. If it still fires,
  **remove the hook and its registry entry** (`.claude/settings.json` or `.codex/hooks.json`) and
  report it skipped. A false-positive hook is worse than no hook.
- Wrong exit semantics for the chosen strictness → fix the exit code, re-test. On **Codex** that is
  usually the wrong shape rather than the wrong code: the script must exit 0 and print the
  `permissionDecision` JSON, and a script ported from Claude Code that exits 2 has to be rewritten.
- Missing binary → rewrite the hook to use a command that exists, or remove it.
- A Codex hook that never fires → check the matcher first. Codex's tool names are `exec`,
  `exec_command`, `shell_command`, `run`, `apply_patch` — **not** `Bash` / `Edit` / `Write` — and a
  wrong **event** name is worse: a `hooks.json` whose only event was `NotAnEvent` loaded with zero
  hooks, zero warnings and zero errors. Emit only the 12 spelled events (`adapters/codex.md` §4.3).

### 5.3 Installed, loaded, armed — three claims, and only the first is checkable in the run that builds it

The static pass proves a registration exists. `hooks/list` proves the harness *read* it. Those are
different claims with different reachability, and collapsing them into one row is what made this
section's pass condition unreachable on every first run.

**Split the claim in three before you run anything.**

| Claim | What proves it | Reachable in the run that built the hook? |
|---|---|---|
| **Installed correctly** — the script is executable, the registry entry is well-formed, the file the harness will parse does parse | the static pass (`hook_script`, `hook_wired`, `settings_hook_command`), the JSON + key-subset check, and §5.2's fixtures | **always.** This is the pass condition. |
| **Loaded** — this agent, in this repo, has the hook in its live registry | `hooks/list` on Codex; a new session on Claude Code | **only when the environment already allows it** — on Codex the project must already be trusted, on Claude Code the session must have started after the write. Neither is something agentify may arrange. For hooks specifically the answer on a first run is always no, on both targets. |
| **Armed** — the harness will actually execute it | the user's `/hooks` approval on Codex | **never.** Trust is the user's decision, by design. |

A check in row two or three that cannot run is recorded `not tested` with its reason and becomes a
numbered needs-you step (`report-template.md` §3.2). It is never a `fail`, and it is never "fixed"
by weakening row one.

**Codex — establish the trust state first, then read `hooks/list` against it.** In the other order
you cannot interpret the result.
`grep -F "$(printf '[projects."%s"]' "$REPO")" "${CODEX_HOME:-$HOME/.codex}/config.toml"`, read
`trust_level` on the following line, then drive `hooks/list` over the app-server — read-only, no
model call, no session created (`adapters/codex.md` §5 carries the full helper). Start
`"$CODEX" --strict-config app-server` with `cwd` at the repo, send `initialize`, then
`{"id":2,"method":"hooks/list","params":{"cwds":["$REPO"]}}` and read `result.data[0]`.

Four outcomes. All four were measured on 2026-09-05 against `codex-cli 0.153.1`, in a scratch
`CODEX_HOME` whose only change between runs was the trust line:

| Trust state | `hooks` | `warnings` | Verdict |
|---|---|---|---|
| no `[projects."<repo>"]` entry, or `trust_level = "untrusted"` | `[]` | `[]` | **`not tested — project not trusted`.** This is the *expected* result of a correct build in a repo Codex has not been trusted in, and it is what a fresh clone always gives you. The reason appears **only on the app-server's stderr**: `Project-local config, hooks, and exec policies are disabled in the following folders until the project is trusted, but skills still load.` Capture stderr and match that line, so the report can say which of the two it was rather than guess. |
| trusted, file well-formed | one entry per generated hook | `[]` | **pass** on `eventName`, `matcher`, `sourcePath`, and `source: "project"` — `"user"` would mean something wrote to the global file, which agentify must never do. `trustStatus` is `"untrusted"` here too; that is the *armed* question, not the *loaded* one. |
| trusted, file rejected | `[]` | one message naming the field, line and column. Measured, on a `hooks.json` carrying a stray top-level `version` key: <code>failed to parse hooks config …/.codex/hooks.json: unknown field &#96;version&#96;, expected &#96;description&#96; or &#96;hooks&#96; at line 17 column 11</code> | **fail.** Fix the file, re-run. |
| **not trusted, file rejected** | `[]` | `[]` | **byte-identical to row one.** The trust gate runs ahead of the parser, so here `hooks/list` says nothing whatever about the file's validity. Measured. |

That last row is why the static JSON check is the authority and `hooks/list` is only ever
corroboration: on a first run it cannot tell a perfect `hooks.json` from a broken one. Never let a
clean-empty `hooks/list` stand in for the parse, and never read one as evidence of either outcome.

**`eventName` comes back camelCased.** A hook declared under `"PreToolUse"` is reported as
`"preToolUse"`. Compare case-insensitively — a literal equality against the declared spelling fails
on a perfectly good hook. Measured.

**Never manufacture the trusted state to reach the check.** Pointing `CODEX_HOME` at a scratch
directory carrying a `trust_level = "trusted"` line does make `hooks/list` return the hook — and it
also makes Codex build an entire new home there: sqlite stores, an `installation_id`, and **`git`
clones of the plugin marketplaces**, which is a network call out of a phase that promises none
(PRD §13). Measured: one `initialize` against a scratch home left seven `plugins-clone-*` working
trees with packfiles in it. Do not do it, do not suggest it to the user, and above all never write
the trust line into the user's real `${CODEX_HOME}/config.toml`. Whether a directory is trusted is a
security decision belonging to the person whose machine it is; agentify's job is to tell them the
decision is theirs to make, in one numbered step, with the reason.

**Three limits are real, must be stated in the report, and must never be papered over as "live":**

1. **Installed ≠ armed.** Every hook comes back `"trustStatus":"untrusted"`, trusted project or not.
   The user arms it with `/hooks` in a Codex session, and editing a hook re-arms the prompt (trust
   is keyed to a hash of the definition — the `currentHash` field). Report line: *"Run `/hooks` in
   Codex and trust the new hooks; until you do, they are installed but do not run."* **Never emit or
   suggest `--dangerously-bypass-hook-trust`.**
2. **A repo-scoped artifact is inert until the project is trusted.** With no trusted
   `[projects."<repo>"]` entry in `${CODEX_HOME:-~/.codex}/config.toml`, `.codex/hooks.json`,
   `.codex/rules/` and `<repo>/.codex/config.toml` all do nothing, silently. agentify never edits
   that file: it is the **first** item in the report's needs-you section. `AGENTS.md` is the one
   exception, and a narrower one than it looks — measured, it loads when there is **no** `[projects]`
   entry and is suppressed only by an explicit `trust_level = "untrusted"`.
3. **agentify cannot restart the user's session**, so anything needing a fresh one is a manual item.

If no `codex` binary resolves (`command -v codex` finds nothing on a working install — check
`~/.local/bin/codex` and `/Applications/ChatGPT.app/Contents/Resources/codex` too), fall back to the
static checks and **say in the report which mode ran**.

**Claude Code — the same split, and the same gap.** Static half:
`python3 -c "import json;json.load(open('.claude/settings.json'))"`, then confirm every pre-existing
top-level key survived the merge. Loaded half: **a hook added to `settings.json` does not apply to
the session that wrote it** (`adapters/claude-code.md` §5). Claude Code fixes its hook set at session
start, so there is no in-run equivalent of `hooks/list` and no amount of re-reading the file changes
that. This is not a Codex-only wrinkle wearing a different hat — on **both** targets the run that
builds a hook cannot be the run that watches it load. Record it `not tested — needs a new session`
and put the numbered step in needs-you: open a new session in this repo, run `/hooks`, and confirm
the entry is listed under the event it was built for. The same treatment goes to any newly written
project skill, subagent or rule this session cannot see (`adapters/claude-code.md` §5) — one
numbered step each, never a silent `pass`.

---

## 6. Rules

### 6.0 Two artifacts share the name `rule`. Check the one in front of you.

`"type": "rule"` covers two artifacts that have nothing in common but the word:

| | **Prose rule** | **Command policy** |
|---|---|---|
| Where | `.claude/rules/<name>.md`; on Codex `<plan-dir>/rules/<name>.md` plus an `AGENTS.md` pointer, or inlined into the section | `<repo>/.codex/rules/<name>.rules` — **Codex only**, no Claude Code equivalent |
| What | markdown with `scope:` frontmatter | Starlark `prefix_rule(pattern=[…], decision=…)` — an execution policy, the analogue of Claude Code's permissions allowlist |
| Says | "handlers return `Result`, not exceptions" | "never run `npm`" |
| Loaded by | the index doc pointing at it | Codex reading `.codex/rules/` itself, once the project is trusted |
| Checked by | `rule_scope`, `rule_body`, `rule_wired`, `rule_contradiction` | `rule_policy_syntax`, `rule_policy_decision`, `rule_policy_pattern`, `rule_policy_examples`, `rule_policy_execpolicy` |

The static pass decides which is which from the file itself and runs only that column. **Do not
carry a verdict across the columns.** A command policy has no `scope:` and needs no pointer;
asking it for either failed a correct artifact on the 2026-09-05 Codex dogfood, and §9's
fix-or-remove loop then reads that fail as an instruction to delete good work. If you ever see a
`rule_scope` or `rule_wired` row against a `.rules` file, the checker is wrong and the artifact is
not — say so in the report and change nothing.

**The command policy is the one generated artifact that can break the user's editor.** A
malformed `.rules` file is a *fatal Codex startup error, not a skipped file*: measured, a bad
`decision` value produced `Error loading rules: … invalid decision: ask` and `codex exec` then
refused to start in that repo at all. `rule_policy_decision` and `rule_policy_syntax` are the two
rows to read first on any Codex run that built one. Where a `codex` binary is available, confirm
by hand as well — `codex execpolicy check --pretty --rules .codex/rules/agentify.rules -- <a
command the rule should catch>`, exit 0 with a `matchedRules` entry carrying the expected
`decision`.

### 6.1 Prose rules

Rules are not executable, so verification is a consistency read, not a run.

**The static pass already does the mechanical half of both passes below** — `rule_contradiction`
reads every rule clause by clause, keys each directive on a normalized subject, and reports
opposing polarity, two members of one exclusive category, and (with `--discovery`) a clash with
`discovery.json`. Start from its rows. What it cannot do is judge *meaning*: paraphrase
("everything goes through the repository layer" vs "call the driver directly from the route"),
a contradiction with an existing CONTRIBUTING or index doc, or a rule that duplicates something
already documented. Those are yours, and they are what the two passes below are for. Treat a
`rule_contradiction` PASS as "no mechanical collision", never as "the rules agree".

**What it deliberately does not read, and why.** A fenced block is an illustration, and everything
under a negative-example heading — `## Incorrect`, `## Anti-pattern`, `## Avoid`, `## Wrong`, down
to the next heading at the same or a higher level — is a negative example, fenced or not. Neither
is a directive. This is not a nicety: `rule.md.tmpl` *mandates* a `## Correct` / `## Incorrect`
pair and ends with an unfenced explanation paragraph under the Incorrect heading, so every rule the
shipped template produces states the opposite of itself somewhere in its body. Read literally, that
hard-failed a correct rule on the 2026-09-05 Codex dogfood with *contradicts-convention on package
manager: rule forbids pnpm, which is the package manager this repo uses* — against a rule whose
whole point was to use pnpm. A tool name inside a longer dotted or hyphenated token
(`pnpm-lock.yaml`, `bun.lockb`, `vitest.config.ts`) is a **file**, not a statement about the tool,
and is not read as one either. If you are judging a rule by hand, apply the same discipline: the
directive is the imperative sentence, not the counter-example under it.

Two of its rows are already verdicts, not hints, and both are fails you act on rather than record:

- `rule_contradiction` → `contradicts-convention` against a hard fact (`package_managers`, a
  `commands.*` line) is this section's Fail case, mechanically detected. Apply the Remediation
  below — the repo wins — rather than re-deriving it by hand.
- `rule_wired` is the other half of "does this rule do anything at all". A rule the index doc does
  not point at is never loaded, so its content is beside the point: wire it or drop it, before you
  spend a paragraph judging what it says.

**Test.** Two passes.

1. **Against each other.** Extract each rule's assertion as a normalized `key → value` pair
   (`package_manager → bun`, `test_runner → vitest`, `db_access → repository layer only`,
   `commit_format → conventional`). Two rules asserting different values for the same key is a
   contradiction. Check path-scoped rules for overlapping scopes that assert different values on
   the same key — a global rule and a `src/db/` rule may differ only if the scoped one is
   explicitly the narrower exception and says so.
2. **Against discovered conventions.** Check every rule against the evidence that is supposed to
   support it: `discovery.commands`, `discovery.package_managers`, `discovery.frameworks`,
   `signals.git.commit_conventions`, `signals.git.branch_naming`, `signals.git.test_discipline`, and any
   existing index doc or CONTRIBUTING content. A rule that contradicts what the repo actually
   does is wrong even if the user's prompts asked for it — in that case the rule is aspirational,
   and it must be worded as the intent (`we are moving to X`) rather than as a description.

3. **That anything loads it.** Every **prose** rule must be referenced from the index doc — a
   prose rules directory is a repo convention, not a load path, and neither Claude Code nor Codex
   walks one. The static pass's `rule_wired` row is this check; read it rather than re-running the
   grep. A rule with no reference is not a weak rule, it is an inert one. **A Codex command policy
   is the exception**, and the static pass says so in its row: `.codex/rules/` *is* a native load
   path, so nothing needs to point at it. Never add a pointer to `AGENTS.md`, or a fake `scope:`
   line, to make a check go green.

Also check that each rule still carries its evidence line and its `agentify-id`, and that no rule
duplicates a statement already present in the pre-existing index doc — duplication is what makes
index docs unreadable. The evidence line's *wording* is mechanical too: `evidence_match` fails when
the rule's `agentify-evidence` is no longer the string the manifest carries, which means the file
has been regenerated from something other than the approved plan.

**Pass.** No key asserted two ways; every rule consistent with, or explicitly framed as a
correction to, discovered convention; every rule referenced from the index doc; no duplicate of
existing documentation.

**Fail.** A direct contradiction between two generated rules, or between a rule and a hard
discovered fact (a rule saying "use npm" in a repo with `bun.lockb` and `packageManager: bun` —
`rule_contradiction` catches this one for you, but only when the run passed `--discovery`). A rule
no index doc references is also a fail, for a different reason: nothing loads it.

**Warn.** Two rules that overlap in topic without contradicting, or a rule whose evidence is a
single occurrence.

**Remediation.**
- Two generated rules contradict → keep the one with the stronger evidence count, delete the
  other, and note the deletion in the report.
- Rule contradicts discovered fact → the repo wins. Rewrite the rule to match, or delete it. If
  the user genuinely asked for the change, reword it as intent — `we are moving to npm` — which is
  both the honest wording and what clears the check.
- `rule_wired` fail → add the rule to the index doc's Rules table (or, for a rule that must apply
  every turn, an `@` import; cap 2 of those) and re-run the static pass. If it does not earn a row
  in the index doc, it does not earn a file: delete it and list it skipped.
- `evidence_match` fail → restore the manifest's evidence string into the file's frontmatter. Do
  not "fix" it by editing the manifest to match the file: the manifest carries the string the plan
  was approved with, and rewriting it hides the drift instead of undoing it.
- Duplicate of existing docs → delete the generated rule; the existing doc already covers it.
- Never resolve a contradiction by keeping both and adding a qualifier.

### 6.2 Command policies (Codex)

**Test.** Read the five `rule_policy_*` rows, then read the file as a human would: a policy is
something someone meets when a command they expected to work is refused, and the `justification`
is the sentence they read. It must state the fix, not the complaint.

**Pass.** It parses; every `decision` is `allow` / `prompt` / `forbidden`; every `pattern` is
non-empty and no longer than the evidence justifies; every `match` example is caught and every
`not_match` example stays allowed; and, where a `codex` binary exists, `codex execpolicy check`
agrees.

**Fail.** It does not parse, or any `decision` is another value — both are fatal startup errors
that stop every Codex session in the repo, so this is the one artifact type where a fail must
never be left in place while the report is written. A `match` example no rule catches is the same
error arriving at load time. A rule with an empty pattern matches nothing or everything.

**Warn.** No `not_match` examples, so nothing pins down what stays allowed; or an unrecognised
policy function, which the rules language being experimental makes plausible rather than wrong.

**Remediation.**
- Does not parse, or an illegal `decision` → fix it, or **delete the file**. Never publish a
  handoff with a failing `.rules` file in the repo: the failure mode is the user's next session
  refusing to start, and they will not connect it to this run.
- A `match` no rule catches → the example and the pattern disagree; fix whichever the evidence
  supports, then re-run.
- No `not_match` → add the near-miss the user is supposed to run instead. Prefix matching has no
  semantics: `npm` does not catch `npx`, `pnpm`, or npm reached through `bash -c`, and the plan
  must say so rather than claim the gate is airtight.
- Trust gate → the file is inert until `[projects."<abs path>"] trust_level = "trusted"`. That is
  a capability note for the plan and a manual step in the report, never a verification fail.

---

## 7. Subagents

**Two file shapes, one artifact type.** Claude Code reads `.claude/agents/<name>.md` — markdown
with YAML frontmatter. Codex reads `<repo>/.codex/agents/<name>.toml` — TOML with `name`,
`description` and `developer_instructions` required, `model_reasoning_effort` and `sandbox_mode`
optional, and **no per-agent tool allowlist at all**. The static pass reads whichever it is given
(until 2026-09-05 it asked the TOML file for YAML frontmatter and failed every correct Codex
subagent); when you judge one by hand, judge it as the format it is. On Codex the static contract
is: it parses as TOML, the three required keys are present, and the filename stem equals `name`.

**Test.** Dry-run each generated subagent with one trivial prompt that requires no tools and no
repo mutation — for example `Reply with your name and the one kind of task you handle.` The point
is to confirm it loads, its identity block parses, its tool list resolves (Claude Code) or its
`sandbox_mode` is honest (Codex), and its description does not collide with another agent's.

**Pass.** It loads, responds in the persona and scope the file defines, and names the same
responsibility the plan claimed for it.

**Fail.** It does not load; its frontmatter is malformed; it requests a tool that does not exist
in this environment; its description is so close to another agent's that dispatch is ambiguous
(the static pass catches exact name duplicates; this catches near-duplicates in description);
it answers as a generic assistant with no evidence of its instructions.

**Warn.** It loads but the response is generic — usually a description that is too broad.

**Remediation.**
- Malformed frontmatter → fix and re-test once.
- Unavailable tool → remove that tool from the list; if the agent's purpose depends on it, remove
  the agent.
- Codex, and the candidate's value depended on tool restriction → there is no equivalent. Emit
  `sandbox_mode = "read-only"` for review and analysis work, state the loss in the plan's
  capability notes, and never emit `danger-full-access` — the static pass fails that outright.
- Ambiguous description → sharpen it to name the concrete trigger from its evidence.
- Still failing → **remove the agent file** and report it skipped.

---

## 8. MCP drafts, permissions, index doc

**MCP drafts.** Verify as configuration only, **in the target's own format** — the two are not
interchangeable, and writing `.mcp.json` for a Codex target configures nothing. Claude Code:
`.mcp.json`, JSON, `mcpServers`. Codex: `[mcp_servers.<name>]` TOML tables, drafted to
`<plan-dir>/codex-mcp.toml` by default and appended into `<repo>/.codex/config.toml` only on an
explicit opt-in. Pass: it parses in that format (static pass, `mcp_json`), the server entry names
a real command or URL, every key sits under a `[table]` header, and it contains **no credential
value** — only an env var *name*. Fail: it does not parse in its own format, or any literal secret
in the file. Remediation: replace any literal with an
env var name, immediately; then confirm the auth steps are in the report's "Needs you" section,
one numbered step each. **Never attempt to connect** to verify it. An unauthenticated server is
the expected state at handoff, not a failure.

**Index doc section.** Pass: the appended section is delimited by its `agentify-id` markers, the
pre-existing content above it is byte-identical to before the run (diff the file against the
branch base to confirm), it links only to files that exist, and it carries the attribution
footer once. Fail: any pre-existing byte changed, a dead link, or duplicated markers from a
previous run. Remediation: restore the original content, re-append cleanly.

Check the other direction too, and the static pass does it for you: every generated rule needs a
link *in*, not just working links *out*. That is `rule_wired`, and a fail there means the section
was built with a row missing — add the row rather than deleting the rule, unless the rule was not
worth a row in the first place.

**Permissions.** On Claude Code the artifact is the `permissions` object inside
`.claude/settings.json`, verified as the `settings` artifact it shares a manifest entry with
(`build-and-verify.md` §5.4). Five checks, all static, none of them executing anything:

1. **The file still parses**, and every key the user had is still there — this is the second merge
   into that file in one run, so diff its key set against the pre-run bytes, not just the hooks half.
2. **Every entry this run added is in `merge.entries`** as `("permission_entry", "<list>:<rule>")`,
   one per string, exact. An entry in the file and not in the manifest is a rule no undo removes.
3. **No `allow` or `ask` entry matches a secret path.** Grep the allow and ask arrays for `.env`,
   `credential`, `secret`, `.pem`, `id_rsa`, `.netrc`. A hit is a **fail**, not a warning: it is
   agentify pre-approving a read it is forbidden to make. Remediation is deletion, not narrowing.
4. **No `deny` entry blocks a command the repo's own `discovery.commands` defines**, unless the
   interview explicitly ruled that manager or command out (Q15). A `deny` on the developer's daily
   command is the failure that gets the whole setup deleted.
5. **Contradictions with the user's own entries are reported, not resolved.** `deny` beats `allow`,
   so a generated `deny` overlapping a pre-existing `allow` silently disables their rule. That is a
   **warn** plus a "needs you" line naming both entries — never an edit to theirs.

On Codex there is no permissions block: the surface is `.codex/rules/agentify.rules`, already
covered by §6.2's command-policy checks, and `codex execpolicy check` is the whole test.

**Plugin manifest — not built.** agentify emits no plugin manifest on either target
(`adapters/capabilities.md`). The `plugin_paths` static check (§2) remains, because a rerun over a
repo an older agentify wrote into can still find one in the manifest and must not report a dangling
path as clean. A **new** run that produces a `plugin` artifact is a phase-4 defect: report it, and
do not verify your way around it.

---

## 9. Recording results and closing the phase

### 9.0 One dangling link is correct, and it resolves at step 5

**The index doc links to `report.md` before `report.md` exists.** The index-doc section is built
first in phase 7's build order; `report.md` is written at §9 step 5, last of everything. So when §8's
index-doc check runs its "links only to files that exist" test — and when the Codex adapter's
Index doc row runs the same test (`adapters/codex.md` §5) — `PLAN_DIR/report.md` is **not on disk
yet**. Measured on the 2026-09-05 h3 run: `docs/agentic-setup/report.md` came back DANGLING in a run
where every artifact was correct.

That is the expected state, not a finding. Which link may dangle at which moment is fixed:

| Link target in the index-doc section | Phase 8 before step 5 | Phase 8 after step 5 |
|---|---|---|
| `PLAN_DIR/plan.md` | **must resolve** — written in phase 6, and a dangling plan link is a real fail | must resolve |
| every rule / skill / subagent path | **must resolve** — written in phase 7; a dangling one means the artifact was removed and its row was not | must resolve |
| `PLAN_DIR/report.md` | **expected to dangle.** Record it and move on | **must resolve.** This is where the check becomes meaningful |

Rules that follow, and the first is the one that matters:

- **Never remove a link to satisfy this check.** Deleting the `report.md` link cuts the index doc's
  pointer to the run record, at the one moment the link is about to become valid. If the check
  reports `report.md` dangling before step 5, the correct action is none. `index-doc-section.md.tmpl`
  emits that link twice — the header line and the MCP line — so a model "fixing" it removes both.
- Re-test the link **after** step 5, not before, and put *that* result in the report's verification
  table. Step 6's static re-run is the natural place: it happens after the report is written, so a
  `report.md` link that is still dangling there is a genuine fail — a wrong `PLAN_DIR`, or a report
  written to a path the index doc does not name.
- Any *other* dangling link, at any point, is a real fail and is handled by §8's remediation:
  restore the target or drop the row.

For every artifact, exactly one of:

- **pass** → row in the report's verification table, artifact stays.
- **warn** → row with the detail spelled out, artifact stays.
- **fail, fixed** → re-test, then record the final status. Note the fix in the Detail column.
- **fail, removed** → delete the artifact's files, remove its entry from
  `build-manifest.json` and from its registry wiring (`.claude/settings.json` /
  `.codex/hooks.json`), re-run the static pass, and move it
  to the report's Skipped table with the reason `failed verification and was removed`.

**One thing is never a reason to remove an artifact: a check asking it for something its format
does not have.** Three manifest types have two file shapes each — `rule` (prose markdown, or a
Codex Starlark command policy), `subagent` (markdown frontmatter, or Codex TOML) and `mcp`
(`.mcp.json`, or Codex `[mcp_servers.*]` TOML) — and every check is written to read the shape in
front of it. If one ever fails an artifact for lacking a field the other shape carries — a
`scope:` on a `.rules` file, YAML frontmatter in a `.toml` agent, `mcpServers` in a TOML draft —
the checker is wrong and the artifact is not. Record it in the report as a verifier defect, name
the check, and **change nothing**. Never add a fake field, a pointer, or a format the target does
not read in order to make a row go green: that ships a file the agent cannot use, and it hides the
defect from whoever fixes the checker. No template documents an expected FAIL any more, and none
should: a check documented to fail on a correct artifact is not a check, it is a trap.

Then, in this order:

1. Re-run `verify_artifacts.py` so the reported summary matches the final state. Carry the same
   flags as the run the user agreed to: keep `--discovery`, and keep `--exec-hooks` only if they
   said yes in §5.1. **This is the run whose rows go into the report's verification table** — it
   covers every artifact plus `plan.md` and the manifest itself (§2.0).
2. Delete the scratch fixture directory.
3. Confirm `git status --porcelain` shows only the intended artifact files, and that nothing is
   staged that should not be.
4a. **Reserve `report.md`'s path in the undo lists — now, before step 4 and before the report is
   written.** Add the path (not an `artifacts[]` entry — see step 6) to `committed_paths` in
   `branch` mode, where phase 8 step 5 commits the report to the branch, and to
   `uncommitted_paths` in the other two, where the removal list has to name it by hand. Add
   `PLAN_DIR/` to `created_dirs` here too if this run brought it into existence and it is not
   there already.

   **The ordering is the fix, and it is deliberate.** The two halves of "add the report to the
   manifest" have opposite deadlines and used to be done together at step 6, which is one step too
   late for one of them:

   | half | earliest it may happen | latest it may happen |
   |---|---|---|
   | the **path**, in `committed_paths` / `uncommitted_paths` | now — nothing about a path needs the file to exist | **here.** §10 enumerates these lists and `report-template.md` §3.1 derives `N` from `len(committed_paths)` and `M` from `len(uncommitted_paths)` |
   | the **`artifacts[]` entry** | step 6 — `file_exists` FAILs on a file that has not been written | step 6 |

   Do it at step 6 and every count the report prints was computed one path short: the
   `REMOVAL_MODE_SENTENCE` says `N` when the truth is `N + 1`, the `uninstall` row in §10.5 adds
   up to one less than the manifest, and §10.2's enumeration never sees the one file the user is
   most likely to still have on disk after an undo they were told removes everything. Measured on
   the axios run — the report claimed a file count that excluded itself.

   **The one cost, and do not "fix" it.** Between here and step 6 the path is in an undo list with
   no artifact to match, so step 4's re-run — if you make one — reports exactly one extra
   `undo_partition` **WARN**: `1 path(s) in the undo lists match no artifact … report.md`. It is a
   WARN and never a FAIL (measured on a fixture: `{'pass': 16, 'fail': 0, 'warn': 1}`), it is
   correct while it lasts, and step 6 clears it (same fixture, entry appended:
   `{'pass': 23, 'fail': 0, 'warn': 0}`). Removing the reservation to silence it puts the off-by-one
   straight back.
4. Run the uninstall check (§10). It decides what the report's removal section may claim.
5. Write `report.md` per `report-template.md`. Every count in it is now final, because 4a made the
   partition final. Two more things feed it here. Every check §5.3 recorded `not tested` —
   project trust, hook trust, a session that has to be restarted — becomes a numbered needs-you
   step carrying its reason (`report-template.md` §3.2); a `not tested` row with no matching
   needs-you step is the defect this sentence exists to prevent. And the moment this file is on
   disk the index doc's `report.md` link resolves, so re-run that link check (§9.0) and let step
   6 be the run that reports it.
6. **Now add the report's `artifacts[]` entry and verify it.** `report.md` is the last thing
   agentify writes and the one file step 1 could not cover, because it did not exist yet. Append:

   ```json
   {"id": "agentic-setup-report", "type": "report",
    "path": "docs/agentic-setup/report.md", "action": "created",
    "evidence": "handoff for the 12 artifacts built and 4 skipped",
    "ignored": false}
   ```

   **The path is already in the undo lists — 4a put it there. Do not add it again**, and above all
   do not add it to the *other* list: a path in both is an `undo_partition` FAIL, and it is the one
   way this step can break what 4a fixed.

   then run the static pass once more, with the same flags. Two outcomes, and no third:
   - **clean** → add one line under the report's verification table: `report.md and
     build-manifest.json verified after the table was written: N checks, all pass.` The table
     stays as it is; re-running it into the table would only chase its own tail.
   - **not clean** → fix `report.md` (a missing `agentify-id`, an empty file, a path that escaped
     the plan directory), re-run, and only then hand off. A report that fails its own verifier is
     the one artifact the user is guaranteed to read.

   Appending this entry changes `build-manifest.json` after the manifest was itself verified, and
   that is fine on purpose: the manifest's own checks are existence, non-emptiness, valid JSON and
   the `_agentify` identity, none of which depends on its contents. See §2.0.

Never report an artifact as verified because it looked correct. If it was not exercised, its row
says `not tested` with the reason, and the report says so plainly.

---

## 10. The uninstall check — prove the undo before you publish it

Run this after §9's fix-or-remove loop and **before** you write `report.md`, because it decides what
that report's "How to remove everything" section is allowed to say. `report-template.md` §3.1
generates three different undos out of `build-manifest.json`; this section is where you find out
whether the one you are about to print is true.

PRD §3 promises `reversible` and PRD §13 promises an uninstall path in every report. **A §10 that
passes a broken undo is worse than no §10 at all.** With no §10, a careful reader still checks the
commands before trusting them. With a §10 that passed, the report says the undo was *proved*, the
user pastes it, git prints `Deleted branch`, and they stop looking. Everything below is written to
fail loudly rather than to pass cheaply; if a check here is ever softened to make a run go green, it
should be deleted instead.

Two measured runs are why:

- **The branch that held nothing.** A dogfood run printed `git checkout master && git branch -D
  agentic-setup/2026-09-04`, ran it verbatim, and git answered `Deleted branch
  agentic-setup/2026-09-04 (was ba6d13d)` — where `ba6d13d` was the base branch's own tip. Nothing
  was removed. The commands were correct for a build that had committed. That build had not.
- **The branch that held only what `.gitignore` allowed.** A run on a clone of `vercel/turborepo`,
  whose `.gitignore` line 6 is `.claude/`, generated 9 artifacts and committed 4. The other 5 — three
  rules, the hook script, `settings.json` — could not be added by a plain `git add`, so the branch
  never contained them and the delete left every one of them on disk. **Every §10.2 precondition as
  it was then written passed**: the log listed a commit, the base tip had not moved, and
  `git status --porcelain -uall` was empty — because `git status` does not list ignored files. That
  is the same failure as the first one, arriving through a door the check did not watch.

The lesson both times is the same, and §10.2 is now built on it: **do not check that the mechanism
ran, check that every artifact is covered by one.** A precondition that reads the shape of the build
("is there a commit?") passes for reasons that have nothing to do with the artifacts. Only an
enumeration over the manifest can fail for the right reason.

**Nothing here removes anything from the user's repo.** Every check below is a read, except §10.4,
which runs in a throwaway copy.

### 10.1 The mode is whatever the manifest says — and the mode alone no longer picks the undo

`manifest.mode` chooses the §3.1 block. Never infer it from the fact that a branch name exists, and
never print the branch-delete lines because the run "was on a branch".

| `mode` | Undo block in §3.1 | It is wrong when |
|---|---|---|
| `branch`, `uncommitted_paths` empty | two-line branch delete | nothing was committed to the branch |
| `branch`, `uncommitted_paths` non-empty | branch delete **plus** step 2's per-file removal | either half is missing, or a path is in neither |
| `stage-only` | six-step per-file removal | a path in the list is not on disk, or `git restore --staged` is given a path git never staged |
| `no-git` | file removal plus the marker script and the JSON un-merge script, whichever the formats present call for | same, or a JSON config was handed to the marker script |

The second row is the one that keeps being lost. `mode` describes the *workspace*; the
`committed_paths` / `uncommitted_paths` partition describes each *artifact*; the undo is chosen by
both. Never read a single per-run flag — a run is routinely half committed and half not, and one
boolean cannot say which half a given file is in.

**And the partition is only the first of two questions.** It says whether git can put a file back;
when git cannot, the file's **format** says which script takes agentify's contribution out. There
are two scripts in `report-template.md` §3.1 and they are not interchangeable:

| the file agentify changed | mechanism | keyed on |
|---|---|---|
| a **marked text file** — `CLAUDE.md`, a rule, a shell config | the marker script | the `agentify:begin` / `agentify:end` pair for its `agentify-id` |
| a **structurally merged JSON config** — `.claude/settings.json` or `.codex/hooks.json`, `.mcp.json` (`type: settings` / `type: mcp` **and a `.json` file**) | the **JSON un-merge script** | the entries this run merged in: each hook artifact's manifest `command`, each `mcpServers` name, and an `_agentify` object whose `agentify-id` matches |

**Read the file's format, not its manifest `type`.** The `mcp` type is JSON on Claude Code and
**TOML** on Codex, and the un-merge script parses JSON. So a Codex `mcp` artifact is routed like
any other file of its shape: `<plan-dir>/codex-mcp.toml` is a draft agentify created whole and
`rm` removes it exactly; an opt-in append into `<repo>/.codex/config.toml` is a marked block —
TOML takes `#` comments — and the marker script takes it out. The un-merge script can do neither,
and there is no TOML writer in the standard library at any version, which is why agentify never
rewrites that file programmatically in the first place. Routing the draft to the un-merge script
made a correct removal block fail with *the removal block `rm`s this JSON config* — the same
defect class as `rule_scope` on a command policy, one artifact type over.

**JSON cannot hold a comment, so a JSON config never carried a marker and never can.** Handed one,
the marker script finds no block, prints `SKIP <path>: no agentify block id=…`, **exits 0**, and
removes nothing — every other step in the undo succeeds around it and the report calls the run
reversible. Reproduced on a fixture while writing this section: `SKIP  .claude/settings.json: no
agentify block id=enforce-bun`, exit 0, file byte-identical before and after, `enforce-bun` still
registered in the user's settings. That is the third file-format defect of this class to ship; the
first two were the branch that held nothing and the branch that held only what `.gitignore`
allowed. **Coverage is necessary and not sufficient** — a step that names the path and then no-ops
reads as covered in every enumeration, which is why §10.2 asks the format question too and §10.4's
byte diff is the only check that cannot pass for the wrong reason.

**A branch delete undoes a path only when git can put that path back.** Phase 7 step 4 keeps two
kinds of artifact off the branch for that reason, and both land in `uncommitted_paths`:

1. **gitignored** — git would not add it, so the branch never held it. The turborepo case.
2. **`action: modified` with `restore: span`** — a file that existed before the run but git never
   tracked. Committing it makes `git checkout BASE_BRANCH` **delete the user's own file** rather
   than restore it, because the base branch has no version to go back to. Measured on a fixture: a
   hand-written untracked `.claude/settings.json` that the run appended to was committed by phase 7
   and destroyed, directory and all, by the undo.

Check both. A manifest with a `restore: span` entry in `committed_paths` is a data-loss bug, not a
reporting one: stop, and tell the user before they run anything.

### 10.2 Every artifact is covered by a removal mechanism — enumerate, never infer

This is the check. It runs in every mode, and it is the only one that can fail for the right reason.

Build two sets and compare them against the manifest:

```bash
# 1. what the BRANCH holds against its base (branch mode; empty in the other modes).
#    BASE_COMMIT is manifest.base_commit -- the whole branch, not one commit.
git -C "$REPO_ROOT" diff --name-only "$BASE_COMMIT".."$branch_name" | LC_ALL=C sort -u

# 2. what the undo you are about to print names for explicit per-file removal
#    (the rm -f / restore / marker-script paths out of the §3.1 block you generated)
```

**Set 1 is a diff against the base, not `git show`, and that is not a style preference.** `git show
--name-only --pretty=format: "$branch_name"` prints the **tip commit alone**, and a branch-mode run
commits twice — phase 7 commits the artifacts, phase 8 commits `report.md` and the manifest — so set 1
came back missing everything in the first commit. Measured on a two-commit branch: `git show` returned
`build-manifest.json` and `report.md`; `git diff --name-only <base>..<branch>` returned those plus
`plan.md`, the generated skill and the appended `README.md`. The axios dogfood run reported the same
shape — `CLAUDE.md`, `build-manifest.json`, `report.md`, and not `plan.md`. Since phase 7 step 4
*corrects* `committed_paths` from set 1, the partition itself was being trimmed to the last commit.

Worse, `git show` fails **open** on the case this section exists for: on a branch with **no commit**,
`git show --name-only <branch>` prints the **base commit's** file list, exit 0 — so the "branch that
held nothing" run gets set 1 populated with files it never committed, and any artifact sharing a name
with one of them reads as covered. `git diff --name-only <base>..<branch>` prints nothing there,
exit 0, which is the answer that makes the enumeration below fail for the right reason.

If `manifest.base_commit` is empty (no commits existed before the run) there is nothing to diff
against and the branch is the entire history — use
`git -C "$REPO_ROOT" log --name-only --pretty=format: "$branch_name" | sed '/^$/d' | LC_ALL=C sort -u`
for set 1 instead.

Then, **for every artifact in `build-manifest.json`**, in order, assert that its `path` appears in
set 1 **or** in set 2. Not "most of them". Not "the ones under `.claude/`". Every one, including
`plan.md` and `build-manifest.json`. `report.md` has no `artifacts[]` entry yet — step 6 appends it
— but **its path is already in the partition lists**, reserved at §9 step 4a precisely so this
enumeration and the report's counts see it. Check that path here by hand, as a set of one.

**Then ask the second question of every path in set 2: can the step that names it actually act on
that file?** Set 2 is a list of paths and a list of mechanisms, and a path is only covered when the
two agree. Walk it against the §10.1 format table:

- an `action: created` path → `rm -f` names it — **unless it is a JSON config** (`type: settings`
  or `type: mcp` **in a `.json` file**; a Codex `.toml` draft is an ordinary created file and `rm`
  is correct for it), which the un-merge script owns instead, so it may not appear in the `rm -f` operand
  list at all;
- an `action: modified` **marked text file** → the marker script's `BLOCKS` list names it, with its
  `agentify-id` and `pre_existing_sha256`;
- an `action: modified` **JSON config** → the un-merge script's `UNMERGE` list names it, with its
  merged entries.

- **fail, a JSON config is in the marker script's `BLOCKS`** — this is the axios defect and it
  passes every coverage check ever written, because the path *is* named. Move it to `UNMERGE`.
- **fail, a JSON config is in an `rm -f` operand list** — a blind `rm` destroys whatever the user
  added to that file after the run. Move it to `UNMERGE`; the script deletes the file itself when
  agentify created it and nothing else is left, and keeps it when something is.
- **fail, the run merged into a JSON config and §3.1 emitted no un-merge block** — the generator
  read `restore: span` as though it named a mechanism. It names the git half of the problem only.

**Half of that enumeration is already done for you, and it is the half you would get wrong by
hand.** The static pass's `undo_partition` walks the manifest and asserts exactly this against
`committed_paths` / `uncommitted_paths`: every artifact in one list and not the other, no
`ignored: true` and no `restore: span` entry sitting in `committed_paths`. Read those rows first.
What it cannot do is compare the lists against what the branch commit and the generated §3.1 block
*actually* contain — set 1 and set 2 above — which is what the rest of this section is for. A green
`undo_partition` means the manifest is self-consistent, never that the undo was run.

- **pass** — every artifact path is in exactly one of the two sets, and `manifest.committed_paths`
  and `manifest.uncommitted_paths` partition them the same way phase 7 recorded.
- **fail, a path is in neither** — that file survives the undo. This is the turborepo failure. Do not
  soften the wording, do not scope the report's claim down to "removes most of it", and do not
  delete the removal section. Fix the generated undo so the path is in set 2, then re-run this check.
- **fail, a path is in both** — the undo tries to `rm` something the branch delete already removed.
  Harmless to run, but it means `ignored` and the commit disagree; find out which is wrong.
- **fail, `manifest.uncommitted_paths` is non-empty and the §3.1 block has no step 2** — the generator
  read `mode` and ignored `ignored`. Regenerate it.

Two properties of the tools make the naive versions of this check useless, and both were measured:

- **`git status --porcelain -uall` is blind to ignored files.** On the turborepo shape it printed
  nothing while five generated files sat in the working tree. `--ignored=traditional` shows them,
  but a status flag is still the wrong instrument: it reports the tree, and the question is about the
  manifest. Enumerate the manifest.
- **`git add -- <mixed list>` exits 1 and stages the rest anyway.** So a build can half-fail and look
  fine. `git add -A` skips ignored paths and exits 0, with no message at all. Neither exit code tells
  you what is on the branch; `git diff --name-only <base>..<branch>` does — and `git show
  --name-only`, which used to be named here, does not: it sees one commit, and a branch-mode run makes
  two.

Only after that coverage check passes are the older branch-mode preconditions worth running — they
are necessary, they were never sufficient:

```bash
git -C "$REPO_ROOT" log --oneline "$BASE_BRANCH".."$branch_name"
git -C "$REPO_ROOT" status --porcelain -uall --ignored=traditional
git -C "$REPO_ROOT" rev-parse "$BASE_BRANCH"      # must equal manifest.base_commit
```

- **fail, empty log** — the artifacts are uncommitted in the working tree and `git branch -D` will
  remove nothing. Go back and commit them (SKILL.md phase 7 step 4). If the user has said not to
  commit, then the mode is not `branch`: set `manifest.mode` to `stage-only` and emit that block.
- **non-empty status** — something the run wrote is loose. Use `--ignored=traditional`, not the
  default and not `--ignored=matching`: plain status hides ignored files entirely, and `matching`
  collapses them to one `!! .claude/` directory line. `traditional` with `-uall` lists them one per
  path, which is what you can compare against the manifest. Every `!!` line must be an artifact whose
  `ignored` is true and which step 2 names; every other loose entry is a miss. `plan.md`, `report.md`
  and `build-manifest.json` are the usual three. This line is a sanity check on the tree, not the
  coverage proof — the enumeration above is the proof.
- **base tip moved** — a base branch whose tip no longer equals `manifest.base_commit` means the run
  committed to it. That is a PRD §13 violation, not a reporting problem. Stop and tell the user.

### 10.3 Stage-only and no-git: every step has to name something real

For each manifest artifact:

- `action: created` — the path exists, and in stage-only mode `git status --porcelain` shows it as
  added **unless its `ignored` is true**, in which case git will never show it and never staged it.
  A created path git does not know about is normal in a `no-git` run, normal for an ignored path,
  and a bug in a stage-only one that is neither.
- **`ignored: true` changes step 1 of the §3.1 stage-only block, not just step 2.** `git restore
  --staged -- <path git never staged>` answers `error: pathspec '…' did not match any file(s) known
  to git`, exits 1, and unstages **nothing** — so one ignored path in that list silently defeats the
  unstage for every other path with it. Confirm step 1 lists `manifest.committed_paths` only, and
  that `manifest.uncommitted_paths` reach the undo through `rm -f` (step 2), the marker script or
  the JSON un-merge script, never through step 1 or step 4.
- `action: modified`, **a marked text file** — the file exists, holds exactly one
  `agentify:begin`/`agentify:end` pair for its `id` (the static pass's `markers` row already told
  you), and carries both `pre_existing_sha256` and `restore`.
- `action: modified`, **a JSON config** (`type: settings` or `type: mcp` in a `.json` file) — it has **no markers and
  must not be checked for any**; the static pass exempts JSON from `markers` for the same reason
  (§2's check table says so in the row). What to confirm instead: the file parses as JSON, it
  carries `pre_existing_sha256` and `restore`, and the entries this run merged in are findable by
  the identity the un-merge script keys on — each hook's manifest `command` under
  `hooks.<Event>[].hooks[].command`, each server name under `mcpServers`, and, in `.mcp.json` only,
  an `_agentify` object whose `agentify-id` matches. Neither hook registry carries an `_agentify`:
  `templates/settings-hooks.json.tmpl` step 6 forbids merging that key into `settings.json`, and
  `.codex/hooks.json` accepts **only** `description` and `hooks` — an `_agentify` beside them makes
  Codex reject the file and load zero hooks. So on both targets the command path is the whole of
  agentify's mark on that file. Reading `restore: span` here as "the marker script handles it" is
  the axios defect (§10.1).
- `restore: head` — git can actually produce the pre-run bytes:
  ```bash
  git -C "$REPO_ROOT" show "$BASE_COMMIT:MODIFIED_PATH" | shasum -a 256
  ```
  It must equal that entry's `pre_existing_sha256`. If it does not, the file was not what the
  manifest claims: downgrade the entry to `restore: span` and re-emit the section.
- `restore: span` — `pre_existing_sha256` is present and non-empty. Without it the §3.1 script
  cannot tell a byte-exact restore from a lucky one and will warn on every file.

`report.md` is the one artifact whose `artifacts[]` entry the manifest cannot have yet — §9 adds it
at step 6, after this check and after the report is written. **Its path is a different matter and is
already here:** §9 step 4a put it in `committed_paths` or `uncommitted_paths` before this check ran,
so the enumeration above and every count the report prints include it. Check the path here even
though no entry claims it yet. In branch mode SKILL.md phase 8 step 5 commits it to the branch and
the delete takes it; in the other two modes it has to be in `CREATED_PATHS` by hand or it is
stranded.

Then check `created_dirs`: every entry exists, resolves inside the repo, is listed deepest-first,
and was genuinely brought into existence by this run. The static pass's `undo_created_dirs` row
covers the first three mechanically — repo-relative, on disk, no parent listed before a directory
it contains — so read it rather than re-deriving them. The fourth is yours and it is the one that
matters: **a directory that existed before the run must never appear there**, and nothing in the
manifest can tell the checker that. `.claude/` on a repo that already had a `.claude/` is the one
to get wrong, and the cost is an `rmdir` in the undo that deletes a directory the user had.

### 10.4 The end-to-end rehearsal

The only way to know an undo works is to run it — **the text that will ship, in the order it will
ship, out of the file it will ship in.** Run it on a copy, never on the user's tree. It is
**mandatory**, not a tie-breaker, whenever any of these is true:

- **`manifest.mode` is `stage-only` or `no-git`** — block D deletes `PLAN_DIR/report.md`, so the undo
  removes the file its own steps are printed in and the order of the blocks is load-bearing;
- **`manifest.uncommitted_paths` is non-empty** — the undo has two mechanisms and §10.2 only proved
  each path is *named* by one; the rehearsal is what proves the naming was right;
- this run appended to a file that existed before it, because that is the case no file deletion
  reverses;
- **this run merged into a JSON config** — `.claude/settings.json` or `.codex/hooks.json` for any
  hook, `.mcp.json` for any server. The file carries no marker, so every list-based check passes
  while the undo removes nothing, and only a byte diff says so. On either target it is not an edge
  case;
- anything in §10.2 or §10.3 was uncertain.

Otherwise run it anyway when you can afford the copy. It is the only check that cannot pass for the
wrong reason.

#### It has to be executable, and it was not

This section used to say: rehearse **before** `report.md` is written, running "verbatim, the same
text the report will carry". Those two clauses cannot both hold. The blocks name
`PLAN_DIR/report.md` — block A copies it, block D deletes it — and the marker and un-merge scripts
are printed *inside* it. Before the report exists there is nothing at that path, so the rehearsal ran
a text that was not the shipped one: block A's `cp` had nothing to copy, block D's `rm -f` was
rehearsed without the one path most likely to be left behind, and the harness held every block in its
own hands, so a block that deletes a later block's input could not fail. **That is how a
self-destroying removal block passed §10 and reached a real run.** A rehearsal that quietly tests
something other than what ships is worse than no rehearsal: it is the sentence in the report that
tells the user the undo was proved.

Two changes make it real, and neither needs the report's prose:

1. **Render the removal section first.** Every value in `report-template.md` §3.1 comes out of
   `build-manifest.json`, so blocks A, B, C and D can be rendered before a word of prose is written.
   Render them into `$REHEARSE/removal.md`, in printed order, in ```bash fences — the same fences
   the report will use, because the harness below finds blocks by them.
2. **Give the rehearsal copy a `report.md` at the real path**, holding exactly that text, *before*
   you take `built.txt`. It is a stand-in for a file that does not exist yet: same path, same blocks,
   same fences. Now `cp` has something to copy, `rm -f` has its true operand list, and the reader
   model below has a file to read each block out of.

#### The copy, the stand-in, and the expected tree

```bash
REHEARSE="$(mktemp -d)"
cp -R "$REPO_ROOT" "$REHEARSE/tree"          # .git comes with it, so branch mode works here
HOME_REAL="$HOME"; export HOME="$REHEARSE/home"; mkdir -p "$HOME"
# block A saves the report to ~ ; the rehearsal must not write into the user's real home,
# and pointing HOME at the copy is also what proves that step actually wrote something.

# >>> Render report-template.md §3.1's blocks A, B, C and D from build-manifest.json into
#     "$REHEARSE/removal.md" now, in printed order, each one inside a ```bash fence.
#     That is a step you take, not a command this block runs, and it has to happen here:
#     $REHEARSE did not exist a line ago and the stand-in below is copied from it. <<<

mkdir -p "$REHEARSE/tree/PLAN_DIR"
cp "$REHEARSE/removal.md" "$REHEARSE/tree/PLAN_DIR/report.md"     # the stand-in, at the real path

listing() { ( cd "$1" && { find . -path ./.git -prune -o -type d -print | sed 's|^|DIR  |'
                           find . -path ./.git -prune -o -type f -print0 \
                             | xargs -0 shasum -a 256 2>/dev/null | sed 's|^|FILE |'; } \
                         | LC_ALL=C sort ); }

listing "$REHEARSE/tree" > "$REHEARSE/built.txt"
```

Now write down what the undo is supposed to produce. You do not need the old tree to do it — every
value is in the manifest. Take `built.txt` and, from it, derive `expected.txt`.

**`listing()` emits two kinds of line and they are not interchangeable.** A directory is one
`DIR␣␣./<path>` line; a file is one `FILE␣<64-hex>␣␣./<path>` line, the hash and the path separated
by the two spaces `shasum` prints. An artifact's own path is always on a **`FILE`** line — a
`.claude/settings.json` artifact produces `FILE <hash>  ./.claude/settings.json`, and the
`DIR  ./.claude` line that also mentions it is its *parent directory*, which rule 2 owns and no
other rule may touch. Match on the whole `./<path>` field, never on a substring.

1. **Drop the `FILE` line** of every artifact with `action: created` — **including the stand-in
   `PLAN_DIR/report.md`**, which is in `CREATED_PATHS` for the same reason the real one is, and
   including a JSON config agentify created, which the un-merge script deletes on a rehearsal copy
   because nothing but agentify's entries is in it. (On the user's real tree that same file survives
   if they have since added keys of their own. The rehearsal runs on an untouched copy, so `created`
   means deleted here.)
2. **Drop the `DIR` line** of every `created_dirs` entry, matching the whole line.
3. **Rewrite the hash field of the `FILE` line** of every artifact with `action: modified` to that
   entry's `pre_existing_sha256`, leaving the `./<path>` field exactly as it is and editing no `DIR`
   line — for a merged JSON config exactly as for a marked text file. Both scripts claim to
   reproduce the pre-run bytes, and this is where that claim is tested rather than believed.
4. **Change nothing else.** Every other line of `built.txt` is a file the undo must leave alone, and
   a line you "tidy" is an assertion you have quietly dropped.

**`pre_existing_sha256` is the only source for rule 3's hash and there is no fallback — least of all
git.** The build records it from the file's bytes *before* agentify touched them, so a file git never
tracked carries one exactly as a tracked one does. Never substitute `git show BASE_COMMIT:<path>` for
a `restore: span` entry: `span` means precisely that git has no clean pre-run copy — the file was
untracked, or gitignored, or already dirty when the user waived the clean-tree gate, or there is no
repo — so git's blob is either absent (`fatal: path … does not exist`, exit 128) or is bytes that
were never the pre-run file. Substituting it turns rule 3 into a test that the undo produced
something other than what it should have. If an `action: modified` entry has an empty or missing
`pre_existing_sha256`, **stop and fix the manifest before rehearsing**: the static pass has already
warned on that entry (§2, `uninstall`), and the hash cannot be recovered here, because every copy of
that file — the tree, the rehearsal copy, `built.txt` — already has agentify's contribution in it.
A rehearsal run without it cannot state result 4 for that path and must not report a byte-exact
restore for it.

Mechanically, on the copy:

```bash
python3 - "$REHEARSE/built.txt" "$REHEARSE/tree/PLAN_DIR/build-manifest.json" \
         > "$REHEARSE/expected.txt" <<'PY'
import json, sys
built, manifest = sys.argv[1], sys.argv[2]
m = json.load(open(manifest, encoding="utf-8"))
created, modified = set(), {}
for a in m.get("artifacts", []):
    path = "./" + a["path"]
    if a.get("action") == "created":
        created.add(path)                                   # rule 1
    elif a.get("action") == "modified":
        want = (a.get("pre_existing_sha256") or "").strip().lower()
        if len(want) != 64:
            sys.exit("STOP %s: action modified with no pre_existing_sha256. Record it at "
                     "build time -- it cannot be recovered here, and git has no clean "
                     "pre-run copy of a `restore: span` file." % a["path"])
        modified[path] = want                               # rule 3
# report.md is a created path before it is an artifacts[] entry (see 9 step 4a),
# so the stand-in is dropped by name whether or not the manifest lists it yet.
created.add("./" + m.get("plan_dir", "docs/agentic-setup").rstrip("/") + "/report.md")
dirs = set("./" + d for d in (m.get("created_dirs") or []))  # rule 2

out = []
for line in open(built, encoding="utf-8"):
    line = line.rstrip("\n")
    if line.startswith("DIR "):
        if line[4:].strip() not in dirs:
            out.append(line)
    elif line.startswith("FILE "):
        sha, _sep, path = line[5:].partition("  ")
        if path in created:
            continue
        out.append("FILE %s  %s" % (modified.get(path, sha), path))
    else:
        out.append(line)                                     # rule 4
# RE-SORT. `listing()` sorts whole lines, so the sort key of a FILE line starts
# with its HASH -- and rule 3 rewrites exactly that field.  Emitting the lines in
# `built.txt`'s order therefore leaves every `action: modified` line filed under
# its POST-build hash while `after.txt` files it under the restored one, and
# `diff` reports each of them twice, as one deletion and one addition carrying
# identical text.  Measured on the 2026-09-05 Codex dogfood: a byte-exact undo
# produced a four-line diff naming `AGENTS.md` and `.codex/hooks.json`, both with
# the correct restored hashes.  Result 4 is a set comparison, so sort both sides.
print("\n".join(sorted(out)))
PY
```

It prints `STOP …` and writes an empty `expected.txt` rather than a wrong one; a path whose name
contains two consecutive spaces breaks `shasum`'s own field separator and has to be checked by hand.

**The `sorted()` is the whole of the fix, and it belongs here rather than at the `diff`.**
`listing()` already ends in `LC_ALL=C sort`, so `built.txt` and `after.txt` are both sorted; only
`expected.txt` is not, because rule 3 edits lines after that sort. Re-sorting the generator's own
output puts all three in one order. Python's `sorted()` compares code points, which is what
`LC_ALL=C sort` does — do not "improve" either side to a locale-aware sort, or they stop agreeing.

#### Run it the way a human runs it — one block at a time, re-read from the file

Do **not** concatenate the blocks into one script and run that. A single script holds all the text
before the first command runs, so the one failure this harness exists to catch — a step that deletes
a later step's input — cannot happen in it. Model the reader instead: before each block, find the
file that block is printed in, *as it is on disk right now*, and take the block out of it.

```bash
n=1; rc=0
while :; do
  src="$REHEARSE/tree/PLAN_DIR/report.md"
  [ -f "$src" ] || src="$HOME/agentify-removal-steps.md"   # only because block A's step 1 named it
  if [ ! -f "$src" ]; then
    echo "FAIL block $n: its instructions no longer exist -- an earlier step deleted them"; rc=1; break
  fi
  python3 - "$src" "$n" > "$REHEARSE/block.$n.sh" <<'PY' || { echo "ran $((n-1)) blocks"; break; }
import re, sys
b = re.findall(r"```bash\n(.*?)```", open(sys.argv[1], encoding="utf-8").read(), re.S)
n = int(sys.argv[2])
if n > len(b): sys.exit(3)
sys.stdout.write(b[n-1])
PY
  echo "block $n  <- $src"
  ( cd "$REHEARSE/tree" && bash "$REHEARSE/block.$n.sh" ) > "$REHEARSE/out.$n" 2>&1; e=$?
  cat "$REHEARSE/out.$n"; echo "block $n exit=$e"
  [ "$e" -eq 0 ] || rc=1
  n=$((n+1))
done

listing "$REHEARSE/tree" > "$REHEARSE/after.txt"
diff "$REHEARSE/expected.txt" "$REHEARSE/after.txt"      # must print nothing
grep -nE 'SKIP|FAIL|STOP|Directory not empty|did not match any file' "$REHEARSE"/out.*   # must print nothing
grep -h 'restored byte-for-byte' "$REHEARSE"/out.* | sort   # one line per script that had work to do
export HOME="$HOME_REAL"
```

**Five results, and all five must hold. Any one of them failing fails the rehearsal.**

1. **Every block was reachable** — no `FAIL block n: its instructions no longer exist`. This is the
   check that catches an undo which is correct as a *set* of steps and wrong as a *sequence*.
2. **Every block exited 0** (`rc` is 0).
3. **No block printed `SKIP`, `FAIL`, `STOP`, `Directory not empty`, or
   `did not match any file(s) known to git`.** A command can exit 0 and still have done nothing: the
   marker script's `SKIP` and the un-merge script's `FAIL … the undo did NOT complete` are the two
   that matter most, and `rmdir`'s `Directory not empty` is how an out-of-order `rmdir` announces
   itself while the step around it succeeds.
4. **`diff expected.txt after.txt` is empty.** A `FILE` line that differs is a file the undo does not
   restore; a `FILE` line only in `after.txt` is one it does not delete; a `DIR` line only in
   `after.txt` is an empty directory left behind.
5. **Every block that was rendered actually did its work.** The last `grep` must print one
   `restored byte-for-byte` line for **each** script the run rendered — one naming the marked text
   file if block B was rendered, one naming the JSON config if block C was. A rendered script that
   printed nothing at all is a step that was reached, exited 0, and did nothing, which 1–4 cannot
   tell from a step that had nothing to do. Count the lines against the blocks; do not assume the
   blocks that were rendered were the blocks that ran.

1–3 detect a step that **could not run**; 4 detects a step that ran and did the wrong thing; 5
detects a step that ran on nothing. **Only 4
was checked before, and 4 alone is not enough** — measured on the fixture below, the pre-fix
stage-only block, concatenated into one script, came back with a single `DIR ./.claude` line and a
completely **empty** `git status --porcelain -uall --ignored=traditional` diff, so `REMOVAL_VERIFY_
SENTENCE`'s check (a) passed on a tree that was not the pre-run tree. The same text, read block by
block from the file, failed at block 2 with `.claude/settings.json` still registering agentify's
hook, `AGENTS.md` still carrying its appended block and `.mcp.json` still holding the merged server.
Same text, same fixture, opposite verdicts: the harness was the variable.

#### The shipped text has to be the rehearsed text

The rehearsal proves something about `$REHEARSE/removal.md`. Nothing so far ties that to the file the
user will read. After `report.md` is written (§9 step 5), compare the two:

```bash
python3 - "$REPO_ROOT/PLAN_DIR/report.md" "$REHEARSE/removal.md" <<'PY'
import re, sys
blocks = lambda p: re.findall(r"```bash\n(.*?)```", open(p, encoding="utf-8").read(), re.S)
a, b = blocks(sys.argv[1]), blocks(sys.argv[2])
print("MATCH" if a == b else "MISMATCH: shipped %d blocks, rehearsed %d" % (len(a), len(b)))
sys.exit(0 if a == b else 1)
PY
rm -rf "$REHEARSE"        # only after MATCH
```

`MISMATCH` means the rehearsal proved nothing about what ships — a re-rendered block, a hand-edit, a
reordering while writing the prose. Fix the report to carry the rehearsed text, or re-render and
re-rehearse. **This is the one part of §10 that runs after §9 step 5**, because it is the only part
that needs the finished file; §10's verdict is not final until it passes, and `$REHEARSE` stays on
disk until then.

#### What this rehearsal proves, and what it cannot

It **proves**, for the tree as the build left it:

- the rendered blocks, run top to bottom in printed order by a reader who re-reads each block from
  the file it is printed in, return that tree to its pre-run bytes;
- every block was still reachable when its turn came;
- every command exited 0 and no script silently no-opped;
- the section the report ships is the text that was rehearsed.

It **cannot prove**:

- **anything about the user's tree at the moment they actually run the undo.** The copy is untouched
  since the build. A created JSON config they have since added keys to is *kept* on their tree and
  *deleted* here; a file they have edited since takes the marker script's `WARNING … only the
  agentify block was removed` path, which the rehearsal never exercises. Both are correct behaviours
  and neither is tested here.
- **that a step is safe on a dirty tree.** `git restore --source=… --worktree` overwrites uncommitted
  changes to the paths it names; the rehearsal copy has none.
- **anything outside the tree** — the `~` copy (rehearsed under a temporary `HOME`), a pushed branch
  (`git push origin --delete BRANCH_NAME`), the user's terminal or clipboard.
- **that the report's prose is right.** It reads the fenced blocks, not the sentences around them;
  the counts in `REMOVAL_MODE_SENTENCE` and the mechanism named in each `MODIFIED_RESTORE_SENTENCE`
  row are §10.2's job, not this one's.
- **anything about a user who runs only some of the blocks.** Every result above assumes all of them,
  in order.

`listing()` hashes ignored files like any other — `find` does not consult `.gitignore` — which is
exactly why the rehearsal catches what `git status` misses. Do not "improve" it into a
`git ls-files` walk.

#### The shape this rehearsal exists to cover

A rehearsal on a repo where every artifact path is committable proves only the easy half. **The
release check for §10 runs on a repo with at least one gitignored artifact path and at least one
that is not**, because a single-mechanism undo passes the first shape and fails the second. Clone
anything with `.claude/` in its `.gitignore` (`vercel/turborepo`), or add the line to a clone, then
build a mixed set: some artifacts under the ignored prefix, `plan.md` and the manifest outside it,
one pre-existing tracked file appended to, one pre-existing **untracked or ignored** file appended
to, one pre-existing **JSON config merged into**, and one **JSON config this run created inside a
directory this run created** — `.claude/settings.json` in a `.claude/` that did not exist before.

The last three are the sharp ones and they fail differently. An ignored file the run appended to is
`restore: span` *and* invisible to `git status` *and* untouched by the branch delete; nothing removes
its block except the marker script. The merged JSON config is `restore: span` in exactly the same way
and **the marker script does nothing to it at all** — it holds no marker and can hold none, so the
script prints `SKIP`, exits 0, and every list-based check still passes. The created config inside a
created directory is the **ordering** case: it is the un-merge script that deletes it, so a `rmdir`
printed before that script finds the directory non-empty, and the only trace is one `DIR` line in the
diff. Coverage catches the first, the byte diff catches the second, and only running the blocks in
printed order catches the third.

**The release fixture must render AND run both scripts — block B and block C — and result 5 above is
where you prove it.** They are the two halves of the format axis and they are independent: a fixture
whose only `restore: span` file is the JSON config renders block C and never block B, and a fixture
whose only one is a marked text file renders block B and never block C. Either way half the axis goes
untested while every other result still comes back green, because a block that was never rendered
cannot fail. Measured: two consecutive release runs proved only the un-merge half — neither fixture
produced a marked text file that needed the marker script, so block B was never exercised in the
order the fix had just changed. **So the fixture is not valid unless the rendered
`$REHEARSE/removal.md` contains at least one `BLOCKS` entry and at least one `UNMERGE` entry**, and
unless the run's output names both files. Check it before running, not after:

```bash
grep -c '^ *("' "$REHEARSE/removal.md"          # >= 2, one BLOCKS entry and one UNMERGE entry
grep -n 'BLOCKS = \[\|UNMERGE = \[' "$REHEARSE/removal.md"   # both must be there, BLOCKS first
```

The order matters as much as the presence: `BLOCKS` before `UNMERGE`, both above the closing block.
`verify_artifacts.py`'s `uninstall` check asserts that statically (§2, **Order**), and this fixture is
what proves the static assertion describes something real.

Measured on that fixture, 9 artifacts, 5 under an ignored `.claude/`:

```
[build] gitignored artifact paths: 5 of 9
        .claude/rules/no-npm.md                  <- .gitignore:6:.claude/
        .claude/settings.json                    <- .gitignore:6:.claude/   (pre-existing, MERGED into: JSON, no marker)
[build] commit holds 4 paths; 5 left uncommitted because .gitignore excludes them
```

With the single-mechanism branch undo, all three §10.2 preconditions as they were previously written
passed and the diff came back with seven lines — two `DIR`, four `FILE` only in `after.txt`, and one
`FILE` whose hash differed (`.claude/settings.json`, still carrying its appended block). With the
two-mechanism undo generated from the same manifest, `diff expected.txt after.txt` and
`diff pristine.txt after.txt` were both empty, in `branch` mode and in `stage-only` mode.

Run the same fixture a second time **with the `.claude/` line removed from `.gitignore`** and keep
the untracked `settings.json`. Nothing is ignored now, so a naive fix that keys only on `ignored`
puts every path on the branch — and the rehearsal catches the §10.1 row-2 failure instead: the
branch delete removed the user's hand-written `settings.json` and its directory outright, `expected`
and `after` differing on two `DIR` lines and one `FILE`. Keying on `committed_paths` instead, both
diffs came back empty in both modes.

Run it a **third** time with the format axis isolated, because the two runs above both pass with a
marker-only undo. Measured on a standalone fixture while writing this section, a pre-existing
`.claude/settings.json` holding the user's `permissions`, `model`, `env`, a `PreToolUse`/`Bash`
group and a `Stop` group, with agentify's `enforce-bun` command merged into that same `Bash` group:

```
# the marker script — the shipped defect
SKIP  .claude/settings.json: no agentify block id=enforce-bun (already removed by hand?)
exit 0 · file byte-identical before and after · enforce-bun still registered

# the JSON un-merge script — same fixture, same manifest entry
.claude/settings.json: 1 entry(s) removed, restored byte-for-byte (id=enforce-bun)
diff pristine.json .claude/settings.json   -> empty
shasum -a 256: 524322f4d9d26d87138851d6ea8262f6b7ad9cd24035144f29969a0ff86932bd  (both)
the user's audit-bash.sh, user-format-guard.sh and notify.sh hooks all still present
```

And on a second fixture where agentify **created** `.claude/settings.json`:
`deleted (agentify created it and it now holds nothing else)`, then `rm -f` the hook script and
`rmdir` the two created directories, and `diff -r pre-run/ post-undo/` came back empty. A third
where the user had since added `"model": "opus"` to that created file: `1 entry(s) removed`, the
file kept, `{"model": "opus"}` left in it — which a blind `rm -f` would have destroyed. Run twice,
the un-merge prints `FAIL … the undo did NOT complete` rather than a reassuring `SKIP`.

Run it a **fourth** time with the **ordering** axis isolated, on the fixture this harness was
written against: a stage-only run whose created set is `.claude/settings.json` (a JSON config, in a
`.claude/` this run created), `.claude/rules/no-npm.md`, `.claude/hooks/enforce-bun.sh` and
`docs/agentic-setup/{plan.md,build-manifest.json,report.md}`; whose modified set is a tracked
`CLAUDE.md` (`restore: head`), an untracked `AGENTS.md` (`span`, marked) and an untracked `.mcp.json`
(`span`, merged); run once with `.claude/` in `.gitignore` and once without. With the blocks in the
order §3.1 now prints them, both harnesses — one concatenated paste and the block-by-block reader —
came back with an empty `diff baseline.txt after.txt`, an empty
`git status --porcelain -uall --ignored=traditional` diff, and a directory listing identical to the
pre-run one, in both `.gitignore` shapes. With the pre-fix order, the concatenated paste left
`DIR ./.claude` behind while `git status` stayed empty, and the block-by-block reader failed at
block 2 with three files still changed. **Same manifest, same text, same fixture — the only variable
was the order the steps were printed in.**

Run it a **fifth** time on the same ordering fixture with the blocks emitted as **A, D, B, C** — the
closing block printed ahead of the two scripts. This is the reordering that got past the static check
once, and it is the sharpest of the set because *nothing about coverage changes*: every artifact is
still reachable by exactly the mechanism its format allows, `undo_partition` still passes, and the
`uninstall` row's tally still adds up to every artifact. What breaks is the sequence — the `rmdir`
finds `.claude/` still holding the config block C has not deleted yet, and the `shasum` confirmation
hashes `AGENTS.md` before block B restores it, so the digest disagrees with the `expected:` line
printed beside it. `verify_artifacts.py` now fails this statically (§2, **Order**), and the rehearsal
has to agree with it: result 3's `Directory not empty` and result 4's `DIR ./.claude` must both
appear. If the rehearsal comes back clean on an A, D, B, C block, the fixture is not exercising both
scripts — go back and check the paragraph above.

**A fix verified only on the shape that motivated it is how this bug class keeps returning under a
new name** — and it has now returned five times. Run all four combinations of
(ignored / not ignored) × (`branch` / `stage-only`), **with a merged JSON config, a created JSON
config, and a marked text file in the artifact set** so blocks B and C both render, and **with the
block-by-block harness**, because the ignored axis, the format axis and the ordering axis are
independent and the one that has shipped a defect is never the one you will remember to test.

### 10.5 Recording it

**The row is emitted by the static pass. You do not write it.** `verify_artifacts.py` runs this
whole section's manifest half as the `uninstall` check (§2) and produces the row itself: `target` is
`the run`, `status` is the verdict, and `detail` is a generated tally naming every mechanism that was
used and adding up to every artifact in the manifest. Copy that row into the report's verification
table exactly as it comes out, the same as every other row.

Measured, on a branch-mode fixture of the shape §10.4 calls for — a `.gitignore` holding `.claude/`,
seven artifacts, all four mechanisms in play, one pre-existing tracked file appended to, one
pre-existing ignored file appended to and one pre-existing `settings.json` merged into:

| Artifact | Check | Result | Detail |
|---|---|---|---|
| the run | `uninstall` | pass | `branch mode: 7 artifact(s) -- 3 by the branch delete, 2 by rm, 1 by the marker script (.claude/rules/existing-conventions.md), 1 by the JSON un-merge (.claude/settings.json); 3 created dir(s) by rmdir; branch holds 3/4 committed_paths (+1 by phase 8); report.md: 7 step(s), order consistent` |
| the run | `uninstall` | fail | `2 committed_paths entry(s) are NOT on \`agentic-setup/2026-09-05\` (git diff --name-only 01e6301..agentic-setup/2026-09-05): CLAUDE.md, docs/agentic-setup/plan.md. \`git branch -D\` prints \`Deleted branch\` and leaves them on disk` |
| `.claude/settings.json` | `uninstall` | fail | `the removal block hands this JSON config to the MARKER script, which finds no \`agentify:begin\` in a file that can never hold one, prints SKIP and exits 0. It belongs in the un-merge script's UNMERGE list (the axios defect)` |

**Never hand-author an `uninstall` row, and never paraphrase one.** The whole reason this check
exists in code is that the row used to be the model's own summary of its own work: the product's
central safety claim resting on self-report, in a table of rows that were all machine-generated and
looked identical. A hand-written `pass` here is indistinguishable from a real one and is worth
nothing. If the check did not run, the report says the static pass was unavailable — it does not get
an `uninstall` row at all.

**The check runs twice, and the second run is the complete one.** §9 step 1's pass happens before
`report.md` exists, so the half of the check that reads the *rendered* removal block has nothing to
read; its detail ends `report.md: not written yet, so the rendered removal block was not read`, and
that is correct rather than degraded. §9 step 6's re-run, after the report is written, is the first
one that sees the block, and it is the only one that can catch a routing or ordering defect in the
text the user will paste. If that run's `uninstall` row is not clean, §9 step 6's **not clean**
branch already binds: fix `report.md`, re-run, and replace the row in the table with the one that
passed. Never hand off on the strength of the step-1 row alone.

- **pass** — every artifact is reachable by a mechanism its format allows, the branch holds what
  `committed_paths` claims, and the printed steps survive their own order.
- **warn** — an input could not be **read**: the manifest carries no undo record, or git could not
  enumerate the branch. The row names which. A warn is not a soft fail — nothing was found wrong,
  and nothing was proved either, so say in the report which half went unchecked.
- **fail** — do not write the removal section as though it works, and do not quietly drop the
  section. Fix the build first. A wrong undo is worse than no undo: the user runs it, reads
  `Deleted branch`, believes the repo is clean, and finds the files weeks later with nothing to
  tell them what wrote them.

**The check does not replace §10.4.** It reads the manifest, the branch and the text of the removal
block; only the rehearsal compares **bytes**, and a mechanism that is correctly routed can still be
wrong about what it writes back. `uninstall` failing means stop. `uninstall` passing means the
rehearsal is now worth running, not that it can be skipped.
