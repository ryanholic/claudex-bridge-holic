#!/usr/bin/env python3
"""PostCompact hook: compact 전 session model override를 복원.

PreCompact 훅(compact_model_reset.py)이 .pre-compact 백업을 만들었으면
compact 완료 후 원래 model override로 복원한다.
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
    backup_file = models_dir / f"{session_id}.model.pre-compact"
    model_file = models_dir / f"{session_id}.model"

    if not backup_file.exists():
        sys.exit(0)

    original_model = backup_file.read_text().strip()
    backup_file.unlink()

    if not model_file.exists():
        model_file.write_text(original_model)
        print(
            f"compact_model_restore: restored session model '{original_model}' session={session_id[:8]}",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
