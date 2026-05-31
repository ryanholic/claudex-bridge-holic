#!/bin/bash
# Session-specific codex mode check
session_id="${CLAUDE_CODE_SESSION_ID}"
if [ -z "$session_id" ]; then
  session_id=$(echo "${CLAUDE_HOOK_CONTEXT:-}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('session_id',''))" 2>/dev/null)
fi

[ -z "$session_id" ] && exit 0

if [ -f "$HOME/.claude/codex_mode_on_${session_id}" ]; then
  cat <<'EOF'
🔴 CODEX 강제 위임 모드 ON (이 세션에서 /codex-on 으로 활성화됨):
- 웹 리서치 / 라이브러리 조사 / 외부 정보 / 최신 동향 → ccp-gpt-5-4-mini 서브에이전트
- 500줄 이상 파일 읽기 / 낯선 디렉토리 탐색 → ccp-gpt-5-4 서브에이전트
- 30줄 이상 코드 신규 작성 / 기능 구현 / 스크립트 생성 → ccp-gpt-5-4 서브에이전트
- 코드 리뷰 / 적대적 검토 → ccp-gpt-5-5 서브에이전트
직접 처리 금지. 위임 결과가 불충분해도 직접 처리로 대체하지 않는다.
해제: /codex-off
EOF
fi
exit 0
