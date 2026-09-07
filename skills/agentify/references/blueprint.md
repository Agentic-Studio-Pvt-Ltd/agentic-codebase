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

### 1.3 The core set — built on every run its licence holds

Some artifacts belong in every serious setup, and their licence is so broad that their *absence* is
the thing that needs explaining. A run is measured against these first. Each is still
evidence-derived — the licence column names the field — but none is ever skipped as "already
covered" by anything except an artifact of the same type, inside this repo, doing the same job
(§2.1), and none is ever skipped for restating the index doc.

| Core artifact | Type | Licence — the field that must be non-empty | Why the usual skip reasons do not apply |
|---|---|---|---|
| **setup-manager** | skill | always | §6.3 |
| **pr-reviewer**, with **review-pr** as its entry point | subagent + skill | `discovery.git.is_repo` | a solo developer reviews their own diff before it lands; `team_size` changes the wording, never the eligibility. A `diff-reviewer` is this artifact under a worse name |
| **qa** | skill | a web framework in `frameworks[]`, or `commands.dev` non-empty | `commands.test` is the unit tests; a browser-driving pass against a running URL is a different job, and no test command covers it |
| **db-inspector**, with **query-db** as its entry point | subagent + skill | a database service or ORM (§3), or a `DATABASE_URL`-shaped env name | a `db:studio` script is a window for a human; the agent's read-only path is this pair. A vendored ORM guide is reference material for it, not a replacement |
| **security-auditor** | subagent | any `.env*` file, or an auth or payments service | — |
| **designer** (`ui-reviewer`), with **new-component** as its entry point | subagent + skill | a UI framework plus a components zone, or a `docs[]` row of kind `design` | an existing `design` skill that *routes* design work does not review a diff against `DESIGN.md` or scaffold a component in this repo's conventions — different jobs |
| **product-analyst**, with **add-product-analytics**, **ask-product** and **build-dashboard** | subagent + skills | an analytics service | a marketplace analytics plugin, at any scope, knows the vendor and not this repo's event names |
| **env-leak blocker**, **destructive-command blocker**, **package-manager enforcer** | hooks | §4.1 | — |
| **permissions** | settings | the target has a permissions surface | — |
| **zone rules** — database, api, web, routes, testing, code-style, security | rules | §5.1, one per zone that exists | the index doc stating the convention is the reason to *scope* the rule to its paths, never the reason to skip it |
| **workflow rules** — branching, commits, project management, decisions, memory, interaction | rules | §5.2 | same |

**The names are the catalogue's names.** `pr-reviewer`, `db-inspector`, `security-auditor`,
`designer`, `product-analyst`, `qa`, `setup-manager`, `create-issue`, `add-product-analytics`,
`ask-product`, `build-dashboard`, `query-db`, `review-pr`. A run does not rename one to signal a
nuance; the nuance goes in the description. The one reason to take the alternate name a row offers
is a collision with a file that already exists at that path (§2.1).

**Skill + subagent pairs are one proposal.** The skill is the human-facing entry point — it gathers
inputs, reads context, formats the output — and delegates the isolated or tool-restricted part to
the subagent. `query-db` reads the question and hands `db-inspector` a read-only job; `review-pr`
fetches the diff and hands `pr-reviewer` the checklist. Two files, one plan entry, one evidence
line. `mapping-rules.md` §2.1's "never both" forbids two artifacts that each do the *whole* job; it
does not forbid a pair.

### 1.4 The size test — a workflow, not a feature

Personalized is not the same as narrow. A skill for something the developer did once, a subagent
for work that fits in the main thread, a rule for one three-file corner — these are noise with a
repo noun in them, and they are the second way a generated setup gets deleted. Before a skill or
subagent goes in the list it passes this, and the shortlist row ends with the number that proves it:

