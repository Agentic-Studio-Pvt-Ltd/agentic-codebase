# interview.md — phase 5 question bank and discipline

Read this file in **phase 5 (Interview) only**, after phase 4 has produced the candidate list
(`mapping-rules.md`, then `blueprint.md`, then `coverage.md`). The interview exists to resolve the handful of choices that evidence
genuinely cannot settle. It is not a discovery interview and it is not a preference survey.

---

## 1. Hard rules

1. **Ask 3 to 8 questions. Absolute ceiling 12.** If your selection produces fewer than 3, ask
   fewer — do not invent filler. If it produces more than 8, cut by priority (§3) until you are
   at 8. Only go past 8 when a question is `must-ask` and its trigger fired, and never past 12.
2. **Every question carries a recommendation, and one word accepts it.** No open-ended question
   without one. The recommended option is the answer you would proceed with if the user walked
   away — so it must be one you would actually defend, not the most cautious cell in the table.
   §5 has the shape it renders in.
3. **Every question has a fired trigger.** If the trigger condition in §4 is false for this run,
   the question does not get asked. No exceptions, no "might as well".
4. **Ask once, in one block.** One message containing all the questions. Do not drip them.
   No follow-up round unless an answer is genuinely unparseable (§7).
5. **One word accepts everything** — `ok`, `yes`, `defaults`, and the rest of §6's list.
6. **Never ask what discovery already answered** (§2).
7. **Never ask a question whose answer changes nothing.** Every entry in §4 names what it
   changes downstream. If, for this run, the answer would change nothing — for example the plugin
   question when zero artifacts are portable — drop it.
8. **There are no caps, and the interview never mentions one.** agentify builds the whole setup
   the evidence supports (`coverage.md` §1). No question offers to raise, lower or explain a limit,
   and the words *cap*, *limit* and *quota* do not appear in a question, an option or a `Why:` line.
9. **Minimal input is a design constraint, not a courtesy.** The user must be able to clear the
   whole interview with the word `ok`, and must never have to re-type something already on their
   screen. Every question is answerable by its letter alone; a whole reply of `ok` accepts every
   recommendation; nothing is re-asked to confirm; and a derived value is never put back as a
   question (§4.8). A question the user has to think hard about to answer *at all* is a question
   that needed a better recommendation.
10. **A recommendation you cannot justify in one clause is not a recommendation.** The `Why:` line
   carries the justification and cites a field and a number (§5). If the honest `Why:` would be
   "I have no idea, you pick", the evidence has not been read hard enough — read it again, or
   derive the value and state it in the plan instead of asking (§4.8).
11. **No trigger may read another question's answer.** Rule 4 asks every question in one message,
   so at the moment you compose a question *no* question has been answered yet. A trigger of the
   form "ask this if Q7 answered `b`" can never fire, and it fails silently — the question simply
   never appears, in any run, and nothing reports it. Every trigger in §4 must resolve against
   `discovery.json`, `signals.json`, the phase-4 candidate list, the phase-0 consent value and
   target detection, or another question's **default** (which *is* known at compose time).
   Where one answer genuinely has to override another, do it **after** the reply, in §7's
   reconciliation step — never in a trigger. §4.3 audits the whole bank against this rule.
12. **Every noun comes from the target, never from a literal.** A question that hardcodes
   `CLAUDE.md`, `.claude/`, "Claude Code plugin", or one target's hook exit contract is wrong on
   every run against the other target — and it fails the way a bad trigger fails, silently, because
   the user cannot tell that the question they were asked was the wrong one. **§3.1 is the
   vocabulary**: a bank row that names a file path, an artifact type, a directory or a tool spells
   the token, and a question whose *options* differ in mechanism rather than only in name carries a
   verbatim per-target block beside it (Q3 → §4.4; Q14 → §4.6).
   Triggers obey the same rule: a trigger that reads a path or an artifact reads the token, so a
   question that is meaningless on one target drops itself there instead of asking wrong. Adding a
   new target-shaped literal anywhere in this file is the defect §3.1 exists to prevent.

---

## 2. Banned questions — discovery already answered these

Never ask any of the following. If you feel the urge to ask, the answer is in `discovery.json`;
go read the field named here instead.

| Do not ask | Already in |
|---|---|
| Which package manager do you use? | `discovery.package_managers`, `discovery.manifests` |
| What framework is this? | `discovery.frameworks` |
| What is your test command? Lint? Build? Typecheck? Format? | `discovery.commands.*`, `discovery.raw_scripts` |
| What language is this repo? | `discovery.languages` |
| Do you use TypeScript / Python / Go? | `discovery.languages` |
| Do you have CI? What does it run? | `discovery.ci[]` |
| Where do tests live? | `discovery.folders[].zone == "tests"`, `signals.git.test_discipline.test_paths` |
| Is this a monorepo? | `discovery.monorepo.is_monorepo` |
| Do you already have an index doc (`CLAUDE.md` / `AGENTS.md`) / skills / agents? | `discovery.existing_agentic_config` |
| Which agent's config is already here? | `discovery.existing_agentic_config.targets_detected[]`, `.artifacts_by_target[]` |
| Do you use Codex / Claude Code? | phase-0 target detection; `targets_detected[]`. Q7 asks which one to **build for** when both are configured and detection was ambiguous — never which ones exist |
| Which env vars / services do you have configured? | `discovery.env_var_names`, `discovery.external_services` |
| How many contributors? How many people work here? How old is the repo? | `discovery.git.age_days`, `signals.git.contributors[]` |
| Do you use conventional commits? | `signals.git.commit_conventions` |
| What do you ask the agent to do most? | `signals.transcripts.request_shapes` |

**Four questions were retired, and are banned outright.** They are listed here because each one was
in the bank and each one was measured wasting a slot or producing a worse setup.

| Never ask | Why it is gone |
|---|---|
| *"When I'm done, open a pull request, or leave the branch for you?"* | **agentify never opens a pull request.** `open_pr` is gone from the record, phase 8 has no PR step, and the push-access ladder that guarded it is gone with it. The branch is left for the user, every time, and the report says so |
| *"Package this as a TARGET_NAME plugin so you can install it in other repos?"* | The setup is derived from **this** repo's evidence and is personalized to it (`blueprint.md` §1.1 test 4) — it is not portable by construction, so packaging it for other repos is offering something that would be wrong wherever it landed. The plugin manifest is not an artifact type any more |
| *"My cap for this repo is N skills / … Raise the cap, or keep the sharpest ones?"* | There are no caps (`coverage.md` §1) |
| *"You already have a mature setup — N of the M skills and agents here are your own. I'll run audit-only?"* | There is no audit-only mode (`coverage.md` §6). Measured: on a repo with 0 rules, 0 hooks and 0 subagents, 61 installed third-party skill directories triggered it and throttled the run. De-duplication is unconditional and needs no question; never restructuring is an invariant, not a mode |

The last one has an adjacent question that is also banned: never ask the user to **confirm** what
their existing setup is. `existing_agentic_config` already says, and §6.1 of `coverage.md` says how
to read it.

**Three more were retired 2026-09-07, and are banned for a different reason than the four above.**
Those four asked for things that should not exist. These three asked for things agentify can work
out for itself, or that the phase 6 gate settles better:

| Never ask | Instead |
|---|---|
| *"Where should I put the files — a new branch, or staged in your working tree?"* | **Always `branch`** when `discovery.git.is_repo`, named `agentic-setup/<yyyy-mm-dd>`; write in place when there is no repo. It is the safer of the two by construction — the commit *is* the undo — and it was the default every run took anyway. `stage-only` stays reachable when the user asks for it in words, at any point (§4.8) |
| *"Of the services I found, which do you actually touch in a normal week?"* | **Rank them and propose, most critical first** (§4.8). The question existed to filter a list the phase 6 gate already lets the user cut by number, and its own `Why:` line admitted the problem: on a run where `tool_mentions[]` is empty there is nothing to rank with, so it asks the user to do the ranking |
| *"Who else reads what I write here, and does anything get reviewed before it lands?"* | **Derive `team_size`** from the contributor rows and the docs (§4.2). The fact was already in the JSON; asking it produced a wrong default on a repo whose top author holds 80% of the commits |

The pattern in all three: **a question whose answer is derivable, or whose effect the plan gate
already exposes, costs a slot and buys nothing.** Before adding one, ask which field would have
answered it, and whether approving the plan by number would have settled it.

Citing a count in a `Why:` line is not asking for it. §5 requires the question to cite a real
signal, so `4 non-bot authors on the default branch over the 365-day window` is a legitimate
*reason* line — never the answer being requested. Name the window from `signals.git.window.days`;
it is chosen per repo, not fixed at 180 (§4.2).

---

## 3. Selection procedure

1. Walk the bank in §4 top to bottom. Evaluate each trigger against `discovery.json`,
   `signals.json`, the phase-4 candidate list, and the consent value from phase 0.
