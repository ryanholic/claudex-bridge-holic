#!/usr/bin/env python3
"""
UserPromptSubmit hook: classifies task tier and writes /tmp/claude_tier_{session_id}.json.
Only active in /codex-on mode. Pairs with pre_tool_router_enforcer.py.
"""
import json, os, re, sys

# ─── Fork customization ────────────────────────────────────────────────────────
# Edit HEAVY and MEDIUM patterns below to match your language and workflow.
# HEAVY  → routes to ccp-gpt-5-5  (deep review / audit tasks)
# MEDIUM → routes to ccp-gpt-5-4  (coding / editing tasks)
# Add terms in any language. Korean examples are included as reference.
# ──────────────────────────────────────────────────────────────────────────────

HEAVY = re.compile(
    r'(review|audit|security|adversarial|critique|architecture|design review|code review'
    r'|리뷰|감사|코드\s*리뷰|설계\s*검토|보안\s*검토|아키텍처|검토)',
    re.IGNORECASE,
)
MEDIUM = re.compile(
    r'(edit|write|implement|create|build|fix|update|add|generate|refactor|migrate|modify'
    r'|수정|작성|구현|만들어|추가|생성|리팩토링|버그\s*수정|고쳐)',
    re.IGNORECASE,
)


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    session_id = payload.get("session_id", "")
    if not session_id:
        sys.exit(0)

    tier_file = f"/tmp/claude_tier_{session_id}.json"
    codex_on = os.path.expanduser(f"~/.claude/codex_mode_on_{session_id}")

    # Only enforce when /codex-on is active
    if not os.path.exists(codex_on):
        try:
            os.remove(tier_file)
        except FileNotFoundError:
            pass
        sys.exit(0)

    prompt = payload.get("prompt", "")
    if HEAVY.search(prompt):
        tier = "heavy"
    elif MEDIUM.search(prompt):
        tier = "medium"
    else:
        try:
            os.remove(tier_file)
        except FileNotFoundError:
            pass
        sys.exit(0)

    try:
        with open(tier_file, "w") as f:
            json.dump({"tier": tier}, f)
    except OSError:
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
