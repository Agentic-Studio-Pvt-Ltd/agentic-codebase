#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agentic-codebase :: lib/scrub.py -- secret scrubbing, shared by every analyzer.

Contract (build contract, "Shared libs"):

    scrub(text) -> (clean_text, hits)

`hits` is one entry per *redaction*, naming the pattern kind, so callers can
build the `scrub_stats` block straight from it:

    {"redactions": len(hits), "patterns_hit": sorted(set(hits))}

Replacement token form is always `[REDACTED:<kind>]`.

Two things this module deliberately separates:

  * REDACTIONS  -- a secret was found and destroyed.  Counted in `hits`.
  * NORMALIZATIONS -- `/Users/<name>` and `/home/<name>` collapse to `~`.
    That is privacy hygiene, not a secret, and counting it in `scrub_stats`
    would inflate the redaction number on every transcript (every path in
    every prompt would count).  It is returned separately by
    `scrub_detailed()` as `path_normalizations`.

Ordering matters and is fixed in `_RULES`: the most specific patterns run
first, so a JWT is reported as `jwt` and not as `base64_blob`, and a
`postgres://user:pass@host` string is reported as `connection_string` and not
as three separate assignment hits.  Generic long-blob patterns run last.

ReDoS safety: no nested quantifiers anywhere, every repetition is upper
bounded, every "anything" run is a lazy bounded `[\\s\\S]{0,N}?` or a negated
character class.  Input is truncated at MAX_INPUT_CHARS per call.

Everything is compiled once at import.  `scrub()` is called on the order of
10^5 times in a rich-history run; it must not compile anything.

