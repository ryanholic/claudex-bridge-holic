# Shared Core Rules — Ryan Kwon (Summerholic)

메인 Claude와 codex 워커 모두에 적용되는 공통 규칙.
이 파일을 직접 수정하면 양쪽 모두에 반영된다.

---

## 행동 원칙 (Karpathy Framework)

> LLM 코딩 실수 방지 4원칙. 모든 프로젝트에 적용.

### 1. Think Before Coding — 코딩 전 먼저 생각

**추정 금지. 혼란 숨기기 금지. 트레이드오프 노출.**

구현 전:
- 전제를 명시적으로 서술. 불확실하면 질문.
- 복수의 해석이 존재하면 모두 제시 — 조용히 선택 금지.
- 더 단순한 방법이 있으면 말할 것. 밀어붙여야 할 때는 밀어붙여라.
- 불분명하면 멈춰라. 무엇이 헷갈리는지 이름을 붙이고 질문.

**블로커 발생 시 즉시 완전 정지** — 추정으로 진행 절대 금지.
보고 형식 (4가지 필수): (1) 무엇이 막혔나 (2) 왜 지금 결정 필요한가 (3) 지금 안 정하면 어떻게 되나 (4) 선택지 2~3개 + 추천안.

**기존 코드 분석은 직접 Read 기반** — 서브에이전트 요약만으로 결론 금지.
- 원본 파일 전문 직접 Read한 라인이 결론의 근거.
- `import` 체인 전부 추적. 형제 파일(같은 디렉토리·같은 목적)도 한 번씩 훑는다.
- **"이 로직은 없을 것이다" 단정 금지.** `grep`·`Read`로 부재 실증 후에만 주장.
- **Ryan이 "기존에 구현돼 있다"고 하면 즉각 원본 탐색 재개.** 내 결론보다 실무 기억 우선. 반박하려면 파일경로:라인번호 인용 필수.
- 설계 오류 결론은 최후 수단. 이식 누락·단순 버그·설정 실수 먼저 의심.

### 2. Simplicity First — 단순함 우선

**문제를 해결하는 최소한의 코드. 추측 기반 구현 금지.**

- 요청된 것 이외의 기능 추가 금지.
- 단일 사용 코드에 추상화 금지.
- 요청하지 않은 "유연성"이나 "설정 가능성" 추가 금지.
- 불가능한 시나리오에 대한 에러 핸들링 금지.
- 200줄로 작성했는데 50줄이 가능하다면, 다시 작성하라.

스스로 질문: "시니어 엔지니어가 이게 과잉설계라고 할까?" → 그렇다면 단순화.

### 3. Surgical Changes — 외과적 수정

**반드시 바꿔야 하는 것만 건드려라. 내가 만든 쓰레기만 치워라.**

기존 코드 수정 시:
- 인접한 코드·주석·포매팅 "개선" 금지.
- 망가지지 않은 것 리팩토링 금지.
- 내가 다르게 할 것 같아도 기존 스타일 맞춰라.
- 무관한 dead code를 발견하면 언급만 — 삭제 금지.

내 변경이 orphan을 만들었을 때:
- 내 변경으로 생긴 사용되지 않는 import·변수·함수만 제거.
- 기존에 있던 dead code는 요청 없이 삭제 금지.

체크: 변경된 모든 줄이 유저의 요청으로 직접 추적 가능한가?

### 4. Goal-Driven Execution — 성공 기준 선 정의

**성공 기준을 정의하라. 검증될 때까지 루프.**

작업을 검증 가능한 목표로 전환:
- "버그 수정" → "해당 케이스를 먼저 재현하고, 해소되면 완료"
- "파이프라인 수정" → "A 테이블에 B 조건의 데이터가 들어가면 완료"
- "마이그레이션" → "적용 전·후 SELECT 결과가 일치하면 완료"

다단계 작업은 시작 전 브리핑:
1. [단계] → 검증: [체크]
2. [단계] → 검증: [체크]

강한 성공 기준은 자율 루프를 가능케 한다. "되게 해"는 기준이 아니다.

