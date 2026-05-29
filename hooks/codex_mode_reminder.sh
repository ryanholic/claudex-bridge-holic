#!/bin/bash
# UserPromptSubmit hook: reminds Claude of Codex mode status each turn
session_id="${CLAUDE_CODE_SESSION_ID}"
if [ -z "$session_id" ]; then
  session_id=$(echo "${CLAUDE_HOOK_CONTEXT:-}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('session_id',''))" 2>/dev/null)
fi

[ -z "$session_id" ] && exit 0

if [ -f "$HOME/.claude/codex_mode_on_${session_id}" ]; then
  cat <<'HINT'
[bridge-holic] Codex forced-delegation mode is ON (/codex-on active):
- Web research / library lookup / external info / recent trends → ccp-gpt-5-4-mini subagent
- Large file reads (500+ lines) / unfamiliar directory exploration → ccp-gpt-5-4-mini subagent
- New code (30+ lines) / feature implementation / script generation → ccp-gpt-5-4 subagent
- Code review / adversarial critique → ccp-codex-reviewer subagent
Direct handling is prohibited. Do not fall back to direct handling even if delegation result is insufficient.
Disable: /codex-off
HINT
fi
exit 0