| Artifact | Must show | Read from |
|---|---|---|
| **Skill** | **the procedure recurs**: `>= 3` existing instances of the thing it produces (3 migrations, 15 tasks, 8 capabilities, 5 ADRs), or a `request_shapes[]` row with `count >= 3`, or a service the repo *extends over time* through a module (events, emails, plans, jobs), or a guide the developer wrote — nobody documents a one-off | `folders[].files` and `sample_files`, `request_shapes[]`, `raw_scripts`, `docs[]` |
| **Subagent** | **it earns its context window**: a restricted tool set (read-only db, review-only), a reviewer stance, or a pass over many files — **and** it is a §3 catalogue row or a `request_shapes[]` count `>= 3` backs it. Never invented for one directory | §3, `mapping-rules.md` §2.1 |
| **Rule** | **it governs a zone or a convention**, never one file triple. A co-change cluster inside a zone folds into that zone's rule as a sentence, unless it states something the zone rule cannot | §5.1, `mapping-rules.md` §1.2 |
| **Hook** | **it catches something that would happen here more than once**. A check for a path with two files is a rule sentence, not a hook | §4.1 |

One feature is not a workflow. "Add the resize tool" is a feature; "add a generation capability" —
eight shipped, with a guide — is a workflow. The test is the count of the thing the artifact would
produce or govern, and the plan states it: `13 tasks in trigger/tasks/`, never `the repo uses
Trigger.dev`. A candidate that fails goes to `Skipped (insufficient evidence)` with the count it
had and the count it needed, exactly like a thin transcript row.

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

### 2.1 What covers a candidate — and what never does

"Already covered" is the skip reason that did the most damage on real runs, because almost anything
can be argued to cover almost anything. It has one meaning: **an artifact of the same type, inside
this repo, that does the same job for this repo.** A rule covers a rule. A hook, a CI job or a repo
script covers a hook. A skill covers a skill — and so does one existing repo command when the whole
procedure *is* that command (`mapping-rules.md` A1). A subagent covers a subagent. Nothing crosses
that line.

| This | Covers | Never covers |
|---|---|---|
| The **index doc** (`CLAUDE.md` / `AGENTS.md`) | an index-doc line | a rule, a hook, a skill, a subagent. Prose loaded every session is the *opposite* of a path-scoped rule: the expensive, unenforced form. When the index doc already states a zone's convention, the zone rule quotes that sentence, points at the section, adds what the code shows, and loads lazily on the zone's paths |
| A **vendored** or third-party artifact (`provenance.vendored_artifacts`) | nothing | anything. It is generic by construction — it would read the same in any repo, which is §1.1 test 4 failing. It becomes a **reference** the generated skill links to from the step that needs it (`drizzle-orm-patterns` from the migration step), and the plan names its source |
| A **user-scope** artifact — `existing_agentic_config.user_scope`, `~/.claude/skills`, `${CODEX_HOME}/skills`, a user-scope plugin or MCP server | nothing | anything. It is not in the repo, a teammate does not get it, and it is generic by construction. A same-name collision is a report line — both load; say so — never a skip |
| The team's **own** artifact (`provenance.own`) of the same type | the candidate, **if it passes §1.1 against this repo** | a candidate for a *different* job on a similar topic. Test it, do not trust it: every command it quotes must exist in `raw_scripts`, every path it names must exist in `folders[]`. One that mostly fails is **stale** — list it under `## Existing setup notes` naming the references that do not resolve, keep its name (never overwrite), and say that deleting it and rerunning builds the personalized one |
| A **document** — a guide, a README section, an ADR, `DESIGN.md` | nothing | a skill, a subagent or a hook. A written procedure is the strongest licence a skill can have (§6.2, guide-to-skill), and a written rule is a hook's licence (§4.1, doc-stated check). The document is the artifact's `references/` source, not its replacement |
| A **human GUI** — `db:studio`, a dashboard URL, a hosted console | nothing | an MCP draft or a subagent. `mapping-rules.md` A13 is about the *agent's* loop; a window the developer opens by hand is not the agent's path to the data |
| A **symlinked** or broken artifact | as its type, once | — and it is never edited |