2. Keep every question whose trigger is true.
3. Sort the kept set by `priority`: `must-ask` first, then `high`, then `medium`, then `low`.
   Within a tier, keep the bank's own order.
4. If the kept set is larger than 8, drop from the bottom until it is 8. Never drop a `must-ask`.
   If the `must-ask` set alone exceeds 8, ask them all, up to the ceiling of 12.
5. Renumber the survivors 1..N. Numbers are positional for this run; do not reuse the bank's IDs.

### 3.1 Target-derived wording — the vocabulary the bank spells instead of literals

`TARGET` is settled before this phase: `SKILL.md` phase 0 step 2 sets it from the agent you are
running inside. Every question below that names a file, a directory, an artifact type or a mechanism
takes its noun from this table (§1.12). The bank writes the **token**; you render the cell.

| Token | `claude-code` | `codex` |
|---|---|---|
| `TARGET_NAME` | `Claude Code` | `Codex` |
| `INDEX_DOC` | `CLAUDE.md` | `AGENTS.md` (`AGENTS.override.md` outranks it in the same directory; Codex does **not** read `CLAUDE.md` unless the user's config lists it — `existing_agentic_config.codex.claude_md_fallback`) |
| `AGENT_DIR` | `.claude/` | `.codex/` |
| `HOOK_CONFIG` | `.claude/settings.json` | `.codex/hooks.json` |
| `HOOK_BLOCK_FORM` | the hook exits **2** and its stderr goes back to the model as the instruction | the hook exits **0** and prints `hookSpecificOutput.permissionDecision: "deny"`, with `permissionDecisionReason` as the instruction |
| `PERMISSIONS_FILE` | `.claude/settings.json` (`permissions.allow` / `.deny`) | `.codex/rules/agentify.rules` — the Starlark command policy is this target's permission surface |
| `MCP_DRAFT` | `.mcp.json`, env-var placeholders only | `<plan-dir>/codex-mcp.toml`, a TOML fragment you apply to `.codex/config.toml` yourself |
| `ALT_PLAN_DIR` | `.claude/agentic-setup/` | `.codex/agentic-setup/` — the symmetric location, and the one `adapters/codex.md` §4's objection actually asks for: what that section forbids on a Codex run is offering `.claude/agentic-setup/`, because a `.claude/` directory in a Codex repo is misleading. `.codex/` is not. Nothing under `.codex/` is a load path except `config.toml`, `hooks.json`, `rules/*.rules` and `agents/*.toml` (`adapters/capabilities.md`), so a directory of markdown there is inert — same as `.claude/agentic-setup/` is on the other target |

Four rules govern the table, and they are what stop this file drifting back to one target:

1. **An empty cell means the thing does not exist on that target.** Drop the option that names it;
   if that leaves the question with one option, drop the question and take its default silently
   (§1.7). **No cell is empty today**, and the one that used to be — `ALT_PLAN_DIR` on Codex — is
   the reason this rule needs restating rather than deleting. An empty cell silently removes a
   *choice*, and it removed the wrong one: with nothing to offer beside `docs/agentic-setup/`, Q9
   could not fire on Codex, so every Codex run wrote its plan and report into the repo's `docs/`
   tree without asking. Measured on the h3 run, where `docs/` is the project's published
   documentation site. Emptying a cell is therefore a decision about what the user is allowed to be
   asked — make it deliberately, and check what question goes quiet when you do.
2. **A token is added here before it is used in a row.** If you are about to type `CLAUDE.md`,
   `.claude/`, `.codex/` or "Claude Code plugin" into a question, stop: either the token exists, or
   this table gains a row first.
3. **`adapters/capabilities.md` is the authority for every value above**, and phase 6 reads it to
   write the plan. If the two disagree, that file is right and this table is stale. **Phase 5 never
   opens an adapter** — the table is here so it does not have to.
4. **Where the two targets differ in *mechanism* and not just in name**, the token is not enough:
   the question carries a verbatim per-target block, the way Q3's option text lives in §4.4. Today
   that is exactly one question, Q3 (§4.4).

Who reads what, so the next edit can see at a glance whether a row is load-bearing: `TARGET_NAME`
→ Q14; `INDEX_DOC` → Q10 and Q12; `AGENT_DIR` and `ALT_PLAN_DIR` → Q9; `MCP_DRAFT` → Q9;
`HOOK_BLOCK_FORM` → Q3, through §4.4; `HOOK_CONFIG` → Q3's `Why:` line only, where it names the
file the hook is registered in; `PERMISSIONS_FILE` → Q3's `Why:` line and Q15's.

**The ambiguous-target run (Q7 in the set).** Q7 exists only when both targets are configured *and*
phase-0 detection was ambiguous, so on that run `TARGET` is not settled when you compose. Resolve
every token against **Q7's own default** — the phase-0 provisional target — exactly as §1.11 requires
a trigger to read a default rather than an answer, and add the other target's form in a trailing clause
where one word covers it (`…in .claude/settings.json (.codex/rules/ if you pick Codex above)`).
**Q9 is now one of the questions that trailing clause saves, and it must be asked.** Its two
options differ only in a directory name — `.claude/agentic-setup/` or `.codex/agentic-setup/` —
so compose it against Q7's default and name the other in the same parenthesis, exactly as the
example above does: `b) .claude/agentic-setup/ (.codex/agentic-setup/ if you pick Codex
above)`. It used to be
dropped here alongside Q12, on the reasoning that its trigger was target-conditional; that stopped
being true when `ALT_PLAN_DIR` gained a Codex value, and dropping it is what forces the plan into
the repo's `docs/` tree unasked (§4.5). **Q12 is still dropped** on any run where Q7 is asked — its
trigger reads `INDEX_DOC`-specific rows and Codex-only fields, which is a genuine target-conditional
trigger and not a wording problem — and takes its default (`append`), safe on either target because
nothing is ever overwritten. Q3's and Q14's answers carry over untouched because what they record —
block or warn, which engineering system — is target-independent. Q7 itself names both targets by
construction and is the one question exempt from the table.

---

## 4. Question bank

`Q#` are bank IDs for your bookkeeping only — the user sees sequential numbers.

| ID | Question text | Default | Trigger — ask only when | What it changes downstream |
|---|---|---|---|---|
| Q3 | **When a generated hook catches the thing it was built to catch, should it block the action, or warn and let it through?** — the options differ in mechanism per target, so take them **verbatim from §4.4** | `a) warn only` | `high`. At least one hook candidate is in the phase-4 candidate list. **Ask on both targets.** Codex has a full hook system — 12 events, `<repo>/.codex/hooks.json`, regex matchers over tool names (`adapters/capabilities.md`, `mapping-rules.md` §2.2) — so there is no "no hook support" case and nothing to substitute. The clause that used to skip this question on Codex shipped every Codex hook at the `warn` default without the user ever being asked. The old second clause (`discovery.commands.test` or `.typecheck` non-empty) is gone with it: it silently suppressed the question for command-policy hooks — "never run `npm` here" — which carry the same strictness choice and have no test command behind them. Name the actual candidates, and the command each wraps where there is one, in the `Why:` line. | `hook_strictness` in the answer record. Phase 7 emits each hook's decision path from it — `HOOK_BLOCK_FORM`, spelled out per target in §4.4 — and the plan's "what it will not do" line for that artifact says which was chosen; `verification.md` §5.2 tests the built hook against this value (`warn` returning non-zero is a fail, not a bonus). Blocking is opt-in, never the default. On Codex, where phase 4 mapped a forbidden-command finding to `.codex/rules/<name>.rules` instead of a hook (`mapping-rules.md` §2.2), the same answer sets that rule's `decision`: blocking → `forbidden`, warn → `prompt`. |
| Q7 | **I can see config for both Claude Code and Codex. Which should I build for?** | `a) the agent you're running me in right now` — name it; `b)` names the other one | `must-ask` when `discovery.existing_agentic_config.targets_detected` contains **both** `claude-code` and `codex` AND phase-0 detection of the running agent was ambiguous. Never ask when detection was unambiguous. `targets_detected[]` is a fixed four-value enum (`claude-code`, `codex`, `cursor`, `copilot`) driven by paths on disk, and `codex` is set by `AGENTS.md` / `AGENTS.override.md` / `CODEX.md` / `.codex/` only — a repo whose sole Codex artifact is `.agents/skills/` does **not** set it, so a `cursor` or `copilot` entry never makes this question fire and a skills-only Codex repo relies on phase-0 detection instead. | Which adapter phase 7 loads, every output path, and which column of `adapters/capabilities.md` phase 6 copies into the plan's capability notes. It also fixes every §3.1 token — until it is answered they resolve against this question's own default, and §3.1's ambiguous-target rule drops Q9 and Q12 for the run. Nothing is substituted on either target as of the 2026-09-05 verification: the difference the notes carry is paths, formats, and Codex's project-trust prerequisite. |
| Q9 | **Where should the plan and report live — `docs/agentic-setup/` or `ALT_PLAN_DIR`?** | evidence-derived — §4.5 picks between `a) docs/agentic-setup/` and `b) ALT_PLAN_DIR` | `low`, raised to `medium` when the docs clause fires. **`ALT_PLAN_DIR` exists on both targets** (§3.1), so the target never removes this question. Ask when **either** holds: `AGENT_DIR` already appears in `discovery.folders[].path` — the repo already keeps agent config, so the plan sitting beside it is a real option; **or** a `discovery.folders[]` row has `zone == "docs"` — that tree is the user's, and agentify's plan is not their documentation. `zone` is `null` on most rows and `"docs"` on a real doc directory: compare, never sort. When neither holds, take `docs/agentic-setup/` silently — creating that directory collides with nothing. | The write path for `plan.md`, `report.md` and `build-manifest.json`, in phases 6, 7 and 8. Referred to elsewhere as `PLAN_DIR`. It also moves every other `<plan-dir>` path: reference docs on both targets, and on Codex the MCP draft and any long prose rule file too (`MCP_DRAFT`, `adapters/codex.md` §4.2.1) — state the resolved directory once in the plan instead of repeating it per artifact. |
| Q10 | **Workspaces detected. Set this up once at the root, or per package?** | `a) root only` | `high`. `discovery.monorepo.is_monorepo` is true AND `len(discovery.monorepo.workspaces) >= 2`. | Whether artifacts are written at the root or duplicated per package, and whether rules get path scopes per workspace. Per-package multiplies the file count — restate the resulting count before building. On Codex, per-package also means a nested `INDEX_DOC` chain, and Codex reads that chain against a single 32768-byte `project_doc_max_bytes` budget and **stops** at the cap: say so before building, and cite `discovery.existing_agentic_config.codex.index_doc_chain_bytes` for what the chain already costs. |
| Q12 | **Your INDEX_DOC is N KB already. Append a delimited section, or draft a separate file for you to merge?** | `a) append a delimited section` | `medium`. A row in `discovery.existing_agentic_config.index_docs[]` **whose `path` is this target's `INDEX_DOC`** has `bytes > 8000` AND `has_agentify_section` false. The path test is the whole fix: those rows are one per real file across `CLAUDE.md`, `AGENTS.md`, `AGENTS.override.md` and `CODEX.md` with **no target field**, and a repo can carry a 6 KB `CLAUDE.md` and a separate 6 KB `AGENTS.md` as unrelated files (measured on a real repo, 2026-09-05). On Codex accept `AGENTS.md` or `AGENTS.override.md`, and accept `CLAUDE.md` **only** when `…codex.claude_md_fallback` is true — otherwise Codex does not read that file, there is nothing to append to, and phase 7 writes a fresh `AGENTS.md`. Cite `…codex.index_doc_chain_bytes` for `N` on Codex, not the single row: it sums the repo's `AGENTS.md` chain plus `~/.codex/AGENTS.md` against the 32768-byte `project_doc_max_bytes` cap, and discovery already warns above 24576. | Phase 7 index-doc emission: in-place append vs a sibling draft file. Changes the modified-files row and its diff preview in the plan. Never overwrite either way. On Codex the separate-draft answer also avoids pushing the instruction chain past the cap, where Codex silently drops the deeper files rather than truncating visibly. |
| Q13 | **I found N low-confidence findings I'd normally skip. Want them included?** | `b) no — skip them` | `low`. At least 2 phase-3 findings are confidence `low` AND none of them is already in the build list. | Moves those candidates from "skipped" into the build list. Low-confidence findings are never built without this explicit yes. |
| Q14 | **Do you run a packaged engineering workflow on top of TARGET_NAME — Every's compound engineering, Obra's superpowers, or another marketplace plugin?** — options in §4.6 | `a) no, none` | `must-ask`. **Always.** No field in either JSON records this, and `blueprint.md` §8 makes it the one thing that changes how the whole setup is stitched together. It is the only unconditional question in the bank besides Q1, and unlike Q1 it has no trigger to check. | `engineering_system` in the answer record. A named system that is **already installed** adds a workflow section to the index-doc stitch (`blueprint.md` §9 item 2) and shapes where the generated rules and skills plug in. A named system the user **wants** becomes a plan line and a "needs you" step with the exact install command — agentify never installs a marketplace plugin itself, and never makes the generated setup depend on one. `a` builds nothing for this and is not editorialized about. |
| Q15 | **Two things in your repo disagree about the package manager — which one does it really use?** — name the exact lockfiles and manifest fields found | evidence-derived: the manager with the strongest signal, named explicitly | `must-ask` when `discovery.commands.install == ""` **and** either `len(discovery.package_managers) >= 2` or a `discovery.warnings` entry names an ambiguous or mismatched package manager. §2 bans asking which manager a repo uses — this fires **only** where discovery says in writing that it could not tell and instructs you to ask, which is the opposite case. | Fills `commands.install` for the rest of the run, so every generated skill and hook quotes a real command. It is also what licenses the **package-manager enforcer** hook (`blueprint.md` §4.1): the chosen manager is what the hook allows, and the others are what it blocks by name. Without an answer that hook cannot be built and is dropped with the reason stated. |
| Q16 | **I could not find a COMMAND_SLOT command in your manifests, and N of the artifacts below need one. What do you run?** — list every empty slot a candidate needs, one line each | `a) skip these — build the rest without them` | `high`. At least one phase-4 candidate needs a `discovery.commands` slot whose value is `""`. Read the empty slots off `discovery.commands` and the two `discovery.warnings` entries that name them, and list only the ones a candidate actually needs. **Never guess a command** (`SKILL.md` phase 1) and never offer one as the default. | Fills the named slots. A candidate whose slot is still empty after the answer is dropped and listed under **Skipped (insufficient evidence)** naming the slot — not built against an invented command. |

Notes on the bank:

- **There is no dirty-tree question in this bank, by design.** The gate binds once, in `SKILL.md`
  phase 7 step 3, immediately before the first artifact is written — not in phase 0 and not here.
  Never invent one: phases 0–6 write only `plan.md`, so a dirty tree cannot harm anything the
  interview decides, and asking here would mean asking twice.
- If consent (phase 0) is `none`, drop any question whose trigger references `signals.transcripts.*`.
  No question in the bank does today; the **service ranking** in §4.8 does, and it degrades rather
  than stopping — signal 3 contributes nothing and signals 1, 2 and 4 carry the order.
- Never add a question that is not in this bank without a concrete, run-specific reason, and
  never add more than one. It still counts against the ceiling and still needs a default and a
  named downstream effect.
- **No row above spells a target-specific literal, and a new one must not either** (§1.12). Six of
  the nine questions name something that differs between Claude Code and Codex — Q3, Q9, Q10, Q12,
  Q14 — and every one of them reads a §3.1 token or a `discovery.existing_agentic_config.codex`
  field. If a run makes you want to write `CLAUDE.md`, `.claude/` or "a Claude Code plugin" into a
  question, the answer is a token in §3.1, never a literal in the question. Three others — Q13, Q15,
  Q16 — are target-neutral, because confidence, lockfiles and shell commands are properties of the
  repo, not of the agent. Q7 is the ninth: it is *about* the target, and §3.1 exempts it.
- **No question is skipped because of the target, and none is left that could be.** Q9 was the last
  one a target could remove — §3.1 rule 1 dropped it wherever `ALT_PLAN_DIR` was empty, and it was
  empty on Codex — so every Codex run took `docs/agentic-setup/` without asking. That is now a live
  question on both targets (§4.5). Every artifact type agentify builds has a native home on both
  targets as of the 2026-09-05 verification, so a trigger clause of the form "skip on Codex, the
  substitution is stated in the plan" is stale by construction — that clause is exactly how Q3 came
  to be skipped on every Codex run, and an empty §3.1 cell is the same failure with no clause to
  point at.
- **Q14, Q15 and Q16 are the three questions that make the setup usable rather than plausible.**
  Q14 decides whether the setup sits inside an existing workflow or beside it; Q15 and Q16 are the
  only way an empty `discovery.commands` slot ever gets filled, and every hook and skill that quotes
  a command depends on one of them. Do not drop them to stay under 8 unless something `must-ask`
  forces it — §3 step 4 sorts them above the `medium` and `low` rows for exactly this reason.

### 4.1 Retired questions — Q1, Q2, Q4, Q5, Q6, Q8 and Q11, and what went with them

These four are banned (§2). Each carried machinery, and the machinery is gone too. It is recorded
here so the next edit does not reintroduce it by reflex.

| Retired | What was removed with it |
|---|---|
| **Q2 — open a pull request?** | The whole **push-access ladder**: reading the push remote, testing the host for GitHub, `command -v gh`, `gh auth status`, and `gh repo view --json viewerPermission`. That ladder was the only network call in a run other than `mine_git.py --no-gh`. **agentify now makes no network call at all in phases 0–8**, and `SKILL.md`'s no-network rule has one exception rather than two. Phase 8 has no PR step and `open_pr` is not a field |
| **Q6 — package as a plugin?** | The plugin manifest as an artifact type: `plugin.json.tmpl`, `codex-plugin.json.tmpl`, `mapping-rules.md` row 12, the `PLUGIN_MANIFEST` token, and the build-order step. The setup is personalized to one repo (`blueprint.md` §1.1 test 4); a portable copy of it would be wrong wherever it landed |
| **Q8 — raise the cap?** | Every cap. See `coverage.md` §1 |
| **Q11 — audit-only?** | The audit-only mode, its clamp table, and the `audit_only` field. De-duplication is unconditional (`coverage.md` §6) and never-restructuring is an invariant, not a mode |

**Three more retired 2026-09-07** — and these were not bad questions, they were *answerable* ones.
Each is now derived in §4.8, and the derivation is stated in one line of the plan so the user can
overturn it at the gate, which is cheaper for them than answering it up front.

| Retired | Derived instead | What it cost |
|---|---|---|
| **Q1 — branch or staged?** | `mode = branch` whenever there is a git repo (§4.8) | A `must-ask` slot on every single run, for a question whose default was taken almost every time. `branch` is also the safer answer: the commit is the undo, and `stage-only`'s undo is a per-file list |
| **Q4 — which services do you touch?** | services ranked structurally, all proposed, most critical first (§4.8) | On a run with no `tool_mentions[]` it hands the user a list of eight and asks them to do the ranking — the work agentify is for. The plan gate already lets them drop any of them by number |
| **Q5 — who else reads this?** | `team_size` from the contributor rows and the docs (§4.2) | It asked for a fact that was already in `signals.git.contributors[]`, and on a repo split 82 / 19 / 2 it defaulted to `team, lands without review` for a developer working alone |

**The test before adding any question back:** name the JSON field that would have answered it, and
say why approving the plan by number would not have. If you can do the first, it is derivable; if
you cannot do the second, the gate already covers it.

**The one thing worth keeping from Q2's ladder** is the reasoning pattern, which §3.1 still cites: a
trigger reads JSON or another question's **default**, never another question's *answer*, because
§1.4 asks everything in one message. That is §1.11, and it is why dependent wording composes against
another question's **default**, never its answer.

**Never re-derive a PR offer from anything.** Not from a `contributing` doc, not from `pr_patterns`,
not from a user saying "I'll PR this later". agentify leaves the branch and says so.

### 4.2 Deriving `team_size` — read one field, drop the machines, weigh the survivors

**`team_size` is derived, never asked** (§2, §4.1). It still needs a correct contributor count, and
getting that count right is most of this section — the question that used to consume it is gone, the
measurement is not.

Once you have the non-bot rows, the derivation is three lines, in order — first match wins:

| Result | Test |
|---|---|
| `solo` | one non-bot author, **or** the top non-bot author holds `>= 80%` of `signals.git.authorship.commits_human` |
| `team-reviewed` | not solo, **and** `discovery.docs[]` holds a `contributing` or `pr-template` kind |
| `team-unreviewed` | not solo, otherwise |

**The 80% clause is the fix, and it is what the retired question got wrong.** A repo split
**82 / 19 / 2** across three non-bot names has one person writing four commits in five; the old
question defaulted it to `team, lands without review` and would have written team-shaped rules for a
developer working alone. A long tail of one- and two-commit names is a pair session, a drive-by fix,
a second machine identity, or a bot the classifier did not catch — none of them is a reader of the
rules this run writes. Take the share off `authorship.commits_human`, never off
`window.commits_analyzed` (which still counts the bots).

**Say the derivation in the plan, in one line**, so the user can overturn it at the gate — that is
the whole reason it is safe not to ask:

```
Writing for a solo repo: 82 of 103 human commits (80%) are yours, and there is no CONTRIBUTING or
PR-template doc. Say "team" and I will widen the rules.
```

What it changes: the **tone and scope** of the index doc and rules — team rules name the convention
*and* the reason it exists, solo rules stay terse — and whether an **onboarding** artifact is
eligible at all. It does **not** gate the pr-reviewer subagent: `blueprint.md` §3 fires that on its
own evidence, and a solo developer reviewing their own diff before it lands is a real use.

---

The rest of this section is the measurement, unchanged, because every `Why:` line that cites a
contributor count still depends on it.

The old question used to ask *"roughly how many people?"*, which §2 bans outright, off a trigger
that read `discovery.git.contributors`. On the commander.js dogfood the second "contributor" was
`Checkpointer <checkpointer@noreply>`: 154 commits, none of them on `HEAD`. The question was
banned **and** a machine had triggered it. Two repairs, both required.

**Read `signals.git.contributors[]`, never `discovery.git.contributors`.** They are different
measurements and only one is usable:

| Field | How it is produced | Verdict |
|---|---|---|
| `discovery.git.contributors` (int) | `git shortlog -sn --all --no-merges`, no time window | `--all` sweeps every ref — stale branches, remote-tracking refs, bot-only refs. **Contaminated by construction. Never trigger on it.** |
| `signals.git.contributors[]` (rows of `{name, commits, email_domain, is_bot, bot_reason}`) | `git log HEAD` over the window `mine_git.py` **chose** (`signals.git.window`), capped by `--max-commits`, top 20 rows, people sorted before machines so a bot can never displace a human out of the cap | Default branch, inside the window, **with the bot verdict already computed**. The right measurement. |

There is **no `email` key** on those rows and there never was one — only `email_domain`, the domain
half. Do not reach for an address: the local part is the identifying half and the script never emits
it. Everything a `Why:` line needs is already in `is_bot` and `bot_reason`.

**The window is chosen, not 180 days.** `mine_git.py` widens 180d → 365d → 1095d → 3650d → all
history until it holds 50 commits, so a `Why:` line that says "in the last 180 days" is wrong on
every repo that had to widen. Read `signals.git.window.days` (`0` means all history) and say what it
actually was — `signals.git.window.reason` is a ready-made sentence.

Reproduced on a second real repo, 2026-09-04: `shortlog -sn --all` counts 11 authors; `HEAD` over
180 days counts 10; the single name present only off `HEAD` is `Checkpointer`, with 3,177 commits
on `--all` and **0** on `HEAD`. The `--all` field calls that repo one contributor larger than it
is, on a bot's say-so — the same failure, on a different repo, from the same field.

**Then drop the machines — the script has already done it for you.** *(This paragraph used to say
`contributors[]` carries "no email" and hand you a name list to pattern-match. Both halves are now
wrong: the rows carry `email_domain`, `is_bot` and `bot_reason`, and the classification runs at the
source where the full address is available.)*

**Count `is_bot == false`. That is the whole method.** `bot_reason` says why each machine was
classified — quote it if the `Why:` line needs to explain a number. `mine_git.py` also excludes bot
commits from every statistic by default, and `signals.git.authorship` reports how many there were,
so a repo that looks busy because of automation reads honestly here.

What the script matches, so you know what it does *not*: a `[bot]` / `(bot)` name, `^bot-` / `-bot$`,
a no-reply sending address, `(unknown)` (its placeholder for an authorless commit), the known CI and
agent identities (`github-actions`, `dependabot`, `renovate`, `snyk-bot`, `imgbot`,
`allcontributors`, `semantic-release-bot`, `greenkeeper`, `copilot`, `claude`, `codex`,
`cursoragent`, `checkpointer`), and — now enforced by **shared address**, not by name — the bare
twin of a `[bot]` row: `cyrusagent` next to `cyrusagent[bot]` is one machine under two display
names, counted once.

That name list is now a **fallback**, not the method: reach for it only if `is_bot` is absent
because `signals.git` is unavailable. A name neither the script nor the list matches, and that reads
as a person, is a person. When genuinely unsure, count them: over-counting by one costs a slightly
wordier rule, while the behaviour this replaces cost a banned question asked because a bot had
commits.

**Truncation and absence.** `signals.git.contributors[]` is truncated at 20 rows, so on a large repo
the plan's derivation line says "at least N", not "N" — the 80% share is still exact, because it
comes from `authorship.commits_human` rather than from the row count. When `signals.git.available`
is false there is no contributor evidence at all: derive from the docs signal alone
(`contributing` / `pr-template` ⇒ `team-reviewed`), and with neither, take `solo` and say so.

### 4.3 Trigger field audit

A trigger that reads a field the scripts no longer emit never fires and never says so — a silent
failure with no symptom. Every field below was confirmed emitted by running `discover.py`,
`mine_git.py` and `mine_transcripts.py` against a real repo, 2026-09-04. Re-run that check
whenever a script's schema moves.

| ID | Field(s) the trigger reads | Emitted by | State |
|---|---|---|---|
| Q3 | the phase-4 candidate list only | — | **repointed, and un-skipped** — the trigger read "target hook support" against a claim (`Codex has no hooks`) that was never a field and is now known false: Codex loads `<repo>/.codex/hooks.json`, 12 events, verified 2026-09-05 against codex-cli 0.152.1. Measured consequence of the old clause: on a Codex run Q3 never appeared, so every generated Codex hook shipped at the `warn` default with the user never asked. The `discovery.commands.test` / `.typecheck` clause went with it — both slots are still emitted (`""` when unknown), but they gated the question on a *test* hook and suppressed it for command-policy hooks |
| Q7 | `discovery.existing_agentic_config.targets_detected[]`; phase-0 detection | `discover.py` | ok — fixed four-value enum (`claude-code`, `codex`, `cursor`, `copilot`), re-read in `discover.py` 2026-09-05. Its `codex` entry comes from `AGENTS.md` / `AGENTS.override.md` / `CODEX.md` / `.codex/` and **not** from `.agents/skills/`, so a skills-only Codex repo does not set it |
| Q9 | `AGENT_DIR` in `discovery.folders[].path`; a `discovery.folders[]` row with `zone == "docs"` (and its `files` count for the `Why:` line) | `discover.py`, §3.1 | **repointed twice** — first the second option was the literal `.claude/agentic-setup/`, which `adapters/codex.md` §4 forbids offering on a Codex run, so it became `ALT_PLAN_DIR`; that cell was then empty on Codex and §3.1 rule 1 silently dropped the whole question there. Now `ALT_PLAN_DIR` has a Codex value and the docs clause is **inverted**: the old trigger required *no* `zone == "docs"` folder, which is exactly backwards — a repo that already owns a `docs/` tree is the repo you must ask (§4.5). `zone` is `null` on most folder rows and `"docs"` on real doc directories; rows carry `{path, files, depth, zone}` and are the top 140 by recursive file count (all re-confirmed in `discover.py`, 2026-09-05): test equality, never sort |
| Q10 | `discovery.monorepo.is_monorepo`, `.workspaces[]` | `discover.py` | ok |
| Q12 | `...index_docs[].path` **and** `.bytes`, `.has_agentify_section`; on Codex `...codex.index_doc_chain_bytes` and `.claude_md_fallback` | `discover.py` | **repointed** — the trigger read any index-doc row, so on a Codex run a large `CLAUDE.md` fired a question about a file Codex does not read. Rows are de-duplicated by real file and carry `path`, `bytes`, `has_agentify_section`, `is_symlink`, `link_target`, `aliases` — and **no target field**, which is why the `path` test is the fix. All five fields confirmed 2026-09-05 |
| Q13 | phase-3 finding confidences | — | ok, internal |
| Q14 | nothing — it is unconditional | — | ok. **Deliberately triggerless**: no field records which engineering system a developer runs, so there is nothing to read. It is the one question whose absence of a trigger is correct rather than a defect |
| Q15 | `discovery.commands.install`; `discovery.package_managers[]`; `discovery.warnings[]` | `discover.py` | ok — confirmed on a real repo 2026-09-07: two root lockfiles (`bun.lock`, `package-lock.json`), `package.json` declaring neither, `commands.install` left `""`, and two warnings naming the ambiguity and instructing that the user be asked |
| Q16 | `discovery.commands.*` (the empty slots); `discovery.warnings[]`; the phase-4 candidate list | `discover.py` | ok — `commands` is always seven slots and never absent, so an empty slot is a value to test, not a missing key |

The bank runs Q3, Q7, Q9, Q10 and Q12–Q16 — nine questions. Q1, Q2, Q4, Q5, Q6, Q8 and Q11 are
retired (§4.1); `mode`, `services` and `team_size` are derived instead (§4.2, §4.8). Those
derivations still read `discovery.git.is_repo`, `discovery.external_services[]`,
`signals.git.contributors[]` and `discovery.docs[].kind`, so those four fields stay live and this
audit still covers them.

**Re-audited in the stale-prose cleanup round, by running all three scripts again.** Every field in
the table above is still emitted, with the same type, and `discovery.folders[]` still carries
dot-directories (`.claude`, `.agents`, `.claude-plugin`, `.github` all present on a real repo), so
Q6's and Q9's path clauses are live. Two shapes moved under fields the bank reads, and neither breaks
a trigger — but a `Why:` line that quotes them naively is wrong:

- `signals.git.contributors[]` gained `email_domain` / `is_bot` / `bot_reason` and has **no `email`
  key**. §4.2 counts `is_bot == false`; nothing here needs an address.
- `discovery.monorepo` grew from three keys to seven. Q10 reads `is_monorepo` and `workspaces[]`,
  both unchanged in name, type and meaning (`workspaces` is now the union across systems with the
  negations moved to `excludes`), so Q10's trigger is unaffected. `systems[]` and `task_runners[]`
  are lists of **objects**, not strings — do not render either into an option or a `Why:` line
  without pulling a field out of the row.

**Re-audited again in the Codex round, 2026-09-05, by running `discover.py`, `mine_git.py` and
`mine_transcripts.py` against three real repos** — this checkout, a Bun/Expo monorepo carrying both
`CLAUDE.md` and `AGENTS.md`, and a git repo with human and bot authors. Every field the table above
reads is still emitted with the same type and meaning. Both analyzers grew Codex-shaped output this
round, and the bank now reads four of the new fields (Q6, Q9, Q10, Q12) — here is the whole delta, so
the next trigger is written against what the scripts emit rather than against what a target used to
lack:

- **`discovery.existing_agentic_config.codex{}` is new and is always present**, even on a repo with
  no Codex config at all (every value empty or `0`). Keys: `repo_trust_level`, `trust_source`,
  `features{}`, `config_files[]`, `hook_files[]`, `hook_scripts[]`, `plugin_manifests[]`,
  `skills_root`, `claude_md_fallback`, `index_doc_chain_bytes`, `notes[]`. Q12 reads two of them;
  Q10 cites one. **`plugin_manifests[]` lists both targets' manifests**, not only Codex's — Q6 reads
  `folders[]` (or the target-tagged `artifacts_by_target[]` row) for that reason.
- **`…artifacts_by_target[]` is new**: rows of `{target, kind, count, names, paths}` where `target`
  is `claude-code`, `codex` or **`shared`** — `.agents/skills/` is shared, so a row's target is not
  a claim about which agent wrote it. No trigger requires it; Q6 may use it as the tagged form of
  its `folders[]` clause.
- **`…user_scope{}` is new** (the `${CODEX_HOME}` store: `skills[]`, `skills_shared_with_claude_code[]`,
  `agents[]`, `rules[]`, `hooks[]`, `plugins[]`). **No trigger may read it** — it is de-duplication
  evidence, it is not this repo, and counting it would inflate Q11's N and M (§4.2's failure mode,
  one level up).
