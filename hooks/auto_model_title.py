#!/usr/bin/env python3
"""UserPromptSubmit hook: 세션 제목 앞에 현재 모델명 prefix 자동 추가 (state.json 직접 패치)."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

HOME = Path.home()
JOBS_DIR = HOME / ".claude" / "jobs"
MAX_TITLE_LEN = 20

CLAUDE_DIR = HOME / ".claude"
MODE_EMOJIS = ("⚡ ", "✨ ")


def find_state_path(session_id: str) -> Path | None:
    quick = JOBS_DIR / session_id[:8] / "state.json"
    if quick.exists():
        try:
            state = json.loads(quick.read_text())
            if session_id in (state.get("sessionId", ""), state.get("resumeSessionId", "")):
                return quick
        except (json.JSONDecodeError, OSError):
            pass
    for p in JOBS_DIR.glob("*/state.json"):
        try:
            state = json.loads(p.read_text())
            if session_id in (state.get("sessionId", ""), state.get("resumeSessionId", "")):
                return p
        except (json.JSONDecodeError, OSError):
            continue
    return None


def is_codex_mode(session_id: str) -> bool:
    # /codex-off 명시적 OFF 신호 우선 확인 — pending 파일보다 강함
    if (CLAUDE_DIR / f"codex_native_on_{session_id}").exists():
        return False
    if (CLAUDE_DIR / f"codex_mode_on_{session_id}").exists():
        return True
    # claude-codex 런처 감지: 런처가 exec 직전에 codex_mode_pending_{PID} 파일을 생성함.
    # Claude Code가 훅 서브프로세스에 ANTHROPIC_BASE_URL 등 env를 sanitize하므로
    # env 체크 대신 pending 파일 감지 → codex_mode_on_{session_id} 파일로 변환(consume).
    pending_files = sorted(CLAUDE_DIR.glob("codex_mode_pending_*"), key=lambda p: p.stat().st_mtime)
    for pending in pending_files:
        try:
            pending.rename(CLAUDE_DIR / f"codex_mode_on_{session_id}")
            return True
        except OSError:
            # 다른 훅 인스턴스가 먼저 소비했으면 이미 codex_mode_on 파일 생성됨
            if (CLAUDE_DIR / f"codex_mode_on_{session_id}").exists():
                return True
    # env 체크 (직접 실행 환경 fallback — sanitize 전 컨텍스트용)
    base_url = os.environ.get("ANTHROPIC_BASE_URL", "")
    if base_url and ("localhost" in base_url or "127.0.0.1" in base_url):
        return True
    model = os.environ.get("ANTHROPIC_MODEL", "")
    if model and model.startswith("gpt-"):
        return True
    return False


def shorten_title(text: str, limit: int = MAX_TITLE_LEN) -> str:
    text = re.sub(r"\s+", " ", (text or "").strip())
    if not text:
        return ""

    text = re.split(r"[\n\r:;|!?]+|\s[-—]\s", text, maxsplit=1)[0].strip()
    text = text.strip("'\"`[](){}")

    normalized = text.lower()
    keyword_rules = [
        (("세션", "제목", "짧"), "세션 제목 짧게"),
        (("세션", "제목", "간결"), "세션 제목 간결화"),
        (("세션", "제목"), "세션 제목"),
        (("remote", "control"), "리모트컨트롤"),
        (("bypass", "permission"), "bypass 기본값"),
        (("권한", "기본값"), "권한 기본값"),
        (("모델", "제목"), "모델 제목 suffix"),
        (("suffix",), "모델 제목 suffix"),
    ]
    for keywords, label in keyword_rules:
        if all(keyword in normalized for keyword in keywords):
            return label

    prefixes = (
        "클로드-코덱스 모드에서 ",
        "claude-codex에서 ",
        "claude-codex ",
        "일반 claude 세션 ",
        "일반 claude ",
        "세션 제목이 ",
        "세션 제목 ",
        "제목이 ",
        "제목 ",
    )
    changed = True
    while changed and text:
        changed = False
        for prefix in prefixes:
            if text.startswith(prefix):
                text = text[len(prefix):].strip()
                changed = True

    for suffix in (
        "해주세요",
        "해 주세요",
        "해줘",
        "해 줘",
        "봐줘",
        "봐 줘",
        "고쳐줘",
        "바꿔줘",
        "수정해줘",
        "설정해줘",
        "요약해줘",
        "정리해줘",
        "알려줘",
        "확인해줘",
    ):
        if text.endswith(suffix):
            text = text[: -len(suffix)].rstrip(" .,!?:;")
            break

    particles = ("은", "는", "이", "가", "을", "를", "도", "만")
    tokens = text.split()
    compact = []
    for token in tokens[:4]:
        if len(token) > 1 and token[-1] in particles:
            token = token[:-1]
        compact.append(token)
    text = " ".join(compact).strip()

    if len(text) > limit:
        text = text[: limit - 1].rstrip() + "…"

    return text or "Untitled session"



def _spawn_summarizer(state_path: Path, raw_title: str, emoji: str) -> None:
    """fire-and-forget: LLM으로 요약 제목 생성 후 state.json 패치."""
    codex_bin = HOME / ".local" / "bin" / "claude-codex"
    if not codex_bin.exists():
        return
    if not raw_title or raw_title.startswith("/") or len(raw_title) < 4:
        return

    prompt = (
        f"다음을 한국어 4단어 이내 명사구 제목으로만 답해. "
        f"이모지·조사·마침표 금지. 결과만 출력: {raw_title[:200]}"
    )
    sp = str(state_path)
    patcher = (
        "import subprocess, json, sys\n"
        "from pathlib import Path\n"
        f"sp = Path({sp!r})\n"
        f"emoji = {emoji!r}\n"
        f"codex = {str(codex_bin)!r}\n"
        f"prompt = {prompt!r}\n"
        "try:\n"
        "    r = subprocess.run(\n"
        "        [codex, '--no-session-persistence', '-p', prompt],\n"
        "        capture_output=True, text=True, timeout=60\n"
        "    )\n"
        "    title = (r.stdout or '').strip().splitlines()[0].strip()\n"
        "    if not title or len(title) > 30: sys.exit(0)\n"
        "except Exception: sys.exit(0)\n"
        "try:\n"
        "    s = json.loads(sp.read_text())\n"
        "    if s.get('nameSource') == 'user': sys.exit(0)\n"
        "    curr = (s.get('name') or '').strip()\n"
        "    active_emoji = '⚡' if curr.startswith('⚡ ') else ('✨' if curr.startswith('✨ ') else emoji)\n"
        "    s['name'] = active_emoji + ' ' + title\n"
        "    sp.write_text(json.dumps(s, ensure_ascii=False))\n"
        "except Exception: pass\n"
    )
    subprocess.Popen(
        [sys.executable, "-c", patcher],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def pick_base_name(state: dict, respawn_flags: list[str]) -> str:
    current_name = (state.get("name") or "").strip()
    if current_name:
        return current_name

    for i, flag in enumerate(respawn_flags):
        if flag in ("-n", "--name") and i + 1 < len(respawn_flags):
            candidate = (respawn_flags[i + 1] or "").strip()
            if candidate:
                return shorten_title(candidate)
        if flag in ("-p", "--print") and i + 1 < len(respawn_flags):
            candidate = (respawn_flags[i + 1] or "").strip().splitlines()[0].strip()
            if candidate:
                return shorten_title(candidate)

    intent = (state.get("intent") or "").strip()
    if intent:
        return shorten_title(intent.splitlines()[0].strip())

    return "Untitled session"



def main():
    raw_ctx = os.environ.get("CLAUDE_HOOK_CONTEXT", "")
    if not raw_ctx:
        raw_ctx = sys.stdin.read()

    session_id = os.environ.get("CLAUDE_CODE_SESSION_ID", "")
    if not session_id:
        try:
            session_id = json.loads(raw_ctx).get("session_id", "")
        except (json.JSONDecodeError, AttributeError):
            pass

    if not session_id:
        sys.exit(0)

    state_path = find_state_path(session_id)
    if not state_path:
        sys.exit(0)

    try:
        state = json.loads(state_path.read_text())
    except (json.JSONDecodeError, OSError):
        sys.exit(0)

    current_name = (state.get("name") or "").strip()
    name_source = state.get("nameSource")

    if name_source == "user":
        sys.exit(0)

    emoji = "⚡" if is_codex_mode(session_id) else "✨"
    if current_name.startswith(f"{emoji} "):
        sys.exit(0)

    was_first = not state.get("nameSource")
    raw_intent = (state.get("intent") or "").strip().splitlines()[0].strip()

    respawn_flags = state.get("respawnFlags", [])
    base_name = pick_base_name(state, respawn_flags)
    for pfx in MODE_EMOJIS:
        if base_name.startswith(pfx):
            base_name = base_name[len(pfx):]
            break
    base_name = re.sub(r"^\[[^\]]+\]\s*", "", base_name)

    state["name"] = f"{emoji} {base_name}"
    state["nameSource"] = "auto"
    try:
        state_path.write_text(json.dumps(state, ensure_ascii=False))
    except OSError:
        sys.exit(0)

    if was_first and raw_intent:
        _spawn_summarizer(state_path, raw_intent, emoji)


if __name__ == "__main__":
    main()