**Name collisions are resolved by naming, never by silence.** A candidate whose catalogue name is
taken by an artifact that does *not* cover it takes the row's alternate name (`db-inspector` →
`db-manager`, `designer` → `ui-reviewer`, `review-pr` → `pr-review`), and the plan says why. A
name taken by an artifact that *does* cover it is the one legitimate `covered by` — with the file
named.

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
| **designer** / **ui-reviewer** | a design system in `frameworks[]` (`Tailwind CSS`, `styled-components`, `Storybook`, `shadcn/ui`) plus a components zone in `folders[]`, or a `docs[]` row of kind `design` | the component directory and its `subdirs` split, the design tokens file, the existing component conventions read off the repo, and the design doc's own rules — including its banned list, which is also a §4.1 doc-stated check. An existing `design` skill that routes design work covers neither this nor `new-component` (§2.1) |
| **product-analyst** | an analytics service (`posthog`, `mixpanel`, `amplitude`, `segment`) | the event names already in the codebase, the analytics client module, and read-only query access. A user-scope analytics plugin covers nothing (§2.1) |
| **test-runner** / **qa** | `commands.test` non-empty **and** `test_discipline.commits_touching_tests_pct` low, or `pain_signals[]` about failing tests | the exact test command, the test directory layout, and how to read this repo's failures |
| **codebase-explorer** | `repo.size_bucket == "large"`, or `folders[]` spanning `>= 5` zones | the zone map — which directory holds what — so it does not rediscover it every time |

Two disciplines:

- **Tool restriction is the point, when the target supports it.** A read-only db subagent with
  write tools is a db subagent with a bug. Claude Code has a per-agent `tools` allowlist; Codex has
  `sandbox_mode` and `mcp_servers` and no direct equivalent — say so in the plan
  (`adapters/capabilities.md`).
- **A subagent that duplicates a skill is one artifact too many.** §2.1 of `mapping-rules.md`
  decides; do not build two artifacts that each do the whole job. A **pair** — an entry-point skill
  delegating to a tool-restricted subagent — is one proposal, not a duplicate (§1.3).
- **Use the catalogue name** (§1.3). `pr-reviewer`, not `diff-reviewer`; `db-inspector`, not
  `database-helper`.

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
| **branch guard** | `signals.git.branch_naming[]` has a pattern with `count >= 5`, or the default branch is protected, **or the index doc names the branch to work on** | `PreToolUse` on the shell tool | the actual branch naming pattern and the default branch name — or the literal sentence from the index doc ("always work on `development`"), quoted. A `branch_naming[]` count below 5 does not override a sentence the developer wrote |
| **doc-stated check** | the repo's own docs state a **mechanically checkable** rule — a forbidden import, class, literal or file, a required helper. Read off the index doc, a `docs[]` row of kind `design` / `style-guide` / `contributing`, or a lint config's gaps | `PostToolUse` on the write/edit tools — a grep over the file just written | the exact strings the doc forbids or requires, quoted, with the doc's path and heading as the evidence. "No raw hex, no `lucide-react`, no `h-screen`" in `DESIGN.md` §7 is three things the model can be reminded of every session, or one hook that catches them at write time — build the hook. **Zero transcript corrections about it is not a reason to skip**: the developer wrote the rule down instead of repeating it |
| **index-doc instruction guard** | an instruction in the user's own index doc that names a **command** or **file** to avoid — "never run `db:push` against staging", "never edit an applied migration" | `PreToolUse` on the shell or edit tool | the literal command or path from the instruction, quoted; the instruction is the evidence |

`hook_strictness` from phase 5 sets block-vs-warn for **all** of them at once. The env-leak and
destructive-command hooks are the two where blocking is the sane default — say so when asking.

