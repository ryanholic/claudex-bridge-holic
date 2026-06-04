#!/usr/bin/env python3
"""
Agent 툴 호출 시 claude-* 계열 subagent_type을 GPT 계열로 강제 리다이렉트.
CLAUDE.md 규칙: Claude 버킷 이중 소모 방지.

예외: Ryan이 명시적으로 요청한 경우 one-shot 플래그 파일로 통과 가능.
  사용법: Bash("touch ~/.claude/allow_claude_agent_${CLAUDE_CODE_SESSION_ID}") 먼저 실행 후 Agent 호출.
  훅이 플래그를 확인하면 즉시 삭제(one-shot)하고 통과.

단, CCP codex mode에서는 `claude-opus`를 항상 차단한다.
이 경우 실제 Opus 요청은 `ccp-opus-direct` Bash helper로만 우회한다.
"""
import sys
import json
import os

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

tool_name = data.get("tool_name", "")
if tool_name != "Agent":
    sys.exit(0)

tool_input = data.get("tool_input", {})
subagent_type = tool_input.get("subagent_type", "")

REDIRECT_MAP = {
    "claude-opus":   ("gpt-5-5",       "복잡한 판단·설계검토"),
    "claude-haiku":  ("gpt-5-4-mini",  "간단한 분류·변환·빠른 처리"),
    "claude-sonnet": (None,             "현재 세션이 이미 Sonnet — 서브에이전트 불필요"),
}

if subagent_type not in REDIRECT_MAP:
    sys.exit(0)

session_id = data.get("session_id", "")
home = os.path.expanduser("~")
codex_mode = bool(session_id) and os.path.exists(
    os.path.join(home, ".claude", f"codex_mode_on_{session_id}")
)

# CCP codex mode에서는 claude-opus one-shot 예외도 허용하지 않음
if subagent_type == "claude-opus" and codex_mode:
    msg = (
        "🚫 Claude 계열 서브에이전트 차단: claude-opus\n"
        "CCP 세션에서는 `Agent(subagent_type=\"claude-opus\")`가 실제 Opus가 아니라 프록시를 타게 됩니다.\n"
        "→ 사용자 요청 본문을 temp prompt file로 저장한 뒤 Bash에서 `ccp-opus-direct <prompt-file>`를 사용하세요.\n\n"
        "CLAUDE.md 라우팅 규칙 위반 — CCP 명시 Opus 요청은 Bash direct path만 허용."
    )
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": msg,
        }
    }))
    sys.exit(0)

# 명시적 사용자 요청 플래그 확인 (one-shot: 확인 즉시 삭제)
if session_id:
    flag = os.path.join(home, ".claude", f"allow_claude_agent_{session_id}")
    if os.path.exists(flag):
        try:
            os.remove(flag)
        except OSError:
            pass
        sys.exit(0)  # 통과

gpt_alt, reason = REDIRECT_MAP[subagent_type]

if gpt_alt:
    msg = (
        f"🚫 Claude 계열 서브에이전트 차단: {subagent_type}\n"
        f"→ subagent_type=\"{gpt_alt}\" 으로 교체하세요 ({reason})\n\n"
        "CLAUDE.md 라우팅 규칙 위반 — Claude 버킷 이중 소모 방지."
    )
else:
    msg = (
        f"🚫 Claude 계열 서브에이전트 차단: {subagent_type}\n"
        f"이유: {reason}\n\n"
        "별도 서브에이전트 없이 현재 세션에서 직접 처리하세요."
    )

print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": msg,
    }
}))
sys.exit(0)
