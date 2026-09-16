# Agentify repair verification — 16 September 2026

## Result

Verified the 17 repair commits through `8bb32e1b8c000b6a946bb5c3e699a50269f5b7d3` against the September 15 audit baseline, and applied remaining concrete fixes locally. **305 checks pass on each of Python 3.14.3 and Python 3.9.6**: 283 analyzer selftests plus 22 integration/regression tests.

The Codex template defects reproduced in this review are fixed. This is **not a complete live launch certification**: the model-driven build/rerun/undo journey has not been run, new hook trust and custom-agent activation remain manual checks, and public install commands still contain `PLACEHOLDER-ORG`. Do not publish those placeholder commands.

No commit, push, release, persistent Codex configuration change, real transcript read or credential access was performed. The staged September 15 audit and untracked `.claude/` worktrees were preserved.

## Repairs applied in this pass

| Area | Remaining defect and repair |
|---|---|
| Codex event responses | PermissionRequest and PostToolUse used PreToolUse-only output. The template now emits each event’s documented response. Prompt/stop hooks no longer require a nonexistent tool name; stop continuations avoid a blocking loop. |
| Codex file scope | A subfolder patch could match the right filter but check the wrong root file. Paths now resolve from the event cwd, filters and checks use the same repo-relative path, and every matching file is checked. |
| Hook verification | Invalid event responses and checks that never completed could look like successful allows. These now fail fixture validation instead of producing a false pass. |
| Consent | Undated or malformed ordinary user turns could escape a last-N-days cutoff. Both readers and fallback prompts now share a timestamp predicate, including UTC offset handling. Unbounded consent still supports undated turns. |
| Repeated requests | Partial Codex streams could erase a later genuine repeat; future parent activity could erase work in an earlier fork. Cross-stream pairing now requires nearby timestamps, and fork matching stops at the child’s creation boundary. Two older selftest fixtures were corrected to give forks creation times after their copied parent turns. Expected counts were preserved. |
| Time zones | File selection interpreted naive UTC as local time. Epoch cutoffs now explicitly use UTC. |
| Redaction | Credential arrays escaped the scalar scrubber. Scalar lists now redact together, including escaped quotes and multiline lists, while nested objects retain their inner-key scan. |
| Network scan | A quoted cat heredoc passed into an outer shell interpreter was incorrectly classified as inert data. Interpreter context now keeps the network hit blocking. |
| Python 3.9/3.10 | Missing TOML parser caused an early return before rejecting `danger-full-access`. Syntax remains unverified, while the definite forbidden sandbox setting still fails. |
| Agent and skill instructions | The shared skill template now explicitly omits Codex `allowed-tools` rather than implying enforcement. The verifier accepts a valid agent whose TOML `name` differs from its filename; matching names remain a generation convention. Adapter, capability and verification instructions were synchronized. |
| Regression coverage | Added tests that execute the actual rendered Codex hook template and parse the wiring fragment, plus synthetic privacy/verifier tests. Tests include a broken canonical-tool filter as a negative control. |

## Original audit verification matrix

“Retained” means the corresponding Claude repair remains in place and its current relevant checks pass. It does not imply a live model-driven setup was generated for every possible repository.

| Finding | Disposition |
|---|---|
| F01 — canonical Bash matcher | Retained; actual rendered hook and wiring tests added. Event-response and false-pass defects repaired above. |
| F02 — apply_patch paths | Retained; object and freeform payload tests pass. Subfolder and multi-file checking repaired above. |
| F03 — quoted credentials | Retained; credential-list redaction added. |
| F04 — discovery symlink reads | Retained; discovery selftests pass. |
| F05 — fallback consent | Retained; ordinary undated/malformed turns now obey the same cutoff. |
| F06 — undo ownership | Retained; full-path and event identity logic remains, verifier selftests pass. |
| F07 — shared matcher groups | Retained; handler-level merge/preservation contract remains. |
| F08 — timeout process groups | Retained; isolated child-session handling and verifier tests pass. |
| F09 — interpreter heredocs | Additional outer-interpreter bypass fixed and regression-tested without executing a network request. |
| F10 — repeated Codex turns | Additional partial-stream and post-fork-parent cases fixed and regression-tested. |
| F11 — resumed sessions | Retained; UTC epoch conversion corrected. |
| F12 — debug remote credentials | Retained; miner tests cover output and diagnostics. |
| F13 — TOML validation | Retained; unsupported-parser mode now also enforces definite forbidden sandbox settings. |
| F14 — Codex symlink metadata | Retained; discovery checks pass. |
| F15 — Git UTF-8 paths | Retained; all 32 git-miner checks pass. |
| F16 — workflow contradictions | Earlier reconciliation retained; Codex event and shared-template contradictions corrected in this pass. |
| F17 — capabilities versus adapter | Earlier trust/path reconciliation retained; event outputs and identity/tool-restriction notes synchronized. |

