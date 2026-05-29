#!/usr/bin/env bash
set -euo pipefail

# ─── colors ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BOLD='\033[1m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✓${NC} $*"; }
warn() { echo -e "${YELLOW}⚠${NC}  $*"; }
err()  { echo -e "${RED}✗${NC} $*"; exit 1; }
info() { echo -e "  $*"; }

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_BIN="$HOME/.local/bin"
mkdir -p "$LOCAL_BIN"

echo ""
echo -e "${BOLD}claudex-bridge-holic installer${NC}"
echo "────────────────────────────────"

# ─── prerequisite: Claude Code ────────────────────────────────────────────────
command -v claude &>/dev/null || err "Claude Code not found. Install it first: https://claude.ai/code"
ok "Claude Code found: $(claude --version 2>/dev/null | head -1)"

# ─── step 1: raine/claude-code-proxy ──────────────────────────────────────────
echo ""
echo -e "${BOLD}Step 1: raine/claude-code-proxy${NC}"

PROXY_BIN="${BRIDGE_HOLIC_PROXY_BIN:-$LOCAL_BIN/claude-code-proxy-headless}"
PROXY_PORT="${CLAUDE_CODE_PROXY_PORT:-18765}"
PROXY_URL="http://127.0.0.1:${PROXY_PORT}"

if [[ -x "$PROXY_BIN" ]]; then
  ok "claude-code-proxy-headless found: $PROXY_BIN"
else
  warn "claude-code-proxy-headless not found at $PROXY_BIN"
  echo ""
  echo "  raine/claude-code-proxy is required. Install options:"
  echo ""
  echo "  Option A — download release binary (recommended):"
  echo "    https://github.com/raine/claude-code-proxy/releases"
  echo "    → place the binary at: $PROXY_BIN"
  echo ""
  echo "  Option B — build from source (requires Node.js 22+):"
  echo "    git clone https://github.com/raine/claude-code-proxy"
  echo "    cd claude-code-proxy && npm install && npm run build"
  echo "    cp dist/headless $PROXY_BIN && chmod +x $PROXY_BIN"
  echo ""
  read -r -p "  Continue install without proxy? [y/N] " ans
  ans="$(echo "$ans" | tr '[:upper:]' '[:lower:]')"
  [[ "$ans" == "y" ]] || exit 1
fi

# ─── step 2: claude-codex launcher ────────────────────────────────────────────
echo ""
echo -e "${BOLD}Step 2: claude-codex launcher${NC}"

LAUNCHER="$LOCAL_BIN/claude-codex"
if [[ -f "$LAUNCHER" ]]; then
  cp "$LAUNCHER" "${LAUNCHER}.bak"
  info "Backed up existing launcher → ${LAUNCHER}.bak"
fi
cp "$REPO_DIR/bin/claude-codex" "$LAUNCHER"
chmod +x "$LAUNCHER"
ok "Launcher installed: $LAUNCHER"

# Inject proxy bin path if non-default
if [[ "${BRIDGE_HOLIC_PROXY_BIN:-}" != "" ]]; then
  sed -i.bak "s|BRIDGE_HOLIC_PROXY_BIN:-\$HOME/.local/bin/claude-code-proxy-headless|BRIDGE_HOLIC_PROXY_BIN:-$BRIDGE_HOLIC_PROXY_BIN|" "$LAUNCHER"
  rm -f "${LAUNCHER}.bak"
fi

# ─── step 3: verify proxy health (optional) ───────────────────────────────────
echo ""
echo -e "${BOLD}Step 3: proxy health check${NC}"
if curl -sf --max-time 2 "${PROXY_URL}/healthz" >/dev/null 2>&1; then
  ok "Proxy responding at $PROXY_URL"
elif [[ -x "$PROXY_BIN" ]]; then
  info "Proxy not running — it will auto-start when you launch claude-codex."
else
  warn "Proxy not running and binary not found. Complete Step 1 before using."
fi

