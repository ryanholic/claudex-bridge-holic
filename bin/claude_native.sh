#!/usr/bin/env bash
set -euo pipefail

prepare_claude_tmpdir() {
  local dir="$1" owner uid mode acl_mode
  uid="$(id -u)"
  case "$dir" in
    *[[:space:]]*)
      printf '%s\n' "claude-native: refusing tmpdir path with whitespace: $dir" >&2
      exit 1
      ;;
  esac
  if [[ -L "$dir" ]]; then
    printf '%s\n' "claude-native: refusing symlink tmpdir: $dir" >&2
    exit 1
  fi
  if [[ ! -d "$dir" ]]; then
    mkdir -m 700 -p "$dir"
  fi
  if [[ -L "$dir" ]]; then
    printf '%s\n' "claude-native: refusing symlink tmpdir after mkdir: $dir" >&2
    exit 1
  fi
  owner="$(stat -f %u "$dir" 2>/dev/null || true)"
  if [[ "$owner" != "$uid" ]]; then
    printf '%s\n' "claude-native: tmpdir owner mismatch: $dir owner=$owner expected=$uid" >&2
    exit 1
  fi
  mode="$(stat -f %Lp "$dir" 2>/dev/null || true)"
  if [[ "$mode" != "700" ]]; then
    printf '%s\n' "claude-native: insecure tmpdir mode: $dir mode=$mode expected=700; remove it and retry" >&2
    exit 1
  fi
  acl_mode="$(ls -lde "$dir" 2>/dev/null | awk '{print $1}' || true)"
  if [[ "$acl_mode" == *+* ]]; then
    printf '%s\n' "claude-native: refusing tmpdir with ACL: $dir" >&2
    exit 1
  fi
}

native_tmpdir="${CLAUDE_NATIVE_TMPDIR:-/tmp/claude-native-$(id -u)}"
prepare_claude_tmpdir "$native_tmpdir"
native_tmpdir_real="$(cd "$native_tmpdir" && pwd -P)"

refuse_same_tmpdir_proxy_daemon() {
  local pid env_text daemon_tmpdir daemon_tmpdir_real
  while IFS= read -r pid; do
    [[ -n "$pid" ]] || continue
    env_text=$(ps eww -p "$pid" -o command= 2>/dev/null || true)
    daemon_tmpdir="$(printf '%s\n' "$env_text" | tr ' ' '\n' | awk -F= '$1 == "CLAUDE_CODE_TMPDIR" {print substr($0, index($0, "=") + 1); exit}')"
    [[ -n "$daemon_tmpdir" && -d "$daemon_tmpdir" ]] || continue
    daemon_tmpdir_real="$(cd "$daemon_tmpdir" 2>/dev/null && pwd -P || true)"
    [[ "$daemon_tmpdir_real" == "$native_tmpdir_real" ]] || continue
    case " $env_text " in
      *" ANTHROPIC_BASE_URL="*) ;;
      *) continue ;;
    esac

    printf '%s\n' "claude-native: proxy-env Claude daemon found in native tmpdir (pid=$pid)." >&2
    printf '%s\n' "claude-native: stop that daemon, then run native Claude again." >&2
    exit 1
  done < <(ps axww -o pid=,command= | awk '/claude daemon run/ && !/awk/ {print $1}')
}

refuse_same_tmpdir_proxy_daemon

exec env -u ANTHROPIC_BASE_URL \
  -u ANTHROPIC_AUTH_TOKEN \
  -u ANTHROPIC_MODEL \
  -u ANTHROPIC_SMALL_FAST_MODEL \
  -u CLAUDE_CODE_DISABLE_NONSTREAMING_FALLBACK \
  -u CLAUDE_CODE_PROXY_TOOL_MODE \
  -u CLAUDE_CODE_PROXY_LIGHT_TOOLS \
  -u CLAUDE_CODE_PROXY_EFFORT \
  -u CLAUDE_OPUS_DIRECT_ACTIVE \
  CLAUDE_CODE_TMPDIR="$native_tmpdir" \
  /Users/ryan_mini/.local/bin/claude "$@"
