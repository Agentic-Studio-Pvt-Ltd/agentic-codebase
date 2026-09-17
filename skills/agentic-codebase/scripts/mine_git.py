#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agentic-codebase :: scripts/mine_git.py

Phase 2 git miner.  Reads the repository's own history and reports the
conventions it already follows, so the plan can propose rules that match the
team instead of inventing new ones.

    python3 "$SKILL_DIR/scripts/mine_git.py" --repo /path/to/repo --no-gh
    python3 "$SKILL_DIR/scripts/mine_git.py" --repo . --days 365 --no-gh

The window is ADAPTIVE unless `--days` is given -- see ADAPTIVE WINDOW below.

Prints exactly one JSON object on stdout and nothing else.  Diagnostics go to
stderr.

Exit codes follow the shared contract in `lib/emit.py`'s module docstring,
which is the single normative statement -- do not restate it here and do not
invent a code.  In one line: no git binary, not a repository, an empty repo, a
path that is a file or does not exist, a `gh` call that is unauthenticated are
all DEGRADED, so they print the full schema with `"available": false`, a
populated `warnings` array, and exit 0.  Exit 1 is reserved for an unhandled
exception, which `emit.main_guard()` turns into JSON on the way out.

Run `python3 scripts/mine_git.py --selftest` for a sub-second sanity check:
imports resolve, emit round-trips, regexes compile, the read-only git guard
still refuses a mutating command, and a synthetic three-commit repository
(created with `git init` in a temp directory) is mined end to end.

WHAT IT EXTRACTS
    window               the window actually analysed, and WHY it was chosen
                         (see ADAPTIVE WINDOW)
    commit_conventions   conventional-commit share, the type and scope
                         vocabulary actually used, ticket-prefix share and
                         pattern, subject length, imperative-mood share
    branch_naming        prefix patterns from local branches and merge subjects
    cochange_clusters    files that change together (support >= 3) -- the
                         strongest evidence for path-scoped rules
    hotspots             per-file commits / authors / churn
    directory_hotspots   the same, aggregated to depth 2
    test_discipline      share of commits that touch a test path
    revert_rate          share of subjects that are reverts
    contributors         author names and commit counts in the window, each
                         marked `is_bot`, people first
    authorship           how much of the window is automation, which machines
                         wrote it, and whether it was excluded
    pr_patterns          optional, `gh`-only (see below)

