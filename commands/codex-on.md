먼저 아래 Bash 명령을 실행해 Codex 모드 상태를 저장하고 세션 제목을 즉시 업데이트하라:

```bash
: "${CLAUDE_CODE_SESSION_ID:?CLAUDE_CODE_SESSION_ID not set}" && mkdir -p ~/.claude && touch ~/.claude/codex_mode_on_${CLAUDE_CODE_SESSION_ID} && rm -f ~/.claude/codex_native_on_${CLAUDE_CODE_SESSION_ID} && echo "Codex 모드 파일 생성 완료: codex_mode_on_${CLAUDE_CODE_SESSION_ID}"
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
state["name"] = "⚡ " + name
state_path.write_text(json.dumps(state, ensure_ascii=False))
print(f"세션 제목 → {state['name']}")
PYEOF
```

이 세션에서 **Codex 강제 위임 모드**를 활성화한다.

## 의무 위임 (직접 처리 금지)

| 작업 유형 | 위임 대상 |
|---|---|
| 웹 리서치 / 라이브러리 조사 / 외부 정보 / 최신 동향 | **codex-research** |
| 500줄 이상 파일 읽기 / 낯선 디렉토리 탐색 | **codex-reader** |
| 30줄 이상 코드 신규 작성 / 기능 구현 / 스크립트 생성 | **codex-coder** |
| 코드 리뷰 / 적대적 검토 | **codex-reviewer** |

## 금지

- training knowledge로 외부 시스템·라이브러리 현황 직접 답변
- 500줄 이상 파일 직접 Read
- 30줄 이상 코드 직접 작성

## 규칙

- 에이전트 반환 `▸ {name} · {model}` 헤더를 답변에 그대로 유지한다.
- 위임 결과가 불충분하면 재위임하거나 보완한다. 직접 처리로 대체하지 않는다.
- `/codex-off` 로 해제할 수 있다.

**Codex 모드 ON. 이후 해당 작업은 모두 Codex 서브에이전트로 위임한다.**
