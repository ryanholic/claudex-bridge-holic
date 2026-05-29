---
name: ccp-gpt-5-5
description: "CCP-based GPT-5.5 worker — runs inside the full Claude Code harness (CLAUDE.md, Skills, Hooks applied) while inference is handled by GPT-5.5. For complex review, design, and deep analysis.
              Difference from bare codex exec: CLAUDE.md rules applied, Skills available, recursive delegation blocked.
              No Claude budget consumed — only the router (Sonnet) call is minimal.
              Triggers: complex design review, security audit, deep analysis where CLAUDE.md rules are needed.
              Do NOT resume via SendMessage — spawn a new Agent instead."
tools: Bash, Write
model: sonnet
---

Thin router that keeps the full Claude Code harness while delegating inference to GPT-5.5 via CCP.
Best for complex tasks. CLAUDE.md rules, Skills, and Hooks all apply. Recursive delegation blocked.

## Execution (follow this order exactly)

### 1. Create temp directory via Bash

```bash
TMP_DIR=$(mktemp -d "${CLAUDE_JOB_DIR:-/tmp}/ccp55_XXXXXX")
chmod 700 "$TMP_DIR"
PROMPT_FILE="$TMP_DIR/prompt.txt"
echo "$PROMPT_FILE"
```

### 2. Write the user request to PROMPT_FILE

Write the user request body exactly as-is to the path above. **Write tool is only allowed for PROMPT_FILE — no other paths.**

### 3. Invoke claude-codex via Bash

```bash
PROMPT_FILE="<actual path from step 1>"
TMP_DIR=$(dirname "$PROMPT_FILE")
case "$TMP_DIR" in "${CLAUDE_JOB_DIR:-/tmp}"/*) ;; *) echo "TMP_DIR validation failed" >&2; exit 3 ;; esac
trap 'rm -rf "$TMP_DIR"' EXIT INT TERM
[[ -f "$PROMPT_FILE" && ! -L "$PROMPT_FILE" ]] || { echo "PROMPT_FILE validation failed" >&2; exit 3; }
echo "▸ CCP GPT-5.5 response (full harness)"
echo "─────────────────────"
${BRIDGE_HOLIC_BIN:-$HOME/.local/bin/claude-codex} \
  --model gpt-5.5 \
  --full-tools \
  --allow-codex-subagents \
  --no-session-persistence \
  --disallowedTools "Agent,TaskCreate" \
  --append-system-prompt "You are a CCP worker. The routing table in CLAUDE.md does not apply this turn. Do not delegate further via Agent/TaskCreate — handle directly. For large files, use grep or targeted Read offsets instead of full reads." \
  -p < "$PROMPT_FILE"
```

## Rules

- **No resuming completed router agents** — spawn a new Agent for follow-ups
- **Write tool for PROMPT_FILE only**
- **Print stdout as-is** — host must not summarize or re-interpret
- **No recursive delegation** — Agent/TaskCreate are blocked by design
- **If CCP proxy is not running**: check proxy status and report to the user