---

## 🚨 배포 규칙 (전역 — 위반 시 프로덕션 장애)
- **배포 경로: `git push origin main` 만 사용.** Vercel GitHub 연동이 자동으로 prod 배포를 트리거함.
- **`vercel --prod` / `vercel deploy --prod` CLI 수동 실행 금지.** GitHub 연동과 이중 배포 발생. 2026-05-30 이중 배포 사고로 확정됨.
- 워크트리(`.claude/worktrees/**`, `ai-pm/**` 등 모든 분기 작업 디렉토리)에서 push 금지. main에 머지 후 main 루트에서 push.
- push 전 `git branch --show-current` 로 현재 브랜치가 `main` 인지 반드시 확인. `main` 이 아니면 **즉시 중단**.

---

## 🚨 시간대 규칙 — 날짜 계산은 반드시 KST (위반 금지)

**날짜 문자열(YYYY-MM-DD) 생성과 날짜 경계 계산은 예외 없이 KST(UTC+9) 기준.**

> 단, `created_at` / `updated_at` / `sent_at` 등 순간(instant)을 저장하는 `timestamptz` 컬럼은 UTC ISO string 그대로 저장 — PostgreSQL이 내부적으로 UTC로 관리하며 이건 정상 동작.

### 절대 금지 — 날짜 문자열 추출 또는 날짜 경계 계산 시
- `new Date().toISOString().slice(0, 10)` — UTC 날짜 반환, KST와 최대 1일 어긋남. **절대 사용 금지.**
- `datetime.utcnow()` — deprecated + UTC 기준. **금지.** (Python 3.12+에서 경고)
- `datetime.now()` (timezone 없이) — 로컬 timezone 의존, 환경마다 다름. **금지.**
- `date.today()` (timezone 없이) — 동일. **금지.**
- UTC offset 없이 날짜 경계(하루 시작/끝) 계산 — **금지.**

### 올바른 패턴

**JavaScript / TypeScript:**
```ts
// KST 오늘 날짜 (YYYY-MM-DD)
function todayKst(): string {
  return new Date(Date.now() + 9 * 3600 * 1000).toISOString().slice(0, 10);
}

// KST N일 전 날짜
function daysAgoKst(days: number): string {
  const d = new Date(Date.now() + 9 * 3600 * 1000);
  d.setUTCDate(d.getUTCDate() - days);
  return d.toISOString().slice(0, 10);
}

// timestamptz 저장용 순간값 — UTC 그대로 OK
const now = new Date().toISOString(); // updated_at, created_at 등에 사용
```

**Python:**
```python
from zoneinfo import ZoneInfo
from datetime import datetime, date

KST = ZoneInfo("Asia/Seoul")

def today_kst() -> date:
    return datetime.now(KST).date()

def now_kst() -> datetime:
    return datetime.now(KST)
```

### Supabase / SQL
- `timestamptz` 컬럼: UTC 저장 정상. 꺼낼 때 표시용으로 KST 변환.
- **집계·필터·날짜 경계 계산은 반드시 KST 기준 경계값으로 파라미터 전달.**
- SQL에서 날짜 경계: `AT TIME ZONE 'Asia/Seoul'` 또는 Python/TS에서 KST 기준 경계값 계산 후 파라미터로 전달.

### 검토 체크리스트
날짜 관련 코드를 작성·수정할 때 확인 (타임스탬프 저장은 해당 없음):
1. `YYYY-MM-DD` 날짜 문자열 생성 시 → UTC 기준 아닌 KST 기준인가?
2. "오늘", "N일 전", "이번 달" 경계 계산 시 → KST 자정 기준인가?
3. Supabase 쿼리에서 날짜 범위 필터(gte/lte) → KST 기준 경계값인가?

---

## 데이터 환각 금지
- 매출·비용 등 경영 수치는 출처(Supabase 테이블·쿼리 조건)를 명시. 확인 안 된 데이터는 "추정" 표시.
- 모르면 모른다고 답변한다.

---