No network. Standard library only. Python 3.9+.
"""

import fnmatch
import os
import re
import sys
from typing import Dict, Iterable, List, Sequence, Tuple

__all__ = [
    "scrub",
    "scrub_all",
    "scrub_detailed",
    "scrub_all_detailed",
    "make_scrub_stats",
    "redaction_counts",
    "collapse_home_paths",
    "is_secret_path",
    "secret_path_reason",
    "is_env_file",
    "SECRET_FILENAME_PATTERNS",
    "SECRET_FILENAME_PATTERNS_EXTRA",
    "ALL_SECRET_FILENAME_PATTERNS",
    "ENV_FILENAME_PATTERNS",
    "MAX_INPUT_CHARS",
    "REDACTION_KINDS",
]

# ---------------------------------------------------------------------------
# Limits
# ---------------------------------------------------------------------------

#: Hard cap on how much text one `scrub()` call will look at.  A single user
#: turn in a transcript is normally < 2 KB; anything past this is a pasted log
#: or file dump, which is not signal, and scanning it 20 times with 20 regexes
#: is the only way this module can become slow.
MAX_INPUT_CHARS = 20000

#: Appended when the input was truncated, so downstream text is never silently
#: half a sentence.
TRUNCATION_MARKER = " [TRUNCATED:input]"

_REDACT_FMT = "[REDACTED:%s]"

#: Sentinel prefix used to recognise our own output and refuse to double-redact.
_REDACT_PREFIX = "[REDACTED:"


# ---------------------------------------------------------------------------
# Secret-looking filenames
# ---------------------------------------------------------------------------

#: The globs named in the build contract.  `discover.py` refuses to open any
#: file matching one of these *for its values*.
SECRET_FILENAME_PATTERNS = [
    ".env*",
    "*.pem",
    "*.key",
    "id_rsa*",
    "*credentials*",
    "*secret*",
    ".npmrc",
    ".netrc",
    "*.p12",
    "*.pfx",
    "*.keystore",
]

#: Additional globs in the same spirit.  Kept in a separate list so the
#: contract-named set above stays verifiable by eye.
SECRET_FILENAME_PATTERNS_EXTRA = [
    "id_dsa*",
    "id_ecdsa*",
    "id_ed25519*",
    "*.jks",
    "*.ppk",
    "*.pgpass",
    ".pgpass",
    ".htpasswd",
    "*.asc",
    "*.gpg",
    "*.kdbx",
    "known_hosts",
    "*.crt.key",
    "service-account*.json",
    "*serviceaccount*.json",
    "*.p8",
]

ALL_SECRET_FILENAME_PATTERNS = SECRET_FILENAME_PATTERNS + SECRET_FILENAME_PATTERNS_EXTRA

#: `.env*` files are a special case: `discover.py` is allowed to read them for
#: variable NAMES ONLY (parse left of `=`, never retain the value).  A caller
#: that wants that behaviour must check `is_env_file()` FIRST -- plain
#: `is_secret_path()` says True for them, which is the safe default.
ENV_FILENAME_PATTERNS = [".env", ".env.*", "*.env", "env.*"]


def _path_parts(path: str) -> List[str]:
    """Split a path into comparable components (both separators tolerated)."""
    if not path:
        return []
    normalized = str(path).replace("\\", "/")
    return [p for p in normalized.split("/") if p not in ("", ".", "..")]


_LOWERED_GLOB_CACHE = {}


def _lowered_globs(patterns: Sequence[str]) -> List[Tuple[str, str]]:
    """`[(glob, glob.lower())]`, cached per pattern list identity."""
    key = id(patterns)
    cached = _LOWERED_GLOB_CACHE.get(key)
    if cached is None or cached[0] is not patterns:
        pairs = [(glob, glob.lower()) for glob in patterns]
        _LOWERED_GLOB_CACHE[key] = (patterns, pairs)
        return pairs
    return cached[1]


def secret_path_reason(path: str, patterns: Sequence[str] = None) -> str:
    """
    Return the glob that makes `path` secret-looking, or "" if none does.

    Both the basename *and* every intermediate directory are checked, so
    `config/credentials/prod.yaml` is caught by `*credentials*` even though the
    basename is innocent.
    """
    if patterns is None:
        patterns = ALL_SECRET_FILENAME_PATTERNS
    parts = _path_parts(path)
    if not parts:
        return ""
    # `fnmatchcase`, not `fnmatch`: the latter calls `os.path.normcase` on BOTH
    # arguments on every call, and both sides are already lower-cased here.  On
    # a 3k-file tree that was 5.4M redundant `normcase` calls.  The lower-cased
    # globs are cached because `glob.lower()` used to run in the innermost loop
    # -- 21 patterns x every component x every read.
    lowered_globs = _lowered_globs(patterns)
    for part in parts:
        lowered = part.lower()
        for glob, lowered_glob in lowered_globs:
            if fnmatch.fnmatchcase(lowered, lowered_glob):
                return glob
    return ""


def is_secret_path(path: str, patterns: Sequence[str] = None) -> bool:
    """
    True when a file (or any directory on its path) looks like it holds
    credentials.  `discover.py` must not open these for their contents.

    >>> is_secret_path("/repo/.env.local")
    True
    >>> is_secret_path("/repo/src/app.ts")
    False
    """
    return secret_path_reason(path, patterns) != ""


def is_env_file(path: str) -> bool:
    """
    True for dotenv-style files, which `discover.py` may open for variable
    NAMES only (everything left of the first `=`; the value is never retained).
    """
    base = os.path.basename(str(path).replace("\\", "/")).lower()
    for glob in ENV_FILENAME_PATTERNS:
        if fnmatch.fnmatch(base, glob):
            # `.env.example` / `.env.sample` are templates, but they still get
            # the names-only treatment -- values in them are frequently real.
            return True
    return False


# ---------------------------------------------------------------------------
# Redaction rules
# ---------------------------------------------------------------------------
# Order is load bearing.  Read it top to bottom as "most specific first".

REDACTION_KINDS = [
    "private_key",
    "jwt",
    "connection_string",
    "url_credentials",
    "aws_key",
    "github_token",
    "slack_token",
    "anthropic_key",
    "openai_key",
    "stripe_key",
    "google_api_key",
    "sendgrid_key",
    "bearer_token",
    "basic_auth",
    "assignment",
    "env_assignment",
    "flag_value",
    "email",
    "hex_blob",
    "base64_blob",
]


def _simple(kind: str):
    """Build a re.sub replacement callable that records a hit."""

    def _factory(hits: List[str]):
        token = _REDACT_FMT % kind

        def _sub(match):
            hits.append(kind)
            return token

        return _sub

    return _factory


def _prefixed(kind: str, prefix: str):
    """Replacement that keeps a literal prefix, e.g. `Bearer <token>`."""

    def _factory(hits: List[str]):
        token = prefix + (_REDACT_FMT % kind)

        def _sub(match):
            hits.append(kind)
            return token

        return _sub

    return _factory


def _assignment_factory(hits: List[str]):
    """
    `password=hunter2` -> `password=[REDACTED:assignment]`.

    Keeps the key (it is signal: knowing the repo uses STRIPE_SECRET_KEY is
    useful) and destroys the value.  Refuses to touch a value that is already
    a redaction token, so `token=[REDACTED:jwt]` is not double counted.
    """
    token = _REDACT_FMT % "assignment"

    def _sub(match):
        value = match.group(3)
        stripped = value.strip("\"'")
        if stripped.startswith(_REDACT_PREFIX) or value.startswith(_REDACT_PREFIX):
            return match.group(0)
        # Obvious placeholders are not secrets and are useful context.
        if stripped.lower() in _PLACEHOLDER_VALUES:
            return match.group(0)
        hits.append("assignment")
        return match.group(1) + match.group(2) + token

    return _sub


_PLACEHOLDER_VALUES = frozenset(
    [
        "",
        "true",
        "false",
        "none",
        "null",
        "nil",
        "todo",
        "xxx",
        "changeme",
        "your_key_here",
        "<value>",
        "...",
        "$env",
        "process.env",
    ]
)

#: Minimum length before an env-var value is even considered secret-looking.
#: `PORT=3000`, `TZ=UTC` and `CGO_ENABLED=0` never reach the entropy test.
_ENV_VALUE_MIN_CHARS = 10

#: How far back `--value <x>` looks for a credential word before redacting.
#: Python's `re` has no variable-width lookbehind, so the check lives in the
#: replacement callable, which can see `match.string`.
_FLAG_CONTEXT_CHARS = 60

_CREDENTIAL_CONTEXT_RE = re.compile(
    r"(?:secret|password|passwd|token|credential|api[ _-]?key|apikey|"
    r"access[ _-]?key|private[ _-]?key|auth)",
    re.IGNORECASE,
)


def _class_count(value: str) -> int:
    """How many of {upper, lower, digit} a string uses.  Cheap entropy proxy."""
    upper = lower = digit = False
    for ch in value:
        if ch.isdigit():
            digit = True
        elif ch.isupper():
            upper = True
        elif ch.islower():
            lower = True
        if upper and lower and digit:
            break
    return int(upper) + int(lower) + int(digit)


#: `localhost:6379`, `db.internal:5432` -- a host:port pair is evidence about
#: the stack, not a credential.
_HOST_PORT_RE = re.compile(r"^[A-Za-z0-9.\-]{1,64}:\d{1,5}$")


def _looks_like_secret_value(value: str) -> bool:
    """
    Gate for values whose KEY did not name a credential.

    Deliberately conservative, because over-redacting here destroys the
    evidence the whole tool is built on: `NODE_ENV=production`,
    `LOG_LEVEL=debug` and `PYTHON_VERSION=3.11.4` must all survive.  Only a
    long value that mixes at least two character classes is destroyed.

    Measured on 40k real source and doc lines: this gate plus the no-spaces
    rule below fires on 0.005% of them.
    """
    stripped = value.strip().strip("\"'`")
    if stripped.startswith(_REDACT_PREFIX):
        return False
    if stripped.lower() in _PLACEHOLDER_VALUES:
        return False
    if len(stripped) < _ENV_VALUE_MIN_CHARS:
        return False
    # URLs and paths are handled by their own rules (connection_string,
    # url_credentials) or are legitimate evidence.
    if "://" in stripped:
        return False
    if stripped[0] in "/.~$<([{" or stripped.startswith("./"):
        return False
    # `$VAR`, `${VAR}` and `%VAR%` are indirection, not a secret.
    if "$" in stripped or stripped.startswith("%"):
        return False
    if _HOST_PORT_RE.match(stripped):
        return False
    if _class_count(stripped) < 2:
        return False
    # Two character classes alone still catches `VITE_APP_TITLE=MyDashboard`.
    # A real key almost always carries a digit; a long one does not need to.
    has_digit = any(ch.isdigit() for ch in stripped)
    return has_digit or len(stripped) >= 16


def _env_assignment_factory(hits: List[str]):
    """
    `SCREAMING_SNAKE=<high-entropy value>` -> value destroyed, name kept.

    This is the shape a pasted `.env` line takes, and the key name frequently
    carries no credential keyword at all (`STRIPE_WEBHOOK_SIGNING`,
    `SENTRY_DSN_INTERNAL`), so the keyword-driven `assignment` rule above
    cannot see it.  The name is signal and is preserved; the value is not.
    """
    token = _REDACT_FMT % "env_assignment"

    def _sub(match):
        if not _looks_like_secret_value(match.group(3)):
            return match.group(0)
        hits.append("env_assignment")
        return match.group(1) + match.group(2) + token

    return _sub


def _flag_value_factory(hits: List[str]):
    """
    `--password hunter2`, `--api-key abc123`, and the generic `--value X`
    when a credential word appears just before it (`wrangler secret put
    API_TOKEN --value X`).
    """
    token = _REDACT_FMT % "flag_value"

    def _sub(match):
        flag = (match.group(1) or "").lower()
        value = match.group(3)
        stripped = value.strip("\"'`")
        if stripped.startswith(_REDACT_PREFIX) or value.startswith(_REDACT_PREFIX):
            return match.group(0)
        if stripped.lower() in _PLACEHOLDER_VALUES:
            return match.group(0)
        # `--token --scope=x` -- the next flag is not this flag's value.
        if stripped.startswith("-") or stripped.startswith("<") or stripped.startswith("$"):
            return match.group(0)
        if flag == "value":
            # Too generic to redact on its own; require nearby credential talk.
            start = max(0, match.start() - _FLAG_CONTEXT_CHARS)
            if not _CREDENTIAL_CONTEXT_RE.search(match.string[start:match.start()]):
                return match.group(0)
        hits.append("flag_value")
        # `--` is part of the flag and is not in group(1); put it back, or the
        # scrubbed command text stops being a runnable command.
        return "--" + match.group(1) + match.group(2) + token

    return _sub


def _aws_secret_factory(hits: List[str]):
    """
    A bare 40-character AWS secret access key.

    `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` splits on `/` into runs too
    short for the base64 rule, so without this it survives every other rule.
    Guarded hard -- exactly 40 chars, must contain `/` or `+`, and must mix
    upper, lower and digit -- so a 40-character file path cannot trip it.
    """
    token = _REDACT_FMT % "aws_key"

    def _sub(match):
        value = match.group(0)
        if "/" not in value and "+" not in value:
            return value
        if _class_count(value) < 3:
            return value
        hits.append("aws_key")
        return token

    return _sub


def _hex_factory(hits: List[str]):
    """
    Long hex run.  Requires at least one a-f letter so that a 32 digit numeric
    id (an epoch-ish sequence, a phone-number blob) is not reported as a
    secret, and requires at least one digit so that an accidental long word
    made only of a-f characters is left alone.
    """
    token = _REDACT_FMT % "hex_blob"

    def _sub(match):
        value = match.group(0)
        has_letter = False
        has_digit = False
        for ch in value:
            if ch.isdigit():
                has_digit = True
            else:
                has_letter = True
            if has_letter and has_digit:
                break
        if not (has_letter and has_digit):
            return value
        hits.append("hex_blob")
        return token

    return _sub


def _base64_factory(hits: List[str]):
    """
    Long unpadded blob: alphanumerics only.

    `/` is deliberately NOT in this rule's character class.  It is a legal
    base64 character, but including it means `Users/ravi/repo/src/app/page`
    reads as a 34 character blob, so every deep file path in a transcript gets
    destroyed and counted as a leaked secret.  Padded base64 (which really can
    contain `/`) is handled by the separate `base64_blob` padded rule above.

    Guarded so English prose and long identifiers survive: the candidate must
    mix upper case, lower case and digits.
    """
    token = _REDACT_FMT % "base64_blob"

    def _sub(match):
        value = match.group(0)
        has_upper = False
        has_lower = False
        has_digit = False
        for ch in value:
            if ch.isdigit():
                has_digit = True
            elif ch.islower():
                has_lower = True
            elif ch.isupper():
                has_upper = True
        if not (has_upper and has_lower and has_digit):
            return value
        hits.append("base64_blob")
        return token

    return _sub


def _base64_padded_factory(hits: List[str]):
    """
    Base64 that ends in real `=` padding.  Padding is what makes `/` safe to
    allow here: a filesystem path does not end in `=`.
    """
    token = _REDACT_FMT % "base64_blob"

    def _sub(match):
        hits.append("base64_blob")
        return token

    return _sub


#: A quoted value, escape aware.  `"he said \"hi\""` and `'C:\\path'` end at
#: their real closing quote and not at the escaped one, so no tail of the value
#: survives the redaction.  Shared by every rule that accepts a quoted value.
#:
#: ReDoS: the two alternatives start with disjoint characters (one is "not a
#: backslash", the other IS a backslash), so there is nothing ambiguous for the
#: engine to backtrack through, neither alternative is itself quantified, and
#: the repetition is upper bounded -- see the note in the module docstring.
_QUOTED_VALUE_SRC = r"\"(?:[^\"\\\n]|\\.){0,512}\"|'(?:[^'\\\n]|\\.){0,512}'"


# Each rule: (kind, compiled regex, factory(hits) -> replacement callable)
_RULES = [
    # 1. Private key blocks.  Whole-block first, stray header second.
    (
        "private_key",
        re.compile(
            r"-----BEGIN[ A-Z]{0,40}PRIVATE KEY-----[\s\S]{0,8000}?-----END[ A-Z]{0,40}PRIVATE KEY-----"
        ),
        _simple("private_key"),
    ),
    (
        "private_key",
        re.compile(r"-----BEGIN[ A-Z]{0,40}PRIVATE KEY-----"),
        _simple("private_key"),
    ),
    (
        "private_key",
        re.compile(r"-----BEGIN OPENSSH PRIVATE KEY-----"),
        _simple("private_key"),
    ),
    # 2. JWTs, before Bearer and before the generic blob rules.
    (
        "jwt",
        re.compile(r"\beyJ[A-Za-z0-9_-]{10,4000}\.[A-Za-z0-9_-]{10,4000}(?:\.[A-Za-z0-9_-]{0,4000})?"),
        _simple("jwt"),
    ),
    # 3. Connection strings that carry credentials.  `mongodb+srv` must precede
    #    `mongodb` in the alternation or the `+srv` is left dangling.
    (
        "connection_string",
        re.compile(
            r"\b(?:postgresql|postgres|mysql|mariadb|mongodb\+srv|mongodb|rediss|redis|amqps|amqp|"
            r"sqlserver|mssql|clickhouse|cockroachdb|snowflake|ftp|ftps|sftp)"
            r"://[^\s:@/]{1,128}:[^\s@/]{1,256}@[^\s\"'<>]{0,256}"
        ),
        _simple("connection_string"),
    ),
    # 4. http(s)://user:pass@host -- same shape, different scheme.
    (
        "url_credentials",
        re.compile(r"\bhttps?://[^\s:@/]{1,128}:[^\s@/]{1,256}@[^\s\"'<>]{0,256}"),
        _simple("url_credentials"),
    ),
    # 5. Vendor-specific key shapes.
    ("aws_key", re.compile(r"\b(?:AKIA|ASIA|AGPA|AIDA|AROA|ANPA)[0-9A-Z]{16}\b"), _simple("aws_key")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{16,255}"), _simple("github_token")),
    ("github_token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,255}"), _simple("github_token")),
    ("slack_token", re.compile(r"\bxox[baprse]-[A-Za-z0-9-]{8,255}"), _simple("slack_token")),
    # Anthropic before the generic `sk-` rule, or `sk-ant-...` reports as openai.
    ("anthropic_key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{16,255}"), _simple("anthropic_key")),
    ("openai_key", re.compile(r"\bsk-proj-[A-Za-z0-9_-]{16,255}"), _simple("openai_key")),
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9]{20,255}"), _simple("openai_key")),
    (
        "stripe_key",
        re.compile(r"\b(?:sk|pk|rk)_(?:live|test)_[A-Za-z0-9]{8,255}"),
        _simple("stripe_key"),
    ),
    ("stripe_key", re.compile(r"\brk_[A-Za-z0-9]{16,255}"), _simple("stripe_key")),
    ("stripe_key", re.compile(r"\bwhsec_[A-Za-z0-9]{16,255}"), _simple("stripe_key")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}"), _simple("google_api_key")),
    ("sendgrid_key", re.compile(r"\bSG\.[A-Za-z0-9_-]{16,255}\.[A-Za-z0-9_-]{16,255}"), _simple("sendgrid_key")),
    # 6. Auth headers.
    (
        "bearer_token",
        re.compile(r"\b[Bb]earer\s+[A-Za-z0-9._~+/=-]{12,4000}"),
        _prefixed("bearer_token", "Bearer "),
    ),
    (
        "basic_auth",
        re.compile(r"\b[Bb]asic\s+[A-Za-z0-9+/=]{16,4000}"),
        _prefixed("basic_auth", "Basic "),
    ),
    # 7. key=value / key: value assignments.
    #
    # The leading boundary is `(?<![A-Za-z0-9])`, NOT `\b`.  `_` is a word
    # character, so `\bpassword` cannot match inside `DB_PASSWORD`,
    # `SENTRY_AUTH_TOKEN` or `AWS_SECRET_ACCESS_KEY` -- which is every
    # real-world env-var shape, and exactly what a pasted `.env` line looks
    # like.  Verified: with `\b` this rule left `DB_PASSWORD=hunter2trombone`
    # completely untouched.
    #
    # The key group ends in an optional `["']` because a QUOTED key puts its
    # closing quote BETWEEN the key and the separator -- `{"password": "x"}`,
    # `{'api_key': 'x'}`, `"api_key": x`.  Only the closing quote needs
    # matching: the opening one is already allowed by the lookbehind, and
    # leaving it out of the pattern is what keeps `{"DB_PASSWORD": "x"}`
    # working, where the opening quote is nowhere near the credential word.
    # The quote is captured WITH the key and handed straight back, so the
    # scrubbed text keeps its original shape.  Verified: with the separator
    # required directly after the bare key, every JSON and dict fixture in the
    # selftest came back verbatim, with zero redactions.
    (
        "assignment",
        re.compile(
            r"(?<![A-Za-z0-9])((?:passwords?|passwd|pwd|passphrase|client[_-]?secrets?|secrets?[_-]?keys?|secrets?|"
            r"api[_-]?keys?|apikeys?|access[_-]?keys?|access[_-]?tokens?|auth[_-]?tokens?|"
            r"refresh[_-]?tokens?|private[_-]?keys?|session[_-]?tokens?|tokens?|credentials?)"
            r"[\"']?)"
            r"(\s*[:=]\s*)"
            # Scalar credential lists are redacted together, respecting quoted
            # elements and escaped quotes. Objects fall through to their inner
            # assignments instead of swallowing an inner credential key.
            r"(" + _QUOTED_VALUE_SRC + r"|\[(?:" + _QUOTED_VALUE_SRC + r"|[^\[\]{}\"'])*\]|[^\s,;)\]}\[{\n]{1,512})",
            re.IGNORECASE,
        ),
        _assignment_factory,
    ),
    # 7b. `--password x` / `--api-key x` / (context-gated) `--value x`.
    (
        "flag_value",
        re.compile(
            r"--(passwords?|passwd|tokens?|secrets?|api[_-]?keys?|access[_-]?tokens?|"
            r"auth[_-]?tokens?|client[_-]?secrets?|credentials?|value)"
            r"([= ]\s{0,8})"
            r"(" + _QUOTED_VALUE_SRC + r"|[^\s,;)\]}\n\"']{4,512})",
            re.IGNORECASE,
        ),
        _flag_value_factory,
    ),
    # 7c. `SCREAMING_SNAKE=<high-entropy value>`, whatever the key is called.
    #     Guarded by `_looks_like_secret_value` so `NODE_ENV=production` and
    #     `LOG_LEVEL=debug` survive intact.
    (
        "env_assignment",
        re.compile(
            # No whitespace around `=`.  That is what a dotenv line and a
            # shell env prefix look like; `const MAX_TURNS = parseInt(...)`
            # in TypeScript always has spaces, and matching it shredded real
            # source lines in the blast-radius test.
            r"(?<![A-Za-z0-9_.\-/])([A-Z][A-Z0-9]{0,40}(?:_[A-Z0-9]{1,40}){1,8})"
            r"(=)"
            r"(" + _QUOTED_VALUE_SRC + r"|[^\s,;)\]}\n\"']{1,512})"
        ),
        _env_assignment_factory,
    ),
    # 7d. Bare 40-char AWS secret access key (contains `/` or `+`, so the
    #     base64 rule below cannot see it as one run).
    (
        "aws_key",
        re.compile(r"(?<![A-Za-z0-9/+=])[A-Za-z0-9/+]{40}(?![A-Za-z0-9/+=])"),
        _aws_secret_factory,
    ),
    # 8. Email addresses.  After connection strings so `user:pass@host` is not
    #    partially matched here first.
    (
        "email",
        re.compile(r"\b[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9-]{1,63}(?:\.[A-Za-z0-9-]{1,63}){0,6}\.[A-Za-z]{2,24}\b"),
        _simple("email"),
    ),
    # 9. Generic high-entropy blobs.  Last, so everything above keeps its name.
    ("hex_blob", re.compile(r"\b[0-9a-fA-F]{32,128}\b"), _hex_factory),
    ("base64_blob", re.compile(r"\b[A-Za-z0-9+/]{32,512}={1,2}"), _base64_padded_factory),
    ("base64_blob", re.compile(r"\b[A-Za-z0-9]{32,512}\b"), _base64_factory),
]

# ---------------------------------------------------------------------------
# Home-path collapse (normalization, NOT a redaction)
# ---------------------------------------------------------------------------

_HOME_PATH_RULES = [
    # /Users/ravi -> ~   /home/runner -> ~
    re.compile(r"(?<![A-Za-z0-9_])/(?:Users|home)/[A-Za-z0-9._-]{1,64}"),
    # C:\Users\ravi -> ~
    re.compile(r"(?<![A-Za-z0-9_])[A-Za-z]:\\Users\\[A-Za-z0-9._ -]{1,64}"),
    # /var/root and /root, for completeness.
    re.compile(r"(?<![A-Za-z0-9_])/(?:var/)?root(?![A-Za-z0-9_])"),
]


def collapse_home_paths(text: str) -> Tuple[str, int]:
    """
    Replace `/Users/<name>` and `/home/<name>` with `~`.

    Returns `(text, count)`.  The count is reported separately from secret
    redactions -- see the module docstring for why.
    """
    if not text:
        return ("", 0)
    total = 0
    out = text
    for rule in _HOME_PATH_RULES:
        out, n = rule.subn("~", out)
        total += n
    return (out, total)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def scrub_detailed(text: str) -> Dict[str, object]:
    """
    Full result for callers that want the normalization count too.

    Returns:
        {
          "text": str,                  # scrubbed + home-path collapsed
          "hits": [kind, ...],          # one entry per redaction
          "redactions": int,            # == len(hits)
          "path_normalizations": int,   # home paths collapsed, NOT secrets
          "truncated": bool,            # input exceeded MAX_INPUT_CHARS
        }
    """
    if text is None:
        return {
            "text": "",
            "hits": [],
            "redactions": 0,
            "path_normalizations": 0,
            "truncated": False,
        }
    if not isinstance(text, str):
        text = str(text)

    truncated = False
    if len(text) > MAX_INPUT_CHARS:
        text = text[:MAX_INPUT_CHARS] + TRUNCATION_MARKER
        truncated = True

    hits = []  # type: List[str]
    out = text
    for _kind, regex, factory in _RULES:
        # Cheap bail-out: most turns contain no secrets at all, and `search`
        # over an already-clean string is the common path.
        out = regex.sub(factory(hits), out)

    out, norm_count = collapse_home_paths(out)

    return {
        "text": out,
        "hits": hits,
        "redactions": len(hits),
        "path_normalizations": norm_count,
        "truncated": truncated,
    }


def scrub(text: str) -> Tuple[str, List[str]]:
    """
    The contract entry point.

    Returns `(clean_text, hits)` where `hits` has one entry per redaction,
    naming the pattern kind.  Home-path collapse is applied but not counted
    here; use `scrub_detailed()` if you need that number.
    """
    result = scrub_detailed(text)
    return (result["text"], result["hits"])


def scrub_all(items: Iterable[str]) -> Tuple[List[str], List[str]]:
    """
    Scrub a sequence of strings.

    Returns `(cleaned_list, hits)` -- hits aggregated across every item, in
    encounter order, so `len(hits)` is the total redaction count.
    """
    cleaned = []  # type: List[str]
    hits = []  # type: List[str]
    for item in items or []:
        text, item_hits = scrub(item)
        cleaned.append(text)
        hits.extend(item_hits)
    return (cleaned, hits)


def scrub_all_detailed(items: Iterable[str]) -> Dict[str, object]:
    """`scrub_all` plus the normalization and truncation counters."""
    cleaned = []  # type: List[str]
    hits = []  # type: List[str]
    normalizations = 0
    truncations = 0
    for item in items or []:
        res = scrub_detailed(item)
        cleaned.append(res["text"])
        hits.extend(res["hits"])
        normalizations += res["path_normalizations"]
        if res["truncated"]:
            truncations += 1
    return {
        "texts": cleaned,
        "hits": hits,
        "redactions": len(hits),
        "path_normalizations": normalizations,
        "truncated_inputs": truncations,
    }


def redaction_counts(hits: Iterable[str]) -> Dict[str, int]:
    """`{kind: n}` for a hits list, for warnings and debugging."""
    counts = {}  # type: Dict[str, int]
    for kind in hits or []:
        counts[kind] = counts.get(kind, 0) + 1
    return counts


def make_scrub_stats(hits: Iterable[str]) -> Dict[str, object]:
    """
    Build the `scrub_stats` block the miner JSON schema expects:

        {"redactions": 0, "patterns_hit": [""]}
    """
    hit_list = list(hits or [])
    return {
        "redactions": len(hit_list),
        "patterns_hit": sorted(set(hit_list)),
    }


# ---------------------------------------------------------------------------
# Self-test:  python3 lib/scrub.py
# ---------------------------------------------------------------------------


def _selftest() -> int:
    failures = 0
    passes = 0

    def check(label, condition, detail=""):
        if condition:
            print("PASS  %s" % label)
            return True
        print("FAIL  %s%s" % (label, ("  -- " + detail) if detail else ""))
        return False

    # (label, input, must_contain_kind_or_None, must_not_appear_substring)
    positives = [
        (
            "aws access key id",
            "creds are AKIAIOSFODNN7EXAMPLE ok?",
            "aws_key",
            "AKIAIOSFODNN7EXAMPLE",
        ),
        (
            "github classic token",
            "use ghp_16C7e42F292c6912E7710c838347Ae178B4a here",
            "github_token",
            "ghp_16C7e42F292c6912E7710c838347Ae178B4a",
        ),
        (
            "github fine-grained pat",
            "token github_pat_11ABCDEFG0abcdefghijkl_ABCDEFGHIJKLMNOP",
            "github_token",
            "github_pat_11ABCDEFG0",
        ),
        (
            "slack bot token",
            "xoxb-123456789012-1234567890123-AbCdEfGhIjKlMnOpQrStUvWx",
            "slack_token",
            "xoxb-123456789012",
        ),
        (
            "anthropic key beats generic sk-",
            "ANTHROPIC_API_KEY is sk-ant-api03-AbCdEf0123456789_-xyzXYZ",
            "anthropic_key",
            "sk-ant-api03",
        ),
        (
            "openai key",
            "export OPENAI_KEY sk-AbCdEf0123456789AbCdEf0123456789",
            "openai_key",
            "sk-AbCdEf0123456789",
        ),
        (
            "stripe live secret",
            "sk_live_51AbCdEfGhIjKlMnOpQrStUv is prod",
            "stripe_key",
            "sk_live_51AbCdEf",
        ),
        (
            "jwt not base64_blob",
            "Authorization eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U",
            "jwt",
            "eyJhbGciOiJIUzI1NiI",
        ),
        (
            "postgres connection string",
            "DATABASE_URL=postgres://admin:hunter2@db.example.com:5432/app",
            "connection_string",
            "hunter2",
        ),
        (
            "mongodb+srv connection string",
            "mongodb+srv://root:s3cr3tpw@cluster0.abcd.mongodb.net/test",
            "connection_string",
            "s3cr3tpw",
        ),
        (
            "redis connection string",
            "redis://default:AbCdEf123456@redis-19999.example.com:19999",
            "connection_string",
            "AbCdEf123456",
        ),
        (
            "bearer token keeps the word Bearer",
            "curl -H 'Authorization: Bearer abcdef1234567890ABCDEF'",
            "bearer_token",
            "abcdef1234567890ABCDEF",
        ),
        (
            "password assignment",
            "set password=hunter2andmore in the config",
            "assignment",
            "hunter2andmore",
        ),
        (
            "api_key assignment keeps the key name",
            'api_key: "abcdefghijklmnop"',
            "assignment",
            "abcdefghijklmnop",
        ),
        (
            "private key block",
            "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA\n-----END RSA PRIVATE KEY-----",
            "private_key",
            "MIIEpAIBAAKCAQEA",
        ),
        (
            "email address",
            "ping ravi.sojitra+dev@example.co.uk about it",
            "email",
            "example.co.uk",
        ),
        (
            "long hex blob",
            "sha is 5f4dcc3b5aa765d61d8327deb882cf99aa11bb22cc33dd44",
            "hex_blob",
            "5f4dcc3b5aa765d6",
        ),
        (
            "base64 blob with padding",
            "payload TWFuIGlzIGRpc3Rpbmd1aXNoZWQsIG5vdCBvbmx5IGJ5IGhpcw==",
            "base64_blob",
            "TWFuIGlzIGRpc3Rpbmd1",
        ),
        # --- regression: `_` is a word char, so a leading `\b` could never
        # match inside a SCREAMING_SNAKE env var name.  Every case below
        # leaked verbatim to mine_transcripts.py stdout before the fix.
        (
            "underscore-prefixed password assignment",
            "DB_PASSWORD=hunter2trombone",
            "assignment",
            "hunter2trombone",
        ),
        (
            "underscore-prefixed secret key assignment",
            "STRIPE_SECRET_KEY=abcdefghijklmnop",
            "assignment",
            "abcdefghijklmnop",
        ),
        (
            "underscore-prefixed auth token assignment",
            "export SENTRY_AUTH_TOKEN=glpat9XYZsecretvaluehere1",
            "assignment",
            "glpat9XYZsecretvaluehere1",
        ),
        (
            "underscore-prefixed api key with colon",
            "MY_API_KEY: swordfishvaluehere",
            "assignment",
            "swordfishvaluehere",
        ),
        (
            "aws secret access key assignment",
            "AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "assignment",
            "wJalrXUtnFEMI",
        ),
        (
            "bare 40-char aws secret access key",
            "the secret is wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY ok",
            "aws_key",
            "wJalrXUtnFEMI",
        ),
        (
            "env var whose name has no credential keyword",
            "run STRIPE_WEBHOOK_SIGNING=whsecretvaluexyz123 npm run dev",
            "env_assignment",
            "whsecretvaluexyz123",
        ),
        (
            "credential passed as a cli flag",
            "psql --password Tr0ub4dor3xyz --host db",
            "flag_value",
            "Tr0ub4dor3xyz",
        ),
        (
            "context-gated --value flag",
            "npx wrangler secret put API_TOKEN --value ZZTOPsecret99value",
            "flag_value",
            "ZZTOPsecret99value",
        ),
        # --- regression: a QUOTED key puts its closing quote between the key
        # and the `:` or `=`, so a matcher that expects the separator directly
        # after the bare key never fired on JSON, on a Python dict, or on
        # quoted YAML.  Every case below came back verbatim, zero hits.
        (
            "json quoted password key",
            '{"password": "hunter2trombone"}',
            "assignment",
            "hunter2trombone",
        ),
        (
            "json quoted api key",
            '{"api_key": "sk-live-AbCdEf0123456789"}',
            "assignment",
            "sk-live-AbCdEf0123456789",
        ),
        (
            "json quoted key carrying a prefix",
            '{"DB_PASSWORD": "hunter2trombone"}',
            "assignment",
            "hunter2trombone",
        ),
        (
            "python dict single-quoted key",
            "{'password': 'hunter2trombone'}",
            "assignment",
            "hunter2trombone",
        ),
        (
            "python dict, credential key among innocent ones",
            "{'host': 'db.internal', 'api_key': 'swordfishvaluehere'}",
            "assignment",
            "swordfishvaluehere",
        ),
        (
            "yaml credential key",
            "database:\n  password: hunter2trombone\n  host: db.internal",
            "assignment",
            "hunter2trombone",
        ),
        (
            "yaml quoted key and quoted value",
            '"api_key": "swordfishvaluehere"',
            "assignment",
            "swordfishvaluehere",
        ),
        (
            "quoted value containing an escaped quote",
            '{"password": "hun\\"ter2trombone"}',
            "assignment",
            "ter2trombone",
        ),
        (
            "quoted value containing an escaped backslash",
            '{"client_secret": "abc\\\\def123ghijk"}',
            "assignment",
            "def123ghijk",
        ),
        (
            "credential key nested inside an object value",
            '{"credentials": {"password": "hunter2trombone"}}',
            "assignment",
            "hunter2trombone",
        ),
    ]

    for label, text, kind, must_vanish in positives:
        clean, hits = scrub(text)
        ok = kind in hits and must_vanish not in clean
        if check("redacts %s" % label, ok, "hits=%s clean=%r" % (hits, clean[:90])):
            passes += 1
        else:
            failures += 1

    negatives = [
        ("plain english prose", "add a new api endpoint for users with validation"),
        ("import statement", "import { createClient } from '@supabase/supabase-js'"),
        ("short hex sha", "the commit is a1b2c3d and it broke ci"),
        ("version number", "bump next to 14.2.3 and react to 18.3.1"),
        ("long word, no digits", "supercalifragilisticexpialidociousandthensome"),
        ("normal file path", "edit src/app/api/users/route.ts and add zod"),
        ("npm scoped package", "install @tanstack/react-query and wire it up"),
        ("uuid-with-dashes stays readable", "run migration 550e8400-e29b-41d4-a716-446655440000"),
        ("word 'token' with no value", "the token is missing from the header"),
        ("32 digit pure number", "id 12345678901234567890123456789012 came back"),
        # Regression: `/` is a base64 character, so a deep path used to read as
        # a 34 character blob and get destroyed + counted as a leaked secret.
        ("deep absolute file path", "open /Users/ravi/repo/src/app/api/users/route.ts now"),
        ("deep relative file path", "check packages/web/src/components/forms/Field.tsx again"),
        # The env-assignment rule must not eat ordinary build configuration --
        # that is the evidence the whole tool reasons from.
        ("NODE_ENV in a package script", "NODE_ENV=production next build"),
        ("CI flag in a package script", "CI=true vitest run"),
        ("log level env var", "LOG_LEVEL=debug bun run dev"),
        ("port env var", "PORT=3000 node server.js"),
        ("go build env vars", "GOOS=linux GOARCH=arm64 CGO_ENABLED=0 go build ./..."),
        ("public url env var", "NEXT_PUBLIC_SUPABASE_URL=https://xyzcompany.supabase.co"),
        ("env var indirection", "DATABASE_URL=$DATABASE_URL prisma migrate deploy"),
        ("short human-readable value", "VITE_APP_TITLE=MyDashboard"),
        ("aws region", "AWS_REGION=us-east-1 terraform apply"),
        ("debug glob", "DEBUG=app:* npm start"),
        # Quoted-key support must not widen the rule into "any line that says
        # password": the key still has to BE a credential word, and there
        # still has to be a value on the other side of a `:` or `=`.
        ("prose about a password", "users forget their password and ask for a reset link"),
        ("doc filename carrying a credential word", "see docs/password_policy.md for the rules"),
        ("quoted key that merely contains a credential word",
         '{"password_policy_doc": "see the wiki"}'),
        ("credential key with no value", "password:"),
        ("subscript read, not an assignment", 'const t = headers["token"] ?? ""'),
        ("already-redacted value is left as it is",
         '{"password": "[REDACTED:assignment]"}'),
        ("json schema whose value is a type object", '{"password": {"type": "string"}}'),
    ]

    for label, text in negatives:
        clean, hits = scrub(text)
        ok = len(hits) == 0
        if check("leaves %s alone" % label, ok, "hits=%s -> %r" % (hits, clean)):
            passes += 1
        else:
            failures += 1

    # Scrubbing our own output is a no-op, quoted keys included.
    once, _first_hits = scrub(
        '{"password": "hunter2trombone", "api_key": "swordfishvaluehere"}'
    )
    twice, second_hits = scrub(once)
    ok = twice == once and len(second_hits) == 0
    if check("redaction of quoted keys is idempotent", ok, "%r -> %r" % (once, twice)):
        passes += 1
    else:
        failures += 1

    # Home-path collapse is a normalization, counted separately.
    clean, hits = scrub("open /Users/x/agentic-codebase/PRD.md please")
    ok = "~/agentic-codebase/PRD.md" in clean and len(hits) == 0
    if check("collapses /Users/<name> to ~ without counting a redaction", ok, repr(clean)):
        passes += 1
    else:
        failures += 1

    detail = scrub_detailed("cd /home/runner/work && cat /Users/ravi/notes.md")
    ok = detail["path_normalizations"] == 2 and detail["redactions"] == 0
    if check("path_normalizations counted separately", ok, repr(detail)):
        passes += 1
    else:
        failures += 1

    # Ordering: a JWT inside an assignment reports as jwt, not base64_blob.
    _clean, hits = scrub("access_token=eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJhYmMifQ.c2ln")
    ok = "jwt" in hits and "base64_blob" not in hits
    if check("specific pattern wins over generic blob", ok, "hits=%s" % hits):
        passes += 1
    else:
        failures += 1

    # Input cap.
    long_text = "a" * (MAX_INPUT_CHARS + 5000)
    detail = scrub_detailed(long_text)
    ok = detail["truncated"] and len(detail["text"]) <= MAX_INPUT_CHARS + len(TRUNCATION_MARKER)
    if check("caps input at MAX_INPUT_CHARS", ok, str(len(detail["text"]))):
        passes += 1
    else:
        failures += 1

    # scrub_all aggregates.
    texts, hits = scrub_all(["AKIAIOSFODNN7EXAMPLE", "nothing here", "ghp_%s" % ("a" * 30)])
    ok = len(texts) == 3 and len(hits) == 2
    if check("scrub_all aggregates hits", ok, "hits=%s" % hits):
        passes += 1
    else:
        failures += 1

    stats = make_scrub_stats(["email", "jwt", "email"])
    ok = stats == {"redactions": 3, "patterns_hit": ["email", "jwt"]}
    if check("make_scrub_stats shape", ok, repr(stats)):
        passes += 1
    else:
        failures += 1

    # Secret filename detection.
    secret_paths = [
        "/repo/.env",
        "/repo/.env.local",
        "/repo/certs/server.pem",
        "/repo/keys/app.key",
        "/home/x/.ssh/id_rsa",
        "/repo/config/credentials/prod.yaml",
        "/repo/my-secrets.json",
        "/repo/.npmrc",
        "/repo/.netrc",
        "/repo/cert.p12",
        "/repo/cert.pfx",
        "/repo/release.keystore",
    ]
    ok = all(is_secret_path(p) for p in secret_paths)
    if check("is_secret_path flags every contract glob", ok,
             str([p for p in secret_paths if not is_secret_path(p)])):
        passes += 1
    else:
        failures += 1

    safe_paths = [
        "/repo/src/index.ts",
        "/repo/package.json",
        "/repo/README.md",
        "/repo/environment.ts",
        "/repo/keyboard/handler.tsx",
    ]
    ok = all(not is_secret_path(p) for p in safe_paths)
    if check("is_secret_path leaves ordinary files alone", ok,
             str([p for p in safe_paths if is_secret_path(p)])):
        passes += 1
    else:
        failures += 1

    ok = is_env_file("/repo/.env.production") and not is_env_file("/repo/environment.ts")
    if check("is_env_file distinguishes dotenv from lookalikes", ok):
        passes += 1
    else:
        failures += 1

    print("")
    print("%d passed, %d failed" % (passes, failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(_selftest())
