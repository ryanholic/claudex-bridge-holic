#!/usr/bin/env python3
import json
import os
import re
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
# WebSearch/WebFetch는 제외: codex worker는 네트워크 격리(전용 CODEX_HOME 최소 config +
# read-only 샌드박스)라 웹검색이 구조적으로 불가 → deny하면 갈 곳 없는 데드락이 된다.
# 웹검색/페치는 정보 수집(판단의 입력)이며 토큰 비용도 적어 차단 이득이 없다.
_DENY_TOOLS = {
    "Edit",
    "Write",
    "Agent",
    "EnterPlanMode",
    "ExitPlanMode",
    "Skill",
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

# 탈출구: codex 모드 토글/킬스위치 명령은 항상 허용한다.
# 그렇지 않으면 codex-on 가드가 codex-off가 쓰는 rm/touch 명령을 막아 데드락이 된다.
_CODEX_FLAG_RE = re.compile(r"codex_(?:mode_on|native_on)_|router_enforcer\.off|gamma_guard\.off")
_ESCAPE_FORBIDDEN = ("curl", "wget", "nc ", "ssh", "scp", "eval", "sudo", "node", "bash ", "/bin/sh", " sh ", "python")
_ESCAPE_VERBS = {"rm", "touch", "mkdir", "echo", "true", ":"}


def _is_codex_escape(command):
    """codex 상태 플래그·킬스위치 파일만 건드리는 rm/touch/mkdir/echo 조합이면 허용.
    &&·세션변수 가드(: "${...:?...}")가 섞여 있어도 통과시킨다."""
    if not command:
        return False
    if not _CODEX_FLAG_RE.search(command):
        return False
    low = command.lower()
    if any(tok in low for tok in _ESCAPE_FORBIDDEN):
        return False
    for seg in re.split(r"&&|\|\||;", command):
        seg = seg.strip()
        if not seg:
            continue
        head = seg.split()[0].strip()
        if head in _ESCAPE_VERBS or head.startswith(":"):
            continue
        return False
    return True


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
        if _bash_allowed(command) or _is_codex_escape(command):
            return 0
        return _deny(
            "codex-on: Bash 직접 실행은 금지입니다. 실작업은 mcp__codex__codex로 위임하세요. "
            "검증용 git status/diff/branch/log, py_compile만 허용됩니다. MCP 실패 시 fallback 금지."
        )

    if tool_name == "Skill":
        skill = str(_tool_input(payload).get("skill", ""))
        if skill in {"codex-off", "codex-on", "codex-model"}:
            return 0

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
