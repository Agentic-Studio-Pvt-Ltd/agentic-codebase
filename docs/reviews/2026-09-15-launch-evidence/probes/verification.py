#!/usr/bin/env python3
"""Report-only probes. No real network and no real termination calls."""
import importlib.util
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib
from types import SimpleNamespace
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[4] / 'skills/agentify/scripts/verify_artifacts.py'
sys.path.insert(0, str(SOURCE.parent))
spec = importlib.util.spec_from_file_location('verifier_audit', SOURCE)
v = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = v
spec.loader.exec_module(v)

def verifier(repo, execute=False):
    return v.Verifier(str(repo), {'target': 'codex', 'artifacts': []}, SimpleNamespace(exec_hooks=execute, no_exec=False, hook_timeout_s=5))

results = {}
with tempfile.TemporaryDirectory(prefix='agentify-audit-verifier-') as scratch:
    repo = Path(scratch)
    baseline = 'name = "reviewer"\ndescription = "Review changed code"\ndeveloper_instructions = "Review the diff"\n'
    cases = {
        'duplicate_key': baseline + 'name = "different"\n',
        'invalid_escape': baseline.replace('Review changed code', r'Review \q changed code'),
        'unquoted_string': baseline.replace('"Review the diff"', 'Review the diff'),
        'invalid_after_table': baseline + '[extras]\nbroken = [\n',
    }
    results['invalid_agent_toml'] = {}
    for name, text in cases.items():
        check = verifier(repo)
        check._check_subagent_toml({'path': '.codex/agents/reviewer.toml', 'text': text}, 'reviewer.toml')
        try:
            tomllib.loads(text)
            parse_error = None
        except tomllib.TOMLDecodeError as exc:
            parse_error = str(exc)
        results['invalid_agent_toml'][name] = {'verifier': check.checks, 'tomllib_error': parse_error}
    mcp = '[mcp_servers.linear]\nurl = "https://mcp.linear.app/mcp"\nurl = [\n'
    check = verifier(repo)
    check._check_mcp_toml('codex-mcp.toml', mcp)
    try:
        tomllib.loads(mcp)
        parse_error = None
    except tomllib.TOMLDecodeError as exc:
        parse_error = str(exc)
    results['invalid_mcp_toml'] = {'verifier': check.checks, 'tomllib_error': parse_error}

    hook_path = repo / '.codex/hooks/guard.sh'
    hook_path.parent.mkdir(parents=True)
    hook_path.write_text('#!/bin/sh\nexit 0\n')
    hook_path.chmod(0o755)
    registration = {'hooks': {'PreToolUse': [{'matcher': '^(exec|exec_command|shell_command|run)$', 'hooks': [{'type': 'command', 'command': str(hook_path)}]}]}}
    (repo / '.codex/hooks.json').write_text(json.dumps(registration))
    check = verifier(repo)
    check.artifacts = [{'type': 'hook', 'path': '.codex/hooks/guard.sh', 'abs': str(hook_path)}]
    with patch.object(check, '_user_registry_paths', return_value=[]):
        check._check_hook_wired()
    results['wrong_codex_matcher'] = {'matcher': registration['hooks']['PreToolUse'][0]['matcher'], 'verifier': check.checks, 'matches_canonical_Bash': bool(v.re.search(registration['hooks']['PreToolUse'][0]['matcher'], 'Bash'))}

    network_source = "#!/bin/sh\nsh <<'SH'\ncurl https://example.invalid\nSH\n"
    check = verifier(repo)
    hook_path.write_text(network_source)
    is_clear = check._check_hook_network({'id': 'guard'}, str(hook_path), str(hook_path), str(hook_path))
    results['quoted_shell_heredoc'] = {'clear_to_execute': is_clear, 'verifier': check.checks}
    # Prove heredoc interpreter semantics with a local function instead of curl.
    inert_fixture = "#!/bin/sh\nsh <<'SH'\ncurl() { printf 'STUB_CALLED:%s\\n' \"$*\"; }\ncurl https://example.invalid\nSH\n"
    stubbed = subprocess.run(['/bin/sh'], input=inert_fixture, text=True, capture_output=True, timeout=5, cwd=scratch, env={'PATH': '/usr/bin:/bin'})
    results['quoted_shell_heredoc']['local_stub_execution'] = {'exit': stubbed.returncode, 'stdout': stubbed.stdout}
    results['quoted_python_heredoc_scan'] = v.scan_network_calls("python3 <<'PY'\nimport urllib.request\nurllib.request.urlopen('https://example.invalid')\nPY\n")

    # Simulate TimeoutExpired without launching a process. Patch BOTH group lookup
    # and killpg so no signal can ever reach the real caller or any other process.
    class TimedOutProcess:
        pid = 87654321
        returncode = None
        def communicate(self, **kwargs):
            raise subprocess.TimeoutExpired('mock-child', kwargs.get('timeout'))
        def kill(self):
            raise AssertionError('No fallback kill should be reached')
    def timeout_probe(method):
        check = verifier(repo, execute=True)
        with patch.object(v.subprocess, 'Popen', return_value=TimedOutProcess()) as popen, patch.object(v, '_resolve_codex', return_value='/mock/codex'), patch.object(v.os, 'getpgid', return_value=112233) as getpgid, patch.object(v.os, 'killpg') as killpg:
            if method == 'execpolicy':
                check._check_policy_execpolicy('agentify.rules', {'abs': str(repo/'agentify.rules')}, [{'args': {'match': ['npm install']}}])
                outcome = check.checks
            else:
                outcome = check._git_read(['rev-parse', '--show-toplevel'])
            return {'start_new_session': popen.call_args.kwargs.get('start_new_session', False), 'process_group_explicitly_set': 'process_group' in popen.call_args.kwargs, 'killpg_requested': killpg.call_args.args, 'pid_looked_up': getpgid.call_args.args, 'outcome': outcome}
    results['timeout_execpolicy_mocked'] = timeout_probe('execpolicy')
    results['timeout_git_read_mocked'] = timeout_probe('git')

    report_path = SOURCE.parent.parent / 'references/report-template.md'
    report = report_path.read_text()
    block = report.split("python3 - <<'PY'\nimport hashlib, io, json, os, re\n", 1)[1].split('\nPY\n```', 1)[0]
    tree = ast.parse('import hashlib, io, json, os, re\n' + block)
    # Load pure helper definitions only; skip its top-level filesystem edit loop.
    definitions = ast.Module(body=[n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom, ast.FunctionDef))], type_ignores=[])
    helpers = {}
    exec(compile(definitions, str(report_path), 'exec'), helpers)
    own = '/repo/.codex/hooks/block-npm.sh'
    user = '/repo/tools/block-npm.sh'
    before = json.dumps({'hooks': {'PreToolUse': [{'matcher': 'Bash', 'hooks': [{'type': 'command', 'command': user}]}]}}, indent=2) + '\n'
    before_hash = hashlib.sha256(before.encode()).hexdigest()
    raw = json.dumps({'hooks': {'PreToolUse': [{'matcher': 'Bash', 'hooks': [{'type': 'command', 'command': user}, {'type': 'command', 'command': own}]}]}})
    unmerge = helpers['unmerge_json']('.codex/hooks.json', 'hook-settings', 'modified', before_hash, [('hook_command', own)], raw)
    results['unmerge_same_basename'] = {'recorded_generated_command': own, 'pre_existing_user_command': user, 'pre_existing_sha256': before_hash, 'result': unmerge}

output = json.dumps(results, indent=2)
print(output)
