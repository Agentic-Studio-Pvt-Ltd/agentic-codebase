# privacy.md — phase 0 consent script and privacy statement

Read this file in **phase 0 (Preflight) only**. It tells you what to say to the user, how to
record their answer, and how the rest of the run changes based on it.

You are the one reading transcripts by proxy. Consent is not a formality and it is not
remembered between runs. Ask every single run, even if the user said yes yesterday.

---

## 1. When to ask

Ask **after** you have detected the repo root and the target agent, and **before** you run
`mine_transcripts.py` for content. Never mine a transcript before the user has answered.

### First, resolve the directory you are asking about

Asking someone to consent to a directory nobody has named is a worse consent flow than naming it.
So run the resolver first. It locates the transcript directory, counts the session files and reads
their date range from file metadata — and **exits before parsing a single turn**:

```bash
python3 "$SKILL_DIR/scripts/mine_transcripts.py" --repo "$REPO_ROOT" --target "$TARGET" \
  --resolve-only
```

It returns `transcript_root`, `match_mode`, `sessions` (`files`, `count`, `first`, `last`,
`bytes_total`), `history_bucket`, and `warnings`. No user turn, no assistant turn, no tool output is
read; on Codex it reads only each rollout's `session_meta` record, which is how the tree gets scoped
to this repo at all.

**`match_mode` is target-specific, because the two targets store sessions in different shapes.** The
value tells the user how confident the association is, so it has to be reported honestly, and there
is no shared value between the two lists but `none`:

| `match_mode` | Target | What it means |
|---|---|---|
| `exact` | Claude Code | one project directory whose encoded name **is** this repo's path |
| `fuzzy` | Claude Code | the closest-scoring directory, not an exact name match |
| `basename` | Claude Code | matched on the last path segment alone |
| `cwd+git` | **Codex** | rollouts kept because their `session_meta.cwd` is this repo (or a directory inside it) **or** their `session_meta.git.repository_url` is this repo's remote — the normal Codex answer whenever the repo has a remote configured |
| `cwd` | **Codex** | the same, minus the remote half: this repo has no git remote to match on, so only `cwd` selected the rollouts |
| `none` | both | nothing matched — no directory, or no rollout belonging to this repo |

Codex has **no per-project directory**: every repo's sessions live in one date-partitioned tree under
`${CODEX_HOME}/sessions/` (plus `archived_sessions/`, which archiving *moves* rollouts into, so the
two cannot double-count). Association is therefore computed, not read off a directory name — see the
consent script's `{HOW_LOCATED}` line, which says this to the user in their own terms before they
answer.

Three things this buys, all of which matter before a yes:

1. `{TRANSCRIPT_ROOT}` in the script below is a real path, not a promise.
2. The user sees the **volume** — file count and date range — so "read my sessions" has a size.
3. A `match_mode` the user should question surfaces **here**, at consent time, and each target has
   its own. **Claude Code `fuzzy` or `basename`:** `That directory was matched by <mode>, so it may
   hold sessions from a different checkout — tell me if that is not this project.` **Codex
   `cwd+git`:** `Some of these sessions were matched by your git remote rather than by directory, so
   they may include work you did from another checkout or worktree of this repo — tell me if you
   want those left out.` (That half is not a rounding error: on one measured repository 2 sessions
   matched by path and 39 by remote.) **Codex `cwd`:** say that this repo has no remote, so only
   sessions started inside this directory were found and work done from a worktree is missing.
   Consenting to the wrong sessions is the one privacy mistake this flow can still make, and it is
   the user's call, not yours.

If it exits 1, or returns `transcript_root: ""`, ask anyway with the not-found wording in the
substitution table. `sessions.count` from this run is a **file** count and an upper bound; phase 2
recomputes the real one. Do not carry `history_bucket` from here into phase 4.

`discover.py` and `mine_git.py` do **not** require this consent — they read only the repo
working tree and local git metadata, both of which the user already handed you by invoking the
skill in this directory. Say so, so the user understands exactly what the yes/no covers.

---

## 2. The consent script — read this verbatim

Print this block exactly. Do not paraphrase it, do not shorten it, do not add emoji. Substitute
only the bracketed values, all of which you already have from phase 0 detection and the
`--resolve-only` run above.

