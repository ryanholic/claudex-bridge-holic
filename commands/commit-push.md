---
description: 현재 레포를 안전하게 커밋·푸시한다 (브랜치 가드 + 자동 커밋메시지 + co-author 푸터 + 배포레포 경고). codex 모드에서도 git을 직접 실행한다.
argument-hint: [커밋 메시지] — 생략 시 diff 보고 자동 생성
---

# Commit & Push

codex-on 세션이어도 git 워크플로는 enforcer가 허용한다(`pre_tool_router_enforcer.py`).
**git을 codex worker에 위임하지 말 것** — codex worker는 `.git` 쓰기가 막혀(index.lock) 실패한다.
아래를 **본 세션에서 직접 Bash로** 실행한다.

## 1단계 — 상태 파악

```bash
git rev-parse --show-toplevel 2>/dev/null || echo "NOT_A_REPO"
git branch --show-current
git status --short
git diff --stat
```

- git repo 아니면 중단.
- staged/unstaged 변경 0이면 "커밋할 변경 없음" 보고 후 중단.

## 2단계 — 브랜치·레포 가드

레포 매핑 (toplevel 경로 기준):
- `summerholic-backoffice` / `summerholic-funnel` / `summerholic-partners` → **Vercel prod 레포**
- `summerholic-cafe24` → **cafe24 (GitHub Actions SFTP)**
- `CODEX` / `autoholic-runtime` → 배포 후 3머신 pull 필요
- `ryan-private` / `appendix` / 기타 → 일반 (제약 없음)

**가드:**
- 현재 브랜치가 `main`이 **아니면**: 그대로 진행하되 push는 `origin <현재브랜치>`로. (워크트리/분기 작업)
- 현재 브랜치가 `main`이고 **Vercel prod 레포**면 ⚠️ **중단하고 경고**:
  > ⚠️ main push = **PROD 자동배포 트리거**. 의도한 배포면 `/deploy` 사용 권장. 그래도 진행할까요?
  → Ryan 확인 받기 전 push 금지.
- `summerholic-cafe24` + main이면 ⚠️ **휴먼게이트 안내**:
  > cafe24 SFTP 접속 허용 기간(최대 7일) 남았는지 먼저 확인. 만료면 갱신 후 진행. `skin1/`·`skin5/` 변경 없으면 Actions 미트리거.
  → 확인 후 진행.
- `vercel --prod` 등 수동 배포 명령 **절대 금지** (전역 규칙).

## 3단계 — 스테이지 + 커밋

```bash
git add -A
```
(사용자가 특정 파일만 지정했으면 그것만 add.)

**커밋 메시지:**
- 인자(`$ARGUMENTS`)가 있으면 그것을 제목으로 사용.
- 없으면 diff를 보고 Conventional Commits로 **자동 생성**: `type(scope): 요약` (제목 ≤50자, 한국어 가능). "왜"가 자명하지 않을 때만 본문 추가.
- **반드시 co-author 푸터로 끝낼 것** (전역 규칙):

```
<제목>

<선택: 본문>

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
```

```bash
git commit -m "$(cat <<'EOF'
<위 메시지>
EOF
)"
```

## 4단계 — 푸시

```bash
git push origin <현재브랜치>
git log --oneline -1
```

push 실패 시 원인(인증·충돌·non-fast-forward) 그대로 보고. 자동 force 금지.

## 5단계 — 후속 (해당 레포만)

- **CODEX**: push 후 3머신 pull 안내
  ```bash
  git -C /Users/ryan_mini/CODEX pull
  ssh air 'git -C /Users/ryankwon/CODEX pull'
  ssh nuc 'git -C /home/ryankwon/CODEX pull'
  ```
- **autoholic-runtime**: push 후 재기동 + 3머신 pull (`/deploy` 참고).
- 그 외: 후속 없음.

## 완료 보고

`<레포> <브랜치> <커밋해시> — push 완료` 한 줄. 헤매지 말고 위 순서대로 직진.
