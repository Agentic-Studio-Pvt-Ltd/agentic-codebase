# blueprint.md — what a complete personalized setup contains

Read this in **phase 4 (Propose)**, immediately after `mapping-rules.md` and before
`coverage.md`. `mapping-rules.md` answers *"does this finding justify an artifact?"*.
This file answers the two questions that one cannot:

1. **What does a finished setup for THIS repo look like?** — the coverage question. A run that
   maps three findings to three rules and stops has not built a setup; it has built three rules.
2. **What makes an artifact personalized rather than generic?** — the quality question. A skill
   that would read identically in any Next.js repo is a template, and templates are the thing this
   product exists not to ship.

---

## 1. The standard this run is held to

The user is not buying findings. They are buying the setup a senior engineer would have built by
hand after a week inside their codebase. That engineer does not ask permission to add a rule for
the database layer when the repo obviously has one. They read the code, read the developer's
history with the agent, and build the whole thing.

So: **propose the complete setup, then let the user cut it in the interview and at the phase 6
gate.** There is no ceiling on artifact count. There never was a good reason for one — a setup with
nine sharp rules covering nine real zones is better than four, and the two gates that protect the
user from sprawl are the evidence requirement (§2) and their own approval, not an arbitrary number.

**Never tell the user a cap or a limit stopped you.** If something is not built it is because the
evidence is not there, and the plan says which number was missing.

### 1.1 The five things that make it feel personalized

Every generated file is checked against all five before it goes in the plan. A file that fails any
of them is rewritten, not shipped.

| # | Test | Fails when |
|---|---|---|
| 1 | **Names this repo's nouns.** At least **3** concrete identifiers from `discovery.json` or `signals.json` — a directory, a table, a script name, a framework, a service, a file path | "keep components small" |
| 2 | **States this repo's convention, not a best practice.** The convention is read off the repo — the commit style it actually uses, the ORM it actually has, the test runner in `commands.test` | "use conventional commits" when `conventional_pct` is 0.2 |
| 3 | **Cites its evidence.** The `agentify-evidence` line names a field and a number | evidence line is prose |
| 4 | **Would be wrong in a different repo.** If you could paste the file into an unrelated project and it would still be true, it is generic | "write tests for new code" |
| 5 | **Answers something the developer actually hit.** Preferably a `request_shapes[]`, `corrections[]` or `pain_signals[]` row; structurally, a gap the code proves | invented from the framework's docs |

Test 4 is the sharp one. Apply it literally: name the repo you would have to paste it into for it
to become false. If you cannot name one, the file is generic.

### 1.2 Where the personalization comes from

Two sources, and both must be used:

- **The code** (`discovery.json`) — what exists. Directories, frameworks, services, commands,
  manifests, docs, monorepo layout. This licenses an artifact and supplies its nouns.
- **The history** (`signals.json`) — what happened. What the developer asked for repeatedly, what
  they corrected, where they got stuck, which commands they ran, which files they kept pointing at.
  This sets priority, supplies the wording, and is what makes a rule read like it was written by
  someone who watched them work.

A structural fact alone is enough to **build**. A transcript signal is what makes it **sharp**.
When both are present, the artifact leads with the transcript evidence.

---

## 2. Evidence, restated for structural facts

`mapping-rules.md` §0.1 stands: **a candidate with no counted evidence maps to nothing.** This file
does not weaken that. It makes explicit what has always been true — that a structural fact carries
a count too, and that count is a fact about the repo:

| Kind of evidence | Example | The number |
|---|---|---|
| Behavioural | `request_shapes[]` row | `count`, `sessions` |
| Structural | a service in `external_services[]` | the count of evidence strings, and its `confidence` |
| Structural | a zone in `folders[]` | its `files` count |
| Structural | a framework | the manifest entry that declares it |
| Structural | an absence | `existing_agentic_config.counts.hooks == 0` with `.env*` files present |