BOTS ARE COUNTED, NEVER MINED
    Release automation writes commits, and on a monorepo it writes the most
    regular ones there are.  Measured on vercel/turborepo: the four
    highest-support co-change clusters -- support 134, 134, 131, 130, every one
    at confidence 1.00 -- were `github-actions[bot]` release version bumps,
    125 of the commits behind one of them being a machine editing a version
    field across packages.  They were the strongest-looking evidence in the
    whole run and they describe nothing a person does.

    So every commit is classified by its author before anything is measured
    (`classify_author`): a `[bot]` / `(bot)` marker in the display name or the
    address, a bot-shaped name (`-bot`, `bot-`), an exact match against
    `KNOWN_BOT_IDENTITIES` (dependabot, renovate, github-actions,
    checkpointer, ...), a no-reply sender, or an address already used by an
    identity classified as a machine -- which is how `cyrusagent` sitting
    beside `cyrusagent[bot]` is counted once, as one machine.

    Matching is EXACT against the whole normalised name, never a substring, so
    a person called Claude Dupont or Jenkins Okafor stays a person.  A
    `users.noreply.github.com` address is NOT a bot signal on its own -- that
    is the address GitHub hands ordinary users who hide their email, and
    treating it as one would reclassify a large share of every open-source
    repository's humans.

    By default bot commits are excluded from commit conventions, branch
    naming, co-change, hotspots, directory hotspots, test discipline and the
    revert rate.  They are never thrown away: `contributors[]` keeps them
    (marked `is_bot`, sorted after the people so the 20-row cap can never hide
    a human behind a machine) and `authorship` reports how many there were and
    who wrote them.  A repository where 60% of the commits are automation is
    itself a finding -- it is just not evidence for an artifact.

    `--include-bots` restores the raw view, sets `authorship.bots_excluded` to
    false, and warns that release automation may now be driving the clusters.

    `contributors[]` also carries `email_domain` -- the domain half only.  The
    local part is the identifying half and is never emitted; the domain is
    what carries the signal (`noreply`, a vendor's bot domain) and it is what
    makes the classification auditable by a reader who has only the JSON.

    Note for consumers: `window.commits_analyzed` stays the number of commits
    READ, so the window never misreports itself.  The denominator of every
    percentage below is `authorship.commits_human` (or `commits_total` under
    `--include-bots`).  When `commits_human` is 0 every percentage is computed
    over nothing and a warning says so -- do not read them as conventions.

ADAPTIVE WINDOW
    A fixed 180-day window destroys the evidence on a stable repository.
    Measured on a fresh clone of tj/commander.js: `--days 180` returned 7
    commits, 0 co-change clusters, and a conventional-commit share computed
    over 7 subjects -- a statistically meaningless number that would still be
    presented to the model as a convention.  The same clone at 365 days
    returns 55 commits and 6 clusters; at 3650 days, 1037 commits and 15.  A
    mature, slow-moving library is exactly the repository where co-change and
    conventions are MOST reliable, and the fixed window saw almost none of it.

    So the window is chosen, not assumed.  With no `--days`, the miner probes
    the ladder 180 -> 365 -> 1095 -> 3650 -> all history with a cheap
    `git rev-list --count` (no --numstat, no parsing) and stops at the FIRST
    rung holding at least `--min-commits` commits (default 50), or at the rung
    that already saturates `--max-commits`, or at the end of the ladder.  Only
    then does the single expensive log pass run, once, over the chosen window.
    The bias is deliberate: the narrowest window that carries enough evidence,
    so recent practice wins whenever there is enough of it to measure.

    `window` reports what was used and why -- `days`, `mode` (`adaptive` or
    `explicit`), `min_commits`, the probe `steps` (`[{days, commits}]`) and a
    one-sentence `reason` -- so the plan can cite the window honestly instead
    of implying the default was chosen on purpose.

    `--days N` is an explicit override and turns the ladder OFF entirely
    (`--days 0` means all history).  `mode` says `explicit` and `steps` is
    empty, so a reader can always tell a chosen window from an imposed one.

RECENCY -- EVERY PIECE OF PATH EVIDENCE IS DATED
    `mapping-rules.md` has a recency gate ("evidence older than 90 days scores
    at most F = 1"), but before this it could only be applied to transcript
    request shapes: the git clusters and hotspots carried no date, so a
    co-change cluster from a directory refactored away two years ago was
    indistinguishable from a live one.  Widening the window makes that worse,
    not better -- so widening and dating land together.

    `cochange_clusters[]`, `hotspots[]` and `directory_hotspots[]` each carry
    `first_seen` / `last_seen` (`YYYY-MM-DD`, from the commits that produced
    that row) and `still_exists` (the path is present in the working tree; for
    a cluster, EVERY path in it is).  A row with `still_exists: false` is dead
    evidence -- the code it describes is gone -- and must not become an
    artifact no matter how high its support.  The dates come from the commit
    records the single log pass already parsed; no extra git call.

PARTIAL (BLOBLESS) CLONES -- DEGRADE CHURN, KEEP EVERYTHING ELSE
    contributors are told to clone the regression fixtures with
    `--filter=blob:none`, and that clone has every commit and every tree but
    almost no blobs.  `git log --numstat` has to read blob CONTENT to count
    lines, so on such a clone it fetches them from the promisor remote one at
    a time.  Measured before this was handled: 65.7s on chalk and 78.6s on
    commander.js, both ending in `available: false` with every statistic empty
    -- a minute of network traffic, inside a tool whose contract is that it
    makes no network calls, in exchange for nothing.

    So the clone is classified before the log pass runs (`detect_partial_clone`,
    three `config --get` reads and a `rev-parse`, under a second), and on a
    partial clone the pass runs as `--name-only --no-renames` instead.

    `--no-renames` is load-bearing.  Inexact rename detection also reads blob
    content, so plain `--name-only` still fetches: 8.07s versus 0.016s on the
    same clone.

    Re-measured 2026-09-05 on fresh blobless clones, same four commands, one
    machine, `--since=3650 days ago`:

        --numstat, lazy fetch allowed        61.31s, then `fatal: could not
                                             fetch ... from promisor remote`
        --name-only, renames on               6.98s  (still fetching blobs)
        --name-only --no-renames              0.010s (what this module runs)
        --numstat, GIT_NO_LAZY_FETCH=1        0.012s, fails and says why

    End to end through this module on those clones: chalk 0.19s, commander.js
    0.13s, axios 0.14s, every one `available: true` with a populated payload,
    against 0.17s for a FULL clone of chalk -- so a blobless clone is no longer
    the slow path, it is the same path minus churn.

    What this costs is one field outright and one count at the margin.  Only
    `analyze_hotspots` ever reads the numstat numbers, and only to sum `churn`,
    so `hotspots[].churn` is 0 on every row and a warning says so and names the
    fix.  Conventions, branch naming, co-change, hotspots, directory hotspots,
    test discipline, revert rate and authorship are all computed from PATHS and
    survive intact.

    They are NOT byte-identical to a full clone, and an earlier version of this
    docstring claimed they were.  `--no-renames` reports a rename as a delete
    plus an add; `--numstat` on a full clone has rename detection on, reports
    the pair as one `old.js => new.js` entry, and `_resolve_rename` collapses
    it onto the destination.  So a renamed path keeps a commit the full clone
    attributes only to its new name.  Measured, blobless chalk against a full
    clone of the same repo at the same window (218 commits, 12 rename entries
    in that history): 3 of 20 `hotspots` rows off by one commit (`index.js`
    31 vs 30, `index.test-d.ts` 20 vs 19, `templates.js` 14 vs 13), two
    `directory_hotspots` rows off by one, and 1 of 15 co-change clusters at
    support 8 vs 7.  Every row, rank and path is otherwise the same.

    Rename following is the better evidence -- it tracks a file across a move --
    so the full-clone pass keeps it rather than being degraded to match.  What
    the warning must not say is "unaffected".

    Two belts, one pair of braces.  `GIT_NO_LAZY_FETCH=1` (see `_child_env`)
    makes any lazy fetch fail instantly instead of dialling out, so a path
    detection misses costs 0.015s rather than 65s; and a `--numstat` pass that
    fails on a missing object is retried once in the path-only form rather
    than returning an empty payload.

    A SHALLOW clone is a different thing and is not degraded: it holds every
    blob for the commits it has.  It gets a warning about its truncated
    history and an honest `--numstat` pass.

SAFETY -- READ-ONLY, ENFORCED
    Every git invocation is routed through `_git()`, which asserts the
    subcommand is a member of the module-level `ALLOWED_GIT` table and that no
    argument is a mutating verb or an option that can write a file.  The table
    holds read-only commands ONLY:

        log, rev-list, rev-parse, shortlog, show --stat, for-each-ref,
        config --get

    Adding a mutating command (add, commit, checkout, reset, rebase, merge,
    push, clean, gc, filter-branch, ...) requires editing both `ALLOWED_GIT`
    and `FORBIDDEN_TOKENS` -- deliberately, not casually.  Do not do it.  The
    contract  is absolute: this tool never writes to the user's git
    state, never rewrites history, never force pushes.  `GIT_OPTIONAL_LOCKS=0`
    is exported so git will not even refresh the index on our behalf.

    Every subprocess call has a timeout and captures stderr.

THE ONE OPTIONAL NETWORK PATH
    `pr_patterns` shells out to the GitHub CLI (`gh pr list`), which talks to
    github.com.  It is the ONLY code path in the whole of agentic-codebase that can
    touch the network, and it is best-effort in every direction:

        * skipped entirely with `--no-gh`;
        * skipped when `gh` is not on PATH;
        * skipped when `gh auth status` fails (not logged in / no token);
        * hard 10 second timeout on the listing, 8 seconds on the auth probe;
        * any failure at all sets `pr_patterns.available = false`, adds a
          warning, and the run continues unaffected.

    To disable it permanently for a run, pass `--no-gh`.  Nothing else in this
    script opens a socket.  No repository content is ever sent anywhere: `gh`
    only reads.

PRIVACY
    Author names and every string taken from a commit subject, a PR title or a
    PR body pass through `lib.scrub` before they land in the output, so tokens,
    keys and home paths cannot leak into the plan.

Python 3.9+, standard library only.
"""

from __future__ import print_function

import json
import os
import re
import shutil
import subprocess
import sys
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

# `scripts/` is sys.path[0] when this file is run directly, so `lib` resolves.
try:
    from lib import emit as emit_lib
    from lib import scrub as scrub_lib
    from lib import textnorm
except ImportError:  # pragma: no cover - direct execution from another cwd
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from lib import emit as emit_lib
    from lib import scrub as scrub_lib
    from lib import textnorm


TOOL = "mine_git.py"
SCHEMA_VERSION = emit_lib.SCHEMA_VERSION

# ---------------------------------------------------------------------------
# Command allow-list.  Nothing here writes.
# ---------------------------------------------------------------------------

#: subcommand -> flags that MUST be present for the call to be permitted.
#: `show` is only ever allowed in its `--stat` (diffstat) form, `config` only
#: in its `--get` (read one key) form.  A bare `git show` would print blobs and
#: a bare `git config` would open an editor.
ALLOWED_GIT = {
    "log": (),
    "rev-list": (),
    "rev-parse": (),
    "shortlog": (),
    "for-each-ref": (),
    "show": ("--stat",),
    "config": ("--get",),
}  # type: Dict[str, Tuple[str, ...]]

#: Anything that mutates the repository, the index, the working tree, refs, or
#: the remote.  Rejected wherever it appears -- as a subcommand or as an
#: argument -- so a future edit cannot smuggle one in through an arg list.
FORBIDDEN_TOKENS = frozenset(
    """
    add am apply archive bisect branch checkout cherry-pick citool clean clone
    commit commit-tree config-set daemon fast-import fetch filter-branch
    filter-repo format-patch fsck gc grep-write hash-object http-backend init
    instaweb maintenance merge merge-base-write mktag mktree mv notes pack-refs
    prune pull push rebase reflog remote repack replace request-pull reset
    restore revert rm send-email send-pack stage stash submodule switch symbolic-ref
    tag update-index update-ref worktree write-tree
    """.split()
)

#: Option prefixes that can write a file or execute a program even under an
#: otherwise read-only subcommand.
FORBIDDEN_OPTION_PREFIXES = (
    "--output",
    "--exec",
    "--upload-pack",
    "--receive-pack",
    "--git-dir",
    "--work-tree",
    "--namespace",
    "--edit",
    "-o=",
)

#: Global options this module owns.  A caller may not pass them as arguments.
RESERVED_GLOBAL_TOKENS = frozenset(["-C", "-c", "--no-pager", "-o"])

#: `gh` subcommands this module may run.  Read-only listings only.
ALLOWED_GH = {
    ("auth", "status"),
    ("pr", "list"),
}


class GitSafetyError(RuntimeError):
    """Raised when a call would step outside the read-only allow-list."""


# ---------------------------------------------------------------------------
# Tunables
# ---------------------------------------------------------------------------

DEFAULT_DAYS = 180
DEFAULT_MAX_COMMITS = 3000

#: The adaptive ladder, narrowest first.  `0` is the last rung and means all
#: history.  Probed with `rev-list --count`, which is cheap; the expensive
#: `--numstat` log pass runs once, over the winner.
ADAPTIVE_LADDER = (180, 365, 1095, 3650, 0)

#: Below this many commits a window cannot support co-change (`support >= 3`
#: needs repetition) and a percentage over its subjects is noise, not a
#: convention.  Measured: 7 commits -> 0 clusters; 55 -> 6; 273 -> 15.
DEFAULT_MIN_COMMITS = 50

#: mine_git is evidence for the model, not a transcript digest, so it gets a
#: larger budget than `lib.emit.DEFAULT_CAP_CHARS` (which sizes the ~3k-token
#: transcript report).  Still hard-capped; --cap-chars overrides.
DEFAULT_CAP_CHARS = 24000

#: Config keys that say "this clone does not hold every object locally".  A
#: `--filter=blob:none` clone (what contributors are told to make)
#: sets the first two on the remote it filtered from; older and hand-rolled
#: layouts set `extensions.partialclone` instead.  All three are read with
#: `config --get`, which is already in the allow-list -- no new git verb.
PARTIAL_CLONE_KEYS = (
    "remote.origin.promisor",
    "remote.origin.partialclonefilter",
    "extensions.partialclone",
)

#: Fragments git uses when a read needs an object this clone does not have.
#: Matched case-insensitively against stderr to turn a hard failure into a
#: retry.  Detection is the fast path; this is the safety net for the shapes
#: detection misses (a promisor remote not named `origin`, a shallow clone, a
#: genuinely damaged object database).
MISSING_OBJECT_MARKERS = (
    "promisor",
    "not in the object database",
    "missing object",
    "lazy fetching disabled",
    "could not fetch",
    "unable to read",
    "bad object",
)

GIT_TIMEOUT_S = 90          # the single --numstat log pass on a big repo
GIT_QUICK_TIMEOUT_S = 15    # rev-parse / for-each-ref / config --get
GH_AUTH_TIMEOUT_S = 8
GH_LIST_TIMEOUT_S = 10      # contract: hard 10s cap on the PR listing
GH_PR_LIMIT = 30

#: Commits touching more than this many files are bulk renames, vendored
#: drops, generated-code refreshes or squashed merges.  They contribute
#: hundreds of meaningless pairs and drown the real co-change signal, so they
#: are skipped for co-change (they still count for hotspots and conventions).
BULK_COMMIT_FILE_LIMIT = 40

MIN_COCHANGE_SUPPORT = 3
MAX_COCHANGE_CLUSTERS = 15
MAX_HOTSPOTS = 20
MAX_DIRECTORY_HOTSPOTS = 15
MAX_CONTRIBUTORS = 20
MAX_BOT_AUTHORS = 10
MAX_BRANCH_PATTERNS = 12
MAX_TYPES = 15
MAX_SCOPES = 20
MAX_TEST_PATHS = 10
MAX_PR_BODY_SECTIONS = 8

#: Guard on the pair table.  With the "only files seen in >= MIN_COCHANGE_SUPPORT
#: commits can form a qualifying pair" pre-filter this is never reached on a
#: normal repo; it exists so a pathological history cannot exhaust memory.
MAX_PAIR_ENTRIES = 400000


# ---------------------------------------------------------------------------
# Path classification
# ---------------------------------------------------------------------------

LOCKFILE_BASENAMES = frozenset(
    """
    package-lock.json npm-shrinkwrap.json yarn.lock pnpm-lock.yaml pnpm-workspace.yaml
    bun.lock bun.lockb deno.lock composer.lock gemfile.lock poetry.lock pipfile.lock
    cargo.lock go.sum uv.lock mix.lock packages.lock.json podfile.lock package.resolved
    gradle.lockfile flake.lock .terraform.lock.hcl conda-lock.yml requirements.lock
    """.split()
)

GENERATED_DIR_SEGMENTS = frozenset(
    """
    node_modules dist build out .next .nuxt .svelte-kit .turbo .output coverage
    vendor target __pycache__ .venv venv .mypy_cache .pytest_cache .gradle
    generated __generated__ .terraform pods carthage bin obj
    """.split()
)

GENERATED_SUFFIXES = (
    ".min.js",
    ".min.css",
    ".map",
    ".snap",
    ".pb.go",
    "_pb2.py",
    "_pb2_grpc.py",
    ".pb.cc",
    ".pb.h",
    ".g.dart",
    ".freezed.dart",
    ".generated.ts",
    ".generated.js",
    ".gen.go",
    ".d.ts",
)

BINARY_ASSET_SUFFIXES = (
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".svg", ".pdf", ".zip",
    ".gz", ".tar", ".mp4", ".mov", ".mp3", ".wav", ".woff", ".woff2", ".ttf",
    ".otf", ".eot", ".jar", ".so", ".dylib", ".dll", ".class", ".wasm",
)

TEST_DIR_SEGMENTS = frozenset(
    ["test", "tests", "__tests__", "spec", "specs", "e2e", "testing",
     "cypress", "playwright", "integration-tests", "it", "features"]
)

TEST_FILE_PATTERNS = (
    re.compile(r"\.(test|spec)\.[a-z0-9]+$", re.IGNORECASE),
    re.compile(r"(^|/)test_[^/]+\.py$", re.IGNORECASE),
    re.compile(r"[._-]test\.[a-z0-9]+$", re.IGNORECASE),
    re.compile(r"_test\.(go|py|rb|rs|dart|exs?)$", re.IGNORECASE),
    re.compile(r"_spec\.(rb|js|ts|lua)$", re.IGNORECASE),
    re.compile(r"(^|/)conftest\.py$", re.IGNORECASE),
    re.compile(r"[A-Za-z0-9]Tests?\.(java|kt|cs|swift|scala)$"),
)

#: Branch prefixes that name a kind of work rather than a person.
BRANCH_TYPE_PREFIXES = frozenset(
    """
    feat feature feats features fix bugfix hotfix bug chore chores docs doc
    refactor test tests spec perf style ci build release rel deps dependabot
    revert exp experiment spike wip poc infra ops migration
    """.split()
)

#: Never counted as a naming *pattern* -- they are trunk / environment branches.
TRUNK_BRANCHES = frozenset(
    """
    main master develop dev trunk staging stage production prod release next
    canary preview qa uat sandbox default gh-pages
    """.split()
)


# ---------------------------------------------------------------------------
# Author classification -- machines vs people
# ---------------------------------------------------------------------------

#: A marker that settles it outright, wherever it appears -- display name or
#: address local part.  GitHub writes both as `dependabot[bot]`.
BOT_MARKERS = ("[bot]", "(bot)")

#: Bot-shaped display names.  Matched against the NORMALISED name (lower-cased,
#: whitespace collapsed), so "Renovate Bot" and "renovate-bot" are one thing.
BOT_NAME_SUFFIXES = ("-bot", "_bot", " bot", ".bot")
BOT_NAME_PREFIXES = ("bot-", "bot_", "bot ")

#: Identities that are machines whatever they call themselves.
#:
#: Matched EXACTLY against the whole normalised display name, its dashed and
#: squashed forms, and the address local part -- never as a substring.  That
#: is the whole reason `claude`, `copilot`, `cursor`, `jenkins` and `stale` are
#: safe to list: "Claude Dupont" normalises to `claude dupont`, which is not a
#: member, so she stays a person.  A substring test would have made her a bot.
KNOWN_BOT_IDENTITIES = frozenset(
    """
    github-actions github-action githubactions actions-user github
    dependabot dependabot-preview renovate renovatebot
    snyk-bot snyk imgbot allcontributors all-contributors
    semantic-release semantic-release-bot greenkeeper mergify
    whitesource pyup restyled depfu scala-steward pre-commit-ci
    netlify vercel sonarcloud codecov coveralls codeclimate deepsource
    stale release-please changeset-bot changeset-release gitbook
    travis travis-ci circleci jenkins azure-pipelines teamcity buildkite
    checkpointer copilot claude codex cursoragent cursor devin sweep
    weblate crowdin transifex lokalise
    """.split()
)

#: Address local parts (and, for a domain-less address, domains) that mean no
#: human reads this mailbox.
NOREPLY_TOKENS = frozenset(["noreply", "no-reply", "donotreply", "do-not-reply"])

_NAME_PUNCT_RE = re.compile(r"[^a-z0-9]+")

#: GitHub prefixes a bot's address with its numeric account id:
#: `49699333+dependabot[bot]@users.noreply.github.com`.
_LOCAL_ID_PREFIX_RE = re.compile(r"^\d{1,12}\+")


def _norm_author_name(name: str) -> str:
    return " ".join((name or "").strip().lower().split())


def _name_forms(normalised: str) -> frozenset:
    """The spellings of one display name that identity matching runs against."""
    if not normalised:
        return frozenset()
    forms = set([normalised])
    dashed = _NAME_PUNCT_RE.sub("-", normalised).strip("-")
    if dashed:
        forms.add(dashed)
    squashed = _NAME_PUNCT_RE.sub("", normalised)
    if squashed:
        forms.add(squashed)
    return frozenset(forms)


def classify_author(name: str, email: str) -> Tuple[bool, str]:
    """
    `(is_bot, reason)` for one commit author.

    Ordered cheapest and most certain first.  The reason is emitted verbatim on
    the `contributors[]` row, so it has to read as an explanation to someone
    auditing the exclusion, not as a rule id.
    """
    normalised = _norm_author_name(name)
    address = (email or "").strip().lower()
    local, _at, domain = address.partition("@")
    local = _LOCAL_ID_PREFIX_RE.sub("", local)

    for marker in BOT_MARKERS:
        if marker in normalised or marker in local:
            return True, "name or address carries the %s marker" % marker

    for suffix in BOT_NAME_SUFFIXES:
        if normalised.endswith(suffix):
            return True, "display name ends with %s" % suffix.strip()
    for prefix in BOT_NAME_PREFIXES:
        if normalised.startswith(prefix):
            return True, "display name starts with %s" % prefix.strip()

    hit = _name_forms(normalised) & KNOWN_BOT_IDENTITIES
    if hit:
        return True, "known CI or agent identity (%s)" % sorted(hit)[0]
    if local and local in KNOWN_BOT_IDENTITIES:
        return True, "address local part is a known CI or agent identity (%s)" % local

    if local in NOREPLY_TOKENS:
        return True, "commits from a no-reply address"
    # `checkpointer@noreply` -- an address with no deliverable domain at all.
    # `users.noreply.github.com` deliberately does NOT match: that is a human's
    # privacy address, not a machine's.
    if domain in NOREPLY_TOKENS or domain.startswith("noreply."):
        return True, "address has no deliverable domain (%s)" % domain
    if local == "bot" or local.endswith("-bot") or local.endswith("_bot"):
        return True, "address local part is bot-shaped (%s)" % local

    return False, ""


def partition_commits(commits: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Split commits into people and machines, and aggregate the author table.

    Two passes.  The first classifies each distinct `(name, address)` identity
    and remembers every address a machine used.  The second re-reads the same
    commits so that a *bare* display name sharing an address with an identity
    already classified as a bot is counted as the same machine -- `cyrusagent`
    beside `cyrusagent[bot]`, one machine under two display names.

    Returns `{"human": [...], "bot": [...], "authors": [...]}` where `authors`
    holds one aggregated row per display name, in first-appearance order:
    `{name, commits, email_domain, is_bot, bot_reason}`.  The address local
    part never leaves this function.
    """
    verdicts = {}  # type: Dict[Tuple[str, str], Tuple[bool, str]]
    bot_addresses = {}  # type: Dict[str, str]
    for commit in commits:
        key = (commit.get("author", "") or "", commit.get("email", "") or "")
        if key not in verdicts:
            verdicts[key] = classify_author(key[0], key[1])
        is_bot, reason = verdicts[key]
        address = key[1].strip().lower()
        if is_bot and address and address not in bot_addresses:
            bot_addresses[address] = reason

    human = []  # type: List[Dict[str, Any]]
    bot = []  # type: List[Dict[str, Any]]
    authors = {}  # type: Dict[str, Dict[str, Any]]
    order = []  # type: List[str]

    for commit in commits:
        key = (commit.get("author", "") or "", commit.get("email", "") or "")
        is_bot, reason = verdicts[key]
        address = key[1].strip().lower()
        if not is_bot and address and address in bot_addresses:
            is_bot = True
            reason = "shares an address with a bot identity (%s)" % bot_addresses[address]
        (bot if is_bot else human).append(commit)

        display = key[0] or "(unknown)"
        row = authors.get(display)
        if row is None:
            row = {"commits": 0, "domains": {}, "is_bot": False, "bot_reason": ""}
            authors[display] = row
            order.append(display)
        row["commits"] += 1
        _domain = address.partition("@")[2]
        if _domain:
            row["domains"][_domain] = row["domains"].get(_domain, 0) + 1
        if is_bot and not row["is_bot"]:
            row["is_bot"] = True
            row["bot_reason"] = reason

    rows = []  # type: List[Dict[str, Any]]
    for display in order:
        row = authors[display]
        domain = ""
        if row["domains"]:
            domain = sorted(row["domains"].items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        rows.append(
            {
                "name": display,
                "commits": row["commits"],
                "email_domain": domain,
                "is_bot": row["is_bot"],
                "bot_reason": row["bot_reason"],
            }
        )
    return {"human": human, "bot": bot, "authors": rows}


def empty_authorship(bots_excluded: bool = True) -> Dict[str, Any]:
    return {
        "bots_excluded": bool(bots_excluded),
        "commits_total": 0,
        "commits_human": 0,
        "commits_bot": 0,
        "bot_pct": 0.0,
        "bot_authors": [],
    }


def analyze_authorship(
    split: Dict[str, Any], bots_excluded: bool, hits: List[str]
) -> Dict[str, Any]:
    """
    How much of the window is automation, and which machines wrote it.

    This block exists so bots stay COUNTABLE after they stop being mined: the
    share of a repository's history written by machines is a real finding about
    that repository, and losing it would be the opposite mistake to the one the
    filter fixes.
    """
    human = len(split["human"])
    bots = len(split["bot"])
    total = human + bots
    bot_rows = sorted(
        [row for row in split["authors"] if row["is_bot"]],
        key=lambda row: (-row["commits"], row["name"].lower()),
    )[:MAX_BOT_AUTHORS]
    return {
        "bots_excluded": bool(bots_excluded),
        "commits_total": total,
        "commits_human": human,
        "commits_bot": bots,
        "bot_pct": _pct(bots, total),
        "bot_authors": [
            {
                "name": _clean(row["name"], hits),
                "commits": row["commits"],
                "reason": row["bot_reason"],
            }
            for row in bot_rows
        ],
    }


# ---------------------------------------------------------------------------
# Regexes
# ---------------------------------------------------------------------------

CONVENTIONAL_RE = re.compile(
    r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)"
    r"(\(([^)]{1,60})\))?(!)?: "
)

#: A ticket key at the head of a subject: `ENG-123 ...`, `[ENG-123] ...`,
#: `feat(api): ENG-123 ...`.
TICKET_RE = re.compile(r"^\[?([A-Z][A-Z0-9]{1,9})-(\d{1,7})\]?[\s:\]]")

TICKET_ANYWHERE_RE = re.compile(r"\b([A-Z][A-Z0-9]{1,9})-(\d{1,7})\b")

REVERT_RE = re.compile(r'^(revert:|revert\s|revert")', re.IGNORECASE)

MERGE_BRANCH_RE = re.compile(
    r"^Merge (?:remote-tracking )?branch '([^']{1,200})'", re.IGNORECASE
)
MERGE_PR_RE = re.compile(
    r"^Merge pull request #\d+ from ([^\s]{1,200})", re.IGNORECASE
)
MERGE_PR_SQUASH_RE = re.compile(r"\(#\d{1,7}\)\s*$")

#: `src/{old => new}/file.ts` and `old.ts => new.ts`
RENAME_BRACE_RE = re.compile(r"^(.*)\{(.*) => (.*)\}(.*)$")

# Path quoting.  `QUOTED_PATH_RE` is one fully quoted path -- the closing quote
# is the last character, so a ` => ` inside it belongs to the NAME, not to a
# rename.  `RENAME_QUOTED_PAIR_RE` is the rename shape git emits once either
# side needs quoting: `"old" => "new"`, each side quoted on its own.  The
# escapes are C-style, and the octal ones are BYTES; see `_unquote_path`.
QUOTED_PATH_RE = re.compile(r'^"(?:[^"\\]|\\.)*"$')
RENAME_QUOTED_PAIR_RE = re.compile(
    r'^(?P<old>"(?:[^"\\]|\\.)*"|[^"]*?) => (?P<new>"(?:[^"\\]|\\.)*"|[^"]*)$'
)
C_ESCAPES = {
    "a": 0x07, "b": 0x08, "f": 0x0C, "n": 0x0A, "r": 0x0D, "t": 0x09, "v": 0x0B,
    "\\": 0x5C, '"': 0x22,
}
OCTAL_DIGITS = "01234567"
HEX_DIGITS = "0123456789abcdefABCDEF"

PR_HEADING_RE = re.compile(r"^\s{0,3}#{1,4}\s+(.{1,80}?)\s*$", re.MULTILINE)
PR_BOLD_HEADING_RE = re.compile(r"^\s{0,3}\*\*(.{1,60}?)\*\*:?\s*$", re.MULTILINE)

RECORD_SEP = "\x1e"
FIELD_SEP = "\x1f"


# ---------------------------------------------------------------------------
# Safe subprocess plumbing
# ---------------------------------------------------------------------------


def _child_env() -> Dict[str, str]:
    """
    Environment for every child process.

    `GIT_OPTIONAL_LOCKS=0` stops git from taking the index lock or writing a
    refreshed index as a side effect of a read.  `GIT_TERMINAL_PROMPT=0` and
    `GIT_ASKPASS`/`SSH_ASKPASS` make sure nothing can ever block on a
    credential prompt.  `GIT_PAGER=cat` defeats a pager configured in the
    user's global config.

    `GIT_NO_LAZY_FETCH=1` is the one that keeps the no-network promise
    STRUCTURAL rather than aspirational.  In a partial clone git will silently
    dial the promisor remote to fetch any object a read needs, so a read-only
    command can open a socket without a single line of this file asking it to.
    Measured on a fresh `--filter=blob:none` clone of chalk: the `--numstat`
    log pass spent 65s fetching blobs one at a time and then failed anyway.
    With this set, the same command fails in 0.015s and says why -- which the
    caller turns into a degrade, not a network call.  It is a no-op on a
    normal clone (git >= 2.40; older git ignores it, which is why detection
    below does not rely on it).
    """
    env = dict(os.environ)
    env["GIT_OPTIONAL_LOCKS"] = "0"
    env["GIT_NO_LAZY_FETCH"] = "1"
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_PAGER"] = "cat"
    env["PAGER"] = "cat"
    env["GIT_ASKPASS"] = "true"
    env["SSH_ASKPASS"] = "true"
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["CLICOLOR"] = "0"
    env.pop("GIT_EXTERNAL_DIFF", None)
    env.pop("GIT_DIR", None)
    env.pop("GIT_WORK_TREE", None)
    env.pop("GIT_INDEX_FILE", None)
    return env


def _run(
    argv: Sequence[str],
    timeout: float,
    debug: bool = False,
    cwd: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run a command with a timeout, capturing both streams.  Never raises.

    Returns {"ok": bool, "code": int, "out": str, "err": str, "reason": str}.
    """
    result = {"ok": False, "code": -1, "out": "", "err": "", "reason": ""}
    if debug:
        emit_lib.eprint("[mine_git] $ %s" % " ".join(argv))
    try:
        completed = subprocess.run(  # nosec - argv list, never shell=True
            list(argv),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            env=_child_env(),
            encoding="utf-8",
            errors="replace",
            shell=False,
            cwd=cwd if (cwd and os.path.isdir(cwd)) else None,
        )
    except subprocess.TimeoutExpired:
        result["reason"] = "timed out after %ss" % timeout
        return result
    except FileNotFoundError:
        result["reason"] = "executable not found: %s" % argv[0]
        return result
    except OSError as exc:
        result["reason"] = "could not start %s: %s" % (argv[0], exc)
        return result
    except Exception as exc:  # pragma: no cover - defensive
        result["reason"] = "unexpected failure running %s: %s" % (argv[0], exc)
        return result

    result["code"] = completed.returncode
    result["out"] = completed.stdout or ""
    result["err"] = completed.stderr or ""
    result["ok"] = completed.returncode == 0
    if not result["ok"] and not result["reason"]:
        result["reason"] = _first_line(result["err"]) or ("exit %d" % completed.returncode)
    return result


def _assert_read_only(subcommand: str, args: Sequence[str]) -> None:
    """
    The single choke point.  Every git call in this file goes through it.

    Raises GitSafetyError unless the subcommand is in `ALLOWED_GIT`, carries
    whatever flag that entry requires, and no argument is a mutating verb or a
    file-writing / program-executing option.
    """
    if subcommand not in ALLOWED_GIT:
        raise GitSafetyError(
            "git subcommand %r is not in the read-only allow-list %s"
            % (subcommand, sorted(ALLOWED_GIT))
        )
    required = ALLOWED_GIT[subcommand]
    for flag in required:
        if not any(a == flag or a.startswith(flag + "=") for a in args):
            raise GitSafetyError(
                "git %s is only permitted with %s" % (subcommand, flag)
            )
    for arg in args:
        token = str(arg)
        head = token.split("=", 1)[0]
        if head in FORBIDDEN_TOKENS or token in FORBIDDEN_TOKENS:
            raise GitSafetyError("argument %r names a mutating git command" % token)
        # Check `head` as well as the whole token: `-o=/tmp/x` splits to `-o`,
        # which is the form the reserved set names.  Testing only `token` let
        # `git log -o=/tmp/pwned` through.
        if token in RESERVED_GLOBAL_TOKENS or head in RESERVED_GLOBAL_TOKENS:
            raise GitSafetyError("argument %r is a reserved global option" % token)
        for prefix in FORBIDDEN_OPTION_PREFIXES:
            # Match against both, since `--output=x` -> head `--output` but
            # `-o=x` -> head `-o`, and the prefix list carries both shapes.
            if head.startswith(prefix) or token.startswith(prefix):
                raise GitSafetyError("argument %r can write or execute" % token)


def _git(
    repo: str,
    subcommand: str,
    args: Optional[Sequence[str]] = None,
    timeout: float = GIT_QUICK_TIMEOUT_S,
    debug: bool = False,
) -> Dict[str, Any]:
    """Run one allow-listed, read-only git command inside `repo`."""
    args = list(args or [])
    _assert_read_only(subcommand, args)
    argv = ["git", "--no-pager", "-C", repo, subcommand] + args
    return _run(argv, timeout=timeout, debug=debug)


def _gh(
    args: Sequence[str],
    timeout: float,
    debug: bool = False,
    cwd: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run one allow-listed `gh` command.  This is the only network-capable call
    in agentic-codebase; see the module docstring.

    `cwd` is the repository root: `gh pr list` resolves which GitHub repo to
    query from the git remote of its working directory.
    """
    args = list(args)
    key = tuple(args[:2])
    if key not in ALLOWED_GH:
        raise GitSafetyError("gh command %r is not in the read-only allow-list" % (key,))
    return _run(["gh"] + args, timeout=timeout, debug=debug, cwd=cwd)


def _first_line(text: str, limit: int = 200) -> str:
    if not text:
        return ""
    line = text.strip().splitlines()[0] if text.strip() else ""
    if len(line) > limit:
        line = line[:limit] + "..."
    return line


def _clean(text: str, hits: List[str]) -> str:
    """Scrub a string and accumulate the redaction kinds."""
    cleaned, found = scrub_lib.scrub(text or "")
    if found:
        hits.extend(found)
    return cleaned


# ---------------------------------------------------------------------------
# Partial / blobless clones
# ---------------------------------------------------------------------------


def _looks_like_missing_object(text: str) -> bool:
    lowered = (text or "").lower()
    return any(marker in lowered for marker in MISSING_OBJECT_MARKERS)


def _config_path(root: str) -> str:
    """
    `<git dir>/config` for a work tree, a `gitdir:` link file, or a bare repo.
    Empty string when it cannot be resolved -- the caller treats that as "no
    extra evidence", never as an error.
    """
    dot_git = os.path.join(root, ".git")
    if os.path.isdir(dot_git):
        candidate = dot_git
    elif os.path.isfile(dot_git):
        try:
            with open(dot_git, encoding="utf-8", errors="replace") as handle:
                head = handle.read(4096).strip()
        except OSError:
            return ""
        if not head.lower().startswith("gitdir:"):
            return ""
        candidate = head.split(":", 1)[1].strip()
        if not os.path.isabs(candidate):
            candidate = os.path.join(root, candidate)
    else:
        candidate = root  # bare repository
    config_path = os.path.join(candidate, "config")
    return config_path if os.path.isfile(config_path) else ""


def detect_partial_clone(
    root: str, debug: bool = False
) -> Dict[str, Any]:
    """
    Answer "does this clone hold every blob?" in well under a second, before
    the expensive log pass runs.

    Returns `{"partial": bool, "shallow": bool, "filter": str, "marker": str}`.

    Three `config --get` reads and one `rev-parse`, all already allow-listed.
    A `.git/config` text fallback catches the one shape the keyed reads miss --
    a promisor remote not named `origin` -- without widening the git
    allow-list to `--get-regexp` for it.
    """
    found = {"partial": False, "shallow": False, "filter": "", "marker": ""}

    for key in PARTIAL_CLONE_KEYS:
        probe = _git(root, "config", ["--get", key], timeout=GIT_QUICK_TIMEOUT_S, debug=debug)
        value = probe["out"].strip() if probe["ok"] else ""
        if not value or value.lower() == "false":
            continue
        found["partial"] = True
        if not found["marker"]:
            found["marker"] = "%s=%s" % (key, value)
        if key.endswith("partialclonefilter"):
            found["filter"] = value

    if not found["partial"]:
        # A promisor remote under some other name.  Read the config file
        # directly: `config --get-regexp` is not in ALLOWED_GIT, and
        # `rev-parse --git-dir` is refused by the safety guard (`--git-dir` is
        # a global redirect, and the guard is right to reject it wherever it
        # appears), so resolve the git directory here instead of widening
        # either table for a fallback.
        config_path = _config_path(root)
        if config_path:
            try:
                with open(config_path, encoding="utf-8", errors="replace") as handle:
                    body = handle.read(200000)
            except OSError:
                body = ""
            for line in body.splitlines():
                stripped = line.strip().lower().replace(" ", "")
                if stripped.startswith("promisor=true"):
                    found["partial"] = True
                    found["marker"] = found["marker"] or "promisor = true in .git/config"
                elif stripped.startswith("partialclonefilter="):
                    found["partial"] = True
                    found["filter"] = stripped.split("=", 1)[1]
                    found["marker"] = "partialclonefilter = %s" % found["filter"]

    shallow = _git(
        root, "rev-parse", ["--is-shallow-repository"], timeout=GIT_QUICK_TIMEOUT_S, debug=debug
    )
    if shallow["ok"] and shallow["out"].strip().lower() == "true":
        found["shallow"] = True
        if not found["marker"]:
            found["marker"] = "shallow repository"

    return found


def plan_log_pass(clone: Dict[str, Any]) -> bool:
    """
    True when the log pass must run in its path-only form.

    A partial clone is the case this exists for.  A shallow clone is NOT: it
    has every blob for the commits it holds, so `--numstat` is honest there and
    the window ladder already reports the truncated history.
    """
    return bool(clone.get("partial"))


def _log_args(
    path_only: bool, max_commits: Optional[int], window_days: Optional[int]
) -> List[str]:
    """The single log pass, in whichever of its two forms the clone supports."""
    args = ["--no-color"]
    if path_only:
        args += ["--name-only", "--no-renames"]
    else:
        args += ["--numstat"]
    args += [
        "--date=iso",
        "--pretty=format:%s%%H%s%%an%s%%ae%s%%ad%s%%P%s%%s"
        % (RECORD_SEP, FIELD_SEP, FIELD_SEP, FIELD_SEP, FIELD_SEP, FIELD_SEP),
    ]
    if max_commits and max_commits > 0:
        args.append("--max-count=%d" % max_commits)
    if window_days and window_days > 0:
        args.append("--since=%d days ago" % window_days)
    return args


def _warn_path_only(warnings: List[str], clone: Dict[str, Any], trigger: str) -> None:
    """One warning, naming the cause, the loss, and the fix."""
    marker = clone.get("marker") or "no marker recorded"
    emit_lib.warn(
        warnings,
        "%s (%s): read path evidence with `git log --name-only --no-renames` and skipped "
        "`--numstat`, which would fetch every blob from the remote one commit at a time -- "
        "measured at 61-79s and then a failed run on blobless clones of chalk and commander.js, "
        "inside a tool that promises no network calls. Per-file CHURN is what is lost: "
        "`hotspots[].churn` is 0 for every row, so rank hotspots by `commits` and never quote "
        "churn from this run. Conventions, branch naming, co-change, hotspots, directory "
        "hotspots, test discipline, revert rate and authorship are all computed from paths and "
        "are intact, with one caveat worth a sentence in the plan: `--no-renames` reads a rename "
        "as a delete plus an add, so a renamed path can carry one more commit here than on a full "
        "clone (measured on chalk: 3 of 20 hotspot rows off by one, no row missing or added). To "
        "get churn, clone without `--filter=blob:none`, or run `git fetch --refetch` in this clone."
        % (trigger, marker),
    )


# ---------------------------------------------------------------------------
# Log parsing
# ---------------------------------------------------------------------------


def _unquote_path(path: str) -> str:
    """
    One git-quoted path -> the name it has in the working tree.

    git quotes a path whose name carries an unusual byte, and what it puts
    between the quotes are BYTES in octal: `src/café.py` comes back as
    `"src/caf\\303\\251.py"`, where `\\303\\251` is ONE UTF-8 code point, not two
    characters.  So every escape is accumulated into a byte buffer and the
    buffer is decoded once, at the end.  Decoding escape-by-escape -- which is
    what `unicode_escape` does, latin-1 style -- yields `src/cafÃ©.py`: a path
    that is not on disk, and therefore a live file reported `still_exists:
    false`.  That was the defect this docstring replaces.

    `errors="replace"` and not `surrogateescape`: a name whose bytes are not
    UTF-8 at all (a latin-1 filename on Linux) has no faithful str form, and
    the surrogates that `surrogateescape` produces cannot be written to stdout
    -- `emit` serializes with `ensure_ascii=False`, so a lone surrogate raises
    UnicodeEncodeError and takes the whole run down.  U+FFFD costs that one
    row's `still_exists`; a crash costs the run.  It is also what every other
    decode in this file already does.

    A no-op on a path that arrives unquoted, which is what `core.quotepath=false`
    produces for anything but a quote or a backslash in the name.
    """
    if not (len(path) >= 2 and path[0] == '"' and path[-1] == '"'):
        return path
    inner = path[1:-1]
    out = bytearray()
    index = 0
    end = len(inner)
    while index < end:
        char = inner[index]
        if char != "\\":
            out.extend(char.encode("utf-8", "replace"))
            index += 1
            continue
        if index + 1 >= end:  # a trailing backslash: keep it literally
            out.extend(b"\\")
            break
        marker = inner[index + 1]
        if marker in C_ESCAPES:
            out.append(C_ESCAPES[marker])
            index += 2
            continue
        if marker in OCTAL_DIGITS:
            digits = ""
            cursor = index + 1
            while cursor < end and len(digits) < 3 and inner[cursor] in OCTAL_DIGITS:
                digits += inner[cursor]
                cursor += 1
            value = int(digits, 8)
            if value <= 0xFF:
                out.append(value)
                index = cursor
                continue
            out.extend(inner[index:cursor].encode("utf-8", "replace"))
            index = cursor
            continue
        if marker in ("x", "X"):  # git does not emit \xNN; read it if it does
            digits = ""
            cursor = index + 2
            while cursor < end and len(digits) < 2 and inner[cursor] in HEX_DIGITS:
                digits += inner[cursor]
                cursor += 1
            if digits:
                out.append(int(digits, 16))
                index = cursor
                continue
        # An escape git has no meaning for: drop the backslash, keep the char.
        out.extend(marker.encode("utf-8", "replace"))
        index += 2
    return out.decode("utf-8", "replace")


def _decode_path_field(field: str) -> str:
    """
    One path field from a `git log` line -> one working-tree path.

    Four shapes reach here, and the rename ones are why this is not just
    `_resolve_rename(_unquote_path(field))`:

        plain                    src/api.py
        quoted                   "src/caf\\303\\251.py"
        rename, quoted sides     "src/caf\\303\\251.py" => src/api.py
        rename, brace-compressed src/{api.py => core.py}

    With quoting on, a rename arrives as `old => new` with each SIDE quoted on
    its own -- measured on git 2.49; the brace form appears only when NEITHER
    side needs quoting.  Stripping one pair of quotes off the whole field, as
    this used to, left `src/caf\\303\\251.py" => "src/api.py` and then split
    THAT on `=>`.  A fully quoted field is never a rename, because git's ` => `
    separator sits outside the quotes.
    """
    field = field.strip()
    if '"' in field:
        pair = RENAME_QUOTED_PAIR_RE.match(field)
        if pair:
            return _unquote_path(pair.group("new").strip())
        if QUOTED_PATH_RE.match(field):
            return _unquote_path(field)
    return _resolve_rename(_unquote_path(field))


def _resolve_rename(path: str) -> str:
    """`src/{a => b}/f.ts` -> `src/b/f.ts`; `old.ts => new.ts` -> `new.ts`."""
    if "=>" not in path:
        return path
    match = RENAME_BRACE_RE.match(path)
    if match:
        joined = match.group(1) + match.group(3) + match.group(4)
        while "//" in joined:
            joined = joined.replace("//", "/")
        return joined.strip()
    return path.split("=>")[-1].strip()


def _parse_numstat_line(line: str) -> Optional[Tuple[int, int, str]]:
    parts = line.split("\t")
    if len(parts) < 3:
        return None
    added_raw, deleted_raw = parts[0].strip(), parts[1].strip()
    path = _decode_path_field("\t".join(parts[2:]))
    if not path:
        return None
    added = 0 if added_raw in ("-", "") else _safe_int(added_raw)
    deleted = 0 if deleted_raw in ("-", "") else _safe_int(deleted_raw)
    if added is None or deleted is None:
        return None
    return (added, deleted, path)


def _safe_int(value: str) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_path_only_line(line: str) -> Optional[Tuple[int, int, str]]:
    """
    One line of `git log --name-only --no-renames` output: a bare path, no
    counts.  Returned in the same `(added, deleted, path)` shape as numstat so
    every downstream analysis is unchanged -- churn is the only thing that
    degrades, and it degrades to 0.

    `--no-renames` is not a stylistic choice.  Inexact rename detection reads
    blob CONTENT to score similarity, so plain `--name-only` still fetches
    blobs on a partial clone: re-measured 2026-09-05 on a fresh blobless chalk
    clone, 6.98s with renames on versus 0.010s with `--no-renames`.

    A rename therefore reads as one path deleted and one added, where the
    full-clone `--numstat` pass sees a single `old => new` entry that
    `_resolve_rename` folds onto the destination.  That is a real, small
    divergence in the counts -- not the "same shape either way" an earlier
    version of this docstring claimed.  See the PARTIAL CLONES section of the
    module docstring for what it measured out at.
    """
    path = _decode_path_field(line)
    if not path or "\t" in path:
        return None
    return (0, 0, path)


def _parse_log(text: str, path_only: bool = False) -> List[Dict[str, Any]]:
    """
    Turn the single `git log --numstat --pretty=format:<RS>...<US>...` pass
    into commit records.  One pass, no per-commit shelling out.

    `path_only=True` parses the degraded `--name-only --no-renames` form used
    on a partial clone (see `plan_log_pass`): identical records, with `added`
    and `deleted` zero.
    """
    commits = []  # type: List[Dict[str, Any]]
    if not text:
        return commits
    for chunk in text.split(RECORD_SEP):
        if not chunk.strip():
            continue
        fields = chunk.split(FIELD_SEP)
        if len(fields) < 6:
            continue
        tail = fields[5].split("\n")
        subject = tail[0].strip()
        files = []  # type: List[Tuple[int, int, str]]
        for line in tail[1:]:
            line = line.rstrip("\r")
            if not line.strip():
                continue
            parsed = (
                _parse_path_only_line(line) if path_only else _parse_numstat_line(line)
            )
            if parsed is not None:
                files.append(parsed)
        parents = [p for p in fields[4].split(" ") if p]
        commits.append(
            {
                "hash": fields[0].strip(),
                "author": fields[1].strip(),
                "email": fields[2].strip(),
                "date": fields[3].strip(),
                "parents": parents,
                "is_merge": len(parents) > 1,
                "subject": subject,
                "files": files,
            }
        )
    return commits


# ---------------------------------------------------------------------------
# Path predicates
# ---------------------------------------------------------------------------


def _is_lockfile(path: str) -> bool:
    return os.path.basename(path).lower() in LOCKFILE_BASENAMES


def _is_generated(path: str) -> bool:
    lowered = path.lower()
    for segment in lowered.split("/")[:-1]:
        if segment in GENERATED_DIR_SEGMENTS:
            return True
    for suffix in GENERATED_SUFFIXES:
        if lowered.endswith(suffix):
            return True
    return False


def _is_binary_asset(path: str) -> bool:
    lowered = path.lower()
    return lowered.endswith(BINARY_ASSET_SUFFIXES)


def _is_noise_path(path: str) -> bool:
    """Excluded from co-change and hotspots: no rule can usefully target it."""
    return _is_lockfile(path) or _is_generated(path) or _is_binary_asset(path)


def _is_test_path(path: str) -> bool:
    lowered = path.lower()
    for segment in lowered.split("/")[:-1]:
        if segment in TEST_DIR_SEGMENTS:
            return True
    for pattern in TEST_FILE_PATTERNS:
        if pattern.search(path):
            return True
    return False


def _dir_depth2(path: str) -> str:
    parts = [p for p in path.split("/") if p]
    if len(parts) <= 1:
        return "(root)"
    return "/".join(parts[: min(2, len(parts) - 1)])


# ---------------------------------------------------------------------------
# Recency + liveness
# ---------------------------------------------------------------------------

DAY_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})")


def _day(iso_date: str) -> str:
    """
    `2026-05-29 18:03:21 +0900` -> `2026-05-29`.

    Dates are compared and reported as calendar days, not instants: the day is
    lexicographically sortable without parsing, and it is the granularity
    `mapping-rules.md`'s 90-day recency gate works in.  Comparing full
    timestamps as strings would be wrong across author timezones; comparing
    days is off by at most one, which no gate is sensitive to.
    """
    match = DAY_RE.match((iso_date or "").strip())
    return match.group(1) if match else ""


def _span(first: str, last: str, day: str) -> Tuple[str, str]:
    """Fold one more day into a (first_seen, last_seen) span."""
    if not day:
        return (first, last)
    if not first or day < first:
        first = day
    if not last or day > last:
        last = day
    return (first, last)


def _exists_checker(repo_root: str):
    """
    A memoised `path -> bool` for "is this still in the working tree".

    A hotspot or co-change cluster whose files were deleted is dead evidence:
    the support count is real history, but no rule, hook or skill can usefully
    target a path that is gone.  `lexists` so a tracked-but-broken symlink
    still counts as present.  Memoised because the same path is asked about
    once per row and hotspots overlap clusters.
    """
    cache = {}  # type: Dict[str, bool]

    def check(path: str, directory: bool = False) -> bool:
        if not repo_root or not path:
            return True  # cannot tell; never call live evidence dead
        if path == "(root)":
            return True
        key = ("d:" if directory else "f:") + path
        cached = cache.get(key)
        if cached is not None:
            return cached
        full = os.path.join(repo_root, *[p for p in path.split("/") if p])
        try:
            value = os.path.isdir(full) if directory else os.path.lexists(full)
        except OSError:  # pragma: no cover - defensive (permissions, ELOOP)
            value = True
        cache[key] = value
        return value

    return check


# ---------------------------------------------------------------------------
# Analyses
# ---------------------------------------------------------------------------


def _median(values: Sequence[int]) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return int(ordered[mid])
    return int(round((ordered[mid - 1] + ordered[mid]) / 2.0))


def _pct(part: int, whole: int) -> float:
    if not whole:
        return 0.0
    return round(part / float(whole), 4)


def _strip_prefixes(subject: str) -> str:
    """Remove a conventional-commit and/or ticket prefix from a subject."""
    text = subject
    match = CONVENTIONAL_RE.match(text)
    if match:
        text = text[match.end():]
    ticket = TICKET_RE.match(text)
    if ticket:
        text = text[ticket.end():]
    return text.strip()


def _looks_imperative(subject: str) -> bool:
    """
    Heuristic mood check on the first word of the subject body.

    `textnorm.VERBS` decides it outright; otherwise a past-tense (`-ed`),
    gerund (`-ing`) or third-person (`-s`) ending votes no.  Anything else is
    counted as imperative, which is the common case for domain verbs the
    lexicon does not know ("wire", "backfill", "vendor").
    """
    body = _strip_prefixes(subject)
    words = re.findall(r"[A-Za-z][A-Za-z'-]*", body)
    if not words:
        return False
    head = words[0].lower()
    if head in textnorm.VERBS:
        return True
    if head.endswith("ing") or head.endswith("ed"):
        return False
    if head.endswith("s") and not head.endswith("ss") and len(head) > 3:
        return False
    return True


def analyze_conventions(commits: Sequence[Dict[str, Any]], hits: List[str]) -> Dict[str, Any]:
    """Conventional-commit share, type/scope vocabulary, tickets, mood."""
    subjects = [c["subject"] for c in commits if c["subject"]]
    total = len(subjects)
    types = {}  # type: Dict[str, int]
    scopes = {}  # type: Dict[str, int]
    ticket_keys = {}  # type: Dict[str, int]
    conventional = 0
    ticketed = 0
    imperative = 0
    lengths = []  # type: List[int]

    for subject in subjects:
        lengths.append(len(subject))
        match = CONVENTIONAL_RE.match(subject)
        if match:
            conventional += 1
            kind = match.group(1)
            types[kind] = types.get(kind, 0) + 1
            scope = (match.group(3) or "").strip()
            if scope:
                for piece in re.split(r"[,/]", scope):
                    piece = piece.strip()
                    if piece and len(piece) <= 40:
                        scopes[piece] = scopes.get(piece, 0) + 1
        rest = subject[match.end():] if match else subject
        ticket = TICKET_RE.match(rest) or TICKET_RE.match(subject)
        if ticket:
            ticketed += 1
            key = ticket.group(1)
            ticket_keys[key] = ticket_keys.get(key, 0) + 1
        if _looks_imperative(subject):
            imperative += 1

    ticket_pattern = ""
    if ticketed and total and (ticketed / float(total)) >= 0.10:
        ranked = sorted(ticket_keys.items(), key=lambda kv: (-kv[1], kv[0]))
        dominant = [k for k, v in ranked if v >= max(2, int(0.10 * ticketed))]
        if len(dominant) == 1:
            ticket_pattern = "%s-<number>" % dominant[0]
        elif dominant:
            ticket_pattern = "[A-Z]{2,10}-<number> (keys: %s)" % ", ".join(dominant[:5])
        else:
            ticket_pattern = "[A-Z]{2,10}-<number>"

    return {
        "conventional_pct": _pct(conventional, total),
        "types": _ranked(types, MAX_TYPES, "type"),
        "scopes": [
            {"scope": _clean(name, hits), "count": count}
            for name, count in _rank_pairs(scopes, MAX_SCOPES)
        ],
        "ticket_prefix_pct": _pct(ticketed, total),
        "ticket_pattern": ticket_pattern,
        "subject_median_len": _median(lengths),
        "imperative_pct": _pct(imperative, total),
    }


def _rank_pairs(counter: Dict[str, int], limit: int) -> List[Tuple[str, int]]:
    return sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]


