# My CLAUDE.md — Example (English)

> This is a sample CLAUDE.md demonstrating rules that bridge-holic's Codex workers will inherit.
> Replace with your own rules. Your CLAUDE.md can be in any language.

---

## Simplicity First

Write the minimum code that solves the problem. No speculative implementations.

- Do not add features beyond what was requested
- No abstractions for single-use code
- No error handling for impossible scenarios
- If you wrote 200 lines and 50 would do, rewrite it

Ask yourself: "Would a senior engineer call this over-engineered?" → If yes, simplify.

## Surgical Changes

Only touch what you must. Don't clean up what you didn't break.

- No "improvements" to adjacent code, comments, or formatting
- No refactoring of code that isn't broken
- Match existing style even if you'd do it differently
- If you spot unrelated dead code, mention it — don't delete it

Check: can every changed line be traced directly back to the user's request?

## Commit Messages

Write commit messages in [your preferred language or format].

## No Comments

Default to writing no comments. Only add one when the WHY is non-obvious.

---

*These rules will be applied to both the Claude Code router session AND any Codex subagents spawned via bridge-holic.*