# ─── step 4: install agents ───────────────────────────────────────────────────
echo ""
echo -e "${BOLD}Step 4: agents${NC}"
AGENTS_DIR="$HOME/.claude/agents"
mkdir -p "$AGENTS_DIR"
for f in "$REPO_DIR"/agents/ccp-*.md; do
  name=$(basename "$f")
  [[ -f "$AGENTS_DIR/$name" ]] && cp "$AGENTS_DIR/$name" "$AGENTS_DIR/$name.bak" && info "Backed up $name"
  cp "$f" "$AGENTS_DIR/$name"
  ok "Agent: $name"
done

# ─── step 5: install hooks ────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}Step 5: hooks${NC}"
UPS_DIR="$HOME/.claude/hooks/UserPromptSubmit"
HOOKS_DIR="$HOME/.claude/hooks"
mkdir -p "$UPS_DIR"

install_hook() {
  local src="$1" dst="$2" label="$3"
  [[ -f "$dst" ]] && cp "$dst" "${dst}.bak" && info "Backed up $(basename "$dst")"
  cp "$src" "$dst"
  chmod +x "$dst"
  ok "Hook: $label"
}

install_hook "$REPO_DIR/hooks/codex_mode_reminder.sh"        "$UPS_DIR/codex_mode_reminder.sh"       "codex_mode_reminder.sh"
install_hook "$REPO_DIR/hooks/codex_tier_writer.py"          "$UPS_DIR/codex_tier_writer.py"         "codex_tier_writer.py (tier → enforcer)"
install_hook "$REPO_DIR/hooks/auto_model_router.py"          "$UPS_DIR/auto_model_router.py"         "auto_model_router.py (routing hints)"
install_hook "$REPO_DIR/hooks/pre_tool_router_enforcer.py"   "$HOOKS_DIR/pre_tool_router_enforcer.py" "pre_tool_router_enforcer.py (write blocker)"
install_hook "$REPO_DIR/hooks/pre_agent_claude_redirect.py"  "$HOOKS_DIR/pre_agent_claude_redirect.py" "pre_agent_claude_redirect.py (agent redirect)"

# ─── step 6: install commands ─────────────────────────────────────────────────
echo ""
echo -e "${BOLD}Step 6: slash commands${NC}"
COMMANDS_DIR="$HOME/.claude/commands"
mkdir -p "$COMMANDS_DIR"
for f in "$REPO_DIR"/commands/codex-*.md; do
  name=$(basename "$f")
  [[ -f "$COMMANDS_DIR/$name" ]] && cp "$COMMANDS_DIR/$name" "$COMMANDS_DIR/$name.bak" && info "Backed up $name"
  cp "$f" "$COMMANDS_DIR/$name"
  ok "Command: /$(basename "$name" .md)"
done

# ─── self-test ────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}Self-test${NC}"
if [[ -x "$PROXY_BIN" ]]; then
  info "Running: claude-codex --model gpt-5.4-mini -p '2+2?'"
  if result=$(claude-codex --model gpt-5.4-mini -p '2+2?' 2>&1); then
    ok "Proxy + launcher working. Response: ${result:0:80}"
  else
    warn "Self-test failed. Check: claude-codex-status (if installed) or /tmp/ccp.log"
  fi
else
  info "Skipping self-test (proxy binary not installed yet)."
fi

# ─── done ─────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}Installation complete.${NC}"
echo ""
# PATH check
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
  warn "~/.local/bin is not in your PATH."
  echo "  Add this to your shell profile (~/.zshrc or ~/.bashrc):"
  echo "    export PATH=\"\$HOME/.local/bin:\$PATH\""
  echo ""
fi
# CLAUDE_BIN hint (claude-opus agent)
CLAUDE_RESOLVED="$(command -v claude 2>/dev/null || true)"
if [[ -n "$CLAUDE_RESOLVED" ]]; then
  info "claude-opus agent: ${CLAUDE_BIN:-claude} → resolved to $CLAUDE_RESOLVED"
  info "  To override: export CLAUDE_BIN=/path/to/claude"
fi

echo "Quick start:"
echo "  claude-codex               # start a Codex-backed Claude session"
echo "  claude-codex --full-tools  # with full tool access (MCP, Agent, etc.)"
echo ""
echo "Inside a session:"
echo "  /codex-on   — route all tasks to Codex subagents"
echo "  /codex-off  — back to Claude direct"
echo ""
echo "Docs: https://github.com/ryanholic/claudex-bridge-holic"
