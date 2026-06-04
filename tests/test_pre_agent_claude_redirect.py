import json
import os
import subprocess
import sys
import tempfile
import unittest

HOOK = os.path.join(os.path.dirname(__file__), "..", "hooks", "pre_agent_claude_redirect.py")


def run_hook(payload: dict, home: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, HOOK],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env={**os.environ, "HOME": home},
    )


def decode_output(result: subprocess.CompletedProcess) -> dict | None:
    out = result.stdout.strip()
    if not out:
        return None
    return json.loads(out)


class PreAgentClaudeRedirectTests(unittest.TestCase):

    def setUp(self):
        self._tmp_home = tempfile.mkdtemp()
        os.makedirs(os.path.join(self._tmp_home, ".claude"), exist_ok=True)

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp_home, ignore_errors=True)

    def _enable_codex(self, session_id: str):
        flag = os.path.join(self._tmp_home, ".claude", f"codex_mode_on_{session_id}")
        open(flag, "w").close()

    def _allow_flag(self, session_id: str):
        flag = os.path.join(self._tmp_home, ".claude", f"allow_claude_agent_{session_id}")
        open(flag, "w").close()
        return flag

    def test_ccp_claude_opus_denied_even_with_allow_flag(self):
        sid = "test_ccp_deny"
        self._enable_codex(sid)
        flag = self._allow_flag(sid)
        result = run_hook(
            {
                "tool_name": "Agent",
                "session_id": sid,
                "tool_input": {"subagent_type": "claude-opus"},
            },
            self._tmp_home,
        )
        self.assertEqual(result.returncode, 0)
        out = decode_output(result)
        self.assertIsNotNone(out)
        reason = out["hookSpecificOutput"]["permissionDecisionReason"]
        self.assertIn("ccp-opus-direct", reason)
        self.assertTrue(os.path.exists(flag))

    def test_native_allow_flag_still_passes(self):
        sid = "test_native_allow"
        flag = self._allow_flag(sid)
        result = run_hook(
            {
                "tool_name": "Agent",
                "session_id": sid,
                "tool_input": {"subagent_type": "claude-opus"},
            },
            self._tmp_home,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")
        self.assertFalse(os.path.exists(flag))

    def test_other_claude_agents_keep_existing_redirect(self):
        sid = "test_other_redirect"
        result = run_hook(
            {
                "tool_name": "Agent",
                "session_id": sid,
                "tool_input": {"subagent_type": "claude-haiku"},
            },
            self._tmp_home,
        )
        self.assertEqual(result.returncode, 0)
        out = decode_output(result)
        self.assertIsNotNone(out)
        reason = out["hookSpecificOutput"]["permissionDecisionReason"]
        self.assertIn('subagent_type="gpt-5-4-mini"', reason)


if __name__ == "__main__":
    unittest.main()
