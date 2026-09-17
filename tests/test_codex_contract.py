"""Developer-only integration tests of the shipped Codex templates.

Uses temporary Git repositories and synthetic events; no Codex model calls,
network access, user configuration changes, or real transcript reads.
Run: python3 -m unittest discover -s tests -v
"""
import json
import pathlib
import re
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "skills" / "agentic-codebase" / "templates"


def render_hook(event="PreToolUse", check="return 1", file_scoped=False):
    source = (TEMPLATES / "codex-hook.sh.tmpl").read_text()
    source = "\n".join(line for line in source.splitlines()
                       if not line.lstrip().startswith("#>")) + "\n"
    values = dict(
        AGENTIC_CODEBASE_ID="contract-test", GENERATED_DATE="2026-09-16",
        EVIDENCE_LINE="Synthetic fixture, 2 cases", HOOK_TITLE="Contract test",
        HOOK_EVENT=event, HOOK_MATCHER="^(Bash|exec_command|apply_patch)$",
        HOOK_FILE_NAME="probe.sh", BLOCK_MESSAGE="Synthetic violation",
        REMEDIATION_HINT="Use the fixture", CHECK_LABEL="probe",
        TOOL_NAME_GLOB="Bash|exec_command|apply_patch", PATH_GLOB="pkg/*.ts",
        CHECK_COMMAND=check,
    )
    for key, value in values.items():
        source = source.replace("{{" + key + "}}", value)
    if not file_scoped:
        begin = source.index("# A patch can touch several files")
        end = source.index("# ---------------------------------------------------------------------------\n# The check.", begin)
        source = source[:begin] + source[end:]
    if re.search(r"\{\{[A-Z_]+\}\}", source):
        raise AssertionError("unfilled hook placeholder")
    return source