def _ranked(counter: Dict[str, int], limit: int, key_name: str) -> List[Dict[str, Any]]:
    return [{key_name: name, "count": count} for name, count in _rank_pairs(counter, limit)]


def _classify_branch(name: str, people: Iterable[str]) -> str:
    """Map one branch name to a naming pattern, or "" if it carries none."""
    raw = name.strip()
    if not raw:
        return ""
    # `origin/feat/x`, `refs/heads/feat/x` -> `feat/x`
    for lead in ("refs/heads/", "refs/remotes/"):
        if raw.startswith(lead):
            raw = raw[len(lead):]
    parts = raw.split("/")
    if parts and parts[0] in ("origin", "upstream", "fork") and len(parts) > 1:
        parts = parts[1:]
        raw = "/".join(parts)
    if raw.lower() in TRUNK_BRANCHES:
        return ""

    if TICKET_ANYWHERE_RE.match(raw.upper()) and "-" in raw:
        return "<TICKET-123>-* (ticket id)"

    if len(parts) == 1:
        head = parts[0].lower()
        if TICKET_ANYWHERE_RE.match(parts[0].upper()):
            return "<TICKET-123>-* (ticket id)"
        if head.split("-")[0] in BRANCH_TYPE_PREFIXES:
            return "%s-* (dash separated)" % head.split("-")[0]
        return "flat (no prefix)"

    prefix = parts[0].lower()
    if prefix in BRANCH_TYPE_PREFIXES:
        return "%s/*" % prefix
    if prefix in people:
        return "user/* (owner prefix)"
    if TICKET_ANYWHERE_RE.match(parts[0].upper()):
        return "<TICKET-123>/*"
    return "%s/*" % prefix


