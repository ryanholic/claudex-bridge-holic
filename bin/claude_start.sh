#!/bin/zsh
set -euo pipefail

SESSION_NAME=$(tmux display-message -p '#S' 2>/dev/null || true)
[[ -z "$SESSION_NAME" ]] && SESSION_NAME="work"

exec env -u ANTHROPIC_BASE_URL \
  -u ANTHROPIC_AUTH_TOKEN \
  -u ANTHROPIC_MODEL \
  -u ANTHROPIC_SMALL_FAST_MODEL \
  -u CLAUDE_CODE_DISABLE_NONSTREAMING_FALLBACK \
  -u CLAUDE_CODE_PROXY_TOOL_MODE \
  -u CLAUDE_CODE_PROXY_LIGHT_TOOLS \
  -u CLAUDE_CODE_PROXY_EFFORT \
  -u CLAUDE_OPUS_DIRECT_ACTIVE \
  /Users/ryan_mini/.local/bin/claude --dangerously-skip-permissions --name "$SESSION_NAME"
