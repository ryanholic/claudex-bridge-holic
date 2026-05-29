First, run this Bash command to activate Codex mode:

```bash
: "${CLAUDE_CODE_SESSION_ID:?CLAUDE_CODE_SESSION_ID not set}" && mkdir -p ~/.claude && touch ~/.claude/codex_mode_on_${CLAUDE_CODE_SESSION_ID} && rm -f ~/.claude/codex_native_on_${CLAUDE_CODE_SESSION_ID} && echo "Codex mode activated: codex_mode_on_${CLAUDE_CODE_SESSION_ID}"
```

**Codex forced-delegation mode is now ON for this session.**

## Mandatory delegation (no direct handling)

| Task type | Delegate to |
|---|---|
| Web research / library lookup / external info | **ccp-gpt-5-4-mini** |
| Large file reading (500+ lines) / directory exploration | **ccp-gpt-5-4-mini** |
| New code (30+ lines) / feature implementation / scripts | **ccp-gpt-5-4** |
| Code review / adversarial critique | **ccp-codex-reviewer** |

## Prohibited

- Answering questions about external systems/libraries from training knowledge
- Directly reading files over 500 lines
- Writing 30+ lines of code directly

## Rules

- Keep the `▸ {name} · {model}` header from agent responses in your reply
- If delegation result is insufficient, re-delegate or supplement — do not fall back to direct handling
- Disable with `/codex-off`

**Codex mode ON. All matching tasks will be routed to Codex subagents.**
