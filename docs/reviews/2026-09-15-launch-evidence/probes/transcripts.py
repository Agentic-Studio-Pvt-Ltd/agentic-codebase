import contextlib
import io
import sys
from unittest.mock import patch
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import tempfile

MINER = Path(__file__).resolve().parents[4] / 'skills/agentify/scripts/mine_transcripts.py'
now = dt.datetime.now(dt.timezone.utc)
old = now - dt.timedelta(days=80)

def iso(t): return t.isoformat().replace('+00:00', 'Z')
def write_records(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(json.dumps(r)+'\n' for r in records))
def meta(repo, timestamp=now):
    return {'timestamp':iso(timestamp),'type':'session_meta','payload':{'id':'synthetic-thread','cwd':str(repo),'source':'cli'}}
def turn(text, timestamp):
    return {'timestamp':iso(timestamp),'type':'response_item','payload':{'type':'message','role':'user','content':[{'type':'input_text','text':text}]}}
sys.path.insert(0, str(MINER.parent))
import mine_transcripts as miner

def run(repo, fixture_root, target='codex', flags=()):
    """Exercise the CLI entry point with isolated config resolvers, no env changes."""
    out, err = io.StringIO(), io.StringIO()
    def config_root(env_name, fallback, user_home):
        return str(fixture_root / ('codex' if env_name == 'CODEX_HOME' else 'claude'))
    with patch.object(miner, '_config_home', side_effect=config_root), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = miner.main(['--repo', str(repo), '--target', target, *flags])
    assert code == 0, (out.getvalue(), err.getvalue())
    return json.loads(out.getvalue()), err.getvalue()

results={}
with tempfile.TemporaryDirectory(prefix='agentify-synthetic-') as raw:
    home=Path(raw)
    repo=home/'repo'; repo.mkdir()
    live=home/'codex'/'sessions'
    prompt='Please run npm test and fix the failing unit tests.'
    rollout=live/now.strftime('%Y/%m/%d')/'repeat.jsonl'
    write_records(rollout,[meta(repo),turn(prompt,now-dt.timedelta(hours=3)),turn(prompt,now-dt.timedelta(hours=2)),turn(prompt,now-dt.timedelta(hours=1))])
    doc,_=run(repo,home)
    results['repeated_genuine_turns']={'expected_analyzed':3,'actual_sessions':doc['sessions'],'commands_requested':doc['commands_requested']}
    # All timestamps different; both user requests share a sufficiently long prefix.
    long_prefix='Review the implementation for data handling, permission boundaries and correct use of repository conventions. '*5
    write_records(rollout,[meta(repo),turn(long_prefix+'Then inspect the authentication module.',now-dt.timedelta(hours=2)),turn(long_prefix+'Then inspect the payment module.',now-dt.timedelta(hours=1))])
    doc,_=run(repo,home)
    results['prefix_collision']={'expected_analyzed':2,'actual_analyzed':doc['sessions']['user_turns_analyzed']}
    rollout.unlink()
    resumed=live/old.strftime('%Y/%m/%d')/'resumed.jsonl'
    write_records(resumed,[meta(repo,old),turn(prompt,now-dt.timedelta(hours=1))])
    doc,_=run(repo,home,flags=['--days','7'])
    results['resumed_old_thread']={'expected_files':1,'actual_sessions':doc['sessions'],'warnings':doc['warnings']}
    # timestamped stale last-prompt survives because file is recently appended/rewritten
    encoded=str(repo).replace('/','-').replace('.','-').replace('_','-')
    for n in [1,2]:
        write_records(home/'claude'/'projects'/encoded/f'stale-{n}.jsonl',[
            {'type':'last-prompt','timestamp':iso(old),'sessionId':f'stale-{n}','lastPrompt':prompt},
            {'type':'system','timestamp':iso(now),'message':'Synthetic recent metadata update'}])
    doc,_=run(repo,home,target='claude-code',flags=['--days','7'])
    results['claude_last_prompt_outside_consent']={'expected_analyzed':0,'actual_sessions':doc['sessions'],'commands_requested':doc['commands_requested'],'warnings':doc['warnings']}
    git=repo/'.git'; git.mkdir()
    git.joinpath('config').write_text('[remote "origin"]\n    url = https://synthetic-user:SYNTHETIC_PASSWORD_12345@example.com/acme/repo.git\n')
    doc,stderr=run(repo,home,flags=['--debug'])
    results['debug_remote_disclosure']={'synthetic_password_in_stderr':'SYNTHETIC_PASSWORD_12345' in stderr,'stderr':stderr}
print(json.dumps(results,indent=2))
