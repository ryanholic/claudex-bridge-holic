먼저 아래 Bash 명령을 실행해 Codex 모드 상태 파일을 삭제하고 네이티브 모드 플래그를 생성하고 세션 제목을 즉시 업데이트하라:

```bash
: "${CLAUDE_CODE_SESSION_ID:?CLAUDE_CODE_SESSION_ID not set}" && rm -f ~/.claude/codex_mode_on_${CLAUDE_CODE_SESSION_ID} && touch ~/.claude/codex_native_on_${CLAUDE_CODE_SESSION_ID} && echo "Codex 모드 파일 삭제 완료 + Native 모드 활성화"
```

```bash
python3 - <<"PYEOF"
import json, os
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
for pfx in ("⚡ ", "✨ "):
    if name.startswith(pfx): name = name[len(pfx):]; break
import re; name = re.sub(r"^\[[^\]]+\]\s*", "", name)
state["name"] = "✨ " + name
state_path.write_text(json.dumps(state, ensure_ascii=False))
print(f"세션 제목 → {state['name']}")
PYEOF
```

**Codex 강제 위임 모드를 해제한다.**

이제부터 이 세션에서는 CCP 서브에이전트 없이 Claude가 직접 처리한다.
라우터 힌트도 "Codex 오프 — Claude 직접 처리"로 교체된다.

복구: `/codex-on`

**Codex 모드 OFF.**
