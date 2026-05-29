# claudex-bridge-holic

> Stay in Claude Code. Let Codex do the work.

**Built on top of [raine/claude-code-proxy](https://github.com/raine/claude-code-proxy).** This repo assumes you already have it running.

---

## The problem

You've spent real time setting up Claude Code exactly the way you want it.

Custom CLAUDE.md rules. Skills for every workflow. Hooks that keep things consistent. A whole harness tuned to how you think.

Then you hit the Claude Max usage limit. You subscribe to Codex Pro too.

Now what?

**Using Codex CLI separately means leaving everything behind.** Different commands. Different context. None of your rules, Skills, or Hooks apply. It feels like starting over.

So you end up using Claude until it hits the limit, then manually switching to Codex — or just not using Codex much at all, leaving that subscription mostly idle.

---

## What claudex-bridge-holic does

It runs Codex as a subagent **inside** Claude Code.

You never leave your environment. You keep your CLAUDE.md rules, your Skills, your Hooks. The router decides which tasks go to Claude and which go to Codex — automatically, based on task type.

```
You type something in Claude Code
          │
          ▼
   Sonnet (router)
          │
          ├─ lightweight tasks  →  Codex mini  (fast, cheap)
          ├─ coding / bugfix    →  Codex 5.4   (standard)
          ├─ review / audit     →  Codex 5.5   (deep)
          └─ adversarial review →  Codex 5.5   (your rules applied)
```

Codex runs in an isolated subagent context. Your CLAUDE.md rules follow it there. The results come back to your main session. You never notice the switch.

**Same workflow. Two subscriptions running at capacity.**

---

## A note on ToS

Using Codex backends via a local proxy is a gray area. raine's README puts it plainly: *"using the Codex or Kimi backends from a non-official client is a gray area."* Use at your own discretion.

---

## What this unlocks

Running Codex inside Claude Code as a subagent opens up things that weren't possible before.

**Pick the right model for the job — automatically or explicitly.**  
Lightweight lookup? Codex mini. Feature implementation? Codex 5.4. Deep architecture review? Codex 5.5. The router handles this automatically, or you can call it explicitly.

**Cross-model review without leaving your session.**  
Claude writes the code. Codex reviews it adversarially — against *your* CLAUDE.md rules, not generic best practices. Claude responds. All in one session, no copy-pasting between tools.

**Multi-model discussion in a single session.**  
Pose a design question. Have Claude draft a proposal. Have Codex 5.5 push back. Have Claude respond. The whole conversation stays in one place, with full context on both sides.

This isn't just about running two models. It's about making them work *together*, in the same environment, with the same rules — without ever switching windows.

---

## How routing works in practice

When `/codex-on` is active, every prompt goes through two hooks before Claude responds:

1. `codex_mode_reminder.sh` — injects a routing hint into the context
2. `codex_tier_writer.py` — classifies the prompt as `medium` or `heavy` based on keywords

The main session (Sonnet) reads the hint and delegates to the right subagent. The `pre_tool_router_enforcer.py` hook backs this up — if Claude tries to edit files directly on a task that should go to Codex, it gets blocked and redirected.

In my own workload, ~90% of tasks route correctly on the first attempt (single-user, self-measured — your mileage will vary). Explicit overrides are available when needed.

**Example: `/codex-on` active**

| You type | Routes to | Because |
|---|---|---|
| "find all usages of X" | `ccp-gpt-5-4-mini` | lightweight lookup |
| "implement feature Y" | `ccp-gpt-5-4` | coding task, medium tier |
| "review this auth flow" | `ccp-codex-reviewer` | review keyword, heavy tier |
| "use Sonnet for this" | Sonnet directly | explicit override |
| "use Opus" | Opus | explicit escalation |

**Example: `/codex-off` active (or no command run)**

All tasks go directly to Claude. The hooks pass through, the tier file is not written, and the enforcer does nothing. Your harness functions exactly as it did before installing bridge-holic.

---

## Explicit overrides

The auto-router handles most cases. When you want to be specific:

```
"handle this in Claude" / "use Sonnet"
→ Sonnet handles directly

"use Opus" / "escalate"
→ Escalates to Opus

/codex-off  →  Claude handles everything directly
/codex-on   →  Resume Codex routing
```

---

## What's in the box

```
claudex-bridge-holic/
├── bin/
│   └── claude-codex                 # launcher: starts proxy + Claude with Codex backend
├── agents/
│   ├── ccp-gpt-5-4-mini.md          # lightweight: search, grep, lookups
│   ├── ccp-gpt-5-4.md               # standard: coding, bugfix, analysis
│   ├── ccp-gpt-5-5.md               # deep: review, design, security audit
│   ├── ccp-codex-reviewer.md        # adversarial: PR review against your rules
│   └── claude-opus.md               # Opus direct: bypasses CCP proxy via env -i
├── commands/
│   ├── codex-on.md                  # /codex-on  — force Codex routing
│   └── codex-off.md                 # /codex-off — back to Claude direct
├── hooks/
│   ├── codex_mode_reminder.sh       # UserPromptSubmit — routing hint injection
│   ├── codex_tier_writer.py         # UserPromptSubmit — classifies task tier (medium/heavy)
│   ├── auto_model_router.py         # UserPromptSubmit — classifies prompt, skips hints in subagent sessions
│   ├── pre_tool_router_enforcer.py  # PreToolUse — blocks direct writes based on tier
│   └── pre_agent_claude_redirect.py # PreToolUse — redirects claude-* agents to GPT equivalents
├── examples/
│   ├── CLAUDE.md                    # sample routing rules (replace with yours)
│   └── proxy-info.json              # proxy metadata: model names and setup notes
└── install.sh                       # one-liner installer
```

All agents block recursive delegation — no infinite loops.

---

## Prerequisites

1. **[Claude Code](https://claude.ai/code)** 1.0+ with subagent support
2. **Codex Pro** subscription (OpenAI)

That's it. `install.sh` walks you through the rest.

---

## Setup

```bash
git clone https://github.com/ryanholic/claudex-bridge-holic
cd claudex-bridge-holic
./install.sh
```

The installer will:
1. Check for **[raine/claude-code-proxy](https://github.com/raine/claude-code-proxy)** and show how to get it if missing
2. Install the `claude-codex` launcher to `~/.local/bin/`
3. Copy hooks, agents, and slash commands into `~/.claude/`
4. Run a self-test to confirm the proxy is working

Restart Claude Code after install. Test: ask Claude to search something — should route to `ccp-gpt-5-4-mini`.

---

## Router configuration

`claude-code-proxy` routes requests to the **ChatGPT Codex backend** (not the standard OpenAI API). Model availability depends on your ChatGPT account plan — if a model isn't supported, the proxy returns a 400 error. The model names below are what raine's proxy accepts:

| Model | Use case |
|---|---|
| `gpt-5.4-mini` | Fast lookups |
| `gpt-5.4` | Standard coding |
| `gpt-5.5` | Deep review (latest) |

> **Note:** Model availability varies by account plan. Check [raine/claude-code-proxy](https://github.com/raine/claude-code-proxy) for the current confirmed model list before changing these values.

See `examples/proxy-info.json` for proxy metadata and model names.

---

## Cost model

```
Claude subscription (e.g. Max 5X)
└─ Sonnet: router + communication — usage reduced, not zero

Codex subscription (e.g. Codex Pro 5X)
└─ All actual work — maximized
```

Sonnet sees every message as the router, so Claude usage doesn't drop to zero — but for typical workloads the shift to Codex is significant. High-frequency tasks (many short prompts) will still accumulate Claude routing overhead.

---

## Known issues

**`pre_tool_router_enforcer.py` tier blocking requires external setup**

The hook reads `/tmp/claude_tier_{session_id}.json` to decide whether to block direct writes. This file must be written by a separate hook or command that classifies task complexity as `"medium"` (blocks Edit/Write) or `"heavy"` (blocks Edit/Write/Bash). If no such writer exists in your setup, the tier-blocking logic is inactive and the hook passes through all tools unchanged — which is safe. The `/codex-off` bypass and the killswitch still work regardless.

---

**Hook deadlock in `/codex-off` mode**

The `pre_tool_router_enforcer.py` hook blocks direct writes and Bash commands when the session tier is elevated. In early versions, switching to `/codex-off` (native mode) didn't bypass this block — causing a situation where Claude couldn't edit files even after the user explicitly disabled Codex routing.

**This is fixed in the current version.** The hook now checks for `~/.claude/codex_native_on_{session_id}` and passes through immediately when native mode is active.

If you ever hit a similar deadlock, the emergency killswitch is:

```bash
touch ~/.claude/router_enforcer.off   # disables the hook entirely
# fix what you need to fix, then:
rm ~/.claude/router_enforcer.off      # re-enable
```

---

## Customizing

bridge-holic is intentionally opinionated — it reflects one person's workflow. Fork it and make it yours.

**Change routing keywords** (what triggers Codex vs. Claude):  
Edit the `HEAVY` and `MEDIUM` regex in `hooks/codex_tier_writer.py`. Comments at the top of the file explain each tier. Add terms in any language — the Korean entries already in there are a working example.

**Change which agents get called**:  
Edit `AGENT_MAP` in `hooks/pre_tool_router_enforcer.py` and the routing table in your `CLAUDE.md`. The agent `.md` files in `agents/` are the actual subagent definitions — rename or replace them to match.

**Change what each agent does**:  
Edit the `.md` files in `agents/`. They're plain markdown — model name, tools allowed, system prompt. The only constraints are: `--disallowedTools "Agent,TaskCreate"` to block recursion, and `CLAUDE_JOB_DIR` validation to block path traversal.

**Use a different proxy or backend**:  
The agents call `${BRIDGE_HOLIC_BIN:-$HOME/.local/bin/claude-codex}`. Point that env var at any launcher script that sets `ANTHROPIC_BASE_URL` and starts a local proxy. The rest of the harness is backend-agnostic.

**`claude` binary location** (`claude-opus` agent):
The `claude-opus` agent calls `${CLAUDE_BIN:-claude}`. If your `claude` binary isn't on PATH — common with `~/.local/bin/claude`, `~/.claude/local/claude`, or bun global installs — set `CLAUDE_BIN` in your shell profile:
```bash
export CLAUDE_BIN=~/.local/bin/claude
```

---

## Related

- [raine/claude-code-proxy](https://github.com/raine/claude-code-proxy) — the transport layer this builds on (`claude-code-proxy-headless`)
- [wshobson/agents](https://github.com/wshobson/agents) — multi-harness agent marketplace (different approach, same problem space)

---

*by [@ryanholic](https://github.com/ryanholic) — part of the -holic stack*

---

*Built while running **[SUMMERHOLIC](https://summerholic.kr)** — 𝘼𝙡𝙬𝙖𝙮𝙨 𝙎𝙪𝙢𝙢𝙚𝙧. Sports suncare & summer beauty brand obsessed with summer. If this saved you time, check us out → [summerholic.kr](https://summerholic.kr) · [Instagram](https://www.instagram.com/summerholic.kr/)*