## Validation evidence

| Check | Python 3.14.3 | Python 3.9.6 |
|---|---:|---:|
| discover selftest | 84 pass | 84 pass |
| mine_git selftest | 32 pass | 32 pass |
| mine_transcripts selftest | 48 pass | 48 pass |
| verify_artifacts selftest | 119 pass | 119 pass |
| Rendered-template and repair regressions | 22 pass | 22 pass |
| **Total** | **305 pass, 0 fail** | **305 pass, 0 fail** |

Run the four existing script selftests and `python3 -m unittest discover -s tests -v` to reproduce. The tests use temporary repositories, synthetic events and synthetic credentials; they are developer tooling, never steps in a real skill invocation. Whitespace validation also passes.

Evidence: [test summary](2026-09-16-repair-evidence/final-test-summary.json), [pre-fix hook output](2026-09-16-repair-evidence/codex-repro.json), [pre-fix failing integration tests](2026-09-16-repair-evidence/codex-contract-before.txt), [Python 3.14 regressions](2026-09-16-repair-evidence/py314-regressions-final.txt), [Python 3.9 regressions](2026-09-16-repair-evidence/py39-regressions-final.txt).

### Actual installed Codex binary

Tested `codex-cli 0.154.0-alpha.6.2` through read-only app-server discovery and execution-policy parsing:

- A synthetic `.agents/skills/contract-probe/SKILL.md` was discovered with repository scope.
- Rules rendered from the shipped policy template parsed successfully; matching commands returned `prompt` and `forbidden`, and an unrelated command matched no rule. No command was executed by these checks.
- The scratch repository hook did **not** appear in `hooks/list`; project trust was not established by the process-only override. This does not prove native hook loading. Script behavior and wiring syntax were tested separately, and no hook trust bypass was used.
- No custom agent was spawned. TOML/static validation is not proof of live activation.

Evidence: [native Codex probe](2026-09-16-repair-evidence/native-smoke.json). Current protocol checked against [official Codex hooks](https://learn.chatgpt.com/docs/hooks), [custom agents](https://learn.chatgpt.com/docs/agent-configuration/subagents), and [skills](https://learn.chatgpt.com/docs/build-skills).

## Remaining release work

1. Replace the public installation placeholders with the owner’s final repository/name. This remains an explicit unresolved product decision in README; no value was invented.
2. Run one real Codex setup on a disposable representative repository: approve the generated plan, build, verify, rerun, then undo. `test-repos.md` still accurately says the full live journey has not run.
3. In that repository, establish project trust, review/trust generated hooks through `/hooks`, confirm their native listing, and spawn a generated custom agent by its TOML `name`. Verify its actual permissions before calling it read-only.

Cross-stream transcript pairing still uses timestamp proximity because historical records lack a universal turn identifier; it cannot prove identity for every unusual log format. The network scanner remains a static detector, not an operating-system network sandbox. These limitations should not be described as guarantees.

## Review scope and process

This pass verified the repair diff and inspected associated instructions/templates; it is not a fresh claim to have reread every unchanged source line. Independent reviewer artifacts and an external Claude CLI pass identified the residual cases. The external receipt reports `claude-opus-5` requested and served; actual effort was unverified. Its completed job was consumed and removed.

Review used the [ce-code-review skill](/Users/ravisojitra/.codex/plugins/cache/compound-engineering-plugin/compound-engineering/3.26.3/skills/ce-code-review/SKILL.md). The later merge worker hit the account usage limit. To honor the request to finish quickly with fewer credits, the parent completed local repairs and direct regression validation; no further paid review workers were launched. A final independent review of the applied patch was not completed.
