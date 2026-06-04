먼저 아래 Bash 명령을 실행해 Codex 모드 상태를 저장하고 세션 제목을 즉시 업데이트하라:

```bash
: "${CLAUDE_CODE_SESSION_ID:?CLAUDE_CODE_SESSION_ID not set}" && mkdir -p ~/.claude && touch ~/.claude/codex_mode_on_${CLAUDE_CODE_SESSION_ID} && rm -f ~/.claude/codex_native_on_${CLAUDE_CODE_SESSION_ID} && echo "Codex 모드 파일 생성 완료: codex_mode_on_${CLAUDE_CODE_SESSION_ID}"
```

```bash
python3 - <<"PYEOF"
import json, os, re
from pathlib import Path
sid = os.environ.get("CLAUDE_CODE_SESSION_ID", "")
if not sid: raise SystemExit(0)
jobs = Path.home() / ".claude" / "jobs"
state_path = None
for p in [jobs / sid[:8] / "state.json"] + list(jobs.glob("*/state.json")):
    try:
        s = json.loads(p.read_text())
        if sid in (s.get("sessionId",""), s.get("resumeSessionId","")):
            state_path = p; break
    except: pass
if not state_path: raise SystemExit(0)
state = json.loads(state_path.read_text())
if state.get("nameSource") == "user": raise SystemExit(0)
name = (state.get("name") or "").strip()
for pfx in ("🤖 ", "🧠 ", "⚡ ", "🔆 ", "✨ "):
    if name.startswith(pfx): name = name[len(pfx):]; break
name = re.sub(r"^\[[^\]]+\]\s*", "", name)
flags = json.dumps(state.get("respawnFlags", []))
is_codex_launcher = "ANTHROPIC_BASE_URL" in flags or "gpt-5" in flags
new_emoji = "🔆" if is_codex_launcher else "🤖"
state["name"] = new_emoji + " " + name
state_path.write_text(json.dumps(state, ensure_ascii=False))
print(f"세션 제목 → {state['name']}")
PYEOF
```

이 세션에서 **Codex MCP 강제 위임 모드**를 활성화한다. 새 native 세션도 SessionStart hook으로 자동 ON 상태가 된다.

## 의무 위임 (직접 처리 금지)

| 작업 유형 | 위임 대상 |
|---|---|
| 파일 탐색 / grep / 조회 / 단순 질문 | `mcp__codex__codex(model="gpt-5.4-mini", sandbox="read-only")` |
| 코딩 / 구현 / 버그 수정 / 분석 | `mcp__codex__codex(model="gpt-5.4", sandbox="workspace-write")` |
| 코드 리뷰 / 설계 검토 / 보안 감사 | `mcp__codex__codex(model="gpt-5.5", sandbox="read-only")` |

## 금지

- 직접 Read/Bash/Edit/Write로 실작업 처리
- Agent/ccp-gpt fallback
- MCP 실패 후 직접 처리

## 규칙

- 모든 호출은 `approval-policy="never"`, `cwd="<대상 repo 절대경로>"`를 지정한다.
- codex가 산출물을 만들면 Claude는 mtime·git diff·필요 최소 Read로 검증만 한다.
- MCP 실패 시 실패 원인과 재시도 조건만 보고한다. 직접 처리로 대체하지 않는다.
- `/codex-off` 로 해제할 수 있다.

**Codex MCP 모드 ON. 이후 실작업은 모두 `mcp__codex__codex`로 위임한다.**