```
Before I go further I need your permission for one thing.

To find the work you repeat, I want to read your local Claude Code / Codex session
files for THIS repo only: {TRANSCRIPT_ROOT}

That is {SESSION_VOLUME}.

What I read:      your prompts (user turns) only, from sessions tied to {REPO_ROOT}
How I found them: {HOW_LOCATED}
What I skip:      my own replies, tool output, subagent traffic, other repos' sessions
What happens:     a local script clusters your prompts into counts and shapes, and
                  scrubs secrets (keys, tokens, JWTs, connection strings, emails,
                  your home path) BEFORE anything is written down or shown to you
Where it goes:    nowhere. No network calls, no telemetry, no files outside this repo.
                  Only the scrubbed ~3k-token summary enters this conversation.

Your options:
→ 1. yes                 read all available sessions for this repo   ← recommended
  2. no                  skip transcripts entirely; I will work from
                         the code and git history only
  3. last N days         e.g. "last 30 days" — read only sessions in that window

I recommend 1: without it I am working from the code alone, which finds your
guardrail gaps but not the work you repeat. Say "no" and the run still works.

I never read .env values, credential files, private keys, or anything matching a
secret filename pattern — not in this phase and not in any other.

Reply "1" or "ok" to go ahead, "no" to skip, or name a window.
```

**Substitutions**

| Token | Source |
|---|---|
| `{TRANSCRIPT_ROOT}` | `transcript_root` from the `--resolve-only` run. When it is empty or the run exited 1, print `not found — there may be no recorded history for this repo` instead of a path. |
| `{SESSION_VOLUME}` | from the same run's `sessions`: `N session files, <bytes_total>, <first> to <last>`, e.g. `81 session files, 340 MB, 2026-05-02 to 2026-09-03`. When the root was not found or holds nothing, print `no session files — there is nothing here to read, so this will be a repo-and-git-only run`. |
| `{REPO_ROOT}` | `discovery.repo.root`, or the detected repo root if `discover.py` has not run yet. |
| `{HOW_LOCATED}` | one line, from `match_mode`. **Claude Code** (`exact`): `a folder Claude Code keeps for this repo — its name is this repo's path.` (`fuzzy` / `basename`): `the closest-named folder Claude Code keeps — matched by <mode>, not exactly, so check the path above is this project.` **Codex** (`cwd+git`): `Codex files every repo's sessions together by date, so to find yours I read only the first record of each session file — the folder it ran in and the git remote — and kept the ones whose folder is this repo or a folder inside it, plus the ones whose remote is this repo's. Nothing else from another project's session is opened, then or later.` (`cwd`): the same sentence ending `...and kept the ones whose folder is this repo or a folder inside it. This repo has no git remote, so sessions you ran from a worktree elsewhere are not included.` (`none`, either target): `nothing here is tied to this repo, so there is nothing to read.` |

The resolver, not an adapter, is what names the directory. **Do not open `adapters/claude-code.md`
or `adapters/codex.md` in phase 0** — path resolution lives in the script, the adapters are read in
phase 7, and the adapter's §2 documents the same encoding for maintainers rather than for this run.

Never print a *sample* of transcript content to persuade the user. You have not scrubbed
anything yet at this point in the run, so you have nothing safe to show.

---

## 3. Interpreting the answer

Accept these forms. If the answer is anything else, ask once more with the three options
restated; if it is still unclear, treat it as **no** and say that you are defaulting to no.

| User says | Scope | What you run |
|---|---|---|
| `1`, `yes`, `y`, `ok`, `sure`, `go ahead`, `all` | full | `mine_transcripts.py --repo <root> --target <target>` |
| `2`, `no`, `n`, `skip`, `don't`, `nope` | none | do **not** run `mine_transcripts.py` at all |
| `3`, `last N days`, `30 days`, `only the last month`, `since <date>` | windowed | `mine_transcripts.py --repo <root> --target <target> --days N` |

For a windowed answer, resolve N to an integer number of days. `a week` → 7, `a month` → 30,
`3 months` → 90, `since <date>` → days between that date and today. Echo the resolved number
back: `Reading the last 30 days of sessions only.` If the user names a window you cannot
resolve to a number, ask for the number of days.

Record the outcome as `consent = full | none | days:N`. Carry it through the whole run. It
appears again in the plan (phase 6) and the report (phase 8).

