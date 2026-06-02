#!/bin/bash
# Session-specific codex mode check
session_id="${CLAUDE_CODE_SESSION_ID}"
if [ -z "$session_id" ]; then
  session_id=$(echo "${CLAUDE_HOOK_CONTEXT:-}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('session_id',''))" 2>/dev/null)
fi

[ -z "$session_id" ] && exit 0

if [ -f "$HOME/.claude/codex_mode_on_${session_id}" ]; then
  cat <<'EOF'
🔴 CODEX 위임 모드 ON (/codex-on). 실작업(물량)은 codex MCP 도구로 위임 → Claude 버킷 절약.
호출: mcp__codex__codex(prompt, model, sandbox, approval-policy="never", cwd="<대상 repo 절대경로>")
- 조회/리서치/탐색      → model="gpt-5.4-mini", sandbox="read-only"
- 코딩/구현/수정/분석   → model="gpt-5.4",      sandbox="workspace-write"
- 리뷰/설계/보안감사    → model="gpt-5.5",      sandbox="read-only"
codex가 결과 텍스트를 직접 반환. 산출물(파일)은 mtime·git diff로 직접 검증 후에만 완료 처리.
판단·계획·검수·Ryan 커뮤니케이션은 Claude가 직접 유지(순수 라우터화 금지 — 거짓 완료를 잡는 주체).
MCP 미동작 시 fallback: Agent(subagent_type="ccp-gpt-5-4"/"ccp-gpt-5-4-mini"/"ccp-gpt-5-5").
해제: /codex-off
EOF
fi
exit 0
