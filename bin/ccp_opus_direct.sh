#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: ccp-opus-direct <prompt-file>" >&2
  exit 2
fi

PROMPT_FILE="$1"
if [[ ! -f "$PROMPT_FILE" || -L "$PROMPT_FILE" ]]; then
  echo "PROMPT_FILE 검증 실패" >&2
  exit 3
fi

PROMPT_DIR="$(cd "$(dirname "$PROMPT_FILE")" && pwd)"
case "$PROMPT_DIR" in
  "${CLAUDE_JOB_DIR:-/tmp}"/*) ;;
  *)
    echo "PROMPT_DIR 검증 실패" >&2
    exit 3
    ;;
esac

if command -v opus >/dev/null 2>&1; then
  OPUS_CMD=("$(command -v opus)")
else
  CLAUDE_BIN="${CLAUDE_BIN:-$(command -v claude || true)}"
  if [[ -z "$CLAUDE_BIN" ]]; then
    echo "opus/claude 실행 파일을 찾지 못함" >&2
    exit 127
  fi
  OPUS_CMD=("$CLAUDE_BIN" --model opus --no-session-persistence -p)
fi

echo "▸ Claude Opus 응답"
echo "─────────────────────"

env -i \
  HOME="$HOME" \
  PATH="$PATH" \
  TERM="${TERM:-xterm-256color}" \
  USER="${USER:-}" \
  LANG="${LANG:-en_US.UTF-8}" \
  CLAUDE_JOB_DIR="${CLAUDE_JOB_DIR:-}" \
  CLAUDE_OPUS_DIRECT_ACTIVE=1 \
  "${OPUS_CMD[@]}" < "$PROMPT_FILE"
