import json
import os
import subprocess
import sys
import tempfile
import unittest

HOOK = os.path.join(os.path.dirname(__file__), "..", "hooks", "auto_model_router.py")


def run_hook(payload: dict, home: str, extra_env: dict | None = None) -> subprocess.CompletedProcess:
    env = {**os.environ, "HOME": home}
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, HOOK],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
    )


def decode_output(result: subprocess.CompletedProcess) -> dict | None:
    out = result.stdout.strip()
    if not out:
        return None
    return json.loads(out)


class AutoModelRouterTests(unittest.TestCase):

    def setUp(self):
        self._tmp_home = tempfile.mkdtemp()
        os.makedirs(os.path.join(self._tmp_home, ".claude"), exist_ok=True)

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp_home, ignore_errors=True)

    def _enable_codex(self, session_id: str):
        flag = os.path.join(self._tmp_home, ".claude", f"codex_mode_on_{session_id}")
        open(flag, "w").close()

    def _tier_path(self, session_id: str) -> str:
        return f"/tmp/claude_tier_{session_id}.json"

    def _cleanup_tier(self, session_id: str):
        try:
            os.remove(self._tier_path(session_id))
        except FileNotFoundError:
            pass

    def test_opus_review_request_gets_direct_hint(self):
        sid = "test_opus_direct"
        self._enable_codex(sid)
        try:
            result = run_hook({"session_id": sid, "prompt": "오푸스로 이 diff 리뷰해줘"}, self._tmp_home)
            self.assertEqual(result.returncode, 0)
            out = decode_output(result)
            self.assertIsNotNone(out)
            ctx = out["hookSpecificOutput"]["additionalContext"]
            self.assertIn("ccp-opus-direct <prompt-file>", ctx)
            self.assertIn("advisor()", ctx)
            with open(self._tier_path(sid)) as f:
                tier_data = json.load(f)
            self.assertEqual(tier_data["tier"], "opus_direct")
        finally:
            self._cleanup_tier(sid)

    def test_advisor_request_stays_advisor(self):
        sid = "test_advisor"
        self._enable_codex(sid)
        try:
            result = run_hook({"session_id": sid, "prompt": "advisor로 이 설계 검토해줘"}, self._tmp_home)
            self.assertEqual(result.returncode, 0)
            out = decode_output(result)
            self.assertIsNotNone(out)
            ctx = out["hookSpecificOutput"]["additionalContext"]
            self.assertIn("advisor()", ctx)
            self.assertNotIn("ccp-opus-direct", ctx)
            with open(self._tier_path(sid)) as f:
                tier_data = json.load(f)
            self.assertEqual(tier_data["tier"], "advisor")
        finally:
            self._cleanup_tier(sid)

    def test_opus_rule_discussion_is_not_direct_hint(self):
        sid = "test_not_opus_direct"
        self._enable_codex(sid)
        try:
            result = run_hook({"session_id": sid, "prompt": "오푸스 금지 규칙 리뷰"}, self._tmp_home)
            self.assertEqual(result.returncode, 0)
            out = decode_output(result)
            self.assertIsNotNone(out)
            ctx = out["hookSpecificOutput"]["additionalContext"]
            self.assertIn('mcp__codex__codex(model="gpt-5.5"', ctx)
            self.assertNotIn("ccp-opus-direct", ctx)
            with open(self._tier_path(sid)) as f:
                tier_data = json.load(f)
            self.assertEqual(tier_data["tier"], "heavy")
        finally:
            self._cleanup_tier(sid)

    def test_recursion_guard_suppresses_output(self):
        sid = "test_recursion_guard"
        self._enable_codex(sid)
        try:
            result = run_hook(
                {"session_id": sid, "prompt": "오푸스로 이 diff 리뷰해줘"},
                self._tmp_home,
                extra_env={"CLAUDE_OPUS_DIRECT_ACTIVE": "1"},
            )
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout.strip(), "")
        finally:
            self._cleanup_tier(sid)


if __name__ == "__main__":
    unittest.main()