class CodexHookContract(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="agentic-codebase-contract-")
        self.addCleanup(self.tmp.cleanup)
        self.repo = pathlib.Path(self.tmp.name).resolve()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        (self.repo / "pkg").mkdir()
        (self.repo / "pkg" / "a.ts").write_text("synthetic violation\n")
        (self.repo / "pkg" / "b.ts").write_text("synthetic violation\n")

    def run_hook(self, event="PreToolUse", tool="Bash", command="git status",
                 check="return 1", file_scoped=False, cwd=None, raw=False,
                 source=None, stop_hook_active=False):
        hook = self.repo / "probe.sh"
        hook.write_text(source if source is not None else render_hook(event, check, file_scoped))
        payload = dict(session_id="synthetic", hook_event_name=event,
                       cwd=str(cwd or self.repo), stop_hook_active=stop_hook_active)
        if tool:
            payload.update(tool_name=tool, tool_input=command if raw else {"command": command})
        result = subprocess.run(["bash", str(hook)], input=json.dumps(payload),
                                capture_output=True, text=True, cwd=cwd or self.repo,
                                timeout=8)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout) if result.stdout.strip() else None, result.stderr

    @staticmethod
    def patch(*paths):
        return "*** Begin Patch\n" + "".join(
            "*** Update File: %s\n@@\n-a\n+b\n" % path for path in paths
        ) + "*** End Patch\n"

    def test_shell_wiring_and_canonical_name(self):
        text = (TEMPLATES / "codex-hooks.json.tmpl").read_text()
        fragment = text.split("<<<AGENTIC_CODEBASE-FRAGMENT-BEGIN>>>")[1].split(
            "<<<AGENTIC_CODEBASE-FRAGMENT-END>>>")[0].strip()
        fragment = fragment[len("```json"):].rsplit("```", 1)[0].strip()
        for key, value in dict(HOOK_EVENT="PreToolUse", HOOK_MATCHER="^(Bash|exec_command)$",
                               HOOK_FILE_NAME="probe.sh", HOOK_STATUS_MESSAGE="Checking fixture").items():
            fragment = fragment.replace("{{" + key + "}}", value)
        group = json.loads(fragment)["hooks"]["PreToolUse"][0]
        self.assertEqual(group["hooks"][0]["timeout"], 5)
        for tool in ("Bash", "exec_command"):
            self.assertIsNotNone(re.fullmatch(group["matcher"], tool))
            data, err = self.run_hook(tool=tool)
            self.assertEqual(data["hookSpecificOutput"]["permissionDecision"], "deny")
            self.assertFalse(err)
        self.assertEqual(self.run_hook(tool="update_plan"), (None, ""))

    def test_permission_request_decision(self):
        data, err = self.run_hook(event="PermissionRequest")
        self.assertEqual(data["hookSpecificOutput"]["decision"]["behavior"], "deny")
        self.assertNotIn("permissionDecision", data["hookSpecificOutput"])
        self.assertFalse(err)

    def test_post_tool_feedback(self):
        data, err = self.run_hook(event="PostToolUse")
        self.assertEqual(data["decision"], "block")
        self.assertTrue(data["reason"])
        self.assertFalse(err)

    def test_prompt_and_stop_events_without_tool_name(self):
        for event in ("UserPromptSubmit", "Stop", "SubagentStop"):
            with self.subTest(event=event):
                data, err = self.run_hook(event=event, tool=None)
                self.assertEqual(data["decision"], "block")
                self.assertTrue(data["reason"])
                self.assertFalse(err)

    def test_stop_continuation_does_not_loop(self):
        for event in ("Stop", "SubagentStop"):
            self.assertEqual(self.run_hook(event=event, tool=None, stop_hook_active=True), (None, ""))

    def test_patch_object_and_freeform(self):
        for raw in (False, True):
            with self.subTest(raw=raw):
                data, err = self.run_hook(tool="apply_patch", command=self.patch("pkg/a.ts"),
                                          file_scoped=True, raw=raw)
                self.assertEqual(data["hookSpecificOutput"]["permissionDecision"], "deny")
                self.assertFalse(err)

    def test_subfolder_checks_the_actual_file(self):
        data, err = self.run_hook(tool="apply_patch", command=self.patch("a.ts"),
                                  cwd=self.repo / "pkg", file_scoped=True,
                                  check='if [ -f "$FILE_PATH" ]; then return 1; else return 0; fi')
        self.assertIsNotNone(data, "the actual touched file must be checked")
        self.assertFalse(err)

    def test_unrelated_first_path_does_not_hide_guarded_path(self):
        data, err = self.run_hook(tool="apply_patch", command=self.patch("README.md", "pkg/a.ts"),
                                  file_scoped=True,
                                  check='if [ -f "$FILE_PATH" ]; then return 1; else return 0; fi')
        self.assertIsNotNone(data)
        self.assertFalse(err)

    def test_all_matching_files_are_checked(self):
        data, err = self.run_hook(tool="apply_patch", command=self.patch("pkg/a.ts", "pkg/b.ts"),
                                  file_scoped=True,
                                  check='case "$FILE_PATH" in pkg/b.ts) return 1;; *) return 0;; esac')
        self.assertIsNotNone(data, "a later matching file must not escape the check")
        self.assertFalse(err)

    def test_outside_path_does_not_alias_guarded_repo_file(self):
        data, err = self.run_hook(tool="apply_patch", command=self.patch("../pkg/a.ts"),
                                  file_scoped=True)
        self.assertIsNone(data)
        self.assertFalse(err)

    def test_missing_check_is_not_a_clean_pass(self):
        data, err = self.run_hook(check="return 127")
        self.assertIsNone(data)
        self.assertIn("check did not complete", err)

    def test_broken_canonical_filter_is_detectable(self):
        source = render_hook().replace("Bash|exec_command|apply_patch)", "exec_command|apply_patch)")
        data, _ = self.run_hook(source=source)
        self.assertIsNone(data, "negative control must change the observed canonical decision")


if __name__ == "__main__":
    unittest.main()
