#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agentify :: lib/textnorm.py -- prompt normalization and clustering, shared.

This is the module that turns a pile of raw user turns into the handful of
counted shapes that phase 3 reasons over.  Everything here is deterministic:
same input, same output, byte for byte.  A clustering result that reshuffles
between runs would make the "evidence with a count" claim unverifiable.

Public surface (build contract, "Shared libs"):

    normalize(text)                      -> str
    skeleton(text)                       -> str          verb + object shape
    cluster(prompts, min_count, jaccard) -> [cluster, ...]
    classify_intent(text_or_skeleton)    -> "work" | "meta" | "social"
    meta_topic(text_or_skeleton)         -> None | "time"|"remaining"|"next"|"recap"
    detect_correction(text)              -> None | {"kind", "text", ...}
    extract_commands(text)               -> ["bun test", "npm run lint", ...]
    find_services(text)                  -> [{"name", "count", "aliases"}, ...]
    count_tokens_estimate(s)             -> int          chars / 4
    tokens(s) / jaccard(a, b)            -> helpers used by cluster()

Three deliberate design decisions worth knowing before you edit this file:

1. SKELETONS DROP TECHNOLOGY NAMES.  "add a new API endpoint for /users with
   zod validation" and "add an endpoint with yup validation" are the same
   *shape* of request and belong in one cluster; the specific library is
   detail, and it is already captured by `find_services()`, `tool_mentions`
   and the retained examples.  `DETAIL_TOKENS` holds that list.  If a skeleton
   collapses to fewer than two tokens this way, the detail tokens are put back
   (see `skeleton()`), so "use bun not npm" does not degrade to "use".

2. THIS MODULE DOES NOT SCRUB.  Callers must run `lib.scrub.scrub()` over any
   text BEFORE it reaches a cluster example or a correction, because those
   strings end up in JSON on stdout.  textnorm deliberately does not import
   scrub so the two can be tested and reasoned about independently.

3. INTENT IS A SPLIT, NOT A FILTER.  `classify_intent()` separates status
   questions ("what's remaining?", "how much time?") and turn-taking ("ok",
   "thanks") from actionable requests.  It exists because those three kinds
   of turn ranked against each other produce a top-ten list that is half
   noise -- but a status question asked twenty times is still evidence, so
   the caller reports it in its own list rather than dropping it.

No network. Standard library only. Python 3.9+.
"""

import hashlib
import math
import re
import sys
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set

__all__ = [
    "normalize",
    "skeleton",
    "shape_key",
    "stem",
    "cluster",
    "classify_intent",
    "meta_topic",
    "detect_correction",
    "extract_commands",
    "find_services",
    "find_services_names",
    "count_tokens_estimate",
    "tokens",
    "jaccard",
    "SERVICE_LEXICON",
    "KNOWN_EXECUTABLES",
    "STOPWORDS",
    "DETAIL_TOKENS",
    "VERBS",
    "ACTION_VERBS",
    "SOCIAL_TOKENS",
    "INTENTS",
    "META_TOPICS",
    "META_TOPIC_LABELS",
    "MAX_SKELETON_TOKENS",
    "SHAPE_KEY_TOKENS",
    "MAX_SOCIAL_TOKENS",
    "CORRECTION_KINDS",
]

#: How many tokens a DISPLAYED skeleton keeps.  Was 10, which made the skeleton
#: a near-verbatim bag of content words instead of the "verb + object" shape the
#: build contract asks for; that is what fragmented the clusters.
MAX_SKELETON_TOKENS = 6

#: How many tokens the MERGE KEY keeps.  A request shape is a verb and its
#: object; everything after that is which instance of the request it was.
#: Measured on four real project histories (384 / 221 / 130 / 6 user turns):
#: at 10 tokens 72% of prompts landed in a singleton cluster and hostshare
#: reported 5 shapes from 384 turns.  At 3 the same corpus yields 38 shapes
#: covering 142 turns.
SHAPE_KEY_TOKENS = 3
MAX_INPUT_CHARS = 20000
EXAMPLE_MAX_CHARS = 160

CORRECTION_KINDS = ["tooling", "style", "process", "architecture", "scope"]

#: Kind returned when a correction marker fires but no topic keyword does
#: ("no, that's wrong").  Deliberately the broadest workflow bucket.
CORRECTION_FALLBACK_KIND = "process"


# ---------------------------------------------------------------------------
# normalize()
# ---------------------------------------------------------------------------

# Scrubbing runs before clustering, so `[REDACTED:jwt]` and `[TRUNCATED:input]`
# markers are in the text by the time normalize() sees it.  They must not
# become skeleton tokens ("update component redacted base64 blob").
_SCRUB_MARKER = re.compile(r"\[(?:redacted|truncated):[a-z0-9_-]{1,40}\]", re.IGNORECASE)
_FENCED_CODE = re.compile(r"```[\s\S]{0,20000}?```")
_FENCED_CODE_UNTERMINATED = re.compile(r"```[\s\S]{0,20000}$")
_INLINE_CODE = re.compile(r"`[^`\n]{0,500}`")
_HTML_TAG = re.compile(r"<[^>\n]{0,200}>")
_URL = re.compile(r"\b(?:https?|ftp|file)://[^\s<>\"')\]]{1,500}")
_WWW = re.compile(r"\bwww\.[^\s<>\"')\]]{1,500}")
_DQUOTED = re.compile(r"\"[^\"\n]{0,500}\"")
_SQUOTED = re.compile(r"(?<![A-Za-z])'[^'\n]{1,300}'(?![A-Za-z])")
# Absolute paths: one leading slash then path characters.  A single bounded
# quantifier -- no nesting -- so this cannot backtrack pathologically.
_ABS_PATH = re.compile(r"(?<![A-Za-z0-9_~])[~/][A-Za-z0-9_./@+-]{1,200}")
# Relative paths: at least one internal slash, e.g. src/app/page.tsx
_REL_PATH = re.compile(r"\b[A-Za-z0-9_.-]{1,64}/[A-Za-z0-9_./-]{1,200}")
_FILENAME = re.compile(
    r"\b[A-Za-z0-9_-]{1,64}\."
    r"(?:tsx?|jsx?|mjs|cjs|py|go|rs|rb|java|kts?|swift|m|mm|c|h|hpp|cc|cpp|cs|php|"
    r"sh|bash|zsh|fish|ps1|sql|prisma|graphql|gql|proto|json|ya?ml|toml|ini|cfg|conf|"
    r"env|lock|md|mdx|txt|csv|tsv|xml|html?|css|scss|sass|less|svg|png|jpe?g|gif|webp|"
    r"ico|pdf|zip|tar|gz)\b"
)
_UUID = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b")
_HEXISH = re.compile(r"\b[0-9a-f]{7,64}\b")
# Standalone numbers only; digits welded to letters ("s3", "v1", "oauth2") stay.
_NUMBER = re.compile(r"(?<![A-Za-z0-9])\d[\d.,_:]{0,24}(?![A-Za-z0-9])")
_NON_WORD = re.compile(r"[^a-z0-9\s]+")
_WS = re.compile(r"\s+")


def _has_digit(value: str) -> bool:
    for ch in value:
        if ch.isdigit():
            return True
    return False


def _hexish_sub(match) -> str:
    """Strip hashes but keep hex-lookalike English words ("defaced", "facade")."""
    return " " if _has_digit(match.group(0)) else match.group(0)


def normalize(text: str) -> str:
    """
    Lowercase a prompt and remove everything that is specific to one instance
    of a request: code, URLs, paths, filenames, quoted strings, numbers,
    hashes and UUIDs.  Punctuation collapses to whitespace.

    >>> normalize('Add a new API endpoint for /users with `zod` validation')
    'add a new api endpoint for with validation'
    """
    if not text:
        return ""
    if not isinstance(text, str):
        text = str(text)
    if len(text) > MAX_INPUT_CHARS:
        text = text[:MAX_INPUT_CHARS]

    out = text.lower()
    out = _SCRUB_MARKER.sub(" ", out)
    out = _FENCED_CODE.sub(" ", out)
    out = _FENCED_CODE_UNTERMINATED.sub(" ", out)
    out = _INLINE_CODE.sub(" ", out)
    out = _HTML_TAG.sub(" ", out)
    out = _URL.sub(" ", out)
    out = _WWW.sub(" ", out)
    out = _DQUOTED.sub(" ", out)
    out = _SQUOTED.sub(" ", out)
    out = _ABS_PATH.sub(" ", out)
    out = _REL_PATH.sub(" ", out)
    out = _FILENAME.sub(" ", out)
    out = _UUID.sub(" ", out)
    out = _HEXISH.sub(_hexish_sub, out)
    out = _NUMBER.sub(" ", out)
    out = _NON_WORD.sub(" ", out)
    out = _WS.sub(" ", out)
    return out.strip()


def tokens(text: str) -> List[str]:
    """Normalized whitespace tokens.  Accepts raw or already-normalized text."""
    if not text:
        return []
    return [t for t in normalize(text).split(" ") if t]


def jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    """|A n B| / |A u B|, 0.0 for two empty sets."""
    set_a = a if isinstance(a, (set, frozenset)) else set(a)
    set_b = b if isinstance(b, (set, frozenset)) else set(b)
    if not set_a and not set_b:
        return 0.0
    union = len(set_a | set_b)
    if union == 0:
        return 0.0
    return len(set_a & set_b) / float(union)


def count_tokens_estimate(s: str) -> int:
    """Rough model-token count: characters / 4, rounded up."""
    if not s:
        return 0
    return int(math.ceil(len(s) / 4.0))


# ---------------------------------------------------------------------------
# skeleton()
# ---------------------------------------------------------------------------

#: Head verbs.  Used to find where the actual request starts, so leading
#: politeness ("hey claude could you please...") can be dropped wholesale.
VERBS = frozenset(
    """
    add create make build write update fix refactor remove delete drop rename move
    implement generate run test check verify review deploy release ship migrate
    setup set install uninstall configure debug investigate explain document
    optimize improve change convert integrate wire hook handle support validate
    parse render style design split extract merge revert bump upgrade downgrade
    lint format commit push pull open close publish scaffold init clean cleanup
    audit analyze summarize list show find search replace apply enable disable
    adjust tweak polish port expose connect mock stub seed backfill cache log
    track instrument secure harden rewrite redo undo finish complete continue
    fetch load save export import upload download compare diff inspect profile
    benchmark measure count sort filter group map reduce wrap unwrap normalize
    sync teach walk read look
    """.split()
)

#: Dropped anywhere in a skeleton -- grammar and filler that carries no shape.
STOPWORDS = frozenset(
    """
    a an the and or but if then than that this these those there here it its
    is are am was were be been being do does did done doing has have had having
    will would shall should can could may might must of in on at to for from by as
    into onto out up down over under about per via with? my our your their his
    her we you i they he she them us me all any some each every both either
    neither also just only so such very really quite pretty more most less least
    still yet ever again already now then today tomorrow asap soon later maybe
    probably basically simply actually literally obviously please pls thanks
    thank ok okay yeah yep sure hey hi hello etc eg ie redacted truncated
    one two three four five
    six seven eight nine ten first second third next last other another same
    thing things stuff bit lot lots kind sort way ways
    new old current existing whole entire above below following given
    """.replace("with?", "").split()
)

#: Politeness and framing that only ever appears in front of the real request.
LEADING_FILLER = frozenset(
    """
    please pls can could would will you i we they lets let us need needs want
    wants help me try trying just also first now then actually kindly quickly
    hey hi hello yo hmm um uh ok okay alright sorry my our the a an this that
    there it is are was were be to do does did should would could shall might
    have has had gonna wanna like really very still again maybe possible
    possibly quick quickly small little bit one more another next
    """.split()
)

#: Technology names.  Dropped from skeletons so that shape clusters do not
#: fragment by library.  Extend freely -- this list is precision, not truth.
_DETAIL_TOKEN_SEED = """
    zod yup joi valibot ajv superstruct pydantic marshmallow
    tailwind tailwindcss shadcn radix mui chakra bootstrap antd daisyui
    eslint prettier biome ruff flake8 pylint mypy pyright tsc
    webpack vite esbuild rollup babel swc turbopack parcel metro
    npm yarn pnpm bun bunx npx pip poetry uv pipenv conda cargo gradle maven
    docker dockerfile kubernetes k8s helm terraform ansible pulumi
    graphql trpc grpc protobuf openapi swagger
    axios lodash ramda dayjs moment zustand redux jotai recoil mobx tanstack swr
    jest vitest mocha chai sinon rspec pytest unittest junit testify
    express fastify koa hapi nestjs django flask fastapi rails laravel sinatra
    spring gin echo fiber actix rocket
    react preact vue svelte sveltekit angular nextjs nuxt remix astro gatsby
    solidjs qwik ember backbone jquery
    expo flutter tauri electron capacitor ionic
    prisma drizzle sequelize typeorm knex sqlalchemy alembic mongoose
    supabase firebase clerk auth0 nextauth betterauth
    stripe twilio resend sendgrid posthog sentry datadog segment mixpanel
    vercel netlify cloudflare wrangler railway render fly heroku
    playwright cypress selenium puppeteer storybook chromatic
    redis memcached elasticsearch opensearch kafka rabbitmq
    postgres postgresql mysql sqlite mongodb dynamodb
    linear jira notion slack asana clickup trello figma
    openai anthropic claude gpt gemini llama ollama langchain
    revenuecat adapty superwall
