#!/usr/bin/env python3
import json
import os
import sys

# 킬 스위치: touch ~/.claude/router_enforcer.off 로 즉시 비활성화
if os.path.exists(os.path.expanduser("~/.claude/router_enforcer.off")):
    sys.exit(0)

PASS_THROUGH = {"Read", "Glob", "Grep"}
BLOCKABLE = {"Edit", "Write"}
AGENT_MAP = {"medium": "ccp-gpt-5-4", "heavy": "ccp-gpt-5-5"}

_TIER_BLOCK = {
    "medium": {"Edit", "Write"},
    "heavy":  {"Edit", "Write", "Bash"},
}


def hint(tool_name, tier, payload):
    suggested = "ccp-gpt-5-4" if tool_name in ("Edit", "Write") else AGENT_MAP.get(tier, "ccp-gpt-5-4")
    msg = (
        f"[router-hint] {tool_name} 직접 실행 중 (tier={tier}). "
        f"무거운 작업이면 Agent(subagent_type=\"{suggested}\")로 위임을 고려하세요. (강제 아님 — 실행은 허용됨)"
    )
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": msg,
        },
    }, ensure_ascii=False))


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    if payload.get("agent_id") or payload.get("agent_type", "claude") != "claude":
        return 0

    tool_name = payload.get("tool_name", "")

    session_id = payload.get("session_id", "unknown")

    # codex-off (native mode) is active — bypass all blocking
    native_flag = os.path.expanduser(f"~/.claude/codex_native_on_{session_id}")
    if os.path.exists(native_flag):
        return 0

    try:
        with open(f"/tmp/claude_tier_{session_id}.json") as f:
            state = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return 0

    tier = state.get("tier", "")
    if tool_name not in _TIER_BLOCK.get(tier, set()):
        return 0

    hint(tool_name, tier, payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
