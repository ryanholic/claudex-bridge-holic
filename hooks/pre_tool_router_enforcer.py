#!/usr/bin/env python3
import json
import os
import sys

# 킬 스위치: touch ~/.claude/router_enforcer.off 로 즉시 비활성화
if os.path.exists(os.path.expanduser("~/.claude/router_enforcer.off")):
    sys.exit(0)

PASS_THROUGH = {"Read", "Glob", "Grep"}
AGENT_MAP = {"medium": "ccp-gpt-5-4", "heavy": "ccp-gpt-5-5"}

_TIER_BLOCK = {
    "medium": {"Edit", "Write"},
    "heavy":  {"Edit", "Write", "Bash"},
}


def block(tool_name, tier, payload):
    suggested = "ccp-gpt-5-4" if tool_name in ("Edit", "Write") else AGENT_MAP.get(tier, "ccp-gpt-5-4")
    reason = (
        f"[router-enforcer] {tool_name} 직접 실행 차단 (tier={tier}). "
        f"-> Agent(subagent_type=\"{suggested}\", prompt=\"...\") 로 위임하세요."
    )
    print(json.dumps({
        "decision": "block",
        "reason": reason,
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        },
    }, ensure_ascii=False))


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    # agent_id check is the real guard; agent_type check is defensive dead code
    if payload.get("agent_id") or payload.get("agent_type", "claude") != "claude":
        return 0

    tool_name = payload.get("tool_name", "")

    session_id = payload.get("session_id", "unknown")

    # codex-off (native mode) is active — bypass all blocking
    native_flag = os.path.expanduser(f"~/.claude/codex_native_on_{session_id}")
    if os.path.exists(native_flag):
        return 0

    # Tier file is written by an external hook/command that classifies task complexity.
    # If it doesn't exist (default for most setups), this hook passes through all tools.
    # "medium" -> blocks Edit/Write;  "heavy" -> blocks Edit/Write/Bash
    try:
        with open(f"/tmp/claude_tier_{session_id}.json") as f:
            state = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return 0

    tier = state.get("tier", "")
    if tool_name not in _TIER_BLOCK.get(tier, set()):
        return 0

    block(tool_name, tier, payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
