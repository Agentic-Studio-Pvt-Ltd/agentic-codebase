#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agentic-codebase :: scripts/mine_transcripts.py -- the transcript miner.

Reads the developer's LOCAL agent session files for one repository and boils
them down to a compact, counted evidence report:  which requests they type
over and over, which corrections they keep having to repeat, where the pain
is, which commands and services show up, which files they keep pointing at.

Phase 3 of the skill reasons over this JSON.  Nothing else in the pipeline
ever touches a raw transcript, and that is deliberate: a 400 MB history has
to arrive at the model as roughly 3k tokens or it eats the context window.

What this script will and will not do (contract "Non-negotiables"):

  * USER TURNS ONLY.  Assistant text, tool results, subagent traffic
    (Claude Code `isSidechain`, Codex `thread_source: subagent`) and injected
    system reminders are dropped before analysis.
  * SCRUBBED FIRST.  Every string passes through `lib.scrub.scrub()` BEFORE
    it enters any accumulator.  There is no code path on which an unscrubbed
    example can reach stdout.
  * THE CONSENT WINDOW IS THE TURN'S.  Under `--days N` a record is analyzed
    only when ITS OWN timestamp is inside the window, and an undated record is
    not analyzed at all.  A directory name or a file mtime is a pre-filter that
    saves I/O and decides nothing.  Stated in full above `_iso_cutoff()`, and
    it is one rule because the two halves have been broken in opposite
    directions -- 80-day-old text admitted by a fresh file, a thread resumed an
    hour ago dropped by an old directory.
  * LOCAL ONLY.  No network, no telemetry, no writes, no subprocess.  Read-only
    on `~/.claude/projects`, `${CODEX_HOME:-~/.codex}/sessions` and
    `${CODEX_HOME:-~/.codex}/archived_sessions`.
  * STREAMING.  Session files are read line by line, in binary, with cheap
    substring rejects before any `json.loads`.  A single 8 MB session file
    and a 429 MB project directory are both normal here.

TWO TARGETS, ONE REPORT.  `--target claude-code` and `--target codex` read two
formats that share nothing but the letters JSONL, and they emit the SAME object
with the same keys, the same caps and the same count>=2 rule, because phases
3-6 are target-agnostic and must not learn which agent produced the evidence.
Everything after `unwrap()` -- scrubbing, clustering, sizing, the character cap
-- is literally the same code for both.  What differs is confined to the reader
and to how a session is tied to a repository:

  claude-code  one directory per project, named by encoding the repo path.
               The directory IS the association.
  codex        one shared date tree for the whole machine.  The association is
               `session_meta.cwd` in each rollout's first record, widened by
               `session_meta.git.repository_url` so that git worktrees of the
               same repo are found (measured: 2 sessions by path, 39 by
               remote), and narrowed by dropping subagent threads, which were
               60% of one real 324-file corpus.

Output: ONE JSON object on stdout.  Top-level keys, which SKILL.md phase 3
and the build contract are both read against:

    schema_version  tool  target  transcript_root  consent_scope
    sessions{files, count, first, last, user_turns_total,
             user_turns_analyzed, social_turns, bytes_read}
    history_bucket
    request_shapes[]    id, skeleton, count, sessions, first_seen, last_seen,
                        examples   -- ACTIONABLE requests only
    meta_queries[]      skeleton, count, sessions, examples
                        -- status/progress questions ("what's remaining?",
                        "how much time?"), merged by topic, max 5 rows
    commands_requested[] command, count
    slash_commands[]    name, count
    corrections[]       text, kind, count, examples
    tool_mentions[]     name, count
    pain_signals[]      pattern, count, examples
    file_hotspots[]     path, mentions   -- CODE paths, IN THIS REPO only
    doc_hotspots[]      path, mentions   -- docs/, plans, specs, *.md
    scrub_stats  output_chars  warnings  timing_ms

Five shaping rules the consumers depend on:

  * EVERY ROW HAS A COUNT OF 2 OR MORE.  A one-off is an anecdote, and
    CLAUDE.md's evidence invariant says a finding with no evidence count maps
    to nothing; emitting singletons beside real counts invites building on
    them.  Fewer honest rows is the correct outcome, including zero.
  * REQUEST SHAPES ARE WORK.  Status questions go to `meta_queries` and
    turn-taking ("ok", "thanks", "continue") to `sessions.social_turns`, so
    the top of `request_shapes` is not half status-checking.  Separated, never
    deleted: twenty status pings ARE evidence, for a different artifact.
  * DOCS ARE NOT CODE.  `file_hotspots` was dominated by `docs/plans/*.md` on
    every large repo measured, which reads as a code hotspot and is not one.
  * HOTSPOTS ARE PATHS IN THIS REPO.  A path anchored outside the repo root
    (`~/Desktop/other/dashboard.json` turned up with 2 mentions on a run
    against an unrelated repo) is dropped, not ranked low: the field's job is
    to say which parts of THIS repo the user works in, and an outside path
    still reads as a repo path.  Repeated ones are named in a `warnings` entry
    instead, because a run whose paths are mostly external usually means the
    transcript directory was matched to the wrong checkout.
  * SWEARING IS MASKED, THE DIRECTIVE IS KEPT.  Every emitted quote passes
    through `mask_profanity()`.  "i don't want fucking trigger stack trace." is
    a real, repeated correction and stays a row; what does not stay is the
    wording, because `corrections[].text` is copied verbatim into `plan.md`,
    `report.md` and an `agentic-codebase-evidence:` frontmatter line.  Masking runs
    after counting, so no count or cluster changes.

Diagnostics on stderr.

Exit codes follow the shared contract in `lib/emit.py`'s module docstring,
which is the single normative statement -- do not restate it here and do not
invent a code.  In one line: no transcript directory, no matching project, a
consent window that excludes everything, a repo path that no longer exists,
an unparseable session file are all DEGRADED, so they print the full schema
with empty values plus a `warnings` entry and exit 0.  Exit 1 is reserved for
an unhandled exception, which `emit.main_guard()` turns into JSON on the way
out; the skill must never abort a phase.

Run `python3 scripts/mine_transcripts.py --selftest` for a sub-second sanity
check: imports resolve, emit round-trips, regexes compile, and a synthetic
two-session fixture is mined end to end -- against a temp CLAUDE_CONFIG_DIR,
so it never reads the developer's real history and never needs them to have
any.

