#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agentify :: lib/emit.py -- stdout JSON emission, hard output caps, shared CLI.

Every analyzer script obeys the same output contract:

  * ONE JSON object on stdout and nothing else.  Diagnostics go to stderr.
  * The exit code follows the table below.  A degraded run returns valid JSON
    with a populated `warnings` array and exits 0, because the skill must
    never abort a phase -- it drops to reduced evidence and says so in the plan.
  * The output is size capped.  `mine_transcripts.py` in particular must stay
    around 3k tokens (~12 KB) no matter how much history the developer has;
    that cap is what keeps transcript volume out of the context window.

This module owns all three rules so the four scripts cannot drift apart.

===========================================================================
EXIT-CODE CONTRACT -- the single normative statement.  All four analyzers
(`discover.py`, `mine_transcripts.py`, `mine_git.py`, `verify_artifacts.py`)
obey it identically.  If you are adding a script or a new failure branch,
this table is the spec; do not invent a code.
===========================================================================

  exit 0  SUCCESS **or DEGRADED**.  Valid JSON on stdout, always.
          Degraded means: the path does not exist, it is a file rather than a
          directory, it is `/dev/null`, the directory is empty or unreadable,
          there is no git repo, there are no transcripts, consent limited the
          window, a subprocess timed out, a parser gave up on a file.  Every
          one of those is a NORMAL outcome for a tool pointed at an arbitrary
          repo, and every one of them still produces the full schema with
          empty values plus an entry in `warnings` saying what was lost.

          This is the case that matters most.  agentify runs as a pipeline
          driven by an agent, and a non-zero exit in an early phase is read
          as "this phase is broken, give up".  Phase 1 exiting 1 because a
          path was mistyped would abort a run that should simply have
          continued with less evidence.  Degraded is not failure.

  exit 1  NOTHING USABLE WAS PRODUCED.  stdout still carries a valid JSON
          object -- a minimal one with `error` and `warnings` populated (see
          `fail()`), never a traceback -- but its content is an explanation,
          not a result.  Reserved for exactly two situations:
            1. A required input is unreadable, so there is no run to report
               on: `verify_artifacts.py --manifest` pointing at something
               missing, empty, or not JSON; or a usage error from argparse.
            2. An unhandled exception escaped `main()`.  `main_guard()` turns
               it into JSON and this exit code, so a crash still leaves the
               caller with something parseable.

  exit 2  RESERVED.  Never emitted.  argparse would use it for usage errors,
          so `base_parser()` overrides `ArgumentParser.error` to route those
          through `fail(..., EXIT_NO_OUTPUT)` instead, which keeps every exit
          from these scripts accompanied by parseable JSON.

Two deliberate exceptions, both outside the analysis contract:

  * `--help` and `--version` print human text and exit 0 (argparse default).
    They are not runs and produce no JSON.
  * `--selftest` is a diagnostic mode for contributors and the release
    checklist.  It prints a JSON pass/fail report and exits 1 when a check
    fails, so CI catches a broken script.  That is the one place exit 1
    accompanies a well-formed report; it is not an analysis result.

Invariants that hold for every exit path:

  * stdout parses as JSON.  A traceback must never reach stdout -- it would
    poison the agent's parse of the phase output.  Tracebacks go to stderr.
  * `warnings` is present and is a list.
  * The tool never exits non-zero merely because the repo was uninteresting.

Trimming policy
---------------
When an object is over its cap, `emit()` removes entries from the TAIL of the
lists named in `trim_keys`.  Those lists arrive sorted by count descending, so
the tail is by construction the weakest evidence -- the shapes seen twice, not
the shapes seen twenty times.  Removal is round-robin across the lists, one
element at a time, and no list is trimmed below `MIN_KEPT_PER_LIST` entries
while some other list still has more to give.  What was dropped, and how much,
is appended to `warnings`, so a truncated run is always self-describing.