The last three rows share one idea, and it is the one runs keep missing: **a rule the developer
wrote into their own docs is evidence of the same tier as a correction they typed three times.**
It licenses a hook when the check is mechanical, and a rule when it is not.

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
| **security** | auth or payments service, or `.env*` present | the env var names, where secrets are read, what never goes client-side (name the framework's own public prefix, e.g. `NEXT_PUBLIC_`), the tenancy check every query makes |
| **routes** | `zone == "routes"` — Next.js `app/` or `pages/`, a Remix / SvelteKit / Nuxt route directory | the route-group layout read off `subdirs` (`(protected)`, `(admin)`), what a page must do before rendering (the session check, the role check), where layouts live, server-vs-client component rules |
| **server actions / jobs** | `zone == "actions"`, or `zone == "jobs"` (`trigger/`, `jobs/`, `workers/`, `queues/`) | the file-per-action or file-per-task convention read off `sample_files`, the validation and auth every one performs, the real run command (`trigger:dev`), what never runs inside one |
| **domain zone** | a depth-1 directory with `zone == null`, `files >= 15`, not a dot-directory, vendor or build output — the repo's own architecture (`server/generation`, `composer`, `actors`, `lib/workflow`) | a convention stateable from **one of**: a README inside it (a `docs[]` row under that path), an index-doc section naming it, a `cochange_clusters[]` row inside it, or a `commit_conventions` scope naming it. None of the four ⇒ no rule, and the walk (§10) says which four were empty |

In a **monorepo** (`monorepo.is_monorepo`), zone rules are **per workspace**: a `web` rule scoped
to `apps/web/**` and an `api` rule scoped to `apps/api/**` are two rules, not one, because their
conventions differ. This is the case where a single merged rule is actively wrong.

**The index doc is never the reason a zone rule is skipped** (§2.1). A 40 KB `CLAUDE.md` with a
"Server discipline" section is a repo whose api rule already has its first sentence written; the
rule quotes it, scopes it to `server/**`, and adds what the code shows that the section does not —
the helper every handler calls, the error shape, the validator. Loaded lazily on those paths it
costs nothing until the zone is touched, which is the opposite of the index doc's cost. The report
may *suggest* that the section could move into the rule; agentify never moves it.

**Sub-zones come from the commit scopes.** `commit_conventions.scopes` — `composer 18`, `voice
15`, `actors 5` — is the developer's own map of the domains inside a zone. Use it to decide whether
an api rule is one rule or one per domain, and to name the sections inside it.

### 5.2 Workflow rules — how this developer works

These come from git and transcripts, not from directories.

| Rule | Fires on | States |
|---|---|---|
| **branching** | `signals.git.branch_naming[]` pattern `count >= 5` | the actual pattern with a real example branch name, the default branch, and how work reaches it |
| **commits** | `commit_conventions.conventional_pct >= 0.6` or `.ticket_prefix_pct >= 0.6` — **or**, below both, any `scopes` vocabulary or an imperative-subject share `>= 0.8` | the real prefix set observed, with counts, and a real example commit subject from this repo. Below the threshold the rule states the convention that *is* observed — "imperative subject, optional `type(scope)`, scopes from {composer, voice, actors}" — never a standard the repo does not follow: the rule describes this repo, it does not prescribe |
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
| `trigger.dev`, `inngest`, `temporal`, `bullmq`, `celery` | **new-background-task** — add a job the way this repo adds one | the task directory and its file-per-task convention (`sample_files`), the real dev and deploy commands (`trigger:dev`, `trigger:deploy`), the retry and idempotency pattern the existing tasks use, the env names the runner needs |
| `openai`, `anthropic`, `openrouter`, `fal`, `replicate`, `gemini`, `elevenlabs` | **add-capability** / **add-model-call** — add a generation or model call the way this repo does | the provider module, the prompt or policy directory, the cost or credit accounting every call passes through, the moderation step, the existing capability the new one is modelled on. When the repo has its own guide for this (§6.2, guide-to-skill), the guide is the spine |
| `dodo`, `lemonsqueezy`, `paddle`, `polar` | same as `stripe` — **billing-change** | the same, plus the product-sync script where one exists (`dodo:sync`) and the entitlement or credit table it feeds |
| `cloudflare` (R2), `aws` (S3), `uploadthing`, `cloudinary` | **add-upload** — only when `>= 2` upload paths exist or a `request_shapes[]` row names uploads; one presign route is a feature, not a workflow (§1.4) | the presign route, the bucket env names, the client-side PUT pattern, the size and type limits already enforced |

Vendored skills in the repo for any of these (`trigger-tasks`, `neon-postgres`, `dodo-best-practices`)
are the generated skill's **references**, linked from the step that needs the vendor's API detail.
They are never the reason the row does not fire (§2.1).

### 6.2 Practice skills — the workflows every serious repo has

These fire on the code, not on a service.

| Skill | Fires on | Personalized with |
|---|---|---|
| **qa** | a web framework in `frameworks[]`, or `commands.dev` non-empty — every web app, not only one with a browser-test framework | a URL parameter, an explicit **stop-and-ask** step when login is required, a goal prompt, this app's real route groups and the role each needs, a fixed findings format with repro steps, and **the browser driver that is actually available**: `agent-browser` when `discovery.tooling.on_path` lists it (the skill's preflight checks for it and names the install command), Playwright when `frameworks[]` has it, otherwise the plan names the driver the user must install before the skill can run. Never "run the tests" — an interactive pass against the running app |
| **design** / **new-component** | a UI framework plus a components zone | the design tokens, the component directory, the primitives already available, and the existing naming convention |
| **new-feature** / **new-endpoint** | `cochange_clusters[]` showing the files that always change together | the actual file set, in order, with the real commands between steps |
| **migration** | an ORM plus a migrations directory | the real create-and-apply commands and the safety checks for this database |
| **review-pr** | `>= 2` non-bot contributors | this run's own rule files as the checklist |
| **debug** / **triage** | `pain_signals[]` clustered on one failure mode | the actual failure, the actual logs to read, the actual fix path |
| **guide-to-skill** | a `docs[]` row of kind `guide`, or a README / index-doc section whose heading is a procedure ("Adding a tool to the composer", "Local Postgres for dev") | the guide's own steps made checkable — the real files, the real commands, a context-gathering step that reads the examples the guide points at — and the guide itself as `references/`. The developer already wrote the procedure; the skill is what makes the agent follow it without being told. **A guide never covers the skill it licenses** (§2.1) |
| **dev-environment** / **seed-local** | `raw_scripts` holds `>= 3` scripts sharing a prefix (`db:seed:*`, `dev:*`) **and** a doc or index-doc comment orders them | the real sequence, in order, the env file each step loads, and the check that proves each step worked |

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