No network. Standard library only. Python 3.9+.
"""

import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import datetime  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402

from lib import emit as emit_lib  # noqa: E402
from lib import scrub as scrub_lib  # noqa: E402
from lib import textnorm  # noqa: E402

TOOL = "mine_transcripts.py"
SCHEMA_VERSION = emit_lib.SCHEMA_VERSION

#: ~3k model tokens.  Hard.  Holds for a 1 MB history and for a 400 MB one.
CAP_CHARS = 12000

#: Total transcript bytes one run will read before it stops and says so.
#:
#: Counted on FILE size, which on Codex is a loose proxy for how much text is
#: there: measured on a real install, one 70 MB rollout held 177 records and the
#: largest single line was 25 MB of base64 image.  The budget still bounds I/O,
#: which is its job, and it is applied only to the rollouts already matched to
#: this repo -- so it drops the oldest of THIS repo's sessions, never other
#: projects' bytes.  Raise it with --max-bytes on an image-heavy history.
DEFAULT_MAX_BYTES = 400 * 1024 * 1024

#: A single JSONL line bigger than this is a pasted log or a serialized tool
#: payload, never a request worth clustering.  Measured ceiling on a real Codex
#: corpus: 25.1 MB for one line, an inlined base64 screenshot.
MAX_LINE_BYTES = 2 * 1024 * 1024

#: How much of one user turn is kept for clustering.  Skeletons are built from
#: the first tokens and examples are capped at 160 chars, so more than this is
#: memory for nothing -- and 20k turns * 400 chars is a bounded ~8 MB.
KEEP_TEXT_CHARS = 400

#: Turns analyzed per run.  Newest sessions are read first, so the cap drops
#: the oldest history, not the most relevant.
MAX_TURNS = 40000

EXAMPLE_CHARS = 160

# Per-list output caps.  emit() is the backstop; these keep it from ever
# having to fire on a normal repo.
TOP_COMMANDS = 12
TOP_SLASH = 10
TOP_CORRECTIONS = 10
TOP_TOOLS = 12
TOP_PAIN = 6
TOP_FILES = 12
TOP_DOCS = 6

#: Status questions are merged by topic before they get here, so five rows is
#: every distinct thing a developer can ask about progress.
TOP_META = 5

#: SACRIFICE ORDER for the character cap -- least load-bearing FIRST.
#:
#: The 81-session dogfood run emitted "output truncated: dropped 1 entry to fit
#: 12000 chars (request_shapes: 1)", which meant `--top 20` was a lie: the 20th
#: shape was invisible to phases 3-6, and the one list the whole plan is built
#: from was the one paying for the overflow.  `fit_to_cap()` walks this order
#: and `request_shapes` is last on purpose: it is only ever touched once every
#: other list is down to MIN_ROWS_KEPT.  `emit()` trims round-robin rather than
#: in order, so it stays as the backstop and this runs first.
TRIM_KEYS = [
    "doc_hotspots",
    "tool_mentions",
    "meta_queries",
    "file_hotspots",
    "slash_commands",
    "commands_requested",
    "pain_signals",
    "corrections",
    "request_shapes",
]

#: No list is trimmed below this while a later one in TRIM_KEYS still has more
#: (matches lib.emit.MIN_KEPT_PER_LIST, deliberately).
MIN_ROWS_KEPT = 3

#: Headroom `fit_to_cap()` leaves for the warning it appends and the
#: `output_chars` digits `emit()` stamps after it.
_CAP_RESERVE = 300


# ---------------------------------------------------------------------------
# Locating transcripts
#
# Claude Code encodes the project directory name from the absolute repo path
# by replacing "/", "." and "_" with "-".  Verified empirically against
# ~/.claude/projects on a machine with 107 project directories:
#
#   /Users/x/Documents/projects/acme/web-app
#     -> -Users-x-Documents-projects-acme-web-app
#   /Users/x/.claude/projects/foo        (note the doubled dash from "/.")
#     -> -Users-x--claude-projects-foo
#
# The encoding is LOSSY -- "a-b", "a.b", "a_b" and "a/b" all encode to "a-b" --
# so an exact directory hit is the only match we can fully trust.  Everything
# else is scored, used, and reported in `warnings` so the model can tell the
# user exactly which transcripts fed the plan.
# ---------------------------------------------------------------------------

_ENCODE_RE = re.compile(r"[/._]")


def encode_project_dir(abs_path):
    """Absolute repo path -> Claude Code project directory name."""
    return _ENCODE_RE.sub("-", abs_path or "")


def _dir_bytes(path, limit=4000):
    """Total size of the .jsonl files in a directory.  Cheap, bounded."""
    total = 0
    try:
        with os.scandir(path) as it:
            for index, entry in enumerate(it):
                if index >= limit:
                    break
                if entry.name.endswith(".jsonl"):
                    try:
                        total += entry.stat().st_size
                    except OSError:
                        pass
    except OSError:
        return 0
    return total


def _name_tokens(name):
    return [t for t in (name or "").lower().split("-") if t]


def _score_candidate(encoded, name):
    """
    How likely is project directory `name` to be this repo?

    Returns `(score, structural)`.  `structural` means the encoded repo path
    literally appears in the directory name -- a worktree, a scratchpad, or a
    session started in a subdirectory.  Those are the only near-misses worth
    telling the user about; a merely token-similar name is a different repo.

    1.00  exact
    0.92  the encoded repo path is a suffix of the name (scratchpad / worktree)
    0.86  the name embeds the encoded repo path somewhere else
    0.80  the name is the repo plus more segments (a cwd *inside* the repo)
    else  ordered token coverage, and only when the basenames agree -- without
          that guard `.../projects/acme/web-app` scores 0.67 against
          `.../projects/other-project`, which is a different project entirely.
    """
    if name == encoded:
        return (1.0, True)
    if not encoded or not name:
        return (0.0, False)
    if name.startswith(encoded + "-"):
        return (0.80, True)
    if name.endswith(encoded):
        return (0.92, True)
    if encoded in name:
        return (0.86, True)

    want = _name_tokens(encoded)
    have = _name_tokens(name)
    if not want or not have or have[-1] != want[-1]:
        return (0.0, False)
    cursor = 0
    matched = 0
    for token in want:
        while cursor < len(have) and have[cursor] != token:
            cursor += 1
        if cursor < len(have):
            matched += 1
            cursor += 1
    coverage = matched / float(max(len(want), len(have)))
    return (min(0.79, coverage), False)


def _config_home(env_var, default_dir, home):
    """
    Resolve an agent's config root, honouring its documented env override.

    adapters/claude-code.md 1.2 and adapters/codex.md 1.2 both require this:
    "never hardcode ~/.claude" / "resolve through ${CODEX_HOME:-$HOME/.codex}
    everywhere".  An unset or blank variable falls back to the home default.
    """
    override = os.environ.get(env_var, "")
    if override and override.strip():
        return os.path.abspath(os.path.expanduser(override.strip()))
    return os.path.join(home, default_dir)


def locate_claude_root(repo, home, warnings):
    """
    Resolve the project directory for `repo`, and report the near-misses.

    Returns `(root_or_None, match_mode)` where match_mode is one of
    "exact", "fuzzy", "basename", "none".
    """
    projects = os.path.join(_config_home("CLAUDE_CONFIG_DIR", ".claude", home), "projects")
    if not os.path.isdir(projects):
        emit_lib.warn(
            warnings,
            "no Claude Code transcript directory at %s; ran with zero transcript evidence"
            % _safe(projects),
        )
        return (None, "none")

    encoded = encode_project_dir(repo)
    try:
        names = sorted(
            n for n in os.listdir(projects) if os.path.isdir(os.path.join(projects, n))
        )
    except OSError as exc:
        emit_lib.warn(warnings, "could not list transcript directories: %s" % exc)
        return (None, "none")

    scored = []
    for name in names:
        score, structural = _score_candidate(encoded, name)
        if score >= 0.55:
            scored.append((score, _dir_bytes(os.path.join(projects, name)), name, structural))
    scored.sort(key=lambda row: (-row[0], -row[1], row[2]))

    chosen = None
    mode = "none"
    if scored and scored[0][0] >= 1.0:
        chosen = scored[0][2]
        mode = "exact"
    elif scored:
        chosen = scored[0][2]
        mode = "fuzzy"
        emit_lib.warn(
            warnings,
            "no exact transcript directory for this repo; using closest match "
            "'%s' (confidence %.2f) -- confirm with the user before trusting counts"
            % (chosen, scored[0][0]),
        )
    else:
        base = encode_project_dir(os.path.basename(repo.rstrip(os.sep)))
        fallback = [
            n
            for n in names
            if n == base or n.endswith("-" + base) or _name_tokens(n)[-1:] == _name_tokens(base)[-1:]
        ]
        if fallback:
            fallback.sort(key=lambda n: (-_dir_bytes(os.path.join(projects, n)), n))
            chosen = fallback[0]
            mode = "basename"
            emit_lib.warn(
                warnings,
                "no transcript directory matched this repo path; fell back to a "
                "basename match on '%s' -- these transcripts may be from a "
                "different checkout" % chosen,
            )

    if chosen is None:
        emit_lib.warn(
            warnings,
            "no Claude Code transcripts found for this repo (looked for '%s'); "
            "evidence is repo-only" % encoded,
        )
        return (None, "none")

    others = [name for _s, _b, name, structural in scored if name != chosen and structural]
    if others:
        shown = ", ".join(others[:4])
        more = "" if len(others) <= 4 else " (+%d more)" % (len(others) - 4)
        emit_lib.warn(
            warnings,
            "%d other transcript director%s embed this repo path (worktrees, "
            "sessions started in a subdirectory, scratchpads) and were NOT merged: %s%s"
            % (len(others), "y" if len(others) == 1 else "ies", shown, more),
        )

    return (os.path.join(projects, chosen), mode)


# ---------------------------------------------------------------------------
# Locating Codex sessions
#
# Codex has NO per-project directory.  Every rollout on the machine lands in
# one shared tree,
#
#     ${CODEX_HOME:-~/.codex}/sessions/YYYY/MM/DD/rollout-<ISO>-<uuid>.jsonl
#
# and the only thing tying a rollout to a repository is the `cwd` recorded in
# its FIRST record, which is always a `session_meta`.  Verified on a 324-file
# install: 324 of 324 files open with `session_meta` and every one of those
# payloads carries `cwd`.  So the locate step is "walk the tree, read ONE line
# per file, keep the ones pointing at this repo" -- measured at 0.15 s for the
# whole 324-file / 554 MB corpus, because no file is opened past its first
# line and nothing is parsed except that line.
#
# ARCHIVED SESSIONS ARE INCLUDED.  `${CODEX_HOME}/archived_sessions/` holds the
# same format, and archiving MOVES a rollout rather than copying it -- measured
# zero id overlap between the two trees, so reading both cannot double-count.
# On the verification machine it held 84 files (~40 of them mineable) whose
# dates sit INSIDE the live tree's range, i.e. archiving is a user action and
# not age eviction: skipping the tree silently discards a third of one repo's
# history.  Its layout is FLAT on that install (no YYYY/MM/DD sharding), so the
# walker handles both shapes rather than assuming the date tree.
# ---------------------------------------------------------------------------


def locate_codex_roots(home, warnings, include_archived=True):
    """
    Codex transcript roots for this machine, newest tree first.

    Returns `(roots, primary_or_None)`.  `primary` is the live `sessions/`
    directory and is what the report names as `transcript_root`; `roots` is
    every tree that will actually be walked.
    """
    codex_home = _config_home("CODEX_HOME", ".codex", home)
    live = os.path.join(codex_home, "sessions")
    archived = os.path.join(codex_home, "archived_sessions")

    roots = []
    if os.path.isdir(live):
        roots.append(live)
    if include_archived and os.path.isdir(archived):
        roots.append(archived)

    if not roots:
        emit_lib.warn(
            warnings,
            "no Codex session directory at %s; ran with zero transcript evidence"
            % _safe(live),
        )
        return ([], None)

    if len(roots) > 1:
        emit_lib.warn(
            warnings,
            "reading archived Codex sessions too (%s): archiving MOVES a rollout, "
            "so the two trees share no session and cannot double-count"
            % _safe(archived),
        )
    return (roots, live if os.path.isdir(live) else roots[0])


# --- the repo's own git remote --------------------------------------------
#
# Codex records `session_meta.payload.git = {commit_hash, branch,
# repository_url}` -- something Claude Code's transcripts have no equivalent
# of, and the single largest recall win available on this target.  Measured:
# a cwd match on one repo's canonical path found 2 sessions; matching the same
# repo's `repository_url` found 39, the rest living in git worktrees under a
# completely different directory.
#
# Read with the standard library, never a subprocess: this script shells out to
# nothing, and `.git/config` is plain INI.

_GIT_SECTION_RE = re.compile(r"^\s*\[([^\]]+)\]\s*$")
_GIT_KEY_RE = re.compile(r"^\s*([A-Za-z0-9_.-]+)\s*=\s*(.*?)\s*$")


def _git_dir(repo):
    """
    `repo/.git` resolved to the directory holding `config`.

    A worktree's `.git` is a FILE reading `gitdir: <path>`, and that path is a
    per-worktree directory whose `config` lives in the shared git dir named by
    `commondir`.  Both hops are followed here; anything unexpected returns None
    rather than guessing.
    """
    dot_git = os.path.join(repo, ".git")
    if os.path.isdir(dot_git):
        return dot_git
    if not os.path.isfile(dot_git):
        return None
    try:
        with open(dot_git, "r", errors="replace") as handle:
            head = handle.read(4096)
    except OSError:
        return None
    found = re.search(r"^\s*gitdir:\s*(.+?)\s*$", head, re.MULTILINE)
    if not found:
        return None
    gitdir = found.group(1)
    if not os.path.isabs(gitdir):
        gitdir = os.path.normpath(os.path.join(repo, gitdir))
    if os.path.isfile(os.path.join(gitdir, "config")):
        return gitdir
    common = os.path.join(gitdir, "commondir")
    if os.path.isfile(common):
        try:
            with open(common, "r", errors="replace") as handle:
                rel = handle.read(4096).strip()
        except OSError:
            return None
        if rel:
            resolved = rel if os.path.isabs(rel) else os.path.normpath(os.path.join(gitdir, rel))
            if os.path.isdir(resolved):
                return resolved
    return gitdir if os.path.isdir(gitdir) else None


def repo_git_url(repo):
    """
    The `origin` remote URL of `repo`, or "" when there is none.

    Falls back to the first remote in the file when there is no `origin`, since
    a checkout with a single differently-named remote is still that repository.
    """
    gitdir = _git_dir(repo or "")
    if not gitdir:
        return ""
    config = os.path.join(gitdir, "config")
    try:
        with open(config, "r", errors="replace") as handle:
            text = handle.read(256 * 1024)
    except OSError:
        return ""

    section = ""
    origin = ""
    first = ""
    for line in text.splitlines():
        found = _GIT_SECTION_RE.match(line)
        if found:
            section = found.group(1).strip().lower()
            continue
        if not section.startswith("remote "):
            continue
        pair = _GIT_KEY_RE.match(line)
        if not pair or pair.group(1).lower() != "url":
            continue
        url = pair.group(2)
        if not url:
            continue
        if not first:
            first = url
        if section == 'remote "origin"':
            origin = url
    return origin or first


_URL_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://")
_URL_USERINFO_RE = re.compile(r"^[^/@]+@")
_SCP_HOST_RE = re.compile(r"^([^/:]+):(?!\d)")


def normalize_git_url(url):
    """
    Compare two remote URLs for "is this the same repository?".

    `https://github.com/Org/repo.git`, `git@github.com:Org/repo.git` and
    `ssh://git@github.com/Org/repo/` all reduce to `github.com/org/repo`.
    Anything unrecognizable reduces to its own lowercased self, which can only
    match itself -- the safe direction.
    """
    value = (url or "").strip()
    if not value:
        return ""
    value = _URL_SCHEME_RE.sub("", value)
    value = _URL_USERINFO_RE.sub("", value)
    value = _SCP_HOST_RE.sub(r"\1/", value, count=1)
    value = value.rstrip("/")
    if value.lower().endswith(".git"):
        value = value[:-4]
    return value.strip("/").lower()


def diagnostic_git_url(url):
    """
    A git remote in the form it may be PRINTED in, which is not the form it is
    read in.

    A remote routinely carries credentials -- `https://user:token@host/org/repo`
    is what a CI checkout or a PAT-authenticated clone leaves in `.git/config`
    -- and `--debug` writes to stderr, which is outside the JSON object every
    other string in this script is scrubbed on the way into.  Printing the raw
    URL put a password on a terminal and into whatever captured it.

    `normalize_git_url()` already drops the scheme and the userinfo, which is
    exactly the credential-bearing part, and what it leaves is the form the
    repository match was actually made on -- so the diagnostic says more about
    the match than the raw URL did, not less.  The `@` sweep behind it is belt
    and braces for a URL shape the normalizer does not recognise and therefore
    returns unchanged.
    """
    value = normalize_git_url(url)
    if not value:
        return "-"
    if "@" in value:
        value = value.rsplit("@", 1)[-1]
    return value or "-"


# --- walking the date tree -------------------------------------------------


def list_codex_session_files(roots, days=None, warnings=None):
    """
    `[(path, mtime, size)]` for every Codex rollout, newest first, pre-filtered
    by `--days` on each file's LAST WRITE time and on nothing else.

    THE DIRECTORY NAME IS NOT A FILTER.  `sessions/YYYY/MM/DD` records the date
    the session STARTED, and a rollout keeps being appended to for as long as
    the thread is resumed, so an 80-day-old directory routinely holds a thread
    that was worked on an hour ago.  This function used to prune whole date
    directories with a few days of slack, which is cheaper and is wrong in
    exactly that case: the slack papered over a resume inside the first week and
    silently dropped every longer-lived thread, consent window or not.

    A last-write time is the one cheap fact that can EXCLUDE a file soundly -- a
    file whose last write predates the cutoff cannot hold a record written after
    it -- and it is the same test `select_sessions()` applies on the Claude Code
    side.  Applying it here rather than only there is worth doing because
    `match_codex_sessions()` opens the head of every row this returns.

    The pre-filter only narrows I/O; it decides nothing.  See the consent rule
    above `_iso_cutoff()`: `read_codex_session()` still tests every turn's own
    timestamp, which is what the window actually means.
    """
    rows = []
    skipped_old = 0
    cutoff_epoch = None
    if days and days > 0:
        cutoff_epoch = (_utc_now().replace(tzinfo=datetime.timezone.utc) - datetime.timedelta(days=int(days))).timestamp()

    for root in roots or []:
        try:
            for dirpath, _dirnames, filenames in os.walk(root):
                for name in filenames:
                    if not name.endswith(".jsonl"):
                        continue
                    full = os.path.join(dirpath, name)
                    try:
                        stat = os.stat(full)
                    except OSError:
                        continue
                    if cutoff_epoch is not None and stat.st_mtime < cutoff_epoch:
                        skipped_old += 1
                        continue
                    rows.append((full, stat.st_mtime, stat.st_size))
        except OSError:
            continue

    if skipped_old and warnings is not None:
        emit_lib.warn(
            warnings,
            "--days %d: %d Codex rollout(s) whose last write predates the window "
            "were not opened; a thread filed under an older date but resumed "
            "inside the window IS read, because the date directory records when "
            "the session started, not when it was last worked on"
            % (int(days), skipped_old),
        )

    rows.sort(key=lambda row: (-row[1], row[0]))
    return rows


# --- session_meta ----------------------------------------------------------


def codex_session_meta(path):
    """
    The `session_meta` payload of one rollout, or None.

    Only the first few lines are read.  `session_meta` is the first record in
    every file measured (324 of 324, live and archived), and a file can carry
    several of them -- up to 45 on one measured session -- but their `cwd`
    values never disagree, so the first one is the answer and the rest are
    resume/fork markers.
    """
    try:
        with open(path, "rb") as handle:
            for index, raw in enumerate(handle):
                if index > 4:
                    break
                if b"session_meta" not in raw:
                    continue
                if len(raw) > MAX_LINE_BYTES:
                    return None
                try:
                    record = json.loads(raw.decode("utf-8", "replace"))
                except (ValueError, UnicodeDecodeError):
                    return None
                if not isinstance(record, dict):
                    return None
                payload = record.get("payload")
                return payload if isinstance(payload, dict) else None
    except OSError:
        return None
    return None


def is_codex_subagent(meta):
    """
    Is this rollout a harness thread rather than the developer talking?

    Codex spawns subagents as SEPARATE rollout files whose "user" turns are the
    parent agent's prompt to the subagent.  They read like human requests, they
    cluster beautifully, and every one of them is a false signal -- exactly
    what `isSidechain: true` marks on Claude Code, which this miner has always
    dropped.  Measured on the verification install: 192 of 324 rollouts, 60%
    of the corpus.

    Three independent markers, OR-ed because each catches files the others
    miss (older builds set `source.subagent` without `thread_source`):

      thread_source == "subagent"          143 files
      source.subagent present              148 metas
      parent_thread_id set                 145 metas, every one of them a
                                           subagent or guardian_review thread
                                           and ZERO plain user threads

    `guardian_review` is a second harness thread kind: a safety-review thread
    that replays the real user's transcript inside its own prompt, so mining it
    both double-counts genuine requests and injects the reviewer's framing.
    """
    if not isinstance(meta, dict):
        return False
    if meta.get("thread_source") in ("subagent", "guardian_review"):
        return True
    source = meta.get("source")
    if isinstance(source, dict) and "subagent" in source:
        return True
    if meta.get("parent_thread_id"):
        return True
    return False


def _meta_git_url(meta):
    git = (meta or {}).get("git")
    if isinstance(git, dict):
        url = git.get("repository_url")
        if isinstance(url, str):
            return url
    return ""


def _nested_repo_between(repo, cwd):
    """
    True when a DIFFERENT git repository sits between `repo` and `cwd`.

    `~/projects/code-integri/ta-code-integri-scanner` is its own checkout
    nested inside `~/projects/code-integri`; a plain prefix match absorbs it
    and reports another project's sessions as this repo's.  A `.git` at any
    directory below the repo root and at or above the session's cwd says the
    session belongs to that inner repository, not this one.
    """
    if not repo or not cwd or cwd == repo:
        return False
    rest = cwd[len(repo):].lstrip("/") if cwd.startswith(repo.rstrip("/") + "/") else ""
    if not rest:
        return False
    walk = repo.rstrip("/")
    for segment in rest.split("/"):
        walk = walk + "/" + segment
        if os.path.exists(os.path.join(walk, ".git")):
            return True
    return False


def match_codex_sessions(rows, repo, repo_url, warnings):
    """
    Keep the rollouts that belong to `repo`, and say what was kept and why.

    Three accepted relationships, in the order they are tested:

      root      session_meta.cwd IS the repo
      subdir    cwd is a directory INSIDE the repo -- a real and common case
                (one measured repo had a session started in `apps/triggers`),
                rejected only when a different checkout sits in between
      worktree  cwd is somewhere else entirely but session_meta.git
                .repository_url is this repo's remote.  This is how Codex
                sessions run from git worktrees are recovered, and it is worth
                far more than it sounds: measured 2 sessions by path and 39 by
                remote on the same repository.

    Every kept group is reported in `warnings`, the way the Claude Code path
    reports the sibling project directories it did NOT merge, so the user can
    see exactly which sessions fed the plan.
    """
    kept = []
    metas = {}
    groups = {"root": [], "subdir": [], "worktree": []}
    subagents = 0
    nested = {}
    unreadable = 0
    other_repos = 0
    repo_key = normalize_git_url(repo_url)
    repo_clean = (repo or "").rstrip(os.sep)

    for path, mtime, size in rows:
        meta = codex_session_meta(path)
        if meta is None:
            unreadable += 1
            continue
        if is_codex_subagent(meta):
            subagents += 1
            continue

        cwd = meta.get("cwd")
        if not isinstance(cwd, str) or not cwd:
            cwd = ""
        cwd = cwd.rstrip(os.sep) or cwd
        session_key = normalize_git_url(_meta_git_url(meta))

        kind = None
        if cwd and cwd == repo_clean:
            kind = "root"
        elif cwd and cwd.startswith(repo_clean + os.sep):
            # A different remote at the same path is decisive; otherwise look
            # for a `.git` between the two, which is the only evidence
            # available when neither side has a remote.
            if (repo_key and session_key and session_key != repo_key) or _nested_repo_between(
                repo_clean, cwd
            ):
                nested[cwd] = nested.get(cwd, 0) + 1
                continue
            kind = "subdir"
        elif repo_key and session_key and session_key == repo_key:
            kind = "worktree"
        else:
            other_repos += 1
            continue

        kept.append((path, mtime, size))
        metas[path] = meta
        groups[kind].append(cwd)

    def _named(cwds, limit=4):
        tally = {}
        for cwd in cwds:
            tally[cwd] = tally.get(cwd, 0) + 1
        ordered = sorted(tally.items(), key=lambda kv: (-kv[1], kv[0]))
        shown = ", ".join("%s (%d)" % (_safe(cwd), n) for cwd, n in ordered[:limit])
        if len(ordered) > limit:
            shown += " (+%d more)" % (len(ordered) - limit)
        return shown

    if groups["subdir"]:
        emit_lib.warn(
            warnings,
            "%d Codex session(s) were started in a subdirectory of this repo and "
            "ARE included: %s"
            % (len(groups["subdir"]), _named(groups["subdir"])),
        )
    if groups["worktree"]:
        emit_lib.warn(
            warnings,
            "%d Codex session(s) ran outside this checkout but against the same "
            "git remote (worktrees, a second clone) and ARE included: %s -- "
            "matched on session_meta.git.repository_url, not on path"
            % (len(groups["worktree"]), _named(groups["worktree"])),
        )
    if nested:
        emit_lib.warn(
            warnings,
            "%d Codex session(s) under this repo's path belong to a DIFFERENT "
            "checkout nested inside it and were excluded: %s"
            % (sum(nested.values()), _named(list(nested.keys()))),
        )
    if subagents:
        emit_lib.warn(
            warnings,
            "%d Codex rollout(s) are subagent or guardian-review threads and were "
            "excluded: their 'user' turns are the agent's own prompts, not this "
            "developer's" % subagents,
        )
    if unreadable:
        emit_lib.warn(
            warnings,
            "%d Codex rollout(s) had no readable session_meta record and could not "
            "be attributed to any repo" % unreadable,
        )
    if rows and not kept:
        emit_lib.warn(
            warnings,
            "found %d Codex rollout(s) but none belong to this repo (%d were "
            "other projects, %d were subagent threads)"
            % (len(rows), other_repos, subagents),
        )
    return (kept, metas)


# --- forks -----------------------------------------------------------------
#
# Codex forks a thread by COPYING its history into a new rollout.  The copy is
# re-serialized: measured on a real fork, 26 of the child's 31 user turns are
# the parent's turns verbatim, and NOT ONE of them kept the parent's timestamp.
# So `(text, timestamp)` -- the obvious de-duplication key, and the one the
# format survey suggested -- silently matches nothing on this build, while a
# plain text key across all sessions would erase the genuine repetition that is
# the whole point of this report.
#
# The key that is both safe and sufficient: a turn is a fork copy when its text
# already appeared IN THE THREAD THIS ONE WAS FORKED FROM.  That is scoped to a
# real parent/child edge, so two sessions that independently say "commit and
# push" still count twice, which is correct.


def codex_read_order(selected, metas):
    """
    Read order for one repo's rollouts: a fork's ancestor always first.

    Selection is newest-first (so `--max-sessions` keeps recent history), but a
    fork is by definition newer than the thread it copied, so reading in that
    order would see the copy before the original and have nothing to compare
    it against.  Ancestors are hoisted; everything else stays oldest-first so
    `first_seen` / `last_seen` read naturally.
    """
    by_id = {}
    for path, _mtime, _size in selected:
        meta = metas.get(path) or {}
        thread_id = meta.get("id") or meta.get("session_id")
        if thread_id:
            by_id.setdefault(str(thread_id), path)

    order = []
    placed = set()

    def place(path, depth=0):
        if path in placed or depth > 32:
            return
        placed.add(path)
        meta = metas.get(path) or {}
        parent = meta.get("forked_from_id")
        if parent:
            parent_path = by_id.get(str(parent))
            if parent_path and parent_path not in placed:
                place(parent_path, depth + 1)
        order.append(path)

    for path, _mtime, _size in sorted(selected, key=lambda row: (row[1], row[0])):
        place(path)
    return order


# ---------------------------------------------------------------------------
# Session file selection
# ---------------------------------------------------------------------------


def _utc_now():
    """Naive UTC.  `utcnow()` is deprecated from 3.12 and this keeps 3.9 happy."""
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


# THE CONSENT RULE.  Stated once, here, because two defects broke it in
# opposite directions and each of the obvious repairs re-broke the other.
#
#   1. THE TURN'S OWN TIMESTAMP DECIDES.  Under bounded consent ("last N days")
#      a record is analyzed only when its own timestamp is inside the window.
#      A record carrying NO timestamp cannot be shown to be inside it, so it is
#      not analyzed at all -- silence is the only answer that is not a guess
#      about something the user set a boundary on.  Under unbounded consent
#      ("yes") there is no window and every record is in scope.
#
#   2. A DIRECTORY NAME OR A FILE MTIME IS ONLY A PRE-FILTER.  It exists to
#      avoid I/O, never to decide.  It may WIDEN the candidate set -- a rollout
#      filed under the date its session started and appended to for months is
#      read in full, and rule 1 then drops the turns that are actually old --
#      and it may never ADMIT an out-of-window turn.  It may narrow the set only
#      where narrowing is provable: a file whose LAST WRITE predates the cutoff
#      cannot hold a record written after it.  A creation-date directory proves
#      nothing of the kind and is never used to exclude anything.
#
# Enforcement sites, all of them: `select_sessions()` and
# `list_codex_session_files()` implement rule 2; `read_claude_session()`,
# `read_codex_session()` and the `last-prompt` fallback in `main()` implement
# rule 1.


def _record_time(value):
    """Parse a transcript timestamp as UTC; missing or malformed is unknown."""
    if not isinstance(value, str) or "T" not in value:
        return None
    try:
        moment = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=datetime.timezone.utc)
        return moment.astimezone(datetime.timezone.utc)
    except (ValueError, OverflowError):
        return None


def _within_window(timestamp, cutoff):
    if not cutoff:
        return True
    moment, boundary = _record_time(timestamp), _record_time(cutoff)
    return moment is not None and boundary is not None and moment >= boundary


def _iso_cutoff(days):
    """
    The window boundary as an ISO prefix, or None for unbounded consent.

    None is the whole of "consent: yes": every caller reads `if cutoff_iso` and
    a falsy cutoff means no window exists to test a turn against.
    """
    if not days or days <= 0:
        return None
    moment = _utc_now() - datetime.timedelta(days=int(days))
    return moment.strftime("%Y-%m-%dT%H:%M:%S")


def list_session_files(root, recursive=False):
    """`[(path, mtime, size)]`, newest first."""
    rows = []
    if not root:
        return rows
    try:
        if recursive:
            for dirpath, _dirnames, filenames in os.walk(root):
                for name in filenames:
                    if name.endswith(".jsonl"):
                        full = os.path.join(dirpath, name)
                        try:
                            stat = os.stat(full)
                        except OSError:
                            continue
                        rows.append((full, stat.st_mtime, stat.st_size))
        else:
            with os.scandir(root) as it:
                for entry in it:
                    if not entry.name.endswith(".jsonl"):
                        continue
                    try:
                        stat = entry.stat()
                    except OSError:
                        continue
                    rows.append((entry.path, stat.st_mtime, stat.st_size))
    except OSError:
        return rows
    rows.sort(key=lambda row: (-row[1], row[0]))
    return rows


def _human_bytes(count):
    """Byte count as the largest unit that keeps it readable."""
    count = int(count or 0)
    for unit, size in (("GB", 1024 ** 3), ("MB", 1024 ** 2), ("KB", 1024)):
        if count >= size:
            return "%.3g %s" % (count / float(size), unit)
    return "%d bytes" % count


def select_sessions(rows, days, max_sessions, max_bytes, warnings):
    """
    Apply --days, --max-sessions and --max-bytes, newest first.

    --days here is rule 2 of the consent rule above: a pre-filter on file mtime,
    sound because a file whose last write predates the cutoff cannot hold a
    record written after it, and the single biggest speedup available.  It
    decides nothing -- the readers still test every record's own timestamp,
    which is rule 1, and a file that survives this test can still contribute
    zero turns.
    """
    selected = []
    skipped_old = 0
    dropped_cap = 0
    dropped_budget = 0
    budget = max_bytes if max_bytes and max_bytes > 0 else None

    cutoff_epoch = None
    if days and days > 0:
        cutoff_epoch = (_utc_now().replace(tzinfo=datetime.timezone.utc) - datetime.timedelta(days=int(days))).timestamp()

    used = 0
    for path, mtime, size in rows:
        if cutoff_epoch is not None and mtime < cutoff_epoch:
            skipped_old += 1
            continue
        if max_sessions and len(selected) >= max_sessions:
            dropped_cap += 1
            continue
        if budget is not None and used + size > budget and selected:
            dropped_budget += 1
            continue
        selected.append((path, mtime, size))
        used += size

    if skipped_old:
        emit_lib.warn(
            warnings,
            "--days %d: %d session file(s) older than the window were not read"
            % (int(days), skipped_old),
        )
    if dropped_cap:
        emit_lib.warn(
            warnings,
            "--max-sessions %d: %d older session file(s) not read"
            % (int(max_sessions), dropped_cap),
        )
    if dropped_budget:
        emit_lib.warn(
            warnings,
            "--max-bytes %s reached: %d older session file(s) not read; counts "
            "below undercount older history%s"
            % (
                _human_bytes(max_bytes or 0),
                dropped_budget,
                # The newest file is always read, even when it alone is over
                # budget, so a run is never empty.  Say so, or `bytes_read`
                # exceeding `--max-bytes` reads as a bug.
                " (the newest session is read even when it alone exceeds the "
                "budget, so bytes_read can exceed --max-bytes)"
                if used > (max_bytes or 0)
                else "",
            ),
        )
    return selected


# ---------------------------------------------------------------------------
# Record filtering  (verified against real Claude Code JSONL, build contract)
# ---------------------------------------------------------------------------

_B_USER = b'"user"'
_B_LAST_PROMPT = b'"last-prompt"'
_B_TOOL_USE_RESULT = b'"toolUseResult"'
_B_TOOL_RESULT = b'"tool_result"'
_B_SIDECHAIN = (b'"isSidechain":true', b'"isSidechain": true')
_B_META = (b'"isMeta":true', b'"isMeta": true')


def _wants(raw):
    """Cheap byte-level triage before any json.loads.  Rejects must be safe:
    a false negative loses a turn, so every test here is one the parsed record
    would fail anyway."""
    if _B_TOOL_USE_RESULT in raw or _B_TOOL_RESULT in raw:
        return False
    if _B_USER not in raw and _B_LAST_PROMPT not in raw:
        return False
    for marker in _B_SIDECHAIN:
        if marker in raw:
            return False
    for marker in _B_META:
        if marker in raw:
            return False
    return True


def _blocks_text(content):
    """
    `message.content` is a string, or a list of blocks.  Only `text` blocks
    count; a single `tool_result` block disqualifies the whole record.
    """
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return None
    parts = []
    for block in content:
        if not isinstance(block, dict):
            continue
        kind = block.get("type")
        if kind == "tool_result":
            return None
        if kind == "text":
            value = block.get("text")
            if isinstance(value, str):
                parts.append(value)
    return "\n".join(parts)


# --- wrapper stripping -----------------------------------------------------


def _pair(tag):
    return re.compile(r"<%s\b[^>]*>.*?</%s\s*>" % (tag, tag), re.IGNORECASE | re.DOTALL)


def _open_ended(tag):
    return re.compile(r"<%s\b[^>]*>.*\Z" % tag, re.IGNORECASE | re.DOTALL)


#: Presence of any of these means the record is machine chatter, not a request.
_DROP_TAGS = ("task-notification", "local-command-stdout")

#: Removed wholesale.  Injected context the user never typed.
_STRIP_TAGS = (
    "command-message",
    "ide_opened_file",
    "ide_selection",
    "system-reminder",
    "environment_context",
    "user-prompt-submit-hook",
    "nested_memory",
    "file-content",
    # Claude Code wraps the "DO NOT respond to these messages" boilerplate
    # around every `!`-run local command.  Measured across four project
    # histories: 41 user records carried it.
    "local-command-caveat",
)

#: Text the HARNESS writes into a record typed as a user turn.  None of it was
#: typed by a human, and all of it clusters beautifully, which is what makes it
#: dangerous: the compact/resume preamble alone produced a `request_shapes`
#: entry ("session continued previous conversation ran context summary below")
#: and a `corrections` entry ("Resume directly -- do not acknowledge the
#: summary, do not recap what was happening") on the runs measured.
_HARNESS_TEXT = re.compile(
    r"This session is being continued from a previous conversation"
    r"|Caveat: The messages below were generated by the user while running"
    r"|Your task is to create a detailed summary of the conversation"
    r"|Please continue the conversation from where we left it off"
    r"|analysis to continue the conversation from where we left off"
    r"|Resume directly\s*[-\u2013\u2014]+\s*do not acknowledge the summary"
    r"|^\s*<\s*local-command-caveat",
    re.IGNORECASE | re.MULTILINE,
)

_DROP_RE = [(_pair(t), _open_ended(t)) for t in _DROP_TAGS]
_STRIP_RE = [(_pair(t), _open_ended(t)) for t in _STRIP_TAGS]

_COMMAND_NAME_RE = re.compile(r"<command-name>\s*([^<\s]{1,120})\s*</command-name>", re.IGNORECASE)
_COMMAND_ARGS_RE = re.compile(r"<command-args>(.*?)</command-args>", re.IGNORECASE | re.DOTALL)
_ANY_TAG_LEFTOVER = re.compile(r"</?(?:command-args|command-name)\s*>", re.IGNORECASE)

# Lowercase, and the name must end the token -- otherwise "/Users/me/app.ts fix
# this" reads as a slash command called "Users".
_LEADING_SLASH_CMD = re.compile(r"^/([a-z0-9_:.-]{2,60})(?=\s|$)")

#: Claude Code's own session commands.  They are housekeeping, not workflows:
#: `/model fable[1m]` is not a request, and counting `/compact` next to a
#: hand-built `/deploy` would bury the thing that matters -- which workflows
#: this developer has already formalized.
_BUILTIN_SLASH = frozenset(
    """
    model compact clear resume cost context help login logout status config
    terminal-setup vim doctor bug agents permissions ide memory add-dir export
    hooks install-github-app output-style pr-comments release-notes todos
    upgrade usage plugin mcp exit quit privacy-settings statusline rewind
    feedback theme approved-tools allowed-tools sandbox init
    """.split()
)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?\n])\s+")


def sentence_around(text, position):
    """
    The sentence containing `position`.

    A pain marker quoted with its own sentence is evidence; the first 160
    characters of a 4 KB turn that happens to contain the marker is not.
    """
    if not text:
        return ""
    cursor = 0
    for candidate in _SENTENCE_SPLIT.split(text):
        end = cursor + len(candidate)
        if cursor <= position <= end:
            found = candidate.strip()
            if found:
                return found
            break
        cursor = end + 1
    return text

_JUNK = re.compile(
    r"^\s*(?:"
    r"\[request interrupted"
    r"|\[image\b"
    r"|\[pasted (?:text|content)\b"
    r"|\[screenshot\b"
    r"|\[attached\b"
    r"|\(no content\)"
    r")",
    re.IGNORECASE,
)

_WS_RE = re.compile(r"\s+")


def unwrap(text):
    """
    Strip the wrappers Claude Code injects around a user turn.

    Returns `(clean_or_None, slash_command_or_None)`.  `None` means the record
    is not a request at all and must be dropped.
    """
    if not text:
        return (None, None)

    for pair_re, open_re in _DROP_RE:
        if pair_re.search(text) or open_re.search(text):
            return (None, None)

    # Harness-authored records masquerading as user turns.  Dropped whole:
    # there is no human sentence in them to salvage.
    if _HARNESS_TEXT.search(text):
        return (None, None)

    slash = None
    found = _COMMAND_NAME_RE.search(text)
    if found:
        slash = found.group(1).lstrip("/").strip()
        text = _COMMAND_NAME_RE.sub(" ", text)

    # <command-args> holds the actual prompt the user typed after the slash
    # command.  Unwrap it; do not drop it.
    text = _COMMAND_ARGS_RE.sub(lambda m: " " + (m.group(1) or "") + " ", text)

    for pair_re, open_re in _STRIP_RE:
        text = pair_re.sub(" ", text)
        text = open_re.sub(" ", text)

    text = _ANY_TAG_LEFTOVER.sub(" ", text)
    text = text.strip()

    if not text or len(text) < 3:
        return (None, slash)
    if _JUNK.match(text):
        return (None, slash)
    # Punctuation-only / emoji-only acks carry no shape.
    if not re.search(r"[A-Za-z0-9]", text):
        return (None, slash)

    if slash is None:
        head = _LEADING_SLASH_CMD.match(text)
        if head:
            slash = head.group(1)

    # `/model fable[1m]`, `/compact`, `/plugin ...`: the arguments are settings,
    # not a request.  Drop the turn; the command name is still counted.
    if slash and slash.split(":")[-1].lower() in _BUILTIN_SLASH:
        return (None, slash)

    return (text, slash)


# ---------------------------------------------------------------------------
# Signal extraction
# ---------------------------------------------------------------------------

#: A line that is machine output, not something a human typed.  Pasted logs,
#: stack traces and terminal transcripts are the single biggest source of
#: garbage clusters: they are long, they repeat verbatim, and they cluster
#: beautifully into shapes that map to no artifact whatsoever.
_PASTE_LINE_ANY = re.compile(
    r"[\u279c\u2714\u2716\u2717\u2718\u2605\u203a\u00bb\u2502\u2514\u251c\u2588]"  # ➜ ✔ ✖ ✗ ★ › » │ └ ├ █
    r"|npm ERR!"
    r"|Traceback \(most recent call last\)"
    r"|node_modules/"
    r"|exited with (?:error )?code \d+"
    r"|^\s*at [\w$.<>\[\]]+ ?\("
    r"|^\s*File \"[^\"]+\", line \d+"
    r"|^\s*(?:\$|%)\s+\S"
    r"|^\s*(?:---|===|\+\+\+|\*\*\*)\s"
    r"|^\s*\d{4}-\d\d-\d\d[T ]\d\d:\d\d"
    r"|\x1b\["
    # Pasted documents: plan files, session summaries, handoffs.  They have no
    # shell glyphs but they are just as much "not a request" as a stack trace,
    # and their imperative sentences ("do not re-investigate these") otherwise
    # get counted as corrections the user never made.
    r"|^\s*#{1,6}\s+\S"
    r"|^\s*\*\*[^*\n]{1,80}\*\*\s*:?\s*$"
    r"|^\s*\*\*[^*\n]{1,80}:\*\*"
    r"|^\s*\d{1,2}[.)]\s+\*\*"
    # Pasted chat: "Ravi [11:18 PM] no.."
    r"|^\s*[A-Za-z][\w .'-]{0,30}\s+\[\d{1,2}:\d{2}\s?[AaPp]\.?[Mm]\.?\]"
    r"|^\s*<[a-z][a-z0-9_-]{2,40}>\s*$"
)

# --- correction sentence filters -------------------------------------------
#
# `detect_correction()` fires on a marker word, and markers are common.  These
# three filters are what separate an instruction the developer gave their agent
# ("Do not commit, stage, push or change branch without asking me first") from
# a sentence that merely contains "don't":
#
#   _DOC_LINE        a line lifted out of a pasted plan, summary or chat log
#   _SELF_STATEMENT  the user describing themselves ("i don't have the cable")
#   _DIRECTIVE       something actually aimed at the agent
#
# Corrections are read from the WHOLE turn, not the prose prefix: the strongest
# rules in this corpus live deep inside long hand-written spec prompts.

_DOC_LINE = re.compile(
    r"\*\*"
    r"|^\s*#{1,6}\s"
    r"|^\s*>\s"
    r"|^\s*\|"
    r"|^\s*[-*+]\s+[A-Z][\w /.-]{0,40}:"
    r"|\[\d{1,2}:\d{2}\s?[AaPp]\.?[Mm]\.?\]"
    r"|^\s*`{3}"
)

# "i don't have the cable", "I fucking don't know anything" -- the user
# describing their own situation.  Restricted to stative verbs so that
# "i don't want you to use npm" still counts as a rule.
_SELF_STATEMENT = re.compile(
    r"\bi\s+(?:\w+\s+){0,2}(?:don'?t|do not|didn'?t|did not|can'?t|cannot|won'?t|"
    r"will not|am not|haven'?t|have not|doubt)\s+"
    r"(?:have|know|see|care|understand|remember|get|think|feel|mind|recall|own|like|agree|believe)\b",
    re.IGNORECASE,
)

#: The contrast form: "use bun, not npm", "call the repo layer rather than raw
#: sql", "import from src/lib instead of the barrel file".  This is the single
#: most common way a developer states a convention -- it is the contract's own
#: example (8, row 5) and the worked example in mapping-rules.md 7 -- and
#: without it the whole shape scored as prose and produced no rule at all.
#: Anchored on an imperative verb so "it is not clear" and "that did not work"
#: cannot match.
_CONTRAST_DIRECTIVE = (
    r"\b(?:use|using|call|import|write|put|run|prefer|switch to|go with)\b"
    r"[^.!?\n]{0,60}?[,;]?\s*(?:not|rather than|instead of)\s+\S"
)

_DIRECTIVE = re.compile(
    r"\b(?:don'?t|do not|never|always|stop|avoid|make sure|ensure|instead|"
    r"no longer|should ?n[o']t|must ?n[o']t|revert|undo|"
    r"we (?:use|prefer|do|don'?t|never|always|should|need)|"
    r"you (?:should|must|need to|keep|always|never))\b"
    r"|" + _CONTRAST_DIRECTIVE,
    re.IGNORECASE,
)

#: Sentences where credentials live.  They are never rules, and belt-and-braces
#: on top of `lib.scrub`: a bare Apple team id or account number is too short
#: for any secret pattern to catch, and it has no business in a rules file.
#: `\b` is deliberately NOT used on the left: an underscore is a word
#: character, so `\bapi[ _-]?key\b` never fires on `FAL_API_KEY`, and a
#: correction reading "... using FAL_API_KEY : [REDACTED:assignment] ..." was
#: reaching the rules list on one measured repo.
_CREDENTIAL_TALK = re.compile(
    r"(?:api[ _-]?key|apikey|secret|password|passcode|token|credential|"
    r"client[ _-]?id|team[ _-]?id|account[ _-]?id|private[ _-]?key|"
    r"access[ _-]?key|bearer|otp|2fa)(?![A-Za-z])",
    re.IGNORECASE,
)

#: A rule is a sentence, not a paragraph.  Past this it is prose that happened
#: to contain "instead of".
MAX_CORRECTION_CHARS = 150

#: Clause boundaries.  A rule often rides in the middle of a sentence
#: ("continue work here, don't commit."), so the imperative test below runs per
#: clause, not on the sentence as a whole.
#: A colon between digits is a ratio or a timestamp ("9:16 reels format",
#: "2:11 pm"), not a clause boundary -- splitting there manufactured the
#: clause " always in 9", which read as an imperative and was not one.
_CLAUSE_SPLIT = re.compile(r"[,;]|(?<!\d):(?!\d)|\b(?:and|but|then|so)\b", re.IGNORECASE)

#: A clause that is genuinely aimed at the agent.  Three accepted forms:
#:   imperative      "do not commit", "never edit x", "make sure y"
#:   first person    "i don't want", "we prefer", "you must"
#:   obligation      "the first task must always be ..."
#:
#: This is what separates a rule from a sentence that merely contains a marker.
#: On the four histories measured it removed, among others:
#:   "By default when i start the mobile app ... it always starts with this
#:    state."                                   (a bug report, marker "always")
#:   "*Spam signups ...* We're getting scripted fake signups in production."
#:                                              (a pasted brief, marker "stop")
#:   "you still don't understand my question."  (frustration, marker "don't")
_IMPERATIVE_CLAUSE = re.compile(
    r"^\s*(?:please\s+|just\s+|also\s+)?"
    r"(?:do not|don'?t|never|always|stop|avoid|make sure|ensure|revert|undo|"
    r"remember|no longer|use)\b\s+\S",
    re.IGNORECASE,
)
_FIRST_PERSON_RULE = re.compile(
    r"^\s*(?:i|we|you)\s+"
    r"(?:should|shouldn'?t|must|mustn'?t|need to|have to|want|don'?t|do not|"
    r"never|always|prefer|use)\b",
    re.IGNORECASE,
)
_OBLIGATION = re.compile(
    r"\b(?:must|should)\s+(?:always|never|not|only)\b", re.IGNORECASE
)


def _is_directed_at_agent(sentence):
    """
    Does some clause of this sentence read as an instruction?

    Sentence-level testing is too blunt in both directions: "continue work
    here, don't commit." is a rule whose directive is in the second clause,
    and "why it's hard to stop" is not a rule even though "stop" is in it.
    """
    if _OBLIGATION.search(sentence):
        return True
    for clause in _CLAUSE_SPLIT.split(sentence):
        if not clause:
            continue
        if _IMPERATIVE_CLAUSE.match(clause) or _FIRST_PERSON_RULE.match(clause):
            return True
    return False


def is_rule_candidate(sentence, correction=None):
    """
    Would this sentence make sense written into a rules file?

    `correction` is the dict `textnorm.detect_correction()` returned; when it
    is flagged `directive: "no"` the marker landed in a subordinate clause, a
    proposal, or somebody else's quoted words, and the sentence is not a rule
    however well it reads.
    """
    if correction is not None and correction.get("directive") == "no":
        return False
    if not sentence or len(sentence) > MAX_CORRECTION_CHARS:
        return False
    if sentence.rstrip().endswith("?"):
        return False
    if _DOC_LINE.search(sentence):
        return False
    if _SELF_STATEMENT.search(sentence):
        return False
    if _CREDENTIAL_TALK.search(sentence):
        return False
    if not _DIRECTIVE.search(sentence):
        return False
    return _is_directed_at_agent(sentence)

#: Case sensitive on purpose: "LOG [WEBVIEW]" is Metro, "more info: ..." is a
#: person talking.
_PASTE_LINE_UPPER = re.compile(
    r"(?:^|\s)(?:LOG|WARN|WARNING|ERROR|INFO|DEBUG|TRACE|FATAL)\s*[\[:]"
    # An exception class name followed by a colon, anywhere on the line -- not
    # just at its start.  "Setup step docs failed: structured_output_invalid |
    # AI model generate | AgentRunError: The agent answer did not match its
    # contract." is pasted machine output, and it was reaching request_shapes
    # as if the developer had asked for it.
    r"|(?:^|[\s|])[A-Za-z_.]*(?:Error|Exception|Warning):\s"
    # `a | b | c` field separators: a log line, never a sentence.
    r"|\S\s+\|\s+\S[^|\n]{0,80}\|\s+\S"
)


def _is_paste_line(line):
    return bool(_PASTE_LINE_ANY.search(line) or _PASTE_LINE_UPPER.search(line))

#: A turn shorter than this once the pasted tail is removed is a bare paste.
MIN_PROSE_CHARS = 8


def prose_prefix(text):
    """
    The part of a turn the human actually typed.

    Users paste an error under a one-line complaint ("still not working" +
    600 lines of Metro output).  The complaint is the signal; the paste is
    noise that would otherwise dominate every cluster.

    Returns "" when the whole turn is machine output.  Used for request shapes
    only: a request is what the human opened with.  Corrections read the whole
    turn instead, because the strongest rules tend to sit deep inside a long
    hand-written spec.
    """
    if not text:
        return ""
    kept = []
    for line in text.split("\n"):
        if _is_paste_line(line):
            break
        kept.append(line)
    head = _WS_RE.sub(" ", " ".join(kept)).strip()
    if len(head) < MIN_PROSE_CHARS:
        return ""
    return head


_FAILURE_CUE = re.compile(
    r"\b(?:not|n[o']t|broken|fail(?:s|ed|ing)?|error|errors|wrong|issue|bug|"
    r"crash|stuck|same|still|nothing|blank|empty|missing)\b",
    re.IGNORECASE,
)

_PAIN_PATTERNS = [
    (
        "still not working",
        re.compile(
            r"\bstill\s+(?:not|no|doesn'?t|does not|isn'?t|is not|won'?t|will not|"
            r"can'?t|cannot|broken|failing|fails|the same|same)\b",
            re.IGNORECASE,
        ),
        False,
    ),
    (
        "not working",
        re.compile(
            r"\b(?:not working|doesn'?t work|does not work|didn'?t work|did not work|"
            r"isn'?t working|won'?t work|not fixed|no[t]? changed|nothing happens)\b",
            re.IGNORECASE,
        ),
        False,
    ),
    (
        "same error again",
        re.compile(r"\bsame\s+(?:error|issue|problem|thing|result|bug)\b", re.IGNORECASE),
        False,
    ),
    (
        "you keep doing that",
        re.compile(
            r"\byou\s+(?:keep\s+\w+ing|always\s+\w+|never\s+\w+|again\s+\w+ed)\b",
            re.IGNORECASE,
        ),
        False,
    ),
    (
        "i said / i told you",
        re.compile(
            r"\b(?:i (?:said|told you|already (?:said|told))|as i said|like i said|"
            r"i asked you)\b",
            re.IGNORECASE,
        ),
        False,
    ),
    (
        "revert that",
        re.compile(
            r"\b(?:revert(?:\s+(?:that|this|it|the))?|undo\s+(?:that|this|it)|"
            r"roll\s?back|take that back)\b",
            re.IGNORECASE,
        ),
        False,
    ),
    ("why did you", re.compile(r"\bwhy\s+(?:did|are|would|the hell)\s+you\b", re.IGNORECASE), False),
    (
        "again (with a failure cue)",
        re.compile(r"\bagain\b", re.IGNORECASE),
        True,  # only counts when the same turn also carries a failure cue
    ),
    # NOT HERE: an "explicit frustration" pattern (wtf / swearing / "???").  It
    # topped `pain_signals` on three of the five repos measured -- 16 hits on
    # the 81-session history, ahead of "still not working" -- and it maps to no
    # row in mapping-rules.md, because "the developer swore" does not name a
    # guardrail to build.  Every pattern that survives here names a diagnosable
    # failure the setup can actually prevent: a retry loop, a repeated
    # correction, a rollback.  Swearing is still used, as a NEGATIVE signal, by
    # `_PROFANITY` above, which keeps frustration out of `request_shapes` and
    # masks the swearing out of every quote that is emitted.
]

_URL_STRIP = re.compile(r"\b(?:https?|ftp|file)://\S+")
_PATH_CANDIDATE = re.compile(r"(?<![\w@:])(?:~/|\./)?(?:[A-Za-z0-9_@.\-]+/){1,10}[A-Za-z0-9_@.\-]+")

_CODE_EXT = frozenset(
    """
    ts tsx js jsx mjs cjs py go rs rb java kt kts swift m mm c h hpp cc cpp cs php
    sh bash zsh fish ps1 sql prisma graphql gql proto json yaml yml toml ini cfg conf
    md mdx txt css scss sass less svg html htm vue svelte astro lock env tf tfvars
    """.split()
)

#: Directory names that identify a path even without a file extension.
#: Deliberately excludes `web`, `mobile`, `ios`, `android` and other words that
#: appear in ordinary prose ("mobile/web parity" is not a path).
_CODE_DIRS = frozenset(
    """
    src app apps packages lib libs components component pages api server client
    tests test __tests__ spec migrations db database scripts docs doc config
    public static styles hooks utils services routes controllers models views
    modules features workers functions supabase prisma cmd internal pkg
    """.split()
)

_NOISE_PATH_SEGMENTS = frozenset(["node_modules", ".git", "dist", "build", ".next", "vendor"])

_TRAILING_PUNCT = ".,:;!?)]}'\"`>"


def _looks_like_path(text):
    if "/" not in text or len(text) > 200:
        return False
    segments = [s for s in text.split("/") if s]
    if len(segments) < 2:
        return False
    for segment in segments:
        if segment in _NOISE_PATH_SEGMENTS:
            return False
    last = segments[-1]
    if "." in last:
        ext = last.rsplit(".", 1)[-1].lower()
        if ext in _CODE_EXT:
            return True
    root = segments[0].lstrip("~.")
    if root.lower() in _CODE_DIRS and len(segments) >= 2:
        return True
    return False


def _strip_repo_prefix(path, prefix):
    """
    `path` with `prefix` removed at a SEGMENT boundary, or None when `path` is
    not inside `prefix`.

    The boundary check is the whole function.  A bare `startswith` turns
    "~/projects/ai-cmo-old/src/x.ts" into "-old/src/x.ts" and files it as a
    path in "~/projects/ai-cmo" -- a sibling checkout reported as this repo.
    """
    if not prefix or not path.startswith(prefix):
        return None
    rest = path[len(prefix):]
    if rest and not rest.startswith("/"):
        return None
    return rest.lstrip("/")


#: First segment of an absolute path that makes it a FILESYSTEM location
#: rather than a repo-rooted or URL-ish reference.  This distinction is the
#: whole reason the list is not simply "starts with a slash": developers type
#: "/src/app/page.tsx" and "/api/me/ws/token" constantly, and both mean
#: something inside this project.  "/Users/...", "/etc/..." and "/opt/..." do
#: not.  When in doubt the path is treated as in-repo -- dropping a real
#: hotspot to catch a rare one is the worse trade.
_FS_ROOTS = frozenset(
    """
    users home root var etc opt tmp usr private volumes mnt media srv
    applications library system windows
    """.split()
)


def _anchored_outside_repo(path):
    """
    True when the path names a location on disk that is not this repo.

    Measured: `~/Desktop/polsia/polsia-dashboard.json` arrived in
    `file_hotspots` with 2 mentions on a run against a completely different
    repo.  It is a real path and the user really was working on it -- in
    another project.  `scrub()` rewrites `/Users/<name>` to `~`, so "~" is
    where nearly every cross-project path lands; a bare "/" additionally needs
    a filesystem root segment to count, per `_FS_ROOTS`.
    """
    if path.startswith("~"):
        return True
    if not path.startswith("/"):
        return False
    segments = [segment for segment in path.split("/") if segment]
    return bool(segments) and segments[0].lower() in _FS_ROOTS


def extract_paths(clean_text, repo_prefixes):
    """
    Paths named in a user turn, split into `(in_this_repo, somewhere_else)`.

    Run on SCRUBBED text and before any path-stripping normalization, since
    `textnorm.normalize()` deletes them.

    The split is the point.  `file_hotspots` exists to tell the model which
    parts of THIS repo the user keeps pointing at, so a path anchored outside
    the repo is not weak evidence, it is a wrong answer -- and it still reads
    as a repo path, which is worse than being absent.  Tier 3 justifies nothing
    on its own (`mapping-rules.md` 0.2), so nothing was ever built on one, but
    a list labelled "file hotspots" must not contain non-files-of-this-repo.

    A RELATIVE path is taken as in-repo.  Nothing in a transcript can prove
    otherwise, and "relative to the repo" is what the field already means.
    """
    if "/" not in clean_text:
        return [], []
    body = _URL_STRIP.sub(" ", clean_text)
    in_repo = []
    external = []
    seen = set()
    for match in _PATH_CANDIDATE.finditer(body):
        # "@docs/plan.md" is Claude Code's file-reference syntax; the @ is not
        # part of the path.
        candidate = match.group(0).lstrip("@").rstrip(_TRAILING_PUNCT)
        if not _looks_like_path(candidate) or len(candidate) > 120:
            continue
        # The pattern starts at the first NAMED segment, so an absolute path
        # arrives with its leading "/" already eaten and "/etc/hosts" is
        # indistinguishable from the relative "etc/hosts".  Put it back before
        # anything decides where the path lives.
        if (
            match.start() > 0
            and body[match.start() - 1] == "/"
            and not candidate.startswith(("~/", "./", "/"))
        ):
            candidate = "/" + candidate

        path = candidate
        inside = False
        for prefix in repo_prefixes:
            stripped = _strip_repo_prefix(path, prefix)
            if stripped is not None:
                path = stripped
                inside = True
                break
        if not inside and _anchored_outside_repo(path):
            # Kept as written, anchor and all, so the caller can say WHERE.
            if candidate not in seen:
                seen.add(candidate)
                external.append(candidate)
            continue

        while path.startswith("./"):
            path = path[2:]
        # "components/workflow/" and "/lib/auth" are the same hotspots as
        # "components/workflow" and "lib/auth"; counting them separately splits
        # the evidence for no reason.
        path = path.strip("/")
        if not path or "/" not in path or len(path) > 120:
            continue
        if path not in seen:
            seen.add(path)
            in_repo.append(path)
    return in_repo, external


#: Profanity, defined once, used for two different jobs.
#:
#: JOB 1 -- REJECT.  `_is_generic()` throws away a request shape containing any
#: of these: "what fucking b1a no fucking b1a" is frustration, not a workflow,
#: and no plan can carry it as a label.  There is deliberately no profanity row
#: in `pain_signals` either (see the note at the end of `_PAIN_PATTERNS`):
#: "the developer swore" names no guardrail anyone can build.
#:
#: JOB 2 -- MASK.  Those two rules miss the case that matters most.  A
#: correction like "i don't want fucking trigger stack trace." is a REAL
#: directive: it says what to stop doing, it repeated, and it is exactly the
#: kind of row `mapping-rules.md` row 5 turns into a rule.  Dropping it would
#: throw away evidence.  But `corrections[].text` is quoted VERBATIM as an
#: evidence string in `plan.md`, in `report.md` and in the `agentic-codebase-evidence:`
#: frontmatter of a generated file -- documents the user may hand to their
#: team.  So the row survives and the wording does not.
#:
#: Masking is PRESENTATIONAL ONLY.  It runs on the way out, after clustering
#: and counting, so no count, cluster key or ranking changes because of it.
_PROFANITY = re.compile(r"\b(?:fuck\w*|shit\w*|damn|bullshit|crap|wtf|ffs)\b", re.IGNORECASE)

#: A mask, not a rewrite.  The reader can see that a word was removed and that
#: agentic-codebase removed it.  Rewriting the sentence into clean prose would change
#: what the user said while still presenting it as a quotation, which is the
#: one thing an evidence string must never do.
PROFANITY_MASK_WORD = "expletive"
PROFANITY_MASK = "[%s]" % PROFANITY_MASK_WORD

#: `textnorm.skeleton()` strips punctuation, so a mask that has already been
#: applied comes out of it as the bare word `expletive` -- which reads like
#: something the user typed.  `--redact-report` is the one path that
#: skeletonizes an already-masked string, and this puts the brackets back.
_MASK_ECHO = re.compile(r"\b%s\b" % PROFANITY_MASK_WORD)


def mask_profanity(text):
    """Swearing out, directive intact.  Run last, on text about to be emitted."""
    if not text:
        return text
    return _PROFANITY.sub(PROFANITY_MASK, text)


def _example(text):
    # Mask BEFORE truncating.  Masking afterwards would let a word the
    # 160-char limit cut in half ("...fuc…") walk straight past the pattern.
    collapsed = mask_profanity(_WS_RE.sub(" ", text or "").strip())
    if len(collapsed) > EXAMPLE_CHARS:
        return collapsed[: EXAMPLE_CHARS - 1].rstrip() + "…"
    return collapsed


def _date_only(stamp):
    if not stamp or not isinstance(stamp, str):
        return ""
    return stamp[:10]


def _safe(text):
    """Anything that ends up in `warnings` or a path field goes through here."""
    cleaned, _hits = scrub_lib.scrub(str(text))
    return cleaned


# ---------------------------------------------------------------------------
# The accumulator.  Every string that reaches it is already scrubbed.
# ---------------------------------------------------------------------------


class Signals(object):
    def __init__(self, repo_prefixes):
        self.repo_prefixes = repo_prefixes
        self.prompts = []  # [{text, session_id, timestamp}] -- intent "work"
        self.meta_prompts = []  # same shape -- intent "meta" (status questions)
        self.social_turns = 0  # intent "social" -- a count, never a list
        self.corrections_by_kind = {}  # kind -> [{text, session_id, timestamp}]
        # Paths the user named that are NOT in this repo.  Counted, never
        # emitted -- they only feed the warning in main(), because a run whose
        # mentioned paths are mostly external usually means the transcript
        # directory was matched to the wrong checkout.
        self.external_paths = {}
        self.commands = {}
        self.slash = {}
        self.services = {}
        self.paths = {}
        self.pain = {}  # label -> {"count": n, "examples": [...]}
        self.scrub_hits = []
        self.turns_total = 0
        self.turns_analyzed = 0
        self.sessions_seen = set()
        self.first_ts = ""
        self.last_ts = ""

    # -- helpers ----------------------------------------------------------
    def _bump(self, table, key, amount=1):
        if not key:
            return
        table[key] = table.get(key, 0) + amount

    def note_slash(self, name):
        if not name:
            return
        cleaned, hits = scrub_lib.scrub(name)
        self.scrub_hits.extend(hits)
        cleaned = cleaned.strip().lstrip("/")
        if not cleaned or len(cleaned) > 80:
            return
        if cleaned.split(":")[-1].lower() in _BUILTIN_SLASH:
            return
        self._bump(self.slash, cleaned)

    def note_timestamp(self, stamp):
        if not stamp:
            return
        if not self.first_ts or stamp < self.first_ts:
            self.first_ts = stamp
        if not self.last_ts or stamp > self.last_ts:
            self.last_ts = stamp

    # -- the one entry point ---------------------------------------------
    def add_turn(self, raw_text, session_id, timestamp):
        """
        SCRUB FIRST.  `raw_text` is the only unscrubbed string in this class
        and it never escapes this method.
        """
        clean, hits = scrub_lib.scrub(raw_text)
        self.scrub_hits.extend(hits)
        if not clean.strip():
            return

        # `prose` is the part the human typed, with any pasted log tail cut
        # off; `flat` is the whole turn on one line.  Shapes and corrections
        # use `prose` (a pasted stack trace is not a request); commands,
        # services, paths and pain markers use `flat`, because a pasted error
        # is exactly where those live.
        prose = prose_prefix(clean)
        flat = _WS_RE.sub(" ", clean).strip()

        self.turns_analyzed += 1
        if session_id:
            self.sessions_seen.add(session_id)
        self.note_timestamp(timestamp)

        # File hotspots: before normalization eats the paths.  Paths anchored
        # outside the repo go to a separate table and are never emitted.
        repo_paths, other_paths = extract_paths(flat, self.repo_prefixes)
        for path in repo_paths:
            self._bump(self.paths, path)
        for path in other_paths:
            self._bump(self.external_paths, path)

        # Commands the user typed or asked for.
        for command in textnorm.extract_commands(flat):
            if command.split(" ")[0] in _UNINFORMATIVE_COMMANDS:
                continue
            self._bump(self.commands, command)

        # Services / tools named.  Counted once per turn: one turn that says
        # "stripe" nine times is one piece of evidence, not nine.
        for service in textnorm.find_services(flat):
            self._bump(self.services, service.get("name"))

        # Corrections -> rule candidates.
        correction = textnorm.detect_correction(flat)
        if correction and is_rule_candidate(correction["text"], correction):
            bucket = self.corrections_by_kind.setdefault(correction["kind"], [])
            bucket.append(
                {
                    "text": correction["text"],
                    "session_id": session_id,
                    "timestamp": timestamp,
                }
            )

        # Pain markers -> guardrail gaps.
        has_failure_cue = None
        for label, regex, needs_cue in _PAIN_PATTERNS:
            found = regex.search(flat)
            if not found:
                continue
            if needs_cue:
                if has_failure_cue is None:
                    has_failure_cue = bool(_FAILURE_CUE.search(flat))
                if not has_failure_cue:
                    continue
            slot = self.pain.setdefault(label, {"count": 0, "examples": []})
            slot["count"] += 1
            if len(slot["examples"]) < 2:
                sample = _example(sentence_around(flat, found.start()))
                if sample and sample not in slot["examples"]:
                    slot["examples"].append(sample)

        # Request shapes -- split by intent BEFORE clustering.
        #
        # Ranking status questions against work requests in one list is what
        # made half of the top ten on the 81-session history non-actionable
        # ("how much time" was the 2nd most frequent shape).  Two pools mean
        # two rankings, and the status pool still keeps its counts: a
        # developer asking for progress 20 times is evidence for a status
        # skill, just not evidence of a repeated piece of WORK.
        if prose and (len(self.prompts) + len(self.meta_prompts)) < MAX_TURNS:
            intent = textnorm.classify_intent(prose)
            if intent == "social":
                self.social_turns += 1
            else:
                entry = {
                    "text": prose[:KEEP_TEXT_CHARS],
                    "session_id": session_id,
                    "timestamp": timestamp,
                }
                if intent == "meta":
                    self.meta_prompts.append(entry)
                else:
                    self.prompts.append(entry)


# ---------------------------------------------------------------------------
# Readers
# ---------------------------------------------------------------------------


def read_claude_session(path, cutoff_iso, signals, stats):
    """
    Stream one Claude Code session file.  Binary line iteration plus substring
    rejects: the 95% of bytes that are tool output never get decoded, let
    alone parsed.

    Returns `(used, last_prompts)` where `last_prompts` is
    `[(text, session_id, timestamp)]` -- the fallback source, WITH the
    timestamp each record carried, or "" when it carried none.  The timestamp
    is retained rather than dropped because `main()` has to apply rule 1 of the
    consent rule to these records too: they are collected before the window is
    known to be relevant, so the window is applied where they are consumed.
    """
    session_id = os.path.basename(path)[:-6] or os.path.basename(path)
    used = False
    last_prompts = []

    try:
        handle = open(path, "rb", buffering=1024 * 1024)
    except OSError as exc:
        stats["read_errors"] += 1
        stats["last_error"] = str(exc)
        return (False, [])

    with handle:
        for raw in handle:
            if len(raw) > MAX_LINE_BYTES:
                stats["oversize_lines"] += 1
                continue
            if not _wants(raw):
                continue
            try:
                record = json.loads(raw.decode("utf-8", "replace"))
            except (ValueError, UnicodeDecodeError):
                stats["parse_errors"] += 1
                continue
            if not isinstance(record, dict):
                continue

            kind = record.get("type")
            timestamp = record.get("timestamp") or ""

            if kind == "last-prompt":
                prompt = record.get("lastPrompt")
                if isinstance(prompt, str) and prompt.strip():
                    # Keep the timestamp.  The record is not filtered here --
                    # whether the fallback is used at all is only known once
                    # every file has been read -- so the window is enforced at
                    # the point of use, and it cannot be enforced there on a
                    # timestamp that was thrown away here.
                    last_prompts.append(
                        (prompt, record.get("sessionId") or session_id, timestamp)
                    )
                continue

            if kind != "user":
                continue
            if record.get("isMeta") or record.get("isSidechain"):
                continue
            if "toolUseResult" in record:
                continue

            message = record.get("message")
            if not isinstance(message, dict) or message.get("role") != "user":
                continue

            text = _blocks_text(message.get("content"))
            if not text:
                continue

            if not _within_window(timestamp, cutoff_iso):
                stats["out_of_window"] += 1
                continue

            stats["user_turns_total"] += 1
            clean, slash = unwrap(text)
            signals.note_slash(slash)
            if clean is None:
                continue
            signals.add_turn(clean, record.get("sessionId") or session_id, timestamp)
            used = True

    return (used, last_prompts)


# --- Codex harness wrappers ------------------------------------------------
#
# Codex's equivalent of the Claude Code system-reminder problem, and it is
# worse: MEASURED across 1,246 `response_item` user turns on a real install,
# 481 of them -- 38.6% -- were written by the harness, not by the developer.
# They are typed `role: "user"`, they are long, and they repeat verbatim in
# every session, which is exactly the profile that dominates a cluster list.
#
# Three treatments, because the wrappers are not all the same kind of thing:
#
#   DROP    the whole record is machine text ("here are some plugins you could
#           install", the repo's own AGENTS.md replayed back, a skill's
#           SKILL.md injected on invoke).  Nothing human is in it.
#   STRIP   a machine block wrapped around a real request -- remove the block,
#           keep the rest.
#   UNWRAP  a machine PREAMBLE followed by the developer's actual sentence
#           under a literal "## My request for Codex:" marker.  Dropping these
#           loses real evidence; keeping them whole makes every one of them
#           cluster on the preamble.
#
# Counts below are from that install and are what each rule is worth.

#: DROP whole.  Wrapper tag anywhere in the turn means the turn is machine text.
_CODEX_DROP_TAGS = (
    "recommended_plugins",      # 187 -- injected marketplace listing
    "system_instruction",       # 105 -- Conductor / workspace preamble
    "skill",                    #  25 -- a SKILL.md injected on invoke
    "turn_aborted",             #  17 -- "the user interrupted the previous turn"
    "subagent_notification",    #   3 -- a subagent's status report
    # Developer-role blocks.  They never reach here (role=developer is never
    # read) but cost nothing and make the list readable as the full vocabulary.
    "multi_agent_mode",
    "collaboration_mode",
    "skills_instructions",
    "apps_instructions",
    "personality_spec",
    "model_switch",
    "app-context",
)

#: STRIP the block, keep whatever else the turn says.
_CODEX_STRIP_TAGS = (
    "environment_context",      #  29 -- <cwd>/<shell>
    "in-app-browser-context",   #   9 -- ambient UI state; a request follows it
    # `<image name=[Image #1] path="/var/folders/.../codex-clipboard-....png">`
    # -- the placeholder Codex leaves where a pasted screenshot was.  The
    # sentence around it is a real request; the temp path is not part of it.
    "image",
)

_CODEX_DROP_RE = [(_pair(t), _open_ended(t)) for t in _CODEX_DROP_TAGS]
_CODEX_STRIP_RE = [(_pair(t), _open_ended(t)) for t in _CODEX_STRIP_TAGS]

#: DROP whole, markdown-headed.  A tag-only stripper misses every one of these,
#: and `# AGENTS.md instructions for ...` alone was 47 turns -- the repo's own
#: conventions file replayed as if the developer had typed it, which would have
#: turned this project's own rules into "evidence" for writing them again.
_CODEX_DROP_HEAD = re.compile(
    r"^\s*(?:"
    r"#\s*AGENTS\.md instructions for\b"
    r"|##\s*Referenced ChatGPT conversation:"
    r"|<INSTRUCTIONS>"
    r")",
    re.IGNORECASE,
)

#: A machine preamble that a real request follows.  Without the marker below
#: there is no human sentence in the turn and it is dropped.
_CODEX_PREAMBLE_HEAD = re.compile(
    r"^\s*#\s*(?:"
    r"Files mentioned by the user:"
    r"|Files pasted by the user:"
    r"|Context from my IDE setup:"
    r")",
    re.IGNORECASE,
)

#: Codex's own label for "everything after this is what the user typed".
#: MEASURED 21 occurrences of the first form and 5 of the second.
_CODEX_REQUEST_MARKER = re.compile(
    r"^\s*##\s*My request(?:\s+for\s+Codex)?\s*:\s*$", re.IGNORECASE | re.MULTILINE
)

#: Harness-authored text with no wrapper tag at all -- Codex's own internal
#: prompts, recorded as `role: "user"` because that is how they are sent.
#:
#: The title generator is the one that matters: MEASURED 8 turns on one repo,
#: which was enough to make it the SECOND most frequent request shape
#: ("respond directly user prompt not run", 8 turns across 8 sessions), the
#: single largest correction ("Do not run shell commands, apply patches, use
#: MCP servers, ..." at count 8, ahead of every rule the developer actually
#: stated), and the top pain signal.  One un-tagged internal prompt was
#: out-ranking the entire human history of the repository.
_CODEX_HARNESS_TEXT = re.compile(
    r"Respond directly to the user'?s prompt\.\s*Do not run shell commands"
    r"|You are generating a short conversation title"
    r"|The caller will discard that response and try again",
    re.IGNORECASE,
)

#: Attachment placeholders Codex substitutes for content it cannot inline.
#: Not typed by anyone; the request usually follows them.
_CODEX_PLACEHOLDER = re.compile(
    r"\[external unsupported block:[^\]\n]{0,60}\]", re.IGNORECASE
)

#: Codex's slash-command form is a markdown link to the skill's SKILL.md:
#: `[$compound-engineering:ce-plan](/abs/path/SKILL.md) then the real request`.
#: The command name is signal (it says which workflows this developer has
#: already formalized) and the text after it is the request.
_CODEX_SKILL_LINK = re.compile(r"\[\$([A-Za-z0-9_:.\-]{2,80})\]\(([^)\n]{0,400})\)")

#: Every other markdown link in a Codex turn is a file reference the UI made
#: out of something the developer dropped in.  Flattened to the path so that
#: `file_hotspots` still sees it.
_CODEX_FILE_LINK = re.compile(r"\[([^\]\n]{0,120})\]\(([^)\s\n]{1,200})\)")


#: A request that is long enough to still be a request once a pasted payload
#: has been peeled off the front of it.
_MIN_TAIL_AFTER_PASTE = 24


def _strip_leading_json(text):
    """
    Peel a pasted JSON payload off the FRONT of a turn.

    Measured on a real Codex history: a developer pastes a failed job's JSON
    ({"attempt": 3, "errorClass": "neon_create_result_uncertain", ...}) and
    then types their question under it.  `prose_prefix()` catches pasted logs
    and stack traces line by line, but a pretty-printed JSON object has none of
    the shell glyphs it keys on, so the payload survived into `request_shapes`
    and supplied a `pain_signals` example that was a machine error record
    rather than the developer's own words.

    Returns the remaining text, or "" when the whole turn was the payload.
    """
    head = (text or "").lstrip()
    if not head or head[0] not in "{[":
        return text
    try:
        _value, end = json.JSONDecoder().raw_decode(head)
    except (ValueError, RecursionError):
        return text
    tail = head[end:].strip()
    if len(tail) < _MIN_TAIL_AFTER_PASTE:
        return ""
    return tail


def unwrap_codex(text):
    """
    Strip Codex's harness wrappers, then hand the remainder to `unwrap()`.

    Returns `(clean_or_None, slash_command_or_None)`, the same contract the
    Claude Code path uses, so everything downstream -- scrubbing, clustering,
    the count>=2 discipline, the caps -- is literally the same code.

    Codex-only on purpose.  `unwrap()` is shared and its behaviour on Claude
    Code transcripts must not move; this is the one place the two formats
    differ, and it is a prefix to the shared function rather than a fork of it.
    """
    if not text:
        return (None, None)

    if _CODEX_DROP_HEAD.match(text) or _CODEX_HARNESS_TEXT.search(text):
        return (None, None)
    for pair_re, open_re in _CODEX_DROP_RE:
        if pair_re.search(text) or open_re.search(text):
            return (None, None)

    text = _CODEX_PLACEHOLDER.sub(" ", text)
    for pair_re, open_re in _CODEX_STRIP_RE:
        text = pair_re.sub(" ", text)
        text = open_re.sub(" ", text)

    # "## My request for Codex:" -- everything before it is a file manifest or
    # an IDE tab list, everything after it is the developer talking.
    # The FIRST marker, not the last: the preamble always sits above it, and
    # cutting at a later one would eat text the developer wrote.
    marker = _CODEX_REQUEST_MARKER.search(text)
    if marker is not None:
        text = text[marker.end():]
    elif _CODEX_PREAMBLE_HEAD.match(text):
        # A manifest with no request under it: pure machine text.
        return (None, None)

    slash = None
    found = _CODEX_SKILL_LINK.search(text)
    if found:
        slash = found.group(1)
        text = _CODEX_SKILL_LINK.sub(" ", text)

    # `[first-phase.md](docs/plans/first-phase.md)` -> `docs/plans/first-phase.md`
    text = _CODEX_FILE_LINK.sub(lambda m: " " + (m.group(2) or m.group(1) or "") + " ", text)

    text = _strip_leading_json(text).strip()
    if not text:
        return (None, slash)

    clean, inner_slash = unwrap(text)
    return (clean, inner_slash or slash)


def _turn_key(text):
    """
    Identity of one user turn's TEXT, for recognising the SAME turn arriving
    twice -- in two record shapes, or re-serialized by a fork.

    Whitespace- and case-insensitive over the COMPLETE text, hashed so a 2 MB
    turn costs 40 bytes in the accumulator and no raw prose is retained.

    It was a 400-character PREFIX, and a prefix is not an identity.  Two
    different long requests that open the same way -- "refactor the pricing
    module ... then rename X" and "refactor the pricing module ... then delete
    Y" -- reduced to one key, and one of the two was erased.

    A key ALONE de-duplicates nothing.  Only `(key, ordinal)` does, where the
    ordinal is the occurrence number within its record stream: three identical
    requests typed on three different days are three pieces of evidence, and
    collapsing them is how `npm test` fell out of `commands_requested` entirely
    on a repo whose developer asked for it every morning.  See
    `read_codex_session()`.
    """
    normalized = _WS_RE.sub(" ", (text or "")).strip().lower()
    if not normalized:
        return ""
    return hashlib.sha1(normalized.encode("utf-8", "replace")).hexdigest()


def read_codex_session(path, cutoff_iso, signals, stats, inherited=None, own=None, fork_time=None):
    """
    Stream one Codex rollout.

    A human turn appears in TWO record shapes and `response_item` is the one
    that lasts:

      response_item / message / role=user   1,246 records measured
      event_msg    / user_message             919 records measured, 99% of
                                              which are byte-identical copies
                                              of a response_item turn

    The newest sessions on the verification machine carry
    `session_meta.history_mode: "paginated"` and emit ZERO `event_msg` user
    records -- Codex is migrating the format, and a miner that prefers
    `event_msg` reads nothing at all on a new session.  So `response_item` is
    primary, `event_msg` fills gaps, and the two are merged so the 99% overlap
    is not counted twice.

    DE-DUPLICATION IS ONE-FOR-ONE, NEVER ACROSS OCCURRENCES.  Both overlaps
    this function removes are duplicate REPRESENTATIONS of a turn, so both are
    removed by matching representations pairwise and nothing else:

      cross-stream  complete-text matches pair only at nearby timestamps;
                    undated records additionally require adjacent positions.
                    Gaps and later repeated requests remain separate turns.
      fork prefix   a fork COPIES its parent's leading turns, in order, so the
                    copies are the child's turns 0..k-1 matching the parent's
                    turns 0..k-1.  Matching is positional and stops at the
                    first divergence: past the fork point the two threads are
                    separate work, and a request the child repeats there counts
                    again even though the parent said it too.

    Identity is `(_turn_key(text), ordinal)` -- complete text plus occurrence
    number within its stream -- never text alone.  Three identical requests at
    three timestamps are three turns; that repetition IS the evidence this
    whole report exists to count.

    NEVER read: `role: "developer"` (766 records, 100% harness), `compacted`
    (its `replacement_history` re-serializes earlier turns and would
    double-count them), `turn_context` (config echo), or any `agent_message`.

    `inherited` is the ORDERED list of turn identities in the thread this
    rollout was FORKED FROM; `own` is the list this rollout appends its own
    identities to, in read order, so its own forks can be matched against it.
    Order is the whole point -- a set would lose the position a fork prefix is
    recognised by.  See `codex_read_order()` for why the caller reads ancestors
    first.
    """
    session_id = os.path.basename(path)
    if session_id.endswith(".jsonl"):
        session_id = session_id[:-6]

    primary = []
    secondary = []

    try:
        handle = open(path, "rb", buffering=1024 * 1024)
    except OSError as exc:
        stats["read_errors"] += 1
        stats["last_error"] = str(exc)
        return False

    with handle:
        for position, raw in enumerate(handle):
            if len(raw) > MAX_LINE_BYTES:
                # A single line here reached 25 MB on the measured corpus: a
                # base64 image part, never a request.
                stats["oversize_lines"] += 1
                continue
            if b'"user_message"' not in raw and b'"user"' not in raw:
                continue
            try:
                record = json.loads(raw.decode("utf-8", "replace"))
            except (ValueError, UnicodeDecodeError):
                stats["parse_errors"] += 1
                continue
            if not isinstance(record, dict):
                continue
            payload = record.get("payload")
            if not isinstance(payload, dict):
                continue
            timestamp = record.get("timestamp") or ""
            kind = record.get("type")
            payload_type = payload.get("type")

            if kind == "response_item" and payload_type == "message":
                if payload.get("role") != "user":
                    continue
                parts = []
                for block in payload.get("content") or []:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") not in ("input_text", "text", "output_text"):
                        continue
                    value = block.get("text")
                    if isinstance(value, str):
                        parts.append(value)
                if parts:
                    primary.append(("\n".join(parts), timestamp, position))
            elif kind == "event_msg" and payload_type == "user_message":
                value = payload.get("message")
                if isinstance(value, str) and value.strip():
                    secondary.append((value, timestamp, position))

    # Pair only nearby representations of the same occurrence, never matching
    # text from different days merely because its ordinal happens to agree.
    merged = []
    candidates = {}
    for text, timestamp, position in primary:
        key = _turn_key(text)
        if not key:
            continue
        merged.append((timestamp or "", position, text, key))
        candidates.setdefault(key, []).append((timestamp, position))
    for text, timestamp, position in secondary:
        key = _turn_key(text)
        if not key:
            continue
        paired = None
        for candidate in candidates.get(key, []):
            moment, other = _record_time(timestamp), _record_time(candidate[0])
            nearby = abs(position - candidate[1]) <= 2
            same_time = moment is not None and other is not None and abs((moment-other).total_seconds()) <= 2
            if same_time or (nearby and not timestamp and not candidate[0]):
                paired = candidate
                break
        if paired is not None:
            candidates[key].remove(paired)
            continue
        merged.append((timestamp or "", position, text, key))
    merged.sort(key=lambda row: row[1])
    boundary = _record_time(fork_time)
    if boundary is None and merged:
        boundary = _record_time(merged[0][0])
    occurrences = {}

    used = False
    # `diverged` turns the fork comparison off for good at the first turn that
    # does not match the parent's, so only a genuine COPIED PREFIX is
    # suppressed.  With no parent there is nothing to compare against.
    diverged = not inherited
    for index, row in enumerate(merged):
        timestamp, _order, text, key = row
        ordinal = occurrences.get(key, 0)
        occurrences[key] = ordinal + 1
        identity = (key, ordinal)
        # Recorded before any filter: a fork inherits its parent's whole turn
        # sequence, including turns this run's consent window excluded.
        if own is not None:
            own.append((key, ordinal, timestamp))
        fork_copy = False
        if not diverged:
            parent_turn = inherited[index] if index < len(inherited) else None
            parent_time = _record_time(parent_turn[2]) if parent_turn and len(parent_turn) > 2 else None
            if (parent_turn and parent_turn[:2] == identity and boundary is not None
                    and parent_time is not None and parent_time <= boundary):
                fork_copy = True
            else:
                diverged = True
        if not _within_window(timestamp, cutoff_iso):
            stats["out_of_window"] += 1
            continue
        if fork_copy:
            stats["fork_duplicates"] += 1
            continue
        stats["user_turns_total"] += 1
        clean, slash = unwrap_codex(text)
        signals.note_slash(slash)
        if clean is None:
            continue
        signals.add_turn(clean, session_id, timestamp)
        used = True

    return used


# ---------------------------------------------------------------------------
# Shaping the report
# ---------------------------------------------------------------------------

#: Skeletons that are pure conversational glue.  They cluster enormously and
#: map to no artifact, so they would crowd out the real evidence.
_GENERIC_SHAPES = frozenset(
    [
        "go ahead",
        "carry on",
        "keep going",
        "continue please",
        "do it",
        "do that",
        "make it",
        "fix it",
        "fix this",
        "try again",
        "run it",
        "show me",
        "tell me",
        "look at",
        "read it",
        "check it",
        "sounds good",
        "thank you",
        "not sure",
        "what about",
        "why not",
        "yes please",
    ]
)

#: Session housekeeping, not work.  A shape made only of these maps to nothing.
_META_TOKENS = frozenset(
    """
    opus sonnet haiku gpt claude codex model models 1m 200k mode think ultrathink
    plan planning compact clear resume continue context window token tokens
    yes yep no nope ok okay sure thanks done next stop wait hmm
    """.split()
)

_INTERROGATIVE = frozenset(["how", "what", "why", "when", "where", "which", "who", "whats"])

#: Turn-taking glue.  Shorter skeletons made these cluster hard -- "confirm and
#: start working" reached count 5 across 5 sessions on one repo -- and a
#: cluster made only of these maps to no artifact at all.
_GLUE_TOKENS = frozenset(
    """
    continue carry on proceed resume go ahead start started begin working work
    confirm confirmed confirms approve approved agreed accept accepted
    ok okay fine cool great perfect nice good alright sure yes yeah yep no nope
    understood noted done finish finished complete completed ready
    please thanks thank sorry
    """.split()
)

#: A request *shape* is short by nature ("commit staged changes", "add api
#: endpoint with validation").  Past this length the skeleton is describing one
#: specific task that happened to be pasted twice, not a recurring workflow.
MAX_SHAPE_TOKENS = 8

#: Uninformative shell verbs.  `open`, `cd`, `ls` are navigation, not a build
#: or test command anyone would wrap in a hook.
_UNINFORMATIVE_COMMANDS = frozenset(
    """
    cd ls cat echo open pwd clear exit which man less more head tail cp mv rm
    touch mkdir chmod chown sudo export source code vim nano nvim emacs sleep
    """.split()
)


#: An opaque identifier is not a request shape.  With the status questions
#: moved out, a Google OAuth client id surfaced into the top 20 as
#: "n1np0vgv8ntcada63cf00redied8n7cp apps googleusercontent com ios google" --
#: a label no plan can use, carrying a value nobody wants echoed back.  A token
#: that mixes letters and digits past 12 characters, or runs past 24, is an id
#: or a hash; English words are neither.
_OPAQUE_TOKEN = re.compile(r"^(?=.*[a-z])(?=.*[0-9])[a-z0-9]{12,}$|^[a-z0-9]{24,}$")


def _is_generic(shape):
    """
    Reject shapes that cluster well but map to no artifact: conversational
    glue, session housekeeping, opaque identifiers, and profanity.  Precision
    matters more than recall here -- the top of this list is the whole product
    in the first thirty seconds.

    Status questions no longer reach this function: `textnorm.classify_intent()`
    routes them to `meta_queries` before clustering, so "how much time" is
    separated (and still counted) rather than judged here.  The short-question
    gate in `build_request_shapes()` stays as a backstop for anything the
    classifier misses.
    """
    if not shape:
        return True
    parts = shape.split(" ")
    if len(parts) < 2 or len(parts) > MAX_SHAPE_TOKENS:
        return True
    if shape in _GENERIC_SHAPES:
        return True
    if all(token in _META_TOKENS for token in parts):
        return True
    if all(token in _GLUE_TOKENS for token in parts):
        return True
    if _PROFANITY.search(shape):
        return True
    for token in parts:
        if _OPAQUE_TOKEN.match(token):
            return True
    return False


def _prefer_repeated(rows, count_key):
    """
    Keep only the entries seen more than once.  Always -- there is no
    "not enough repeated rows, show the singletons instead" fallback.

    There used to be one, and the dogfood run showed exactly what it costs:
    `corrections`, `tool_mentions` and `slash_commands` all shipped count-1
    rows sitting in the same ranked list as a count-15 one, with nothing in
    the JSON to say the first is anecdote and the second is evidence.
    CLAUDE.md's evidence invariant is that a finding with no evidence count
    maps to nothing, so a singleton can only mislead the phase that reads it.
    Returning three honest rows -- or none -- is the correct outcome.
    """
    return [row for row in rows if row.get(count_key, 0) >= 2]


def build_request_shapes(signals, top):
    # 0.5 on the 3-token merge key = two of three tokens in common, with the
    # low-information guard in textnorm stopping "fix auth bug" and "fix layout
    # bug" from collapsing.  At 0.6 (two of three shared but nothing else
    # allowed to differ) one measured repo reported a single request shape from
    # 130 user turns.
    clusters = textnorm.cluster(
        signals.prompts, min_count=2, jaccard_threshold=0.5, max_examples=2
    )
    out = []
    for entry in clusters:
        shape = entry.get("skeleton") or ""
        if _is_generic(shape):
            continue
        # A turn that recites credentials is never a request worth automating,
        # and it is the last place a leaked value could still be hiding.
        if _CREDENTIAL_TALK.search(shape):
            continue
        sessions = entry.get("sessions", 0)
        count = entry.get("count", 0)
        # Repetition inside one session is a retry loop; repetition ACROSS
        # sessions is a workflow.  Only the second kind earns a skill.
        if sessions < 2 and count < 4:
            continue
        # A two- or three-word question ("how much time", "what remaining")
        # is a status ping.  Across three or more sessions that is a real
        # workflow gap; below that it is small talk.
        if shape.split(" ")[0] in _INTERROGATIVE and len(shape.split(" ")) <= 3 and sessions < 3:
            continue
        out.append(
            {
                "id": entry.get("id", ""),
                "skeleton": shape,
                "count": entry.get("count", 0),
                "sessions": entry.get("sessions", 0),
                "first_seen": _date_only(entry.get("first_seen")),
                "last_seen": _date_only(entry.get("last_seen")),
                "examples": [_example(x) for x in (entry.get("examples") or [])][:2],
            }
        )
        if len(out) >= top:
            break
    return out


def _containment_merge(rows):
    """
    Fold a correction into the longer one that contains it.

    "don't commit", "do not commit and push" and "Do not commit, stage, push
    or change branch without asking me first" are one rule stated three times,
    but Jaccard keeps them apart because the long form dilutes the overlap.
    Subset-of-tokens plus an identical head verb is a safe, cheap merge: it
    joins "use bun" to "use bun not npm" without joining "use bun" to
    "add a bun script for tests".
    """
    ordered = sorted(rows, key=lambda r: (-r["count"], -len(r["_tokens"]), r["text"]))
    kept = []
    for row in ordered:
        target = None
        for candidate in kept:
            if (
                row["_tokens"]
                and row["_tokens"] <= candidate["_tokens"]
                and row["_head"] == candidate["_head"]
            ):
                target = candidate
                break
        if target is None:
            kept.append(row)
            continue
        target["count"] += row["count"]
        for example in row["_examples"]:
            if example not in target["_examples"] and len(target["_examples"]) < 3:
                target["_examples"].append(example)
    return kept


def build_corrections(signals, top):
    """
    A correction the user made twice is a rule candidate, so the whole job
    here is to stop the same rule from being counted as three different ones.

    Clustering runs across all kinds at once (a "don't commit" turn lands in
    `process` or `architecture` depending on the other words in it, and
    splitting on that would split the count); the kind is then decided by
    majority vote over the skeletons that were merged.
    """
    items = []
    kind_votes = {}  # skeleton -> {kind: n}
    for kind, bucket in signals.corrections_by_kind.items():
        for item in bucket:
            shape = textnorm.skeleton(item["text"])
            if not shape:
                continue
            votes = kind_votes.setdefault(shape, {})
            votes[kind] = votes.get(kind, 0) + 1
            items.append(item)
    if not items:
        return []

    clusters = textnorm.cluster(items, min_count=1, jaccard_threshold=0.55, max_examples=3)

    rows = []
    for entry in clusters:
        examples = [_example(x) for x in (entry.get("examples") or []) if x]
        if not examples:
            continue
        shapes = [entry.get("skeleton") or ""] + list(entry.get("variants") or [])
        tally = {}
        for shape in shapes:
            for kind, count in (kind_votes.get(shape) or {}).items():
                tally[kind] = tally.get(kind, 0) + count
        kind = "process"
        if tally:
            kind = sorted(tally.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        rows.append(
            {
                # Verbatim, because a rule is written from the words the user
                # actually used, not from a skeleton.
                "text": examples[0],
                "kind": kind,
                "count": entry.get("count", 0),
                "_examples": examples[1:],
                "_tokens": set((entry.get("skeleton") or "").split(" ")) - set([""]),
                "_head": (entry.get("skeleton") or " ").split(" ")[0],
            }
        )

    rows = _containment_merge(rows)
    rows.sort(key=lambda row: (-row["count"], row["kind"], row["text"]))
    rows = _prefer_repeated(rows, "count")[:top]
    return [
        {
            "text": row["text"],
            "kind": row["kind"],
            "count": row["count"],
            "examples": row["_examples"][:2],
        }
        for row in rows
    ]


def build_meta_queries(signals, top=TOP_META):
    """
    The status questions, merged by TOPIC rather than by wording.

    Wording-based clustering is what produced the defect: "how much time" (8),
    "what remaining" (5), "how many remaining" (4) and "anything remains" (3)
    are one developer asking one question, and they arrived as four separate
    rows crowding four real request shapes out of the top ten.  Grouping on
    `textnorm.meta_topic()` collapses them into one counted row, which is both
    smaller and truer: the evidence is "asks for progress 20 times", not
    "asked it this way 5 times".

    The row is labelled with the most frequent real skeleton in the group, so
    it still reads as something the developer typed, and examples prefer that
    skeleton so the quote matches the label.
    """
    groups = {}
    for item in signals.meta_prompts:
        text = item.get("text") or ""
        topic = textnorm.meta_topic(text) or "status"
        shape = textnorm.skeleton(text)
        group = groups.setdefault(
            topic, {"count": 0, "sessions": set(), "labels": {}, "entries": []}
        )
        group["count"] += 1
        session_id = item.get("session_id")
        if session_id:
            group["sessions"].add(str(session_id))
        if shape:
            group["labels"][shape] = group["labels"].get(shape, 0) + 1
        group["entries"].append((shape, text))

    rows = []
    for topic, group in groups.items():
        if group["count"] < 2:
            # Same evidence bar as every other list: one status ping is not a
            # habit worth naming in a plan.
            continue
        # Label with the developer's own words when one phrasing actually
        # dominates the group, and with the canonical gloss when it does not.
        # A merged group of eight ways of asking "what next?" was labelled
        # "tell what working search side native" -- one member's skeleton,
        # true of that turn and misleading about the other seven, and it read
        # like a feature request sitting in the status list.
        label = textnorm.META_TOPIC_LABELS.get(topic, topic)
        if group["labels"]:
            best, hits = sorted(
                group["labels"].items(), key=lambda kv: (-kv[1], len(kv[0]), kv[0])
            )[0]
            if hits * 2 >= group["count"]:
                label = best
        # The label is the developer's own skeleton when one phrasing wins, so
        # it is user text and gets the same treatment as every other quote.
        label = mask_profanity(label)
        examples = []
        for shape, text in sorted(
            group["entries"], key=lambda pair: 0 if pair[0] == label else 1
        ):
            sample = _example(text)
            if sample and sample not in examples:
                examples.append(sample)
            if len(examples) >= 2:
                break
        rows.append(
            {
                "skeleton": label,
                "count": group["count"],
                "sessions": len(group["sessions"]),
                "examples": examples,
            }
        )

    rows.sort(key=lambda row: (-row["count"], row["skeleton"]))
    return rows[:top]


def build_pain(signals, top):
    rows = [
        {"pattern": label, "count": data["count"], "examples": data["examples"][:2]}
        for label, data in signals.pain.items()
    ]
    rows.sort(key=lambda row: (-row["count"], row["pattern"]))
    # Same evidence bar as every other list: one "you keep doing that" is a bad
    # afternoon, not a guardrail gap.  Two repos measured shipped a count-1
    # pain row directly above a count-3 one with nothing to tell them apart.
    return _prefer_repeated(rows, "count")[:top]


#: Extensions and directory names that make a path documentation rather than
#: code.  On all three large repos measured, `file_hotspots` was dominated by
#: `docs/plans/*.md` -- the top entry on the 81-session history was a plan
#: document with 10 mentions, ahead of every source directory -- which reads
#: as "this code changes constantly" and means nothing of the kind.
_DOC_EXT = frozenset("md mdx markdown rst adoc asciidoc txt".split())
_DOC_DIRS = frozenset(
    """
    docs doc documentation plans plan specs spec adr adrs rfc rfcs notes wiki
    handbook runbook runbooks proposals design designs
    """.split()
)


def is_doc_path(path):
    """True for documentation: any `.md`-family file, or anything under docs/."""
    if not path:
        return False
    segments = [segment for segment in path.split("/") if segment]
    if not segments:
        return False
    last = segments[-1]
    if "." in last and last.rsplit(".", 1)[-1].lower() in _DOC_EXT:
        return True
    for segment in segments[:-1]:
        if segment.lower() in _DOC_DIRS:
            return True
    return False


def split_hotspots(table):
    """`{path: mentions}` -> `(code_table, doc_table)`."""
    code = {}
    docs = {}
    for path, mentions in table.items():
        if is_doc_path(path):
            docs[path] = mentions
        else:
            code[path] = mentions
    return code, docs


def _counted(table, key_name, count_name, top):
    rows = [{key_name: key, count_name: value} for key, value in table.items()]
    rows.sort(key=lambda row: (-row[count_name], row[key_name]))
    return _prefer_repeated(rows, count_name)[:top]


def history_bucket(session_count):
    if session_count <= 0:
        return "none"
    if session_count < 20:
        return "thin"
    if session_count <= 100:
        return "medium"
    return "rich"


def apply_redaction(report):
    """
    `--redact-report`: keep every count, drop every verbatim quote.

    For the extra-cautious run.  Shapes, kinds and counts survive -- they are
    what phase 3 reasons over -- but nothing the developer literally typed
    reaches stdout, including the correction sentences, which are normalized
    down to their skeletons.
    """
    for shape in report.get("request_shapes") or []:
        shape["examples"] = []
    for query in report.get("meta_queries") or []:
        query["examples"] = []
    for correction in report.get("corrections") or []:
        correction["examples"] = []
        shape = mask_profanity(textnorm.skeleton(correction.get("text") or ""))
        correction["text"] = _MASK_ECHO.sub(PROFANITY_MASK, shape)
    for pain in report.get("pain_signals") or []:
        pain["examples"] = []
    return report


def fit_to_cap(report, cap, warnings, order=TRIM_KEYS, floor=MIN_ROWS_KEPT):
    """
    Bring the report under `cap` characters by dropping rows in `order` --
    least load-bearing first -- instead of round-robin across every list.

    `lib.emit.emit()` trims fairly, one entry per list in rotation, which is
    right when it cannot know what the lists mean.  Here we do know: a
    `doc_hotspots` tail row costs the plan nothing and a `request_shapes` row
    is the plan.  The dogfood run dropped a request shape while
    `tool_mentions` still carried seven rows, so `--top 20` quietly meant 19.

    Walks `order` front to back, emptying each list down to `floor` before
    moving on, and only reaches the last entry (`request_shapes`) when every
    other list is already at the floor.  emit() stays wired up behind this as
    the backstop, and records its own warning if it ever has to fire.
    """
    if not cap or cap <= 0:
        return 0
    if len(emit_lib.serialize(report)) <= cap:
        return 0

    # The warning this function appends, and the `output_chars` digits emit()
    # stamps afterwards, both cost characters -- so trim to a budget under the
    # cap rather than to the cap itself, or the fix puts the object back over.
    budget = cap - _CAP_RESERVE
    if budget < 1:
        budget = cap

    dropped = {}
    total = 0
    for pass_floor in (floor, 0):
        for key in order:
            rows = report.get(key)
            if not isinstance(rows, list):
                continue
            while len(rows) > pass_floor:
                if len(emit_lib.serialize(report)) <= budget:
                    break
                rows.pop()
                dropped[key] = dropped.get(key, 0) + 1
                total += 1
            if len(emit_lib.serialize(report)) <= budget:
                break
        if len(emit_lib.serialize(report)) <= budget:
            break

    if total:
        detail = ", ".join(
            "%s: %d" % (key, dropped[key]) for key in order if key in dropped
        )
        emit_lib.warn(
            warnings,
            "output trimmed to fit %d chars: dropped %d low-value row(s) (%s); "
            "least load-bearing lists first, request_shapes last"
            % (cap, total, detail),
        )
    return total


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def _mtime_iso(mtime):
    """File mtime as a naive-UTC ISO day-and-time string, or ""."""
    try:
        moment = datetime.datetime.fromtimestamp(
            float(mtime), datetime.timezone.utc
        ).replace(tzinfo=None)
    except (TypeError, ValueError, OSError, OverflowError):
        return ""
    return moment.strftime("%Y-%m-%dT%H:%M:%S")


def _resolve_only_report(target, transcript_root, match_mode, rows, warnings, elapsed_ms):
    """
    The `--resolve-only` payload: where the transcripts are, how many there are,
    and how far back they go -- computed from directory entries and file
    metadata alone, so no conversation has been read.

    On Claude Code that is literally "directory entries and stat", because the
    project directory name IS the repo association.  On Codex there is no
    per-project directory, so one metadata record per file -- the leading
    `session_meta`, carrying cwd, git remote and thread kind -- has to be read
    to know which rollouts belong to this repo.  That is stated in the warning
    rather than glossed, because the whole point of this mode is to tell the
    user exactly what was touched before they consent to a full read.

    `sessions.count` here is the *file* count, an upper bound on the session
    count a full run reports (a full run counts only sessions that yielded a
    usable user turn).  `history_bucket` is therefore also an upper bound and
    phase 4 must recompute it from the real mining output.
    """
    mtimes = [row[1] for row in rows]
    total_bytes = sum(int(row[2] or 0) for row in rows)
    if rows:
        read_note = (
            "reading only the leading session_meta record of each rollout (cwd, "
            "git remote, thread kind) and no conversation"
            if target == "codex"
            else "without reading any of their content"
        )
        emit_lib.warn(
            warnings,
            "--resolve-only: located %d session file(s) (%s) %s; counts are file "
            "counts, not analyzed-session counts"
            % (len(rows), _human_bytes(total_bytes), read_note),
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "tool": TOOL,
        "target": target,
        "mode": "resolve-only",
        "transcript_root": _safe(transcript_root) if transcript_root else "",
        "match_mode": match_mode,
        "sessions": {
            "files": len(rows),
            "count": len(rows),
            "first": _mtime_iso(min(mtimes)) if mtimes else "",
            "last": _mtime_iso(max(mtimes)) if mtimes else "",
            "bytes_total": total_bytes,
        },
        "history_bucket": history_bucket(len(rows)),
        "warnings": warnings,
        "timing_ms": elapsed_ms,
    }


def build_parser():
    parser = emit_lib.base_parser(
        TOOL,
        "Mine local agent transcripts for this repo into a counted, scrubbed "
        "evidence report (user turns only, secrets removed before anything is "
        "written).",
    )
    parser.add_argument(
        "--target",
        choices=["claude-code", "codex"],
        default="claude-code",
        help="which agent's session files to read (default: claude-code)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        metavar="N",
        help="only read sessions from the last N days (consent scope)",
    )
    parser.add_argument(
        "--max-sessions",
        type=int,
        default=None,
        dest="max_sessions",
        metavar="N",
        help="read at most N session files, newest first",
    )
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=DEFAULT_MAX_BYTES,
        dest="max_bytes",
        metavar="N",
        help="total transcript bytes to read before stopping (default: 400 MB)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=20,
        metavar="N",
        help="max request shapes to report (default: 20; output cap may trim further)",
    )
    parser.add_argument(
        "--redact-report",
        action="store_true",
        default=False,
        dest="redact_report",
        help="drop every verbatim example from the output, keeping only shapes and counts",
    )
    parser.add_argument(
        "--resolve-only",
        action="store_true",
        default=False,
        dest="resolve_only",
        help=(
            "locate the transcript directory and report it, the session-file count "
            "and the date range, then exit WITHOUT parsing a single turn. Used by "
            "phase 0 to name the directory in the consent prompt before consent is "
            "given, so the user sees what would be read and how much of it."
        ),
    )
    return parser


def main(argv=None):
    timer = emit_lib.Timer()
    timer.__enter__()

    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "selftest", False):
        return selftest()

    repo = emit_lib.resolve_repo(args.repo)
    warnings = []

    # A missing repo directory is degraded, not fatal: transcripts outlive the
    # checkout (renamed, moved, deleted worktree) and the path string is all
    # the transcript lookup needs.  Phase 0 has already validated the repo for
    # the rest of the pipeline.
    if not os.path.isdir(repo):
        emit_lib.warn(
            warnings,
            "repo path does not exist on disk (%s); mining transcripts recorded "
            "against that path anyway" % _safe(repo),
        )

    home = os.path.expanduser("~")
    top = max(1, int(args.top or 20))

    # Prefixes used to make file paths repo-relative.  The scrubbed form is
    # what actually appears in mined text, since scrub() collapses /Users/<me>.
    repo_prefixes = [repo, _safe(repo)]
    seen_prefix = set()
    repo_prefixes = [p for p in repo_prefixes if p and not (p in seen_prefix or seen_prefix.add(p))]

    signals = Signals(repo_prefixes)
    stats = {
        "user_turns_total": 0,
        "parse_errors": 0,
        "read_errors": 0,
        "oversize_lines": 0,
        "out_of_window": 0,
        "fork_duplicates": 0,
        "last_error": "",
    }

    cutoff_iso = _iso_cutoff(args.days)
    transcript_root = None
    match_mode = "none"
    codex_metas = {}

    if args.target == "codex":
        roots, transcript_root = locate_codex_roots(home, warnings)
        # --days prunes whole date directories here, before a single file is
        # opened; select_sessions() applies it again per file on mtime.
        # --resolve-only reports the FULL directory (see below), so it must not
        # prune by the window it is about to ask the user about.
        rows = list_codex_session_files(
            roots, None if args.resolve_only else args.days, warnings
        )
        found = len(rows)
        repo_url = repo_git_url(repo)
        rows, codex_metas = match_codex_sessions(rows, repo, repo_url, warnings)
        if rows:
            match_mode = "cwd+git" if repo_url else "cwd"
        if args.debug:
            # The remote goes through diagnostic_git_url(): stderr is not
            # covered by the scrubber and a remote can carry a password.
            emit_lib.eprint(
                "codex: %d rollout(s) on disk, %d for this repo (origin=%s)"
                % (found, len(rows), diagnostic_git_url(repo_url))
            )
    else:
        transcript_root, match_mode = locate_claude_root(repo, home, warnings)
        rows = list_session_files(transcript_root, recursive=False)

    if transcript_root and not rows:
        emit_lib.warn(
            warnings,
            "transcript directory exists but holds no session files; the repo "
            "has agent history recorded elsewhere or none at all",
        )

    # --resolve-only stops here, before a single turn is parsed.  Everything
    # above this line is the locate phase: directory resolution, and for Codex
    # the session_meta match that scopes the shared tree to this repo -- one
    # metadata record per file (cwd, git remote, thread kind), never a line of
    # conversation.  No user turn, no assistant turn, no tool output has been
    # read, which is what lets phase 0 state the real volume before it asks for
    # consent to read any of it.
    if args.resolve_only:
        # The consent window is not known yet -- that is the question being
        # asked -- so resolve-only counts every file and says so rather than
        # silently reporting a windowed number as the whole volume.
        if args.days or args.max_sessions:
            emit_lib.warn(
                warnings,
                "--resolve-only ignores --days/--max-sessions: it reports the full "
                "directory so the consent question can state the real volume",
            )
        timer.__exit__(None, None, None)
        emit_lib.emit(
            _resolve_only_report(
                args.target, transcript_root, match_mode, rows, warnings, timer.elapsed_ms()
            ),
            cap_chars=args.cap_chars if args.cap_chars else CAP_CHARS,
        )
        return 0

    selected = select_sessions(rows, args.days, args.max_sessions, args.max_bytes, warnings)

    bytes_read = 0
    fallback_prompts = []
    sizes = dict((row[0], row[2]) for row in selected)

    if args.target == "codex":
        # Ancestors before their forks, so a copied turn can be recognised as
        # one; see codex_read_order().
        # ORDERED lists, not sets: a fork is recognised by its copied PREFIX,
        # which is a statement about position as well as content.
        keys_by_thread = {}
        for path in codex_read_order(selected, codex_metas):
            meta = codex_metas.get(path) or {}
            thread_id = str(meta.get("id") or meta.get("session_id") or path)
            parent = meta.get("forked_from_id")
            inherited = keys_by_thread.get(str(parent)) if parent else None
            own = []
            used = read_codex_session(path, cutoff_iso, signals, stats, inherited, own, meta.get("timestamp"))
            keys_by_thread[thread_id] = own
            size = sizes.get(path, 0)
            bytes_read += size
            if args.debug:
                emit_lib.eprint(
                    "read %s (%d bytes, used=%s)" % (os.path.basename(path), size, used)
                )
    else:
        for path, _mtime, size in selected:
            used, last_prompts = read_claude_session(path, cutoff_iso, signals, stats)
            fallback_prompts.extend(last_prompts)
            bytes_read += size
            if args.debug:
                emit_lib.eprint(
                    "read %s (%d bytes, used=%s)" % (os.path.basename(path), size, used)
                )

    # `last-prompt` records are a cheap fallback source: truncated, sometimes
    # undated, but present even when the user records are unusable.
    #
    # RULE 1 APPLIES TO THEM TOO.  A `last-prompt` record lives in whatever file
    # the session last wrote, so under `--days 7` a file touched minutes ago
    # routinely carries a prompt from months back; feeding that to the
    # accumulator hands the user content from outside the window they set.  The
    # record's own timestamp decides, and a record with no timestamp cannot be
    # shown to be inside the window, so under bounded consent it is not read.
    if cutoff_iso and fallback_prompts:
        in_window = [
            row for row in fallback_prompts if _within_window(row[2], cutoff_iso)
        ]
        outside = len(fallback_prompts) - len(in_window)
        if outside:
            stats["out_of_window"] += outside
            emit_lib.warn(
                warnings,
                "--days %d: %d 'last-prompt' fallback record(s) were dated outside "
                "the window or carried no timestamp and were not analyzed (the "
                "record's own timestamp decides, not the file's)"
                % (int(args.days), outside),
            )
        fallback_prompts = in_window

    if signals.turns_analyzed == 0 and fallback_prompts:
        emit_lib.warn(
            warnings,
            "no usable user turns parsed; fell back to %d truncated 'last-prompt' "
            "records -- shapes are reliable, counts are not"
            % len(fallback_prompts),
        )
        for prompt, session_id, timestamp in fallback_prompts:
            stats["user_turns_total"] += 1
            clean, slash = unwrap(prompt)
            signals.note_slash(slash)
            if clean is None:
                continue
            signals.add_turn(clean, session_id, timestamp)

    if stats["parse_errors"]:
        emit_lib.warn(
            warnings, "%d transcript line(s) failed to parse and were skipped" % stats["parse_errors"]
        )
    if stats["read_errors"]:
        emit_lib.warn(
            warnings,
            "%d session file(s) could not be read (%s)"
            % (stats["read_errors"], _safe(stats["last_error"])[:120]),
        )
    if stats["oversize_lines"]:
        emit_lib.warn(
            warnings,
            "%d oversized transcript line(s) (>%d MB) skipped as pasted payloads"
            % (stats["oversize_lines"], MAX_LINE_BYTES // (1024 * 1024)),
        )
    if stats["fork_duplicates"]:
        emit_lib.warn(
            warnings,
            "%d user turn(s) in this repo's Codex history were copies that a "
            "forked thread inherited from the thread it was forked from, and "
            "were counted once rather than once per fork"
            % stats["fork_duplicates"],
        )

    session_count = len(signals.sessions_seen)
    bucket = history_bucket(session_count)
    if bucket in ("none", "thin"):
        emit_lib.warn(
            warnings,
            "history is '%s' (%d session(s) with usable turns): transcript evidence "
            "is weak, lean on repo and git signals" % (bucket, session_count),
        )

    # Docs and code rank separately: a plan document mentioned ten times is not
    # a code hotspot, and mixing them made `file_hotspots` read as one.
    code_paths, doc_paths = split_hotspots(signals.paths)

    # Paths anchored outside the repo were already withheld from both lists.
    # Warn only about the ones that would otherwise have cleared the count>=2
    # bar and been printed: that is the only case where a reader loses
    # something, and a run whose repeated paths are mostly external is the
    # signature of a transcript directory matched to the wrong checkout.
    external_repeated = sorted(
        ((path, hits) for path, hits in signals.external_paths.items() if hits >= 2),
        key=lambda pair: (-pair[1], pair[0]),
    )
    if external_repeated:
        emit_lib.warn(
            warnings,
            "%d repeatedly-mentioned path(s) live outside this repo and are not "
            "in file_hotspots (e.g. %s); if that is the work you do here, the "
            "matched transcript directory may be the wrong checkout"
            % (
                len(external_repeated),
                ", ".join(path for path, _hits in external_repeated[:2]),
            ),
        )

    report = {
        "schema_version": SCHEMA_VERSION,
        "tool": TOOL,
        "target": args.target,
        "transcript_root": _safe(transcript_root) if transcript_root else "",

        "consent_scope": {
            "days": args.days if args.days else None,
            "max_sessions": args.max_sessions if args.max_sessions else None,
        },
        "sessions": {
            "files": len(selected),
            "count": session_count,
            "first": signals.first_ts,
            "last": signals.last_ts,
            "user_turns_total": stats["user_turns_total"],
            "user_turns_analyzed": signals.turns_analyzed,
            # Turn-taking ("ok", "thanks", "continue").  A number, not a list:
            # it says how chatty the history is and maps to no artifact.
            "social_turns": signals.social_turns,
            "bytes_read": bytes_read,
        },
        "history_bucket": bucket,
        "request_shapes": build_request_shapes(signals, top),
        "meta_queries": build_meta_queries(signals, TOP_META),
        "commands_requested": _counted(signals.commands, "command", "count", TOP_COMMANDS),
        "slash_commands": _counted(signals.slash, "name", "count", TOP_SLASH),
        "corrections": build_corrections(signals, TOP_CORRECTIONS),
        "tool_mentions": _counted(signals.services, "name", "count", TOP_TOOLS),
        "pain_signals": build_pain(signals, TOP_PAIN),
        "file_hotspots": _counted(code_paths, "path", "mentions", TOP_FILES),
        "doc_hotspots": _counted(doc_paths, "path", "mentions", TOP_DOCS),
        "scrub_stats": scrub_lib.make_scrub_stats(signals.scrub_hits),
        "output_chars": 0,
        "warnings": warnings,
        "timing_ms": 0,
    }

    if args.redact_report:
        report = apply_redaction(report)
        emit_lib.warn(warnings, "--redact-report: verbatim examples omitted; counts only")

    timer.__exit__(None, None, None)
    report["timing_ms"] = timer.elapsed_ms()

    cap = args.cap_chars if args.cap_chars else CAP_CHARS
    # Priority trim first (least load-bearing lists lose rows, request_shapes
    # last); emit() stays wired up behind it as the fair-share backstop.
    fit_to_cap(report, cap, warnings)
    emit_lib.emit(report, cap_chars=cap, trim_keys=TRIM_KEYS)
    return 0


# ---------------------------------------------------------------------------
# --selftest
# ---------------------------------------------------------------------------

def selftest():
    """
    Fast internal sanity check: imports resolve, emit round-trips, the module's
    regexes compile, and a synthetic four-turn session is mined end to end --
    proving the record filter, the scrubber and the clusterer are all wired up.

    Runs against a temp CLAUDE_CONFIG_DIR, so it never reads the developer's
    real history and never depends on them having any.  Sub-second.
    """
    import io
    import shutil
    import tempfile
    import time as _time

    started = int(_time.time() * 1000)
    checks = []

    def add(name, ok, detail=""):
        checks.append((name, bool(ok), str(detail)))

    add(
        "imports resolve",
        hasattr(scrub_lib, "scrub") and hasattr(textnorm, "skeleton") and hasattr(emit_lib, "emit"),
        "lib.emit, lib.scrub, lib.textnorm",
    )

    ok, detail = emit_lib.check_regexes(sys.modules[__name__])
    add("regexes compile and match", ok, detail)

    buffer = io.StringIO()
    text = emit_lib.emit(
        {"schema_version": SCHEMA_VERSION, "tool": TOOL, "request_shapes": [], "warnings": []},
        cap_chars=CAP_CHARS,
        trim_keys=TRIM_KEYS,
        stream=buffer,
    )
    try:
        add("emit round-trips", json.loads(text).get("tool") == TOOL, text[:120])
    except ValueError as exc:
        add("emit round-trips", False, str(exc))

    add(
        "project-dir encoding matches the documented scheme",
        encode_project_dir("/Users/x/Documents/projects/acme/web-app")
        == "-Users-x-Documents-projects-acme-web-app"
        and encode_project_dir("/Users/x/.claude/projects/foo") == "-Users-x--claude-projects-foo",
        encode_project_dir("/Users/x/.claude/projects/foo"),
    )

    # -- synthetic session, mined end to end ---------------------------------
    sandbox = tempfile.mkdtemp(prefix="agentic-codebase-mt-selftest-")
    saved_env = os.environ.get("CLAUDE_CONFIG_DIR")
    saved_codex_env = os.environ.get("CODEX_HOME")
    try:
        repo = os.path.join(sandbox, "repo")
        os.makedirs(repo)
        config = os.path.join(sandbox, "config")
        project = os.path.join(config, "projects", encode_project_dir(repo))
        os.makedirs(project)

        def user(text_, stamp, session):
            return json.dumps(
                {
                    "type": "user",
                    "sessionId": session,
                    "timestamp": stamp,
                    "message": {"role": "user", "content": text_},
                }
            )

        # TWO sessions on purpose.  build_request_shapes() only promotes a
        # cluster seen in 2+ sessions (or 4+ times), because repetition inside
        # one session is a retry loop while repetition across sessions is a
        # workflow.  A one-session fixture would report zero shapes and teach
        # a contributor that the clusterer is broken when it is working.
        first = [
            user("add a new API endpoint for /users with zod validation", "2026-09-01T10:00:00.000Z", "s1"),
            user("no, use bun not npm for this", "2026-09-01T10:10:00.000Z", "s1"),
            user("run the tests again, the build is still failing", "2026-09-01T10:15:00.000Z", "s1"),
            user("here is my key sk-ant-api03-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", "2026-09-01T10:20:00.000Z", "s1"),
            # A status question, a turn-taking turn, and a turn naming one code
            # path and one doc path -- the three splits the report depends on.
            user("what's done, what's remaining?", "2026-09-01T10:25:00.000Z", "s1"),
            user("ok thanks, continue", "2026-09-01T10:26:00.000Z", "s1"),
            user("check src/api/users.ts against docs/plans/rollout.md", "2026-09-01T10:30:00.000Z", "s1"),
            # A path in a DIFFERENT project, and a real directive wrapped in
            # swearing.  Both repeat in session 2, so both clear count>=2 and
            # both would reach stdout if the two rules below stopped working.
            user("the numbers are in ~/Desktop/other/dashboard.json", "2026-09-01T10:35:00.000Z", "s1"),
            user("i don't want fucking trigger stack trace.", "2026-09-01T10:40:00.000Z", "s1"),
            # Must all be ignored: assistant turn, tool result, sidechain, meta.
            json.dumps({"type": "assistant", "message": {"role": "assistant", "content": "sure"}}),
            json.dumps({"type": "user", "toolUseResult": {"x": 1}, "message": {"role": "user", "content": "tool out"}}),
            json.dumps({"type": "user", "isSidechain": True, "message": {"role": "user", "content": "subagent work"}}),
            json.dumps({"type": "user", "isMeta": True, "message": {"role": "user", "content": "meta noise"}}),
            "{not json at all",
        ]
        second = [
            user("add an api endpoint for /orders with validation", "2026-09-02T09:00:00.000Z", "s2"),
            user("add the api endpoint for /invoices with validation", "2026-09-02T09:30:00.000Z", "s2"),
            user("how many are remaining now?", "2026-09-02T09:40:00.000Z", "s2"),
            user("compare src/api/users.ts with docs/plans/rollout.md once more", "2026-09-02T09:45:00.000Z", "s2"),
            user("pull the numbers from ~/Desktop/other/dashboard.json", "2026-09-02T09:50:00.000Z", "s2"),
            user("i don't want fucking trigger stack trace.", "2026-09-02T09:55:00.000Z", "s2"),
        ]
        with open(os.path.join(project, "session-1.jsonl"), "w") as handle:
            handle.write("\n".join(first) + "\n")
        with open(os.path.join(project, "session-2.jsonl"), "w") as handle:
            handle.write("\n".join(second) + "\n")

        os.environ["CLAUDE_CONFIG_DIR"] = config
        buffer = io.StringIO()
        saved_stdout = sys.stdout
        try:
            sys.stdout = buffer
            code = main(["--repo", repo, "--target", "claude-code"])
        finally:
            sys.stdout = saved_stdout
        raw = buffer.getvalue()
        add("synthetic session run exits 0", code == 0, str(code))
        try:
            result = json.loads(raw)
        except ValueError as exc:
            result = {}
            add("synthetic session emits one JSON object", False, "%s | %r" % (exc, raw[:120]))
        else:
            add("synthetic session emits one JSON object", raw.count("\n") == 1, str(raw.count("\n")))

        sessions = result.get("sessions", {})
        add(
            "user turns are counted, non-user records are not",
            sessions.get("user_turns_analyzed", 0) == 15 and sessions.get("count", 0) == 2,
            "analyzed=%s sessions=%s"
            % (sessions.get("user_turns_analyzed"), sessions.get("count")),
        )
        add(
            "assistant / tool / sidechain / meta records are dropped",
            "subagent work" not in raw and "tool out" not in raw and "meta noise" not in raw,
        )
        shapes = result.get("request_shapes") or []
        add(
            "cross-session repeats cluster into a request shape",
            any(s.get("skeleton") == "add api endpoint with validation" and s.get("count") == 3 for s in shapes),
            str([(s.get("skeleton"), s.get("count"), s.get("sessions")) for s in shapes]),
        )
        meta = result.get("meta_queries") or []
        add(
            "status questions go to meta_queries, not request_shapes",
            len(meta) == 1
            and meta[0].get("count") == 2
            and meta[0].get("sessions") == 2
            and not any("remain" in (s_.get("skeleton") or "") for s_ in shapes),
            "meta=%s shapes=%s"
            % ([(m.get("skeleton"), m.get("count")) for m in meta], [s_.get("skeleton") for s_ in shapes]),
        )
        add(
            "turn-taking is a number, not a row",
            sessions.get("social_turns") == 1,
            str(sessions.get("social_turns")),
        )
        add(
            "docs and code hotspots are separate lists",
            [h.get("path") for h in (result.get("file_hotspots") or [])] == ["src/api/users.ts"]
            and [h.get("path") for h in (result.get("doc_hotspots") or [])] == ["docs/plans/rollout.md"],
            "code=%s docs=%s"
            % (result.get("file_hotspots"), result.get("doc_hotspots")),
        )
        add(
            "paths outside the repo never reach a hotspot list",
            "Desktop/other/dashboard.json"
            not in json.dumps(
                (result.get("file_hotspots") or []) + (result.get("doc_hotspots") or [])
            )
            and any("outside this repo" in w for w in (result.get("warnings") or [])),
            "code=%s docs=%s warnings=%s"
            % (result.get("file_hotspots"), result.get("doc_hotspots"), result.get("warnings")),
        )
        profane = [
            row
            for row in (result.get("corrections") or [])
            if "trigger stack trace" in (row.get("text") or "")
        ]
        add(
            "a profane correction survives as a row, masked",
            len(profane) == 1
            and profane[0].get("count", 0) >= 2
            and PROFANITY_MASK in profane[0]["text"]
            and not _PROFANITY.search(raw),
            "row=%s" % (profane[:1],),
        )
        add(
            "every reported row has a count of 2 or more",
            all(
                row.get("count", row.get("mentions", 0)) >= 2
                for key in (
                    "request_shapes", "meta_queries", "commands_requested", "slash_commands",
                    "corrections", "tool_mentions", "pain_signals", "file_hotspots", "doc_hotspots",
                )
                for row in (result.get(key) or [])
            ),
            str({k: result.get(k) for k in ("corrections", "pain_signals", "tool_mentions")}),
        )
        add(
            "secrets are scrubbed before anything is written",
            "sk-ant-api03" not in raw and result.get("scrub_stats", {}).get("redactions", 0) >= 1,
            str(result.get("scrub_stats")),
        )
        add(
            "malformed lines degrade rather than raise",
            isinstance(result.get("warnings"), list),
            str(len(result.get("warnings") or [])),
        )


        # -- Codex: the same job against a different format -------------------
        #
        # A second synthetic fixture, mined end to end against a temp
        # CODEX_HOME.  Codex's rollout format shares nothing with Claude Code's
        # except being JSONL, and the failure this guards against is specific
        # and was real: an earlier miner read `event_msg`/`user_message` only
        # and extracted FOUR of eight planted turns, because on this format the
        # durable representation of a human turn is `response_item`.
        #
        # Everything the fixture plants is something measured in a real 324-file
        # history: subagent and guardian-review rollouts (60% of that corpus),
        # a fork that re-copies its parent's turns, harness text typed as
        # `role: "user"`, and a session in a git worktree at an unrelated path.
        codex_home = os.path.join(sandbox, "codex")
        day = os.path.join(codex_home, "sessions", "2026", "09", "01")
        os.makedirs(day)
        os.makedirs(os.path.join(codex_home, "archived_sessions"))

        def rec(kind, payload, stamp="2026-09-01T10:00:00.000Z"):
            return json.dumps({"timestamp": stamp, "type": kind, "payload": payload})

        def meta(cwd, **extra):
            payload = {"id": "t-main", "cwd": cwd, "timestamp": "2026-09-01T10:00:00.000Z"}
            payload.update(extra)
            return rec("session_meta", payload)

        def uturn(text_, stamp):
            return rec(
                "response_item",
                {"type": "message", "role": "user",
                 "content": [{"type": "input_text", "text": text_}]},
                stamp,
            )

        def event_uturn(text_, stamp):
            return rec("event_msg", {"type": "user_message", "message": text_}, stamp)

        planted = [
            "add a new API endpoint for /users with zod validation",
            "add an api endpoint for /orders with validation",
            "add the api endpoint for /invoices with validation",
            "no, use bun not npm for this",
            "run the tests again, the build is still failing",
            "here is my key sk-ant-api03-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
            "check src/api/users.ts against docs/plans/rollout.md",
            "what's done, what's remaining?",
        ]
        main_session = [meta(repo, git={"repository_url": "git@github.com:acme/thing.git"})]
        for index, line in enumerate(planted):
            main_session.append(uturn(line, "2026-09-01T10:0%d:00.000Z" % index))
        # The same turn in BOTH representations must be counted once.
        main_session.append(event_uturn(planted[0], "2026-09-01T10:00:01.000Z"))
        # Harness text typed as a user turn.  Every one of these was measured
        # in the real corpus and every one of them clusters if it survives.
        main_session += [
            uturn("<recommended_plugins>\nHere is a list of plugins…\n</recommended_plugins>", "2026-09-01T10:20:00.000Z"),
            uturn("# AGENTS.md instructions for %s\n\n<INSTRUCTIONS>\nnever use npm\n</INSTRUCTIONS>" % repo, "2026-09-01T10:21:00.000Z"),
            uturn("<skill>\n<name>x:y</name>\n---\nname: y\n---\nbody\n</skill>", "2026-09-01T10:22:00.000Z"),
            uturn("Respond directly to the user's prompt. Do not run shell commands, apply patches, use MCP servers, use web search, or call any tools.\n\nYou are generating a short conversation title.", "2026-09-01T10:23:00.000Z"),
            uturn("# Files mentioned by the user:\n\n## a.json: /tmp/a.json\n\n## My request for Codex:\ndeploy the worker to staging please", "2026-09-01T10:24:00.000Z"),
            uturn("[$acme:ship](/tmp/skills/ship/SKILL.md) [plan.md](docs/plans/rollout.md) \nship the release branch now", "2026-09-01T10:25:00.000Z"),
            # Assistant + developer + compaction records must never be read.
            rec("response_item", {"type": "message", "role": "assistant",
                                  "content": [{"type": "output_text", "text": "sure"}]}),
            rec("response_item", {"type": "message", "role": "developer",
                                  "content": [{"type": "input_text", "text": "developer noise"}]}),
            rec("compacted", {"message": "summary", "replacement_history": [
                {"type": "message", "role": "user",
                 "content": [{"type": "input_text", "text": "compacted echo"}]}]}),
            "{not json at all",
        ]

        # A session started in a SUBDIRECTORY of the repo: included, reported.
        subdir_session = [
            meta(os.path.join(repo, "apps", "web"), id="t-sub"),
            uturn("add an api endpoint for /payments with validation", "2026-09-01T11:00:00.000Z"),
            uturn("<environment_context>\n<cwd>%s</cwd>\n</environment_context>\ndeploy the worker to staging please" % repo, "2026-09-01T11:01:00.000Z"),
            uturn("[$acme:ship](/tmp/skills/ship/SKILL.md) ship the release branch now", "2026-09-01T11:02:00.000Z"),
        ]
        # A git WORKTREE of the same repo at an unrelated path: included via
        # session_meta.git.repository_url, which has no Claude Code equivalent.
        worktree_session = [
            meta(os.path.join(sandbox, "worktree-elsewhere"), id="t-wt",
                 git={"repository_url": "https://github.com/acme/thing.git"}),
            uturn("add an api endpoint for /refunds with validation", "2026-09-01T11:10:00.000Z"),
        ]
        # A FORK: its history is a re-serialized copy of the main thread's, with
        # NEW timestamps (measured), so only the parent/child edge can spot it.
        fork_session = [meta(repo, id="t-fork", forked_from_id="t-main", timestamp="2026-09-01T12:00:00.000Z")]
        for index, line in enumerate(planted[:3]):
            fork_session.append(uturn(line, "2026-09-01T12:0%d:00.000Z" % index))
        # Subagent + guardian-review rollouts: the Codex analogue of a sidechain.
        subagent_session = [
            rec("session_meta", {"id": "t-sa", "cwd": repo, "thread_source": "subagent",
                                 "parent_thread_id": "t-main",
                                 "source": {"subagent": {"thread_spawn": {"depth": 1}}}}),
            uturn("subagent prompt that reads exactly like a human request", "2026-09-01T13:00:00.000Z"),
        ]
        guardian_session = [
            rec("session_meta", {"id": "t-gr", "cwd": repo, "thread_source": "guardian_review"}),
            uturn("guardian replay of the user transcript", "2026-09-01T13:10:00.000Z"),
        ]
        # Another project entirely.
        other_session = [
            rec("session_meta", {"id": "t-other", "cwd": os.path.join(sandbox, "other-repo")}),
            uturn("work on the other project instead", "2026-09-01T14:00:00.000Z"),
        ]
        # Archived tree: same format, must be read.
        archived_session = [
            rec("session_meta", {"id": "t-arch", "cwd": repo}),
            uturn("add an api endpoint for /credits with validation", "2026-09-01T09:00:00.000Z"),
        ]

        fixtures = [
            (os.path.join(day, "rollout-2026-09-01T10-00-00-main.jsonl"), main_session),
            (os.path.join(day, "rollout-2026-09-01T11-00-00-sub.jsonl"), subdir_session),
            (os.path.join(day, "rollout-2026-09-01T11-10-00-wt.jsonl"), worktree_session),
            (os.path.join(day, "rollout-2026-09-01T12-00-00-fork.jsonl"), fork_session),
            (os.path.join(day, "rollout-2026-09-01T13-00-00-sa.jsonl"), subagent_session),
            (os.path.join(day, "rollout-2026-09-01T13-10-00-gr.jsonl"), guardian_session),
            (os.path.join(day, "rollout-2026-09-01T14-00-00-other.jsonl"), other_session),
            (
                os.path.join(codex_home, "archived_sessions",
                             "rollout-2026-09-01T09-00-00-arch.jsonl"),
                archived_session,
            ),
        ]
        for target_path, lines in fixtures:
            with open(target_path, "w") as handle:
                handle.write("\n".join(lines) + "\n")

        # The repo's own remote, so the worktree session can be matched to it.
        os.makedirs(os.path.join(repo, ".git"))
        with open(os.path.join(repo, ".git", "config"), "w") as handle:
            handle.write(
                '[core]\n\trepositoryformatversion = 0\n'
                '[remote "origin"]\n\turl = https://github.com/acme/thing.git\n'
            )
        add(
            "the repo's git remote is read from .git/config without a subprocess",
            normalize_git_url(repo_git_url(repo)) == "github.com/acme/thing"
            and normalize_git_url("git@github.com:Acme/Thing.git") == "github.com/acme/thing",
            repo_git_url(repo),
        )

        os.environ["CODEX_HOME"] = codex_home
        os.environ["CLAUDE_CONFIG_DIR"] = os.path.join(sandbox, "no-such-config")
        buffer = io.StringIO()
        saved_stdout = sys.stdout
        try:
            sys.stdout = buffer
            code = main(["--repo", repo, "--target", "codex"])
        finally:
            sys.stdout = saved_stdout
        raw_codex = buffer.getvalue()
        add("codex run exits 0", code == 0, str(code))
        try:
            cx = json.loads(raw_codex)
        except ValueError as exc:
            cx = {}
            add("codex run emits one JSON object", False, "%s | %r" % (exc, raw_codex[:120]))
        else:
            add("codex run emits one JSON object", raw_codex.count("\n") == 1,
                str(raw_codex.count("\n")))

        add(
            "codex emits the SAME top-level schema as claude-code",
            set(cx.keys()) == set(result.keys()) and cx.get("target") == "codex",
            "only-in-codex=%s only-in-claude=%s"
            % (sorted(set(cx) - set(result)), sorted(set(result) - set(cx))),
        )

        cx_sessions = cx.get("sessions", {})
        # Main rollout: 8 planted turns, one of them repeated as an `event_msg`
        # (merged, not counted twice), and 6 harness turns of which 4 are
        # dropped whole and 2 unwrap to a real request.  Then 3 turns in the
        # subdirectory session, 1 in the worktree, 1 in the archived tree, and
        # 3 fork copies that must not be counted at all.
        add(
            "all eight planted turns are read, not four "
            "(response_item is the source, event_msg only fills gaps)",
            cx_sessions.get("user_turns_analyzed", 0) == 15
            and cx_sessions.get("count", 0) == 4,
            "analyzed=%s sessions=%s total=%s"
            % (
                cx_sessions.get("user_turns_analyzed"),
                cx_sessions.get("count"),
                cx_sessions.get("user_turns_total"),
            ),
        )
        add(
            "the same turn in both record shapes is counted once",
            cx_sessions.get("user_turns_total", 0) == 19,
            str(cx_sessions.get("user_turns_total")),
        )
        add(
            "subagent, guardian-review, assistant, developer and compacted "
            "records are all dropped",
            "subagent prompt" not in raw_codex
            and "guardian replay" not in raw_codex
            and "developer noise" not in raw_codex
            and "compacted echo" not in raw_codex
            and "other project instead" not in raw_codex,
        )
        add(
            "harness turns typed as role=user never reach the report",
            "recommended_plugins" not in raw_codex
            and "AGENTS.md instructions" not in raw_codex
            and "conversation title" not in raw_codex
            and "INSTRUCTIONS" not in raw_codex,
            raw_codex[:200],
        )
        cx_shapes = [s_.get("skeleton") for s_ in (cx.get("request_shapes") or [])]
        add(
            "a request wrapped in a file manifest is unwrapped, not dropped",
            any("deploy worker staging" in (s_ or "") for s_ in cx_shapes),
            str(cx_shapes),
        )
        add(
            "cross-session repeats cluster the same way as on claude-code",
            any(
                s_.get("skeleton") == "add api endpoint with validation"
                and s_.get("count") == 6
                for s_ in (cx.get("request_shapes") or [])
            ),
            str([(s_.get("skeleton"), s_.get("count"), s_.get("sessions"))
                 for s_ in (cx.get("request_shapes") or [])]),
        )
        add(
            "a forked thread's copied turns are counted once, not twice",
            any("forked thread" in w for w in (cx.get("warnings") or [])),
            str(cx.get("warnings")),
        )
        add(
            "subdirectory and worktree sessions are included AND reported",
            any("subdirectory of this repo" in w for w in (cx.get("warnings") or []))
            and any("same git remote" in w for w in (cx.get("warnings") or [])),
            str(cx.get("warnings")),
        )
        add(
            "codex slash commands are read from the [$plugin:skill](path) form",
            any(
                s_.get("name") == "acme:ship" and s_.get("count") == 2
                for s_ in (cx.get("slash_commands") or [])
            ),
            str(cx.get("slash_commands")),
        )
        add(
            "secrets are scrubbed on the codex path too",
            "sk-ant-api03" not in raw_codex
            and cx.get("scrub_stats", {}).get("redactions", 0) >= 1,
            str(cx.get("scrub_stats")),
        )
        add(
            "every reported codex row has a count of 2 or more",
            all(
                row.get("count", row.get("mentions", 0)) >= 2
                for key in (
                    "request_shapes", "meta_queries", "commands_requested", "slash_commands",
                    "corrections", "tool_mentions", "pain_signals", "file_hotspots",
                    "doc_hotspots",
                )
                for row in (cx.get(key) or [])
            ),
            str({k: cx.get(k) for k in ("request_shapes", "slash_commands")}),
        )

        # --resolve-only: counts and dates, no conversation read.
        buffer = io.StringIO()
        saved_stdout = sys.stdout
        try:
            sys.stdout = buffer
            code = main(["--repo", repo, "--target", "codex", "--resolve-only"])
        finally:
            sys.stdout = saved_stdout
        try:
            resolved = json.loads(buffer.getvalue())
        except ValueError:
            resolved = {}
        add(
            "codex --resolve-only reports root, count and range without turns",
            code == 0
            and resolved.get("mode") == "resolve-only"
            and resolved.get("sessions", {}).get("files") == 5
            and "user_turns_total" not in resolved.get("sessions", {}),
            "files=%s root=%s"
            % (resolved.get("sessions", {}).get("files"), resolved.get("transcript_root")),
        )

        # A missing CODEX_HOME degrades exactly like a missing project dir.
        os.environ["CODEX_HOME"] = os.path.join(sandbox, "no-such-codex")
        buffer = io.StringIO()
        saved_stdout = sys.stdout
        try:
            sys.stdout = buffer
            code = main(["--repo", repo, "--target", "codex"])
        finally:
            sys.stdout = saved_stdout
        try:
            empty = json.loads(buffer.getvalue())
        except ValueError:
            empty = {}
        add(
            "no codex sessions is degraded (exit 0 + warning)",
            code == 0 and empty.get("history_bucket") == "none" and bool(empty.get("warnings")),
            "exit=%s bucket=%s" % (code, empty.get("history_bucket")),
        )

        # -- a missing transcript root is degraded, not fatal -----------------
        os.environ["CLAUDE_CONFIG_DIR"] = os.path.join(sandbox, "no-such-config")
        buffer = io.StringIO()
        saved_stdout = sys.stdout
        try:
            sys.stdout = buffer
            code = main(["--repo", repo, "--target", "claude-code"])
        finally:
            sys.stdout = saved_stdout
        try:
            parsed = json.loads(buffer.getvalue())
        except ValueError:
            parsed = {}
        add(
            "no transcripts is degraded (exit 0 + warning)",
            code == 0 and parsed.get("history_bucket") == "none" and bool(parsed.get("warnings")),
            "exit=%s bucket=%s" % (code, parsed.get("history_bucket")),
        )

        # -- the consent window is decided by the TURN'S OWN timestamp --------
        #
        # Four fixtures for one rule, because two real defects pulled in
        # opposite directions.  A `last-prompt` record 80 days old arrived in a
        # file written minutes ago and was analyzed under `--days 7`; a rollout
        # filed under an 80-day-old date directory and resumed an hour ago was
        # dropped under the same flag.  Both are the same mistake -- letting a
        # FILE or a DIRECTORY decide what a TURN's timestamp decides -- and the
        # checks below pin each direction so neither can be fixed back into the
        # other.

        def _stamp(moment):
            return moment.strftime("%Y-%m-%dT%H:%M:%S.000Z")

        stale_moment = _utc_now() - datetime.timedelta(days=80)
        recent_moment = _utc_now() - datetime.timedelta(hours=1)

        def run(argv):
            """
            One miner run with BOTH streams captured.  stderr matters here:
            `--debug` writes to it, and it is outside the JSON object that
            everything else in this script is scrubbed on the way into.
            """
            out_buf = io.StringIO()
            err_buf = io.StringIO()
            saved_out, saved_err = sys.stdout, sys.stderr
            try:
                sys.stdout, sys.stderr = out_buf, err_buf
                exit_code = main(argv)
            finally:
                sys.stdout, sys.stderr = saved_out, saved_err
            out_text = out_buf.getvalue()
            try:
                parsed_json = json.loads(out_text)
            except ValueError:
                parsed_json = {}
            return exit_code, out_text, err_buf.getvalue(), parsed_json

        def last_prompt(text_, session, stamp=None):
            record = {"type": "last-prompt", "lastPrompt": text_, "sessionId": session}
            if stamp:
                record["timestamp"] = stamp
            return json.dumps(record)

        # A project whose user records are unusable, so the `last-prompt`
        # fallback is the only source -- two records dated 80 days ago and one
        # carrying no timestamp at all, in files written just now.
        fb_repo = os.path.join(sandbox, "fallback-repo")
        os.makedirs(fb_repo)
        fb_config = os.path.join(sandbox, "fallback-config")
        fb_project = os.path.join(fb_config, "projects", encode_project_dir(fb_repo))
        os.makedirs(fb_project)
        with open(os.path.join(fb_project, "stale-1.jsonl"), "w") as handle:
            handle.write(
                "\n".join(
                    [
                        last_prompt(
                            "run npm test and fix the failing suite", "f1", _stamp(stale_moment)
                        ),
                        last_prompt(
                            "run npm test again for the api package", "f1", _stamp(stale_moment)
                        ),
                    ]
                )
                + "\n"
            )
        with open(os.path.join(fb_project, "stale-2.jsonl"), "w") as handle:
            handle.write(last_prompt("run npm test one more time before release", "f2") + "\n")

        os.environ["CLAUDE_CONFIG_DIR"] = fb_config
        os.environ["CODEX_HOME"] = os.path.join(sandbox, "no-such-codex")

        _code, fb_raw, _fb_err, fb = run(
            ["--repo", fb_repo, "--target", "claude-code", "--days", "7"]
        )
        fb_sessions = fb.get("sessions", {})
        add(
            "a last-prompt fallback record older than --days is not analyzed",
            fb_sessions.get("user_turns_analyzed") == 0
            and fb_sessions.get("user_turns_total") == 0,
            "analyzed=%s total=%s"
            % (fb_sessions.get("user_turns_analyzed"), fb_sessions.get("user_turns_total")),
        )
        add(
            "no evidence is derived from out-of-window last-prompt records",
            not (fb.get("commands_requested") or [])
            and not (fb.get("request_shapes") or [])
            and not (fb.get("slash_commands") or [])
            and not (fb.get("corrections") or [])
            and "npm test" not in fb_raw,
            "commands=%s shapes=%s"
            % (fb.get("commands_requested"), fb.get("request_shapes")),
        )

        # An undated fallback record on its own: it cannot be SHOWN to be inside
        # the window, so under bounded consent it is not read.
        und_config = os.path.join(sandbox, "fallback-config-undated")
        und_project = os.path.join(und_config, "projects", encode_project_dir(fb_repo))
        os.makedirs(und_project)
        with open(os.path.join(und_project, "undated.jsonl"), "w") as handle:
            handle.write(last_prompt("run npm test one more time before release", "u1") + "\n")
        os.environ["CLAUDE_CONFIG_DIR"] = und_config
        _code, und_raw, _und_err, und = run(
            ["--repo", fb_repo, "--target", "claude-code", "--days", "7"]
        )
        add(
            "an undated last-prompt fallback is skipped under bounded consent",
            und.get("sessions", {}).get("user_turns_analyzed") == 0
            and "npm test" not in und_raw,
            "analyzed=%s" % (und.get("sessions", {}).get("user_turns_analyzed"),),
        )

        # Consent "yes" (no window) must still get the fallback -- the repair is
        # a window check, not a deletion of the fallback.
        os.environ["CLAUDE_CONFIG_DIR"] = fb_config
        _code, _unb_raw, _unb_err, unb = run(["--repo", fb_repo, "--target", "claude-code"])
        add(
            "unbounded consent still reads the last-prompt fallback",
            unb.get("sessions", {}).get("user_turns_analyzed") == 3
            and any(
                row.get("command") == "npm test" and row.get("count") == 3
                for row in (unb.get("commands_requested") or [])
            ),
            "analyzed=%s commands=%s"
            % (
                unb.get("sessions", {}).get("user_turns_analyzed"),
                unb.get("commands_requested"),
            ),
        )

        # -- codex de-duplication: same turn once, repeated work N times ------
        #
        # De-duplication exists for two real overlaps -- one turn recorded in
        # both record streams, and a fork that re-copies its parent's prefix --
        # and for nothing else.  Keyed on a 400-character text prefix it also
        # erased three identical requests typed on three different days, which
        # is the exact evidence `request_shapes` and `commands_requested` exist
        # to carry, and merged two different long prompts that happened to open
        # the same way.
        f10_repo = os.path.join(sandbox, "dedup-repo")
        os.makedirs(f10_repo)
        f10_home = os.path.join(sandbox, "dedup-codex")
        f10_day = os.path.join(f10_home, "sessions", "2026", "09", "01")
        os.makedirs(f10_day)
        os.makedirs(os.path.join(f10_home, "archived_sessions"))

        repeated_turn = "run npm test and fix the failing suite"
        long_prefix = (
            "please refactor the checkout pricing module so that every currency "
            "conversion happens in one helper instead of being duplicated across "
            "the cart the invoice and the receipt renderer and make sure the "
            "rounding behaviour stays identical to what the finance team signed "
            "off on last quarter and keep the existing public function names so "
            "the other packages do not have to change and add a short comment "
            "explaining the rounding rule "
        )
        long_a = (
            long_prefix + "then rename src/alpha/service.ts to keep the handler naming consistent."
        )
        long_b = (
            long_prefix + "then delete the dead feature guard inside src/alpha/service.ts before we ship."
        )

        dup_session = [meta(f10_repo, id="t-dup")]
        for index in range(3):
            dup_session.append(uturn(repeated_turn, "2026-09-01T10:0%d:00.000Z" % index))
        dup_session.append(uturn(long_a, "2026-09-01T10:10:00.000Z"))
        dup_session.append(uturn(long_b, "2026-09-01T10:11:00.000Z"))
        # ONE turn, both record shapes.  This is what de-duplication is for.
        dup_session.append(uturn("deploy the worker to staging please", "2026-09-01T10:20:00.000Z"))
        dup_session.append(
            event_uturn("deploy the worker to staging please", "2026-09-01T10:20:01.000Z")
        )

        parent_turns = [
            "rotate the staging database credentials for the worker",
            "add a health check endpoint to the billing service",
            "write the migration for the invoice totals column",
        ]
        f10_parent = [meta(f10_repo, id="t-parent")]
        for index, line in enumerate(parent_turns):
            f10_parent.append(uturn(line, "2026-09-01T11:0%d:00.000Z" % index))
        f10_child = [meta(f10_repo, id="t-child", forked_from_id="t-parent", timestamp="2026-09-01T12:00:00.000Z")]
        for index, line in enumerate(parent_turns):
            f10_child.append(uturn(line, "2026-09-01T12:0%d:00.000Z" % index))
        f10_child.append(
            uturn("back out the invoice totals migration for now", "2026-09-01T12:30:00.000Z")
        )

        for name_, lines_ in (
            ("rollout-2026-09-01T10-00-00-dup.jsonl", dup_session),
            ("rollout-2026-09-01T11-00-00-parent.jsonl", f10_parent),
            ("rollout-2026-09-01T12-00-00-child.jsonl", f10_child),
        ):
            with open(os.path.join(f10_day, name_), "w") as handle:
                handle.write("\n".join(lines_) + "\n")

        os.environ["CODEX_HOME"] = f10_home
        os.environ["CLAUDE_CONFIG_DIR"] = os.path.join(sandbox, "no-such-config")
        _code, _f10_raw, _f10_err, f10 = run(["--repo", f10_repo, "--target", "codex"])
        f10_sessions = f10.get("sessions", {})
        add(
            "three identical codex turns at three timestamps stay three turns",
            any(
                row.get("command") == "npm test" and row.get("count") == 3
                for row in (f10.get("commands_requested") or [])
            ),
            "commands=%s analyzed=%s"
            % (f10.get("commands_requested"), f10_sessions.get("user_turns_analyzed")),
        )
        add(
            "two different long prompts sharing a 400-character prefix stay two turns",
            any(
                row.get("path") == "src/alpha/service.ts" and row.get("mentions") == 2
                for row in (f10.get("file_hotspots") or [])
            ),
            "hotspots=%s" % (f10.get("file_hotspots"),),
        )
        add(
            "the same codex turn in two record streams is still counted once",
            f10_sessions.get("user_turns_total") == 10
            and f10_sessions.get("user_turns_analyzed") == 10,
            "total=%s analyzed=%s"
            % (
                f10_sessions.get("user_turns_total"),
                f10_sessions.get("user_turns_analyzed"),
            ),
        )
        add(
            "a forked thread's copied prefix is counted once and its new turn kept",
            any("forked thread" in w for w in (f10.get("warnings") or []))
            and f10_sessions.get("count") == 3,
            "sessions=%s warnings=%s" % (f10_sessions.get("count"), f10.get("warnings")),
        )

        # -- a thread filed under an old date and resumed inside the window ---
        f11_repo = os.path.join(sandbox, "resumed-repo")
        os.makedirs(f11_repo)
        f11_home = os.path.join(sandbox, "resumed-codex")
        old_date = (_utc_now() - datetime.timedelta(days=80)).date()
        f11_day = os.path.join(
            f11_home,
            "sessions",
            "%04d" % old_date.year,
            "%02d" % old_date.month,
            "%02d" % old_date.day,
        )
        os.makedirs(f11_day)
        os.makedirs(os.path.join(f11_home, "archived_sessions"))
        with open(os.path.join(f11_day, "rollout-resumed.jsonl"), "w") as handle:
            handle.write(
                "\n".join(
                    [
                        meta(f11_repo, id="t-resumed"),
                        uturn("clean up the legacy billing importer", _stamp(stale_moment)),
                        uturn("run npm test and fix the failing suite", _stamp(recent_moment)),
                    ]
                )
                + "\n"
            )
        os.environ["CODEX_HOME"] = f11_home
        _code, f11_raw, _f11_err, f11 = run(
            ["--repo", f11_repo, "--target", "codex", "--days", "7"]
        )
        add(
            "a codex thread filed under an old date but resumed inside the window is read",
            f11.get("sessions", {}).get("user_turns_analyzed") == 1
            and f11.get("sessions", {}).get("files") == 1,
            "analyzed=%s files=%s warnings=%s"
            % (
                f11.get("sessions", {}).get("user_turns_analyzed"),
                f11.get("sessions", {}).get("files"),
                f11.get("warnings"),
            ),
        )
        add(
            "an out-of-window turn in a freshly written file is still not analyzed",
            "legacy billing importer" not in f11_raw
            and f11.get("sessions", {}).get("user_turns_analyzed") == 1,
            "analyzed=%s" % (f11.get("sessions", {}).get("user_turns_analyzed"),),
        )

        # -- --debug diagnostics never carry credentials ----------------------
        f12_repo = os.path.join(sandbox, "remote-repo")
        os.makedirs(os.path.join(f12_repo, ".git"))
        with open(os.path.join(f12_repo, ".git", "config"), "w") as handle:
            handle.write(
                "[core]\n\trepositoryformatversion = 0\n"
                '[remote "origin"]\n\turl = https://svcuser:s3cr3t@example.invalid/repo.git\n'
            )
        f12_home = os.path.join(sandbox, "remote-codex")
        f12_day = os.path.join(f12_home, "sessions", "2026", "09", "01")
        os.makedirs(f12_day)
        os.makedirs(os.path.join(f12_home, "archived_sessions"))
        with open(os.path.join(f12_day, "rollout-remote.jsonl"), "w") as handle:
            handle.write(
                "\n".join(
                    [
                        meta(f12_repo, id="t-remote"),
                        uturn("check the deploy script once more", "2026-09-01T10:00:00.000Z"),
                    ]
                )
                + "\n"
            )
        os.environ["CODEX_HOME"] = f12_home
        _code, f12_out, f12_err, _f12 = run(
            ["--repo", f12_repo, "--target", "codex", "--debug"]
        )
        add(
            "--debug never prints a credential-bearing git remote",
            "s3cr3t" not in f12_out
            and "s3cr3t" not in f12_err
            and "svcuser" not in f12_out
            and "svcuser" not in f12_err,
            # Never echo the value itself, not even a synthetic one.
            "password_in_stdout=%s password_in_stderr=%s user_in_stderr=%s"
            % ("s3cr3t" in f12_out, "s3cr3t" in f12_err, "svcuser" in f12_err),
        )

        # F03's second gate, which the scrubber-level tests do not reach: a
        # QUOTED credential key planted in a real transcript must be absent
        # from BOTH streams of a real miner run.
        #
        # Two things make this check load-bearing, and both were missing from
        # the two pre-existing end-to-end secret checks:
        #   1. The planted value is caught ONLY by the quoted-key repair.  The
        #      others plant `sk-ant-api03-...`, which the dedicated vendor rule
        #      already caught BEFORE that repair -- so they passed with the
        #      defect fully present and would still pass if it were reverted.
        #   2. The turn repeats enough to clear the request-shape threshold, so
        #      the text is actually EMITTED in `request_shapes[].examples`.  A
        #      single turn is analyzed but echoed nowhere, which makes any
        #      assertion about it vacuous no matter what the scrubber does.
        # Verified by swapping in the pre-repair scrubber: the canary reaches
        # stdout there and is redacted here.
        _QK = "QUOTEDKEYCANARY" + "-8f3a1c"
        f03_home = os.path.join(sandbox, "f03-home")
        f03_repo = os.path.join(sandbox, "f03-repo")
        os.makedirs(f03_repo)
        os.makedirs(os.path.join(f03_home, "archived_sessions"))
        for _sid, _day in (("f03a", "14"), ("f03b", "15"), ("f03c", "16")):
            _dir = os.path.join(f03_home, "sessions", "2026", "09", _day)
            os.makedirs(_dir)
            _rows = [meta(f03_repo, id=_sid)]
            for _i in range(2):
                _rows.append(uturn(
                    'deploy the api and fix the config {"password": "%s"} '
                    "then rerun tests" % _QK,
                    "2026-09-%sT10:0%d:00.000Z" % (_day, _i)))
            with open(os.path.join(_dir, "rollout-%s.jsonl" % _sid), "w") as handle:
                handle.write("\n".join(_rows) + "\n")
        os.environ["CODEX_HOME"] = f03_home
        for _label, _argv in (
            ("plain", ["--repo", f03_repo, "--target", "codex"]),
            ("debug", ["--repo", f03_repo, "--target", "codex", "--debug"]),
        ):
            _c, f03_out, f03_err, f03_json = run(_argv)
            _shapes = f03_json.get("request_shapes") or []
            _examples = [ex for row in _shapes for ex in (row.get("examples") or [])]
            add(
                "a quoted-key transcript secret reaches neither stream (%s run)" % _label,
                _QK not in f03_out and _QK not in f03_err
                # the guard against a vacuous pass: the text must really have
                # been emitted, redacted, rather than dropped before it got here
                and any("REDACTED" in ex for ex in _examples),
                # report booleans, never the value itself
                "in_stdout=%s in_stderr=%s examples_emitted=%d redacted=%s exit=%s"
                % (_QK in f03_out, _QK in f03_err, len(_examples),
                   any("REDACTED" in ex for ex in _examples), _c),
            )

    finally:
        if saved_env is None:
            os.environ.pop("CLAUDE_CONFIG_DIR", None)
        else:
            os.environ["CLAUDE_CONFIG_DIR"] = saved_env
        if saved_codex_env is None:
            os.environ.pop("CODEX_HOME", None)
        else:
            os.environ["CODEX_HOME"] = saved_codex_env
        shutil.rmtree(sandbox, ignore_errors=True)

    return emit_lib.selftest_report(TOOL, checks, started_ms=started)


if __name__ == "__main__":
    sys.exit(emit_lib.main_guard(main, TOOL))