- **`mine_transcripts.py` gained a working Codex path** and reports `target` in its output. Its
  `match_mode` — `"none"` / `"cwd"` / `"cwd+git"` on Codex, `"exact"` / `"fuzzy"` / `"basename"` /
  `"none"` on Claude Code — appears **only in the `--resolve-only` report phase 0 reads**, never in
  the full report that becomes `signals.transcripts`. **Never write a trigger against
  `signals.transcripts.match_mode`**: the field does not exist there, and per this section's opening
  line it would never fire and never say so. Everything the bank does read is target-agnostic and
  emitted by the same builder on both targets: `tool_mentions[]` (§4.8 signal 3), `request_shapes[]`,
  `sessions{}`.
- `signals.git.*` is unchanged this round: `contributors[]` rows still carry
  `{name, commits, email_domain, is_bot, bot_reason}`, `window.reason` is still a ready-made
  sentence, and `pr_patterns.available` is still `false` under the `--no-gh` phase 2 runs — no
  trigger reads it, and Q2, the question that once did, is retired (§4.1).

**Answer-dependency audit (§1.11) — every row above re-checked, 2026-09-04.** A trigger that reads
another question's *answer* can never fire, because §1.4 asks everything in one message. Two rows
did, and both are repaired above:

| ID | Read | Now reads |
|---|---|---|

