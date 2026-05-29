"""
Tests for hooks/codex_tier_writer.py.

Execution model: subprocess.run — feeds a JSON payload via stdin, checks
the tier file written to /tmp and the exit code.  Each test uses a unique
session_id so tests never share state.  A real ~/.claude/codex_mode_on_*
flag file is isolated via a temporary HOME directory.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HOOK = os.path.join(os.path.dirname(__file__), "..", "hooks", "codex_tier_writer.py")


def run_hook(payload: dict, home: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, HOOK],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env={**os.environ, "HOME": home},
    )


class TierWriterTests(unittest.TestCase):

    def setUp(self):
        self._tmp_home = tempfile.mkdtemp()
        os.makedirs(os.path.join(self._tmp_home, ".claude"), exist_ok=True)

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp_home, ignore_errors=True)

    def _session_id(self):
        # unique per test method so tier files never collide
        import uuid
        return f"test_{uuid.uuid4().hex}"

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

    # ── session_id absent → exit 0, no tier file ──────────────────────────────

    def test_no_session_id_exits_cleanly(self):
        sid = self._session_id()
        self._enable_codex(sid)
        result = run_hook({"prompt": "implement feature X"}, self._tmp_home)
        self.assertEqual(result.returncode, 0)
        # no session_id in payload → tier file must NOT be written
        self.assertFalse(os.path.exists(self._tier_path("")))

    # ── codex-off (flag absent) → tier file deleted ───────────────────────────

    def test_codex_off_removes_existing_tier_file(self):
        sid = self._session_id()
        # pre-write a stale tier file
        tier_path = self._tier_path(sid)
        with open(tier_path, "w") as f:
            json.dump({"tier": "heavy"}, f)
        try:
            result = run_hook({"session_id": sid, "prompt": "review code"}, self._tmp_home)
            self.assertEqual(result.returncode, 0)
            self.assertFalse(os.path.exists(tier_path))
        finally:
            self._cleanup_tier(sid)

    def test_codex_off_no_tier_file_written(self):
        sid = self._session_id()
        tier_path = self._tier_path(sid)
        try:
            result = run_hook({"session_id": sid, "prompt": "implement feature X"}, self._tmp_home)
            self.assertEqual(result.returncode, 0)
            self.assertFalse(os.path.exists(tier_path))
        finally:
            self._cleanup_tier(sid)

    # ── codex-on + HEAVY keyword → tier=heavy ─────────────────────────────────

    def test_heavy_keyword_english_review(self):
        sid = self._session_id()
        self._enable_codex(sid)
        tier_path = self._tier_path(sid)
        try:
            result = run_hook({"session_id": sid, "prompt": "review this auth flow"}, self._tmp_home)
            self.assertEqual(result.returncode, 0)
            with open(tier_path) as f:
                data = json.load(f)
            self.assertEqual(data["tier"], "heavy")
        finally:
            self._cleanup_tier(sid)

    def test_heavy_keyword_security_audit(self):
        sid = self._session_id()
        self._enable_codex(sid)
        tier_path = self._tier_path(sid)
        try:
            result = run_hook({"session_id": sid, "prompt": "security audit of payment module"}, self._tmp_home)
            self.assertEqual(result.returncode, 0)
            with open(tier_path) as f:
                data = json.load(f)
            self.assertEqual(data["tier"], "heavy")
        finally:
            self._cleanup_tier(sid)

    def test_heavy_keyword_korean_review(self):
        sid = self._session_id()
        self._enable_codex(sid)
        tier_path = self._tier_path(sid)
        try:
            result = run_hook({"session_id": sid, "prompt": "이 코드 리뷰해줘"}, self._tmp_home)
            self.assertEqual(result.returncode, 0)
            with open(tier_path) as f:
                data = json.load(f)
            self.assertEqual(data["tier"], "heavy")
        finally:
            self._cleanup_tier(sid)

    # ── codex-on + MEDIUM keyword → tier=medium ───────────────────────────────

    def test_medium_keyword_implement(self):
        sid = self._session_id()
        self._enable_codex(sid)
        tier_path = self._tier_path(sid)
        try:
            result = run_hook({"session_id": sid, "prompt": "implement the login flow"}, self._tmp_home)
            self.assertEqual(result.returncode, 0)
            with open(tier_path) as f:
                data = json.load(f)
            self.assertEqual(data["tier"], "medium")
        finally:
            self._cleanup_tier(sid)

    def test_medium_keyword_fix(self):
        sid = self._session_id()
        self._enable_codex(sid)
        tier_path = self._tier_path(sid)
        try:
            result = run_hook({"session_id": sid, "prompt": "fix the null pointer crash"}, self._tmp_home)
            self.assertEqual(result.returncode, 0)
            with open(tier_path) as f:
                data = json.load(f)
            self.assertEqual(data["tier"], "medium")
        finally:
            self._cleanup_tier(sid)

    def test_medium_keyword_korean_modify(self):
        sid = self._session_id()
        self._enable_codex(sid)
        tier_path = self._tier_path(sid)
        try:
            result = run_hook({"session_id": sid, "prompt": "이 함수 수정해줘"}, self._tmp_home)
            self.assertEqual(result.returncode, 0)
            with open(tier_path) as f:
                data = json.load(f)
            self.assertEqual(data["tier"], "medium")
        finally:
            self._cleanup_tier(sid)

    # ── codex-on, no keyword match → tier file deleted ────────────────────────

    def test_no_keyword_match_removes_tier_file(self):
        sid = self._session_id()
        self._enable_codex(sid)
        tier_path = self._tier_path(sid)
        # pre-write so we can confirm deletion
        with open(tier_path, "w") as f:
            json.dump({"tier": "medium"}, f)
        try:
            result = run_hook({"session_id": sid, "prompt": "what is the capital of France"}, self._tmp_home)
            self.assertEqual(result.returncode, 0)
            self.assertFalse(os.path.exists(tier_path))
        finally:
            self._cleanup_tier(sid)

    def test_no_keyword_match_no_file_created(self):
        sid = self._session_id()
        self._enable_codex(sid)
        tier_path = self._tier_path(sid)
        try:
            result = run_hook({"session_id": sid, "prompt": "what is 2 + 2"}, self._tmp_home)
            self.assertEqual(result.returncode, 0)
            self.assertFalse(os.path.exists(tier_path))
        finally:
            self._cleanup_tier(sid)

    # ── HEAVY takes precedence over MEDIUM when both match ────────────────────

    def test_heavy_wins_over_medium(self):
        """A prompt matching both HEAVY and MEDIUM should resolve to heavy."""
        sid = self._session_id()
        self._enable_codex(sid)
        tier_path = self._tier_path(sid)
        try:
            result = run_hook(
                {"session_id": sid, "prompt": "implement and review the auth module"},
                self._tmp_home,
            )
            self.assertEqual(result.returncode, 0)
            with open(tier_path) as f:
                data = json.load(f)
            self.assertEqual(data["tier"], "heavy")
        finally:
            self._cleanup_tier(sid)


if __name__ == "__main__":
    unittest.main()