The last row is the one runs keep missing. **An absence is evidence.** A 268k-line repo with a
`.env.local` on disk, zero hooks and zero rules has a guardrail gap that is a measured fact, not a
guess, and the fix does not need a transcript to justify it.

What is still forbidden: an artifact whose trigger fired on nothing you can name. Every row in
every catalogue below names the field and the test. Cite it. If the field is empty, the row does
not fire.

---

## 3. Subagents — the specialists

A subagent is warranted when the work needs **its own context window**, a **restricted tool set**,
or a **persona that would pollute the main thread**. Read `mapping-rules.md` §2.1 for skill-vs-
subagent; this table is what to look for, and what each one must contain to pass §1.1.

| Subagent | Fires on | Must contain, from this repo |
|---|---|---|
| **db-inspector** / **db-manager** | a database service in `external_services[]` (`postgres`, `neon`, `supabase`, `planetscale`, `mongodb`, `redis`) or an ORM in `frameworks[]` (`Prisma`, `Drizzle ORM`, `SQLAlchemy`, `TypeORM`) | the schema directory, the migration directory and command, the ORM's own query idiom, and a **read-only tool allowlist** when the agent supports one. Name the tables or schema files it may read |
| **pr-reviewer** | `>= 2` non-bot rows in `signals.git.contributors[]`, or a `contributing`/`pr-template` doc in `docs[]`, or `pain_signals[]` about review. **Fires on a `solo` repo too** — reviewing your own diff before it lands is the commonest use; `team_size` changes its wording, never its eligibility | the repo's own rules as the review checklist — every rule file this run builds, by path — plus the commit convention and the test command it must confirm ran |
| **security-auditor** | any of: `.env*` files present, an auth service in `external_services[]` (`better-auth`, `clerk`, `auth0`, `next-auth`), a payments service (`stripe`, `revenuecat`), or `env_var_names` naming secrets | the actual env var names (names only, never values), the auth entry points, and the specific classes of leak this stack allows |
| **designer** / **ui-reviewer** | a design system in `frameworks[]` (`Tailwind CSS`, `styled-components`, `Storybook`) plus a components zone in `folders[]`, or a `DESIGN.md`-shaped doc | the component directory, the design tokens file, the existing component conventions read off the repo, and the design doc's own rules |
| **product-analyst** | an analytics service (`posthog`, `mixpanel`, `amplitude`, `segment`) | the event names already in the codebase, the analytics client module, and read-only query access |
| **test-runner** / **qa** | `commands.test` non-empty **and** `test_discipline.commits_touching_tests_pct` low, or `pain_signals[]` about failing tests | the exact test command, the test directory layout, and how to read this repo's failures |
| **codebase-explorer** | `repo.size_bucket == "large"`, or `folders[]` spanning `>= 5` zones | the zone map — which directory holds what — so it does not rediscover it every time |

Two disciplines:

- **Tool restriction is the point, when the target supports it.** A read-only db subagent with
  write tools is a db subagent with a bug. Claude Code has a per-agent `tools` allowlist; Codex has
  `sandbox_mode` and `mcp_servers` and no direct equivalent — say so in the plan
  (`adapters/capabilities.md`).
- **A subagent that duplicates a skill is one artifact too many.** §2.1 of `mapping-rules.md`
  decides; do not build both for the same job.

---

## 4. Hooks and permissions — the guardrails

Hooks are the highest-value artifact per line written, and the one most runs under-build. **Zero
hooks in a repo with a `.env` file and a package manager is a finding, not a neutral state.**

### 4.1 The guardrail catalogue

