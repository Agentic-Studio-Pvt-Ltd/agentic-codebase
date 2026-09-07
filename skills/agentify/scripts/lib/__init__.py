# -*- coding: utf-8 -*-
"""
agentify :: scripts/lib

Shared, dependency-free helpers for the agentify analyzer scripts.

Three modules, each usable standalone (`python3 lib/<name>.py` runs its
self-test):

    scrub     secret redaction + secret-filename detection.  Everything that
              leaves a script -- transcript text, examples, file paths --
              passes through here FIRST.  PRD 13, contract "Shared libs".
    textnorm  prompt normalization, verb+object skeletonization, clustering,
              correction detection, command extraction, service lexicon.
    emit      single-JSON-object stdout emission, hard output caps, warning
              helpers, shared argparse flags, timing.

Rules that apply to every module in this package:

* Python 3.9+ compatible syntax.  No `match`, no PEP 604 (`X | Y`) unions at
  runtime, no dataclass slots, no walrus in comprehension-heavy code.
* Standard library only.  No pip installs, ever.
* No network calls.  Not now, not behind a flag.
* Nothing is printed to stdout except by `emit.emit()` / `emit.fail()`.
  Diagnostics go to stderr.

Scripts live one directory up (`scripts/discover.py` etc.), so when they are
run as `python3 "$SKILL_DIR/scripts/discover.py"` the `scripts/` directory is
`sys.path[0]` and `from lib import scrub` resolves without any path juggling.

Submodules are intentionally NOT imported here: a syntax or import error in
one module must not take down the other two, and `discover.py` should be able
to load `scrub` without paying for `textnorm`.  Import explicitly:

    from lib import scrub, textnorm, emit
    from lib.scrub import scrub, is_secret_path
"""

__all__ = ["scrub", "textnorm", "emit"]

# Bumped only when a shared-lib signature changes in a way callers must know
# about.  Independent of the JSON `schema_version` the scripts emit.
__version__ = "1.0.0"

# Schema version every analyzer script stamps on its stdout JSON.  Kept here so
# the four scripts cannot drift apart.
SCHEMA_VERSION = 1
