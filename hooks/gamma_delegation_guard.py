#!/usr/bin/env python3
"""γ 위임 가드 (Agent 도구).

- PreToolUse(Agent)  : 동일 위임(subagent_type+prompt) 중복 호출 소프트경고 (#2 #10).
- PostToolUse(Agent) : 워커가 쓰기·완료를 주장하면 부모에 '직접 검증' 리마인더 주입 (#1 #7).

원칙: deny 없음·fail-open. 잘못돼도 위임을 막지 않는다 (라이브 잡 보호).
킬스위치: touch ~/.claude/gamma_guard.off
"""

import hashlib
import json
import os
import sys
import time

if os.path.exists(os.path.expanduser("~/.claude/gamma_guard.off")):
    sys.exit(0)

DEDUP_WINDOW = 600  # 초. 동일 위임이 이 안에 재호출되면 경고.
WORKER_PREFIX = "ccp-"  # GPT 워커 위임만 대상 (claude-* 서브에이전트 제외)

# 쓰기·완료 주장 (과거형 동사). 읽기작업("조회/확인 완료")은 매칭 안 되게 일반 "완료" 제외.
WRITE_CLAIM = (
    "수정했", "작성했", "생성했", "구현했", "반영했", "추가했",
    "고쳤", "커밋했", "삭제했", "변경했", "적용했", "교체했",
)


def emit(event: str, msg: str) -> None:
    print(json.dumps(
        {"hookSpecificOutput": {"hookEventName": event, "additionalContext": msg}},
        ensure_ascii=False,
    ))


def call_key(tool_input: dict) -> str:
    st = str(tool_input.get("subagent_type", ""))
    prompt = str(tool_input.get("prompt", ""))
    return hashlib.sha256(f"{st}\0{prompt}".encode("utf-8", "replace")).hexdigest()[:16]


def pre_dedup(session_id: str, tool_input: dict) -> None:
    st = str(tool_input.get("subagent_type", ""))
    if not st.startswith(WORKER_PREFIX):
        return
    key = call_key(tool_input)
    path = f"/tmp/claude_gamma_calls_{session_id}.json"
    now = time.time()
    try:
        with open(path) as f:
            calls = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        calls = {}
    calls = {k: v for k, v in calls.items() if now - v < DEDUP_WINDOW}
    prev = calls.get(key)
    calls[key] = now
    try:
        with open(path, "w") as f:
            json.dump(calls, f)
    except OSError:
        pass
    if prev is not None:
        ago = int(now - prev)
        emit(
            "PreToolUse",
            f"[γ-dedup] 동일 위임(subagent={st}, 동일 프롬프트)이 {ago}초 전 실행됐습니다. "
            f"이전 결과를 재사용할 수 있으면 이 호출을 생략하세요. 의도된 재시도면 그대로 진행. (강제 아님)",
        )


def post_verify(tool_input: dict, tool_response) -> None:
    st = str(tool_input.get("subagent_type", ""))
    if not st.startswith(WORKER_PREFIX):
        return
    text = tool_response if isinstance(tool_response, str) else json.dumps(tool_response, ensure_ascii=False)
    if any(kw in text for kw in WRITE_CLAIM):
        emit(
            "PostToolUse",
            f"[γ-verify] 워커({st})가 변경·완료를 주장합니다. 자기보고를 신뢰하지 말고 "
            f"산출물 파일의 존재·mtime 또는 git diff를 직접 확인한 뒤에만 '완료'로 처리하세요. "
            f"변경이 감지되지 않으면 '미완료'로 간주하고 1회 재위임하세요. (강제 아님)",
        )


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    # 서브에이전트 내부에서 발생한 호출은 스킵 (이중주입 방지)
    if payload.get("agent_id") or payload.get("agent_type", "claude") != "claude":
        return 0
    if payload.get("tool_name", "") != "Agent":
        return 0
    event = payload.get("hook_event_name") or payload.get("hookEventName") or ""
    tool_input = payload.get("tool_input", {}) or {}
    session_id = payload.get("session_id", "unknown")
    try:
        if event == "PreToolUse":
            pre_dedup(session_id, tool_input)
        elif event == "PostToolUse":
            post_verify(tool_input, payload.get("tool_response", payload.get("tool_result", "")))
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