| Hook | Fires on | Event / matcher | Must contain, from this repo |
|---|---|---|---|
| **env-leak blocker** | any `.env*` file in the repo, or `env_var_names` non-empty | `PreToolUse` on the read/edit tools | the exact `.env*` filenames present, plus any credential paths this stack uses. **Deny reads of the file, allow `.env.example`** |
| **destructive-command blocker** | always, when hooks are supported | `PreToolUse` on the shell tool | the destructive commands that would actually hurt **this** repo: the migration reset command for its ORM, its deploy command, `git push --force` against its default branch, `rm -rf` of its build dirs |
| **package-manager enforcer** | `len(package_managers) >= 1`; **required** when `discovery.warnings` reports an ambiguous or mismatched manager | `PreToolUse` on the shell tool | the chosen manager and the ones to block, by name. On riffads-shaped repos (`bun.lock` **and** `package-lock.json`) this is the single highest-value hook, and phase 5 asks which manager wins |
| **auto-format / auto-lint** | `commands.format` or `commands.lint` non-empty | `PostToolUse` on the write/edit tools | the exact command, scoped to the file just written, with the repo's own config file |
| **typecheck on write** | `commands.typecheck` non-empty and no CI job runs it (`ci[]`) | `PostToolUse` or `Stop` | the exact command; time-box it, since it is the slow one |
| **test-on-stop** | `commands.test` non-empty **and** `test_discipline.commits_touching_tests_pct` is low or a `pain_signals[]` row names a test that broke after a change | `Stop` | the exact command and which subset to run. Time-box it; propose it at `warn` unless `hook_strictness` says otherwise |
| **secret-scan before commit** | a payments/auth/cloud service in `external_services[]` | `PreToolUse` on the shell tool, matching `git commit` | the secret patterns this stack produces — the env prefixes in `env_var_names`, nothing invented |
| **branch guard** | `signals.git.branch_naming[]` has a pattern with `count >= 5`, or the default branch is protected | `PreToolUse` on the shell tool | the actual branch naming pattern, and the default branch name |

`hook_strictness` from phase 5 sets block-vs-warn for **all** of them at once. The env-leak and
destructive-command hooks are the two where blocking is the sane default — say so when asking.

### 4.2 Permissions — the allow/deny lists

A permissions block is **not** a hook and is not covered by the hook catalogue. It is the cheapest
guardrail in the product and most runs skip it entirely.

Fires when: the target supports a permissions block **and** `discovery.commands` has `>= 2`
populated slots. Build it as part of the settings artifact.

- **Allow** the repo's own verified commands — the populated `commands` slots, quoted from
  `raw_scripts["#commands"]` — plus the read-only git and inspection commands the agent uses
  constantly. Every allow entry removes a permission prompt the developer is answering by hand today.
- **Deny** what the hooks block, restated declaratively: reads of the `.env*` files by name, the
  wrong package managers, the destructive commands from §4.1.
- **Never** allow a command that was not found in the repo. Never deny something the developer's
  own transcripts show them running successfully.

The adapter owns the file and the key names. Never write a permissions block without reading it.

---

## 5. Rules — the conventions

Rules are how the setup stops repeating itself. The mistake to avoid is **one giant rule file**:
a rule earns its file by having a scope, and a scope is a path glob.

### 5.1 Zone rules — one per real zone

Take `discovery.folders[]` and its `zone` field, corroborated by `signals.git.directory_hotspots[]`
and `cochange_clusters[]`. Build one rule per zone that is real in this repo — real meaning the
directory exists, holds files, and has a convention you can state from evidence.