def _people_tokens(commits: Sequence[Dict[str, Any]], config_name: str) -> frozenset:
    """Name-ish tokens used to tell `ravi/fix-x` from `feat/fix-x`."""
    tokens = set()

    def absorb(source: str) -> None:
        if not source:
            return
        for piece in re.split(r"[\s._+-]+", source):
            piece = piece.strip().lower()
            if 2 <= len(piece) <= 24 and piece.isalpha():
                tokens.add(piece)
        # `ravisojitra/fix-x` should read as a person too, so keep the
        # squashed form of the whole name / handle alongside its parts.
        squashed = re.sub(r"[^a-z]", "", source.lower())
        if 4 <= len(squashed) <= 32:
            tokens.add(squashed)

    for commit in commits:
        absorb(commit.get("author", ""))
        absorb((commit.get("email", "") or "").split("@")[0])
    absorb(config_name or "")
    return frozenset(tokens)


def analyze_branch_naming(
    branch_names: Sequence[str],
    commits: Sequence[Dict[str, Any]],
    config_name: str,
) -> List[Dict[str, Any]]:
    """
    Prefix patterns from local branch refs plus the branch names that survive
    in merge-commit subjects (a squash-merge workflow leaves no refs behind,
    but the merge subjects still carry the names).
    """
    people = _people_tokens(commits, config_name)
    candidates = list(branch_names)
    for commit in commits:
        subject = commit["subject"]
        match = MERGE_BRANCH_RE.match(subject)
        if match:
            candidates.append(match.group(1))
            continue
        match = MERGE_PR_RE.match(subject)
        if match:
            ref = match.group(1)
            # GitHub writes `Merge pull request #12 from <owner>/<branch>`, and
            # `<branch>` may itself contain slashes.  The leading segment is
            # always the fork owner, never part of the naming convention.
            if ":" in ref:
                ref = ref.split(":", 1)[1]
            else:
                pieces = ref.split("/")
                if len(pieces) >= 2:
                    ref = "/".join(pieces[1:])
            candidates.append(ref)

    counts = {}  # type: Dict[str, int]
    seen = set()
    for name in candidates:
        key = name.strip()
        if not key or key in seen:
            continue  # a branch that is both a live ref and a merge subject counts once
        seen.add(key)
        pattern = _classify_branch(key, people)
        if pattern:
            counts[pattern] = counts.get(pattern, 0) + 1
    return [
        {"pattern": pattern, "count": count}
        for pattern, count in _rank_pairs(counts, MAX_BRANCH_PATTERNS)
    ]


