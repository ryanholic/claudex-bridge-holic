#!/usr/bin/env python3
"""UserPromptSubmit hook: 프롬프트 분류 → 적합 모델/에이전트 힌트를 additionalContext로 주입."""

import json
import os
import re
import subprocess
import sys

# --- 키워드 패턴 ---

# advisor: 사용자 명시 요청 — 최우선 체크
_ADVISOR = re.compile(
    r"어드바이저|advisor|오푸스\s*리뷰|opus\s*리뷰|오푸스로|opus로",
    re.I,
)

# heavy: 설계·복잡 추론·리뷰·보안
_HEAVY = re.compile(
    r"설계|아키텍처|architecture|(?:코드\s*)?리뷰|review|검토|분석|analysis"
    r"|전략|strategy|최적화|optim|refactor|리팩터|보안|security|audit|취약"
    r"|prd|복잡|complex|tradeoff|트레이드|pros.*cons|프로.*콘스",
    re.I,
)

# medium: 코딩·버그 수정·구현
_MEDIUM = re.compile(
    r"고쳐|수정|fix|bug|버그|에러|error|exception"
    r"|구현|implement|작성|짜줘|코드\s*써|함수|function"
    r"|추가해|migration|migrate|테스트.*짜|짜.*테스트"
    r"|리서치|웹검색|검색해|찾아봐|탐색해|살펴봐|조사해",
    re.I,
)

# light: 조회·목록·단순 질문
_LIGHT = re.compile(
    r"보여줘|목록|리스트|\blist\b|\bls\b|파일.*있|있.*파일"
    r"|뭐야|뭔가|what is|어디.*있|있.*어디|경로|path"
    r"|확인해줘|\bcheck\b|간단히|briefly|설명해줘",
    re.I,
)

# 컨텍스트 의존 신호 — 이 개수가 높으면 Claude 선호
_CTX = re.compile(
    r"기존|현재|우리|이\s*코드|이\s*프로젝트|이\s*레포"
    r"|위에서|방금|이전|아까"
    r"|src/|lib/|\.py\b|\.ts\b|\.tsx\b|\.go\b",
    re.I,
)


def _spark_classify(prompt: str) -> str:
    """regex 미히트 시 Spark으로 폴백 분류. 실패하면 'medium' 반환."""
    spark_prompt = (
        "아래 프롬프트를 light/medium/heavy 중 하나로만 분류해. "
        "단어 하나만 출력:\n"
        "- light: 단순 조회·목록·짧은 질문\n"
        "- medium: 코딩·구현·버그 수정·탐색·리서치·웹검색\n"
        "- heavy: 설계·리뷰·보안 감사·복잡한 분석\n\n"
        f"프롬프트: {prompt[:500]}"
    )
    try:
        result = subprocess.run(
            ["codex", "exec", "--ignore-user-config", "-m", "gpt-5.3-codex-spark", spark_prompt],
            capture_output=True, text=True, timeout=8,
        )
        output = result.stdout.strip().lower()
        for tier in ("heavy", "medium", "light"):
            if tier in output:
                return tier
    except Exception:
        pass
    return "medium"


def classify(prompt: str) -> tuple[str, bool]:
    """(tier, needs_context) 반환. tier: 'heavy'|'medium'|'light'"""
    # 슬래시커맨드는 라우터 차단 대상 아님 — 항상 light로 통과
    if prompt.strip().startswith("/"):
        return "light", False
    if _ADVISOR.search(prompt):
        return "advisor", False
    # heavy 우선
    if _HEAVY.search(prompt):
        tier = "heavy"
    elif _MEDIUM.search(prompt):
        tier = "medium"
    elif _LIGHT.search(prompt) or len(prompt.strip()) < 120:
        tier = "light"
    else:
        tier = _spark_classify(prompt)

    ctx_hits = len(_CTX.findall(prompt))
    needs_context = ctx_hits >= 2
    return tier, needs_context