Both of those questions are retired (§4.1). The rows are kept because the *pattern* recurs: any
trigger phrased "ask this if QN answered X" is unreachable, silently, in every run.

**No other trigger in the bank references an answer.** Q3, Q13 and Q16 read the phase-4 candidate
list and phase-3 finding confidences, which are complete before the interview is composed; Q7
reads phase-0 target detection, likewise earlier in the run; every remaining trigger reads
`discovery.json` or `signals.json`. Re-run this audit whenever a trigger is edited, and treat any
new mention of another question's answer inside the trigger column as the defect it is.

Fields that exist and that no trigger reads, deliberately: `meta_queries[]`, `doc_hotspots[]`,
`sessions.social_turns`, `history_bucket`, `cochange_clusters[]`, `revert_rate`,
`directory_hotspots[]`, `authorship{}`, `window{}`. They are phase-3 and phase-4 evidence and they
answer nothing the interview needs to ask — with one exception that is not a trigger: `window.days`
and `window.reason` belong in a `Why:` line whenever it cites a git count, because the window is
chosen per repo (§4.2). `discovery.git.dirty` is the fourth kind: real, and read by `SKILL.md`
phase 7 step 3, which is where the dirty-tree gate lives. A field being new — or unread here — is
not a reason to grow the bank (§1.7).