Two things never cover a draft (§2.1): a server configured at **user scope** (`~/.codex/config.toml`,
`~/.claude.json`) — it is not in the repo — and a **human GUI** such as a `db:studio` script, which
is the developer's window and not the agent's loop. A server already declared in the repo's own
`.mcp.json` or `.codex/config.toml` does cover it, once, by name.

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

## 10. The catalogue walk — the table the plan must contain

The coverage check is not a feeling about completeness. It is a table with **one row per catalogue
row above** — every §1.3 core artifact, every §3, §4.1, §5.1, §5.2, §6.1 and §6.2 row — and the
plan carries it as its last section (`plan-template.md`, `## Catalogue walk`). A catalogue row
missing from the table is a bug in the run. A row present with an honest `not licensed — <field>
is empty` is a correct run. This is the mechanism behind "never a silent gap": the run shows its
work, row by row, and the user reads the reasons instead of trusting a count.

| Catalogue row | Trigger field | Found | Outcome |
|---|---|---|---|
| §3 db-inspector | `external_services[]` postgres / neon / drizzle | 3 entries, all `high` | built #13, paired with #11 query-db |
| §3 designer | `frameworks[]` Tailwind CSS + `folders[]` components (390) + `docs[]` DESIGN.md (`design`, 15.9 KB) | fired | built #17 |
| §3 test-runner | `test_discipline.commits_touching_tests_pct` | 0.83 — not low | not licensed — the share is high |
| §6.1 send-notification | `external_services[]` resend | `high`; 1 module, 2 files, no template dir | skipped — steps not readable off the repo (`mapping-rules.md` §3 condition 3) |
| §6.1 ask-product | `external_services[]` posthog | `high`; client module present | built #20 — the user-scope PostHog plugin covers nothing (§2.1) |
| §6.2 qa | `frameworks[]` Next.js; `tooling.on_path` agent-browser | fired | covered by `.claude/skills/qa/SKILL.md` (own; 1 stale path listed in Existing setup notes) |