def build_hint(tier: str, needs_context: bool) -> str:
    if tier == "advisor":
        return (
            "【모델 라우터 — advisor】"
            " 사용자가 명시적으로 advisor/Opus를 요청했습니다."
            " → 즉시 advisor() 를 호출하세요."
        )
    if tier == "heavy":
        if needs_context:
            return (
                "【모델 라우터 — heavy + 컨텍스트 의존】"
                " 기존 코드베이스 참조가 필요한 복잡 작업입니다."
                " → 현재 세션에서 Read/Grep으로 탐색 후 `ccp-gpt-5-5` 서브에이전트를 호출하세요."
            )
        return (
            "【모델 라우터 — heavy】"
            " 복잡한 추론·설계·구현 작업입니다."
            " → `ccp-gpt-5-5` 서브에이전트를 호출하세요."
        )

    if tier == "medium":
        if needs_context:
            return (
                "【모델 라우터 — medium + 컨텍스트 의존】"
                " 기존 코드 참조가 필요한 코딩/수정 작업입니다."
                " → 현재 세션에서 Read/Grep으로 탐색 후 `ccp-gpt-5-4` 서브에이전트를 호출하세요."
            )
        return (
            "【모델 라우터 — medium】"
            " 코딩·버그 수정·구현 작업입니다."
            " → `ccp-gpt-5-4` 서브에이전트를 호출하세요."
        )

    # light
    return (
        "【모델 라우터 — light】"
        " 간단한 조회·질문입니다."
        " → `ccp-gpt-5-4-mini` 서브에이전트를 호출하세요."
    )


def main() -> None:
    raw = os.environ.get("CLAUDE_HOOK_CONTEXT", "") or sys.stdin.read()
    try:
        ctx = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    # 서브에이전트 세션 판별 — agent_type이 'claude'가 아니면 라우팅 힌트 주입 금지.
    # (예: agent_type='claude-opus', 'ccp-gpt-5-4' 등 — 이미 라우팅된 컨텍스트에서
    #  추가 힌트를 주입하면 에이전트 지시문과 충돌해 잘못된 동작 유발)
    agent_type = ctx.get("agent_type", "")
    if agent_type and agent_type != "claude":
        sys.exit(0)

    prompt = ctx.get("prompt") or ctx.get("message") or ctx.get("user_prompt") or ""
    if len(prompt.strip()) < 8:
        sys.exit(0)

    tier, needs_context = classify(prompt)

    # PreToolUse hook이 tier를 읽을 수 있도록 세션별 상태 파일 기록
    session_id = ctx.get("session_id", "unknown")
    try:
        with open(f"/tmp/claude_tier_{session_id}.json", "w") as _f:
            import json as _json
            _json.dump({"tier": tier, "needs_context": needs_context}, _f)
    except OSError:
        pass

    from pathlib import Path as _Path

    # Codex 모드 ON 감지: ~/.claude/codex_mode_on_{session_id} 파일 존재 여부
    # 환경변수 CLAUDE_SESSION_ID 우선, 없으면 ctx의 session_id 사용
    env_session_id = os.environ.get("CLAUDE_SESSION_ID", "")
    codex_mode_session = env_session_id if env_session_id else session_id
    codex_mode_flag = _Path.home() / f".claude/codex_mode_on_{codex_mode_session}"

    if codex_mode_flag.exists():
        # Codex 모드 ON: tier 무관하게 강제 위임 힌트 주입
        # (codex_mode_reminder.sh가 이미 상세 메시지를 출력하므로 여기서는 짧게)
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "UserPromptSubmit",
                        "additionalContext": (
                            "【모델 라우터 — CODEX 강제】"
                            " 모든 작업을 ccp-gpt 에이전트로 위임하세요."
                            " → 조회/탐색: `ccp-gpt-5-4-mini`,"
                            " 코딩/분석: `ccp-gpt-5-4`,"
                            " 리뷰/설계: `ccp-gpt-5-5`"
                        ),
                    }
                },
                ensure_ascii=False,
            )
        )
        return

    # Codex 모드 OFF: 아무 힌트도 주입하지 않음
    # (native_flag /codex-off 처리도 힌트 없음으로 통일)
    return


if __name__ == "__main__":
    main()