def analyze_cochange(
    commits: Sequence[Dict[str, Any]],
    warnings: List[str],
    repo_root: str = "",
) -> List[Dict[str, Any]]:
    """
    Files that change together.

    Two passes over the already-parsed commits (no extra git calls):

      1. count how many commits touch each interesting file;
      2. pair only files seen in >= MIN_COCHANGE_SUPPORT commits.  A pair can
         never have more support than its rarer member, so this pre-filter is
         lossless and it collapses the pair table by orders of magnitude.

    Triples are built from strong pairs: all three constituent pairs must
    already qualify, then the triple's own co-occurrence is counted.

    confidence = support / max(individual commit counts).  Sorted by
    confidence desc, then support desc.  Capped at MAX_COCHANGE_CLUSTERS.

    Each emitted cluster is dated (`first_seen` / `last_seen`, from the commits
    that actually contain all of its paths) and marked `still_exists` -- false
    as soon as ONE of its paths has left the working tree, because a cluster is
    a claim about files changing together and a deleted member cannot change.
    """
    file_counts = {}  # type: Dict[str, int]
    #: (sorted paths, the same as a set, commit day) -- the set is kept because
    #: the triple pass and the dating pass both do membership tests over it.
    commit_sets = []  # type: List[Tuple[List[str], frozenset, str]]
    skipped_bulk = 0

    for commit in commits:
        if commit["is_merge"]:
            continue
        paths = []
        for _added, _deleted, path in commit["files"]:
            if _is_noise_path(path):
                continue
            paths.append(path)
        paths = sorted(set(paths))
        if len(paths) < 2:
            continue
        if len(paths) > BULK_COMMIT_FILE_LIMIT:
            skipped_bulk += 1
            continue
        commit_sets.append((paths, frozenset(paths), _day(commit.get("date", ""))))
        for path in paths:
            file_counts[path] = file_counts.get(path, 0) + 1

    if skipped_bulk:
        emit_lib.warn(
            warnings,
            "co-change: skipped %d bulk commit(s) touching more than %d files"
            % (skipped_bulk, BULK_COMMIT_FILE_LIMIT),
        )

    frequent = set(p for p, c in file_counts.items() if c >= MIN_COCHANGE_SUPPORT)
    if len(frequent) < 2:
        return []

    pair_counts = {}  # type: Dict[Tuple[str, str], int]
    truncated = False
    for paths, _path_set, _day_ in commit_sets:
        interesting = [p for p in paths if p in frequent]
        if len(interesting) < 2:
            continue
        for i in range(len(interesting)):
            for j in range(i + 1, len(interesting)):
                key = (interesting[i], interesting[j])
                pair_counts[key] = pair_counts.get(key, 0) + 1
        if len(pair_counts) > MAX_PAIR_ENTRIES and not truncated:
            truncated = True
    if truncated:
        emit_lib.warn(
            warnings,
            "co-change: pair table exceeded %d entries; results may be partial"
            % MAX_PAIR_ENTRIES,
        )

    strong = {
        key: count
        for key, count in pair_counts.items()
        if count >= MIN_COCHANGE_SUPPORT
    }
    if not strong:
        return []

    # --- triples, built only from files that already form strong pairs ------
    neighbours = {}  # type: Dict[str, set]
    for (left, right) in strong:
        neighbours.setdefault(left, set()).add(right)
        neighbours.setdefault(right, set()).add(left)

    triple_candidates = set()
    for (left, right) in strong:
        shared = neighbours.get(left, set()) & neighbours.get(right, set())
        for third in shared:
            triple_candidates.add(tuple(sorted((left, right, third))))
        if len(triple_candidates) > 4000:
            break

    triple_counts = {}  # type: Dict[Tuple[str, str, str], int]
    if triple_candidates:
        members = set()
        for triple in triple_candidates:
            members.update(triple)
        for _paths, path_set, _day_ in commit_sets:
            present = members.intersection(path_set)
            if len(present) < 3:
                continue
            for triple in triple_candidates:
                if present.issuperset(triple):
                    triple_counts[triple] = triple_counts.get(triple, 0) + 1

    clusters = []  # type: List[Dict[str, Any]]
    for triple, support in triple_counts.items():
        if support < MIN_COCHANGE_SUPPORT:
            continue
        denominator = max(file_counts.get(p, 1) for p in triple)
        clusters.append(
            {
                "paths": list(triple),
                "support": support,
                "confidence": round(support / float(denominator or 1), 3),
            }
        )
    for (left, right), support in strong.items():
        denominator = max(file_counts.get(left, 1), file_counts.get(right, 1))
        clusters.append(
            {
                "paths": [left, right],
                "support": support,
                "confidence": round(support / float(denominator or 1), 3),
            }
        )

    # Confidence, then support, then size: on a tie the triple must come out
    # ahead of the pairs it contains, so the redundancy filter below can see
    # it first and drop them.
    clusters.sort(
        key=lambda c: (-c["confidence"], -c["support"], -len(c["paths"]), c["paths"])
    )

    # Redundancy filter.  Two clusters with the SAME support that share two or
    # more files describe one change-set seen through different subsets -- the
    # pair inside an emitted triple, or three overlapping 3-subsets of the same
    # four files.  Keep the first (largest, by the sort above) and drop the
    # rest, so fifteen slots hold fifteen distinct signals.  Sharing a single
    # file is not redundancy: `schema.ts + a.ts` and `schema.ts + b.ts` are two
    # real facts about `schema.ts`.
    # Emitted clusters accumulate into "families" -- a family is the union of
    # everything already reported at one support level.  A candidate that adds
    # no new file to a family it overlaps is fully implied by what the reader
    # has already seen.
    emitted = []  # type: List[Dict[str, Any]]
    families = []  # type: List[List[Any]]
    for cluster in clusters:
        paths = set(cluster["paths"])
        support = cluster["support"]
        redundant = False
        home = None  # type: Optional[List[Any]]
        for family in families:
            known, family_support = family[0], family[1]
            if family_support != support or not (paths & known):
                continue
            if paths.issubset(known) or len(paths & known) >= 2:
                redundant = True
                break
            if home is None:
                home = family
        if redundant:
            continue
        emitted.append(cluster)
        if home is None:
            families.append([set(paths), support])
        else:
            home[0].update(paths)
        if len(emitted) >= MAX_COCHANGE_CLUSTERS:
            break

    # --- date and liveness, for the recency gate ----------------------------
    # One more pass over commit_sets, but only for the <= 15 emitted clusters:
    # a cluster is "seen" in a commit that contains every one of its paths,
    # which is the same predicate that produced its support.
    member_sets = [frozenset(c["paths"]) for c in emitted]
    spans = [["", ""] for _ in emitted]
    for _paths, path_set, day in commit_sets:
        if not day:
            continue
        for index, members in enumerate(member_sets):
            if members <= path_set:
                spans[index][0], spans[index][1] = _span(
                    spans[index][0], spans[index][1], day
                )
    exists = _exists_checker(repo_root)
    for index, cluster in enumerate(emitted):
        cluster["first_seen"] = spans[index][0]
        cluster["last_seen"] = spans[index][1]
        cluster["still_exists"] = all(exists(p) for p in cluster["paths"])
    return emitted


