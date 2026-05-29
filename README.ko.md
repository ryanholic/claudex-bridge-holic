# claudex-bridge-holic

> Claude Code 환경 그대로. Codex가 일한다.

**[raine/claude-code-proxy](https://github.com/raine/claude-code-proxy) 위에서 동작합니다.** 이 레포는 이미 실행 중임을 전제합니다.

---

## 문제

Claude Code를 딱 내 방식대로 세팅하는 데 시간을 꽤 썼습니다.

커스텀 CLAUDE.md 규칙. 워크플로우마다 맞춤 스킬. 일관성을 잡아주는 훅. 내가 생각하는 방식에 맞게 튜닝된 하네스 전체.

그런데 Claude Max 사용량이 바닥납니다. Codex Pro도 추가 구독합니다.

이제 어떻게 하죠?

**Codex CLI를 따로 쓰면 그동안 쌓아온 게 다 사라집니다.** 다른 명령어. 다른 컨텍스트. CLAUDE.md 규칙도, Skills도, Hooks도 적용 안 됩니다. 처음부터 다시 시작하는 느낌입니다.

결국 Claude 한도까지 쓰다가 수동으로 Codex로 전환하거나, 아니면 Codex를 거의 안 쓴 채 구독료만 나가게 됩니다.

---

## claudex-bridge-holic이 하는 일

Codex를 Claude Code **안에서** 서브에이전트로 실행합니다.

환경을 벗어날 필요가 없습니다. CLAUDE.md 규칙, Skills, Hooks 그대로입니다. 라우터가 작업 유형에 따라 Claude로 갈지 Codex로 갈지 자동으로 결정합니다.

```
Claude Code에서 무언가 입력
          │
          ▼
   Sonnet (라우터)
          │
          ├─ 가벼운 작업       →  Codex mini  (빠름, 저렴)
          ├─ 코딩 / 버그수정   →  Codex 5.4   (표준)
          ├─ 리뷰 / 감사       →  Codex 5.5   (심층)
          └─ 적대적 리뷰       →  Codex 5.5   (내 규칙 적용)
```

Codex는 격리된 서브에이전트 컨텍스트에서 실행됩니다. 내 CLAUDE.md 규칙이 거기까지 따라옵니다. 결과는 메인 세션으로 돌아옵니다. 전환 자체가 보이지 않습니다.

**같은 워크플로우. 두 구독 모두 최대 활용.**

---

## ToS 참고

로컬 프록시를 통해 Codex 백엔드를 사용하는 것은 회색지대입니다. raine의 README 표현을 빌리면: *"using the Codex or Kimi backends from a non-official client is a gray area."* 사용은 본인 판단 하에.

---

## 이게 열어주는 것들

Codex가 Claude Code 안에서 서브에이전트로 돌아가면서 이전에는 불가능했던 것들이 가능해집니다.

**작업에 맞는 모델을 자동으로, 또는 명시적으로 선택.**  
가벼운 조회? Codex mini. 기능 구현? Codex 5.4. 심층 아키텍처 리뷰? Codex 5.5. 라우터가 자동으로 처리하거나, 직접 지정할 수도 있습니다.

**세션을 벗어나지 않고 크로스모델 리뷰.**  
Claude가 코드를 작성합니다. Codex가 적대적으로 리뷰합니다 — 범용 best practice가 아닌 *내* CLAUDE.md 규칙 기준으로. Claude가 응답합니다. 한 세션 안에서, 복붙 없이.

**한 세션 안에서 멀티모델 토론.**  
설계 질문을 던집니다. Claude가 제안을 작성합니다. Codex 5.5가 반론을 제기합니다. Claude가 응답합니다. 대화 전체가 한 곳에, 양쪽 컨텍스트가 모두 유지된 채로.

두 모델을 동시에 쓰는 게 아닙니다. 같은 환경에서, 같은 규칙으로, 창을 전환하지 않고 *함께* 작동하게 만드는 겁니다.

---

## 실제로 라우팅이 어떻게 작동하나

`/codex-on`이 활성화되면 매 프롬프트마다 Claude가 응답하기 전에 두 개의 훅이 실행됩니다.

1. `codex_mode_reminder.sh` — 컨텍스트에 라우팅 힌트 주입
2. `codex_tier_writer.py` — 키워드 기반으로 프롬프트를 `medium` 또는 `heavy`로 분류, tier 파일 작성

메인 세션(Sonnet)은 힌트를 읽고 적절한 서브에이전트에 위임합니다. `pre_tool_router_enforcer.py`가 이를 강제합니다 — Codex로 가야 할 작업을 Claude가 직접 파일 편집으로 처리하려 하면 차단하고 리다이렉트합니다.

실사용 기준으로 약 90%의 작업이 첫 시도에서 의도한 대로 라우팅됩니다 (단일 사용자 자체 측정값 — 사용 패턴에 따라 다를 수 있음). 필요할 때는 명시적 오버라이드를 사용할 수 있습니다.

**예시: `/codex-on` 활성 상태**

| 입력 | 라우팅 | 이유 |
|---|---|---|
| "X 사용처 전부 찾아줘" | `ccp-gpt-5-4-mini` | 경량 조회 |
| "Y 기능 구현해줘" | `ccp-gpt-5-4` | 코딩 작업, medium tier |
| "이 인증 로직 리뷰해줘" | `ccp-codex-reviewer` | review 키워드, heavy tier |
| "소넷으로 해줘" | Sonnet 직접 처리 | 명시적 오버라이드 |
| "오퍼스로" | Opus | 명시적 에스컬레이션 |

**예시: `/codex-off` 활성 또는 아무 커맨드 없는 상태**

모든 작업이 Claude로 직접 갑니다. 훅은 통과, tier 파일은 작성 안 됨, enforcer는 아무것도 안 합니다. bridge-holic 설치 전과 동일하게 동작합니다.

---

## 명시적 오버라이드

대부분의 경우 자동 라우터가 처리합니다. 특정 모델을 원할 때:

```
"소넷으로 봐줘" / "Claude로 해줘"
→ Sonnet이 직접 처리

"오퍼스로" / "Opus로 검토해"
→ Opus로 에스컬레이션

/codex-off  →  Claude가 모든 작업 직접 처리
/codex-on   →  Codex 라우팅 재개
```

---

## 포함된 파일

```
claudex-bridge-holic/
├── agents/
│   ├── ccp-gpt-5-4-mini.md          # 경량: 검색, grep, 조회
│   ├── ccp-gpt-5-4.md               # 표준: 코딩, 버그수정, 분석
│   ├── ccp-gpt-5-5.md               # 심층: 리뷰, 설계, 보안 감사
│   ├── ccp-codex-reviewer.md        # 적대적: 내 규칙으로 PR 리뷰
│   └── claude-opus.md               # Opus 직접 호출: env -i로 CCP 프록시 우회
├── commands/
│   ├── codex-on.md                  # /codex-on  — Codex 강제 위임 모드
│   └── codex-off.md                 # /codex-off — Claude 직접 처리 복원
├── hooks/
│   ├── codex_mode_reminder.sh       # UserPromptSubmit — 라우팅 힌트 주입
│   ├── codex_tier_writer.py         # UserPromptSubmit — 프롬프트 tier 분류 (medium/heavy)
│   ├── auto_model_router.py         # UserPromptSubmit — 프롬프트 분류, 서브에이전트 세션에서 힌트 주입 차단
│   ├── pre_tool_router_enforcer.py  # PreToolUse — tier 기반 직접 쓰기 차단
│   └── pre_agent_claude_redirect.py # PreToolUse — claude-* 서브에이전트를 GPT 계열로 리다이렉트
├── examples/
│   ├── CLAUDE.md                    # 예시 라우팅 규칙 (본인 것으로 교체)
│   └── proxy-info.json              # 프록시 메타데이터: 모델명 및 설정 안내
└── install.sh                       # 원라이너 설치 스크립트
```

모든 에이전트는 재귀 위임 차단 — 무한 루프 없음.

---

## 전제 조건

1. **[Claude Code](https://claude.ai/code)** 1.0+ (서브에이전트 지원)
2. **Codex Pro** 구독 (OpenAI)

이것만 있으면 됩니다. 나머지는 `install.sh`가 안내합니다.

---

## 설치

```bash
git clone https://github.com/ryanholic/claudex-bridge-holic
cd claudex-bridge-holic
./install.sh
```

인스톨러가 자동으로 처리합니다:
1. **[raine/claude-code-proxy](https://github.com/raine/claude-code-proxy)** 설치 여부 확인 → 없으면 설치 방법 안내
2. `claude-codex` 런처를 `~/.local/bin/`에 설치
3. hooks, agents, slash commands를 `~/.claude/`에 복사
4. 셀프 테스트로 프록시 동작 확인

설치 후 Claude Code 재시작. 확인: 간단한 검색 요청 → `ccp-gpt-5-4-mini`로 라우팅되면 성공.

---

## 라우터 설정

`claude-code-proxy`는 표준 OpenAI API가 아닌 **ChatGPT Codex 백엔드**로 요청을 라우팅합니다. 사용 가능한 모델은 ChatGPT 계정 플랜에 따라 다르며, 지원하지 않는 모델을 요청하면 400 에러가 반환됩니다.

| 모델 | 용도 |
|---|---|
| `gpt-5.4-mini` | 빠른 조회 |
| `gpt-5.4` | 일반 코딩 |
| `gpt-5.5` | 심층 리뷰 (최신) |

> **참고:** 계정 플랜에 따라 모델 가용성이 다를 수 있습니다. 모델명을 변경하기 전에 [raine/claude-code-proxy](https://github.com/raine/claude-code-proxy)에서 현재 확인된 모델 목록을 확인하세요.

`examples/proxy-info.json` (프록시 메타데이터 및 모델명)을 참고하세요.

---

## 비용 구조

```
Claude 구독 (예: Max 5X)
└─ Sonnet: 라우터 + 커뮤니케이션 — 사용량 감소하지만 0이 되진 않음

Codex 구독 (예: Codex Pro 5X)
└─ 실제 작업 대부분 — 최대 활용
```

Sonnet은 모든 메시지를 라우터로 받으므로 Claude 사용량이 완전히 0이 되지는 않습니다. 단, 일반적인 워크플로에서는 실제 추론의 상당 부분이 Codex로 이동합니다. 고빈도 단문 요청이 많은 경우에는 라우팅 오버헤드가 쌓일 수 있습니다.

---

## 알려진 문제

**`pre_tool_router_enforcer.py` tier 차단은 별도 설정 필요**

이 훅은 `/tmp/claude_tier_{session_id}.json` 파일을 읽어 직접 쓰기 차단 여부를 결정합니다. 이 파일은 작업 복잡도를 `"medium"` (Edit/Write 차단) 또는 `"heavy"` (Edit/Write/Bash 차단)으로 분류하는 별도 훅이나 커맨드가 작성해야 합니다. 그런 writer가 없으면 tier 차단 로직은 비활성 상태로 동작하고 모든 툴이 통과됩니다 — 안전한 동작입니다. `/codex-off` bypass와 킬스위치는 이 설정과 무관하게 항상 작동합니다.

---

**`/codex-off` 모드에서 훅 데드락**

`pre_tool_router_enforcer.py` 훅은 세션 tier가 높을 때 직접 쓰기와 Bash 명령을 차단합니다. 초기 버전에서는 `/codex-off`(native 모드)로 전환해도 이 차단이 해제되지 않아 — 사용자가 명시적으로 Codex 라우팅을 껐는데도 Claude가 파일을 수정할 수 없는 상황이 발생했습니다.

**현재 버전에서는 수정됐습니다.** 훅이 이제 `~/.claude/codex_native_on_{session_id}` 파일을 확인해 native 모드일 때 즉시 통과시킵니다.

유사한 데드락이 발생하면 비상 킬스위치:

```bash
touch ~/.claude/router_enforcer.off   # 훅 전체 비활성화
# 필요한 작업 후:
rm ~/.claude/router_enforcer.off      # 재활성화
```

---

## 커스터마이징

bridge-holic은 의도적으로 opinionated합니다 — 한 사람의 워크플로를 그대로 담았습니다. Fork해서 자신의 것으로 만드세요.

**라우팅 키워드 변경** (어떤 작업이 Codex로 갈지 결정):  
`hooks/codex_tier_writer.py`의 `HEAVY`·`MEDIUM` 정규식을 편집하세요. 파일 상단 주석이 각 tier를 설명합니다. 어떤 언어든 추가 가능 — 이미 들어있는 한국어 항목이 작동 예시입니다.

**호출 에이전트 변경**:  
`hooks/pre_tool_router_enforcer.py`의 `AGENT_MAP`과 자신의 `CLAUDE.md` 라우팅 테이블을 수정하세요. `agents/` 디렉토리의 `.md` 파일이 실제 서브에이전트 정의입니다 — 이름을 바꾸거나 교체하면 됩니다.

**각 에이전트 동작 변경**:  
`agents/` 디렉토리의 `.md` 파일을 편집하세요. 모델명, 허용 도구, 시스템 프롬프트가 담긴 일반 마크다운입니다. 제약은 두 가지뿐: 재귀 차단용 `--disallowedTools "Agent,TaskCreate"`, path traversal 차단용 `CLAUDE_JOB_DIR` 검증.

**다른 프록시나 백엔드 사용**:  
에이전트는 `${BRIDGE_HOLIC_BIN:-$HOME/.local/bin/claude-codex}`를 호출합니다. `ANTHROPIC_BASE_URL`을 설정하고 로컬 프록시를 시작하는 런처 스크립트라면 무엇이든 이 환경변수로 가리킬 수 있습니다. 나머지 하네스는 백엔드에 무관합니다.

---

## 관련 프로젝트

- [raine/claude-code-proxy](https://github.com/raine/claude-code-proxy) — 이 레포가 기반으로 하는 transport 레이어 (`claude-code-proxy-headless`)
- [wshobson/agents](https://github.com/wshobson/agents) — 멀티 하네스 에이전트 마켓플레이스 (다른 접근, 같은 문제 공간)

---

*by [@ryanholic](https://github.com/ryanholic)*

---

*이 도구는 **[썸머홀릭](https://summerholic.kr)** 을 운영하면서 만들었습니다 — 여름에 중독된 썸머뷰티 브랜드, 𝘼𝙡𝙬𝙖𝙮𝙨 𝙎𝙪𝙢𝙢𝙚𝙧 𝙎𝙐𝙈𝙈𝙀𝙍 𝙃𝙊𝙇𝙄𝘾. 도움이 됐다면 한번 들러보세요 → [summerholic.kr](https://summerholic.kr) · [Instagram](https://www.instagram.com/summerholic.kr/)*
