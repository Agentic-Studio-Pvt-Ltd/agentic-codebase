"""Isolated probes of shipped templates. No model calls or user configuration reads."""
import json
import pathlib
import re
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[4]
TEMPLATES = ROOT / 'skills/agentify/templates'

def render_hook(**changes):
    source = (TEMPLATES / 'codex-hook.sh.tmpl').read_text()
    source = '\n'.join(line for line in source.splitlines() if not line.lstrip().startswith('#>')) + '\n'
    values = dict(AGENTIFY_ID='audit-probe', GENERATED_DATE='2026-09-15',
                  EVIDENCE_LINE='Synthetic audit fixture, 2 cases', HOOK_TITLE='Audit probe',
                  HOOK_EVENT='PreToolUse', HOOK_MATCHER='^(exec|exec_command|shell_command|run|local_shell)$',
                  HOOK_FILE_NAME='probe.sh', BLOCK_MESSAGE='Probe violation', REMEDIATION_HINT='Use fixture',
                  CHECK_LABEL='probe', TOOL_NAME_GLOB='exec|exec_command|shell_command|run|local_shell',
                  PATH_GLOB='src/*.ts', CHECK_COMMAND='return 1')
    values.update(changes)
    for key, value in values.items():
        source = source.replace('{{' + key + '}}', value)
    assert not re.search(r'\{\{[A-Z_]+\}\}', source)
    return source

results = {}
with tempfile.TemporaryDirectory(prefix='agentify-codex-probe-') as tmp:
    wd = pathlib.Path(tmp)
    # A shell hook must remove the file-path filter, per the template filling rules.
    shell = render_hook()
    begin = shell.index('# A patch can touch several files, so this matches if ANY touched path matches.')
    end = shell.index('# ---------------------------------------------------------------------------\n# The check.', begin)
    shell = shell[:begin] + shell[end:]
    hook = wd / 'probe.sh'
    hook.write_text(shell)
    hook.chmod(0o755)
    calls = []
    for name in ['exec_command', 'Bash']:
        event = dict(tool_name=name, tool_input={'command': 'npm install fixture'},
                     cwd=tmp, hook_event_name='PreToolUse', session_id='synthetic')
        p = subprocess.run(['bash', str(hook)], input=json.dumps(event), text=True,
                           cwd=wd, capture_output=True, timeout=8)
        calls.append({'tool_name': name, 'exit': p.returncode,
                      'denied': '"permissionDecision": "deny"' in p.stdout,
                      'stderr': p.stderr})
    results['shell_canonical_name'] = calls
    results['documented_name_matches_emitted_regex'] = bool(re.search(
        r'^(exec|exec_command|shell_command|run|local_shell)$', 'Bash'))

    # Exercise exactly the extractor shipped in the template, with both input contracts.
    text = (TEMPLATES / 'codex-hook.sh.tmpl').read_text()
    start = text.index('import json, sys\n\nHEADERS')
    end = text.index("\n' 2>/dev/null || printf ''", start)
    extractor = text[start:end]
    patch = '*** Begin Patch\n*** Update File: src/example.ts\n@@\n-old\n+new\n*** End Patch'
    inputs = [('raw_rollout', patch), ('documented_hook', {'command': patch})]
    results['patch_payload_extraction'] = []
    for kind, payload in inputs:
        p = subprocess.run(['python3', '-c', extractor],
                           input=json.dumps({'tool_input': payload}), text=True,
                           capture_output=True, timeout=5)
        results['patch_payload_extraction'].append({'input_kind': kind, 'exit': p.returncode,
                                                    'has_path': 'PATH\tsrc/example.ts' in p.stdout,
                                                    'output': p.stdout})

symlink = ROOT / 'skills/agentify/agentify'
results['distribution_symlink'] = {'is_symlink': symlink.is_symlink(),
                                  'target': str(symlink.readlink()),
                                  'target_exists': symlink.exists()}
description = (ROOT / 'skills/agentify/SKILL.md').read_text().splitlines()[2].split(': ', 1)[1]
results['orchestrator_description_characters'] = len(description)
print(json.dumps(results, indent=2))
