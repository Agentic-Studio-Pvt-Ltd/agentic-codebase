import json, os, pathlib, subprocess, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[4] / 'skills/agentify/scripts'))
import mine_git as m
with tempfile.TemporaryDirectory(prefix='agentify-git-probe-') as tmp:
 root=pathlib.Path(tmp)
 def git(*args):
  return subprocess.run(['git','-C',str(root),*args], check=True, capture_output=True, text=True, env=dict(os.environ, GIT_AUTHOR_DATE='2020-01-01T00:00:00+00:00', GIT_COMMITTER_DATE='2020-01-01T00:00:00+00:00')).stdout
 git('init','-q')
 git('config','user.name','Synthetic Tester')
 git('config','user.email','tester@example.invalid')
 (root/'src').mkdir(); (root/'src'/'café.py').write_text('print(1)\n')
 git('add','src/café.py')
 git('-c','core.hooksPath=/dev/null','-c','commit.gpgsign=false','commit','-qm','feat: synthetic old fixture','--date=2020-01-01T00:00:00+00:00')
 p=m.collect(str(root),days=1,max_commits=10,no_gh=True)
 raw=git('log','--numstat','--format=')
 print(json.dumps({'explicit_days_1':{'window':p['window'],'available':p['available'],'warnings':p['warnings']},'non_ascii_filename':{'git_numstat':raw,'hotspots':p['hotspots'],'actual_file_exists':(root/'src'/'café.py').exists()}},ensure_ascii=False,indent=2))