The Codex fields belong in that same list, and one of them is a fifth kind — read by a later phase,
never by a question. `existing_agentic_config.codex.repo_trust_level` / `.trust_source` /
`.features{}` say whether a generated `.codex/` artifact will load at all, and that belongs in the
plan's capability notes, the report's needs-you list and phase 8 (`adapters/capabilities.md`) —
**not** in the interview. **Do not add a "shall I mark this project trusted?" question**: agentify
never edits `config.toml`, so the answer would change nothing this run can do (§1.7), and the user
has to run `/hooks` and trust the directory in Codex itself either way. Same for
`codex.config_files[]`, `.hook_files[]`, `.hook_scripts[]`, `.skills_root`, `.notes[]` and all of
`user_scope{}`: evidence for phases 3, 4 and 8, and no question's business.

### 4.4 Q3's option text, per target — the answer is the same, the mechanism is not

Q3 is asked on **both** targets. What the user is choosing is identical either way — *does a
generated hook stop the work, or only complain about it* — and it resolves to the same
`hook_strictness` value. Only the contract the built script obeys differs, and because a user who
picks "blocking" is entitled to know what blocking means on their agent, the option text names it.
This block is the authority; the Q3 bank row abbreviates it. **Do not paraphrase the mechanism** —
these are the two decision contracts phase 7 emits and phase 8 tests.

