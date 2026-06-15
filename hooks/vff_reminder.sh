#!/bin/bash
# VFF 드리프트 방지 훅 (UserPromptSubmit) — itsinseong/value-for-fable 포팅
# transcript 400KB 초과 + VFF 활성 상태일 때만 리마인더 주입, 그 외 침묵(비용 0).

THRESHOLD=400000

input=$(cat)
tp=$(printf '%s' "$input" | sed -n 's/.*"transcript_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
[ -z "$tp" ] && exit 0
[ -f "$tp" ] || exit 0

size=$(wc -c < "$tp" 2>/dev/null | tr -d ' ')
[ "${size:-0}" -lt "$THRESHOLD" ] && exit 0

style_on=0
cwd=$(printf '%s' "$input" | sed -n 's/.*"cwd"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
for f in "$HOME/.claude/settings.json" "$cwd/.claude/settings.local.json" "$cwd/.claude/settings.json"; do
  [ -f "$f" ] && grep -qsiE '"outputStyle"[[:space:]]*:[[:space:]]*"(value-for-fable:)?vff"' "$f" && style_on=1 && break
done

if [ "$style_on" -eq 0 ]; then
  on=$(grep -nF -e 'VFF 적용' -e 'VFF 적용' "$tp" 2>/dev/null | tail -1 | cut -d: -f1)
  [ -z "$on" ] && exit 0
  off=$(grep -nF -e 'VFF 해제됨' -e 'VFF 해제됨' "$tp" 2>/dev/null | tail -1 | cut -d: -f1)
  if [ -n "$off" ] && [ "$off" -gt "$on" ]; then exit 0; fi
fi

printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"<vff-reminder>VFF 유지: 첫 문장=결론, 산문 우선(토막문장·화살표 체인 금지), 완료 주장 전 검증, 단서 우선 진단, 직접 본 것만 단정.</vff-reminder>"}}'
exit 0