**Silence is not consent**, and this is the boundary `SKILL.md` rule 9 draws: the recommendation is
printed, and a reply is still required. A one-word `ok` **is** a reply and reads as `full`; saying
nothing, or answering something else entirely, is not — re-ask once, then take **no**. Never carry
`interview.md` §6's accept-everything list into this question: that list resolves preferences in a
phase that writes nothing, and this one decides whether agentic-codebase reads the user's prompts at all.

---

## 4. What is read, precisely

Only when consent is `full` or `days:N`, and only via `mine_transcripts.py`. You never open a
session file yourself with Read, Grep, cat, or any other tool. There is no exception to this —
not "just to check the format", not "just one file". The whole point of the script is that the
raw text never reaches this conversation.

The miner reads, **on Claude Code**:

- Session files under the transcript root the resolver located for **this repo path only**.
  Other projects' session directories are out of scope and must not be touched.
- Within those files, records where `type == "user"` and `message.role == "user"`, with
  `toolUseResult` absent, `isMeta` not true, and `isSidechain` not true.
- From those records, `type == "text"` content blocks only.
- `type == "last-prompt"` records as a fallback source when the user records are unusable.

**On Codex** the file shape is different and so is the rule:

- Rollout files under `${CODEX_HOME}/sessions/` and `archived_sessions/`, **filtered to this repo**
  by the `session_meta` match described in §1. There is no per-repo directory to scope to, so the
  filter *is* the scope.
- Within the kept files, `response_item` records whose `payload.type` is `message` and whose
  `payload.role` is `user`, and from those the `input_text` blocks.
- `event_msg` / `user_message` records only as a de-duplication key — never as the source, because
  the newest sessions (`history_mode: "paginated"`) emit none at all.
- Roughly **two turns in five of that stream are harness-authored, not typed by the user**, and are
  dropped or unwrapped before anything is counted: `<recommended_plugins>`, `<system_instruction>`,
  `<skill>`, `<turn_aborted>`, `<in-app-browser-context>`, `<subagent_notification>`,
  `<task-notification>`, `<local-command-stdout>`, `<environment_context>`, and the tag-less
  `# AGENTS.md instructions for …` and `## Referenced ChatGPT conversation:` forms are dropped
  whole; `# Files mentioned by the user:`, `# Files pasted by the user:` and `# Context from my IDE
  setup:` are split at `## My request…` and only the request is kept. Verified against an
  independent parse of 38 real rollouts: 242 user turns counted exactly, 72 harness-wrapped turns
  stripped.
- Never read on Codex: `role: "developer"` records (100% harness-authored), `compacted` payloads
  (they re-serialise earlier turns and would double-count), `turn_context`, and every assistant
  form. Never read at all: the `${CODEX_HOME}` SQLite databases (`logs_2.sqlite`,
  `thread_history_1.sqlite`, `memories_1.sqlite`, `goals_1.sqlite`, `queue_1.sqlite`), `auth.json`,
  `transcription-history.jsonl`, `dictation-history/`, `attachments/`, `browser/`, or
  `external_agent_session_imports.json`.

The miner discards on both targets, before any analysis:

- Assistant turns and reasoning.
- Tool calls and every `tool_result` / `toolUseResult` payload.
- Subagent traffic (`isSidechain` on Claude Code, the subagent thread kind on Codex) and meta records.
- Injected wrappers: `<system-reminder>`, `<task-notification>`, `<ide_opened_file>`,
  `<ide_selection>`, `<local-command-stdout>`, `<command-message>`, and the Codex vocabulary above.
- Interrupt markers and pasted-image placeholders.

What comes back to you is the aggregate JSON in the `mine_transcripts.py` contract: cluster
skeletons with counts, command counts, correction categories, tool mentions, file hotspots, and
at most **2 examples per cluster, each truncated to 160 characters and scrubbed**.

---

## 5. What is scrubbed, and when

Scrubbing happens inside `lib/scrub.py`, **before** any text is written to the JSON output or
returned to you. Not after. Not on display. Before. If a value was in a prompt, it is already a
`[REDACTED:<kind>]` token by the time you can see it.

Covered kinds: AWS access keys, `sk-` / `sk_live_` / `pk_live_` / `rk_` secret keys,
`ghp_` / `gho_` / `github_pat_` GitHub tokens, `xox[baprs]-` Slack tokens, Bearer tokens, JWTs,
Anthropic and OpenAI keys, private key blocks, database connection strings carrying credentials
(`postgres://`, `mysql://`, `mongodb+srv://`, `redis://`), `password=` / `token=` / `secret=` /
`api_key=` assignments, email addresses, hex or base64 blobs of 32+ characters, and absolute
home paths (`/Users/<name>` → `~`).