**`claude-code` — verbatim:**

```
→ a) warn only — the hook exits 0 and prints what it found   ← recommended
  b) blocking — the hook exits 2, the tool call does not run, and its stderr
     goes back to me as the instruction to fix it
```

**`codex` — verbatim:**

```
→ a) warn only — the hook exits 0 and prints what it found   ← recommended
  b) blocking — the hook still exits 0 and answers with a "deny" decision, so
     the tool call does not run and the reason comes back to me as the
     instruction to fix it
```

Why the Codex option is not "exit 2": the documented exit-2 path exists on Codex as well, but
`adapters/codex.md` §4.3 emits the JSON form instead — `hookSpecificOutput.permissionDecision:
"deny"` with a `permissionDecisionReason` on stdout and exit **0** — because that is what production
Codex hooks do, it carries a structured reason, and the meaning of other non-zero exits is
undocumented there. Generated Codex hook scripts only ever exit 0. So a cross-target statement of
the form "blocking means a non-zero exit" is true on Claude Code and **false on Codex**; state the
contract, not the exit code, anywhere both targets are in scope — `verification.md` §5.2's
behavioural test included, since a Codex blocking hook that returned non-zero would be the defect,
not the pass.

Two more things travel with this question and neither is a new option:

- **On Codex, blocking does not mean armed.** A generated hook is installed, not active: it needs
  the project marked trusted *and* a one-time approval through Codex's `/hooks` command, and editing
  the hook re-arms that prompt. Say it in one clause on the `Why:` line when it fits — `either way
  the hook is installed, not armed until you trust it in /hooks` — and let the plan's capability
  notes and the report's needs-you list carry the full version (`adapters/capabilities.md`). Never
  word the question so that a `blocking` answer sounds like a hook that is already running. Never
  offer, and never mention, `--dangerously-bypass-hook-trust`.
- **`warn` is a real contract, not a weaker one.** On both targets a warn-mode hook exits 0 and says
  what it found, and on Codex it emits no `deny` decision. A warn hook that returns non-zero — or
  that denies — is a `verification.md` §5.2 **fail**, not a bonus. That is why `a` is the default:
  a hook that blocks ordinary work gets deleted within a day and takes the rest of the setup with
  it.

### 4.5 Q9's docs clause — the old trigger had it exactly backwards

Q9 used to require **three** things, and the third was `the repo has no folder with zone == "docs"`.
Read that as behaviour rather than as a sentence: *ask where to put the plan only when the repo has
no documentation directory; when it already has one, write into it without asking.* That is the
wrong way round on both halves.

- A repo with **no** `docs/` is the safe case. Creating `docs/agentic-setup/` there collides with
  nothing and invents one directory nobody had an opinion about.
- A repo **with** a `docs/` tree is the case that needs the question. That directory is the user's,
  it very often has a build behind it, and agentify's plan is not their documentation.

**Measured, on the h3 run.** `docs/` in that repo is the project's published documentation site.
`docs/agentic-setup/plan.md` and `report.md` went in beside it, and Q9 never appeared — the clause
above suppressed it, and on Codex §3.1 rule 1 had already dropped the whole question because
`ALT_PLAN_DIR` was empty. Two independent gates, both silent, both pointing the same way. Nothing
was overwritten, so the additive invariant held; the user was still never asked whether two generated
files belonged in a tree a static-site generator turns into public pages.

The trigger is now `AGENT_DIR` **or** a docs zone, either one is enough, and the docs arm raises the
priority to `medium` so §3 step 4 does not cut it first.

**Picking Q9's default.**

| Evidence, in this order | Default |
|---|---|
| a `discovery.folders[]` row has `zone == "docs"` | `b) ALT_PLAN_DIR` |
| else — the `AGENT_DIR` arm fired on its own | `a) docs/agentic-setup/` |

The flip is the walk-away test from §1.2, applied honestly. If the user never replies, `b` puts two
markdown files in a dot-directory the run summary names — mildly out of the way, wrong about
nothing. `a` puts them inside a tree the repo may publish. Recoverable either way, but only one of
them can reach somebody else's browser.

**Do not claim the site is published — you cannot see that.** `zone` is a *name* guess: `discover.py`
maps the directory segments `docs`, `doc`, `documentation`, `adr`, `adrs` and `rfcs` to `"docs"`, and
nothing checks for a site generator. That is exactly why this is a question and not a rule. Cite what
you can actually see in the `Why:` line — the row's `path` and its recursive `files` count, both real
fields on `discovery.folders[]` — and let the user supply the fact you lack:

```
Why: docs/ is yours already (412 files); the plan and report are a record of this run, not docs
```

**One directory, said once.** Q9 sets `PLAN_DIR` for `plan.md`, `report.md` and
`build-manifest.json`, and every other `<plan-dir>` path follows it — reference docs on both targets,
plus the MCP draft and long prose rule files on Codex. An answer of `b` therefore also moves the path
the `AGENTS.md` pointer lines cite, so resolve `PLAN_DIR` before phase 6 writes a single one of them.

---

### 4.6 Q14's option text — the engineering system

Verbatim, on both targets. `TARGET_NAME` is the only token in it.

```
→ a) no, none — just build the setup for this repo   ← recommended
  b) yes, one I already have installed — which?
  c) I want one — which? (I'll put the install command in the report; I won't run it for you)
```

**Naming the two by name is deliberate.** Compound engineering and superpowers are the two the user
is most likely to mean, and naming them makes the question answerable in one word instead of
prompting "what do you mean by engineering workflow?". Do not extend the list — a third name turns a
question into a menu, and `b`/`c` are open.

What each answer does, in full:

| Answer | Phase 6 (plan) | Phase 7 (build) | Phase 8 (report) |
|---|---|---|---|
| `a` | nothing — do not mention it | nothing | nothing |
| `b` — installed | one line naming the system, and how the generated rules and skills plug into its workflow | the index-doc stitch gains the workflow section (`blueprint.md` §9 item 2), written from what the user said the system does — **never** from what you assume it does | nothing; it was already there |
| `c` — wanted | one line naming the system and the install step, listed as a **needs-you** item, not a build item | nothing is installed. Generated artifacts must not depend on it | a "needs you" entry with the exact install command for their agent, and a one-line note that the setup works without it |

**Three hard limits.** agentify never installs a marketplace plugin on its own; never adds a
dependency on one to a generated artifact; and never suggests one the user did not name. If they
answer `c` with a name you do not recognise, say so plainly, put their words in the report as the
thing to install, and do not invent a command for it.

### 4.7 Q15 and Q16 — asking for a command without leaking a guess

Both questions exist because `discover.py` refuses to invent a command, and the model must not
invent one on its behalf. Two rules, and they are the whole of it.

**1. Name what was actually found, then ask.** The question quotes the evidence, so the user can
correct the premise rather than just the answer:

```
3. Two lockfiles sit at your repo root — bun.lock and package-lock.json — and package.json
   declares no packageManager. Which one does this repo really use?
   → a) bun   ← recommended
     b) npm
     c) something else — name it
   Why: discovery left commands.install empty on purpose; the enforcement hook below needs
        to know which one to allow and which to block.
```

The default is the manager with the strongest signal, and the `Why:` line says which signal. When
the signals are genuinely equal, default to the one whose lockfile was modified most recently and
say that is why.

