#!/usr/bin/env python3
import json
import os
import shlex
import sys

# 킬 스위치: touch ~/.claude/router_enforcer.off 로 즉시 비활성화
if os.path.exists(os.path.expanduser("~/.claude/router_enforcer.off")):
    sys.exit(0)

# Codex MCP 자체와 대화/상태관리 도구는 허용.
_ALWAYS_ALLOW = {
    "mcp__codex__codex",
    "AskUserQuestion",
    "TaskCreate",
    "TaskGet",
    "TaskList",
    "TaskUpdate",
    "PushNotification",
}

# codex-on에서 직접 실작업으로 새기 쉬운 도구.
_DENY_TOOLS = {
    "Edit",
    "Write",
    "Agent",
    "EnterPlanMode",
    "ExitPlanMode",
    "Skill",
    "WebSearch",
    "WebFetch",
    "Workflow",
    "NotebookEdit",
}

# 검증용 최소 Bash만 허용. 구현/탐색/수정 Bash는 차단.
_ALLOWED_BASH_FORMS = (
    ("git", "status"),
    ("git", "diff"),
    ("git", "branch", "--show-current"),
    ("git", "log"),
    ("python3", "-m", "py_compile"),
    ("python", "-m", "py_compile"),
    ("python3", "-m", "json.tool"),
    ("python", "-m", "json.tool"),
)
_SHELL_META = {"&&", "||", ";", "|", "&", ">", ">>", "<", "<<", "$(", "`"}


def _session_id(payload):
    return payload.get("session_id") or os.environ.get("CLAUDE_CODE_SESSION_ID") or "unknown"


def _codex_mode_on(session_id):
    native_flag = os.path.expanduser(f"~/.claude/codex_native_on_{session_id}")
    if os.path.exists(native_flag):
        return False
    codex_flag = os.path.expanduser(f"~/.claude/codex_mode_on_{session_id}")
    return os.path.exists(codex_flag)


def _tool_input(payload):
    value = payload.get("tool_input")
    return value if isinstance(value, dict) else {}


def _bash_allowed(command):
    try:
        parts = shlex.split(command or "")
    except ValueError:
        return False
    if not parts:
        return False
    if any(token in _SHELL_META or any(marker in token for marker in (";", "|", "`", "$(")) for token in parts):
        return False
    return any(tuple(parts[:len(form)]) == form for form in _ALLOWED_BASH_FORMS)


def _deny(reason):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        },
    }, ensure_ascii=False))
    return 0


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    if payload.get("agent_id") or payload.get("agent_type", "claude") != "claude":
        return 0

    tool_name = payload.get("tool_name", "")
    session_id = _session_id(payload)

    if not _codex_mode_on(session_id):
        return 0

    if tool_name in _ALWAYS_ALLOW or tool_name.startswith("mcp__codex__"):
        return 0

    if tool_name == "Bash":
        command = _tool_input(payload).get("command", "")
        if _bash_allowed(command):
            return 0
        return _deny(
            "codex-on: Bash 직접 실행은 금지입니다. 실작업은 mcp__codex__codex로 위임하세요. "
            "검증용 git status/diff/branch/log, py_compile만 허용됩니다. MCP 실패 시 fallback 금지."
        )

    if tool_name in _DENY_TOOLS:
        return _deny(
            f"codex-on: {tool_name} 직접 사용은 금지입니다. 실작업은 mcp__codex__codex로 위임하세요. "
            "MCP 실패 시 직접 처리·ccp fallback 금지."
        )

    # Read/Grep/Glob 등은 검수·원인 확인용으로 남긴다.
    # 대량 탐색은 UserPromptSubmit 지시와 γ 가드가 Codex MCP 위임을 요구한다.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