def analyze_hotspots(
    commits: Sequence[Dict[str, Any]], repo_root: str = ""
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Per-file commits/authors/churn, and the same rolled up to depth 2.

    Both lists are dated (`first_seen` / `last_seen`, from the commits that
    touched the path) and carry `still_exists`, so the recency gate applies to
    git evidence and not only to transcript request shapes.  A file with 40
    commits that was deleted last spring is history, not a hotspot.
    """
    per_file = {}  # type: Dict[str, Dict[str, Any]]
    per_dir = {}  # type: Dict[str, Dict[str, Any]]

    for commit in commits:
        if commit["is_merge"]:
            continue
        author = commit["author"]
        day = _day(commit.get("date", ""))
        touched_dirs = set()
        for added, deleted, path in commit["files"]:
            if _is_noise_path(path):
                continue
            entry = per_file.get(path)
            if entry is None:
                entry = {"commits": 0, "authors": set(), "churn": 0, "first": "", "last": ""}
                per_file[path] = entry
            entry["commits"] += 1
            entry["authors"].add(author)
            entry["churn"] += added + deleted
            entry["first"], entry["last"] = _span(entry["first"], entry["last"], day)
            touched_dirs.add(_dir_depth2(path))
        for directory in touched_dirs:
            entry = per_dir.get(directory)
            if entry is None:
                entry = {"commits": 0, "first": "", "last": ""}
                per_dir[directory] = entry
            entry["commits"] += 1
            entry["first"], entry["last"] = _span(entry["first"], entry["last"], day)

    hotspots = sorted(
        per_file.items(),
        key=lambda kv: (-kv[1]["commits"], -kv[1]["churn"], kv[0]),
    )[:MAX_HOTSPOTS]
    directory_hotspots = sorted(
        per_dir.items(), key=lambda kv: (-kv[1]["commits"], kv[0])
    )[:MAX_DIRECTORY_HOTSPOTS]

    exists = _exists_checker(repo_root)
    return (
        [
            {
                "path": path,
                "commits": data["commits"],
                "authors": len(data["authors"]),
                "churn": data["churn"],
                "first_seen": data["first"],
                "last_seen": data["last"],
                "still_exists": exists(path),
            }
            for path, data in hotspots
        ],
        [
            {
                "path": path,
                "commits": data["commits"],
                "first_seen": data["first"],
                "last_seen": data["last"],
                "still_exists": exists(path, directory=True),
            }
            for path, data in directory_hotspots
        ],
    )


def analyze_test_discipline(commits: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Share of non-merge commits that touch a test path, plus where tests live."""
    considered = 0
    with_tests = 0
    test_dirs = {}  # type: Dict[str, int]
    for commit in commits:
        if commit["is_merge"]:
            continue
        considered += 1
        touched = False
        for _added, _deleted, path in commit["files"]:
            if _is_test_path(path):
                touched = True
                directory = os.path.dirname(path) or "(root)"
                test_dirs[directory] = test_dirs.get(directory, 0) + 1
        if touched:
            with_tests += 1
    return {
        "commits_touching_tests_pct": _pct(with_tests, considered),
        "test_paths": [path for path, _count in _rank_pairs(test_dirs, MAX_TEST_PATHS)],
    }


def analyze_reverts(commits: Sequence[Dict[str, Any]]) -> float:
    subjects = [c["subject"] for c in commits if c["subject"]]
    if not subjects:
        return 0.0
    reverts = sum(1 for s in subjects if REVERT_RE.match(s))
    return _pct(reverts, len(subjects))


def analyze_contributors(
    authors: Sequence[Dict[str, Any]], hits: List[str]
) -> List[Dict[str, Any]]:
    """
    The author table: people first, machines after, each side by commit count.

    Ordering is deliberate and is not "top 20 by commits".  The list is capped
    at MAX_CONTRIBUTORS, and on a repository where release automation
    out-commits everyone -- which is most monorepos -- a plain commit-count
    sort fills the cap with machines and truncates the people away.  Every
    consumer of this list is counting PEOPLE (`interview.md` Q5 gates on
    non-bot rows >= 2), so a bot must never be able to displace a human.

    `email_domain` is the domain half of the author's address; the local part
    is the identifying half and is never emitted.  `bot_reason` is empty on a
    person and carries the sentence that classified a machine, so the
    exclusion can be audited from the JSON alone.
    """
    ordered = sorted(
        authors,
        key=lambda row: (bool(row["is_bot"]), -row["commits"], row["name"].lower()),
    )[:MAX_CONTRIBUTORS]
    return [
        {
            "name": _clean(row["name"], hits),
            "commits": row["commits"],
            "email_domain": _clean(row["email_domain"], hits),
            "is_bot": bool(row["is_bot"]),
            "bot_reason": row["bot_reason"],
        }
        for row in ordered
    ]


def _warn_authorship(
    authorship: Dict[str, Any], include_bots: bool, warnings: List[str]
) -> None:
    """Say what was set aside, and never let a silent exclusion change a count."""
    bots = authorship["commits_bot"]
    names = ", ".join(row["name"] for row in authorship["bot_authors"][:4]) or "unnamed"
    if include_bots:
        if bots:
            emit_lib.warn(
                warnings,
                "authorship: --include-bots is on, so %d bot-authored commit(s) (%s) are "
                "INCLUDED in every statistic; release automation is the most regular "
                "committer in most repositories and can dominate co-change and hotspots "
                "-- do not build a path-scoped rule out of a version bump" % (bots, names),
            )
        return
    if bots:
        emit_lib.warn(
            warnings,
            "authorship: excluded %d bot-authored commit(s) by %d machine(s) (%s) from "
            "commit conventions, branch naming, co-change, hotspots, test discipline and "
            "the revert rate; they are still counted in `authorship` and listed in "
            "`contributors[]`. Pass --include-bots for the raw view"
            % (bots, len(authorship["bot_authors"]), names),
        )
    if authorship["commits_total"] and authorship["bot_pct"] >= 0.5:
        emit_lib.warn(
            warnings,
            "authorship: %d%% of the commits in this window are automation -- that is a "
            "finding about how this repository is maintained, not evidence for an "
            "artifact" % int(round(authorship["bot_pct"] * 100)),
        )
    if authorship["commits_total"] and not authorship["commits_human"]:
        emit_lib.warn(
            warnings,
            "authorship: every commit in this window is bot-authored, so there is no "
            "human git evidence: every percentage below is computed over 0 commits and "
            "must not be read as a convention. Widen --days, or pass --include-bots if "
            "the automation itself is what you mean to study",
        )


# ---------------------------------------------------------------------------
# PR patterns (the optional, disableable, network-touching path)
# ---------------------------------------------------------------------------


def _empty_pr_patterns() -> Dict[str, Any]:
    return {"available": False, "title_convention": "", "body_sections": [], "sample": 0}


def analyze_pr_patterns(
    repo_root: str,
    no_gh: bool,
    warnings: List[str],
    hits: List[str],
    debug: bool = False,
) -> Dict[str, Any]:
    """
    Best-effort PR title/body conventions via `gh`.

    Every failure mode -- flag, missing binary, unauthenticated, timeout, bad
    JSON, empty list -- returns `{"available": false, ...}` plus a warning.
    Nothing here can fail the run.
    """
    result = _empty_pr_patterns()
    if no_gh:
        emit_lib.warn(warnings, "pr_patterns: skipped (--no-gh)")
        return result
    if shutil.which("gh") is None:
        emit_lib.warn(warnings, "pr_patterns: skipped (gh not on PATH)")
        return result

    auth = _gh(["auth", "status"], timeout=GH_AUTH_TIMEOUT_S, debug=debug, cwd=repo_root)
    if not auth["ok"]:
        emit_lib.warn(
            warnings, "pr_patterns: skipped (gh not authenticated: %s)" % auth["reason"]
        )
        return result

    listing = _gh(
        [
            "pr",
            "list",
            "--state",
            "merged",
            "--limit",
            str(GH_PR_LIMIT),
            "--json",
            "title,body",
        ],
        timeout=GH_LIST_TIMEOUT_S,
        debug=debug,
        cwd=repo_root,
    )
    if not listing["ok"]:
        emit_lib.warn(warnings, "pr_patterns: gh pr list failed (%s)" % listing["reason"])
        return result

    try:
        payload = json.loads(listing["out"] or "[]")
    except ValueError as exc:
        emit_lib.warn(warnings, "pr_patterns: could not parse gh output (%s)" % exc)
        return result
    if not isinstance(payload, list) or not payload:
        emit_lib.warn(warnings, "pr_patterns: no merged pull requests found")
        return result

    titles = []  # type: List[str]
    bodies = []  # type: List[str]
    for item in payload:
        if not isinstance(item, dict):
            continue
        titles.append(_clean(str(item.get("title") or ""), hits))
        bodies.append(_clean(str(item.get("body") or "")[:8000], hits))

    sample = len(titles)
    if not sample:
        emit_lib.warn(warnings, "pr_patterns: gh returned no usable titles")
        return result

    conventional = sum(1 for t in titles if CONVENTIONAL_RE.match(t))
    ticketed = sum(1 for t in titles if TICKET_RE.match(t))
    squash_ref = sum(1 for t in titles if MERGE_PR_SQUASH_RE.search(t))

    parts = []  # type: List[str]
    if conventional and conventional / float(sample) >= 0.4:
        parts.append("conventional-commit titles (%d/%d)" % (conventional, sample))
    if ticketed and ticketed / float(sample) >= 0.3:
        parts.append("ticket-prefixed titles (%d/%d)" % (ticketed, sample))
    if squash_ref and squash_ref / float(sample) >= 0.5:
        parts.append("squash-merge `(#123)` suffix (%d/%d)" % (squash_ref, sample))
    if not parts:
        parts.append("free-form titles (no dominant convention in %d PRs)" % sample)

    section_counts = {}  # type: Dict[str, int]
    for body in bodies:
        if not body.strip():
            continue
        seen = set()
        for pattern in (PR_HEADING_RE, PR_BOLD_HEADING_RE):
            for heading in pattern.findall(body):
                key = re.sub(r"[^a-z0-9 ]+", "", heading.lower()).strip()
                if not key or len(key) > 48:
                    continue
                seen.add(key)
        for key in seen:
            section_counts[key] = section_counts.get(key, 0) + 1

    threshold = max(2, int(round(0.2 * sample)))
    sections = [
        name
        for name, count in _rank_pairs(section_counts, MAX_PR_BODY_SECTIONS * 2)
        if count >= threshold
    ][:MAX_PR_BODY_SECTIONS]

    result["available"] = True
    result["title_convention"] = "; ".join(parts)
    result["body_sections"] = sections
    result["sample"] = sample
    return result


# ---------------------------------------------------------------------------
# Payload assembly
# ---------------------------------------------------------------------------


def empty_window(days: int, mode: str = "", min_commits: int = 0) -> Dict[str, Any]:
    """
    The `window` block with every key present.

    `days` is the window in force (0 = all history).  `mode` is `adaptive` when
    the ladder chose it, `explicit` when `--days` imposed it, `""` on a
    degraded run where no choice was ever made.  `steps` is the probe ladder,
    `[]` under `--days`.  `min_commits` is the floor that was applied, and 0
    under `--days` because no floor was consulted.  `reason` is one sentence
    naming the counts the choice rests on -- the plan quotes it, so it must
    read as a sentence and must never claim a window it did not use.
    """
    return {
        "days": days,
        "commits_analyzed": 0,
        "first": "",
        "last": "",
        "mode": mode,
        "min_commits": min_commits,
        "steps": [],
        "reason": "",
    }


def _describe_days(days: int) -> str:
    return "all history" if not days else "%dd" % days


def _count_commits(root: str, days: int, debug: bool = False) -> Optional[int]:
    """
    How many commits a window holds, without reading any of them.

    `rev-list --count` walks the same revisions `git log` would but emits a
    single integer -- no `--numstat`, no subjects, nothing to parse -- so
    probing four rungs costs a fraction of one real log pass.  Returns None
    when the count could not be taken (no HEAD in an empty repo, a timeout);
    the caller falls back rather than guessing.
    """
    args = ["--count", "HEAD"]
    if days and days > 0:
        args.append("--since=%d days ago" % days)
    result = _git(root, "rev-list", args, timeout=GIT_QUICK_TIMEOUT_S, debug=debug)
    if not result["ok"]:
        return None
    return _safe_int(result["out"].strip().splitlines()[0] if result["out"].strip() else "")


def choose_window(
    root: str,
    explicit_days: Optional[int],
    min_commits: int,
    max_commits: int,
    warnings: List[str],
    debug: bool = False,
) -> Dict[str, Any]:
    """
    Decide which window to mine, and record why.

    `explicit_days is not None` means the user named a window: it is used
    verbatim, the ladder never runs, and `mode` says `explicit`.

    Otherwise walk ADAPTIVE_LADDER narrowest-first and take the first rung that
    holds `min_commits` commits or already saturates `--max-commits` (widening
    past the cap buys nothing -- the log pass would truncate to the same
    commits, just an older slice of them).  Falling off the end of the ladder
    means all history, with the counts recorded so the plan can say the
    repository simply does not have enough history to be sure.
    """
    if explicit_days is not None:
        window = empty_window(explicit_days, mode="explicit")
        window["reason"] = "--days %d given explicitly (%s); adaptive widening off" % (
            explicit_days,
            _describe_days(explicit_days),
        )
        return window

    window = empty_window(ADAPTIVE_LADDER[0], mode="adaptive", min_commits=min_commits)
    counts = []  # type: List[Tuple[int, Optional[int]]]
    for rung in ADAPTIVE_LADDER:
        found = _count_commits(root, rung, debug=debug)
        if found is None:
            if not counts:
                # No count at all -- an empty repo, or rev-list is unhappy.
                # Use the default window; the log pass below reports the real
                # failure, and its own "quiet window" retry still applies.
                window["reason"] = (
                    "could not count commits (rev-list gave no answer); "
                    "fell back to the default %d-day window" % DEFAULT_DAYS
                )
                emit_lib.warn(
                    warnings,
                    "window: could not probe commit counts; using the default %d-day window"
                    % DEFAULT_DAYS,
                )
                return window
            break
        counts.append((rung, found))
        window["steps"].append({"days": rung, "commits": found})
        if found >= min_commits:
            window["days"] = rung
            if rung == ADAPTIVE_LADDER[0]:
                window["reason"] = (
                    "%s holds %d commits, at or above the %d-commit floor; not widened"
                    % (_describe_days(rung), found, min_commits)
                )
            else:
                window["reason"] = (
                    "widened %s -> %s: %s held %d commits, below the %d-commit floor; "
                    "%s holds %d"
                    % (
                        _describe_days(counts[0][0]),
                        _describe_days(rung),
                        _describe_days(counts[0][0]),
                        counts[0][1],
                        min_commits,
                        _describe_days(rung),
                        found,
                    )
                )
                emit_lib.warn(
                    warnings,
                    "window: widened from %s to %s -- %s held only %d commit(s), "
                    "too few for co-change or a convention percentage"
                    % (
                        _describe_days(counts[0][0]),
                        _describe_days(rung),
                        _describe_days(counts[0][0]),
                        counts[0][1],
                    ),
                )
            return window
        if max_commits and found >= max_commits:
            window["days"] = rung
            window["reason"] = (
                "%s holds %d commits, at or above the --max-commits cap of %d; "
                "not widened further" % (_describe_days(rung), found, max_commits)
            )
            return window

    # Ladder exhausted (or a probe failed part-way): take the widest rung tried.
    widest = counts[-1] if counts else (ADAPTIVE_LADDER[-1], 0)
    window["days"] = widest[0]
    window["reason"] = "no window reached the %d-commit floor (%s); using %s" % (
        min_commits,
        ", ".join("%s:%s" % (_describe_days(d), c) for d, c in counts) or "no counts",
        _describe_days(widest[0]),
    )
    emit_lib.warn(
        warnings,
        "window: widened all the way to %s and still found only %s commit(s), under the "
        "%d-commit floor; git evidence is thin and every percentage in it is computed over "
        "that sample" % (_describe_days(widest[0]), widest[1], min_commits),
    )
    return window


def empty_payload(days: int, warnings: Optional[List[str]] = None) -> Dict[str, Any]:
    """The full schema, all fields present, nothing measured."""
    return {
        "schema_version": SCHEMA_VERSION,
        "tool": TOOL,
        "available": False,
        "window": empty_window(days),
        "commit_conventions": {
            "conventional_pct": 0.0,
            "types": [],
            "scopes": [],
            "ticket_prefix_pct": 0.0,
            "ticket_pattern": "",
            "subject_median_len": 0,
            "imperative_pct": 0.0,
        },
        "branch_naming": [],
        "cochange_clusters": [],
        "hotspots": [],
        "directory_hotspots": [],
        "test_discipline": {"commits_touching_tests_pct": 0.0, "test_paths": []},
        "revert_rate": 0.0,
        "contributors": [],
        "authorship": empty_authorship(),
        "pr_patterns": _empty_pr_patterns(),
        "warnings": list(warnings or []),
        "timing_ms": 0,
    }


def _find_git_root(start: str) -> str:
    """
    Walk up looking for `.git` (a directory in a normal clone, a file in a
    worktree or submodule).  Filesystem-only, so "not a repo" is answered
    without running git at all.
    """
    current = os.path.abspath(start)
    while True:
        if os.path.exists(os.path.join(current, ".git")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return ""
        current = parent


def collect(
    repo: str,
    days: Optional[int],
    max_commits: int,
    no_gh: bool,
    debug: bool = False,
    min_commits: int = DEFAULT_MIN_COMMITS,
    include_bots: bool = False,
) -> Dict[str, Any]:
    """
    Run the miner.  Always returns a complete payload; never raises.

    `days=None` means "choose the window" (see ADAPTIVE WINDOW); an int is an
    explicit override, 0 meaning all history.
    """
    warnings = []  # type: List[str]
    hits = []  # type: List[str]
    payload = empty_payload(DEFAULT_DAYS if days is None else days, warnings)
    payload["warnings"] = warnings

    if not os.path.isdir(repo):
        emit_lib.warn(warnings, "not a directory: %s" % repo)
        return payload

    if shutil.which("git") is None:
        emit_lib.warn(warnings, "git is not installed or not on PATH; git evidence unavailable")
        return payload

    root = _find_git_root(repo)
    if not root:
        emit_lib.warn(warnings, "not a git repository (no .git found at or above %s)" % repo)
        return payload

    top = _git(root, "rev-parse", ["--show-toplevel"], timeout=GIT_QUICK_TIMEOUT_S, debug=debug)
    if top["ok"] and top["out"].strip():
        root = top["out"].strip().splitlines()[0]
    else:
        emit_lib.warn(warnings, "git rev-parse failed (%s); using %s" % (top["reason"], root))

    # --- does this clone hold every blob? ------------------------------------
    # Asked BEFORE the log pass, and cheap: three `config --get` reads and a
    # `rev-parse`.  A blobless clone that reaches `--numstat` spends a minute
    # dialling the promisor remote and then returns nothing (see
    # `_warn_path_only`), which is the worst of the available behaviours.
    clone = detect_partial_clone(root, debug=debug)
    path_only = plan_log_pass(clone)
    if path_only:
        _warn_path_only(warnings, clone, "partial clone detected")
    elif clone.get("shallow"):
        emit_lib.warn(
            warnings,
            "shallow clone (%s): every blob for the commits it holds is present, so churn and "
            "co-change are honest -- but the history is truncated, so read window.reason before "
            "quoting a count. A `--depth 1` clone measures a repo that does not exist."
            % (clone.get("marker") or "no marker recorded"),
        )

    # --- choose the window before reading anything ---------------------------
    payload["window"] = choose_window(
        root, days, min_commits, max_commits, warnings, debug=debug
    )
    window_days = payload["window"]["days"]

    # --- the single log pass -------------------------------------------------
    log_args = _log_args(path_only, max_commits, window_days)

    log = _git(root, "log", log_args, timeout=GIT_TIMEOUT_S, debug=debug)
    if not log["ok"] and not path_only and _looks_like_missing_object(log["err"] or log["reason"]):
        # The safety net for the shapes detection missed: a promisor remote
        # under another name, a repo whose objects were pruned, an old git
        # that ignores GIT_NO_LAZY_FETCH.  Retry once in the form that needs
        # no blob contents rather than returning an empty payload.
        path_only = True
        _warn_path_only(
            warnings,
            clone,
            "git log --numstat could not read an object (%s)" % _clean(_first_line(log["err"] or log["reason"], 120), hits),
        )
        log_args = _log_args(path_only, max_commits, window_days)
        log = _git(root, "log", log_args, timeout=GIT_TIMEOUT_S, debug=debug)
    if not log["ok"]:
        reason = log["reason"]
        lowered = (log["err"] or "").lower()
        if "does not have any commits" in lowered or "bad default revision" in lowered:
            emit_lib.warn(warnings, "repository has no commits yet; git evidence unavailable")
        else:
            emit_lib.warn(warnings, "git log failed: %s" % _clean(reason, hits))
        return payload

    commits = _parse_log(log["out"], path_only=path_only)
    if not commits and window_days and window_days > 0:
        # A quiet window is not an empty repo.  Retry over all history once.
        # Under the adaptive ladder this is nearly unreachable -- the probe
        # would have widened already -- but it still catches an explicit
        # `--days N` over a dormant repo, and a probe that failed.
        emit_lib.warn(
            warnings,
            "no commits in the last %d days; widened the window to full history"
            % window_days,
        )
        retry_args = [a for a in log_args if not a.startswith("--since=")]
        log = _git(root, "log", retry_args, timeout=GIT_TIMEOUT_S, debug=debug)
        if log["ok"]:
            commits = _parse_log(log["out"], path_only=path_only)
            payload["window"]["days"] = 0
            payload["window"]["reason"] = (
                "%s held no commits at all; fell back to all history"
                % _describe_days(window_days)
            )

    if not commits:
        emit_lib.warn(warnings, "repository has no commits yet; git evidence unavailable")
        return payload

    payload["available"] = True
    payload["window"]["commits_analyzed"] = len(commits)
    payload["window"]["last"] = commits[0]["date"]
    payload["window"]["first"] = commits[-1]["date"]
    if max_commits and len(commits) >= max_commits:
        emit_lib.warn(
            warnings,
            "analysis capped at --max-commits %d; older history not read" % max_commits,
        )

    # --- branch refs + the local identity used to spot `user/` prefixes ------
    branch_names = []  # type: List[str]
    refs = _git(
        root,
        "for-each-ref",
        ["--format=%(refname:short)", "--count=500", "refs/heads"],
        timeout=GIT_QUICK_TIMEOUT_S,
        debug=debug,
    )
    if refs["ok"]:
        branch_names = [line.strip() for line in refs["out"].splitlines() if line.strip()]
    else:
        emit_lib.warn(warnings, "git for-each-ref failed (%s); branch naming from merge subjects only" % refs["reason"])

    config_name = ""
    cfg = _git(root, "config", ["--get", "user.name"], timeout=GIT_QUICK_TIMEOUT_S, debug=debug)
    if cfg["ok"]:
        config_name = cfg["out"].strip()

    # --- authorship: machines are counted here, then set aside ---------------
    # Everything below this line is measured over `analysed`, never `commits`.
    # `window.commits_analyzed` stays the number READ, so the window keeps
    # describing itself honestly; `authorship.commits_human` is the
    # denominator of every percentage.
    split = partition_commits(commits)
    payload["authorship"] = analyze_authorship(split, not include_bots, hits)
    _warn_authorship(payload["authorship"], include_bots, warnings)
    analysed = commits if include_bots else split["human"]

    # --- analyses ------------------------------------------------------------
    payload["commit_conventions"] = analyze_conventions(analysed, hits)
    payload["branch_naming"] = analyze_branch_naming(branch_names, analysed, config_name)
    payload["cochange_clusters"] = analyze_cochange(analysed, warnings, repo_root=root)
    hotspots, dir_hotspots = analyze_hotspots(analysed, repo_root=root)
    payload["hotspots"] = hotspots
    payload["directory_hotspots"] = dir_hotspots
    payload["test_discipline"] = analyze_test_discipline(analysed)
    payload["revert_rate"] = analyze_reverts(analysed)
    payload["contributors"] = analyze_contributors(split["authors"], hits)
    payload["pr_patterns"] = analyze_pr_patterns(root, no_gh, warnings, hits, debug=debug)

    dead = sum(
        1
        for row in (
            payload["cochange_clusters"] + payload["hotspots"] + payload["directory_hotspots"]
        )
        if row.get("still_exists") is False
    )
    if dead:
        emit_lib.warn(
            warnings,
            "%d path-evidence row(s) name files that are no longer in the working tree "
            "(still_exists: false); they are history, not a target -- do not build on them"
            % dead,
        )

    if hits:
        emit_lib.warn(
            warnings,
            "scrubbed %d secret-shaped value(s) from git text (%s)"
            % (len(hits), ", ".join(sorted(set(hits))[:6])),
        )
    return payload


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

TRIM_KEYS = (
    "cochange_clusters",
    "hotspots",
    "directory_hotspots",
    "contributors",
    "authorship.bot_authors",
    "commit_conventions.scopes",
    "commit_conventions.types",
    "branch_naming",
    "test_discipline.test_paths",
    "pr_patterns.body_sections",
)


def build_parser():
    parser = emit_lib.base_parser(
        TOOL,
        "Mine local git history for conventions, co-change clusters and hotspots.",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        metavar="N",
        help=(
            "pin the window to the last N days (0 = all history).  OMIT IT for the "
            "adaptive default: the window widens %s until it holds --min-commits "
            "commits.  Passing --days turns the widening off."
            % " -> ".join(_describe_days(d) for d in ADAPTIVE_LADDER)
        ),
    )
    parser.add_argument(
        "--min-commits",
        type=int,
        default=DEFAULT_MIN_COMMITS,
        metavar="N",
        dest="min_commits",
        help="commits an adaptive window must hold before it stops widening "
        "(default: %d); ignored when --days is given" % DEFAULT_MIN_COMMITS,
    )
    parser.add_argument(
        "--max-commits",
        type=int,
        default=DEFAULT_MAX_COMMITS,
        metavar="N",
        dest="max_commits",
        help="hard cap on commits read (0 = no cap; default: %d)" % DEFAULT_MAX_COMMITS,
    )
    parser.add_argument(
        "--no-gh",
        action="store_true",
        default=False,
        dest="no_gh",
        help="never invoke the GitHub CLI; disables the only network-capable path",
    )
    parser.add_argument(
        "--include-bots",
        action="store_true",
        default=False,
        dest="include_bots",
        help=(
            "count bot-authored commits in every statistic (raw view).  By DEFAULT "
            "commits by machines -- github-actions, dependabot, renovate, "
            "checkpointer, any [bot] name or no-reply sender -- are excluded from "
            "conventions, branch naming, co-change, hotspots, test discipline and "
            "the revert rate, because release automation produces the highest-support "
            "co-change clusters in a monorepo and they describe nothing a human does. "
            "They are always counted in `authorship` and listed in `contributors[]` "
            "either way"
        ),
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    if getattr(args, "selftest", False):
        return selftest()

    repo = emit_lib.resolve_repo(args.repo)
    cap = args.cap_chars if args.cap_chars is not None else DEFAULT_CAP_CHARS

    # `None` is the adaptive default and is NOT the same as `--days 0`, which
    # explicitly asks for all history.
    days = None if args.days is None else max(0, int(args.days))
    fallback_days = DEFAULT_DAYS if days is None else days

    timer = emit_lib.Timer()
    with timer:
        try:
            payload = collect(
                repo,
                days=days,
                max_commits=max(0, int(args.max_commits or 0)),
                no_gh=bool(args.no_gh),
                debug=bool(args.debug),
                min_commits=max(1, int(args.min_commits or DEFAULT_MIN_COMMITS)),
                include_bots=bool(args.include_bots),
            )
        except GitSafetyError as exc:
            payload = empty_payload(fallback_days)
            emit_lib.warn(payload["warnings"], "internal safety check tripped: %s" % exc)
            emit_lib.eprint("[mine_git] SAFETY: %s" % exc)
        except Exception as exc:  # never raise out of main
            payload = empty_payload(fallback_days)
            emit_lib.warn(payload["warnings"], "git mining failed: %s" % exc)
            if args.debug:
                import traceback

                traceback.print_exc(file=sys.stderr)

    payload["timing_ms"] = timer.ms
    emit_lib.emit(payload, cap_chars=cap, trim_keys=TRIM_KEYS)
    return 0


# ---------------------------------------------------------------------------
# --selftest
# ---------------------------------------------------------------------------

def selftest() -> int:
    """
    Fast internal sanity check: imports resolve, emit round-trips, the module's
    regexes compile, the read-only git guard still refuses a mutating command,
    and a synthetic three-commit repository is mined end to end.

    The fixture lives in a temp directory and is created with `git init`, so it
    never touches the user's repo.  When git is not installed the end-to-end
    check reports what it skipped rather than failing -- a missing git is the
    machine's state, not a defect in this script, and the degraded path below
    is what actually has to hold in that case.  Sub-second.
    """
    import io
    import tempfile
    import time as _time
    import unicodedata

    started = int(_time.time() * 1000)
    checks = []  # type: List[Tuple[str, bool, str]]

    def add(name, ok, detail=""):
        checks.append((name, bool(ok), str(detail)))

    def _nfc(text):
        """A normalizing filesystem stores NFD; git reports NFC.  Compare one."""
        return unicodedata.normalize("NFC", text)

    add("imports resolve", hasattr(emit_lib, "emit") and hasattr(emit_lib, "selftest_report"), "lib.emit")

    ok, detail = emit_lib.check_regexes(sys.modules[__name__])
    add("regexes compile and match", ok, detail)

    # Path decoding.  git quotes any path carrying an unusual byte, and quotes
    # it as OCTAL BYTES: `src/café.py` leaves git as `"src/caf\303\251.py"` --
    # two escapes that are ONE UTF-8 code point, not two characters.  Decoding
    # them one chr() at a time yields `src/cafÃ©.py`, a path that is not on
    # disk, which then reports `still_exists: false` for a live file.
    #
    # A rename is the second shape, and it is not the brace form: with quoting
    # on, git emits `"old" => "new"` with each SIDE quoted independently (the
    # `src/{a => b}` form appears only when NEITHER side needs quoting).  The
    # last row is the `core.quotepath=false` case -- an already-plain path must
    # come through untouched.
    numstat_path_cases = [
        (r'"src/caf\303\251.py"', "src/café.py"),
        (r'"src/\346\227\245\346\234\254\350\252\236.py"', "src/日本語.py"),
        (r'"src/emoji\360\237\230\200.py"', "src/emoji😀.py"),
        (r'"src/we\"ird.py"', 'src/we"ird.py'),
        (r'"src/back\\slash.py"', "src/back\\slash.py"),
        (r'"src/tab\there.py"', "src/tab\there.py"),
        (r'"src/new\nline.py"', "src/new\nline.py"),
        (r'"src/bell\a\b\f\v\r.py"', "src/bell\a\b\f\v\r.py"),
        (r'"src/caf\303\251.py" => "src/na\303\257ve.py"', "src/naïve.py"),
        (r'src/plain.py => "src/caf\303\251-new.py"', "src/café-new.py"),
        (r'"src/caf\303\251.py" => src/one-plain.py', "src/one-plain.py"),
        ("src/{a.py => b.py}", "src/b.py"),
        ("{src => lib}/日本語.py", "lib/日本語.py"),
        ("old.ts => new.ts", "new.ts"),
        ("src/plain.py", "src/plain.py"),
    ]
    wrong_paths = []
    for field, expected in numstat_path_cases:
        row = _parse_numstat_line("1\t0\t" + field)
        got = row[2] if row else None
        if got != expected:
            wrong_paths.append("%r -> %r (want %r)" % (field, got, expected))
    add(
        "quoted paths decode from git's octal BYTES, not one chr() per escape",
        not wrong_paths,
        "; ".join(wrong_paths) or "%d cases" % len(numstat_path_cases),
    )

    # The same decoder, on the `--name-only --no-renames` line shape used for
    # partial clones.  A path holding a tab or a newline is excluded here on
    # purpose: that line shape cannot carry one unambiguously.
    wrong_name_only = []
    for field, expected in numstat_path_cases:
        if "\t" in expected or "\n" in expected:
            continue
        got = _parse_path_only_line(field)
        got_path = got[2] if got else None
        if got_path != expected:
            wrong_name_only.append("%r -> %r (want %r)" % (field, got_path, expected))
    add(
        "the path-only line shape decodes the same way",
        not wrong_name_only,
        "; ".join(wrong_name_only) or "%d cases" % (len(numstat_path_cases) - 2),
    )

    # Bot classification, decided without touching git.  The two rows that
    # matter most are the last two: a human on a `users.noreply.github.com`
    # privacy address must stay a human, and a person whose given name is on
    # the identity list must stay a person (exact match, never substring).
    author_cases = [
        ("github-actions[bot]", "41898282+github-actions[bot]@users.noreply.github.com", True),
        ("dependabot[bot]", "support@dependabot.com", True),
        ("renovate[bot]", "29139614+renovate[bot]@users.noreply.github.com", True),
        ("Checkpointer", "checkpointer@noreply", True),
        ("Renovate Bot", "bot@renovateapp.com", True),
        ("GitHub", "noreply@github.com", True),
        ("Ravi Sojitra", "12345+ravisojitra@users.noreply.github.com", False),
        ("Claude Dupont", "claude.dupont@example.com", False),
        ("Jenkins Okafor", "jenkins.okafor@example.com", False),
    ]
    wrong = [
        "%s -> %s" % (name, classify_author(name, mail)[0])
        for name, mail, expected in author_cases
        if classify_author(name, mail)[0] is not expected
    ]
    add(
        "bot classification: machines caught, people left alone",
        not wrong,
        ", ".join(wrong) or "%d cases" % len(author_cases),
    )
    twin = partition_commits(
        [
            {"author": "cyrusagent[bot]", "email": "agent@example.com", "subject": "a", "date": "", "is_merge": False, "files": []},
            {"author": "cyrusagent", "email": "agent@example.com", "subject": "b", "date": "", "is_merge": False, "files": []},
            {"author": "Real Person", "email": "person@example.com", "subject": "c", "date": "", "is_merge": False, "files": []},
        ]
    )
    add(
        "one machine under two display names is counted once, as a machine",
        len(twin["bot"]) == 2 and len(twin["human"]) == 1,
        "bot=%d human=%d" % (len(twin["bot"]), len(twin["human"])),
    )

    buffer = io.StringIO()
    text = emit_lib.emit(empty_payload(DEFAULT_DAYS), cap_chars=DEFAULT_CAP_CHARS, trim_keys=TRIM_KEYS, stream=buffer)
    try:
        parsed = json.loads(text)
    except ValueError as exc:
        parsed = {}
        add("emit round-trips", False, str(exc))
    else:
        add("emit round-trips", parsed.get("tool") == TOOL, "%d keys" % len(parsed))
    add(
        "empty_payload carries every contract key",
        all(
            k in parsed
            for k in (
                "available", "window", "commit_conventions", "branch_naming",
                "cochange_clusters", "hotspots", "directory_hotspots",
                "test_discipline", "revert_rate", "contributors", "authorship",
                "pr_patterns", "warnings", "timing_ms",
            )
        ),
        str(sorted(parsed.keys())),
    )
    add(
        "window carries the choice it made, not just the number",
        set(parsed.get("window", {}).keys())
        == set(["days", "commits_analyzed", "first", "last", "mode", "min_commits", "steps", "reason"]),
        str(sorted(parsed.get("window", {}).keys())),
    )

    # The read-only guard is the safety property this script exists to keep.
    blocked = False
    try:
        _git(os.getcwd(), "push", ["--force"], timeout=1.0)
    except GitSafetyError:
        blocked = True
    except Exception as exc:  # pragma: no cover - any other error is a defect
        add("read-only git guard blocks a mutating command", False, "%r" % (exc,))
    add("read-only git guard blocks a mutating command", blocked, "push --force refused")

    # -- synthetic repository, mined end to end ------------------------------
    if shutil.which("git") is None:
        add("synthetic repo mined end to end", True, "git not on PATH; fixture skipped")
    else:
        fixture = tempfile.mkdtemp(prefix="agentic-codebase-minegit-selftest-")
        unicode_fixture = tempfile.mkdtemp(prefix="agentic-codebase-minegit-unicode-")
        try:
            env = dict(os.environ)
            env.update(
                {
                    "GIT_AUTHOR_NAME": "Selftest",
                    "GIT_AUTHOR_EMAIL": "selftest@example.invalid",
                    "GIT_COMMITTER_NAME": "Selftest",
                    "GIT_COMMITTER_EMAIL": "selftest@example.invalid",
                    "GIT_CONFIG_GLOBAL": os.path.join(fixture, "gitconfig"),
                    "GIT_CONFIG_SYSTEM": os.path.join(fixture, "gitconfig"),
                }
            )

            def run(*argv_, **kw):
                subprocess.run(
                    ["git"] + list(argv_),
                    cwd=kw.get("cwd", fixture),
                    env=kw.get("env", env),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=15,
                )

            run("init", "-q", "-b", "main")
            legacy = os.path.join(fixture, "legacy.py")
            for index, subject in enumerate(
                ["feat(api): add users endpoint", "fix(api): handle empty body", "test(api): cover users endpoint"]
            ):
                with open(os.path.join(fixture, "api.py"), "a") as handle:
                    handle.write("# change %d\n" % index)
                os.makedirs(os.path.join(fixture, "tests"), exist_ok=True)
                with open(os.path.join(fixture, "tests", "test_api.py"), "a") as handle:
                    handle.write("# test %d\n" % index)
                # `legacy.py` is born in the first commit and deleted in the
                # last, so the fixture carries one piece of DEAD evidence: a
                # real hotspot whose file is gone from the working tree.
                if index == 0:
                    with open(legacy, "w") as handle:
                        handle.write("# legacy shim\n")
                elif index == 2 and os.path.exists(legacy):
                    os.remove(legacy)
                run("add", "-A")
                run("commit", "-q", "-m", subject)

            # One machine commit, so the exclusion is measurable rather than
            # asserted: release automation touching a file no human edits,
            # with a subject that is deliberately NOT conventional.  With bots
            # excluded the convention share stays 1.00 over three human
            # commits; with --include-bots it falls to 0.75 and RELEASE_VERSION
            # appears as a hotspot.  That difference IS the test.
            bot_env = dict(env)
            bot_env.update(
                {
                    "GIT_AUTHOR_NAME": "github-actions[bot]",
                    "GIT_AUTHOR_EMAIL": "41898282+github-actions[bot]@users.noreply.github.com",
                    "GIT_COMMITTER_NAME": "github-actions[bot]",
                    "GIT_COMMITTER_EMAIL": "41898282+github-actions[bot]@users.noreply.github.com",
                }
            )
            with open(os.path.join(fixture, "RELEASE_VERSION"), "w") as handle:
                handle.write("1.2.3\n")
            run("add", "-A", env=bot_env)
            run("commit", "-q", "-m", "Version Packages", env=bot_env)

            def run_main(argv):
                buf = io.StringIO()
                saved = sys.stdout
                try:
                    sys.stdout = buf
                    exit_code = main(argv)
                finally:
                    sys.stdout = saved
                text_out = buf.getvalue()
                try:
                    return exit_code, json.loads(text_out), text_out
                except ValueError:
                    return exit_code, {}, text_out

            code, result, raw = run_main(["--repo", fixture, "--no-gh", "--days", "3650"])
            add("synthetic repo run exits 0", code == 0, str(code))
            add(
                "synthetic repo emits one JSON object",
                bool(result) and raw.count("\n") == 1,
                "%d newline(s)" % raw.count("\n"),
            )
            add(
                "history is read (available, commits counted)",
                result.get("available") is True and result.get("window", {}).get("commits_analyzed", 0) == 4,
                "available=%s commits=%s"
                % (result.get("available"), result.get("window", {}).get("commits_analyzed")),
            )
            explicit_window = result.get("window", {})
            add(
                "--days is an explicit override (ladder off)",
                explicit_window.get("mode") == "explicit"
                and explicit_window.get("days") == 3650
                and explicit_window.get("steps") == []
                and bool(explicit_window.get("reason")),
                "mode=%s days=%s steps=%s"
                % (
                    explicit_window.get("mode"),
                    explicit_window.get("days"),
                    explicit_window.get("steps"),
                ),
            )

            # -- adaptive: 3 commits is under the floor at every rung, so the
            #    ladder must run to the end and land on all history, saying so.
            code, adaptive, _raw = run_main(["--repo", fixture, "--no-gh"])
            window = adaptive.get("window", {})
            add(
                "no --days widens through the ladder and reports why",
                code == 0
                and window.get("mode") == "adaptive"
                and window.get("days") == 0
                and len(window.get("steps") or []) == len(ADAPTIVE_LADDER)
                and window.get("min_commits") == DEFAULT_MIN_COMMITS
                and "floor" in (window.get("reason") or "")
                and adaptive.get("window", {}).get("commits_analyzed") == 4,
                "days=%s steps=%s reason=%r"
                % (window.get("days"), window.get("steps"), (window.get("reason") or "")[:80]),
            )
            add(
                "--min-commits stops the ladder at the first rung when met",
                (
                    run_main(["--repo", fixture, "--no-gh", "--min-commits", "2"])[1]
                    .get("window", {})
                    .get("days")
                    == ADAPTIVE_LADDER[0]
                ),
                "floor 2 over 4 commits",
            )

            spots = {row["path"]: row for row in adaptive.get("hotspots", [])}
            today = _day(adaptive.get("window", {}).get("last", ""))
            add(
                "hotspots carry first_seen / last_seen / still_exists",
                bool(spots)
                and all(
                    DAY_RE.match(row.get("last_seen") or "")
                    and DAY_RE.match(row.get("first_seen") or "")
                    and isinstance(row.get("still_exists"), bool)
                    for row in spots.values()
                )
                and spots.get("api.py", {}).get("last_seen") == today,
                str(spots.get("api.py")),
            )
            add(
                "a deleted path is marked still_exists: false",
                spots.get("legacy.py", {}).get("still_exists") is False
                and spots.get("api.py", {}).get("still_exists") is True,
                "legacy=%s api=%s"
                % (
                    spots.get("legacy.py", {}).get("still_exists"),
                    spots.get("api.py", {}).get("still_exists"),
                ),
            )
            add(
                "co-change clusters are dated and liveness-marked",
                all(
                    DAY_RE.match(c.get("last_seen") or "")
                    and DAY_RE.match(c.get("first_seen") or "")
                    and isinstance(c.get("still_exists"), bool)
                    for c in adaptive.get("cochange_clusters", [])
                )
                and bool(adaptive.get("cochange_clusters")),
                str(adaptive.get("cochange_clusters")),
            )
            add(
                "directory hotspots are dated and liveness-marked",
                all(
                    DAY_RE.match(d.get("last_seen") or "")
                    and isinstance(d.get("still_exists"), bool)
                    for d in adaptive.get("directory_hotspots", [])
                )
                and bool(adaptive.get("directory_hotspots")),
                str(adaptive.get("directory_hotspots")),
            )
            add(
                "conventional commits and their types are detected",
                result.get("commit_conventions", {}).get("conventional_pct", 0) > 0.9
                and {t.get("type") for t in result.get("commit_conventions", {}).get("types", [])}
                == set(["feat", "fix", "test"]),
                str(result.get("commit_conventions", {}).get("types")),
            )
            add(
                "test discipline is measured",
                result.get("test_discipline", {}).get("commits_touching_tests_pct", 0) > 0.9,
                str(result.get("test_discipline")),
            )

            # -- bots: counted, excluded, and restorable -----------------------
            authorship = adaptive.get("authorship", {})
            add(
                "authorship counts the machines it set aside",
                authorship.get("commits_total") == 4
                and authorship.get("commits_human") == 3
                and authorship.get("commits_bot") == 1
                and authorship.get("bots_excluded") is True
                and [row.get("name") for row in authorship.get("bot_authors", [])]
                == ["github-actions[bot]"],
                str(authorship),
            )
            add(
                "bot commits do not reach hotspots or the convention share",
                "RELEASE_VERSION" not in [row.get("path") for row in adaptive.get("hotspots", [])]
                and adaptive.get("commit_conventions", {}).get("conventional_pct") == 1.0,
                "hotspots=%s conventional_pct=%s"
                % (
                    [row.get("path") for row in adaptive.get("hotspots", [])],
                    adaptive.get("commit_conventions", {}).get("conventional_pct"),
                ),
            )
            _code, raw_view, _raw = run_main(["--repo", fixture, "--no-gh", "--include-bots"])
            add(
                "--include-bots restores the raw view",
                raw_view.get("authorship", {}).get("bots_excluded") is False
                and "RELEASE_VERSION"
                in [row.get("path") for row in raw_view.get("hotspots", [])]
                and raw_view.get("commit_conventions", {}).get("conventional_pct") == 0.75,
                "conventional_pct=%s hotspots=%s"
                % (
                    raw_view.get("commit_conventions", {}).get("conventional_pct"),
                    [row.get("path") for row in raw_view.get("hotspots", [])],
                ),
            )
            people = adaptive.get("contributors", [])
            add(
                "contributors mark machines and rank people first",
                len(people) == 2
                and people[0].get("name") == "Selftest"
                and people[0].get("is_bot") is False
                and people[1].get("is_bot") is True
                and bool(people[1].get("bot_reason"))
                and people[1].get("email_domain") == "users.noreply.github.com",
                str(people),
            )
            _c2, _r2, adaptive_raw = run_main(["--repo", fixture, "--no-gh"])
            add(
                "the address local part is never emitted",
                "41898282" not in adaptive_raw and "@" not in adaptive_raw,
                "domain only",
            )

            # -- unicode paths, mined end to end ------------------------------
            # Its own repository, so every count asserted above stays what it
            # is.  Three names git has to quote, one ASCII control, and a
            # rename of a quoted path -- the shape that arrives as
            # `"old" => "new"`, each side quoted on its own, never the brace
            # form.  Nothing here is ever deleted, so EVERY row must come back
            # `still_exists: true`; a row that decoded to mojibake cannot,
            # which is what makes this a test and not a restatement.  Compared
            # NFC-normalized because a normalizing filesystem (HFS+) stores
            # the name decomposed while git reports it precomposed.
            uni_src = os.path.join(unicode_fixture, "src")
            os.makedirs(uni_src)
            created = []
            for name in ("café.py", "日本語.py", "emoji😀.py", "plain.py"):
                try:
                    with open(os.path.join(uni_src, name), "w") as handle:
                        handle.write("# %s\n" % name)
                except (OSError, UnicodeError):  # a filesystem that refuses it
                    continue
                created.append(name)
            run("init", "-q", "-b", "main", cwd=unicode_fixture)
            run("add", "-A", cwd=unicode_fixture)
            run("commit", "-q", "-m", "feat(i18n): add unicode modules", cwd=unicode_fixture)
            renamed = ""
            if "日本語.py" in created:
                renamed = "src/漢字.py"
                run("mv", "src/日本語.py", renamed, cwd=unicode_fixture)
            with open(os.path.join(uni_src, "plain.py"), "a") as handle:
                handle.write("# touched\n")
            run("add", "-A", cwd=unicode_fixture)
            run("commit", "-q", "-m", "refactor(i18n): rename the module", cwd=unicode_fixture)

            _uni_code, uni, uni_raw = run_main(
                ["--repo", unicode_fixture, "--no-gh", "--days", "3650"]
            )
            uni_rows = dict((_nfc(row["path"]), row) for row in uni.get("hotspots", []))
            on_disk = set(_nfc("src/" + n) for n in os.listdir(uni_src))
            add(
                "a unicode filename is mined under the name it has on disk",
                bool(uni_rows) and on_disk <= set(uni_rows),
                "mined=%s on_disk=%s" % (sorted(uni_rows), sorted(on_disk)),
            )
            add(
                "still_exists tracks the working tree for a unicode name too",
                bool(uni_rows)
                and on_disk <= set(uni_rows)
                and all(
                    row.get("still_exists") is (path in on_disk)
                    for path, row in uni_rows.items()
                ),
                str(sorted((p, r.get("still_exists"), p in on_disk) for p, r in uni_rows.items())),
            )
            # The old name keeps the one commit it was born in -- that is real
            # history, and it is correctly marked dead above.  What must NOT
            # happen is the rename commit landing on it (2 commits) or on a
            # mangled third path: `"old" => "new"` resolves to the destination.
            source = _nfc("src/日本語.py")
            destination = _nfc(renamed)
            add(
                "a renamed unicode path folds onto its destination",
                not renamed
                or (
                    destination in uni_rows
                    and uni_rows[destination].get("still_exists") is True
                    and uni_rows.get(source, {}).get("commits") == 1
                ),
                "destination=%s source=%s" % (uni_rows.get(destination), uni_rows.get(source)),
            )
            add(
                "no mojibake and no escape survives into the output",
                "Ã" not in uni_raw
                and "æ" not in uni_raw
                and "\\3" not in uni_raw,
                "%d chars scanned" % len(uni_raw),
            )
        finally:
            shutil.rmtree(fixture, ignore_errors=True)
            shutil.rmtree(unicode_fixture, ignore_errors=True)

    # -- degraded paths ------------------------------------------------------
    degraded_ok = True
    degraded_detail = []
    for label, path in (("missing", os.path.join(tempfile.gettempdir(), "agentic-codebase-no-such-repo")),
                        ("file", os.path.abspath(__file__)),
                        ("devnull", os.devnull)):
        buffer = io.StringIO()
        saved_stdout = sys.stdout
        try:
            sys.stdout = buffer
            code = main(["--repo", path, "--no-gh"])
        except SystemExit as exit_error:  # pragma: no cover - must not happen
            code = exit_error.code
        finally:
            sys.stdout = saved_stdout
        try:
            parsed = json.loads(buffer.getvalue())
        except ValueError:
            parsed = {}
        if code != 0 or parsed.get("available") is not False or not parsed.get("warnings"):
            degraded_ok = False
        degraded_detail.append("%s=%s" % (label, code))
    add("non-repo paths exit 0 with available=false", degraded_ok, " ".join(degraded_detail))

    return emit_lib.selftest_report(TOOL, checks, started_ms=started)


if __name__ == "__main__":
    sys.exit(emit_lib.main_guard(main, TOOL))