"""
DETAIL_TOKENS = frozenset(_DETAIL_TOKEN_SEED.split())

#: Connectors that must not be left dangling at either end of a skeleton.
_EDGE_CONNECTORS = frozenset(
    "with without and or for to in on at from by into of that not than as but so "
    "using via across between".split()
)

_KEBAB = re.compile(r"[^a-z0-9]+")


def _filter_tokens(raw: Sequence[str], drop_detail: bool) -> List[str]:
    """
    Content tokens, in order, each kept once.

    De-duplication is global, not just adjacent: "fix all the data ... fix all
    the other things. fix if anything" produced the skeleton "fix data company
    task completed fix", and a label that says the same word twice reads as a
    bug in the tool.
    """
    out = []  # type: List[str]
    seen = set()  # type: Set[str]
    for token in raw:
        if len(token) < 2:
            continue
        if token in STOPWORDS:
            continue
        if drop_detail and token in DETAIL_TOKENS:
            continue
        if token in seen:
            continue
        seen.add(token)
        out.append(token)
    return out


def _trim_edges(items: List[str]) -> List[str]:
    start = 0
    end = len(items)
    while start < end and items[start] in _EDGE_CONNECTORS:
        start += 1
    while end > start and items[end - 1] in _EDGE_CONNECTORS:
        end -= 1
    return items[start:end]


def skeleton(text: str) -> str:
    """
    Reduce a prompt to its verb+object shape.

    >>> skeleton("Add a new API endpoint for /users with zod validation")
    'add api endpoint with validation'
    >>> skeleton("could you please write unit tests for the auth service")
    'write unit tests auth service'

    The leading run of politeness is dropped by jumping to the first head verb
    (searched within the first 8 tokens); when no verb is present the leading
    filler is stripped token by token instead.  Result is capped at
    MAX_SKELETON_TOKENS.
    """
    raw = normalize(text).split(" ")
    raw = [t for t in raw if t]
    if not raw:
        return ""

    # Jump to the head verb when there is one near the front.
    start = 0
    for index, token in enumerate(raw[:8]):
        if token in VERBS:
            start = index
            break
    else:
        limit = min(len(raw), 8)
        while start < limit and raw[start] in LEADING_FILLER:
            start += 1
    body = raw[start:]
    if not body:
        body = raw

    picked = _trim_edges(_filter_tokens(body, drop_detail=True))

    # Guard: a prompt that is *only* technology names ("use bun not npm")
    # must not collapse to a one-word skeleton that over-merges with
    # everything else.  Put the detail tokens back.
    if len(picked) < 2:
        picked = _trim_edges(_filter_tokens(body, drop_detail=False))
    if len(picked) < 1:
        picked = _trim_edges(_filter_tokens(raw, drop_detail=False))
    if not picked:
        return ""

    return " ".join(picked[:MAX_SKELETON_TOKENS])


# ---------------------------------------------------------------------------
# shape_key() -- the merge key
#
# `skeleton()` is what a human reads.  `shape_key()` is what the clusterer
# compares, and it is deliberately blunter: stemmed, and cut to the verb and
# its object.  Without it, "is anything remains to be done now?", "...before we
# commit this?" and "...for this stripe integration phase?" are three separate
# one-off clusters instead of one recurring status check with a count of three,
# which is the difference between evidence and noise.
# ---------------------------------------------------------------------------

#: Irregulars worth hard-coding; everything else goes through suffix rules.
_IRREGULAR_STEMS = {
    "is": "be", "are": "be", "was": "be", "were": "be",
    "has": "have", "had": "have", "does": "do", "did": "do",
}


def stem(token: str) -> str:
    """
    Cheap, conservative suffix stemmer -- plural, `-ing` and `-ed` only.

    It exists so "commit"/"commits"/"committed"/"committing" and
    "remains"/"remaining" land on one merge key.  It is not linguistically
    correct and does not need to be: the output is a hash bucket, never shown
    to the user (the cluster is labelled with a real skeleton instead).

    >>> stem("remaining"), stem("commits"), stem("tests")
    ('remain', 'commit', 'test')
    """
    if not token:
        return ""
    if token in _IRREGULAR_STEMS:
        return _IRREGULAR_STEMS[token]
    if len(token) <= 4:
        return token
    if token.endswith("ies") and len(token) > 5:
        return token[:-3] + "y"
    if token.endswith(("sses", "shes", "ches", "xes")):
        return token[:-2]
    if token.endswith("s") and not token.endswith(("ss", "us", "is")):
        token = token[:-1]
    if token.endswith("ing") and len(token) > 6:
        base = _undouble(token[:-3])
        if len(base) > 3:
            return base
    if token.endswith("ed") and len(token) > 5:
        base = _undouble(token[:-2])
        if len(base) > 3:
            return base
    return token


def _undouble(base: str) -> str:
    """"committ" -> "commit"; leaves "call", "pass", "buzz" alone."""
    if len(base) > 2 and base[-1] == base[-2] and base[-1] not in "lsz":
        return base[:-1]
    return base


#: Key tokens too common to justify a merge on their own.  Two keys that share
#: only these are not the same request: "fix auth bug" and "fix layout bug"
#: overlap on {fix, bug} and would otherwise collapse into one meaningless
#: "fix bug" cluster -- the exact over-merge this module has to avoid.  At
#: least one shared token must sit OUTSIDE this set.
_LOW_INFO_KEY_TOKENS = frozenset(
    """
    fix bug issue problem error broken add update change make create build
    run need want work do get give take put set keep use help let look
    show tell check code file app thing part piece stuff
    read write see know think say said ask tell start finish
    don doesn didn isn aren wasn weren won wouldn couldn shouldn hasn haven
    hadn cant dont ain
    """.split()
)


def _key_from_skeleton(shape: str, limit: int = SHAPE_KEY_TOKENS) -> str:
    """Stem an already-built skeleton down to the merge key."""
    out = []  # type: List[str]
    previous = None
    for word in (shape or "").split(" "):
        if not word:
            continue
        stemmed = stem(word)
        if not stemmed or stemmed == previous:
            continue
        out.append(stemmed)
        previous = stemmed
    out = _trim_edges(out)
    return " ".join(out[:limit])


def shape_key(text: str, limit: int = SHAPE_KEY_TOKENS) -> str:
    """
    The merge key for a raw prompt.

    >>> shape_key("commit the staged changes")
    'commit stag change'
    >>> shape_key("is anything remains to be done before we commit this?")
    'anyth remain before'
    """
    return _key_from_skeleton(skeleton(text), limit)


# ---------------------------------------------------------------------------
# cluster()
# ---------------------------------------------------------------------------


def _coerce_item(item: Any, index: int) -> Optional[Dict[str, Any]]:
    """
    Accept a plain string, a `(text, session_id, timestamp)` tuple, or a dict
    with `text` / `prompt`, `session_id` / `session`, `timestamp` / `ts`.
    """
    text = ""
    session_id = None
    timestamp = None
    if item is None:
        return None
    if isinstance(item, str):
        text = item
    elif isinstance(item, dict):
        text = item.get("text") or item.get("prompt") or item.get("content") or ""
        session_id = item.get("session_id") or item.get("session") or item.get("sessionId")
        timestamp = item.get("timestamp") or item.get("ts") or item.get("time")
    elif isinstance(item, (tuple, list)):
        if len(item) > 0:
            text = item[0] or ""
        if len(item) > 1:
            session_id = item[1]
        if len(item) > 2:
            timestamp = item[2]
    else:
        text = str(item)
    if not isinstance(text, str) or not text.strip():
        return None
    return {
        "text": text,
        "session_id": session_id,
        "timestamp": timestamp,
        "_idx": index,
    }


def _cluster_id(shape: str) -> str:
    """Stable, human-readable id: first four tokens plus a short digest."""
    digest = hashlib.sha1(shape.encode("utf-8")).hexdigest()[:6]
    slug = _KEBAB.sub("-", shape).strip("-")
    parts = [p for p in slug.split("-") if p][:4]
    prefix = "-".join(parts) if parts else "shape"
    if len(prefix) > 48:
        prefix = prefix[:48].rstrip("-")
    return "%s-%s" % (prefix, digest)


def _example_text(text: str) -> str:
    collapsed = _WS.sub(" ", text or "").strip()
    if len(collapsed) > EXAMPLE_MAX_CHARS:
        return collapsed[: EXAMPLE_MAX_CHARS - 1].rstrip() + "…"
    return collapsed


def cluster(
    prompts: Iterable[Any],
    min_count: int = 2,
    jaccard_threshold: float = 0.5,
    max_examples: int = 2,
    max_session_ids: int = 25,
) -> List[Dict[str, Any]]:
    """
    Group prompts by request shape.

    Two passes:
      1. exact buckets on `shape_key()` -- the stemmed verb+object form, so
         "commit the staged changes" and "commit staged change" are one bucket;
      2. near-duplicate merge -- buckets whose keys share at least two tokens
         AND have Jaccard >= `jaccard_threshold`, or where one key's tokens are
         a subset of the other's, fold into the larger bucket.

    The `skeleton` reported for a cluster is the most frequent real skeleton
    inside it, never the stemmed key: "commit staged changes", not
    "commit stag change".

    Two shared tokens are required before Jaccard is consulted.  Without that
    guard a two-token key merges with a three-token key on one word in common,
    and "fix layout" swallows "fix auth".

    Determinism: buckets are sorted by `(-count, skeleton)` before merging and
    each bucket folds into the FIRST accepted representative it matches, so
    the result never depends on dict insertion order or on the order the
    caller happened to read session files in.

    Returns, sorted by `(-count, skeleton)`:

        {
          "id": "add-new-api-endpoint-3f2a1b",
          "skeleton": "add new api endpoint with validation",
          "count": 7,
          "sessions": 4,
          "session_ids": ["...", ...],       # capped
          "first_seen": "2026-06-01T...",
          "last_seen": "2026-08-30T...",
          "examples": ["...", "..."],        # <= max_examples, <=160 chars
          "variants": ["add api endpoint with validation", ...]
        }

    NOTE: `examples` are echoed straight from the input.  Scrub before calling.
    """
    if min_count < 1:
        min_count = 1
    try:
        threshold = float(jaccard_threshold)
    except (TypeError, ValueError):
        threshold = 0.6

    coerced = []  # type: List[Dict[str, Any]]
    for index, item in enumerate(prompts or []):
        entry = _coerce_item(item, index)
        if entry is not None:
            coerced.append(entry)
    if not coerced:
        return []

    buckets = {}  # type: Dict[str, List[Dict[str, Any]]]
    labels = {}  # type: Dict[str, Dict[str, int]]
    for entry in coerced:
        shape = skeleton(entry["text"])
        if not shape:
            continue
        key = _key_from_skeleton(shape)
        if not key:
            continue
        buckets.setdefault(key, []).append(entry)
        tally = labels.setdefault(key, {})
        tally[shape] = tally.get(shape, 0) + 1
    if not buckets:
        return []

    # Deterministic merge order: biggest bucket first, then the most GENERAL
    # key (fewest tokens), then alphabetical.  Generality first matters: it
    # makes "anyth remain" the representative that "anyth remain before" and
    # "anyth remain integration" fold into, rather than the reverse.
    ordered = sorted(
        buckets.items(), key=lambda kv: (-len(kv[1]), len(kv[0].split(" ")), kv[0])
    )

    reps = []  # type: List[Dict[str, Any]]
    for key, entries in ordered:
        key_tokens = set(key.split(" "))
        target = None
        for rep in reps:
            overlap = key_tokens & rep["tokens"]
            if len(overlap) < 2:
                continue
            if not (overlap - _LOW_INFO_KEY_TOKENS):
                continue
            if jaccard(key_tokens, rep["tokens"]) >= threshold:
                target = rep
                break
            # Containment: a shorter key that is wholly inside a longer one is
            # the same request stated with more detail.
            if key_tokens <= rep["tokens"] or rep["tokens"] <= key_tokens:
                target = rep
                break
        if target is None:
            reps.append(
                {
                    "key": key,
                    "tokens": key_tokens,
                    "entries": list(entries),
                    "labels": dict(labels.get(key) or {}),
                    "variants": [],
                }
            )
        else:
            target["entries"].extend(entries)
            target["variants"].append(key)
            for shape, hits in (labels.get(key) or {}).items():
                target["labels"][shape] = target["labels"].get(shape, 0) + hits

    # Label each cluster with the most frequent real skeleton it contains;
    # ties go to the shortest, then alphabetical, so the label reads as a shape
    # and not as one member's full sentence.
    for rep in reps:
        rep["skeleton"] = sorted(
            rep["labels"].items(), key=lambda kv: (-kv[1], len(kv[0]), kv[0])
        )[0][0]

    out = []  # type: List[Dict[str, Any]]
    for rep in reps:
        label = rep["skeleton"]
        # Examples that match the label first, so the quote a reader sees is a
        # member of the shape the cluster is named after and not whichever turn
        # happened to be read first.
        entries = sorted(
            rep["entries"],
            key=lambda e: (0 if skeleton(e["text"]) == label else 1, e["_idx"]),
        )
        count = len(entries)
        if count < min_count:
            continue

        session_ids = []  # type: List[str]
        seen_sessions = set()  # type: Set[str]
        stamps = []  # type: List[str]
        examples = []  # type: List[str]
        seen_examples = set()  # type: Set[str]
        for entry in entries:
            session_id = entry.get("session_id")
            if session_id:
                session_id = str(session_id)
                if session_id not in seen_sessions:
                    seen_sessions.add(session_id)
                    session_ids.append(session_id)
            stamp = entry.get("timestamp")
            if stamp:
                stamps.append(str(stamp))
            if len(examples) < max_examples:
                example = _example_text(entry["text"])
                key = example.lower()
                if example and key not in seen_examples:
                    seen_examples.add(key)
                    examples.append(example)

        out.append(
            {
                "id": _cluster_id(rep["skeleton"]),
                "skeleton": rep["skeleton"],
                "count": count,
                "sessions": len(seen_sessions),
                "session_ids": session_ids[:max_session_ids],
                "first_seen": min(stamps) if stamps else "",
                "last_seen": max(stamps) if stamps else "",
                "examples": examples,
                # The other real skeletons that were folded in -- the evidence
                # that this cluster is one request stated several ways.
                "variants": sorted(
                    shape for shape in rep["labels"] if shape != rep["skeleton"]
                )[:5],
            }
        )

    out.sort(key=lambda c: (-c["count"], c["skeleton"]))
    return out


# ---------------------------------------------------------------------------
# classify_intent()
#
# Not every user turn is a request for work, and the ones that are not do not
# belong in the same list as the ones that are.
#
# Measured on a real 81-session history: four of the top ten request shapes
# were the SAME non-actionable status question stated four ways -- "how much
# time" (8), "what remaining" (5), "how many remaining" (4), "anything
# remains" (3) -- and a fifth was "tell me what should we be working on next"
# (5).  Half the headline evidence mapped to no artifact in mapping-rules.md,
# and the model running phase 3 had to exclude it by judgement, with no rule
# to point at.
#
# The fix is to SEPARATE, never to delete.  A developer who asks for status
# twenty times is real evidence -- for a status/standup skill -- it is just
# not the same KIND of evidence as "commit the staged changes", and merging
# the two kinds into one ranked list is what made the ranking useless.
#
#   work    an actionable request.  Everything that is not meta or social.
#   meta    a status or progress question with no work verb: what is done,
#           what remains, how many are left, how much time, is anything left,
#           what should we do next, are we finished, summarize progress,
#           what did you just do.
#   social  greetings, thanks, acknowledgements, "ok", "continue", "yes".
#
# Accepts either a raw user turn or an already-built skeleton, because the
# miner classifies raw prose and the selftests (and any future audit pass)
# want to be able to sanity-check a label.  Everything is word-boundary
# matched -- no substring tests -- so "notime" is not "no time" and "already"
# is not "ready".
# ---------------------------------------------------------------------------

#: The complete label set.  Nothing else is ever returned.
INTENTS = ("work", "meta", "social")

#: Canonical meta topics, in match priority order.  Two questions with the
#: same topic are the same question: the miner groups on this, which is what
#: collapses four "what is left?" clusters into one counted row.
META_TOPICS = ("time", "recap", "remaining", "next")

#: Human-readable gloss per topic, for callers that want to label a group
#: without picking one member's wording.
META_TOPIC_LABELS = {
    "time": "how much time is left",
    "recap": "what did you just do",
    "remaining": "what work remains",
    "next": "what should we do next",
}

_APOSTROPHE = re.compile(r"[‘’ʼ']")
_INTENT_NON_WORD = re.compile(r"[^a-z0-9]+")


def _intent_text(value: Any) -> str:
    """
    Lowercase, drop apostrophes, and turn every other non-word character into
    a single space.  `"What's done, what's remaining?"` becomes
    `"whats done whats remaining"`, so every pattern below can rely on `\\b`
    and on contractions having exactly one spelling.
    """
    if not value:
        return ""
    if not isinstance(value, str):
        value = str(value)
    if len(value) > MAX_INPUT_CHARS:
        value = value[:MAX_INPUT_CHARS]
    lowered = _APOSTROPHE.sub("", value.lower())
    return _INTENT_NON_WORD.sub(" ", lowered).strip()


#: `(topic, regex)` in priority order; the first hit wins.  Patterns run over
#: `_intent_text()` output, so they are already lowercase and punctuation-free
#: -- which is also why the "same clause" bound is a character count and not
#: `[^.?!]`.  A pattern that reaches across a sentence boundary is caught by
#: the action-verb veto below instead.
_META_PATTERNS = [
    # -- how long is this going to take -------------------------------------
    ("time", re.compile(r"\bhow (?:much|many|long)\b.{0,24}\b(?:time|hours?|hrs?|minutes?|mins?|days?|weeks?)\b")),
    ("time", re.compile(r"\bhow (?:much )?longer\b")),
    ("time", re.compile(r"\bhow long\b.{0,32}\b(?:take|takes|taking|until|left|more|before|to go)\b")),
    ("time", re.compile(r"\bhow much more\b")),
    ("time", re.compile(r"\b(?:eta|time (?:left|remaining|estimate))\b")),
    # -- what did you just do -----------------------------------------------
    (
        "recap",
        re.compile(
            r"\bwhat (?:did|have|has) (?:you|we|u)\b.{0,24}\b(?:do|done|doing|change|"
            r"changed|built|added|finished)\b"
        ),
    ),
    ("recap", re.compile(r"\bwhat (?:just )?(?:happened|changed|broke)\b")),
    ("recap", re.compile(r"\bsummar(?:ize|ise|y)\b.{0,32}\b(?:progress|status|change|changes|work|done|so far|what)\b")),
    ("recap", re.compile(r"\brecap\b")),
    ("recap", re.compile(r"\bwhat (?:was|were) (?:the )?(?:change|changes|done)\b")),
    # -- what is done / what is left ----------------------------------------
    ("remaining", re.compile(r"\bwhats?\b.{0,40}\b(?:remain|remains|remaining|left|pending|outstanding)\b")),
    ("remaining", re.compile(r"\bwhats?\b.{0,30}\b(?:done|complete|completed|finished)\b")),
    ("remaining", re.compile(r"\bhow (?:many|much)\b.{0,40}\b(?:remain|remains|remaining|left|pending|done|complete|completed|finished)\b")),
    ("remaining", re.compile(r"\banything\b.{0,24}\b(?:remain|remains|remaining|left|pending|missing)\b")),
    ("remaining", re.compile(r"\b(?:is|are) (?:there )?anything (?:else )?\b")),
    ("remaining", re.compile(r"\bare we (?:all )?(?:done|complete|completed|finished)\b")),
    ("remaining", re.compile(r"\b(?:is|are) (?:it|this|that|they|everything|all|we|the)(?: \w+){0,2} (?:all )?(?:done|complete|completed|finished)\b")),
    ("remaining", re.compile(r"\beverything (?:is )?(?:done|complete|completed|finished)\b")),
    ("remaining", re.compile(r"\bwhere (?:are we|do we stand)\b")),
    ("remaining", re.compile(r"\bhow far (?:along|are we)\b")),
    ("remaining", re.compile(r"\bwhats? (?:the )?(?:status|progress)\b")),
    ("remaining", re.compile(r"\b(?:status|progress) (?:update|check|report|so far)\b")),
    # -- what should i pick up ----------------------------------------------
    (
        "next",
        re.compile(
            r"\bwhat (?:should|shall|do|does|can|could|would|will|must) (?:i|we|you|they)\b"
            r".{0,32}\b(?:next|start|starting|do|doing|work|working|tackle|pick|"
            r"prioriti[sz]e|focus|begin)\b"
        ),
    ),
    ("next", re.compile(r"\bwhats? (?:the )?next (?:step|steps|task|tasks|thing|things|one|move)\b")),
    ("next", re.compile(r"\bwhats? next\b")),
    ("next", re.compile(r"\bwork(?:ing)? on next\b")),
    ("next", re.compile(r"\bwhere (?:should|do|shall) (?:i|we) (?:start|begin)\b")),
    ("next", re.compile(r"\bwhich (?:one|task|tasks|thing) (?:should|do|shall) (?:i|we)\b")),
]

#: Base-form action verbs.  A status question that ALSO asks for work is a
#: work turn -- "what's left? also add the logout button" is a request.
#:
#: Deliberately BASE FORMS ONLY.  An imperative is uninflected ("fix the
#: header"), while an inflected form is almost always description or
#: reference ("review previous commits", "the completed tasks"), and treating
#: those as work vetoes would push genuine status questions back into
#: `request_shapes` -- the exact defect this function exists to fix.
ACTION_VERBS = frozenset(
    """
    add create build make write implement generate scaffold init setup install
    uninstall configure fix repair patch resolve debug refactor rewrite simplify
    optimize update change modify edit adjust tweak replace rename move remove
    delete drop migrate deploy release ship publish push commit merge rebase
    revert undo bump upgrade downgrade integrate wire connect extract split
    render seed backfill instrument harden run execute lint format typecheck
    """.split()
)

#: A verb behind one of these is a time reference, not an order: "is anything
#: remains to be done BEFORE WE COMMIT this?" is a status question that happens
#: to name `commit`, and vetoing on it would put the single most-repeated meta
#: shape back in the work list.
#:
#: `to` is deliberately NOT here.  It was, and it read "what do i need to do TO
#: CREATE a dynamic workflow node?" as a status question -- an infinitive after
#: a status question is usually the work being asked for.  The cost is that
#: "what's remaining to fix?" now counts as work, which is the safe direction:
#: an ambiguous turn belongs in `request_shapes`, where it is visible, not in
#: `meta_queries`, where it is filed away as small talk.
_SUBORDINATORS = frozenset(
    "before after once when until while since unless whenever although though whether than".split()
)

_PRONOUNS = frozenset("i we you they it he she".split())

#: Pure turn-taking.  A turn made only of these (plus grammar glue) is social.
SOCIAL_TOKENS = frozenset(
    """
    ok okay okey oki kk k alright fine cool great awesome perfect nice good excellent
    thanks thank thanx thx ty tysm cheers appreciate appreciated
    yes yeah yep yup yea ya sure absolutely definitely certainly right correct exactly
    no nope nah
    hi hello hey yo hola sup morning evening
    continue continued proceed resume carry going ahead go keep
    done finished complete completed noted understood ack acknowledged
    lgtm sounds sound np bye later gotcha got
    please pls now again also just still
    """.split()
)

#: Grammar glue ignored when deciding whether a turn is ONLY social.
_SOCIAL_IGNORE = frozenset(
    "a an the it this that to for of on in and but so then you i we me us my your".split()
)

#: Past this many tokens a turn is saying something, whatever words it uses.
MAX_SOCIAL_TOKENS = 6


def _has_action_verb(prepared: str) -> bool:
    """True when `prepared` carries a base-form action verb used as an order."""
    parts = prepared.split(" ")
    for index, token in enumerate(parts):
        if token not in ACTION_VERBS:
            continue
        previous = parts[index - 1] if index >= 1 else ""
        before = parts[index - 2] if index >= 2 else ""
        if previous in _SUBORDINATORS:
            continue
        if previous in _PRONOUNS and before in _SUBORDINATORS:
            continue
        return True
    return False


def _meta_topic_prepared(prepared: str) -> Optional[str]:
    if not prepared:
        return None
    for topic, regex in _META_PATTERNS:
        if regex.search(prepared) is not None:
            if _has_action_verb(prepared):
                return None
            return topic
    return None


def meta_topic(text_or_skeleton: Any) -> Optional[str]:
    """
    Which status question is this, if it is one at all?

    Returns a member of `META_TOPICS`, or None when the turn is not a status
    question (or is one that also asks for work).  Callers group on the return
    value: it is what makes "how many remaining", "what's remaining" and "is
    anything remains to be done" one counted row instead of three.

    >>> meta_topic("is anything remains to be done before we commit this?")
    'remaining'
    >>> meta_topic("how much more time?")
    'time'
    >>> meta_topic("commit the staged changes") is None
    True
    """
    return _meta_topic_prepared(_intent_text(text_or_skeleton))


def _is_social(prepared: str) -> bool:
    parts = [token for token in prepared.split(" ") if token]
    if not parts or len(parts) > MAX_SOCIAL_TOKENS:
        return False
    meaningful = [token for token in parts if token not in _SOCIAL_IGNORE]
    if not meaningful:
        return True
    return all(token in SOCIAL_TOKENS for token in meaningful)


def classify_intent(text_or_skeleton: Any) -> str:
    """
    Sort one user turn into `"work"`, `"meta"` or `"social"`.

    >>> classify_intent("commit the staged changes")
    'work'
    >>> classify_intent("how much more time?")
    'meta'
    >>> classify_intent("thanks!")
    'social'

    Meta is tested before social so a short status question is never eaten by
    the acknowledgement list ("are we done?" is meta, "done" is social).  An
    empty or whitespace-only input is `"social"`: it is certainly not a
    request, and the miner counts it in the dropped-turns stat.
    """
    prepared = _intent_text(text_or_skeleton)
    if not prepared:
        return "social"
    if _meta_topic_prepared(prepared) is not None:
        return "meta"
    if _is_social(prepared):
        return "social"
    return "work"


# ---------------------------------------------------------------------------
# detect_correction()
# ---------------------------------------------------------------------------

# Strong markers: any single one of these makes the turn a correction.
_STRONG_MARKERS = [
    ("no", re.compile(r"(?:^|[\s\"'(])no\s*[,.!:;]", re.IGNORECASE)),
    ("no", re.compile(r"^\s*no\b", re.IGNORECASE)),
    ("dont", re.compile(r"\bdon'?t\b", re.IGNORECASE)),
    ("do not", re.compile(r"\bdo not\b", re.IGNORECASE)),
    ("stop", re.compile(r"\bstop\b", re.IGNORECASE)),
    ("never", re.compile(r"\bnever\b", re.IGNORECASE)),
    ("always", re.compile(r"\balways\b", re.IGNORECASE)),
    ("we use", re.compile(r"\bwe (?:use|prefer|do)\b", re.IGNORECASE)),
    ("we don't use", re.compile(r"\bwe (?:don'?t|do not|never)\b", re.IGNORECASE)),
    ("instead of", re.compile(r"\binstead of\b", re.IGNORECASE)),
    ("instead", re.compile(r"\binstead\b", re.IGNORECASE)),
    ("not x, use y", re.compile(r"\bnot\s+[A-Za-z0-9_.@/-]{1,40}\s*[,.;]?\s*use\b", re.IGNORECASE)),
    ("i told you", re.compile(r"\bi (?:already )?(?:told|asked) you\b", re.IGNORECASE)),
    ("i said", re.compile(r"\b(?:as|like) i said\b", re.IGNORECASE)),
    ("that's wrong", re.compile(r"\b(?:that'?s|this is|it'?s)\s+(?:wrong|incorrect|not right)\b", re.IGNORECASE)),
    ("wrong", re.compile(r"\bwrong\b", re.IGNORECASE)),
    ("incorrect", re.compile(r"\bincorrect\b", re.IGNORECASE)),
    ("revert", re.compile(r"\brevert\b", re.IGNORECASE)),
    ("undo", re.compile(r"\bundo\b", re.IGNORECASE)),
    ("no need", re.compile(r"\bno need\b", re.IGNORECASE)),
    ("why did you", re.compile(r"\bwhy (?:did|are) you\b", re.IGNORECASE)),
]

# "again" on its own is ordinary English ("run it again").  It only signals a
# correction when it follows a repetition cue in the same clause.
_AGAIN_MARKER = re.compile(
    r"\b(?:said|told|asked|repeat|repeated|repeating|mentioned|doing|did|keep|keeps|"
    r"kept|same|wrong|failed|broke|broken|happening|happened)\b[^.!?\n]{0,60}\bagain\b",
    re.IGNORECASE,
)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?\n])\s+")

_KIND_KEYWORDS = {
    "tooling": """
        npm yarn pnpm bun bunx npx pip poetry uv pipenv conda cargo gem bundler brew
        make just docker compose kubectl helm terraform cli command commands script
        scripts install installed package packages dependency dependencies library
        libraries lib sdk tool tools toolchain runtime node deno python ruby java
        binary version env jest vitest pytest mocha rspec playwright cypress webpack
        vite esbuild tsc prisma drizzle orm framework react next vue svelte django
        flask rails flag flags
    """,
    "style": """
        naming name names rename camelcase snakecase kebab casing capitalize
        formatting format indentation indent semicolon semicolons quotes prettier
        eslint biome comment comments commented docstring jsdoc style styling tabs
        spaces wording typo verbose concise readable readability emoji emojis
        docblock header footer whitespace linebreak
    """,
    "process": """
        test tests testing commit commits committing branch branches pr prs pull
        request merge rebase push pushed ci cd pipeline review reviewed changelog
        release releases deploy deployment staging production ticket issue approval
        checklist tdd coverage workflow process gate verify verification
    """,
    "architecture": """
        layer layers layering architecture folder folders directory directories
        structure module modules pattern patterns abstraction repository service
        services controller controllers component components hook hooks middleware
        boundary boundaries import imports coupling separation schema model models
        migration migrations endpoint endpoints route routes state context provider
        interface interfaces type types generic generics belongs live lives placed
        placement organize organized colocate colocated
    """,
    "scope": """
        scope stop only minimal minimum less smaller simpler simplest overkill extra
        unnecessary unneeded revert undo remove delete skip focus enough small
        nothing else later premature
    """,
}

_COMPILED_KIND_KEYWORDS = {}
for _kind, _words in _KIND_KEYWORDS.items():
    _COMPILED_KIND_KEYWORDS[_kind] = frozenset(_words.split())

# Phrases that push a turn firmly into "scope" even when other topics appear.
# Deliberately excludes the bare "don't add X" -- that turn is about X (style,
# tooling, architecture), not about how much work to do.
_SCOPE_BOOST = re.compile(
    r"\b(?:stop|revert|undo|no need|too much|out of scope|overkill|"
    r"keep it (?:simple|small)|nothing else|only do|just do)\b",
    re.IGNORECASE,
)

# Tie-break order when two kinds score the same.
_KIND_PRIORITY = ["scope", "tooling", "process", "architecture", "style"]


def _classify_correction(text: str, fallback: Optional[str] = None) -> str:
    """
    Pick the rule kind.

    Classified from the SENTENCE carrying the marker, not the whole turn.  On
    a 900-word spec prompt the whole turn contains "component", "hook" and
    "interface" somewhere, so every rule inside it used to come back
    `architecture` -- "do not ask me any question" was filed under
    architecture on two of the four repos measured.  `fallback` (the full
    turn) is consulted only when the sentence itself scores nothing.
    """
    kind = _score_kind(text)
    if kind is None and fallback:
        kind = _score_kind(fallback)
    return kind or CORRECTION_FALLBACK_KIND


def _score_kind(text: str) -> Optional[str]:
    normalized = set(normalize(text).split(" "))
    scores = {}  # type: Dict[str, int]
    for kind, keywords in _COMPILED_KIND_KEYWORDS.items():
        scores[kind] = len(normalized & keywords)
    if _SCOPE_BOOST.search(text):
        scores["scope"] = scores.get("scope", 0) + 2

    best_kind = None
    best_score = 0
    for kind in _KIND_PRIORITY:
        score = scores.get(kind, 0)
        if score > best_score:
            best_kind = kind
            best_score = score
    if best_kind is None or best_score == 0:
        return None
    return best_kind


#: A sentence that carries a marker but is not aimed at the agent.
#:
#: Measured on four real project histories, these three shapes were the bulk of
#: the false positives in `corrections`, and every one of them would have been
#: written into a rules file as if the developer had said it:
#:
#:   subordinate  "since they don't have this product concept"
#:   proposal     "why don't we give product option in the ad creation as well"
#:   third party  "Now if you guys don't already know, Gemini Omni is the ..."
#:                (a pasted YouTube transcript)
_SUBORDINATE_OPENER = re.compile(
    r"^\s*(?:and\s+|but\s+|so\s+)?(?:since|because|cause|coz|if|when|while|"
    r"whenever|although|though|unless|whereas|as long as|given that|in case|"
    r"which|who|that)\b",
    re.IGNORECASE,
)

#: "why don't we ...", "what if we ...", "should we not ..." -- a suggestion
#: being floated, not a rule being laid down.
_PROPOSAL = re.compile(
    r"\b(?:why (?:don'?t|not|can'?t|shouldn'?t)|what if|how about|"
    r"should we|shall we|do you think|would it be)\b",
    re.IGNORECASE,
)

#: The subject of the negation is somebody other than the agent or the team.
_THIRD_PARTY_SUBJECT = re.compile(
    r"\b(?:they|he|she|it|people|users?|everyone|nobody|guys|"
    r"you guys|most (?:people|devs|folks))\s+"
    r"(?:\w+\s+){0,2}(?:don'?t|doesn'?t|do not|does not|didn'?t|did not|"
    r"never|won'?t|can'?t|aren'?t|isn'?t)\b",
    re.IGNORECASE,
)


def is_directive_sentence(sentence: str) -> bool:
    """
    Is this sentence an instruction the developer aimed at their agent?

    The marker regexes are deliberately loose -- "don't", "never", "instead"
    are ordinary English -- so this is the filter that decides whether the
    sentence would make sense pasted into a rules file.
    """
    if not sentence:
        return False
    stripped = sentence.strip()
    if not stripped:
        return False
    if _SUBORDINATE_OPENER.search(stripped):
        return False
    if _PROPOSAL.search(stripped):
        return False
    if _THIRD_PARTY_SUBJECT.search(stripped):
        return False
    return True


def detect_correction(text: str) -> Optional[Dict[str, str]]:
    """
    Decide whether a user turn is a correction, and what kind.

    Returns None, or:

        {"kind": "tooling|style|process|architecture|scope",
         "text": "<the sentence carrying the marker, <=200 chars>",
         "marker": "we use"}

    A correction is a user turn carrying a negation or directive marker:
    "no,", "don't", "do not", "stop", "never", "always", "we use",
    "we don't use", "instead of", "not X, use Y", "i told you", "that's
    wrong", "revert", and "again" when it follows a repetition cue.
    """
    if not text or not isinstance(text, str):
        return None
    if len(text) > MAX_INPUT_CHARS:
        text = text[:MAX_INPUT_CHARS]

    # Scan sentence by sentence and return the first one that both carries a
    # marker and reads as an instruction.  Scanning the whole turn for the
    # marker and only then cutting out its sentence -- the old behaviour --
    # threw the turn away whenever the FIRST "don't" happened to sit in a
    # quoted paste or a subordinate clause, even when a real rule followed.
    fallback_hit = None
    for index, candidate in enumerate(_SENTENCE_SPLIT.split(text)):
        if index >= 400:
            break
        sentence = _WS.sub(" ", candidate).strip()
        if not sentence:
            continue
        marker_name = None
        for name, regex in _STRONG_MARKERS:
            if regex.search(sentence) is not None:
                marker_name = name
                break
        if marker_name is None and _AGAIN_MARKER.search(sentence) is not None:
            marker_name = "again"
        if marker_name is None:
            continue
        if not is_directive_sentence(sentence):
            if fallback_hit is None:
                fallback_hit = (sentence, marker_name)
            continue
        return {
            "kind": _classify_correction(sentence, text),
            "text": _truncate_sentence(sentence),
            "marker": marker_name,
        }

    if fallback_hit is None:
        return None
    # Every marker in the turn sat in a non-directive sentence.  Report it, but
    # kind-classify from the sentence so the caller can still filter it out.
    sentence, marker_name = fallback_hit
    return {
        "kind": _classify_correction(sentence, text),
        "text": _truncate_sentence(sentence),
        "marker": marker_name,
        "directive": "no",
    }


def _truncate_sentence(sentence: str) -> str:
    if len(sentence) > 200:
        return sentence[:199].rstrip() + "…"
    return sentence


# ---------------------------------------------------------------------------
# extract_commands()
# ---------------------------------------------------------------------------

#: Executables recognised without a shell prompt marker.  Anything outside this
#: set is only accepted when the line explicitly starts with `$ ` or `% `,
#: which keeps backticked prose (`useEffect`, `POST /users`) out of the
#: command counts.  Extend freely.
KNOWN_EXECUTABLES = frozenset(
    """
    npm yarn pnpm bun bunx npx pnpx node deno tsx ts-node nodemon
    python python3 py pip pip3 pipx poetry uv pipenv conda pytest tox nox
    ruff black isort flake8 pylint mypy pyright
    cargo rustc go gofmt golangci-lint
    make just task mise asdf direnv
    docker docker-compose podman kubectl helm kustomize skaffold terraform ansible
    pulumi vagrant
    git gh glab hub
    rails bundle rake gem rspec rubocop
    mvn gradle gradlew dotnet php composer artisan symfony laravel
    jest vitest mocha karma playwright cypress ava tap
    eslint prettier biome tsc vite webpack rollup esbuild parcel next nuxt astro
    swift xcodebuild fastlane pod flutter dart expo eas react-native
    psql mysql sqlite3 redis-cli mongosh mongo
    supabase vercel netlify wrangler fly flyctl heroku railway render aws gcloud az
    prisma drizzle-kit alembic sequelize knex
    curl wget jq rg grep sed awk find ls cat echo sh bash zsh chmod mkdir cp mv rm
    open code cursor claude codex
    """.split()
)

#: `npm run lint` must survive as three tokens, not collapse to `npm run`.
_PASSTHROUGH_SUBCOMMANDS = frozenset(["run", "exec", "x", "compose", "workspace", "dlx", "global"])

#: Wrappers that prefix a real command.
_COMMAND_WRAPPERS = frozenset(["sudo", "time", "env", "nohup", "xargs", "command", "nice", "watch"])

#: Runners whose first argument is the interesting part.
_RUNNER_EXECUTABLES = frozenset(["npx", "bunx", "pnpx", "dlx", "uvx"])

#: Executables that are also ordinary English words.  On a bare prose line
#: ("make sure the tests pass", "just fix it", "go to the settings page") these
#: would otherwise be counted as commands, so on that source they additionally
#: need a flag or a path-looking argument.
_AMBIGUOUS_EXECUTABLES = frozenset(
    """
    just make open find test code echo cat ls go python py sh bash zsh watch
    command time env rm cp mv mkdir chmod grep sed awk node next render fly task
    mise hub tap pod gem dart claude codex cursor
    """.split()
)

#: Fence languages whose contents are shell.  A ```ts or ```json block is code,
#: not a command list, and scanning it only produces noise.
_SHELL_FENCE_TAGS = frozenset(
    ["", "sh", "bash", "zsh", "fish", "shell", "shellsession", "sh-session", "console", "terminal", "cmd", "term"]
)

_BACKTICK_SPAN = re.compile(r"`([^`\n]{2,200})`")
_FENCE_BLOCK = re.compile(r"```([A-Za-z0-9_+-]{0,15})[ \t]*\n([\s\S]{0,4000}?)```")
_FENCE_ANY = re.compile(r"```[\s\S]{0,20000}?```")
_PROMPT_PREFIX = re.compile(r"^\s*(?:\$|%|>|❯)\s+")
_ENV_ASSIGNMENT = re.compile(r"^[A-Z_][A-Z0-9_]{0,63}=")
#: A trailing colon means the token was a label ("bun path:"), not a subcommand.
_SUBCOMMAND_OK = re.compile(r"^[a-z][a-z0-9:._-]{0,29}[a-z0-9._-]$|^[a-z]$")
_COMMAND_SPLIT = re.compile(r"&&|\|\||[;|]")
#: Shell-safe token: a prose line containing a comma, quote or question mark is
#: a sentence, not a command.
_SHELL_TOKEN = re.compile(r"^[A-Za-z0-9_./:@=+~\[\]{}*-]{1,120}$")
_TRUSTED_HEAD = re.compile(r"^[./A-Za-z0-9_-]{1,64}$")

#: A `> `-prefixed line inside an untagged fence is treated as a shell prompt,
#: which is right for a terminal paste and wrong for a numbered code listing or
#: a markdown quote.  These heads are never executables, and without the guard
#: one measured repo reported `313`, `314`, `const files` and `const problems`
#: as commands its developer had asked for.
_NON_EXECUTABLE_HEAD = re.compile(
    r"^\d+$"
    r"|^(?:const|let|var|function|func|return|import|export|from|class|def|"
    r"public|private|static|new|await|async|if|else|elif|for|while|try|catch|"
    r"throw|print|console|type|interface|enum|struct|impl|use|package)$",
    re.IGNORECASE,
)
#: A plain English word wearing sentence punctuation ("remaining.", "clear,").
_PROSE_PUNCT = re.compile(r"^[A-Za-z]{2,}[.,;:!?]$")


def _normalize_command_tokens(parts: Sequence[str]) -> str:
    """`['npm','run','lint','--','--fix']` -> `'npm run lint'`."""
    if not parts:
        return ""
    executable = parts[0]
    if "/" in executable:
        executable = executable.rsplit("/", 1)[-1]
    if not executable:
        return ""

    rest = list(parts[1:])

    # `python -m pytest` keeps its module flag; it is the whole meaning.
    if executable in ("python", "python3", "py") and "-m" in rest:
        index = rest.index("-m")
        if index + 1 < len(rest):
            return "%s -m %s" % (executable, rest[index + 1])

    if executable in _RUNNER_EXECUTABLES and rest:
        inner = _normalize_command_tokens(rest)
        return ("%s %s" % (executable, inner)).strip() if inner else executable

    words = [t for t in rest if _SUBCOMMAND_OK.match(t)]
    if not words:
        return executable
    first = words[0]
    if first in _PASSTHROUGH_SUBCOMMANDS and len(words) > 1:
        return "%s %s %s" % (executable, first, words[1])
    return "%s %s" % (executable, first)


#: Words a developer puts in front of a command when asking for it to be run.
#: Only these may be skipped over, and only ahead of a known executable.
_REQUEST_LEAD_IN = frozenset(
    """
    run rerun re-run execute exec please pls can could would will you your
    just now then again also first quickly kindly do lets let us
    """.split()
)

#: How many lead-in words to look past.  "can you please run bun test" is 4.
_MAX_LEAD_IN_TOKENS = 5


def _strip_request_lead_in(parts: List[str]) -> List[str]:
    """
    Drop an English request lead-in ("run", "please run", "can you run") when
    a known executable follows it within a few tokens.

    Returns `parts` untouched when the head is already an executable, or when
    nothing behind the filler looks like a command -- so ordinary prose such as
    "can you explain the router" is still not mistaken for a command.
    """
    if not parts:
        return parts
    head = parts[0].lower().strip(".,;:!?`'\"")
    if head in KNOWN_EXECUTABLES or head in _COMMAND_WRAPPERS:
        return parts
    for index in range(min(_MAX_LEAD_IN_TOKENS, len(parts))):
        token = parts[index].lower().strip(".,;:!?`'\"")
        if token in KNOWN_EXECUTABLES:
            return parts[index:] if index else parts
        if token not in _REQUEST_LEAD_IN:
            return parts
    return parts


def _command_from_candidate(candidate: str, trusted: bool, strict: bool = False) -> List[str]:
    """
    Turn one candidate string into zero or more normalized commands.

    `trusted`  the candidate came after an explicit shell prompt (`$ `, `% `),
               so an unrecognised executable is still accepted.
    `strict`   the candidate is a bare prose line, so extra shape checks apply
               (see `_AMBIGUOUS_EXECUTABLES`).
    """
    out = []  # type: List[str]
    for piece in _COMMAND_SPLIT.split(candidate):
        raw = piece.strip()
        if not raw or len(raw) > 400:
            continue
        parts = raw.split()
        # Strip the English lead-in a request wraps a command in: "run bun run
        # typecheck", "please run bun test", "can you run npm run build".
        # Without this the head is the word "run" and the whole command is
        # dropped -- which starved commands_requested[] (mapping-rules.md
        # row 4, the hook-evidence path) on the most common phrasing there is.
        # Conservative on purpose: only skip filler words, only the first few,
        # and only when a real executable is sitting behind them.
        parts = _strip_request_lead_in(parts)
        # Strip `FOO=bar` prefixes and wrapper executables.
        while parts and (_ENV_ASSIGNMENT.match(parts[0]) or parts[0] in _COMMAND_WRAPPERS):
            parts = parts[1:]
        if not parts:
            continue
        head = parts[0]
        base = head.rsplit("/", 1)[-1] if "/" in head else head
        if trusted:
            if not _TRUSTED_HEAD.match(head):
                continue
            if _NON_EXECUTABLE_HEAD.match(base):
                continue
        else:
            if base not in KNOWN_EXECUTABLES:
                continue
        if strict and not trusted:
            # A bare prose line has to look like a command all the way through.
            if len(parts) < 2:
                continue
            if not all(_SHELL_TOKEN.match(token) for token in parts):
                continue
            if base in _AMBIGUOUS_EXECUTABLES:
                # A word carrying sentence punctuation is prose, not an
                # argument.  Without this, "just give me a list for how many is
                # remaining." was reported as the command `just give`, because
                # the period on "remaining." satisfied the dot test below.
                # Scoped to the ambiguous heads so that "bun run test, then
                # commit." still yields `bun run test`.
                if any(_PROSE_PUNCT.match(token) for token in parts):
                    continue
                argumentative = False
                for token in parts[1:]:
                    if token.startswith("-") or "/" in token or "=" in token:
                        argumentative = True
                        break
                    stripped_token = token.rstrip(".,;:!?")
                    if "." in stripped_token and len(stripped_token) > 2:
                        argumentative = True
                        break
                if not argumentative:
                    continue
        normalized = _normalize_command_tokens(parts)
        if normalized:
            out.append(normalized)
    return out


def extract_commands(text: str) -> List[str]:
    """
    Pull shell commands out of a user turn and normalize each to the
    executable plus its first meaningful subcommand.

    >>> extract_commands("run `bun test` then `npm run lint`, not pytest")
    ['bun test', 'npm run lint']

    Sources, in order: fenced code blocks, backticked spans, and whole lines
    that start with a shell prompt (`$ `, `% `, `> `) or with a known
    executable.  Duplicates are preserved so the caller can count them.
    """
    if not text or not isinstance(text, str):
        return []
    if len(text) > MAX_INPUT_CHARS:
        text = text[:MAX_INPUT_CHARS]

    found = []  # type: List[str]

    # 1. Fenced blocks, but only the ones tagged as shell (or untagged).
    for tag, block in _FENCE_BLOCK.findall(text):
        if tag.lower() not in _SHELL_FENCE_TAGS:
            continue
        for line in block.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            trusted = bool(_PROMPT_PREFIX.match(line))
            found.extend(_command_from_candidate(_PROMPT_PREFIX.sub("", stripped), trusted))

    remainder = _FENCE_ANY.sub(" ", text)

    # 2. Backticked spans -- the backticks are themselves the evidence.
    for span in _BACKTICK_SPAN.findall(remainder):
        trusted = bool(_PROMPT_PREFIX.match(span))
        found.extend(_command_from_candidate(_PROMPT_PREFIX.sub("", span).strip(), trusted))

    # 3. Whole lines, with the strict shape checks so prose is not mistaken for
    #    a command ("make sure the tests pass", "just fix it").
    for line in _BACKTICK_SPAN.sub(" ", remainder).splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        trusted = bool(_PROMPT_PREFIX.match(line))
        candidate = _PROMPT_PREFIX.sub("", stripped)
        found.extend(_command_from_candidate(candidate, trusted, strict=True))

    return found


# ---------------------------------------------------------------------------
# Service lexicon
# ---------------------------------------------------------------------------

#: External systems the setup might need an MCP server, a rule, or a skill for.
#: Aliases are matched with word boundaries, never as substrings, so "aws"
#: cannot fire on "laws".
SERVICE_LEXICON = {
    "stripe": ["stripe", "stripe-node", "@stripe", "stripe-js", "stripe cli"],
    "supabase": ["supabase", "@supabase", "supabase-js", "supabase cli"],
    "neon": ["neon", "neon.tech", "neondatabase", "@neondatabase"],
    "planetscale": ["planetscale", "@planetscale", "pscale"],
    "linear": ["linear", "linear.app", "@linear", "linear ticket", "linear issue"],
    "jira": ["jira", "atlassian", "jira ticket"],
    "posthog": ["posthog", "post hog", "@posthog", "posthog.com"],
    "sentry": ["sentry", "sentry.io", "@sentry"],
    "datadog": ["datadog", "dd-trace", "@datadog", "datadoghq"],
    "vercel": ["vercel", "@vercel", "vercel.app"],
    "netlify": ["netlify", "@netlify"],
    "cloudflare": ["cloudflare", "wrangler", "cloudflare workers", "workers kv", "r2 bucket"],
    "aws": ["aws", "aws-sdk", "boto3", "amazon web services", "dynamodb", "cloudfront", "cloudwatch"],
    "gcp": ["gcp", "google cloud", "gcloud", "bigquery", "cloud run"],
    "firebase": ["firebase", "firestore", "@react-native-firebase"],
    "clerk": ["clerk", "@clerk", "clerk.dev", "clerk.com"],
    "better-auth": ["better-auth", "better auth", "betterauth"],
    "auth0": ["auth0", "@auth0"],
    "resend": ["resend", "resend.com", "@resend"],
    "twilio": ["twilio", "@twilio"],
    "openai": ["openai", "chatgpt", "gpt-4", "gpt-4o", "gpt-5", "@ai-sdk/openai"],
    "anthropic": ["anthropic", "@anthropic-ai", "claude api", "claude-sonnet", "claude-opus"],
    "replicate": ["replicate.com", "replicate.run", "@replicate", "replicate api"],
    "playwright": ["playwright", "@playwright"],
    "cypress": ["cypress", "cypress.io"],
    "storybook": ["storybook", "@storybook"],
    "prisma": ["prisma", "@prisma", "prisma schema"],
    "drizzle": ["drizzle", "drizzle-orm", "drizzle-kit"],
    "redis": ["redis", "ioredis", "upstash", "redis-cli"],
    "postgres": ["postgres", "postgresql", "psql", "pgbouncer", "pg_dump"],
    "mongodb": ["mongodb", "mongo", "mongoose", "mongodb atlas"],
    "elasticsearch": ["elasticsearch", "elastic search", "opensearch"],
    "notion": ["notion", "notion.so", "@notionhq"],
    "slack": ["slack", "slack api", "@slack", "slack channel"],
    "github": ["github", "octokit", "github actions", "gh cli", "github.com"],
    "gitlab": ["gitlab", "@gitlab", "gitlab ci"],
    "figma": ["figma", "figma file"],
    "expo": ["expo", "expo.dev", "eas build", "expo go"],
    "revenuecat": ["revenuecat", "revenue cat", "@revenuecat"],
}

#: Aliases that are also ordinary English words.  A bare hit only counts when a
#: technical context word sits nearby.
_AMBIGUOUS_ALIASES = frozenset(
    ["linear", "notion", "slack", "expo", "sentry", "clerk", "resend", "neon", "mongo", "aws"]
)

_CONTEXT_WINDOW = 48
_CONTEXT_RE = re.compile(
    r"\b(?:api|apis|sdk|mcp|cli|token|key|keys|secret|dashboard|integration|integrations|"
    r"integrate|webhook|webhooks|client|server|account|workspace|project|board|ticket|"
    r"tickets|issue|issues|error|errors|exception|trace|traces|db|database|schema|branch|"
    r"instance|connect|connected|connection|auth|login|sync|docs|doc|page|pages|channel|"
    r"message|email|send|build|deploy|deployed|deployment|app|url|endpoint|config|env|"
    r"install|package|dep|dependency|npm|sdk|monitor|monitoring|alert|alerts|tracking|"
    r"analytics|migration|query|table|bucket|storage|dev|prod|production|staging)\b"
    r"|\.(?:com|io|so|dev|app|tech|sh|ai|co)\b",
    re.IGNORECASE,
)


def _build_alias_index():
    """One combined regex over every alias -> {matched_lowercase: (name, alias)}."""
    lookup = {}
    alternatives = []
    pairs = []
    for name in sorted(SERVICE_LEXICON.keys()):
        for alias in SERVICE_LEXICON[name]:
            pairs.append((alias.lower(), name, alias))
    # Longest alias first so "claude api" wins over a hypothetical "claude".
    pairs.sort(key=lambda p: (-len(p[0]), p[0]))
    for lowered, name, alias in pairs:
        if lowered in lookup:
            continue
        lookup[lowered] = (name, alias)
        alternatives.append(re.escape(lowered))
    pattern = r"(?<![A-Za-z0-9_])(?:%s)(?![A-Za-z0-9_])" % "|".join(alternatives)
    return lookup, re.compile(pattern, re.IGNORECASE)


_ALIAS_LOOKUP, _ALIAS_RE = _build_alias_index()


def _context_ok(text: str, start: int, end: int) -> bool:
    left = max(0, start - _CONTEXT_WINDOW)
    right = min(len(text), end + _CONTEXT_WINDOW)
    return _CONTEXT_RE.search(text[left:right]) is not None


def find_services(text: str) -> List[Dict[str, Any]]:
    """
    Find external systems mentioned in a piece of text.

    Word-boundary matching only -- "aws" does not match "laws", "expo" does
    not match "exposed".  Aliases that are also ordinary English words
    ("linear", "notion", "slack", "sentry", ...) additionally require a
    technical context word within ~48 characters, so "linear regression" and
    "cut me some slack" do not invent an integration.

    Returns, sorted by count desc then name asc:

        [{"name": "supabase", "count": 3, "aliases": ["supabase", "@supabase"]}]
    """
    if not text or not isinstance(text, str):
        return []
    if len(text) > MAX_INPUT_CHARS:
        text = text[:MAX_INPUT_CHARS]

    counts = {}  # type: Dict[str, int]
    aliases_seen = {}  # type: Dict[str, Set[str]]
    for match in _ALIAS_RE.finditer(text):
        lowered = match.group(0).lower()
        entry = _ALIAS_LOOKUP.get(lowered)
        if entry is None:
            continue
        name, alias = entry
        if lowered in _AMBIGUOUS_ALIASES and not _context_ok(text, match.start(), match.end()):
            continue
        counts[name] = counts.get(name, 0) + 1
        aliases_seen.setdefault(name, set()).add(alias)

    out = [
        {"name": name, "count": count, "aliases": sorted(aliases_seen.get(name, set()))}
        for name, count in counts.items()
    ]
    out.sort(key=lambda item: (-item["count"], item["name"]))
    return out


def find_services_names(text: str) -> List[str]:
    """Just the service names, in the same order as `find_services()`."""
    return [item["name"] for item in find_services(text)]


# ---------------------------------------------------------------------------
# Self-test:  python3 lib/textnorm.py
# ---------------------------------------------------------------------------


def _selftest() -> int:
    def check(label, condition, detail=""):
        if condition:
            print("PASS  %s" % label)
            return True
        print("FAIL  %s%s" % (label, ("  -- " + detail) if detail else ""))
        return False

    results = []  # type: List[bool]

    # -- normalize -----------------------------------------------------------
    got = normalize("Add a new API endpoint for /users with `zod` validation")
    results.append(check("normalize strips paths and inline code", "/users" not in got and "`" not in got, got))

    got = normalize("see https://example.com/x?y=1 and src/app/page.tsx line 42")
    results.append(
        check(
            "normalize strips urls, relative paths, filenames and numbers",
            "http" not in got and "page.tsx" not in got and "42" not in got,
            got,
        )
    )

    got = normalize("commit a1b2c3d4e5 broke 550e8400-e29b-41d4-a716-446655440000")
    results.append(check("normalize strips hashes and uuids", "a1b2c3d4e5" not in got and "550e8400" not in got, got))

    got = normalize("we DEFACED the facade")
    results.append(check("normalize keeps hex-lookalike english words", "defaced" in got and "facade" in got, got))

    got = normalize('use "double quoted" text')
    results.append(check("normalize strips quoted strings", "double quoted" not in got, got))

    got = normalize("don't break contractions")
    results.append(check("normalize keeps contractions readable", "don" in got and "break" in got, got))

    # Scrubbing runs first, so redaction markers are in the input by design.
    got = skeleton("update the component with key=[REDACTED:openai_key] in ~/repo/src/app/page.tsx")
    results.append(
        check(
            "scrub markers never become skeleton tokens",
            "redacted" not in got and "openai" not in got,
            got,
        )
    )

    # -- skeleton ------------------------------------------------------------
    got = skeleton("add a new API endpoint for /users with zod validation")
    # The build contract used to spell this example "add new api endpoint
    # with validation"; it has since been corrected to the string below, so
    # the two now agree.  The shipped skeleton drops "new" as a stopword and
    # that is the behaviour that is CORRECT: "new" is an adjective on the
    # object, not part of the verb+object shape -- keeping it splits "add a
    # new api endpoint" from "add an api endpoint", which is the same
    # request.  That, together with MAX_SKELETON_TOKENS 10 -> 6, is what took
    # hostshare from 5 request shapes over 384 user turns to 19.  Do NOT
    # relax the filter to put "new" back.
    results.append(check("skeleton matches the contract example", got == "add api endpoint with validation", got))

    got = skeleton("Hey Claude, could you please write unit tests for the auth service?")
    results.append(check("skeleton drops leading politeness", got.startswith("write"), got))

    got = skeleton("please just fix the failing build again")
    results.append(check("skeleton keeps the head verb", got.split(" ")[0] == "fix", got))

    a = skeleton("add a new api endpoint with yup validation")
    b = skeleton("Add a new API endpoint with zod validation")
    results.append(check("skeleton is library-agnostic (same shape clusters)", a == b, "%r vs %r" % (a, b)))

    got = skeleton("we use bun not npm")
    results.append(check("skeleton does not collapse tech-only prompts", len(got.split(" ")) >= 2, got))

    got = skeleton("do " + "very " * 40 + "many things now")
    results.append(check("skeleton caps at MAX_SKELETON_TOKENS", len(got.split(" ")) <= MAX_SKELETON_TOKENS, got))

    results.append(check("skeleton of empty input is empty", skeleton("") == "" and skeleton(None) == ""))

    # -- cluster -------------------------------------------------------------
    prompts = [
        {"text": "add a new API endpoint for /users with zod validation", "session_id": "s1", "timestamp": "2026-01-01T00:00:00Z"},
        {"text": "add an endpoint for /orders with validation", "session_id": "s1", "timestamp": "2026-01-02T00:00:00Z"},
        {"text": "add a new api endpoint for /teams with zod validation", "session_id": "s2", "timestamp": "2026-01-03T00:00:00Z"},
        {"text": "write unit tests for the billing module", "session_id": "s2", "timestamp": "2026-01-04T00:00:00Z"},
        {"text": "write unit tests for the auth module", "session_id": "s3", "timestamp": "2026-01-05T00:00:00Z"},
        {"text": "deploy to staging", "session_id": "s3", "timestamp": "2026-01-06T00:00:00Z"},
    ]
    clusters = cluster(prompts)
    results.append(check("cluster drops singletons at min_count=2", all(c["count"] >= 2 for c in clusters), str(clusters)))
    results.append(check("cluster finds the endpoint shape", clusters and clusters[0]["count"] == 3, str(clusters[:1])))
    top = clusters[0] if clusters else {}
    results.append(
        check(
            "cluster reports sessions, timestamps and <=2 examples",
            top.get("sessions") == 2
            and top.get("first_seen") == "2026-01-01T00:00:00Z"
            and top.get("last_seen") == "2026-01-03T00:00:00Z"
            and len(top.get("examples", [])) <= 2,
            str(top),
        )
    )
    results.append(check("cluster ids are stable", _cluster_id("add new api endpoint") == _cluster_id("add new api endpoint")))

    shuffled = [prompts[i] for i in (5, 2, 0, 4, 1, 3)]
    results.append(
        check(
            "cluster is order independent",
            [(c["skeleton"], c["count"]) for c in cluster(prompts)]
            == [(c["skeleton"], c["count"]) for c in cluster(shuffled)],
            str(cluster(shuffled)),
        )
    )
    results.append(check("cluster tolerates plain strings", len(cluster(["fix the build", "fix the build"])) == 1))
    results.append(check("cluster of nothing is empty", cluster([]) == [] and cluster(None) == []))

    # -- classify_intent -----------------------------------------------------
    # The meta cases are VERBATIM turns from the 81-session history that put
    # four copies of the same status question in the top ten request shapes.
    meta_cases = [
        ("how much time", "time"),
        ("how much more time?", "time"),
        ("how long will this take?", "time"),
        ("what's done, what's remaining?", "remaining"),
        ("what's remaining in this", "remaining"),
        ("how many remaining", "remaining"),
        ("check how many of these are completed now. review previous commits", "remaining"),
        ("is anything remains to be done now?", "remaining"),
        ("is anything remains to be done before we commit this?", "remaining"),
        ("is anything remains to be done for this stripe integration phase?", "remaining"),
        ("are we finished?", "remaining"),
        ("everything completed?", "remaining"),
        ("is this task completed?", "remaining"),
        ("just give me a list for how many is remaining.", "remaining"),
        ("now tell me what should we be working on next? now that search side is on native", "next"),
        ("tell me what should i start with", "next"),
        ("what do i need to do?", "next"),
        ("what's next?", "next"),
        ("what did you just do?", "recap"),
        ("summarize the progress so far", "recap"),
    ]
    for text, expected_topic in meta_cases:
        got = classify_intent(text)
        topic = meta_topic(text)
        results.append(
            check(
                "classify_intent(%r) -> meta/%s" % (text[:44], expected_topic),
                got == "meta" and topic == expected_topic,
                "%s / %s" % (got, topic),
            )
        )

    work_cases = [
        "commit the staged changes",
        "add a new API endpoint for /users with zod validation",
        "merge origin main",
        "we need to fix this. the UI is broken",
        "can you make the listing detail page UI block exactly same as given in web in mobile?",
        "what's remaining? also add the logout button",  # asks for work too
        "run the test suite again",
        "what should i name this function",
        "what do you think about the layout",
    ]
    for text in work_cases:
        got = classify_intent(text)
        results.append(check("classify_intent(%r) -> work" % text[:44], got == "work", got))

    social_cases = ["ok", "okay thanks", "thanks!", "continue", "go ahead", "yes", "yep", "hi", "perfect", "got it"]
    for text in social_cases:
        got = classify_intent(text)
        results.append(check("classify_intent(%r) -> social" % text[:44], got == "social", got))

    results.append(
        check(
            "classify_intent returns only the three labels",
            all(classify_intent(t) in INTENTS for t in ["", None, "  ", "x", "how much time", "ok"]),
        )
    )
    results.append(
        check(
            "classify_intent is word-boundary safe",
            classify_intent("notime for anything") == "work"
            and classify_intent("already done with the recapture script") == "work",
            "%s / %s" % (classify_intent("notime for anything"), classify_intent("already done with the recapture script")),
        )
    )
    results.append(
        check(
            "classify_intent works on a skeleton too",
            classify_intent("how much time") == "meta"
            and classify_intent("what remaining") == "meta"
            and classify_intent("anything remains") == "meta"
            and classify_intent("commit staged changes") == "work",
        )
    )
    results.append(
        check(
            "meta_topic collapses the four hostshare status clusters into one",
            len(set(meta_topic(t) for t in [
                "what's done, what's remaining?",
                "how many remaining",
                "is anything remains to be done now?",
                "what's remaining in this",
            ])) == 1,
        )
    )

    # -- detect_correction ---------------------------------------------------
    correction_cases = [
        ("no, use bun instead of npm", "tooling"),
        ("we use pnpm here, never yarn", "tooling"),
        ("don't add comments to every line", "style"),
        ("always run the tests before you commit", "process"),
        ("that's wrong, db access belongs in the repository layer", "architecture"),
        ("stop, that is way too much, revert it", "scope"),
    ]
    for text, expected in correction_cases:
        got = detect_correction(text)
        results.append(
            check(
                "detect_correction(%r) -> %s" % (text[:34], expected),
                got is not None and got["kind"] == expected,
                str(got),
            )
        )

    non_corrections = [
        "add a new endpoint for users",
        "run the test suite again",
        "what does this function do",
        "generate a migration for the orders table",
    ]
    for text in non_corrections:
        got = detect_correction(text)
        results.append(check("detect_correction ignores %r" % text[:34], got is None, str(got)))

    got = detect_correction("i told you again, the imports go at the top")
    results.append(check("detect_correction fires on 'told you ... again'", got is not None, str(got)))

    got = detect_correction("no, that's not it")
    results.append(
        check(
            "detect_correction falls back to a valid kind",
            got is not None and got["kind"] in CORRECTION_KINDS,
            str(got),
        )
    )

    # -- extract_commands ----------------------------------------------------
    command_cases = [
        ("run `bun test` first", ["bun test"]),
        ("then `npm run lint` please", ["npm run lint"]),
        ("just `pytest -q tests/unit`", ["pytest"]),
        ("use `make build` not the script", ["make build"]),
        ("`git commit -m \"wip\"`", ["git commit"]),
        ("`npx prisma migrate dev`", ["npx prisma migrate"]),
        ("`python -m pytest`", ["python -m pytest"]),
        ("`docker compose up -d`", ["docker compose up"]),
    ]
    for text, expected in command_cases:
        got = extract_commands(text)
        results.append(check("extract_commands(%r) -> %s" % (text[:30], expected), got == expected, str(got)))

    got = extract_commands("the `useEffect` hook and the `Button` component")
    results.append(check("extract_commands ignores backticked identifiers", got == [], str(got)))

    got = extract_commands("$ ./scripts/deploy.sh production")
    results.append(check("extract_commands trusts an explicit $ prompt", got == ["deploy.sh production"], str(got)))

    got = extract_commands("```bash\nbun install\nbun run dev\n```")
    results.append(check("extract_commands reads fenced blocks", got == ["bun install", "bun run dev"], str(got)))

    got = extract_commands("`bun test && bun run lint`")
    results.append(check("extract_commands splits on &&", got == ["bun test", "bun run lint"], str(got)))

    got = extract_commands("make sure the tests pass\njust fix it\ngo to the settings page")
    results.append(check("extract_commands ignores prose starting with an exe name", got == [], str(got)))

    got = extract_commands("bun run dev")
    results.append(check("extract_commands still reads a bare command line", got == ["bun run dev"], str(got)))

    got = extract_commands("```json\n{\"scripts\": {\"test\": \"jest\"}}\n```")
    results.append(check("extract_commands skips non-shell fences", got == [], str(got)))

    # -- find_services -------------------------------------------------------
    got = find_services_names("we use supabase auth and stripe for billing")
    results.append(check("find_services finds supabase and stripe", set(got) == {"supabase", "stripe"}, str(got)))

    got = find_services_names("the laws of thermodynamics and flawed reasoning")
    results.append(check("find_services does not match 'aws' inside 'laws'", got == [], str(got)))

    got = find_services_names("deploy the lambda to aws with the aws-sdk")
    results.append(check("find_services matches aws with context", "aws" in got, str(got)))

    got = find_services_names("use linear regression on the dataset")
    results.append(check("find_services skips 'linear regression'", "linear" not in got, str(got)))

    got = find_services_names("move the linear ticket to done via the linear api")
    results.append(check("find_services keeps linear when it is the tool", "linear" in got, str(got)))

    got = find_services_names("exposed the endpoint and exported the data")
    results.append(check("find_services does not match 'expo' inside 'exposed'", "expo" not in got, str(got)))

    got = find_services("call the posthog api, posthog again, and stripe once")
    results.append(check("find_services counts and sorts", got and got[0]["name"] == "posthog" and got[0]["count"] == 2, str(got)))

    # -- misc ----------------------------------------------------------------
    results.append(check("count_tokens_estimate is chars/4", count_tokens_estimate("a" * 400) == 100))
    results.append(check("jaccard basics", abs(jaccard({"a", "b"}, {"b", "c"}) - (1.0 / 3.0)) < 1e-9))
    results.append(check("SERVICE_LEXICON covers the contract list", len(SERVICE_LEXICON) >= 38, str(len(SERVICE_LEXICON))))

    passes = sum(1 for r in results if r)
    failures = sum(1 for r in results if not r)
    print("")
    print("%d passed, %d failed" % (passes, failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(_selftest())
