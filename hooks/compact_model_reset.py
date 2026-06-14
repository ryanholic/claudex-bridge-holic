#!/usr/bin/env python3
"""PreCompact hook: session model override를 임시 제거.

compact 요청이 session override된 모델(gpt-5.5 등)로 가면
context window 초과로 compact 자체가 실패한다.
compact 직전에 override를 없애면 기본 haiku(→gpt-5.4-mini)로 실행됨.
PostCompact 훅(compact_model_restore.py)이 복원한다.
"""

import json
import os
import sys
from pathlib import Path


def main() -> None:
    raw = os.environ.get("CLAUDE_HOOK_CONTEXT", "") or sys.stdin.read()
    try:
        ctx = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    session_id = ctx.get("session_id", "")
    if not session_id:
        sys.exit(0)

    models_dir = Path.home() / ".local/state/claude-code-proxy/session-models"
    model_file = models_dir / f"{session_id}.model"

    if not model_file.exists():
        sys.exit(0)

    current_model = model_file.read_text().strip()
    # 복원용 백업
    backup_file = models_dir / f"{session_id}.model.pre-compact"
    backup_file.write_text(current_model)
    # override 제거 → compact는 기본 모델(haiku → gpt-5.4-mini)로 실행
    model_file.unlink()

    print(
        f"compact_model_reset: paused session model '{current_model}' for compact session={session_id[:8]}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
