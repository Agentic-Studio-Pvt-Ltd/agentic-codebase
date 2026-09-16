import contextlib, io, json, os, pathlib, sys, tempfile
from unittest.mock import patch
SCRIPTS = pathlib.Path(__file__).resolve().parents[4] / 'skills/agentify/scripts'
sys.path.insert(0, str(SCRIPTS))
import discover as d
from lib import scrub
results = {}
results['quoted_credential_keys'] = [dict(input=s, output=scrub.scrub(s)[0], hits=scrub.scrub(s)[1]) for s in [
    '{"password": "SYNTHETIC-pw-123", "api_key": "SYNTHETIC-key-456"}',
    "{'password': 'SYNTHETIC-pw-123'}",
    'password=SYNTHETIC-pw-123',
]]
with tempfile.TemporaryDirectory(prefix='agentify-safe-probe-') as tmp:
    base = pathlib.Path(tmp)
    repo = base / 'repo'
    repo.mkdir()
    outside = base / 'outside'
    outside.mkdir()
    outside_file = outside / 'credentials.json'
    outside_file.write_text('{"scripts": {"dev": "echo SYNTHETIC-outside-content"}}')
    (repo / 'package.json').symlink_to(outside_file)
    reader = d.Reader([])
    results['reader_outside_secret_symlink'] = {'text':reader.text(str(repo/'package.json')), 'bytes_read':reader.bytes_read, 'refused':reader.refused, 'resolved_is_secret':scrub.is_secret_path(str(outside_file))}
    (repo / 'store' / 'workflow').mkdir(parents=True)
    (repo / 'store' / 'workflow' / 'SKILL.md').write_text('---\nname: workflow\ndescription: synthetic\n---\n# Workflow\n')
    (repo / 'store' / 'reviewer.toml').write_text('name = "reviewer"\ndescription = "synthetic"\ndeveloper_instructions = "Review."\n')
    (repo / '.agents' / 'skills').mkdir(parents=True)
    (repo / '.agents' / 'skills' / 'workflow').symlink_to(repo/'store'/'workflow', target_is_directory=True)
    (repo / '.codex' / 'agents').mkdir(parents=True)
    (repo / '.codex' / 'agents' / 'reviewer.toml').symlink_to(repo/'store'/'reviewer.toml')
    fake_user = base / 'fixture-user'
    fake_user.mkdir()
    original_expanduser = os.path.expanduser
    def fixture_expanduser(value):
        if value == '~': return str(fake_user)
        if value.startswith('~/'): return str(fake_user / value[2:])
        return original_expanduser(value)
    out = io.StringIO()
    with patch.object(os.path, 'expanduser', side_effect=fixture_expanduser), patch.object(d, 'codex_home_dir', return_value=str(fake_user/'.codex')), patch.object(d, 'claude_home_dir', return_value=str(fake_user/'.claude')), contextlib.redirect_stdout(out):
        exit_code = d.main(['--repo', str(repo), '--json', '--cap-chars', '100000'])
    payload = json.loads(out.getvalue())
    results['discovery_symlink_end_to_end'] = {'exit':exit_code, 'raw_scripts':payload['raw_scripts'], 'skills':payload['existing_agentic_config']['skills'], 'agents':payload['existing_agentic_config']['agents'], 'symlinked':payload['existing_agentic_config']['symlinked'], 'warnings':payload['warnings']}
print(json.dumps(results, indent=2))
