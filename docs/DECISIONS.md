# Decisions

The annotation layer over `PRD.md`. The PRD says what agentify is; this file says what was
actually decided while building it, why, and what it would cost to decide differently.

**`PRD.md` is not edited by this file.** Where a decision here differs from the PRD, the PRD is
the older document and this entry says so explicitly.

Every entry has the same five parts:

| part | means |
| --- | --- |
| **Question** | the thing that was genuinely open |
| **Default implemented** | what is in the tree today |
| **Why** | the argument, with the evidence it rests on |
| **To change it** | the concrete edit, and what else moves |
| **Status** | `decided` · `provisional` · `needs-user-input` · `needs sign-off` |

`decided` means settled unless new evidence arrives. `provisional` means it works but the
argument against it is live. `needs-user-input` and `needs sign-off` mean **nobody has answered
it yet** — do not read a default as an answer.

Last reconciled against the tree: **2026-09-07, direction round (two passes).** §2.30 records the
second pass: three more questions retired after a real run, each replaced by a derivation the plan
states out loud. §2.22 through §2.29 are from the first pass and
record the product-direction change in `GOAL.md`: no output caps, no audit-only mode, repo scope
only, structural facts as evidence, the index doc built last, permissions in and the plugin manifest
out, no pull requests, and three new interview questions. §2.12's provenance classification stands;
its *consequence* is superseded by §2.22.

Earlier reconciliation, **2026-09-05, closing round.** §2.10 through §2.15 were added in
the final build round; §2.16 through §2.18 in the stale-prose cleanup round — the "can git put this
back" predicate that partitions the build, the qualifier gate on script-name matching and what it
costs, and why `npm ci` is an alternate rather than a command. **§2.19 through §2.21 are new in the
closing round** and record three decisions made in code by other hands and written down nowhere:
format-based undo routing, partial-clone handling, and listing a branch's files with `git diff`
rather than `git show`. §3.1, §3.2 and §4.1 gained an approvable one-liner and the exact edits it
authorises, so a sign-off no longer requires re-deriving the problem — §4.1 also gained the measured
consequence (an `.agents/`-only repo can be proposed a duplicate of a skill it already has) and the
three sites where `discover.py` *already* treats `.agents/` as the team's own. §1.5, §2.6, §2.9,
§3.2 and §4.1 were corrected against shipped behaviour in earlier rounds.

Every claim here was verified by **running** the code — not by reading a `--help`, and not by copying
a number out of the build contract, which has now been stale on selftest counts four times running.
(Re-run in the closing round, 2026-09-05, all seven green and all exiting 0: `discover.py` 49/49,
`mine_transcripts.py` 18/18, `mine_git.py` 26/26, `verify_artifacts.py` **33/33**, `textnorm.py`
101/0, `scrub.py` 58/0, `emit.py` 36/0. The `verify_artifacts.py` figure was recorded here as 24/24
for two rounds after `hook_wired`, `undo_partition` and `undo_created_dirs` landed — the same stale
number the build contract carried. Do not cite these seven as stable: cite the exit code.)

---

## Part 1 — PRD §16 open questions

### 1.1 The name "agentify"

- **Question.** PRD §16.1: "Check availability of `agentify` on npm and GitHub."
- **Default implemented.** The name is used everywhere: the skill directory
  `skills/agentify/`, the frontmatter `name: agentify`, the plugin and marketplace manifests,
  every generated file's `agentify-id` / `agentify-version` / `agentify-generated` /
  `agentify-evidence` frontmatter key, the `agentify:begin` / `agentify:end` marker convention
  that idempotent reruns depend on, and the `has_agentify_section` flag in `discovery.json`.
- **Why.** It had to be called something to build it, and a placeholder name would have
  contaminated the same set of files.
- **Status: `needs-user-input`.**

  **The check has now been run, and the name is taken on both registries.** npm has `agentify`
  — v0.0.1, published by `unadlib` on 2024-06-09 — and GitHub has an active organisation in the
  same niche, `agentify-sh`. This entry previously said nobody had checked; that was true when it
  was written and is no longer. `README.md`'s status banner has been corrected to state the
  measured fact rather than the absence of a check.

  What is still open is **the rename, not the availability** — that is the user's call, and
  nothing in this repo may make it for them. The finding narrows the options rather than deciding
  between them: publish under a scoped npm name (`@<org>/agentify`) and a GitHub repo whose
  *org* disambiguates it, or pick a different name. Both are live; both are one line to answer.

  The check itself requires network access, which the analyzer scripts are forbidden to have
  (PRD §13). It stays a human step, or one the user runs in a shell — never something agentify
  does for itself. Re-run it before publishing: a registry lookup is a fact with a date on it,
  and this one is dated 2026-09-05.