**Outcome vocabulary, and nothing else:** `built #N`, `not licensed — <field> is <value>`,
`covered by <same-type artifact path in this repo>`, `skipped — <one of coverage.md §1's three
reasons>`, `merged into #N`. "Restates the index doc", "a vendored guide exists", "installed at
user scope" and "the procedure is documented" are not outcomes; a row carrying one is re-walked.

Then read the finished table against these, and fix every "no" before writing the plan:

1. Is every §1.3 core artifact either `built` or `not licensed` with its field named?
2. Is there at least one skill besides `setup-manager`? Zero is a failed walk, not a thin repo.
3. Does every `folders[]` row with a zone, and every domain zone (§5.1), have a rule or a named
   empty field?
4. Does every `external_services[]` entry in the §4.8 ranking have a skill, a subagent, an MCP
   draft or a stated reason? For the tail the reason is usually "no module in the repo calls it
   yet" — say that, naming the service.
5. Does every `docs[]` row of kind `guide` have a skill or a stated reason?
6. Does every mechanically checkable rule in the index doc or a `design` doc have a hook (§4.1)?
7. Is `setup-manager` last among skills, and the index doc last overall (§9)?
8. Does every artifact pass §1.1, and does every evidence line carry a number?
9. Does the plan contain a sentence arguing that fewer artifacts is the better outcome for this
   repo? Delete the sentence and re-walk the rows it was excusing (`mapping-rules.md` A17).
10. Does every skill and subagent pass the size test (§1.4) — its shortlist row ends with the count
    of the thing it produces or the repeat signal behind it, not with a service name?

---

## 11. What this file does not license

- **Padding.** No artifact exists to fill a table row. Ten sharp rules beat ten rules of which four
  are filler, and the difference is visible in §1.1's test 4.
- **Overwriting.** Every invariant in `SKILL.md` still holds: additive, reversible, marker-delimited,
  never a destructive git command, never a secret read.
- **Duplication.** De-duplicate against artifacts of the **same type inside this repo** (§2.1). A
  candidate an own artifact genuinely covers is skipped with that file named. Vendored, user-scope,
  index-doc and document content cover nothing — and a symlinked or vendored artifact is never
  edited.
- **Rationalizing.** A plan that explains why a small setup is the right setup for a large repo
  has stopped walking the catalogue (`mapping-rules.md` A17). The user cuts at the gate; the run
  does not cut for them.
- **Niche artifacts.** A skill for a feature that exists once, a subagent for work that fits in the
  main thread, a rule for a three-file cluster the zone rule already covers (§1.4). The setup
  describes how this developer works, not every corner they have touched — "complete" and "narrow"
  are different failures, and the size test and the walk keep them apart.
- **Guessing a command.** An empty `commands` slot stays empty until `interview.md` Q15 or Q16
  answers it. Never invent one to make a hook or a skill look complete.