Two obligations on you:

1. **Never un-redact.** If a `[REDACTED:...]` token appears in an example you quote in the plan
   or report, leave it exactly as it is. Do not guess what it was, do not ask the user to
   confirm it, do not reconstruct it from context.
2. **Never widen the sample.** If a cluster's two examples are not enough to understand it,
   raise `--top` or re-read the aggregate. Do not go read the source session file.

If `scrub_stats.redactions` is greater than zero, mention it once in the preflight summary:
`Scrubbed N secret-shaped values from your prompts before reading them.` It is reassurance, and
it is true. Do not list the patterns hit unless the user asks.

---

## 6. What is never read — in any phase

This list binds every phase of the run, not just phase 0. It is not overridable by the user; if
the user offers to show you a `.env`, decline and explain that the tool does not read
credentials by design.

- **Env values.** `.env`, `.env.local`, `.env.*` and friends are parsed for variable **names
  only** — the text left of `=`. The value is never retained, never printed, never reasoned
  over.
- **Credential files.** Anything matching `*.pem`, `*.key`, `id_rsa*`, `*credentials*`,
  `*secret*`, keychains, `.npmrc` / `.netrc` auth lines, cloud credential directories.
- **Transcripts from other repos**, other users, or other machines. **One precise exception, and it
  is a Codex structural fact rather than a choice:** Codex stores every repo's rollouts in one shared
  tree, so to find *this* repo's the resolver reads the leading `session_meta` record — `cwd`, git
  remote, thread kind — of each rollout file on the machine, then opens only the matching ones. That
  is a path and a remote URL, never a line of conversation, and it happens **before** the consent
  question so that the question can state the real volume. Nothing else from another project's
  session is read, at any point, on either target. Say this in the consent script's `{HOW_LOCATED}`
  line rather than leaving the user to infer it.
- **Assistant turns and tool output** from any transcript.
- **Anything over the network.** The analyzer scripts make zero network calls. `gh` is the sole
  exception, it is optional and best-effort, it is read-only, and `mine_git.py --no-gh` disables
  it. If the user prefers no `gh` at all, pass `--no-gh` and say so in the plan.

Never run a destructive or history-rewriting git command at any point: no `reset --hard`, no
`checkout -f`, no `clean`, no `rebase`, no `commit --amend`, no `push --force`, no `filter-*`.
The git miner uses `log`, `show --stat`, `rev-list`, and `shortlog` only.

---

## 7. Guarantees to state, and to keep

State these in the preflight summary in one compact line each. They are commitments, so do not
state them if the run cannot honor them.

- **Local only.** No analyzer script opens a socket. Nothing is uploaded. The only thing that
  leaves your machine is whatever this conversation already sends to the model.
- **No telemetry.** No usage counters, no phone-home, no opt-out needed because there is nothing
  to opt out of.
- **Consent every run.** This answer expires when the run ends.
- **Additive and reversible.** Nothing is overwritten, everything lands on a branch or staged,
  and the report lists the exact removal steps.

---

## 8. Degraded runs — no transcript evidence

Two runs reach phase 4 with `history_bucket: "none"`: consent refused (this section) and consent
given with nothing found (§8.1). Both are normal and supported; they are recorded differently.

Consent `none` is a normal, supported path. It is not a failure and you must not nag, re-ask
later in the run, or imply the output will be bad. Say once, plainly, what changes — then move on.

**What still works:** `discover.py` (full repo evidence: languages, manifests, commands,
frameworks, external services, folder zones, CI, env var *names*, monorepo layout, existing
agentic config) and `mine_git.py` (commit conventions, branch naming, co-change clusters,
hotspots, test discipline, contributors). **Not PR patterns:** phase 2 runs `mine_git.py --no-gh`
by default, so `pr_patterns` comes back `{"available": false}` — promising it here would promise
the one thing the no-network default gives up.

**What is unavailable:** every finding whose only possible evidence is a prompt — recurring
request shapes with counts, repeated corrections, slash-command usage, pain signals, tool
mentions from prompts. Concretely:

