"""Synthetic privacy and verification regressions; never reads real histories."""
import collections
import datetime
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/agentify/scripts'
def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

miner, verifier = load('mine_transcripts'), load('verify_artifacts')

class Signals:
    def __init__(self): self.turns = []; self.slashes = []
    def note_slash(self, value): self.slashes.append(value)
    def add_turn(self, *value): self.turns.append(value)

class Recorder:
    def __init__(self): self.rows = []
    def add(self, *row): self.rows.append(row)

class RepairRegressions(unittest.TestCase):
    def read(self, rows, cutoff=None, claude=False, inherited=None, own=None, fork_time=None):
        with tempfile.TemporaryDirectory(prefix='agentify-history-test-') as tmp:
            path = Path(tmp) / 'fixture.jsonl'
            path.write_text('\n'.join(json.dumps(row) for row in rows))
            signals, stats = Signals(), collections.defaultdict(int)
            if claude:
                miner.read_claude_session(str(path), cutoff, signals, stats)
            else:
                miner.read_codex_session(str(path), cutoff, signals, stats, inherited, own, fork_time)
            return signals, stats

    @staticmethod
    def turn(stamp, secondary=False, text='run npm test and fix the failing suite'):
        return dict(timestamp=stamp, type='event_msg' if secondary else 'response_item',
                    payload=dict(type='user_message', message=text) if secondary else
                    dict(type='message', role='user', content=[dict(type='input_text', text=text)]))

    def test_undated_and_invalid_consent_on_both_readers(self):
        for stamp in ('', 'not-a-timestamp', 123):
            for claude in (False, True):
                row = dict(type='user', timestamp=stamp, message=dict(role='user', content='run npm test')) if claude else self.turn(stamp)
                signals, stats = self.read([row], '2026-09-09T00:00:00', claude)
                self.assertEqual(signals.turns, [])
                self.assertEqual(signals.slashes, [])
                self.assertEqual(stats['out_of_window'], 1)
        self.assertEqual(len(self.read([self.turn('')])[0].turns), 1)

    def test_timestamp_offsets_use_actual_utc(self):
        self.assertFalse(miner._within_window('2026-09-09T01:00:00+05:30', '2026-09-09T00:00:00'))
        self.assertTrue(miner._within_window('2026-09-08T23:00:00-04:00', '2026-09-09T00:00:00'))

    def test_partial_stream_repeat_is_retained(self):
        rows = [self.turn('2026-09-14T10:00:00Z'), self.turn('2026-09-15T10:00:00Z', True)]
        self.assertEqual(len(self.read(rows)[0].turns), 2)
        rows[1]['timestamp'] = '2026-09-14T10:00:01Z'
        self.assertEqual(len(self.read(rows)[0].turns), 1)

    def test_parent_continuation_cannot_erase_child_turn(self):
        own = []
        self.read([self.turn('2026-09-14T10:00:00Z', text='implement the fixture'), self.turn('2026-09-16T10:00:00Z')], own=own)
        child = [self.turn('2026-09-15T10:00:00Z', text='implement the fixture'), self.turn('2026-09-15T10:05:00Z')]
        signals, stats = self.read(child, inherited=own, fork_time='2026-09-15T10:00:00Z')
        self.assertEqual(len(signals.turns), 1)
        self.assertEqual(stats['fork_duplicates'], 1)

    @unittest.skipUnless(hasattr(time, 'tzset'), 'requires POSIX timezone switching')
    def test_mtime_cutoff_west_of_utc(self):
        fixed = datetime.datetime(2026, 9, 16, 12)
        with patch.dict(os.environ, {'TZ': 'EST5EDT'}):
            time.tzset()
            try:
                epoch = fixed.replace(tzinfo=datetime.timezone.utc).timestamp()
                with patch.object(miner, '_utc_now', return_value=fixed):
                    rows = [('fixture', epoch - 23 * 3600, 1)]
                    self.assertEqual(miner.select_sessions(rows, 1, None, None, []), rows)
            finally:
                pass
        time.tzset()

    def test_array_credentials_are_redacted_and_idempotent(self):
        for text in ('{"api_keys": ["hunter2trombone", "swordfishvalue"]}',
                     '{"password": ["hunter2trombone", "x]y\\\"swordfishvalue"]}',
                     'api_keys: [\n "hunter2trombone",\n "swordfishvalue"\n]'):
            clean, _ = miner.scrub_lib.scrub(text)
            self.assertNotIn('hunter2trombone', clean)
            self.assertNotIn('swordfishvalue', clean)
            self.assertEqual(miner.scrub_lib.scrub(clean)[0], clean)

    def test_shell_substitution_heredoc_cannot_bypass_network_gate(self):
        command = 'sh -c "$(cat <<\'EOF\'\ncurl https://example.invalid/probe\nEOF\n)"'
        record = Recorder()
        allowed = verifier.Verifier._check_hook_network(record, {'id': 'probe'}, 'probe', '', command)
        self.assertFalse(allowed)
        self.assertTrue(any(row[2] == verifier.FAIL for row in record.rows))

    def test_forbidden_sandbox_without_toml_parser(self):
        record = Recorder()
        artifact = dict(path='probe.toml', text='name="probe"\ndescription="Fixture"\ndeveloper_instructions="Review"\nsandbox_mode="danger-full-access"\n')
        with patch.object(verifier, '_TOMLLIB', None):
            verifier.Verifier._check_subagent_toml(record, artifact, 'probe')
        self.assertTrue(any(row[0] == 'subagent_frontmatter' and row[2] == verifier.UNVERIFIED for row in record.rows))
        self.assertTrue(any(row[0] == 'subagent_tools' and row[2] == verifier.FAIL for row in record.rows))

    def test_agent_identity_does_not_require_matching_filename(self):
        record = Recorder()
        artifact = dict(path='review-agent.toml', text='name="review_agent"\ndescription="Fixture"\ndeveloper_instructions="Review"\n')
        verifier.Verifier._check_subagent_toml(record, artifact, 'probe')
        self.assertFalse(any(row[2] == verifier.FAIL for row in record.rows))

    def test_fixture_protocol_rejects_wrong_event_and_failed_check(self):
        base = dict(code=0, stderr='', error='', timeout=False)
        wrong = json.dumps({'hookSpecificOutput': {'hookEventName': 'PermissionRequest', 'permissionDecision': 'deny'}})
        self.assertEqual(verifier.fixture_verdict(dict(base, stdout=wrong), 'PermissionRequest'), 'invalid output')
        self.assertEqual(verifier.fixture_verdict(dict(base, stdout='', stderr='check did not complete (exit 127), allowing.')), 'inconclusive')
        problems, _ = verifier.run_fixture_set(lambda _: dict(base, stdout='', stderr='check did not complete (exit 127), allowing.'), 'PreToolUse', ['shell'], 'Bash', 'exec_command', '')
        self.assertTrue(problems)

if __name__ == '__main__': unittest.main()