- **Asking what you can derive.** `mode`, `services` and `team_size` are derived, not asked
  (`interview.md` §4.2, §4.8), and each is stated in one line of the plan so the user can overturn
  it. A question whose answer is in the JSON, or that the phase 6 gate already settles by number, is
  a retired question being reinvented.

---

## 12. Worked example — what a complete walk produces

The repo the caps were measured on (`coverage.md` §1): Next.js + React + Tailwind + shadcn/ui,
Drizzle on Neon/Postgres, Better Auth, Dodo payments (10 `DODO_*` names), PostHog, Resend,
Trigger.dev (`trigger/` with its own README), R2 uploads, fal and OpenRouter generation under
`server/generation/` (187 files, with `docs/guides/adding-a-capability.md`), a 15.9 KB `DESIGN.md`
with a banned list, `CONTEXT.md`, five ADRs, 61 skill directories of which 48 are vendored, and
**0 rules, 0 hooks, 0 subagents, 0 permissions**. 268k lines, one developer, 30 sessions.

The run that produced 16 artifacts read this as *"knowledge is not the gap, enforcement is"* and
built 3 rules, 6 hooks, 2 skills and 3 subagents. The senior engineer's read is the opposite: 48
vendored library guides are not workflows, a 40 KB index doc loaded every session is the expensive
unscoped form of the rules that do not exist yet, and every service on the list has a workflow the
developer runs through the agent. The complete walk produces, in build order:

- **Rules (12):** database (`db/**`), migrations, api (`server/**`, quoting "Server discipline"),
  routes (`app/**` — the `(protected)` / `(admin)` / `(workspace)` groups and the session check),
  web (`components/**`, quoting `DESIGN.md`), server actions (`actions/**`), jobs (`trigger/**`,
  from its README), generation (`server/generation/**`, a domain zone with a guide), testing
  (Vitest, `*.test.ts` beside the source), security (env names, the `NEXT_PUBLIC_` boundary,
  tenancy), decisions (`docs/adr/`, numbered), memory (`CONTEXT.md` is a glossary — what goes
  there and what does not), commits (the observed scope vocabulary, stated as observed).
- **Hooks (8):** env-leak blocker, destructive-command blocker (`db:reset`, `db:push:production`,
  `git push --force`), package-manager enforcer (after Q15), lint-on-write, typecheck-on-stop, a
  money-path test gate (`server/billing/**`), a `DESIGN.md` doc-stated check (raw hex,
  `lucide-react`, `h-screen`), and a branch guard from the index doc's own "always work on
  `development`".
- **Permissions (1):** the five real commands allowed; `.env*` reads and the destructive scripts denied.
- **Skills (13):** query-db, migration, add-capability (from the guide), new-background-task,
  billing-change, add-product-analytics, ask-product, build-dashboard, new-component, review-pr,
  seed-local (`db:push:local` → `db:seed` → `db:seed:catalog`, ordered by the index doc's own
  comment), qa — **covered** here by the developer's own `qa` skill, with its one stale path
  listed — and setup-manager last.
- **Subagents (6):** db-inspector, pr-reviewer, security-auditor, designer, product-analyst,
  codebase-explorer (large repo; the zone map lives in its prompt, which is not the same as the
  map living in the index doc).
- **MCP drafts (2):** PostHog and Neon, each paired with its skill; Trigger.dev already declared in
  `.mcp.json`, so covered.
- **Index doc (1)**, plus two report suggestions that are not artifacts: the three index-doc
  sections that are zone-specific and would be cheaper as path-scoped rules, and the `AGENTS.md`
  chain sitting 2 KB under Codex's `project_doc_max_bytes`.

Around forty artifacts, every one with a field and a number behind it, not one that would be true
in a different repo, and not one for a single feature — each skill row on the shortlist ends with
the count of the thing it produces (`15 tasks`, `8 capabilities`, `25 migrations`, `5 ADRs`). That is what "complete" means when the evidence is this rich — a
calibration, not a target to pad toward: a 4k-line CLI with no services gets six.
