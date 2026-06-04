#!/usr/bin/env bash
set -euo pipefail

# Opus 4.8 direct caller — bypass CCP/claude-code-proxy env leakage.
# Usage: opus < taskfile  OR  echo "prompt" | opus
exec env -i \
  HOME="$HOME" \
  PATH="$PATH" \
  TERM="${TERM:-xterm-256color}" \
  USER="${USER:-}" \
  LANG="${LANG:-en_US.UTF-8}" \
  CLAUDE_JOB_DIR="${CLAUDE_JOB_DIR:-}" \
  CLAUDE_OPUS_DIRECT_ACTIVE="${CLAUDE_OPUS_DIRECT_ACTIVE:-1}" \
  /Users/ryan_mini/.local/bin/claude \
    --model claude-opus-4-8 \
    --no-session-persistence \
    -p "$@"