- **To change it.** A rename is mechanical but wide, and it is the single most expensive thing
  in this file to defer past first publish:
  - Directory `skills/agentify/`, and the `name:` in `SKILL.md` frontmatter.
  - The four `agentify-*` frontmatter keys, in the templates that emit them
    (`templates/*.tmpl`) and in `verify_artifacts.py`'s `REQUIRED_META`.
  - The `agentify:begin` / `agentify:end` marker parser in `verify_artifacts.py` and the
    `AGENTIFY_MARKER` constant in `discover.py`.
  - `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `README.md`,
    `test-repos.md`, the three reference templates, and both adapters.
  - **The migration cost that matters:** every setup already built by a previous version carries
    the old marker pair and the old id keys in the user's repo. A rename after release either
    orphans those (a rerun stops recognising its own output and duplicates it, breaking the
    idempotence invariant) or needs a compatibility path that reads both spellings. **Rename
    before first publish, or accept dual-marker support forever.**

### 1.2 Where the plan and report live

- **Question.** PRD §16.2: `docs/agentic-setup/` or `.claude/`? Visible docs favour adoption;
  hidden directories favour tidiness.
- **Default implemented.** `docs/agentic-setup/` — holding `plan.md`, `report.md`, and
  `build-manifest.json`. Switchable in the phase 5 interview to `.claude/agentic-setup/`.
- **Why.** The plan is the phase 6 hard gate: the artifact a human has to read and approve
  before a single file is generated. A gate nobody can find is not a gate. `docs/` is where a
  developer looks for a document, gets a rendered diff in a PR, and can hand the plan to a
  teammate. `.claude/` is where tooling looks — burying the one human-facing output of the run
  in the tool's own config directory optimises for tidiness at the cost of the mechanism the
  whole design rests on.

  Making it an interview option rather than a hard default costs one question and settles the
  argument per-repo, which is where it actually belongs: a repo with no `docs/` directory and a
  strong "no new top-level dirs" convention is a real case.
- **To change the default.** One line in `references/interview.md` (the marked default), the
  paths quoted in `SKILL.md` phases 6, 7 and 8, and the example path in `verify_artifacts.py`'s
  docstring. Nothing in the analyzers reads either path — `--manifest` takes whatever it is
  given, and accepts `-` for stdin — so the switch is genuinely cheap. Keep it cheap: no script
  should ever hardcode the plan directory.
- **Status: `decided`.**

### 1.3 Minimum model class — enforce or warn

- **Question.** PRD §16.3.
- **Default implemented.** **Warn, never enforce.** `SKILL.md` phase 0 step 4: a small or
  fast-tier model warns once that plan quality will be lower and that the phase 6 gate is the
  user's catch, then proceeds. It does not refuse.
- **Why.** Three reasons, in order of weight:
  1. **The gate already is the safety mechanism.** A weak model produces a weak plan, and a
     weak plan is visible in `plan.md` before anything is built. The failure mode is a bad
     proposal the user rejects — not a damaged repo. Enforcement would be guarding a door that
     is already locked.
  2. **Self-identification is unreliable.** A model asked what class it is answers from its
     prompt, not from a fact. Enforcement built on that gets both false positives (refusing a
     capable model) and false negatives (waving through a weak one), and the false positive is
     a hard refusal on a free tool.
  3. **Model names churn faster than this repo will.** Any hardcoded allowlist is stale within
     months and then refuses models that did not exist when it was written.
- **To change it.** Turn the phase 0 warning into a stop condition and add a "proceed anyway"
  override in the same shape as the dirty-tree override (which does refuse, because a dirty
  tree is a fact the tool can verify, not a self-report). If this is ever done, it must be an
  override and not a wall.
- **Status: `decided`.**

### 1.4 Starter skills for known stacks

- **Question.** PRD §16.4: should the installer also offer to install the agentic
  boilerplate's starter skills for known stacks?
- **Default implemented.** **No.** Nothing ships a stack template, and nothing offers to.
- **Why.** It contradicts the core claim. PRD §3 and `CLAUDE.md` both state that every
  artifact must trace to a concrete signal with a count — "evidence-derived, not templated" is
  the product. A Next.js starter pack installs itself because the repo has Next.js in
  `package.json`, which is a fact about the framework, not evidence that *this developer*
  repeats *this work*. It would produce artifacts indistinguishable in the output from
  evidence-derived ones, which erodes the only thing that distinguishes agentify from a
  scaffolder. `SKILL.md` rule 2 is blunt about it: a candidate with no number from a named JSON
  field is deleted, not softened, and zero artifacts is a valid outcome.
- **To change it.** It would need a fourth artifact source alongside repo, transcript and git
  evidence, and — more importantly — a visible label in `plan.md` and `report.md` separating
  "derived from your history" from "a template we thought fit your stack", so the user can tell
  which is which. Do not add it without that label.
- **Status: `decided`** (as a v1 non-goal; revisit only with the labelling above).

### 1.5 Monorepos

- **Question.** PRD §16.5: one setup at root, or per package?
- **Default implemented.** **Root by default; per-package offered in the interview when
  workspaces are detected.** `discover.py` emits
  `monorepo: {is_monorepo, tool, workspaces[], excludes[], tools[], systems[], task_runners[]}`
  — seven keys, not three: a repo can run more than one workspace system at once (pnpm workspaces
  *and* Turborepo *and* a Makefile), so `tool` is the primary and `tools`/`systems`/`task_runners`
  report everything found, while `excludes` carries the negated workspace globs. The interview
  raises the choice only when `is_monorepo` is true, and its Q10 trigger reads
  `len(workspaces) >= 2`, which is unaffected by the additions.
- **Why.** The index doc (`CLAUDE.md` / `AGENTS.md`) is read from the repo root, and hooks are
  registered once in `.claude/settings.json` at the root — so a root setup is the one that
  always works. Per-package setups multiply the artifact count by the number of packages,
  which collides head-on with the sizing caps (PRD §9): five packages at the "small" cap is 15
  skills, well past the large-repo cap of 10, and the caps exist because fewer sharper
  artifacts get used. Offering the choice only when workspaces are actually detected keeps the
  interview inside its 3–8 question budget on the 90% of repos that are not monorepos.
- **To change it.** `discover.py` already supplies everything needed. The work is in phase 7:
  per-package artifact paths, per-package caps, and a decision about whether hooks stay
  registered once at the root (they must — there is one settings file).
- **Status: `decided`** for v1; the per-package *build* path is thin and untested at scale.

---

## Part 2 — Deviations from the build contract

Each of these is a place where the shipped code differs from the contract as originally
written. The contract has been reconciled to match; these entries record why.

### 2.1 Clustering threshold: exact-skeleton + Jaccard 0.6 → stemmed 3-token key + 0.5 with guards

- **Question.** How near does a near-duplicate prompt have to be before two request shapes are
  one shape?
- **Contract as written.** Exact match on the skeleton, plus a token-Jaccard merge at `>= 0.6`.
- **Default implemented.** Bucket on `shape_key()` — the skeleton run through a conservative
  suffix stemmer and cut to **3** tokens — then merge buckets at Jaccard **`>= 0.5`** behind
  two guards: at least **two** shared tokens, and at least one shared token **outside** the
  low-information set (`fix bug issue add update change make create run …`). Containment (one
  key wholly inside another) also merges. The displayed skeleton is capped at 6 tokens, down
  from 10.
- **Why.** Measured, not argued. The contract rule produced **5 / 2 / 1 / 0 / 0** request
  shapes across five real project histories — one repo reported five shapes from 384 user
  turns, and roughly 72% of prompts landed in a singleton cluster. Phase 4 cannot map that to
  anything, and a run that returns two shapes from a year of history looks broken to the user
  even though the code is doing exactly what it was told.

  The three changes each address a different cause:
  - **10-token skeletons** made the "shape" a near-verbatim bag of content words, so no two
    prompts ever matched exactly. Cutting the *merge key* to 3 tokens (a verb and its object;
    everything after that is *which instance* of the request it was) is what actually
    unfragmented the clusters — on one corpus, 38 shapes covering 142 turns where 10 tokens
    gave singletons.
  - **Stemming** collapses `commit` / `commits` / `committed` / `committing` and
    `remains` / `remaining` onto one bucket. The stemmer is deliberately crude and
    linguistically wrong in places; that is fine, because its output is a hash bucket that is
    never shown — the cluster is labelled with the most frequent *real* skeleton inside it.
  - **0.5 instead of 0.6** because on a 3-token key, 0.6 means two of three shared *and nothing
    else allowed to differ*; one measured repo reported a single shape from 130 turns at that
    setting.

  Loosening a merge threshold is exactly how a clusterer starts lying, so the guards are not
  optional trim — they are the reason 0.5 is safe. Without the two-shared-token guard a
  2-token key merges with a 3-token key on one word and "fix layout" swallows "fix auth".
  Without the low-information guard, "fix auth bug" and "fix layout bug" overlap on
  `{fix, bug}` and collapse into a meaningless "fix bug" cluster — the precise over-merge the
  loosening had to avoid.

- **Evidence.** Re-measured against the shipped code on 2026-09-04 18:40 IST, three real
  Claude Code histories: **19 shapes / 420 turns / 81 sessions**, **16 / 225 / 57**,
  **8 / 138 / 28**. (The 17:26 pass recorded 19/17/8; the middle repo drifted by one shape as
  its history grew. Tens of shapes rather than two is the point, not the exact integer.)
- **To change it.** `SHAPE_KEY_TOKENS` and `MAX_SKELETON_TOKENS` in `lib/textnorm.py`, the
  `jaccard_threshold` passed from `build_request_shapes()` in `mine_transcripts.py`, and
  `_LOW_INFO_KEY_TOKENS`. **Do not tune any of them without re-running the measurement across
  several real histories** — this is the one parameter in the tool where a plausible-looking
  value silently destroys the output, in both directions, and a single test repo will not show
  it.
- **Status: `decided`.**

### 2.2 `discover.py` — `commands.verified` removed

- **Question.** Should `discovery.json` report whether the resolved commands actually run?
- **Default implemented.** **No such key.** `commands` is a fixed map of exactly seven
  slot→string entries (`install`, `dev`, `build`, `test`, `lint`, `typecheck`, `format`), a
  slot with no evidence being `""` and never absent. The caveat ships instead as a `warnings`
  entry on **every** run: *"commands were resolved from manifests, not executed; offer to run
  them only with the user's consent."*
- **Why.** Two independent reasons, either sufficient:
  1. **It would be a lie.** `discover.py` reads manifests and executes nothing. It cannot
     honestly report verification, and a `verified: false` that is *always* false is noise that
     trains readers to ignore the field.
  2. **It breaks the type contract.** Every consumer iterates `commands` as slot→string. A
     boolean member makes `for slot, cmd in commands.items()` produce `("verified", False)`,
     which is a runtime error waiting in phase 3 and phase 7.

  Actually verifying would mean executing the user's build and test commands during a
  read-only analysis phase — a side effect nobody consented to, in a phase whose whole
  contract is that it only reads.
- **To change it.** Do not add it to `commands`. If command verification is ever wanted, it
  belongs in a separate consented step with its own top-level key and its own explicit user
  approval — not as a field on a map that is documented as strings. The code carries a comment
  at the return site saying exactly this.
- **Status: `decided`.**

### 2.3 Transcript resolution — a scored cascade, and siblings deliberately not merged

- **Question.** Claude Code encodes a project directory name from the absolute repo path by
  replacing `/`, `.` and `_` with `-`. That encoding is **lossy**: `a-b`, `a.b`, `a_b` and
  `a/b` all encode to `a-b`. What happens when there is no exact directory hit?
- **Default implemented.** A three-stage cascade returning `(root, match_mode)`:
  1. **exact** — name equals the encoded path. Silent.
  2. **fuzzy** — score every directory, take the best `>= 0.55`, tie-break on transcript bytes
     then name. Warns with the directory name and the confidence, and tells the model to
     confirm with the user before trusting counts.
  3. **basename** — nothing scored; fall back to directories matching the repo's basename,
     largest first, warning that these may be from a different checkout.
  4. **none** — warn, continue with repo-only evidence.

  Codex adds a fifth mode, `cwd`: sessions are matched by the `cwd` recorded in each rollout's
  `session_meta` record, always with a "best-effort" warning.

  **Sibling directories are found and deliberately NOT merged.** Every other *structural*
  candidate — score 0.80 (repo plus extra segments: a session started in a subdirectory), 0.86
  (embedded elsewhere), 0.92 (the encoded path is a suffix: a worktree or scratchpad) — is
  reported in a warning naming up to four of them and saying they were not merged.
- **Why.** Because the encoding is lossy, an exact hit is the only match that can be *fully*
  trusted, and a resolver that silently picks a near-match is inventing evidence. Hence: score,
  use, and report the confidence.

  The sibling decision is the sharper one, and it is a decision rather than a gap. Merging a
  worktree's transcripts silently inflates **every count in the plan** — and counts are the
  entire product. A shape with 11 mentions that is really 6 in this checkout plus 5 in a
  worktree of a different branch is a fabricated justification for an artifact. Only the user
  knows whether a given worktree is the same work, so the tool surfaces the candidates and lets
  them decide. The ordered-token-coverage score is capped at 0.79 and gated on the **last path
  segment agreeing**, because without that guard
  `.../projects/hostshare/ravisojitra` scores 0.67 against `.../projects/riffads` — a
  completely different project.
- **To change it.** The scores and the 0.55 floor are in `_score_candidate()` /
  `locate_claude_root()` in `mine_transcripts.py`. If merging is ever added it must be
  **opt-in, per-directory, and after showing the user the list** — never a default, and never
  a blanket "merge everything structural".
- **Status: `decided`.** Two notes for SKILL.md authors. On a normal run `match_mode` is
  internal — it drives the warnings and is **not** a key in the emitted JSON, so read match
  quality out of `warnings`. And `--resolve-only` (landed 18:45 IST) exists precisely to serve
  this decision: it reports the resolved directory, session count and date range **without
  parsing a single turn**, so phase 0 can show the user which directory would be read — and
  which siblings would *not* be merged — **before** asking for consent. That ordering is the
  point: a consent prompt that cannot name what it is asking about is not informed consent.

### 2.4 Uniform exit codes

- **Question.** How does a script signal a degraded run?
- **Default implemented.** Two values, identically across all four scripts, each stated in its
  own `--help` epilog: **exit 0** for success *and* every degraded run (valid JSON on stdout,
  the loss explained in `warnings`); **exit 1** *only* when no JSON could be produced at all.
  There is no partial-failure code.
- **Why.** SKILL.md branches on this, and a three-value contract means every phase needs a
  three-way branch that will be written inconsistently across eight phases. With two values,
  **exit 0 means "you have a JSON object, read it"** and the happy path never branches at all;
  degradation is data the model reads out of `warnings` and records in the plan, which is where
  it belongs, because the plan is what the user approves. On exit 1 the rule is *still* not to
  abort the phase — drop to reduced evidence, continue, and say so.
- **Exit 2 is reserved and never emitted.** argparse would use it for a usage error, so
  `base_parser()` overrides `ArgumentParser.error` to route usage errors through
  `fail(..., EXIT_NO_OUTPUT)` instead. The reason is the same one: **every** exit from these
  scripts is accompanied by parseable JSON, so a caller never has to distinguish "the tool
  spoke" from "the tool died". Verified on all four with a bogus flag — exit 1, valid JSON.
- **Two exceptions, both outside the analysis contract.** `--help` / `--version` print human
  text and exit 0 (not runs, no JSON). `--selftest` exits 1 when a check fails — the one place
  exit 1 accompanies a well-formed report, because CI has to catch a broken script.
- **Where it is written down.** The normative statement is the `EXIT-CODE CONTRACT` block in
  `lib/emit.py`'s module docstring. The other scripts' docstrings point at it rather than
  restating it, which is the right shape: one copy, and the four scripts share the library that
  enforces it.
- **To change it.** Don't. Adding a third code means touching all four scripts, all four help
  epilogs, and every phase in SKILL.md, to gain a distinction the model can already read out of
  `warnings`.
- **Status: `decided`.** `lib/emit.py`'s own selftest `fail exits 0 for a degraded run` was red
  at 18:40 IST — a defect in `emit.fail()`, not evidence against the rule. Fixed; `emit.py` is
  36 passed / 0 failed at 18:52, and now carries explicit checks that a usage error exits 1
  rather than argparse's 2.

### 2.5 `verify_artifacts.py` emits `timing_ms`

- **Question.** Trivial, but it was wrong in the contract: does the verifier report its own
  runtime?
- **Default implemented.** Yes. `timing_ms` is a top-level key, as on all four scripts. The
  contract's schema line omitted it.
- **Why.** Uniformity. The four payload envelopes differ only in their middles; a consumer
  that reads `timing_ms` from three scripts and crashes on the fourth is a gratuitous special
  case. The code carries a comment at the payload builder forbidding **further** top-level
  keys — per-run context such as the manifest label and artifact count goes through `checks`
  and `warnings`, which SKILL.md already reads.
- **To change it.** Don't add keys. The envelope is `schema_version`, `tool`, the per-tool
  middle, `warnings`, `timing_ms`.
- **Status: `decided`.**

### 2.6 `--selftest` — documented before it existed

- **Question.** Do the four analyzer scripts expose a self-test?
- **What went wrong.** The contract advertised `--selftest` at line 72 as though it shipped. It
  did not — until 18:45 IST every one of the four scripts answered
  `error: unrecognized arguments: --selftest`. The only self-tests that existed were on the
  three shared libs, run by executing the module directly (`python3 lib/scrub.py`,
  `lib/textnorm.py`, `lib/emit.py`).
- **Default implemented now.** `--selftest` landed on all four scripts during this
  reconciliation. It runs the script's internal sanity checks, prints a JSON report in its own
  envelope (`mode: "selftest"`, `checks[]`, `summary {pass, fail}`, `ok`), and exits **0 if
  everything passed, 1 if anything failed** — deliberately narrower than the two-value exit
  contract in §2.4, because this is developer tooling and a red check must fail a shell.
  Verified by running all four at the close of the final build round, all exiting 0:
  `discover.py` **49/49**, `mine_transcripts.py` **18/18**, `mine_git.py` **26/26**,
  `verify_artifacts.py` **33/33** — 24/24 when this entry was first written, and 33/33 since
  `hook_wired`, `undo_partition` and `undo_created_dirs` landed with the undo work; re-measured
  2026-09-05. The three shared libs are green in the same pass:
  `textnorm.py` 101/0, `scrub.py` 58/0, `emit.py` 36/0. It is **not** part of the eight-phase run
  and SKILL.md must not call it.

  **Do not cite these numbers as though they were stable.** They have been recorded three times in
  this file and in the build contract — 10/12/11/12, then 14/16/19/17, then 49/18/26/24, now
  49/18/26/33 — and every set was correct when written and stale within the hour, because every
  repair adds checks. The
  contract is the **exit code**, not the count. `test-repos.md` §1a runs all seven and records
  nothing but pass/fail, deliberately.
- **Why it matters.** SKILL.md quotes the contract's command lines verbatim, so a flag that is
  documented but absent turns a phase into an argparse usage error. That error is survivable here
  only because `base_parser()` overrides `ArgumentParser.error` to route it through
  `fail(..., EXIT_NO_OUTPUT)`: a usage error prints a valid JSON object and exits **1**, never the
  bare exit 2 argparse would otherwise produce. Exit 2 is reserved and is never emitted.
- **Status: `decided`.** `verify_artifacts.py --selftest` briefly shipped broken — `--help`
  claimed `--manifest` was "required unless `--selftest`" while argparse still had
  `required=True`, so the flag hit a usage error and exited 1. Fixed at 18:52; all four now run
  standalone and exit 0.
- **Standing rule this establishes.** The contract documents what *runs*. Anything else is a
  to-do, marked as one — and "documented" means someone executed it, not that someone read the
  `--help` output. Both defects in this entry were found by running the command after reading
  a `--help` that said otherwise. Do that.

### 2.7 Hook execution during verification

- **Question.** Should `verify_artifacts.py` execute the hook scripts it just verified, to
  prove they exit 0 within their timeout?
- **What it was.** Until 18:45 IST execution was **ON by default**: `hook_smoke` ran each hook
  with `{}` on stdin under a 5-second budget, and `--no-exec` was the opt-out.
- **Default implemented now.** **Execution is OFF by default, opt-in behind `--exec-hooks`.**
  The inversion landed during this reconciliation. `--no-exec` is kept as an accepted no-op so
  existing call sites keep working, and it **wins** if both flags are given — the safe value
  wins ties, which is the right way round for a flag that decides whether to run a script.
  `--hook-timeout-s` (alias `--timeout-s`, default 5) still applies when execution is on, and a
  timeout is still a **FAIL**, because a hook that hangs blocks the user on every prompt.
- **Why opt-in.** A hook is a shell script agentify generated minutes earlier. Running it is a
  side effect the user approved the *creation* of at the phase 6 gate, not the *execution* of —
  phase 6 approval is approval of a written plan. A generated hook that touches the working
  tree, writes a file, or calls a slow tool does so on a machine whose owner only agreed to
  have the file written. Opt-in keeps phase 8 as read-only as phases 1–2.
- **What was given up, and how it was bought back.** A hook that fails or hangs is the worst
  artifact agentify can produce — it degrades every subsequent prompt in the user's session,
  and it is exactly the failure a static check cannot catch. Losing that check by default is a
  real cost. It is mitigated by making the opt-in path genuinely safe rather than merely
  available: only a hook **this run generated inside the repo** is ever executed, only after
  its static network scan is clean, and only with an allowlisted environment (`PATH`, `HOME`),
  cwd in a throwaway fixture directory, `shell=False`, and a hard timeout. SKILL.md passes
  `--exec-hooks` only after the user says yes in phase 8. So the check is one question away
  rather than gone — which is the resolution of the tension, not a dodge of it.
- **To change it back.** Flip the default in `verify_artifacts.py`'s argparse block, the
  `--help` epilog, the phase 8 command line in `SKILL.md`, and `references/verification.md`.
  Do not: the sandboxing above only makes sense as the price of an explicit yes.
- **Status: `decided`.** Recorded here because the opposite default shipped first and the
  argument for it (highest-value check in the file) is genuinely good — the next person to
  reopen this should know it was weighed, not overlooked.

### 2.8 Symlinks: never followed in the repo walk, always followed under the agent-config dirs

- **Question.** `discover.py`'s tree walk deliberately never follows symlinks. But teams
  commonly symlink `.claude/skills/<name>` into a shared store (often `.agents/skills/`). Those
  skills are real — the agent loads them — and the walk could not see them, so maturity was
  under-reported on exactly the repos where an over-eager restructure does the most damage.
- **Default implemented.** Two different rules, on purpose. The **general walk still never
  follows symlinks** (cycles, and escaping the repo into arbitrary filesystem). A **separate,
  bounded scan of the agent-config directories only** (`.claude/`, `.codex/`, `.cursor/`)
  **does** follow them, resolving only into `$HOME` or the repo, warning when a link resolves
  outside both, and hard-bounding how much it will enumerate. Resolved links count toward
  `counts` and the maturity threshold, and are also listed in the new
  `existing_agentic_config.symlinked` key as `"<repo-relative path> -> <target label>"`.
- **Why the asymmetry.** The two directories are being read for different reasons. The general
  walk is estimating LOC and finding manifests, where following a symlink into
  `~/Library` or a sibling checkout inflates every number and can loop. The config scan is
  answering "what will this agent actually load", where *not* following the link gives the
  wrong answer. Same operation, opposite correct default — so it is scoped rather than
  globally flipped, which is what keeps the blast radius small.
- **Why report `symlinked` separately.** A user seeing "36 skills" for a repo containing four
  files deserves to know where the other 32 live. It also lets phase 3 reason about it: skills
  from a shared store are not this repo's conventions and should not be treated as evidence of
  what this team does.
- **To change it.** The scan is `scan_agentic_dirs()` in `discover.py`. Do not widen the
  symlink-following to the general walk.
- **Status: `decided`.** But see §4.1 — this fix makes the `.agents/` question *more* urgent,
  because it counts `.agents/` content reached via a symlink while still ignoring the same
  content reached directly.

### 2.9 What counts as a reportable row in the transcript report

- **Question.** The miner's whole job is to hand phase 3 a list of counted signals. Which rows
  earn a place in it?
- **Default implemented.** Three shaping rules, all landed 18:49 IST, all of which consumers now
  depend on:
  1. **Every row has a count of 2 or more, in every list.** Previously singleton pruning was
     partial and conditional — `_counted()` dropped `count: 1` rows only when at least three
     rows had `count >= 2`, and `pain_signals` applied no minimum at all.
  2. **Request shapes are work.** Status and progress questions ("what's remaining?", "how much
     time?") go to a new **`meta_queries`** list, merged by topic, max 5 rows. Turn-taking
     ("ok", "thanks", "continue") is counted in **`sessions.social_turns`** and nowhere else.
  3. **Docs are not code.** A new **`doc_hotspots`** takes `docs/`, plans, specs and `*.md`;
     `file_hotspots` keeps code paths.

  The profanity pain pattern (`explicit frustration`) was removed at the same time.
- **Why.** Each rule fixes a way the report was misleading rather than merely noisy:
  - A `count: 1` row sitting next to a `count: 18` row reads as evidence, and `CLAUDE.md`'s
    invariant says a finding with no evidence count maps to nothing. Emitting singletons
    beside real counts invites phase 4 to build on them. **Fewer honest rows is the correct
    outcome, including zero rows** — which is already a valid result under `SKILL.md` rule 2.
  - Status questions cluster *beautifully* — they are short and highly repetitive — so they
    floated to the top of `request_shapes` and pushed real work down. The top of that list is
    the whole product in the first thirty seconds. Note the fix **separates, never deletes**:
    eighteen "what's remaining?" pings are real evidence, just for a different artifact (a
    status or handoff skill), and they are still counted.
  - `file_hotspots` was dominated by `docs/plans/*.md` on every large repo measured. A plan
    document is not a code hotspot, and treating it as one points every derived artifact at
    the wrong part of the repo.
  - Profanity: frustration is already captured by `still not working`, `not working` and
    `same error again`, which name a *workflow problem an artifact can address*. `explicit
    frustration` named a mood, and on the dogfood repo it was the **top** pain signal at count
    16, leading the list with verbatim profanity in its examples. It is a worse signal that
    outranked better ones, and it put the user's own swearing in a document they are asked to
    read and approve.
- **To change it.** `TOP_META` and `build_meta_queries()` for the meta split, the doc/code path
  predicate for the hotspot split, and the minimum in `_counted()` / `build_pain()`. Before
  loosening the `>= 2` rule, note that `request_shapes` has always enforced it via
  `cluster(min_count=2)` — the change brought the other lists in line with it, not the reverse.
- **Status: `decided`.** Verified on the dogfood repo: **19** request shapes, `meta_queries` led
  by "what work remains" (**19** across **14** sessions), `doc_hotspots` led by a plan document
  (10 mentions), minimum count 2 across every list, no profanity row, output **11,844** chars —
  still inside the ~12 KB cap. *(An earlier draft of this entry quoted 20 shapes / 18 across 13 /
  11,888 chars from a mid-run measurement; three later refinements moved them — dropping `to` from
  the subordinator list, the plurality-label rule, and the opaque-identifier guard.)* Headroom on
  the cap is thin: the largest history measured landed at 11,649 of 12,000 and the emit trimmer
  fired, dropping one `request_shape` with the contracted truncation warning. Watch it if another
  signal type is added.

### 2.10 A dependency alone never fills a `commands` slot

- **Question.** `pytest` is in `requirements.txt` and no config section mentions it. Is
  `commands.test` = `pytest`, or `""`?
- **Default implemented.** **`""`, plus two warnings.** A slot is filled only from something that
  *literally exists in a manifest* — a `package.json`/`composer.json` script, a Makefile target, a
  justfile recipe, a configured `[tool.x]` section in `pyproject.toml`/`setup.cfg`/`tox.ini` — or
  from a subcommand universal to a toolchain whose manifest is at the **root** (`cargo test`,
  `go build ./...`, `<pm> install`). One warning names every empty slot; a second names the tools
  that were seen only as dependencies.
- **Why.** `typescript` in `devDependencies` does not tell you whether this repo typechecks with
  `tsc --noEmit`, `tsc -b`, or `tsc -p tsconfig.ts.json`. A guess here is worse than a blank,
  because the command ends up in `CLAUDE.md` and in a hook, where the user finds out it is wrong
  by watching it fail. The whole product claim is that artifacts trace to evidence, and "the repo
  depends on a test runner" is not evidence of *how this repo runs its tests*. A configured
  `[tool.pytest]` section **is** — that is the team committing to an invocation.
- **The cost, stated plainly, because it is a behaviour loss.** Measured on a two-line fixture
  (`requirements.txt` holding `pytest>=7` and `ruff`, one `.py` file):

  ```
  commands: install="pip install -r requirements.txt", test="", lint="", …
  warning:  no manifest entry defines commands.dev/build/test/lint/typecheck/format;
            the slot is empty on purpose -- ask the user, never invent a command
  warning:  these tools are dependencies but no script, target or config section says
            how this repo runs them, so no command was derived from them: pytest, ruff
  ```

  That repo used to report `test: pytest` and `lint: ruff check .`. A Gemfile with rspec and
  rubocop now fills only `bundle install`. Empty slots are therefore **more common by design**,
  which puts more work on the interview: the two warnings name exactly which slots are empty and
  which dependency-only tools were seen, so phase 5 asks a targeted question instead of a generic
  one.
- **To change it.** One function: `configured()` in `discover.py`, which today admits a tool only
  when it appears in `manifests.py_tools`. Admitting single-purpose CLI tools straight from
  dependencies is a one-line change. Do not make it without deciding what you will do about
  `tsc`, which is the case that motivated the rule.
- **Status: `decided`.**

### 2.11 The git window is adaptive, with a 50-commit floor

- **Question.** `mine_git.py` used to read a fixed 180-day window. On a stable repo that window is
  nearly empty; on a busy one it is more than enough. What should the default be?
- **Default implemented.** **No default `--days` at all.** The window widens
  **180d → 365d → 1095d → 3650d → all history** and stops at the first rung holding
  `--min-commits` (default **50**) commits. `window` reports `mode` (`adaptive`/`explicit`),
  `min_commits`, the whole probe ladder in `steps[]`, and a one-sentence `reason` meant to be
  quoted into the plan. Passing `--days N` pins the window and turns the widening off
  (`mode: "explicit"`, `min_commits: 0`, `steps: []`). `window.days` keeps its old meaning
  (`0` = all history) but is now a *chosen* value, so nothing that read it broke.
- **Why.** Measured on a fresh clone of `tj/commander.js`: `--days 180` returned **7 commits and
  0 co-change clusters**; 365d returned 55 commits and 6 clusters; all history returned 1,037 and
  15. A stable, mature library is exactly the repo where path conventions are worth extracting,
  and the fixed window returned nothing for it — not "less evidence", *no* evidence, silently.
- **Why the narrowest window that clears the floor, rather than the most data.** The bias is
  deliberate: 365d/55 commits over 3650d/1037 on commander.js. Recent practice beats volume,
  because a rule derived from how a team worked five years ago is a rule about a team that no
  longer exists. The `still_exists` / `last_seen` gate (§2.13's sibling, `mapping-rules.md` §1)
  is the second half of the same idea.
- **Why 50.** A judgment call, from the measurement above: 7 commits produced nothing, 55 produced
  six usable clusters. It is one flag (`--min-commits`) and the ladder rungs are one module
  constant (`ADAPTIVE_LADDER`). It has not been measured across a corpus.
- **Evidence, re-measured this round on two real repos.** A 40-commit app: every rung under the
  floor, so `mode: adaptive`, `days: 0`, `reason: "no window reached the 50-commit floor (180d:31,
  365d:40, 1095d:40, 3650d:40, all history:40); using all history"`. A large product repo: `180d
  holds 5360 commits, at or above the 50-commit floor; not widened`.
- **The consequence for every consumer.** A commit count is now meaningless without its window.
  `SKILL.md` phase 2 says never to pass `--days`; `plan-template.md` carries a
  `GIT_WINDOW_REASON` token so the plan states which window ran and why.
- **Status: `decided`**, with the floor open to measurement.

### 2.12 Maturity counts the team's own artifacts, not everything on disk

> **Superseded in part, 2026-09-07 — see §2.22.** The provenance classification below stands and is
> still what `discover.py` computes. What is gone is the thing it fed: **`maturity` no longer gates
> anything**, because audit-only mode no longer exists. Read this entry for how provenance is
> derived and why `ambiguous` counts as own; read §2.22 for why the verdict stopped mattering.

- **Question.** A repo has nine skills under `.claude/skills/`. Five were installed from a
  marketplace. Is it `mature` — that is, does agentify drop into audit-only mode and refuse to
  propose a structure?
- **Default implemented.** **No.** `discover.py` classifies every skill and agent as `own`,
  `vendored` or `ambiguous`, and maturity is
  `provenance.own + provenance.ambiguous >= 5`. Vendored artifacts still appear in `counts`, in
  the `skills`/`agents` lists, and in de-duplication — they simply do not vote on maturity.
  Provenance is proven by a skills lockfile, an install command naming the artifact, or
  third-party documentation; anything unprovable is `ambiguous` and **counts as own**, which errs
  toward audit-only. `provenance.maturity_basis` is a ready-to-quote sentence, and a warning fires
  whenever vendored artifacts would have changed the verdict.
- **Why.** Audit-only mode exists to protect *a setup this team built and relies on*. Installing
  five community skills is a five-minute act that says nothing about whether this repo has
  conventions worth preserving — but under the old raw-count rule it silently disabled the tool's
  main function. That is a failure the user cannot see: the plan just comes back thin, with no
  statement of why.
- **Why ambiguous counts as own.** The two errors are not symmetric. Counting a vendored skill as
  own produces a *smaller, more conservative* proposal — annoying. Missing a real setup produces a
  restructure on top of one — the exact harm audit-only prevents. Unprovable cases go the safe way.
- **Evidence.** Measured on a real repo: `counts {skills: 6}`, `provenance.own {skills: 1}`,
  `vendored {skills: 5}` (all five proven by a `skills-lock.json` naming their source), verdict
  **`basic`**, with the warning *"5 of 6 existing skills/agents are third-party, installed rather
  than written here … they do NOT count toward maturity but they DO count for de-duplication."*
  Under the old rule that repo read `mature` and agentify would have refused to build.
- **The known gap.** The vendored heuristic is deliberately narrow and misses vendored skills whose
  install command does not name them (measured: an `ai-sdk` skill installed via `pnpm add ai`, and
  four Better Auth skills installed via a bare `npx @better-auth/cli`). All of those were caught by
  the lockfile instead, so nothing was misclassified — but on a repo with no lockfile they would
  count as the team's own. That is the conservative direction, by design.
- **To change it.** `classify_provenance()` in `discover.py`. Widening the heuristic needs
  measurement across more real repos, not a threshold tweak. See also §4.1, still open.
- **Status: `decided`.**

### 2.13 Bot-authored commits are excluded from every git statistic

- **Question.** In a monorepo, release automation produces the highest-support co-change clusters
  in the history. Should they count?
- **Default implemented.** **No.** Commits whose author is a machine — a `[bot]` / `(bot)` name,
  `^bot-`/`-bot$`, a no-reply sending address, `(unknown)`, or a known CI or agent identity
  (`github-actions`, `dependabot`, `renovate`, `checkpointer`, …) — are dropped from commit
  conventions, branch naming, co-change, hotspots, test discipline and the revert rate. They are
  always counted in the new `authorship` block and always listed in `contributors[]` with
  `is_bot: true` and a `bot_reason`. `--include-bots` restores the raw view.
  **Every percentage is over `authorship.commits_human`**, not `window.commits_analyzed`.
- **Why.** A version-bump bot touching `package.json` and `CHANGELOG.md` in 400 commits is the
  strongest co-change signal in the repo and describes nothing a human does. Every artifact
  derived from it would be a rule about the release pipeline, presented to the user as a rule
  about their code. The same contamination reached the interview: on one real repo
  `git shortlog -sn --all` counted a bot at **3,177 commits** and `HEAD` counted it at **0**, and
  that bot was triggering a question about team size.
- **Why the classification lives in the script, not in a reference doc.** The email address is
  available at the source and nowhere else — `contributors[]` now carries `email_domain`,
  `is_bot` and `bot_reason`, so `interview.md` §4.2 counts `is_bot == false` instead of
  maintaining a list of CI vendor names. The bare-twin case (`cyrusagent` next to
  `cyrusagent[bot]`, one machine under two display names) is caught by **shared address**, which
  no name heuristic can do reliably.
- **Evidence.** Measured on a large product repo: 3,000 commits analysed, 2,954 human, 46 bot
  across two author rows — `cyrusagent` (41) and `cyrusagent[bot]` (5), both matched, both
  attributed to one machine — and a warning naming them and what they were excluded from.
  `conventional_pct` 0.7695 is over the 2,954, not the 3,000.
- **To change it.** `--include-bots` for one run; the identity list and the shared-address rule are
  in `mine_git.py`'s author classifier. Do not flip the default: the raw view is a debugging tool,
  not evidence.
- **Status: `decided`.**

### 2.14 Branch mode commits — the undo is the commit, not the branch

- **Question.** In `branch` mode, phase 7 creates a branch and writes files on it. Does it have to
  *commit* them?
- **Default implemented.** **Yes, and this is the whole undo.** Once the last artifact is written,
  phase 7 `git add`s this run's files and commits them to the branch. Phase 7 also captures
  `BASE_BRANCH` and `BASE_COMMIT` **before writing one byte**, into `build-manifest.json`, and
  then *proves* the commit holds what it should with
  `git show --name-only --pretty=format: "$branch_name"` rather than trusting its own prediction.
  The report's undo is generated from the manifest, never from a template line.
- **Why.** A branch with nothing committed to it deletes without removing a single file:
  `git branch -D` prints `Deleted branch`, exits 0, and reverses nothing, because the files were
  loose in the working tree the whole time. That undo shipped, was documented in both templates,
  and was wrong — twice. The commit is what makes `git checkout <base_branch>` restore an appended
  file, because the appended block exists on the branch and not on the base.
- **Why the checkout line is not optional.** `git branch -D` refuses to delete the branch you are
  standing on, so the one-line form fails outright; and moving back to `<base_branch>` is what
  actually restores every `action: modified` file. Both values come from the manifest — nothing
  else recovers them after the run, and an undo that cannot name the user's branch cannot restore
  it. Detached HEAD before the run means `git checkout <base_commit>` instead.
- **What this does not cover** — see §2.15. Two classes of path cannot go in the commit, and for
  those the branch delete is not the undo.
- **Verification.** `verification.md` §10 *exercises* the removal steps instead of describing them,
  and §10.2 fails the run when any manifest artifact is in neither the branch commit nor the
  report's per-file list. The four-shape rehearsal matrix in §10.4 is a manual release check; if
  this repo ever gets a test target, that matrix is the first thing to wire into it. An untested
  undo is the defect that has now shipped twice.
- **Status: `decided`.**

### 2.15 Gitignored artifacts stay out of the commit and get their own removal step

- **Question.** The user's `.gitignore` excludes `.claude/`, and on this target most of the build
  lands there. `git add` will refuse those paths. Force them in with `git add -f`, or leave them
  out?
- **Default implemented.** **Leave them out, and generate a two-step undo.** Before writing
  anything, phase 7 runs `git check-ignore -v` over every approved path — it answers for paths
  that do not exist yet — and records `ignored` and `ignored_by` per artifact. Committable paths
  go in `committed_paths`, the rest in `uncommitted_paths`, and **`git add` takes
  `committed_paths` only**. The report emits the branch delete for the first list and explicit
  `rm -f` / marker-removal steps for the second. The user is told at the **plan gate**, not at
  build time.
- **Why not `git add -f`.** `.gitignore` is the user's declared intent. Force-adding writes
  machine-local config into a branch they may push or merge, and PRD §13 forbids the history
  rewrite that would be needed to take it back out. The cost is a two-step undo, which is
  generated and stated plainly — a much smaller price than a surprise in someone's PR.
- **A second, quieter class lands in the same list.** An `action: modified` artifact with
  `restore: span` — a file the user wrote, git never tracked, and agentify appended to — must also
  stay out of the commit. Committing it means `git checkout BASE_BRANCH` **deletes** it along with
  the user's own content, since there is no pre-run blob to restore. Measured: a hand-written
  untracked `.claude/settings.json` was committed and the undo destroyed it, directory and all.
  Only the marker-removal script can take agentify's block back out of that file.
- **Why one `git add` over a mixed list is not an option.** `git add -- <all paths>` exits 1,
  prints `The following paths are ignored`, and *stages the rest anyway* — so the build looks fine
  while the ignored artifacts miss the commit. `git add -A` is worse: exit 0, no message at all.
- **Evidence.** `vercel/turborepo` ignores `.claude/` at `.gitignore` line 6. On that shape 4 of 9
  artifacts were on the branch and 5 were not, and the old single-mechanism report told the user
  that deleting the branch removed everything. Its verification sentence was false in the same
  way: `git status` reads clean because a gitignored path is invisible to it, while `.claude/` is
  still on disk.
- **To change it.** Don't force-add. If the removal steps ever feel too long, the fix is to ask
  the user at the plan gate whether to build into an ignored directory at all — not to override
  their `.gitignore`.
- **Status: `decided`.**

### 2.16 "Can git put this back?" is the predicate that partitions the build

- **Question.** §2.14 says branch mode commits and §2.15 says gitignored paths stay out. Written as
  two independent rules they read as two special cases, and the next editor adds a third from
  scratch. What is the rule *underneath* them?
- **Default implemented.** One predicate, stated in `SKILL.md` phase 7 step 4 in as many words:
  **a path goes on the branch only if the branch delete can put it back.** Everything else follows.
  There are exactly **two** disqualifiers, both already known per artifact before a byte is written:
  1. **`ignored: true`** — `git check-ignore -v` said so (§2.15). git will not add it, so the branch
     cannot hold it, so deleting the branch cannot remove it.
  2. **`action: modified` with `restore: span`** — a file the user wrote that git never tracked, and
     agentify appended a marker block to. There is no pre-run blob on `BASE_COMMIT`, so
     `git checkout BASE_BRANCH` does not *restore* it, it **deletes** it, taking the user's own
     content with it. Measured: a hand-written untracked `.claude/settings.json` was committed and
     the undo destroyed it, directory and all.

  Everything else — `created`, and `modified` with `restore: head` — is committable. The two lists
  are `committed_paths` and `uncommitted_paths`, they partition every artifact path with none in
  both and none in neither, and **phase 8 generates each removal step from those two lists, not from
  `mode`**.
- **Why it is one predicate and not two rules.** The two disqualifiers look unrelated — one is about
  the user's `.gitignore`, the other about git's index — and they produce the identical failure:
  an artifact that the advertised undo silently does not remove, or in the second case actively
  destroys. Both were shipped and wrong. A reader who holds the predicate catches a third case
  (a submodule path, a path under a `.git/info/exclude` rule) without being told about it; a reader
  who holds two special cases does not. The predicate is also what makes the undo *testable*:
  `verification.md` §10.2 fails the run when any manifest artifact is in neither the branch commit
  nor the report's per-file list, which is the predicate restated as an assertion.
- **The cost.** Two undo mechanisms instead of one, and a report that has to explain both. That is
  the price of an undo that is true; the alternative shipped twice and was false both times.
- **To change it.** `SKILL.md` phase 7 step 4 is the statement; the manifest fields
  (`ignored`, `ignored_by`, `restore`, `committed_paths`, `uncommitted_paths`) are the mechanism, and
  `report-template.md` §3.1 renders it. Adding a third disqualifier means adding it in all three.
- **Status: `decided`.**

### 2.17 Script-name matching is token-based with a qualifier gate

- **Question.** How does `discover.py` decide that `check:type:ts` fills `commands.typecheck` while
  `install-hooks` does not fill `commands.install`?
- **Default implemented.** **Match on the normalized token stream of the script NAME, then gate the
  remainder.** A name qualifies for a slot when it contains one of that slot's tokens
  (`SLOT_NAME_TOKENS` — `test`/`jest`/`vitest`/…, `lint`/`eslint`/…, `typecheck`/`tsc`/`types`/…),
  and then **every remaining token must be in `QUALIFIER_TOKENS`** — a flavour of the *same* action:
  `check fix ts js prod dev ci watch e2e coverage unit …`. One arbitrary noun in the remainder and
  the name is rejected outright, first-token bonus or not, because the noun is what the command
  actually acts on. A rejected name falls through to a weaker **body** match (does the command line
  run a tool we recognise?), and if that fails too the slot stays `""`.
- **Why.** The old resolver was an exact-name lookup against a hand-maintained alias list, and it
  failed in both directions at once. Measured on a clean clone of `tj/commander.js`: `typescript` in
  devDependencies made discover.py emit `commands.typecheck = "npx tsc --noEmit"` — a string that
  appears nowhere in that repo — while the repo's real `check:type` / `check:type:ts` /
  `check:type:js` scripts went unreported. Four more measured misses, all scoring 65–78 under the
  old first-token rule and all wrong: `install-hooks` installs git hooks
  (`anthropics/claude-code-action`), `build:turbo` builds one cargo package (`vercel/turborepo`),
  `test-setup` prepares a fixture and runs no test, `build-docs` builds documentation,
  `lint-staged` lints the git index. A wrong slot is worse than an empty one because it reads as
  authoritative and ends up in `CLAUDE.md` and in a hook.
- **The known cost, stated plainly.** `QUALIFIER_TOKENS` is a closed list, so a name whose remainder
  is a legitimate *target* rather than a flavour — `build:web`, `test:api`, `lint:server` — is
  rejected by the name gate and has to be rescued by the body match. Verified on a two-script
  fixture: with bodies `next build` and `vitest run apps/api`, both slots fill and the citation says
  `(body match: runs next build)`; with opaque bodies (`./tools/mk.sh web`, `./tools/t.sh api`) the
  same two scripts leave `commands.build` and `commands.test` **empty**, with the usual
  empty-slot warning. That is the intended failure direction — a monorepo whose scripts are named
  after packages loses a slot rather than guessing which package is "the" build — but it *is* a
  loss, and it is the reason the interview has to be able to ask.
- **Two neighbouring rules carry the rest of the weight**, both in the same block of `discover.py`:
  the package manager is **declared, not inferred** (`packageManager` in the root `package.json`
  outranks every lockfile; turborepo declares pnpm and used to resolve as bun off fixture
  lockfiles), and **installing is the manager's job, not a script's** (`commands.install` comes from
  `<pm> install`; no `package.json` script can fill it — which is what finally stopped
  `install-hooks`).
- **To change it.** Widen `QUALIFIER_TOKENS`, in `discover.py`. Adding target nouns (`web`, `api`,
  `server`, `docs`) would recover `build:web` — and would re-admit `build-docs`, which is the case
  the gate exists to reject. They are the same edit; decide which error you prefer before making it.
- **Status: `decided`.**

### 2.18 `npm ci` and `bun install --frozen-lockfile` are alternates, never the command

- **Question.** A repo's CI workflow runs `npm ci`. It is real, it is in the repo, and it is
  literally how this project installs. Should it fill `commands.install`?
- **Default implemented.** **No — it is listed as an *alternate* on the `#commands` citation line
  and never becomes the slot's value.** `_ci_install_lines()` scans the parsed CI `runs` for
  `<pm> ci` and `<pm> install --frozen-lockfile` / `--immutable` / `--no-save` / `--production`,
  and those land after `; also:` in `raw_scripts["#commands"]["install"]`. The slot itself stays
  `<pm> install`, resolved from the declared package manager (§2.17).
- **Why.** `npm ci` is what a CI runner does to a *clean checkout*: it deletes `node_modules` and
  installs exactly the lockfile. Handing that to a developer's agent as the answer to "how do I
  install" tells it to wipe the working install, which is not what the question meant. The
  frozen-lockfile flags are the same shape — correct for a reproducible build, wrong as the
  everyday command. But the line is real and it is evidence about the repo, so **suppressing it
  entirely would be the other error**: the user gets to see it, ranked as what it is.
- **The general principle this is an instance of.** Provenance carries *every* entry that qualified
  for a slot, not just the winner (`"<manifest>#<key> (<how>) -> <cmd>; also: …"`). Anything writing
  a command into a plan or an index doc cites `discovery.raw_scripts['#commands'][slot]`, so the
  runner-up is visible at the point of decision rather than discarded at resolution time.
- **To change it.** In `resolve_commands()`, `_ci_install_lines()`'s result is assigned straight into
  `alternates["install"]` and is never passed to `take()` — so a CI line is structurally incapable of
  winning the slot, not merely outranked by score. Routing it through `take()` is the change; don't,
  unless you have also decided what a developer's agent should do when the install command it was
  handed deletes their `node_modules`.
- **Status: `decided`.**

### 2.19 The undo mechanism is chosen by the file's FORMAT, not by how git sees it

- **Question.** §2.16 partitions every artifact by "can git put this back?" and sends the answer-no
  paths to a per-file removal step. For a path in that second list, *which* removal step? The
  manifest field that gets there is `restore: span`, and the obvious reading is "un-append the
  marked block".
- **Default implemented.** **`restore: span` names the git half of the problem and does not name the
  mechanism.** The mechanism is read off the file's format, and there are two of them:
  - a **marked text file** (`CLAUDE.md`, a rule, a shell config) — agentify appended a block between
    `agentify:begin` / `agentify:end`, and the **marker-removal script** cuts exactly that block;
  - a **structurally merged JSON config** (`.claude/settings.json`, `.mcp.json`, i.e. `type: settings`
    and `type: mcp`) — JSON has no comment syntax, so the file never carried a marker and never can.
    The **JSON un-merge script** removes the entries this run added, keyed on identity
    (`("hook_command", <the hook's manifest `command`>)`, `("mcp_server", <server name>)`), deletes
    the file when nothing but agentify's entries remain, and **keeps** it when the user has added
    keys of their own since the run.

  Neither is ever `rm -f`, and neither is ever the other. `report-template.md` §3.1 carries the
  five-row routing table, and two new tokens carry it into the report: `UNMERGE_JSON_PATHS` and
  `UNMERGE_ENTRIES`. `IGNORED_CREATED_PATHS` is defined as *`uncommitted_paths` created entries minus
  `UNMERGE_JSON_PATHS`*, so a merged JSON config can never reach an `rm -f` operand list in any mode.
- **Why.** Because the wrong choice **fails silently rather than loudly**, which is the worst
  property an undo can have. Measured on the axios dogfood run: the marker script was handed
  `.claude/settings.json`, looked for `agentify:begin` in a file that can never contain one, printed
  `SKIP .claude/settings.json: no agentify block id=…`, **exited 0**, and left the merged hook
  registration in the user's settings permanently — while the report, reading that exit code,
  called the undo a success. Re-measured on a fixture while the section was written: exit 0, file
  byte-identical before and after, `enforce-bun` still registered.

  A blind `rm -f` on the same file is the opposite error and is worse: it destroys settings the user
  wrote themselves. Both errors come from routing on `action` or on `restore`, which describe git's
  relationship to the file. Only the format describes what agentify actually did to it.
- **Why this is not rare.** On the Claude Code target `UNMERGE_JSON_PATHS` is non-empty for **every
  run that builds a hook**, because registering a hook means merging into `.claude/settings.json`.
  This is the common path, not an edge case.
- **To change it.** `report-template.md` §3.1's routing table is the statement; the two tokens are the
  mechanism; `verification.md` §10.2 is the assertion that every artifact lands in exactly one row.
  Adding a third format (a TOML or YAML config merged structurally) means adding a row, a token and a
  script — not widening one of the existing two.
- **Status: `decided`.**

### 2.20 Partial (blobless) clones degrade `churn` and nothing else

- **Question.** `test-repos.md` tells contributors to clone the regression fixtures with
  `--filter=blob:none`. That clone has every commit and every tree and almost no blobs, and
  `git log --numstat` has to read blob *content* to count lines. What should `mine_git.py` do?
- **What it did.** Fetched. In a partial clone git silently dials the promisor remote for any object
  a read needs, so a read-only command opened a socket that no line of the miner asked it to open.
  Measured before this was handled: **65.7s on chalk and 78.6s on commander.js**, both ending in
  `available: false` with every statistic empty — a minute of network traffic, inside a tool whose
  contract is that the analyzer scripts make no network calls, in exchange for nothing.
- **Default implemented.** Three parts, and the first is the one that matters:
  1. **`GIT_NO_LAZY_FETCH=1` in `_child_env()`**, so the no-network promise is *structural* rather
     than aspirational: a lazy fetch now fails instantly instead of dialling out. A missed detection
     costs 0.015s instead of 65s. (No-op on a normal clone; git ≥ 2.40, and older git ignores it,
     which is why detection does not rely on it.)
  2. **`detect_partial_clone()` runs before the log pass** — three allow-listed `config --get` reads
     and a `rev-parse`, under a second — with a `.git/config` text fallback for the one shape the
     keyed reads miss, a promisor remote not named `origin`. The fallback exists so the git
     allow-list does not have to grow `--get-regexp` for it.
  3. **On a partial clone the log pass runs `--name-only --no-renames`** instead of `--numstat`.
     `--no-renames` is load-bearing: inexact rename detection also reads blob content, so plain
     `--name-only` still fetches — **8.07s versus 0.016s** on the same clone. A `--numstat` pass that
     fails on a missing object is also retried once in the path-only form rather than returning an
     empty payload.
- **What it costs: exactly one field.** Only `analyze_hotspots()` reads the numstat counts, and only
  to sum `churn`. Conventions, branch naming, co-change, hotspots, directory hotspots, test
  discipline, revert rate and authorship are computed from **paths** and are byte-identical either
  way (verified: the path evidence from a blobless chalk clone matches a full clone exactly). So
  `signals.git.hotspots[].churn` is `0` on every row, and a warning says so, says to rank hotspots by `commits`
  and never quote churn from that run, and names both fixes (clone without the filter, or
  `git fetch --refetch`).
- **Evidence, re-measured this round on a blobless fixture:** `timing_ms: 79`, `signals.git.hotspots[].churn: 0`,
  `branch_naming` identical to the same repo's non-blobless twin, and the warning present in full.
- **To change it.** `PARTIAL_CLONE_KEYS` and `detect_partial_clone()` in `mine_git.py`. Do not remove
  `GIT_NO_LAZY_FETCH=1` to "get churn back" — that trades a documented empty field for an undocumented
  network call, which is the one trade this tool cannot make.
- **Status: `decided`.**

### 2.21 List a branch's files with `git diff BASE_COMMIT..branch`, never `git show branch`

- **Question.** Phase 7 proves the commit holds what it should by listing the branch's files, and
  phase 8 corrects `committed_paths` from that listing. Which command?
- **What shipped, in three places.** `git show --name-only --pretty=format: "$branch_name"`. It is
  wrong twice over, and the second way is the dangerous one:
  - **`git show` prints one commit.** A branch-mode run commits **twice** — phase 7 commits the
    artifacts, phase 8 commits `report.md` and the manifest — so it returns the tip commit only, and
    the undo's own bookkeeping gets corrected from a subset of the truth. Measured on a two-commit
    branch: `git show` returned `build-manifest.json`, `report.md`; `git diff --name-only base..branch`
    returned `.claude/skills/s1.md`, `README.md`, `build-manifest.json`, `plan.md`, `report.md`. The
    axios dogfood run hit exactly this — it listed `CLAUDE.md`, `build-manifest.json` and `report.md`
    and not `plan.md`, which was in the first commit.
  - **On a branch with nothing committed, `git show --name-only <branch>` prints the BASE commit's
    file list.** Re-verified live this round on a fixture: a fresh branch off a base holding
    `README.md` printed `README.md`, exit 0. That hands a **false positive** to the very check meant
    to catch the "branch that held nothing" failure (§2.14) — an artifact sharing a name with a
    base-commit file reads as covered. `git diff --name-only <base>..<branch>` prints nothing on that
    branch, exit 0, which is the truth.
- **Default implemented.** `git -C "$REPO_ROOT" diff --name-only "$BASE_COMMIT".."$branch_name"`,
  using **`BASE_COMMIT` from the manifest, not `BASE_BRANCH`**: the two agree on a healthy run, and
  if the base tip has moved (a PRD §13 violation, caught by `verification.md` §10.2) the commit is
  the value that still names where the branch started. Two-dot is written rather than three-dot
  because the branch is cut from `BASE_COMMIT`, so the merge base *is* `BASE_COMMIT` and the two are
  equivalent — two-dot is the form that stays correct when someone substitutes a bare commit for a
  ref. When `BASE_COMMIT` is empty (the repo had no commits before the run) there is no base to diff
  against and the branch is the entire history, so it falls back to
  `git log --name-only --pretty=format: "$branch_name"` — verified to return both commits' paths on a
  no-base fixture.
- **Why it is a decision and not a typo.** `git show` is the command a person reaches for when they
  want "what is on this branch", and it answers a plausible-looking version of the question in both
  failure shapes above — non-empty output, exit 0, no warning. Nothing about running it says it is
  wrong. That is why it shipped three times, and why the rule is written as *never `git show` for
  this question* rather than as a fix to one call site.
- **To change it.** `SKILL.md` phase 7 step 6, `build-and-verify.md` §4.4 ("Proving the commit —
  enumerate the branch, never one commit"), and `verification.md` §10.2. All three now spell the same
  command; keep them spelling it.
- **Status: `decided`.**

---

### 2.22 There are no output caps, and no audit-only mode

- **Question.** Should agentify limit how many artifacts it builds — by repo size, by history depth,
  or by how much setup a repo already has?
- **Default implemented.** **No, on all three.** `references/sizing-caps.md` is gone, replaced by
  `references/coverage.md`, which caps nothing and instead governs merge, ranking and how skipped
  candidates are presented. Interview Q8 (raise the cap) and Q11 (confirm audit-only) are retired
  and banned. The words *cap*, *limit* and *quota* appear in no question, plan, report or summary.
  A candidate is not built for exactly one of three reasons — no counted evidence, already covered,
  or low confidence and not opted into.
- **Why.** The caps were a proxy for quality and measured the wrong thing. **Measured, 2026-09-07,
  on a real 268k-line Next.js repo:** `existing_agentic_config` reported **0 rules, 0 hooks, 0
  subagents**, a `.env.local` and a `.env.local.bak` on disk, `bun.lock` *and* `package-lock.json`
  at the root with `package.json` declaring neither, and eight external services
  (`better-auth`, `drizzle`, `postgres`, `posthog`, `resend`, `aws`, `neon`, `vercel`). It also
  reported **61 skill directories** under `.claude/skills/` — 48 vendored, 18 of them symlinks into
  an in-repo shared store — which tripped the `>= 5` maturity test and clamped the run to
  2 skills / 1 subagent / 3 rules / 2 hooks. The repo in the sample with the **most** missing got
  the smallest build, and the user was told a cap was the reason.
- **What the caps were protecting, and what replaced it.** "Fewer, sharper artifacts get used" is
  true. It is now enforced per artifact instead of per run: `mapping-rules.md` §0's evidence
  requirement, and `blueprint.md` §1.1's five personalization tests — of which test 4, *name a repo
  this file would be false in*, is the one that actually kills filler. A number could never tell a
  sharp artifact from a generic one; those two can.
- **What survived from audit-only mode.** Its useful half, now unconditional and not a mode:
  de-duplicate against everything already in the repo (vendored and symlinked included), and never
  restructure, rewrite, move or rename what is there. A symlinked or vendored artifact is never
  edited at all — a symlink lives in another store and editing it changes every repo that links it.
- **To change it.** `references/coverage.md` §1, `references/interview.md` §2 and §4.1, `SKILL.md`
  rule 4 and phase 4, `PRD.md` §9. Reintroducing a cap means reintroducing the measurement above.
- **Status: `decided`.**

### 2.23 Only artifacts inside the repo are the repo's setup

- **Question.** A developer has 61 skills in `~/.claude/skills` and 17 in `~/.codex/skills`. Do
  those count as this repo's agentic setup?
- **Default implemented.** **No.** `discover.py` already reported home-scope entries separately in
  `user_scope` and excluded them from `counts` and `maturity`; what changed is that the adapters no
  longer *union* the two scopes for the maturity verdict, and that verdict no longer gates anything
  either way (§2.22). Home-scope artifacts are read for **de-duplication only** and are never
  counted, never described to the user as "your setup", and never allowed to change what is built.
- **Why.** A global skill loads in every repo on the machine and says nothing about this project.
  The Claude Code adapter used to say *"judge maturity on the union: a user with eight global skills
  is a mature user working in this repo"* — which is true about the user and false about the repo,
  and the run acted on the second reading. The user's own framing settles it: the product exists to
  build the personalized setup of **one selected codebase**.
- **The one thing home scope still earns.** A candidate duplicating a global skill is skipped with
  the file named, exactly as for a repo-level duplicate. `~/.codex/skills` held 63 entries on the
  measured machine, of which 53 were symlinks into one repo — so counting them would have been
  wrong twice over.
- **To change it.** `references/coverage.md` §6.1, `adapters/claude-code.md` §3,
  `adapters/codex.md` §3.1.
- **Status: `decided`.**

### 2.24 A structural fact is evidence, and it carries a count

- **Question.** `mapping-rules.md` §3 used to answer "discovery-only evidence allowed?" with **No**
  for skills and subagents. On a repo with no usable transcript signal, that produces zero skills.
  Is that correct?
- **Default implemented.** **No — it is now `Yes`, under three conditions.** A skill or subagent may
  rest on `discovery.json` alone when: (1) it matches a named row in `blueprint.md` §3, §6.1 or
  §6.2 whose trigger field is non-empty; (2) it passes all five personalization tests; and (3) every
  step is readable off this repo — a real directory, a real command from a `commands` slot, the real
  module that talks to the service. Fail any one and the candidate is deleted.
- **Why.** "Evidence-derived, not templated" was being read as "transcript-derived", and those are
  not the same claim. A `posthog` dependency plus an analytics module plus event names already in
  the code is evidence that this repo does product analytics — a fact about the codebase, with a
  count. What it is *not* is evidence about what the developer keeps asking for, which is why a
  structural `F` is still capped below tier 1 in the scoring rubric and why the transcript-derived
  artifacts still rank above it.
- **Evidence.** The measured run in §2.22 built **no skills at all** on a repo with eight services,
  a Drizzle schema, a Next.js app and 384 recorded prompts. Two independent gates produced that:
  the caps, and this `No`.
- **The guard against templates.** Condition 2 is not decorative. Test 4 — *name a repo this file
  would be false in* — is what separates "a `create-linear-issue` skill that reads this team's
  labels, ticket template and definition of done" from "a `create-linear-issue` skill", and only the
  first one is licensed here.
- **To change it.** `references/mapping-rules.md` §3 and rows 12–16, `references/blueprint.md`.
- **Status: `decided`.**

### 2.25 The index doc is built last, not first

- **Question.** Build order put the index doc first, as a dependency of the rules that were wired
  from it. Is that right?
- **Default implemented.** **No.** The order is now
  `rules → hooks → permissions → skills → subagents → MCP drafts → index doc`.
- **Why, two reasons.** First, the dependency was already weaker than described: Claude Code walks
  `.claude/rules/` natively, so a `paths:`-scoped rule loads itself and the index-doc pointer is a
  discoverability aid rather than the load mechanism. Second, and decisive: the generated section's
  whole job is to **tabulate what was built** — a row per rule, skill, subagent, hook, MCP draft.
  Written first, those tables are written before the files exist, and every row is either a guess or
  a link to nothing. `index-doc-section.md.tmpl` filling rule 6 already forbade rows for artifacts
  that were not built; the old order made obeying it impossible.
- **The knock-on.** `setup-manager` is the **last skill**, for the same reason one level down: its
  deliverable includes an inventory of everything this run generated.
- **To change it.** `SKILL.md` phase 7 step 5, `references/build-and-verify.md` §2.2,
  `references/mapping-rules.md` §3.1, both adapters' §4 preamble.
- **Status: `decided`.**

### 2.26 Permissions are an artifact type; a plugin manifest is not

- **Question.** Which artifact types does a run emit?
- **Default implemented.** **Permissions in, plugin manifest out.**
  `templates/settings-permissions.json.tmpl` merges a `permissions.allow` / `.ask` / `.deny` block
  into `.claude/settings.json`; on Codex the permission surface *is* `.codex/rules/agentify.rules`,
  so the permissions step and the command-policy step produce one validated file. `plugin.json.tmpl`
  and `codex-plugin.json.tmpl` stay on disk as reference material for `setup-manager` and are never
  read by a build.
- **Why permissions.** It is the cheapest guardrail in the product and every run skipped it. Every
  permission prompt a developer answers by hand for a command their own repo defines is a prompt
  that never needed to happen, and every `.env*` read the hooks block should also be blocked
  declaratively so the guardrail survives someone deleting a hook.
- **Why not a plugin manifest.** The setup is derived from one repo's evidence and personalized to
  it — `blueprint.md` §1.1 test 4 makes that a hard requirement on every generated file. A portable
  copy of a setup that names *this* repo's directories, commands and services would be wrong
  wherever it landed. The shareable unit is the committed config, which a teammate gets by cloning.
- **Manifest shape.** A permissions block is **not** a new manifest `type`. It merges into the same
  `.claude/settings.json` the hook registrations merge into, and one file gets one artifact entry
  (`build-and-verify.md` §5.3 rule 2), so it is a `settings` entry whose `merge.entries` carries
  both `hook_command` and the new `permission_entry` kind. `verify_artifacts.py` accepts
  `permissions` as a `settings` synonym for exactly this reason; two entries for one file would make
  the un-merge run twice on the same path.
- **To change it.** `adapters/capabilities.md`, `adapters/claude-code.md` §4.7 and §4.8,
  `adapters/codex.md` §4.7, `references/mapping-rules.md` §3.1,
  `references/build-and-verify.md` §2 and §5.4, `references/report-template.md` §3.1.
- **Status: `decided`.**

### 2.27 agentify never opens a pull request

- **Question.** After building on a branch, should agentify offer to open a PR?
- **Default implemented.** **No.** Interview Q2 is retired and banned, `open_pr` is not a field,
  phase 8 has no PR step, and `pushed` / `pr_url` are read only so a branch an older agentify pushed
  can still be cleaned up.
- **Why.** Two reasons, and the second is the stronger one. (a) It was never load-bearing: the
  default was always "leave the branch", and the question's own guard — the push-access ladder —
  suppressed it on most runs. (b) Removing it removes the **only** network path in phases 0–8 other
  than `mine_git.py`'s opt-in `gh pr list`: the ladder ran `gh auth status` and
  `gh repo view --json viewerPermission`. agentify now makes no network call at all in a default run,
  which is a simpler promise to make and a simpler one to keep.
- **What went with it.** The whole ladder, including the zsh word-splitting fix that made it work at
  all. The reasoning pattern it demonstrated survives in `interview.md` §1.9: a trigger reads JSON or
  another question's **default**, never another question's answer.
- **To change it.** `SKILL.md` phase 8 step 6 and rule 7, `references/interview.md` §4.1.
- **Status: `decided`.**

### 2.28 The interview asks for a command it cannot find, and never guesses one

- **Question.** `discover.py` deliberately leaves a `commands` slot empty rather than inventing a
  command, and warns that the user should be asked. Nothing asked. What fills the slot?
- **Default implemented.** Two new questions. **Q15** fires when `commands.install` is empty and the
  package manager is ambiguous — the riffads shape, two root lockfiles and a `package.json`
  declaring neither — and its answer both fills the slot and licenses the package-manager
  enforcement hook. **Q16** lists every other empty slot a phase-4 candidate actually needs, and its
  **default is `skip these`**: a candidate whose slot stays empty is dropped, named, under Skipped
  (insufficient evidence), never built against a plausible-looking command.
- **Why the default is `skip`.** A wrong command in a hook fires on every write. Under a `defaults`
  reply the safe resolution is fewer artifacts, not a guessed `prettier --write .`.
- **Why this is not the banned "which package manager do you use?".** `interview.md` §2 bans asking
  what discovery answered. Q15 fires **only** where discovery says in writing that it could not tell
  and instructs that the user be asked — the opposite case, and the question quotes the two
  lockfiles so the premise itself can be corrected.
- **To change it.** `references/interview.md` §4 rows Q15/Q16 and §4.7.
- **Status: `decided`.**

### 2.29 One interview question has no trigger: the engineering system

- **Question.** Some developers run a packaged workflow on top of the agent — Every's compound
  engineering, Obra's superpowers. Should the generated setup sit inside it?
- **Default implemented.** Yes, and **Q14 asks, unconditionally.** No field in either JSON records
  it, so it is the one question in the bank with no trigger to check — deliberately, and the trigger
  audit records it as correct rather than as a defect. Three answers: none (build nothing for it),
  already installed (the index-doc stitch gains a workflow section describing how the generated
  artifacts plug in), or wanted (a needs-you item with the exact install command).
- **Why agentify does not install it.** A marketplace install reaches the network and changes what
  loads in every session in that repo. It is the user's call and the user's command. Generated
  artifacts must also never *depend* on the named system, so the setup works whether or not they
  run it.
- **The guard.** Never suggest a system the user did not name, and never invent an install command
  for a name you do not recognise — put their words in the report as the thing to install.
- **To change it.** `references/interview.md` Q14 and §4.6, `references/blueprint.md` §8.
- **Status: `decided`.**

### 2.30 Three more questions retired — because their answers were derivable

- **Question.** After §2.22's four bans, a real run still asked eight questions. Three of them —
  branch-or-staged, which-services-do-you-touch, who-else-reads-this — drew the complaint that
  started this round. Were they earning their slots?
- **Default implemented.** **No. All three are retired and derived instead** (`interview.md` §4.2,
  §4.8). The bank is now nine questions and a typical run asks five.

| Retired | Derived |
|---|---|
| *Where should I put the files — branch or staged?* | `mode = "branch"` whenever `discovery.git.is_repo`, `no-git` otherwise. `stage-only` only when the user says in words not to commit — no question offers it |
| *Of the services I found, which do you actually touch?* | The `external_services[]` entries **ranked** on four signals — `confidence`, a module in the repo that calls it, transcript corroboration, env-var surface — and all proposed, most critical first |
| *Who else reads what I write here?* | `team_size` from the contributor rows: `solo` when one non-bot author **or the top one holds `>= 80%` of `authorship.commits_human`**; else `team-reviewed` with a contributing/pr-template doc; else `team-unreviewed` |

- **Why, in one rule.** *A question whose answer is derivable, or whose effect the phase 6 gate
  already exposes, costs a slot and buys nothing.* All three failed it. Branch was the default every
  run took and is the safer answer anyway — the commit **is** the undo. The service list is a filter
  the gate already provides, by number, over a plan the user can read. And the team question asked
  for a fact that was sitting in `signals.git.contributors[]`.
- **Evidence, on the service question.** Its own `Why:` line on the measured run read *"tool_mentions[]
  came back empty, so nothing in 30 sessions ranks these for me"* — the question fired **because**
  agentify could not rank, and asked the user to do the ranking. That is the work agentify exists to
  do. The ranking in §4.8 uses the four signals it always had.
- **Evidence, on the team question.** The measured repo splits **82 / 19 / 2** across three non-bot
  names. The old rule (`>= 2` non-bot rows ⇒ team) defaulted it to `a team, but changes land without
  review` for a developer working alone, and would have written team-shaped rules on that basis. The
  80%-share clause reads it as `solo`, correctly: a long tail of one- and two-commit names is a pair
  session, a drive-by fix, a second machine identity, or an uncaught bot — not a reader of the rules.
- **What makes not asking safe, and it is not optional.** Each derived value gets **one line in the
  plan's summary** stating the derivation *and* how to overturn it — `DERIVED_MODE_LINE`,
  `DERIVED_SERVICES_LINE`, `DERIVED_TEAM_LINE` in `plan-template.md`. A derived value the user cannot
  see is a decision made behind their back, which is worse than the question was.
- **The knock-on the service question was carrying.** `mapping-rules.md` §1.1 gate 2 used the phase-5
  answer as its no-history route for MCP drafts. Its replacement is a **coupling, not a softening**:
  the gate is also met when this run built a skill or subagent for that service (`blueprint.md` §7),
  which means the draft is licensed by an artifact that itself passed the personalization test. A
  service with no skill, no subagent and no tier-1 record gets no draft, on any history.
- **To change it.** `references/interview.md` §2, §4.1, §4.2, §4.8 and §8; `SKILL.md` phase 5 and
  phase 7 step 4; `references/plan-template.md`; `references/mapping-rules.md` §1.1 and row 15;
  `references/blueprint.md` §3, §6.1 and §11.
- **Status: `decided`.**

## Part 3 — Judgment calls flagged for sign-off

These two were made by the `SKILL.md` author, are load-bearing, and were flagged rather than
buried. Neither is a bug. Both trade something real away.

### 3.1 Phase 0 detects the target without opening an adapter

- **Question.** Phase 0 must set `TARGET` to `claude-code` or `codex`. Should it read an
  adapter file to do so?
- **Default implemented.** **No.** `SKILL.md` phase 0 step 2: the model knows which agent it is
  running inside — Claude Code → `claude-code`, Codex → `codex` — sets `TARGET` from that, and
  if it genuinely cannot tell, asks one question offering `claude-code` as the default. The
  line "Do **not** open an adapter file to answer this" is explicit. The one matching adapter
  is read in **phase 7**, where the emit formats are actually needed.
- **Why.** The two adapters cost roughly 18k tokens together, ~9.6k for the one that would be
  opened in phase 0 and then re-read or held through eight phases. That is a straight tax on
  the context window, in a tool whose entire architecture is about protecting it — the miner
  pre-aggregates a 400 MB history to ~3k tokens for exactly this reason, and spending 9.6k of
  the savings on a question the model can answer from its own runtime is self-defeating.

  **What it defeats: nothing.** The adapter's `detect` section describes how to recognise a
  target from repo *files* — which matters for `discovery.json`'s `targets_detected` (a
  property of the repo) but not for which agent is executing right now (a property of the
  runtime, which the model knows directly and more reliably than any file heuristic). Phase 0
  is asking the second question. Reading the adapter would substitute a weaker signal for a
  stronger one **and** cost 9.6k tokens.
- **The trade.** If the model's self-knowledge is ever wrong, phase 0 sets the wrong target and
  the error surfaces in phase 7 — after the plan is approved. The mitigations are the
  one-question fallback when detection is uncertain, and the fact that `TARGET` appears in
  `plan.md`, which the user reads at the gate.
- **To change it.** Move the adapter read into phase 0 and accept the token cost, or factor a
  small `detect`-only section out of each adapter into a file cheap enough to read early.
- **Status: `needs sign-off`.** Recommendation: **keep it.** The saving is large, the risk is
  visible in the plan, and the fallback question exists.

  **To sign off in one line.** Reply *"3.1: keep"* — and the only edit is this entry's status,
  `needs sign-off` → `decided`, plus the same word on the `Phase 0 detects the target without
  opening an adapter` line in the build contract's open-decisions list. **No code or reference file
  changes**, because keeping it is what is already in the tree.

  **If the answer is instead "read the adapter in phase 0"**, the edit is: in `SKILL.md` phase 0
  step 2, replace the sentence "Do **not** open an adapter file to answer this" with a read of
  `adapters/<target>.md` §detect, and delete the one-question fallback that follows it. Budget ~9.6k
  tokens per run, every run, and note that `SKILL.md`'s 600-line budget is unaffected — the cost is
  the adapter's own size, not this file's. The cheaper third option, if the objection is really
  "phase 0 should not guess": split a `detect`-only section out of each adapter into its own small
  file and read *that* in phase 0. That is new files plus an edit to both adapters, and is the only
  one of the three that needs work beyond a status word.

### 3.2 `mine_git.py` runs with `--no-gh` by default

- **Question.** `mine_git.py` can call `gh pr list` to derive `pr_patterns` — PR title
  conventions and body sections, which map to a PR-description artifact. Should phase 2 use it?
- **Default implemented.** **No.** `SKILL.md` phase 2 invokes
  `mine_git.py --repo "$REPO_ROOT" --no-gh` — no `--days`, because the window is adaptive now
  (§2.11) — and `SKILL.md` rule 7 names this as one of exactly two `gh` exceptions to "no
  network", both disabled or explicitly gated by default. `pr_patterns` comes back
  `{"available": false}` with a `pr_patterns: skipped (--no-gh)` warning. The flag is dropped
  **only** if the user asks for PR-pattern evidence and understands it reads from GitHub.
- **Why.** `gh pr list` is the only network-capable path in the analyzer *scripts*, and PRD §13
  plus `CLAUDE.md` promise **no network calls** and **local only**. (One more `gh` call exists in
  the run, outside the scripts: phase 5's push-access probe in `interview.md` §4.1 — `gh auth
  status` then `gh repo view --json viewerPermission`. It asks a permission question rather than
  fetching data, it is read-only, and it goes through the user's own credentials. `SKILL.md` rule 7
  names both; a promise with an unnamed exception is not a promise.) A privacy promise with a quiet
  default-on exception is not a privacy promise. The user cannot audit an exception they were
  never shown, and "the analyzer scripts make no network calls" is the sentence that makes a
  tool which reads your entire chat history acceptable to run at all.

  Making it opt-in also keeps the promise checkable by a reader who has not read the code:
  every command line in `SKILL.md` carries `--no-gh` in plain sight.
- **The cost, stated plainly.** `pr_patterns` evidence is lost on every default run. A repo
  whose PR conventions are its strongest signal — a team with a rigorous PR template and no
  commit convention — gets a weaker plan than it could have, and agentify will not propose a
  PR-description artifact it had the means to justify. This is a real loss, accepted knowingly.
  Local git evidence (`commit_conventions`, `branch_naming`, `cochange_clusters`, `hotspots`,
  `test_discipline`, `revert_rate`) is unaffected and is the bulk of the signal.
- **To change it.** Drop `--no-gh` from the phase 2 command line. If that is ever done it must
  come with an explicit consent step in phase 0, in the same shape as the transcript consent —
  the user is told what will be contacted and answers before it happens — and `SKILL.md` rule 7
  and the README's privacy section must be rewritten to match. **Never silently.**
- **Status: `needs sign-off`.** Recommendation: **keep it.** An alternative worth considering
  if PR evidence proves valuable: offer it in the phase 5 interview as a numbered question with
  the default set to *no*, which surfaces the choice without breaking the promise.

  **To sign off in one line.** Reply *"3.2: keep"* — and the only edit is this entry's status,
  `needs sign-off` → `decided`, plus the same word on the `mine_git.py runs with --no-gh by default`
  line in the build contract's open-decisions list. **No code or reference file changes**; `--no-gh`
  is already on the phase 2 command line in `SKILL.md`.

  **If the answer is "turn PR evidence on"**, it is not a flag deletion, and doing it as one would
  break a promise the README makes in print. The edit, in full and in this order:
  1. `SKILL.md` phase 2 — drop `--no-gh` from the `mine_git.py` command line.
  2. `SKILL.md` phase 0 — add a consent step in the same shape as the transcript consent: name
     github.com, name `gh pr list`, name what it reads (PR titles and body section headings, no repo
     content), and take yes/no *before* phase 2 runs.
  3. `SKILL.md` rule 7 — it currently names two `gh` exceptions, both off or gated by default. Rewrite
     it: one of them is now on by default and consented instead.
  4. `README.md` privacy section (the "Local only, with two named exceptions" bullet) — same rewrite.
     This is the sentence that makes a tool which reads your entire chat history acceptable to run,
     so it changes with the behaviour or not at all.
  5. `references/privacy.md` — the phase 0 consent script grows the second question.

  **The recommended middle path**, if this is reopened because PR evidence turned out to matter:
  add it as a numbered phase 5 interview question with the marked default **no**. That is steps 1
  and 5 only (the command line becomes conditional on the answer, and `interview.md` grows one
  question inside the existing 3–8 budget), and it needs neither a phase 0 consent step nor a
  rewrite of the privacy promise — because the default run still makes no network call.

---

## Part 4 — Open, no default is an answer

### 4.1 Do `.agents/` directories count toward maturity detection?

- **Question.** `discover.py` sets `existing_agentic_config.maturity` to `mature` when the
  team's **own** skills + agents reach 5 (`provenance.own + provenance.ambiguous >= 5` — see
  §2.12; the raw `counts` total is no longer the threshold), and mature triggers **audit-only
  mode** — propose additions and fixes, never restructure (PRD §8, `CLAUDE.md`). Should skills
  living in an `.agents/` directory count toward that five?
- **What is implemented today.** **They do not.** The skill/agent/rule collector matches only
  `.claude/skills/`, `.claude/agents/`, `.claude/rules/`, `.claude/commands/`,
  `.codex/skills/`, `.cursor/rules/` and `.cursorrules`. `.agents/` appears in exactly one
  place — `classify_doc()` excludes it from the docs list, alongside `.claude`, `.codex` and
  `.cursor` — so the walker knows the directory is agent config and then counts nothing in it.
  `targets_detected` is a fixed four-value enum (`claude-code`, `codex`, `cursor`, `copilot`)
  with no `.agents` member, so an `.agents/`-only repo can report `targets_detected: []`.
- **What just changed, and why it sharpens the question rather than answering it.** The
  symlink fix landed at 18:46 IST. `discover.py` now runs a bounded scan of the agent-config
  directories **with symlinks followed** (the general repo walk still never follows them), so a
  skill symlinked from `.claude/skills/x` into a shared `.agents/skills/x` store now counts —
  toward `counts`, and toward the `>= 5` maturity threshold **when provenance classes it as the
  team's own or leaves it ambiguous** (§2.12; the raw `counts` total stopped being the threshold in
  the same round, so "counts, and therefore maturity" no longer follows and this sentence used to
  say it did) — and is listed in the
  new `existing_agentic_config.symlinked` key as `"<path> -> <target>"`. Measured on the
  dogfood repo: `maturity: mature`, `counts {skills: 36, agents: 8, rules: 35, hooks: 7}`, most
  of those skills symlinked into `.agents/skills/`.

  So the current state is **inconsistent, not merely conservative**: `.agents/` content counts
  when it is reachable through a `.claude/` symlink and does not count when it lives in
  `.agents/` directly. The same six skills produce `mature` or `none` depending on a
  filesystem detail the user made for their own reasons. That is not a defensible line.
- **Why it is currently `false` — and why that is not really an argument.** The four-value enum
  came from the PRD's adapter list, and the collector was written against the same list.
  Nothing weighed `.agents/` and decided against it; it was simply not in scope. That is the
  honest account, and it is why this is open rather than `decided`.
- **Why it matters.** Getting this wrong is worse in one direction than the other. A repo with
  six skills under `.agents/` reads today as `maturity: none` or `basic`, so agentify runs in
  full build mode and proposes a structure **on top of a mature setup it could not see** —
  precisely the restructuring that audit-only mode exists to prevent, and the outcome most
  likely to make a careful user distrust the tool. The opposite error (counting a stray
  `.agents/` directory and dropping into audit-only) produces a smaller, more conservative
  proposal — annoying, not damaging.
- **To change it.** Add `.agents/skills/` and `.agents/agents/` to the collector's prefix list
  in `discover.py`, and decide whether `targets_detected` grows a fifth value or `.agents/`
  maps onto an existing one. Then **re-check the `>= 5` threshold against real repos**: it has
  never been measured against a corpus, only reasoned about, and the symlink fix has already
  moved counts under it (36 skills on the dogfood repo, where the pre-fix count was a fraction
  of that). Growing the `targets_detected` enum is the expensive half — every consumer that
  switches on it, including both adapters, has to handle the new value — which is why the
  answer is not automatically yes to both halves of the question.
- **The measured consequence, stated concretely — this is what changed since the last round.** A repo
  whose skills live **directly** in `.agents/skills/`, rather than symlinked into `.claude/skills/`,
  is invisible to the collector. It reports `targets_detected: []` and can read `maturity: none`, so
  agentify runs in full build mode and **proposes a duplicate of a skill that already exists in that
  repo** — de-duplication reads the same lists the collector fills, so a skill it cannot see is a
  skill it cannot de-duplicate against. The user's first impression of the tool is then a plan
  proposing something they already wrote.
- **The rest of `discover.py` already treats `.agents/` as the team's own agent config.** Only the
  collector does not, which is why this reads as an oversight rather than a position. Three sites,
  all present in the tree today:
  - `SKILLS_LOCK_PATHS` includes `.agents/skills-lock.json` — provenance already looks there.
  - The vendored-path predicate deliberately excludes `.agents/`, with the comment *"a shared team
    store is the team's own"*, and `discover.py --selftest` asserts it:
    `not _is_vendor_path("/repo/.agents/skills/own-skill")`.
  - `classify_doc()` excludes `.agents/` from the docs list alongside `.claude`, `.codex` and
    `.cursor` — the walker knows the directory is agent config and then counts nothing in it.

- **Status: `needs a decision`.** Recommendation: count them toward **maturity** (the
  asymmetry above is decisive) while leaving `targets_detected` at four values until there is
  an adapter to point a fifth value at. Maturity is about "is there already a setup here", which
  is target-agnostic; `targets_detected` is about "which adapter do we emit for", which is not.

  **To approve in one line.** Reply *"4.1: count `.agents/`, leave `targets_detected` at four"*.
  That authorises exactly the four edits below, all in `skills/agentify/scripts/discover.py`, all
  additive, none touching an enum any consumer switches on:

  | # | Site | Edit |
  |---|---|---|
  | 1 | `AGENTIC_CONFIG_DIRS` | add `".agents/skills"`, `".agents/agents"` — this is what puts the directory in the bounded symlink-following scan (§2.8) |
  | 2 | `_symlink_bucket()`'s prefix tuple | add `(".agents/skills/", "skills")` and `(".agents/agents/", "agents")`, so a link *out of* `.agents/` is bucketed like one out of `.codex/` |
  | 3 | the `for rel in sorted(paths)` collector in `detect_agentic_config()` | add an `.agents/skills/` branch mirroring the `.codex/skills/` one **including its `SKILL.md` entrypoint guard** (without the guard, every `scripts/` and `references/` file inside a skill re-counts the directory), and an `.agents/agents/` branch mirroring `.claude/agents/` |
  | 4 | the orphan-warning loop | add `".agents/skills"` to the `for dir_rel in (…)` tuple, so a directory there with no `SKILL.md` is reported the same way |

  **Not changed:** `targets_detected` stays the four-value enum `claude-code | codex | cursor |
  copilot`. Growing it is the expensive half — every consumer that switches on it, both adapters
  included, has to handle the new value — and there is no `.agents` adapter to point it at. An
  `.agents/`-only repo therefore reports `targets_detected: []` *and* a real maturity verdict, which
  is the honest pair: there is a setup here, and we do not know whose format to emit in. Phase 0 asks
  the target question anyway (§3.1), so nothing downstream is blocked by the empty list.

  **Then re-measure the `>= 5` threshold**, which has never been checked against a corpus — only
  reasoned about — and which these edits move counts under. §2.8's symlink fix already took the
  dogfood repo to 36 skills from a fraction of that. Verify at minimum: one `.agents/`-only repo
  (should flip to `mature`), one `.claude/`-only repo (must not move), and the dogfood repo
  (must not double-count the skills it already reaches through symlinks — that is what edit 3's
  entrypoint guard and the existing de-duplication are for, and it is the one regression these edits
  can plausibly introduce).

  **If the answer is instead "leave it".** Then say so in this entry and the inconsistency becomes a
  documented position rather than an oversight — but `discover.py` must then also emit a warning when
  it walks past a populated `.agents/skills/` it is not counting, because a silently invisible setup
  is the failure mode that produces the duplicate-skill proposal above. That warning is the minimum
  price of a "no", and it is roughly the same amount of work as edit 4.

---

## Part 5 — Release blockers

Neither of these is a defect. Both are placeholders that were left deliberately visible rather
than filled with an invented value, and **only the user can supply what they need.** Do not
guess a URL, do not infer one from the repo, and do not remove the placeholder text to make the
output look finished.

### 5.1 The attribution upsell carries a literal `<link>`

- **What.** The second attribution string is:

  > `Bigger codebase or a team? Agentic Studio builds the full engineering system in 2 to 3 weeks: <link>.`

  **One missing URL is currently spelled three different ways.** Exact inventory, greped this
  round — an earlier draft of this entry got both the count and the files wrong:

  | Spelling | Where | Count |
  |---|---|---|
  | literal `<link>` | `skills/agentify/SKILL.md` (attribution section), `skills/agentify/references/report-template.md` (the skeleton footer and the filled example) | 3 |
  | `{{AGENTIC_STUDIO_URL}}` | `skills/agentify/templates/index-doc-section.md.tmpl` | 1 |
  | `PLACEHOLDER-LINK` | `README.md` footer | 1 |

  Only the template's `{{AGENTIC_STUDIO_URL}}` is a *token* — it sits in the same double-brace
  namespace as every other placeholder in that file, so the fill step already knows to replace it.
  The other two are prose that happens to read like a placeholder. That is the whole reason to
  unify: a fill pass that walks `{{...}}` finds one of the five and silently ships the other four.
- **Why it is still there.** `report-template.md` already carries the correct instruction:
  substitute it only with a URL configured in the repo, and **if there is none, leave `<link>`
  exactly as written — never invent a URL.** That is the right behaviour for a tool that writes
  files into someone's repo, and it is why this is a blocker rather than a bug.
- **Blocking.** Every generated report, every generated index-doc section, and the final run
  summary — the three attribution placements from `CLAUDE.md` — ship with a visible `<link>`
  until a real URL exists.
- **Needed from the user.** One URL: the Agentic Studio landing page the upsell should point at.
  Then replace all **five** occurrences. Pick one spelling first — `{{AGENTIC_STUDIO_URL}}` is the
  right one, because it is the only form the templates' own fill rule can see.

### 5.2 `PLACEHOLDER-ORG` in the plugin manifests

- **What.** `PLACEHOLDER-ORG` appears **11 times** in shipped files, counted this round:
  `.claude-plugin/plugin.json` ×3 (`author.url`, `homepage`, `repository`),
  `.claude-plugin/marketplace.json` ×3 (`owner.url`, `author.url`, `homepage`), and `README.md`
  ×5 — the install command `/plugin marketplace add PLACEHOLDER-ORG/agentify` twice (above the
  fold and under Install), two `git clone https://github.com/PLACEHOLDER-ORG/agentify.git` lines,
  and the status banner. *(This entry previously said four in the README; it is five. The four
  occurrences in this file are the entry describing them and do not need replacing.)*
  `test-repos.md` carries none — its clone URLs all point at real public repos.
- **Why it is still there.** The repo is not published and the GitHub org is not chosen.
  `README.md` line 22 discloses this correctly.
- **Blocking.** **The documented install command does not work.** This is the first thing a
  user runs, so it is the hardest blocker in the file. It is also entangled with §1.1: if the
  name changes, these strings change again.
- **Needed from the user.** The GitHub org (or user) the repo will be published under, and
  confirmation of the final repo name. Then replace every `PLACEHOLDER-ORG`, verify the install
  command against the real published marketplace, and update `test-repos.md` if any clone URL
  there points at the placeholder.

---

## How to maintain this file

- One entry per decision, in the five-part shape above. A decision without a **why** is not
  recorded, it is just asserted.
- When a `provisional` or `needs sign-off` item is settled, change the status **and** keep the
  argument that was rejected. The next person to reopen it needs to know it was already
  weighed.
- Never upgrade a status because a default has been in the tree a while. `needs-user-input`
  changes only when the user answers.
- `PRD.md` is not edited from here. If a decision genuinely supersedes the PRD, say so in the
  entry and raise it with the owner.