- Skills: **not proposable at all on this path.** They need tier-1 behavioural evidence — a
  `request_shapes[]` cluster clearing row 1 or row 3 — and `mapping-rules.md` §3 allows a skill no
  discovery-only route: *"a skill with a discovery-only evidence string is a template, which is the
  one thing this tool does not produce."* A multi-step package script chain, a procedure in
  CONTRIBUTING, or a many-step CI job is a real repo signal, but it evidences **what the repo
  does**, not **what this developer repeats**, and a skill is an answer to the second question.
  Route those signals to the index doc instead, where discovery-only evidence is allowed (§3, row
  "Index doc"). *(An earlier version of this bullet said skills could still be proposed from a repo
  signal. It contradicted `mapping-rules.md` §3, which is the phase-4 authority and is the rule
  `CLAUDE.md`'s evidence invariant backs. §3 wins.)*
- Rules derived from "the user corrected this 2+ times": cannot be justified. Rules may still
  come from git conventions (`commit_conventions`, `branch_naming`) and repo conventions.
- MCP recommendations fall back to `discovery.external_services` with `confidence` high only,
  and the interview question about daily-use systems becomes **mandatory** rather than optional,
  because there is no usage evidence to answer it.

**How to run it:**

1. Skip `mine_transcripts.py` entirely. Do not run it with `--days 0` or any other token gesture.
2. Treat `signals.transcripts` as absent and `history_bucket` as `none`. Phase 4 reads that value
   in `coverage.md` §3. There is no clamp and no cap: the behavioural rows are simply empty, so
   `mapping-rules.md` §3's evidence requirement removes the candidates that needed them, and
   nothing else changes.
3. In the interview, do not ask any question whose trigger condition depends on transcript
   signals.
4. Expect a **structural** output, not an empty one. The `blueprint.md` catalogues run off
   `discovery.json`, so a no-history run on a real codebase still produces zone rules, guardrail
   hooks, permissions, integration skills, MCP drafts and `setup-manager`. What it loses is the
   artifacts that needed to know what the developer keeps asking for. Say which, in the plan
   (`coverage.md` §3's verbatim line), and never pad with template artifacts to compensate.

### 8.1 The other zero-evidence path — consent given, nothing found

Consent `full` or `days:N` with `signals.transcripts.sessions.count == 0` is a **different** state
from refusal, and it is the commonest fresh-repo run: a new clone, a new machine, a repo whose work
has not happened in this agent yet. `CLAUDE.md` calls this the secondary user and says the tool still
works. Two runs hit it and had to improvise a line, because there was no fourth string below.

It differs from refusal in one mechanical way, and phase 4 depends on the difference:
`mine_transcripts.py` **did** run, so `signals.transcripts` is **present but empty**, with
`history_bucket: "none"` and every list at zero rows. On a refusal the key is **absent**. Either
way phase 4 sees `history_bucket == "none"` and reads `coverage.md` §3, so the output comes out the
same; only the wording of the record differs. Do not run the miner a second time,
do not widen `--days` to go looking, and do not treat an empty result as a failed run.

Everything in §8's "How to run it" applies from step 2 onward. Step 1 does not: the script already
ran, correctly, and returned nothing.

**How to say it in the plan (phase 6).** The plan's summary carries a consent line; fill it with
exactly one of these four. Pick on the consent value **and** the session count, never on consent
alone — that is what produced the improvisation:

- `Transcript evidence: full history read with your consent.` — consent `full`, sessions `> 0`.
- `Transcript evidence: last N days read with your consent.` — consent `days:N`, sessions `> 0`.
- `Transcript evidence: you consented, and there are no recorded sessions for this repo yet. This
  plan is derived from your code and git history alone — no usage evidence went into it. That is
  the expected result on a fresh repo, not a fault. Results improve after a week of normal use:
  rerun me then and the repetition, corrections and friction this plan could not see will have
  counts to be judged on.` — consent `full` or `days:N`, sessions `== 0`.
- `Transcript evidence: declined. This plan is derived from repo and git evidence only, so it
  proposes fewer artifacts and no repetition-based skills. Rerunning with transcript access
  after a week of normal use will find more.` — consent `none`.

Never say `full history read` over a count of zero — nothing was read, and a plan that claims to
have read a history it did not read is the one sentence in the document a user can check and catch.
Never say `declined` either: the user said yes, and telling them otherwise misrecords a consent
answer.

The same line is repeated in the report (phase 8), so the record explains its own size.