**2. For Q16, list only the slots a candidate needs, and never offer a guess as an option.**

```
4. I could not find a format command, and the auto-format hook below needs one. What do you run?
   → a) skip it — build everything else   ← recommended
     b) type the command
   Why: package.json defines no format script; prettier is a devDependency but nothing
        configures it, so I will not assume `prettier --write .`.
```

`a` is the default on Q16 and never `b`, because a wrong command in a hook fires on every write.
A slot left empty drops its dependent candidates, named, under **Skipped (insufficient evidence)** —
it never downgrades into a candidate built against a plausible-looking command.

### 4.8 The three derived answers — `mode`, `services`, `team_size`

Resolved in phase 5 without a question, each stated in **one line of the plan's summary** so the
user can overturn it at the gate. `team_size` is §4.2; the other two are here.

#### `mode` — always `branch`

```
mode        = "branch"  and branch_name = "agentic-setup/<yyyy-mm-dd>"   when discovery.git.is_repo
mode        = "no-git"  (write in place, and say so)                     otherwise
```

No condition raises `stage-only` on its own. **It is still reachable, and the user does not have to
know the word:** any message meaning *don't commit anything* — "just stage it", "leave it
uncommitted", "don't make a branch" — sets `mode = "stage-only"`, at any point up to the first byte
of phase 7, and phase 7 obeys it. `report-template.md` §3.1's stage-only block exists for exactly
that run.

**Why `branch` rather than asking:** it was the default every run took, and it is the safer of the
two by construction — the commit *is* the undo, so `git branch -D` genuinely reverses the run, while
`stage-only`'s undo is a per-file removal list that has to be right file by file. A `must-ask` slot
on every run, spent on a question whose answer was the same every time, is a slot the questions in
§4.7 needed.

Plan line:

```
Everything lands on branch agentic-setup/2026-09-07 and is committed there, so `git branch -D
agentic-setup/2026-09-07` removes the run. Say "stage only" and I will leave the files uncommitted
instead.
```

#### `services` — rank, propose all, most critical first

The retired question asked which services the user touches in a normal week. Rank them instead,
and let the phase 6 gate do the cutting it already does.

**Rank each `discovery.external_services[]` entry on four signals, in this order:**

1. **`confidence`** — `high` over `medium` over `low`. This is `discover.py`'s own score over
   dependency, env-var and marker-file evidence, and it is the strongest single signal.
2. **A module in the repo that calls it.** A `folders[]` or `file_hotspots[]` path naming the
   service, or a framework entry that implies it. A service with code behind it outranks one that
   appears only in a lockfile — this is the §1.1 gate 1 test, applied as a *rank* rather than a gate.
3. **Transcript corroboration** — a `request_shapes[]`, `commands_requested[]` or `slash_commands[]`
   row naming it. **Raises rank; never gates.** `tool_mentions[]` is tier 3 and is a tiebreak only.
4. **Env-var surface** — how many `env_var_names` carry its prefix. Ten `DODO_*` names is a service
   somebody wired up properly; one is a trial.

**Then propose for all of them**, in that order, and say the order out loud. What each service is
eligible for is unchanged and is still gated per artifact type:

| Artifact | Still gated by |
|---|---|
| Skill, subagent | `blueprint.md` §6.1 / §3, plus the four conditions in `mapping-rules.md` §3 — the fourth being the size test, `blueprint.md` §1.4 |
| Rule | the zone or convention actually existing |
| **MCP draft** | `mapping-rules.md` §1.1 — **or** the coupling in `blueprint.md` §7: this run built a skill or subagent for that service. Never on a dependency alone |

Plan line, naming the ordering so the user can re-cut it:

```
Ranked by how much of this repo actually depends on them: PostHog (client module + 4 env names),
Drizzle (schema + migrations), Better Auth, Postgres/Neon, Resend, Dodo (10 env names, no module
yet), fal, Trigger.dev. Items 1 to 5 get artifacts below; drop any of them by number.
```

**Never write "you told me you use X"** in an evidence line or a generated file. Nobody told you
anything. The evidence is the dependency, the module and the env names, and that is what the
`agentify-evidence` line says.

---

## 5. Rendering format — emit exactly this shape