| Zone rule | Zone signal | States |
|---|---|---|
| **database** | `zone == "db"`, an ORM framework, a migrations directory | the schema file, how a migration is created and applied (the real command), the naming convention in the existing migration filenames, what never to do (hand-edit an applied migration, reset in a shared environment) |
| **api** | `zone == "api"` | the route layout, the validation library (`Zod`, `Pydantic`), the error shape used by existing handlers, the auth check every route makes |
| **web** / **frontend** | `zone == "components"`, `zone == "web"`, a UI framework | the component directory split, the styling system, server-vs-client component rules where the framework has them, the shared UI primitives directory |
| **testing** | `commands.test` non-empty | the runner, the file naming convention read off the repo, where tests live, what `test_discipline` says about the current bar |
| **code style** | a linter/formatter in `frameworks[]` | the config file, the command, and only the conventions the config does **not** already enforce — never restate ESLint's own rules |
| **security** | auth or payments service, or `.env*` present | the env var names, where secrets are read, what never goes client-side (name the framework's own public prefix, e.g. `NEXT_PUBLIC_`) |

In a **monorepo** (`monorepo.is_monorepo`), zone rules are **per workspace**: a `web` rule scoped
to `apps/web/**` and an `api` rule scoped to `apps/api/**` are two rules, not one, because their
conventions differ. This is the case where a single merged rule is actively wrong.

### 5.2 Workflow rules — how this developer works

These come from git and transcripts, not from directories.

| Rule | Fires on | States |
|---|---|---|
| **branching** | `signals.git.branch_naming[]` pattern `count >= 5` | the actual pattern with a real example branch name, the default branch, and how work reaches it |
| **commits** | `commit_conventions.conventional_pct >= 0.6` or `.ticket_prefix_pct >= 0.6` | the real prefix set observed, with counts, and a real example commit subject from this repo |
| **project management** | a tracker in `external_services[]` (`linear`, `jira`, `notion`, `github`), or a ticket prefix in `commit_conventions` | the tracker, the ticket-id format seen in commits, when an issue is opened, what belongs in it — the `linear-workflow.md`-shaped rule |
| **decision recording** | `docs[]` holds an `adr` kind, or `doc_hotspots[]` names a decisions/architecture doc | the doc's real path, its existing numbering, and when a decision belongs there rather than in a commit message |
| **memory / context recording** | `meta_queries[]` non-empty, or a `CONTEXT.md`-shaped doc | where running context is kept and what gets written back after a session |
| **interaction** | `corrections[]` clustered on style of response | the corrections themselves, generalized — how much to explain, when to ask, what to never do again |

`corrections[]` is the most under-used list in the product. Every repeated correction is a rule the
developer has already written for you, in their own words. Quote them.

---

## 6. Skills — the workflows

**A run that builds zero skills has almost certainly failed.** Skills are the artifact the user
came for: the repeated multi-step procedure, captured once, with the repo's own conventions baked
in. If the candidate list has no skills, go back to §6.1 and §6.2 before writing the plan.

### 6.1 Integration skills — one workflow per service the repo actually uses

**Services are ranked, never filtered by a question** (`interview.md` §4.8). Walk every
`discovery.external_services[]` entry in that ranked order — most critical first — and for each ask:
**what does the developer do with it, through the agent, more than once?** The service being present
with a module behind it is the licence; the workflow is the skill. The user drops what they do not
want at the phase 6 gate, by number.

| Service | Skill shape | Personalized with |
|---|---|---|
| `linear`, `jira` | **create-issue** — turn a description into a properly-formed ticket | the team's label and project names where discoverable, the ticket template, the repo's own definition-of-done, and a context-gathering step that reads the codebase before writing the issue |
| `posthog`, `mixpanel`, `amplitude`, `segment` | **add-product-analytics** — instrument a feature | the analytics client module in this repo, the existing event-naming convention read off the code, and the product's own KPIs where a doc states them |
| same | **ask-product** — answer a question with a **read-only** query | the project's real event names, and a hard read-only constraint |
| same | **build-dashboard** — assemble a view from events already in the code | the events this repo emits, by name |
| `neon`, `postgres`, `supabase`, `planetscale` | **query-db** — answer a data question, read-only, delegating to the db subagent (§3) | the schema, the connection env var **name**, and a read-only tool restriction |
| `stripe`, `revenuecat` | **billing-change** — add or change a plan, price or entitlement | the pricing model in the code, the webhook handler path, the test-mode workflow |
| `resend`, `sendgrid`, `twilio` | **send-notification** — add a transactional message | the template directory, the sending module, the existing message tone |
| `sentry`, `datadog` | **triage-error** — take an error and produce a diagnosis | the release/environment tagging this repo uses, and the source-map or symbol setup |
| `vercel`, `netlify`, `cloudflare`, `aws` | **ship** — the real deploy path | the actual deploy command, preview-vs-production, the env vars each stage needs, by name |
| `github` | **pr-review**, **release-notes** | the repo's own rules as the checklist, the commit convention for the notes |

### 6.2 Practice skills — the workflows every serious repo has

These fire on the code, not on a service.

| Skill | Fires on | Personalized with |
|---|---|---|
| **qa** | a browser-testing framework (`playwright`, `cypress`) or a web framework plus a dev command | a URL parameter, an explicit **stop-and-ask** step when login is required, a goal prompt, the app's real routes, and a fixed output format for findings. Not "run the tests" — an interactive QA procedure |
| **design** / **new-component** | a UI framework plus a components zone | the design tokens, the component directory, the primitives already available, and the existing naming convention |
| **new-feature** / **new-endpoint** | `cochange_clusters[]` showing the files that always change together | the actual file set, in order, with the real commands between steps |
| **migration** | an ORM plus a migrations directory | the real create-and-apply commands and the safety checks for this database |
| **review-pr** | `>= 2` non-bot contributors | this run's own rule files as the checklist |
| **debug** / **triage** | `pain_signals[]` clustered on one failure mode | the actual failure, the actual logs to read, the actual fix path |

### 6.3 `setup-manager` — build this one on every run

**This is the skill that keeps the rest alive, and it is not optional.** Everything this run
generates will need changing: a rule goes stale, a hook is too strict, a new service arrives. The
developer should not have to learn the config formats to do that.

`setup-manager` is a skill that knows how **this target's** configuration works and can create,
extend, modify, audit and remove any part of the setup on request.

It must contain, concretely:

- **The target's real config surface**, from the adapter: every path, every file format, every
  frontmatter key, the hook events and their matcher shapes, where subagents live, where skills
  live, how permissions are expressed, how MCP servers are declared.
- **An inventory of what agentify built here** — every generated file, its path, its `agentify-id`,
  and what it governs. This is the map the developer edits from.
- **The editing procedures**: add a rule, add a skill, add a subagent, add or loosen a hook, change
  the permission lists, register an MCP server, remove one artifact cleanly.
- **The invariants**: additive changes only, never delete the user's own instructions, keep the
  index-doc tables in sync with the files, one artifact per file, and re-verify after editing.
- **The verification step** — how to check a change actually loaded, per artifact type.

Evidence: it is licensed by the setup itself. Its evidence line names the count of artifacts this
run built. Build it **last among skills**, so its inventory is complete.

---

## 7. MCP drafts

`mapping-rules.md` §1.1 owns the gate — a draft is written only for a service the user confirms
they work against **through the agent**. What this file adds: when a skill from §6.1 exists for a
service, the MCP draft and the skill are **one proposal**, planned together and stated together,
because the skill is what makes the server useful and the server is what makes the skill work.

Drafts only. Env-var **names** only. Never a credential, never an authentication step performed for
the user — that is a "needs you" item in the report.

---

## 8. The engineering system — ask, then install what they name

Some developers already run a packaged engineering workflow on top of the agent — Every's
**compound engineering**, Obra's **superpowers**, or another marketplace plugin. If they do, the
setup this run builds must sit inside it rather than beside it.

This is the one question in the interview that evidence cannot answer, so **ask it** (`interview.md`
Q14). Behaviour:

- **They name one that is already installed** → do not install anything. Read its workflow, and
  make this run's artifacts fit it: the index-doc stitch (§9) gets a section describing the
  workflow and where the generated rules and skills plug into it.
- **They name one they want** → agentify does **not** install it silently. It is a network action
  against a marketplace, so it goes in the plan as a named step and in the report's "needs you"
  list with the exact command. Offer to run it once the user has approved the plan, and only then.
- **They name none** → build nothing for this, and do not editorialize about it.

Never install a plugin that was not named by the user. Never make the generated setup depend on one.

---

## 9. The stitch — the index doc is the last thing written

Everything above is inert until the index doc points at it. This is the step that turns a pile of
files into a setup, and it is **the last artifact built**, not the first, because its tables
enumerate what was actually written.

The generated section carries, in this order, dropping any block whose artifact type was not built:

1. **One paragraph** saying what this setup is, when it was generated, and where the plan and
   report live.
2. **The workflow section** — if §8 named an engineering system, how it runs here; otherwise the
   repo's own branch, commit and review flow, stated from `signals.git`.
3. **Subagents table** — name, one-or-two-line description, trigger, when to delegate.
4. **Skills table** — name, description, how to invoke.
5. **Rules table** — rule name, file path, scope glob, what it governs.
6. **Hooks and permissions** — what fires, on what event, and where it is wired.
7. **MCP servers** — declared, and which still need authentication.
8. **Interaction rules** — the handful of corrections-derived directives about how to work with
   this developer, from §5.2.
9. **Removal instructions**, then the attribution footer.

**The additive law, restated because this is where it gets broken:** the user's own index doc is
theirs. Never delete, reword, reorder, summarize or "clean up" a line of it. Everything agentify
writes lives inside the `agentify:begin`/`agentify:end` span and nowhere else. If their existing
text contradicts a generated rule, say so in `report.md` and let them decide — do not fix their
prose. If the doc is large enough that appending is risky (Codex's `project_doc_max_bytes`), phase
5 already asked; follow that answer.

---

## 10. Coverage check — run this before writing the plan

Walk it once. Every "no" is either a fixed omission or a line in the plan saying which field was
empty. Never a silent gap.

| # | Question | If no |
|---|---|---|
| 1 | Is there **at least one skill**? | Re-read §6.1 and §6.2 against `external_services[]` and `commands`. Zero skills needs an explicit sentence in the plan naming what was missing |
| 2 | Is `setup-manager` in the list? | Add it (§6.3). It is unconditional |
| 3 | Does every zone in `folders[]` with a real `zone` value have a rule, or a stated reason it does not? | Add the rule, or state the reason |
| 4 | If `.env*` exists, is there an env-leak guardrail? | Add it (§4.1) |
| 5 | If a package manager is ambiguous or mismatched, is there an enforcer? | Add it (§4.1) |
| 6 | Is there a permissions block? | Add it (§4.2), or state that the target has none |
| 7 | Does every service in the §4.8 ranking have **either** a skill, a subagent, an MCP draft, or a stated reason? | Close the gap or state it. Working down the ranking, the reason for the tail is usually "no module in the repo calls it yet" — say that, naming the service |
| 8 | Is the index-doc stitch last in the build order, with a table per built type? | Reorder (§9) |
| 9 | Does every artifact pass all five personalization tests (§1.1)? | Rewrite the ones that do not — do not ship a generic file |
| 10 | Does the plan name a number for every artifact, and no cap for any of them? | Fix the plan. The word "cap" does not appear in agentify's output |

---

## 11. What this file does not license

- **Padding.** No artifact exists to fill a table row. Ten sharp rules beat ten rules of which four
  are filler, and the difference is visible in §1.1's test 4.
- **Overwriting.** Every invariant in `SKILL.md` still holds: additive, reversible, marker-delimited,
  never a destructive git command, never a secret read.
- **Duplication.** De-duplicate against `existing_agentic_config` — including vendored and
  symlinked artifacts, which cover their subject just as well as one the team wrote
  (`mapping-rules.md` anti-pattern A9). A candidate that overlaps an existing artifact is skipped
  with the existing file named.
- **Guessing a command.** An empty `commands` slot stays empty until `interview.md` Q15 or Q16
  answers it. Never invent one to make a hook or a skill look complete.
- **Asking what you can derive.** `mode`, `services` and `team_size` are derived, not asked
  (`interview.md` §4.2, §4.8), and each is stated in one line of the plan so the user can overturn
  it. A question whose answer is in the JSON, or that the phase 6 gate already settles by number, is
  a retired question being reinvented.
