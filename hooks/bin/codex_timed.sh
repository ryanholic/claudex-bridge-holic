#!/usr/bin/env bash
# γ #3 — claude-codex 워커 호출에 wall-clock 타임아웃 강제 (행업 조기중단).
# macOS에 coreutils `timeout`/`gtimeout`이 없어 순정 bash watchdog로 구현.
#
# 사용법: codex_timed.sh <seconds> <command> [args...]
#   stdin은 그대로 자식에게 전달됨 (wrapper의 `-p < PROMPT_FILE` 패턴 지원).
#   초과 시 자식에 TERM→(5s)→KILL. exit 124 반환.
#
# 한계: 자식(claude-codex)의 손자 프로세스(codex/node)는 TERM 전파에 의존.
#       claude-codex가 자체 trap으로 자식을 정리하나 100% 보장은 아님.
#       목적은 부모(Claude)가 92분 행업에서 풀리는 것 — 잔존 백그라운드는
#       92분 포어그라운드 행업보다 훨씬 경미. 추후 B(codex-mcp)에서 근본 해소.

set -u

secs="${1:?usage: codex_timed.sh <seconds> <command...>}"
shift || true
[ "$#" -ge 1 ] || { echo "[γ-timeout] 실행할 명령 없음" >&2; exit 2; }

# 비대화형 bash는 백그라운드 잡의 stdin을 /dev/null로 돌림 → 원본 stdin을 fd3로
# 보존해 자식에 명시 전달 (claude-codex `-p < PROMPT_FILE` 프롬프트 유실 방지).
exec 3<&0
"$@" <&3 &
cmd_pid=$!
exec 3<&-

(
  sleep "$secs"
  kill -TERM "$cmd_pid" 2>/dev/null || exit 0
  # 자식의 직계 손자도 함께 정리 시도 (best-effort)
  pkill -TERM -P "$cmd_pid" 2>/dev/null || true
  sleep 5
  kill -KILL "$cmd_pid" 2>/dev/null || true
  pkill -KILL -P "$cmd_pid" 2>/dev/null || true
) &
watch_pid=$!

wait "$cmd_pid"
rc=$?

# watchdog 종료 (정상 완료 시)
kill "$watch_pid" 2>/dev/null || true
wait "$watch_pid" 2>/dev/null || true

# TERM(143)/KILL(137)로 죽었으면 타임아웃으로 간주
if [ "$rc" -eq 143 ] || [ "$rc" -eq 137 ]; then
  echo "[γ-timeout] 워커가 ${secs}s 초과 — 강제종료됨 (산출물 미완성 가능). 부모는 결과를 '미완료'로 처리하고 재위임 여부 판단하라." >&2
  exit 124
fi

exit "$rc"
