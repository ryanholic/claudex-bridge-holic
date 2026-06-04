#!/bin/bash
# SessionStart: native sessions start with Codex MCP mode ON unless /codex-off marker exists.
set -euo pipefail

session_id="${CLAUDE_CODE_SESSION_ID:-}"
if [ -z "$session_id" ]; then
  session_id=$(echo "${CLAUDE_HOOK_CONTEXT:-}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('session_id',''))" 2>/dev/null || true)
fi

[ -z "$session_id" ] && exit 0

native_flag="$HOME/.claude/codex_native_on_${session_id}"
codex_flag="$HOME/.claude/codex_mode_on_${session_id}"

# /codex-off explicitly disables auto-on for this session.
[ -f "$native_flag" ] && exit 0

mkdir -p "$HOME/.claude"
touch "$codex_flag"

cat <<'EOF'
Codex MCP mode auto-on. 실작업은 mcp__codex__codex만 사용. MCP 실패 시 직접 처리·ccp fallback 금지.
EOF

exit 0
