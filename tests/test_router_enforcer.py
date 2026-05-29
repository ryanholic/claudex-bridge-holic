"""
Tests for hooks/pre_tool_router_enforcer.py.

Execution model: subprocess.run — feeds a JSON payload via stdin, checks
stdout (block decision) and exit code.  Each test isolates ~/.claude by
pointing HOME at a fresh tempdir so no real session state is touched.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HOOK = os.path.join(os.path.dirname(__file__), "..", "hooks", "pre_tool_router_enforcer.py")


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
    """Return parsed JSON from stdout, or None if stdout is empty."""
    out = result.stdout.strip()
    if not out:
        return None
    return json.loads(out)


class RouterEnforcerTests(unittest.TestCase):

    def setUp(self):
        self._tmp_home = tempfile.mkdtemp()
        os.makedirs(os.path.join(self._tmp_home, ".claude"), exist_ok=True)

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp_home, ignore_errors=True)

    def _session_id(self):
        import uuid
        return f"test_{uuid.uuid4().hex}"

    def _tier_path(self, session_id: str) -> str:
        return f"/tmp/claude_tier_{session_id}.json"

    def _write_tier(self, session_id: str, tier: str):
        with open(self._tier_path(session_id), "w") as f:
            json.dump({"tier": tier}, f)

    def _cleanup_tier(self, session_id: str):
        try:
            os.remove(self._tier_path(session_id))
        except FileNotFoundError:
            pass

    def _enable_native(self, session_id: str):
        flag = os.path.join(self._tmp_home, ".claude", f"codex_native_on_{session_id}")
        open(flag, "w").close()

    def _enable_killswitch(self):
        ks = os.path.join(self._tmp_home, ".claude", "router_enforcer.off")
        open(ks, "w").close()

    # ── killswitch → always pass through ─────────────────────────────────────

    def test_killswitch_bypasses_block(self):
        sid = self._session_id()
        self._write_tier(sid, "heavy")
        self._enable_killswitch()
        try:
            result = run_hook(
                {"session_id": sid, "tool_name": "Bash"},
                self._tmp_home,
            )
            self.assertEqual(result.returncode, 0)
            out = decode_output(result)
            # killswitch: hook exits before any output
            self.assertIsNone(out)
        finally:
            self._cleanup_tier(sid)

    # ── native flag → always pass through ────────────────────────────────────

    def test_native_flag_bypasses_block(self):
        sid = self._session_id()
        self._write_tier(sid, "heavy")
        self._enable_native(sid)
        try:
            result = run_hook(
                {"session_id": sid, "tool_name": "Bash"},
                self._tmp_home,
            )
            self.assertEqual(result.returncode, 0)
            out = decode_output(result)
            self.assertIsNone(out)
        finally:
            self._cleanup_tier(sid)

    # ── no tier file → pass through ───────────────────────────────────────────

    def test_no_tier_file_passes_through(self):
        sid = self._session_id()
        # no tier file written
        result = run_hook(
            {"session_id": sid, "tool_name": "Edit"},
            self._tmp_home,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIsNone(decode_output(result))

    # ── agent_id present → pass through ──────────────────────────────────────

    def test_agent_id_bypasses_block(self):
        sid = self._session_id()
        self._write_tier(sid, "heavy")
        try:
            result = run_hook(
                {"session_id": sid, "tool_name": "Bash", "agent_id": "some-subagent-id"},
                self._tmp_home,
            )
            self.assertEqual(result.returncode, 0)
            self.assertIsNone(decode_output(result))
        finally:
            self._cleanup_tier(sid)

    # ── PASS_THROUGH tools → never blocked ───────────────────────────────────

    def test_read_passes_through_medium(self):
        sid = self._session_id()
        self._write_tier(sid, "medium")
        try:
            result = run_hook(
                {"session_id": sid, "tool_name": "Read"},
                self._tmp_home,
            )
            self.assertEqual(result.returncode, 0)
            self.assertIsNone(decode_output(result))
        finally:
            self._cleanup_tier(sid)

    def test_glob_passes_through_heavy(self):
        sid = self._session_id()
        self._write_tier(sid, "heavy")
        try:
            result = run_hook(
                {"session_id": sid, "tool_name": "Glob"},
                self._tmp_home,
            )
            self.assertEqual(result.returncode, 0)
            self.assertIsNone(decode_output(result))
        finally:
            self._cleanup_tier(sid)

    def test_grep_passes_through_heavy(self):
        sid = self._session_id()
        self._write_tier(sid, "heavy")
        try:
            result = run_hook(
                {"session_id": sid, "tool_name": "Grep"},
                self._tmp_home,
            )
            self.assertEqual(result.returncode, 0)
            self.assertIsNone(decode_output(result))
        finally:
            self._cleanup_tier(sid)

    # ── tier=medium → Edit and Write blocked, Bash passes ────────────────────

    def test_medium_blocks_edit(self):
        sid = self._session_id()
        self._write_tier(sid, "medium")
        try:
            result = run_hook(
                {"session_id": sid, "tool_name": "Edit"},
                self._tmp_home,
            )
            self.assertEqual(result.returncode, 0)
            out = decode_output(result)
            self.assertIsNotNone(out)
            self.assertEqual(out.get("decision"), "block")
        finally:
            self._cleanup_tier(sid)

    def test_medium_blocks_write(self):
        sid = self._session_id()
        self._write_tier(sid, "medium")
        try:
            result = run_hook(
                {"session_id": sid, "tool_name": "Write"},
                self._tmp_home,
            )
            self.assertEqual(result.returncode, 0)
            out = decode_output(result)
            self.assertIsNotNone(out)
            self.assertEqual(out.get("decision"), "block")
        finally:
            self._cleanup_tier(sid)

    def test_medium_allows_bash(self):
        sid = self._session_id()
        self._write_tier(sid, "medium")
        try:
            result = run_hook(
                {"session_id": sid, "tool_name": "Bash"},
                self._tmp_home,
            )
            self.assertEqual(result.returncode, 0)
            self.assertIsNone(decode_output(result))
        finally:
            self._cleanup_tier(sid)

    # ── tier=heavy → Edit, Write, and Bash all blocked ───────────────────────

    def test_heavy_blocks_edit(self):
        sid = self._session_id()
        self._write_tier(sid, "heavy")
        try:
            result = run_hook(
                {"session_id": sid, "tool_name": "Edit"},
                self._tmp_home,
            )
            self.assertEqual(result.returncode, 0)
            out = decode_output(result)
            self.assertIsNotNone(out)
            self.assertEqual(out.get("decision"), "block")
        finally:
            self._cleanup_tier(sid)

    def test_heavy_blocks_bash(self):
        sid = self._session_id()
        self._write_tier(sid, "heavy")
        try:
            result = run_hook(
                {"session_id": sid, "tool_name": "Bash"},
                self._tmp_home,
            )
            self.assertEqual(result.returncode, 0)
            out = decode_output(result)
            self.assertIsNotNone(out)
            self.assertEqual(out.get("decision"), "block")
        finally:
            self._cleanup_tier(sid)

    def test_heavy_blocks_write(self):
        sid = self._session_id()
        self._write_tier(sid, "heavy")
        try:
            result = run_hook(
                {"session_id": sid, "tool_name": "Write"},
                self._tmp_home,
            )
            self.assertEqual(result.returncode, 0)
            out = decode_output(result)
            self.assertIsNotNone(out)
            self.assertEqual(out.get("decision"), "block")
        finally:
            self._cleanup_tier(sid)


if __name__ == "__main__":
    unittest.main()