One message. This header, then the questions, then the footer. Nothing else — no preamble about
how important the interview is, no summary of the candidate list (that is the plan's job).

```
## A few things I can't work out from the evidence (N questions)

**Reply `ok` and I'll use every recommendation below.** To change one, just name it —
`2b`, `3 blocking`, or plain English. Anything you don't mention keeps its recommendation.

1. QUESTION TEXT
   → a) OPTION TEXT   ← recommended
     b) OPTION TEXT
   Why: ONE LINE OF EVIDENCE, WITH A COUNT WHERE THERE IS ONE

2. QUESTION TEXT
   → a) OPTION TEXT   ← recommended
     b) OPTION TEXT
     c) OPTION TEXT
   Why: ONE LINE OF EVIDENCE, WITH A COUNT WHERE THERE IS ONE

...

Next: I'll write the full plan to PLAN_DIR/plan.md and wait for your approval before
creating a single file.
```

Formatting rules:

- Numbers are sequential from 1 with no gaps. Options are lettered `a)`, `b)`, `c)`.
- **Exactly one option per question is marked recommended**, with a leading `→ ` on its line and a
  trailing `   ← recommended`. Every other option is indented two spaces so the marked one is the
  line the eye lands on. There is no unmarked question: a question agentify cannot recommend an
  answer to is one it has not finished thinking about (§1.11).
- **Put the recommended option first** unless the option order is itself meaningful
  (`a) warn` before `b) blocking` is an escalation and stays in that order).
- The word is **recommended**, not *default*. `default` describes what happens if the user ignores
  you; `recommended` says you have an opinion and are willing to be overruled — which is the whole
  point of asking in a way that costs one word to answer. `[default]` is the retired marker; do not
  emit it.
- `Why:` is one line, and it cites a real signal — `7 sessions asked for a new endpoint`,
  `stripe + @sentry/node in package.json`, `4 non-bot authors on the default branch over the
  365-day window` (§4.2 — never the raw `--all` count, and name the window `mine_git.py` actually
  chose rather than assuming 180 days). If you cannot
  write a truthful `Why:` line with a real signal behind it, the question does not belong here.
- A genuinely open question still gets a default option `a)` plus an instruction to name what they
  want — Q15's `c) something else` and Q16's `b) type the command` are the two today.
- A `Why:` line may cite a count that §2 bans as a *question* — `at least 4 non-bot authors on the
  default branch over the window I read` is a legitimate reason line, not a request for the number. Never invert that: a question whose text asks for a fact §2 lists is banned however
  good its `Why:` line is.
- No question exceeds two lines of text before its options.
- **Every §3.1 token is rendered to this target's value before the message is sent.** A literal
  `TARGET_NAME`, `INDEX_DOC` or `PERMISSIONS_FILE` reaching the user is a bug; so is the *other*
  target's noun — `CLAUDE.md` in a Codex run's question is the same defect as an unrendered token,
  and harder to spot, because it reads like a sentence. Read the rendered message back once against
  §3.1 before you send it. Q3 takes its options verbatim from §4.4 and Q14 from §4.6, not from the
  token table. `COMMAND_SLOT` in Q16 is not a §3.1 token — it is the literal slot name
  (`format`, `test`, `install`, …), one question line per slot.
- **No question, option or `Why:` line contains the words *cap*, *limit* or *quota*** (§1.8), and
  none offers to open a pull request or to package the setup for other repos (§2, §4.1).
- The closing `Next:` line is mandatory. It is the promise that phase 6 is a gate.

---

## 6. Handling an accept-everything reply

**The one-word path is the point of the whole render (§1.9), so recognise it generously.**
Case-insensitively, with surrounding punctuation and emoji stripped:

| Family | Forms |
|---|---|
| Plain assent | `ok`, `okay`, `k`, `yes`, `y`, `yep`, `yeah`, `sure`, `fine`, `right`, `correct`, `agreed`, `sounds good`, `looks good`, `all good`, `perfect`, `great` |
| The literal word | `defaults`, `default`, `all defaults`, `accept defaults`, `use defaults`, `d`, `recommended`, `your recommendations`, `all recommended`, `take the recommendations` |
| Proceed | `go`, `go ahead`, `proceed`, `continue`, `carry on`, `do it`, `ship it`, `lgtm`, `+1`, `👍` |
| All-yes | `yes to all`, `all yes`, `yes please`, `all of them` |

That list is **not** exhaustive and is not a parser. Any whole reply whose plain meaning is *use
what you suggested* takes this path; when the meaning is genuinely unclear, §7's unparseable rule
applies and you ask that one question again, not all of them.

**`continue` is safe here and at the phase-6 shortlist, and nowhere else.** Both write nothing —
the interview resolves answers, the shortlist (`plan-template.md` §0) confirms a list — so a loose
reading of an accept costs at most a preference the user corrects at the gate. **The plan gate is
the opposite** — `SKILL.md` phase 6 requires an explicit approval of *that plan*, and a stray
`continue` from an earlier message is never it, nor is the `ok` that confirmed the shortlist. Do
not carry this list to the plan gate: only an explicit approval of *that file* builds anything.

When one of those is the **whole** reply:

1. Resolve every question to its recommended option. No follow-up questions. Not even one.
2. Echo the resolved set back in a compact list so the record is explicit, then proceed
   immediately to phase 6:

```
Using my recommendations:
1. QUESTION SHORT LABEL — RESOLVED ANSWER
2. QUESTION SHORT LABEL — RESOLVED ANSWER
...

Writing the plan now.
```

3. Low-confidence findings are **not** included. Q13 recommends no.
4. Hooks are **not** blocking, on either target. Q3 recommends warn-only, and Q3 is asked on
   both targets (§4.4) — while it was skipped on Codex, every Codex hook shipped at this default
   without the question ever being put.
5. **No engineering system is installed.** Q14 recommends `none`, so a one-word accept never
   produces a marketplace install or a dependency on one.
6. **Every command slot the user did not fill stays empty**, and the candidates that needed one are
   dropped, named, under Skipped (insufficient evidence). Q16's default is `skip these`, and that
   is the whole point: a one-word accept must never resolve to a guessed command. Q15 is the
   exception — it recommends a real manager read off a real lockfile, named in the question.
7. A dirty tree is **not** resolved by a one-word accept and is not this phase's business: phase 7
   step 3 refuses to build without an explicit override.
8. **Nothing about accepting the recommendations shrinks the build.** There is no cap to keep and
   no audit-only mode to confirm; a bare `ok` builds the full proposed set minus the low-confidence
   opt-ins.
9. **A one-word accept does not touch the three derived values.** `mode`, `services` and
   `team_size` were never questions, so there is nothing to accept — they stay as §4.2 and §4.8
   derived them, and their plan lines still say how to overturn them.

**Partial replies.** `ok except 3`, `defaults but blocking hooks`, `looks good, use bun`: apply the
recommendations to everything, then the named overrides, then echo the resolved set exactly as
above with the overridden lines marked ` (yours)`. Do not re-ask the rest — an override is an
answer, not an invitation to reopen the round.

**Mixed replies.** `1a, 3 blocking, defaults for the rest`: same handling.

---

## 7. Handling everything else

- **Answered by number/letter** (`1a, 2b, 4 Linear + Sentry`): parse and apply. Unanswered
  questions take their defaults, silently.
- **Answered in prose** (`don't block my commits, and just stage it`): map to options by meaning.
  Echo the resolved set back so a misread is caught before the plan. **A prose reply can also
  overturn a derived value** — anything meaning *don't commit* sets `mode = "stage-only"` (§4.8),
  anything naming the team shape sets `team_size`, and anything naming services reorders them. None
  of those is a question, so none of them needs one to be answered.
- **One answer unparseable:** ask **only** that one, once, restating its options. Everything else
  is already resolved. If the second attempt is still unclear, take the default and say which
  default you took.
- **User answers with a question** (`what would you recommend?`): give the default, in one
  sentence, with the reason, then take the default and move on.
- **User asks to change something not on the list**: accept it, record it as an interview
  answer, and reflect it in the plan. Do not open a new question round.
- **User says stop:** stop. Write nothing.
- **A derived value is never re-asked to confirm it.** `mode`, `services` and `team_size` are stated
  in the plan and overturned there or in prose — putting any of them back as a question is
  reintroducing a retired one (§4.1).

**Then reconcile the answers that depend on other answers.** Triggers cannot read an answer
(§1.11), so the places where one answer overrides another — or settles a noun another question was
composed against — are settled *here*, after the reply and before §8's record is written:

- **Q15's answer fills `discovery.commands.install`** for the rest of the run, and every later
  reference to the install command reads the filled value. If the answer named a manager with no
  lockfile in the repo, take it anyway — the user knows their repo — and note the mismatch in the
  plan in one line.
- **Q16's answers fill their named `commands` slots.** Any slot still empty after the reply drops
  its dependent candidates: move each to **Skipped (insufficient evidence)** with the slot named,
  and say so in the plan. Never carry a candidate forward against a command nobody supplied.
- **Q14 answered `c`** ⇒ the named system is a needs-you item, never a build item (§4.6). Nothing
  in the approved artifact list may depend on it.
- Q7 came back with the target phase-0 detection did **not** provisionally pick ⇒ re-resolve every
  §3.1 token against the answer before the §8 record is written, and say which nouns moved in one
  line: `Building for Codex — so the index doc is AGENTS.md, not CLAUDE.md.` Nothing is re-asked.
  **Q9's answer carries over and only its rendering moves**: `a` is `docs/agentic-setup/` on either
  target, and `b` was asked as `.claude/agentic-setup/ (.codex/agentic-setup/ if you pick Codex
  above)` (§3.1), so a `b` here resolves to `.codex/agentic-setup/` — say the resolved directory in
  the same line, because every other `<plan-dir>` path follows it. Q12 was dropped for this run by
  §3.1's ambiguous-target rule and stays dropped at its `append` default. Q3's, Q14's, Q15's and
  Q16's answers carry over untouched because what they record — block or warn, which engineering
  system, which package manager, which commands — is target-independent. Only the wording was
  provisional.

Nothing else in the bank cross-depends; do not invent further reconciliations.

---

## 8. Output of this phase

Carry forward a resolved answer record. Every field below has a value before phase 6 begins — from
an answer, a default, or a derivation. Phase 6 reads it; phase 7 obeys it; phase 8 reports it.

```
mode           : branch | no-git | stage-only   (**derived**, §4.8 — `branch` whenever
                 `discovery.git.is_repo`, `no-git` otherwise. `stage-only` only when the user
                 says in words not to commit; no question offers it)
branch_name    : agentic-setup/<yyyy-mm-dd>     (when mode is branch)
hook_strictness: warn | blocking            (Q3; asked on **both** targets — the value is
                 target-independent, the contract phase 7 emits from it is not: exit 2 with
                 stderr on Claude Code, exit 0 with a `deny` decision on Codex, §4.4)
services       : [names, most critical first]   (**derived**, §4.8 — every
                 `discovery.external_services[]` entry, ranked. Not a filter: what each service
                 is eligible for is gated per artifact type, and the user drops by number at the
                 phase 6 gate)
team_size      : solo | team-reviewed | team-unreviewed   (**derived**, §4.2 — `solo` when one
                 non-bot author or the top one holds >= 80% of `authorship.commits_human`; else
                 `team-reviewed` with a contributing/pr-template doc; else `team-unreviewed`.
                 The field name is fixed — `SKILL.md` carries the record forward by it. Never a
                 headcount.)
target         : claude-code | codex        (Q7; usually set at phase 0 without asking. It
                 fixes every §3.1 token, so nothing downstream re-derives a path)
plan_dir       : docs/agentic-setup | ALT_PLAN_DIR   (Q9; `ALT_PLAN_DIR` renders to
                 `.claude/agentic-setup` on Claude Code and `.codex/agentic-setup` on Codex,
                 so both values are reachable on both targets. Record the rendered path, not
                 the token — phases 6, 7 and 8 write to it verbatim, and on Codex reference
                 docs, the MCP draft and long prose rule files follow it too)
scope          : root | per-package         (Q10)
index_doc_mode : append | separate-draft    (Q12; the doc is `INDEX_DOC`, so on Codex this is
                 about `AGENTS.md`. When the target's index doc does not exist yet, Q12 is
                 not asked and this stays `append` — phase 7 creates the file)
include_low_conf: true | false              (Q13)
engineering_system: none | {name, installed: true|false}   (Q14; `installed: true` shapes the
                 index-doc stitch, `false` makes it a needs-you item and nothing else. Never
                 a value the user did not say out loud — §4.6)
package_manager: <name> | ""                (Q15, when asked; also written back into
                 `discovery.commands.install` by §7's reconciliation. `""` when Q15 did not
                 fire, in which case `discovery.package_managers` already settled it)
filled_commands: {slot: command, ...}       (Q16; the slots the user supplied. Slots still
                 empty after the reply are absent here and their candidates are dropped)
```

**Three fields are gone and must not be reintroduced:** `open_pr` (agentify never opens a pull
request), `plugin` (there is no plugin manifest artifact) and `caps` / `audit_only` (there are no
caps and no audit-only mode). See §4.1. A downstream file still reading one of them is stale.

**Three fields are derived, and the record does not say which question produced them, because none
did:** `mode`, `services` and `team_size`. Each gets **one line in the plan's summary** stating the
derivation and how to overturn it (§4.2, §4.8). That line is not optional — it is the entire reason
not asking is safe, and a derived value the user cannot see is a decision made behind their back.

State the answer record's material choices in the plan's summary so the user can see what their
answers did, without having to remember what they typed.
