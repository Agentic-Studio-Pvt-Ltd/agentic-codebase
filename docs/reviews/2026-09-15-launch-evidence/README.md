# Launch audit evidence

Audit date: **15 September 2026**. Product revision: `c159c58217cd515eedf322db7af0bbce6ee17aa5`.

This directory preserves reproducible observations, not repaired product tests. A probe can exit successfully while demonstrating a product defect. Compare its JSON values against the expected behavior in the launch report. Future fixes should turn these cases into ordinary regression tests with passing expectations.

## Contents

| Probe | Report findings | What it exercises |
|---|---|---|
| `probes/analyzers.py` | F03, F04, F14 | Shared scrubber, outside-root secret-file symlink and missing protection metadata |
| `probes/codex_hooks.py` | F01, F02; packaging | Actual rendered Codex hook and extracted payload parser; distribution link |
| `probes/transcripts.py` | F05, F10, F11, F12 | Miner entry point with synthetic Codex/Claude records and fixture config resolvers |
| `probes/verification.py` | F01, F06, F08, F09, F13 | Registration checks, embedded undo helper, mocked timeout behavior, heredoc network gate and malformed TOML |
| `probes/git_paths.py` | F15 | Unicode filename through a real temporary git repository |

F07, F16 and F17 are instruction-level findings established by comparing source passages; they are not represented as executed model workflows.

`results/` contains outputs from all five probes and all four built-in suites. `inventory.json` accounts for every tracked baseline file, with SHA-256 hashes for text files, logical line counts, document headings, Python definitions and release-placeholder locations. Paths and usernames inside probe outputs refer to temporary/synthetic fixtures, apart from the intentionally recorded broken distribution symlink.

## Reproduce

Run from the repository root using **Python 3.11+**, git, Bash and a POSIX shell. The audit harness uses `tomllib` as an independent parser; this requirement does not change the product's declared Python 3.9 minimum. Results here were produced with Python 3.14.3.

```sh
python3 docs/reviews/2026-09-15-launch-evidence/probes/analyzers.py
python3 docs/reviews/2026-09-15-launch-evidence/probes/codex_hooks.py
python3 docs/reviews/2026-09-15-launch-evidence/probes/transcripts.py
python3 docs/reviews/2026-09-15-launch-evidence/probes/verification.py
python3 docs/reviews/2026-09-15-launch-evidence/probes/git_paths.py
```

Each probe prints JSON and cleans up its temporary fixtures. They do not change product files. The transcript probe calls the actual CLI entry function while mocking configuration-directory resolution; it does not redirect the user's environment variables or inspect their histories. The git probe creates a commit only inside its throwaway repository, disables commit hooks/signing for that commit, and uses `--no-gh`.

The verification probe mocks **both** process-group lookup and signaling on the timeout path. Keep those mocks: reproducing the group-kill defect with real signals would be unsafe. Network examples are only scanned or executed with a local stub function; no external endpoint is called. The undo probe extracts pure helper definitions and does not execute the reference's filesystem mutation loop.

The Codex hook probe intentionally renders the pre-fix matcher. After changing the adapter's contract, update the fixture to derive the corrected matcher and expected runtime event rather than retaining that hardcoded historical value. The parser extraction also depends on the audited template's current delimiters.

## Recorded built-in suites

| Result file | Pass | Fail |
|---|---:|---:|
| `results/discover-selftest.json` | 73 | 0 |
| `results/mine-git-selftest.json` | 26 | 0 |
| `results/mine-transcripts-selftest.json` | 35 | 0 |
| `results/verifier-selftest.json` | 82 | 0 |

These are a dated snapshot, not permanent expected suite sizes. No live Codex activation, model dispatch, authenticated MCP connection, public installation or full setup/undo lifecycle is certified by these results.