## Apps Script / Google Sheets 전면 폐기
- `biz_automation/apps_script/` 디렉토리는 `archive/apps_script_deprecated/`로 이관됨. **참조·수정·탐색·제안 금지.**
- Google Sheets(V1/V2 스프레드시트 전부)는 읽기·쓰기 전용 대상 아님.
- 데이터는 Supabase SSOT. 시트 싱크·수식·clasp push 같은 제안이 나오려 하면 **중단하고 Supabase 경로로 전환**.
- 유일 예외: 이미 돌고 있는 `scripts/sync_summer_dashboard_sources.py` (Supabase → 대시보드 src_* 시트 읽기 전용 복제).

---

## 세션 실행 환경 자각
머신 식별은 수집기·백필·외부 서비스 쓰기 작업 요청이 들어왔을 때만 수행한다. 매 세션 시작 시 머신이나 제약을 선제 선언하지 않는다.

머신 식별이 필요한 경우 `pwd` + `hostname` 실측값으로 확인하고, 경로명 단독으로 단정하지 않는다.

  | 경로 | 머신 | Tailscale IP | 역할 |
  |---|---|---|---|
  | `/Users/ryan_mini/CODEX` | 맥미니 M2 (ryan_mini) | `100.92.4.113` | AI 봇(슬랙·오토홀릭·지피홀릭) 실행 환경. Tailscale hostname: `mini` |
  | `/Users/ryankwon/CODEX` | 맥북에어 M1 (ryankwon) | `100.98.180.9` | 주 개발 머신. Chrome MCP 등 UI 자동화. SSH: `ssh air` |
  | `/home/ryankwon/CODEX` | NUC (ryankwon) | `100.86.44.81` | 데이터 수집 크론잡 전용 (모든 수집기·백필·reconcile). SSH: `ssh nuc` |

- 커밋·push 후 나머지 2개 머신 `git pull` 필수.
- 수집기·백필·외부 서비스 쓰기 실행은 **무조건 NUC**. 맥미니/맥북에어에서는 실행하지 않는다. 이 제약은 수집기·백필 요청이 들어왔을 때만 언급하고 NUC 실행으로 안내한다.
- 단순 조회, 로컬 파일 분석, Supabase read-only는 수집기 실행 금지 대상이 아니다. 쓰기 가능성이 있으면 실행 전 확인한다.
- **접속은 무조건 Tailscale IP 또는 hostname** — 로컬 IP(192.168.x.x)·ZeroTier IP 사용 금지.

---

## SSOT 위계: Ryan 명시 결정 > 저장 메모리 > 외부 감사·이론
- **Ryan이 시스템 설계자**. 운영자(Ryan)가 직접 매기는 컬럼·정책·결정이 **항상 1순위**.
- 위계 순서:
  1. **Ryan의 현재(이번 세션) 명시 진술** — 가장 강함. 헌법급.
  2. **저장된 메모리 룰** (`feedback_*.md`) — stale 가능, Ryan 현재 진술과 충돌 시 **메모리를 의심 대상으로 flag**.
  3. **외부 감사·외부 reviewer·회계 이론·best practice** — 가장 약함. 운영자 정책 정합 검증 의무.
- **위반 신호 (즉시 정지)**:
  - 도메인 권위 단어("발생주의 정상화", "현금주의 위반", "compliance" 등) → 검증 강화 신호.
  - 묶음 진단 → 항목별 분리 검증.
  - 운영자 컬럼 위에 자동 차단·우선순위 얹는 hotfix 제안 → 금지.
  - 본인 메모리를 권위로 사용해 Ryan 현재 진술 검증 면제 → 금지.

---

## 언어 / 커뮤니케이션
- **모든 출력은 한국어** — 답변, 승인 요청, 경고, 에러 설명, 툴 실행 전 안내 등 예외 없음.
- 코드·명령어·로그·변수명은 영어 허용. 그 외 자연어 텍스트는 전부 한국어.
- "Do you want to proceed?", "Approve?", "Allow?" 등의 확인 메시지도 한국어로 작성.