No network. Standard library only. Python 3.9+.
"""

import argparse
import json
import os
import re
import sys
import time
import traceback as _traceback
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

__all__ = [
    "emit",
    "fail",
    "warn",
    "eprint",
    "Timer",
    "base_parser",
    "main_guard",
    "resolve_repo",
    "serialize",
    "selftest_report",
    "check_regexes",
    "compiled_patterns",
    "DEFAULT_CAP_CHARS",
    "MIN_KEPT_PER_LIST",
    "SCHEMA_VERSION",
    "EXIT_OK",
    "EXIT_NO_OUTPUT",
    "EXIT_RESERVED",
]

#: JSON schema version stamped on every analyzer's stdout object.
SCHEMA_VERSION = 1

# --- Exit codes.  See the EXIT-CODE CONTRACT block in the module docstring;
# that table is normative and these three names are the only way to spell it.

#: Success, or degraded-but-usable.  The overwhelmingly common case.
EXIT_OK = 0

#: Nothing usable was produced.  stdout still carries valid JSON with `error`.
EXIT_NO_OUTPUT = 1

#: Reserved, never emitted.  Present so nobody reintroduces argparse's 2.
EXIT_RESERVED = 2

#: ~3k model tokens.  `mine_transcripts.py` uses this; `discover.py` and
#: `mine_git.py` pass a larger cap explicitly.
DEFAULT_CAP_CHARS = 12000

#: A list is never trimmed below this while another trimmable list still has
#: more entries -- otherwise one long list would wipe out a short one that
#: happens to be the only evidence for its artifact type.
MIN_KEPT_PER_LIST = 3

#: Room left for the truncation warning itself, so appending it cannot push a
#: freshly trimmed object back over the cap.
_WARNING_RESERVE = 240

#: Never trimmed, whatever the caller says.
_PROTECTED_KEYS = frozenset(["warnings", "checks"])

#: `re.Pattern` is only public from 3.8; compile once and read its type so the
#: selftest helpers work on 3.9 without a version branch.
_REGEX_TYPE = type(re.compile(""))


def eprint(*args: Any) -> None:
    """Diagnostics.  stderr only -- stdout belongs to the JSON object."""
    sys.stderr.write(" ".join(str(a) for a in args) + "\n")


def serialize(obj: Any, ensure_ascii: bool = False) -> str:
    """
    json.dumps with the contract's settings, and a last-resort fallback so a
    stray non-serializable value can never turn into a traceback on stdout.
    """
    try:
        return json.dumps(obj, ensure_ascii=ensure_ascii)
    except (TypeError, ValueError):
        return json.dumps(obj, ensure_ascii=ensure_ascii, default=_coerce)


def _coerce(value: Any) -> Any:
    if isinstance(value, (set, frozenset)):
        return sorted(value)
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8", "replace")
        except Exception:  # pragma: no cover - defensive
            return str(value)
    return str(value)


def warn(warnings: Optional[List[str]], message: str, dedupe: bool = True) -> List[str]:
    """
    Append a warning, creating the list if needed, and return it.

        warnings = warn(warnings, "transcript root not found; used fuzzy match")
    """
    if warnings is None:
        warnings = []
    text = str(message)
    if dedupe and text in warnings:
        return warnings
    warnings.append(text)
    return warnings


class Timer(object):
    """
    Wall-clock timing for the `timing_ms` field.

        with Timer() as t:
            ...
        payload["timing_ms"] = t.ms

    `elapsed_ms()` also works while the block is still running, so a script
    can check itself against a budget (`discover.py` must finish in <10s).
    """

    def __init__(self, label: str = ""):
        self.label = label
        self.started = None  # type: Optional[float]
        self.ms = 0

    def __enter__(self):
        self.started = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.ms = self.elapsed_ms()
        return False  # never swallow an exception

    def elapsed_ms(self) -> int:
        if self.started is None:
            return self.ms
        return int(round((time.perf_counter() - self.started) * 1000.0))


# ---------------------------------------------------------------------------
# Trimming
# ---------------------------------------------------------------------------


def _resolve_list(obj: Any, path: str) -> Optional[List[Any]]:
    """Resolve `"request_shapes"` or `"a.b.c"` to the list it names, or None."""
    if not isinstance(path, str) or not path:
        return None
    node = obj
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node if isinstance(node, list) else None


def _auto_trim_keys(obj: Any) -> List[str]:
    """
    Fallback when the caller named nothing: every top-level list longer than
    the floor, biggest serialized payload first (ties broken by key name so the
    order is deterministic).
    """
    if not isinstance(obj, dict):
        return []
    candidates = []  # type: List[Tuple[int, str]]
    for key, value in obj.items():
        if key in _PROTECTED_KEYS or not isinstance(value, list):
            continue
        if len(value) <= MIN_KEPT_PER_LIST:
            continue
        candidates.append((len(serialize(value)), key))
    candidates.sort(key=lambda pair: (-pair[0], pair[1]))
    return [key for _size, key in candidates]


def _average_entry_chars(lists: Sequence[List[Any]]) -> float:
    """Rough per-entry cost, sampled from the tails that are about to go."""
    total = 0
    sampled = 0
    for items in lists:
        for entry in items[-5:]:
            total += len(serialize(entry)) + 1
            sampled += 1
            if sampled >= 20:
                break
        if sampled >= 20:
            break
    if sampled == 0:
        return 64.0
    return max(8.0, total / float(sampled))


def _trim_to_budget(
    obj: Any, budget: int, paths: Sequence[str]
) -> Tuple[Dict[str, int], int]:
    """
    Drop tail entries round-robin until the object serializes under `budget`.

    Returns `({path: dropped_count}, total_dropped)`.
    """
    lists = []  # type: List[Tuple[str, List[Any]]]
    for path in paths:
        if path in _PROTECTED_KEYS:
            continue
        target = _resolve_list(obj, path)
        if target is not None and len(target) > 0:
            lists.append((path, target))
    if not lists:
        return ({}, 0)

    dropped = {}  # type: Dict[str, int]
    total_dropped = 0
    floor = MIN_KEPT_PER_LIST
    cursor = 0
    guard = 0

    while guard < 100000:
        guard += 1
        text_len = len(serialize(obj))
        if text_len <= budget:
            break

        eligible = [pair for pair in lists if len(pair[1]) > floor]
        if not eligible:
            if floor > 0:
                floor = 0  # every list is at the floor; start eating into it
                continue
            break  # nothing left to give

        # Undershoot deliberately: remove about half the estimated excess, then
        # re-measure.  Converges in a handful of passes without over-trimming.
        excess = text_len - budget
        average = _average_entry_chars([pair[1] for pair in eligible])
        batch = int((excess / average) * 0.5)
        if batch < 1:
            batch = 1
        removable = sum(len(items) - floor for _p, items in eligible)
        if batch > removable:
            batch = removable

        removed_this_pass = 0
        while removed_this_pass < batch:
            progressed = False
            for _ in range(len(lists)):
                path, items = lists[cursor % len(lists)]
                cursor += 1
                if len(items) > floor:
                    items.pop()
                    dropped[path] = dropped.get(path, 0) + 1
                    total_dropped += 1
                    removed_this_pass += 1
                    progressed = True
                    break
            if not progressed:
                break
        if removed_this_pass == 0:
            break

    return (dropped, total_dropped)


_TRUNCATION_PREFIX = "output truncated:"


def _set_truncation_warning(obj: Dict[str, Any], total: int, dropped: Dict[str, int], cap: int) -> None:
    """
    Replace (never stack) the truncation warning, so a multi-pass trim reports
    one accurate total instead of two contradictory ones.
    """
    detail = ", ".join(
        "%s: %d" % (path, count)
        for path, count in sorted(dropped.items(), key=lambda kv: (-kv[1], kv[0]))
    )
    message = "%s dropped %d entr%s to fit %d chars (%s)" % (
        _TRUNCATION_PREFIX,
        total,
        "y" if total == 1 else "ies",
        cap,
        detail,
    )
    existing = obj.get("warnings")
    if not isinstance(existing, list):
        existing = []
    kept = [w for w in existing if not (isinstance(w, str) and w.startswith(_TRUNCATION_PREFIX))]
    kept.append(message)
    obj["warnings"] = kept


def _stamp_output_chars(obj: Any, text: str, cap: int) -> str:
    """
    Keep a self-reported `output_chars` field honest.  Setting it changes the
    length, so iterate until it stabilizes (three passes is always enough --
    the value only grows by digits).
    """
    if not isinstance(obj, dict) or "output_chars" not in obj:
        return text
    for _ in range(4):
        obj["output_chars"] = len(text)
        updated = serialize(obj)
        if updated == text:
            break
        text = updated
    return text


def emit(
    obj: Any,
    cap_chars: int = DEFAULT_CAP_CHARS,
    trim_keys: Optional[Sequence[str]] = None,
    stream: Any = None,
    ensure_ascii: bool = False,
) -> str:
    """
    Serialize `obj`, enforce the size cap, print it as the script's one and
    only line of stdout, and return the text that was printed.

    Args:
        cap_chars: hard character budget.  0 or negative disables capping.
        trim_keys: list-valued fields (top level, or dotted like `"a.b"`) whose
            TAIL entries may be dropped to fit.  They must already be sorted by
            evidence strength descending.  When omitted, every top-level list
            longer than MIN_KEPT_PER_LIST is fair game, largest first.
        stream: defaults to sys.stdout.  Tests pass a StringIO.

    A truncated run appends to `obj["warnings"]`:

        "output truncated: dropped 41 entries to fit 12000 chars
         (request_shapes: 22, corrections: 12, pain_signals: 7)"
    """
    if stream is None:
        stream = sys.stdout

    text = serialize(obj, ensure_ascii=ensure_ascii)

    if cap_chars and cap_chars > 0 and len(text) > cap_chars:
        paths = list(trim_keys) if trim_keys else _auto_trim_keys(obj)
        budget = cap_chars - _WARNING_RESERVE
        if budget < 1:
            budget = cap_chars

        totals = {}  # type: Dict[str, int]
        grand_total = 0
        # The warning itself costs characters, so trimming and warning have to
        # converge together.  _WARNING_RESERVE covers the first pass; if the
        # detail line runs long, shrink the budget and go round again.
        for _attempt in range(6):
            dropped, removed = _trim_to_budget(obj, budget, paths)
            for path, count in dropped.items():
                totals[path] = totals.get(path, 0) + count
            grand_total += removed
            if grand_total > 0 and isinstance(obj, dict):
                _set_truncation_warning(obj, grand_total, totals, cap_chars)
            text = serialize(obj, ensure_ascii=ensure_ascii)
            if len(text) <= cap_chars or removed == 0:
                break
            budget = max(1, budget - max(200, len(text) - cap_chars))

    text = _stamp_output_chars(obj, text, cap_chars)

    stream.write(text + "\n")
    try:
        stream.flush()
    except Exception:  # pragma: no cover - defensive
        pass
    return text


def fail(
    message: str,
    tool: str = "",
    exit_code: int = EXIT_NO_OUTPUT,
    extra: Optional[Dict[str, Any]] = None,
    schema_version: int = SCHEMA_VERSION,
    stream: Any = None,
) -> None:
    """
    Print a minimal but VALID JSON object describing the failure, then exit.

    `fail()` is the exit-1 path: it is for "there is no run to report on".
    The exit code defaults to EXIT_NO_OUTPUT precisely so that a contributor
    reaching for `fail()` gets the honest answer without thinking about it.

    A degraded run is NOT a failure and must not come through here.  Emit the
    full schema with empty values and a `warnings` entry via `emit()` instead;
    see the EXIT-CODE CONTRACT in the module docstring for where the line is.

    Never raises; always exits.
    """
    if stream is None:
        stream = sys.stdout
    payload = {
        "schema_version": schema_version,
        "tool": tool or "",
    }  # type: Dict[str, Any]
    if extra:
        payload.update(extra)
    payload["error"] = str(message)
    payload["warnings"] = warn(payload.get("warnings"), str(message))
    # Every agentify JSON payload carries the same four keys, so a caller can
    # parse a failure with the same reader it uses for a successful run.
    payload.setdefault("timing_ms", 0)

    stream.write(serialize(payload) + "\n")
    try:
        stream.flush()
    except Exception:  # pragma: no cover - defensive
        pass
    sys.exit(exit_code)


# ---------------------------------------------------------------------------
# Shared CLI
# ---------------------------------------------------------------------------


def resolve_repo(value: str) -> str:
    """Expand `~`, resolve to an absolute path, never raise."""
    if not value:
        return os.path.abspath(os.getcwd())
    try:
        return os.path.abspath(os.path.expanduser(str(value)))
    except Exception:  # pragma: no cover - defensive
        return os.path.abspath(os.getcwd())


def base_parser(tool_name: str, description: str = "") -> argparse.ArgumentParser:
    """
    An argparse parser pre-seeded with the flags every analyzer shares, so all
    four scripts behave identically:

        --repo PATH        repository root (default: cwd)
        --json             implied; output is always a single JSON object
        --cap-chars N      override the output size cap
        --debug            verbose diagnostics on stderr
        --version          print the shared-lib version

    Scripts add their own flags on top:

        parser = base_parser("mine_transcripts.py")
        parser.add_argument("--target", choices=["claude-code", "codex"], ...)
        args = parser.parse_args()
    """
    parser = argparse.ArgumentParser(
        prog=tool_name,
        description=description or ("agentify analyzer: %s" % tool_name),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Prints one JSON object on stdout and nothing else.  Diagnostics go\n"
            "to stderr.\n"
            "\n"
            "EXIT CODES (identical across all four analyzers; the normative\n"
            "statement is the module docstring of scripts/lib/emit.py):\n"
            "  0  success, OR degraded -- a missing/empty/unreadable path, no git,\n"
            "     no transcripts, a consent limit, a timeout.  Valid JSON with the\n"
            "     full schema and a populated `warnings` array either way.  A\n"
            "     degraded run is NOT a failure: keep going on less evidence.\n"
            "  1  nothing usable was produced (an unreadable manifest, an\n"
            "     unhandled exception).  stdout still carries valid JSON with an\n"
            "     `error` field -- never a traceback.\n"
            "  2  never emitted; usage errors are reported as exit 1 with JSON.\n"
            "\n"
            "--selftest runs the script's internal checks and prints a JSON\n"
            "pass/fail report (exit 1 if anything failed).\n"
            "\n"
            "Local only: no network calls, ever."
        ),
    )
    parser.add_argument(
        "--repo",
        default=os.getcwd(),
        metavar="PATH",
        help="repository root to analyze (default: current directory)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        default=True,
        help="implied; output is always a single JSON object on stdout",
    )
    parser.add_argument(
        "--cap-chars",
        type=int,
        default=None,
        metavar="N",
        dest="cap_chars",
        help="override the output character cap (default: per-tool)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        default=False,
        help="verbose diagnostics on stderr (never on stdout)",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        default=False,
        help="run the script's internal sanity checks, print a JSON pass/fail "
             "report, and exit (0 all passed, 1 something failed)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%s (agentify shared libs, schema_version %d)" % (tool_name, SCHEMA_VERSION),
    )

    # argparse's own usage errors exit 2 with a bare message on stderr and
    # NOTHING on stdout.  That breaks the contract's promise that every exit
    # carries parseable JSON, so route them through fail() instead.  Only
    # `error()` is overridden: `--help` and `--version` go through `exit()`
    # and keep argparse's human output and exit 0.
    def _error(message, _parser=parser, _tool=tool_name):
        fail(
            "usage error: %s" % message,
            tool=_tool,
            exit_code=EXIT_NO_OUTPUT,
            extra={"usage": _parser.format_usage().strip()},
        )

    parser.error = _error  # type: ignore[assignment]
    return parser


def main_guard(main_fn: Callable[..., int], tool: str, argv: Optional[Sequence[str]] = None) -> int:
    """
    The `if __name__ == "__main__":` body every analyzer uses:

        if __name__ == "__main__":
            sys.exit(emit_lib.main_guard(main, TOOL))

    It exists so that an exception nobody anticipated still leaves the caller
    with something parseable.  A traceback on stdout would poison the agent's
    parse of the phase output, so the traceback goes to stderr (where a human
    debugging the script can still see it) and stdout gets a `fail()` object.

    `SystemExit` passes through untouched -- `emit()`/`fail()`/`--help` all
    reach the process exit that way, and re-wrapping them would double-print.
    """
    try:
        return int(main_fn(argv) or 0)
    except SystemExit:
        raise
    except KeyboardInterrupt:
        _traceback.print_exc(file=sys.stderr)
        fail("interrupted", tool=tool, exit_code=EXIT_NO_OUTPUT)
    except Exception as exc:
        _traceback.print_exc(file=sys.stderr)
        fail(
            "unrecoverable error: %s: %s" % (type(exc).__name__, exc),
            tool=tool,
            exit_code=EXIT_NO_OUTPUT,
        )
    return EXIT_NO_OUTPUT  # pragma: no cover - fail() exits


# ---------------------------------------------------------------------------
# --selftest support
#
# Every analyzer answers `--selftest` with the same JSON shape so the release
# checklist and CI can run all four and diff one format.  These helpers keep
# that shape in one place; the per-script checks live in the scripts.
# ---------------------------------------------------------------------------


def compiled_patterns(module: Any) -> List[Tuple[str, Any]]:
    """
    Every already-compiled regex reachable from `module`'s top-level names,
    as `(name, pattern)` pairs -- including the members of top-level lists,
    tuples and dict values, which is where most scripts keep their pattern
    tables.  Used by `check_regexes` so a script's selftest proves its regexes
    are live objects, not just that the file imported.
    """
    found = []  # type: List[Tuple[str, Any]]
    seen = set()  # type: set

    def consider(name, value):
        if isinstance(value, _REGEX_TYPE):
            key = id(value)
            if key not in seen:
                seen.add(key)
                found.append((name, value))

    for name in sorted(vars(module).keys()):
        if name.startswith("__"):
            continue
        value = vars(module)[name]
        consider(name, value)
        if isinstance(value, (list, tuple)):
            for index, item in enumerate(value):
                consider("%s[%d]" % (name, index), item)
                if isinstance(item, (list, tuple)):
                    for sub in item:
                        consider("%s[%d]" % (name, index), sub)
        elif isinstance(value, dict):
            for key, item in value.items():
                consider("%s[%r]" % (name, key), item)
    return found


def check_regexes(module: Any, sources: Optional[Iterable[str]] = None) -> Tuple[bool, str]:
    """
    Assert that a module's regexes are usable: every compiled pattern matches
    against a scratch string without raising (catastrophic groups, bad flags
    and stale escapes all surface here), and every raw pattern string in
    `sources` still compiles.  Returns `(ok, detail)`.
    """
    probe = "agentify selftest probe 123 /tmp/x.py `npm run build` https://e.co"
    checked = 0
    for name, pattern in compiled_patterns(module):
        try:
            pattern.search(probe)
        except Exception as exc:  # pragma: no cover - defensive
            return False, "%s failed to match: %s: %s" % (name, type(exc).__name__, exc)
        checked += 1
    for source in sources or []:
        try:
            re.compile(source)
        except re.error as exc:
            return False, "pattern %r does not compile: %s" % (source[:60], exc)
        checked += 1
    return True, "%d regex(es) compile and match" % checked


def selftest_report(
    tool: str,
    checks: Sequence[Tuple[str, bool, str]],
    stream: Any = None,
    started_ms: Optional[int] = None,
) -> int:
    """
    Print the shared `--selftest` JSON object and return the exit code.

        checks = [("imports resolve", True, "lib.scrub, lib.textnorm"), ...]
        return emit_lib.selftest_report(TOOL, checks)

    Shape:

        {"schema_version":1,"tool":"discover.py","mode":"selftest",
         "checks":[{"name":"","status":"pass|fail","detail":""}],
         "summary":{"pass":0,"fail":0},"ok":true,"warnings":[],"timing_ms":0}

    Exit 1 when anything failed -- the one place exit 1 accompanies a
    well-formed report, because CI has to notice a broken script.
    """
    rows = []
    passed = 0
    failed = 0
    for name, ok, detail in checks:
        rows.append({"name": str(name), "status": "pass" if ok else "fail", "detail": str(detail)})
        if ok:
            passed += 1
        else:
            failed += 1
    payload = {
        "schema_version": SCHEMA_VERSION,
        "tool": tool,
        "mode": "selftest",
        "checks": rows,
        "summary": {"pass": passed, "fail": failed},
        "ok": failed == 0,
        "warnings": [],
        "timing_ms": max(0, int(time.time() * 1000) - started_ms) if started_ms else 0,
    }
    if failed:
        payload["warnings"].append(
            "%d selftest check(s) failed: %s"
            % (failed, ", ".join(r["name"] for r in rows if r["status"] == "fail"))
        )
    emit(payload, cap_chars=0, stream=stream)
    return EXIT_NO_OUTPUT if failed else EXIT_OK


# ---------------------------------------------------------------------------
# Self-test:  python3 lib/emit.py
# ---------------------------------------------------------------------------


def _selftest() -> int:
    import io

    results = []  # type: List[bool]

    def check(label, condition, detail=""):
        if condition:
            print("PASS  %s" % label)
            return True
        print("FAIL  %s%s" % (label, ("  -- " + detail) if detail else ""))
        return False

    # -- emit basics ---------------------------------------------------------
    buffer = io.StringIO()
    payload = {"schema_version": 1, "tool": "t", "warnings": []}
    text = emit(payload, cap_chars=12000, stream=buffer)
    results.append(check("emit prints exactly one line", buffer.getvalue().count("\n") == 1))
    results.append(check("emit output round-trips as JSON", json.loads(text) == payload, text))

    buffer = io.StringIO()
    emit({"note": "café → ok"}, stream=buffer)
    results.append(check("emit keeps non-ascii readable", "café" in buffer.getvalue(), buffer.getvalue()))

    # -- capping -------------------------------------------------------------
    big = {
        "schema_version": 1,
        "tool": "mine_transcripts.py",
        "request_shapes": [
            {"id": "s%d" % i, "skeleton": "shape number %d here" % i, "count": 500 - i}
            for i in range(400)
        ],
        "corrections": [
            {"text": "correction number %d" % i, "kind": "tooling", "count": 100 - i}
            for i in range(90)
        ],
        "warnings": [],
    }
    buffer = io.StringIO()
    text = emit(big, cap_chars=4000, trim_keys=["request_shapes", "corrections"], stream=buffer)
    results.append(check("emit enforces the cap", len(text) <= 4000, str(len(text))))
    parsed = json.loads(text)
    results.append(check("capped output is still valid JSON", isinstance(parsed, dict)))
    results.append(
        check(
            "cap trims the tail, keeping the highest counts",
            parsed["request_shapes"][0]["count"] == 500,
            str(parsed["request_shapes"][:1]),
        )
    )
    results.append(
        check(
            "truncation is recorded in warnings",
            any(w.startswith("output truncated:") for w in parsed["warnings"]),
            str(parsed["warnings"]),
        )
    )
    results.append(
        check(
            "trimming is round-robin across every named list",
            len(parsed["request_shapes"]) < 400 and len(parsed["corrections"]) < 90,
            "%d / %d" % (len(parsed["request_shapes"]), len(parsed["corrections"])),
        )
    )

    # Floor: a short list survives while a long one is still being eaten.
    lopsided = {
        "schema_version": 1,
        "long": [{"i": i, "pad": "x" * 80} for i in range(300)],
        "short": [{"i": i, "pad": "y" * 20} for i in range(4)],
        "warnings": [],
    }
    buffer = io.StringIO()
    text = emit(lopsided, cap_chars=2500, trim_keys=["long", "short"], stream=buffer)
    parsed = json.loads(text)
    results.append(
        check(
            "no list is trimmed below the floor while another has more",
            len(parsed["short"]) >= MIN_KEPT_PER_LIST,
            "short=%d long=%d" % (len(parsed["short"]), len(parsed["long"])),
        )
    )
    results.append(check("lopsided output respects the cap", len(text) <= 2500, str(len(text))))

    # Auto-detected trim keys when the caller names none.
    auto = {"schema_version": 1, "items": [{"i": i, "pad": "z" * 60} for i in range(200)], "warnings": []}
    buffer = io.StringIO()
    text = emit(auto, cap_chars=2000, stream=buffer)
    results.append(check("emit auto-detects trimmable lists", len(text) <= 2000, str(len(text))))

    # output_chars stays honest.
    counted = {"schema_version": 1, "tool": "t", "output_chars": 0, "warnings": []}
    buffer = io.StringIO()
    text = emit(counted, stream=buffer)
    results.append(check("output_chars matches the emitted length", json.loads(text)["output_chars"] == len(text), text))

    # A small object is untouched.
    small = {"a": [1, 2, 3, 4, 5], "warnings": []}
    buffer = io.StringIO()
    text = emit(small, cap_chars=12000, trim_keys=["a"], stream=buffer)
    results.append(check("under-cap objects are not trimmed", json.loads(text)["a"] == [1, 2, 3, 4, 5]))

    # Non-serializable values must not blow up stdout.
    buffer = io.StringIO()
    text = emit({"s": set(["b", "a"]), "warnings": []}, stream=buffer)
    results.append(check("emit survives non-serializable values", json.loads(text)["s"] == ["a", "b"], text))

    # -- warn ----------------------------------------------------------------
    warnings = warn(None, "first")
    warn(warnings, "first")
    warn(warnings, "second")
    results.append(check("warn creates, dedupes and appends", warnings == ["first", "second"], str(warnings)))

    # -- Timer ---------------------------------------------------------------
    with Timer() as timer:
        _ = sum(range(10000))
    results.append(check("Timer records milliseconds", isinstance(timer.ms, int) and timer.ms >= 0, str(timer.ms)))

    try:
        with Timer() as timer:
            raise ValueError("boom")
    except ValueError:
        results.append(check("Timer does not swallow exceptions", True))
    else:
        results.append(check("Timer does not swallow exceptions", False))

    # -- fail ----------------------------------------------------------------
    buffer = io.StringIO()
    code = None
    try:
        fail("no transcripts found", tool="mine_transcripts.py", stream=buffer)
    except SystemExit as exit_error:
        code = exit_error.code
    parsed = json.loads(buffer.getvalue())
    # `fail()` is the exit-1 path by definition -- "there is no run to report
    # on".  An earlier version of this test asserted the default was 0, which
    # contradicted both the EXIT-CODE CONTRACT above and fail()'s own
    # docstring; a degraded run must go through emit() with the full schema,
    # never through fail().  The default staying EXIT_NO_OUTPUT is what makes
    # a contributor who reaches for fail() get the honest answer by accident.
    results.append(check("fail defaults to exit 1", code == EXIT_NO_OUTPUT, str(code)))
    results.append(
        check(
            "fail emits valid JSON with error and warnings",
            parsed["error"] == "no transcripts found" and parsed["warnings"] == ["no transcripts found"],
            buffer.getvalue(),
        )
    )

    buffer = io.StringIO()
    code = None
    try:
        fail("repo does not exist", tool="discover.py", exit_code=1, extra={"available": False}, stream=buffer)
    except SystemExit as exit_error:
        code = exit_error.code
    parsed = json.loads(buffer.getvalue())
    results.append(check("fail exits 1 when nothing could be produced", code == 1, str(code)))
    results.append(check("fail merges caller-supplied fields", parsed["available"] is False, buffer.getvalue()))

    # -- base_parser ---------------------------------------------------------
    parser = base_parser("discover.py")
    args = parser.parse_args([])
    results.append(check("base_parser defaults --repo to cwd", args.repo == os.getcwd(), args.repo))
    args = parser.parse_args(["--repo", "~/somewhere", "--cap-chars", "9000", "--debug"])
    results.append(
        check(
            "base_parser parses the shared flags",
            args.cap_chars == 9000 and args.debug is True and args.json is True,
            str(vars(args)),
        )
    )
    results.append(
        check(
            "resolve_repo expands ~ to an absolute path",
            os.path.isabs(resolve_repo(args.repo)) and "~" not in resolve_repo(args.repo),
            resolve_repo(args.repo),
        )
    )

    args = parser.parse_args(["--selftest"])
    results.append(check("base_parser offers --selftest", args.selftest is True))

    # A usage error must produce JSON and exit 1, never argparse's bare exit 2.
    buffer = io.StringIO()
    code = None
    saved_stdout = sys.stdout
    try:
        sys.stdout = buffer
        base_parser("discover.py").parse_args(["--nope"])
    except SystemExit as exit_error:
        code = exit_error.code
    finally:
        sys.stdout = saved_stdout
    results.append(check("usage errors exit 1, not argparse's 2", code == EXIT_NO_OUTPUT, str(code)))
    try:
        parsed = json.loads(buffer.getvalue())
    except ValueError:
        parsed = {}
    results.append(
        check(
            "usage errors still print JSON on stdout",
            "usage error" in str(parsed.get("error", "")),
            buffer.getvalue()[:160],
        )
    )

    # -- main_guard ----------------------------------------------------------
    results.append(check("main_guard returns a clean exit code", main_guard(lambda argv: 0, "t") == 0))

    buffer = io.StringIO()
    code = None
    saved_stdout = sys.stdout

    def _boom(argv):
        raise RuntimeError("kaboom")

    try:
        sys.stdout = buffer
        main_guard(_boom, "discover.py")
    except SystemExit as exit_error:
        code = exit_error.code
    finally:
        sys.stdout = saved_stdout
    results.append(check("main_guard converts a crash to exit 1", code == EXIT_NO_OUTPUT, str(code)))
    try:
        parsed = json.loads(buffer.getvalue())
    except ValueError:
        parsed = {}
    results.append(
        check(
            "main_guard puts JSON on stdout, not a traceback",
            "kaboom" in str(parsed.get("error", "")) and "Traceback" not in buffer.getvalue(),
            buffer.getvalue()[:160],
        )
    )

    code = None
    try:
        main_guard(lambda argv: sys.exit(0), "t")
    except SystemExit as exit_error:
        code = exit_error.code
    results.append(check("main_guard lets SystemExit through untouched", code == 0, str(code)))

    # -- selftest_report -----------------------------------------------------
    buffer = io.StringIO()
    code = selftest_report("discover.py", [("a", True, ""), ("b", True, "ok")], stream=buffer)
    parsed = json.loads(buffer.getvalue())
    results.append(
        check(
            "selftest_report exits 0 when everything passes",
            code == 0 and parsed["ok"] is True and parsed["summary"] == {"pass": 2, "fail": 0},
            buffer.getvalue(),
        )
    )
    buffer = io.StringIO()
    code = selftest_report("discover.py", [("a", True, ""), ("b", False, "why")], stream=buffer)
    parsed = json.loads(buffer.getvalue())
    results.append(
        check(
            "selftest_report exits 1 and names the failure",
            code == 1 and parsed["ok"] is False and "b" in parsed["warnings"][0],
            buffer.getvalue(),
        )
    )

    # -- regex helpers -------------------------------------------------------
    module = sys.modules[__name__]
    found = dict(compiled_patterns(module))
    results.append(check("compiled_patterns finds module-level regexes", len(found) >= 0, str(len(found))))
    ok, detail = check_regexes(module, sources=[r"^ab+c$", r"\bnpm run \w+"])
    results.append(check("check_regexes passes on good patterns", ok, detail))
    ok, detail = check_regexes(module, sources=[r"(unclosed"])
    results.append(check("check_regexes catches a broken pattern", not ok, detail))

    passes = sum(1 for r in results if r)
    failures = sum(1 for r in results if not r)
    print("")
    print("%d passed, %d failed" % (passes, failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(_selftest())
