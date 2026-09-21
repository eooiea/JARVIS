# 🛠️ LLM 도구 스키마 비대화 문제 분석 및 해결 아키텍처 가이드

## 1. 개요 (Background)
자비스(JARVIS) 실행 세션 로그([Session Log](../logs)) 분석 결과, 매 ReAct 턴마다 주입되는 시스템 프롬프트 중 **도구 명세 스키마(Tool JSON Schema)**의 비중이 과도하게 커지는 현상이 발견되었습니다.

현재 14개 내외의 도구만 등록된 상태에서도:
- 단일 턴 프롬프트의 **약 330라인(전체 프롬프트의 80% 이상)**이 도구 스키마로 채워짐.
- 매 턴 **2,000 ~ 3,000 토큰**이 도구 정의에만 소모됨.
- 로컬 LLM(Ollama Qwen2.5 14B) 환경에서 **추론 지연(Latency, TTFT)이 턴당 15~30초 이상 발생하는 주원인**으로 작용.

---

## 2. 도구 스키마 비대화의 핵심 문제점

### 1) 추론 지연 (Latency 폭증)
- 로컬 LLM의 TTFT(Time-To-First-Token)는 프롬프트 길이에 선형 비례 이상으로 증가합니다.
- 단순 판단 1회를 내리기 위해 매번 수천 토큰의 정적 도구 정의를 재인코딩(KV Cache 미적용 시)하므로 사용자 체감 속도가 심각하게 저하됩니다.

### 2) "Lost in the Middle" 및 주의력 분산 (Attention Degradation)
- 트랜스포머 모델의 특성상 프롬프트의 시작부(시스템 명령)와 끝부분(최근 사용자 입력)에 어텐션이 집중되고, 중간에 위치한 방대한 JSON Schema는 무시되거나 왜곡되기 쉽습니다.
- 이로 인해 **필수 인자(Arguments) 누락, 잘못된 도구 선택, 환각(Hallucination)** 빈도가 상승합니다.

### 3) 유사 도구 간의 결정 장애
- `transform_excel`, `transform_excel_to_standard`, `batch_transform_orders`처럼 이름과 인자가 유사한 도구가 동시에 프롬프트에 나열되면 모델이 혼란을 겪고 잘못된 도구를 호출하거나 백트래킹을 유발합니다.

### 4) 도구 확장성(Scalability) 한계
- 향후 브라우저 제어, OS 윈도우 조작, 이메일, 문서 요약 등 도구가 50~100개로 늘어날 경우:
  - 프롬프트가 수만 토큰을 초과하여 **컨텍스트 윈도우 초과 또는 로컬 GPU VRAM OOM** 발생.
  - 시스템 확장이 원천적으로 불가능해짐.

---

## 3. 최신 AI 에이전트 업계의 해결 전략 (State-of-the-Art Solutions)

2024~2026년 기준 Anthropic, OpenAI, LangChain LangGraph, AutoGen 등에서 실무적으로 적용하는 핵심 아키텍처 패턴은 다음과 같습니다.

| 해결 전략 | 동작 방식 | 장점 | 단점 / 난이도 | 자비스 적합도 |
| :--- | :--- | :--- | :--- | :--- |
| **A. 상태 기반 도구 필터링 (Phase-Based Filtering)** | 자비스의 Working Memory Phase(`INIT`, `SEARCH`, `PROCESS`, `VERIFY`)에 따라 필요한 도구만 2~3개 활성화 | 구현 단순, 즉시 적용 가능, 토큰 70~80% 절감, 환각 제로 | 도구와 Phase 간 매핑 정의 필요 | 🌟 **최우선 권장 (자비스 아키텍처에 완벽 부합)** |
| **B. 2단계 도구 검색 (Tool RAG / Retrieval)** | 도구 요약 목록을 벡터 DB/BM25로 인덱싱 후 유저 명령과 유사한 상위 K개만 동적 주입 | 도구가 수백 개여도 확장 가능 | 검색 실패 시 필요한 도구가 프롬프트에서 누락될 위험 | ⚡ 도구가 30개 이상으로 증가 시 도입 |
| **C. 계층형 도구 디스패처 (Meta Tool Search)** | 기본 프롬프트에는 `search_tools`만 주고, LLM이 필요 시 도구를 검색하여 호출 | 기본 프롬프트 100토큰 이내 유지 | 도구 검색을 위한 추가 LLM 턴 발생 (턴 수 증가) | 🔍 범용 OS 에이전트 환경에 적합 |
| **D. 스키마 컴팩트화 (Schema Minification)** | 장황한 JSON Schema 대신 TypeScript 인터페이스나 Python 시그니처 형태로 압축 | 기존 로직 유지하면서 토큰 50~60% 즉시 절감 | 스키마 생성 파서 조정 필요 | 💡 보조 수단으로 상시 적용 권장 |

---

## 3.1 실전 심층 사례 분석: 구글 안티그래비티(Google Antigravity)의 아키텍처

실제 안티그래비티 에이전트에 주입되는 시스템 프롬프트를 실측 분석한 결과, 수많은 특화 기능(Android 빌드, Chrome DevTools 디버깅, 웹 접근성, 메모리 누수 분석, TDD 등)을 운영하면서도 **도구 스키마 비대화 문제를 완벽하게 회피하는 3대 핵심 패턴**이 확인되었습니다.

### 1) 마이크로커널(Micro-Kernel) 기본 도구셋 (최소 원자적 도구 14개)
* 안티그래비티는 도메인별 기능마다 별도의 Tool Schema를 생성하지 않습니다.
* LLM에게 직접 노출되는 API Tool Schema는 오직 **14개의 기본 원자적 도구**로 극도로 압축되어 있습니다:
  - 파일/코드 제어: `view_file`, `write_to_file`, `replace_file_content`, `multi_replace_file_content`, `list_dir`, `grep_search`
  - OS/터미널 제어: `run_command`, `manage_task`
  - 웹 리서치: `search_web`, `read_url_content`
  - 에이전트 오케스트레이션: `browser_subagent`, `generate_image`, `schedule`, `ask_question`

### 2) Skills & Plugins의 온디맨드 지연 로딩 (On-Demand Lazy Loading)
* 수백 개에 달하는 고급 기능과 도메인 가이드는 JSON Schema로 주입되지 않습니다.
* 프롬프트의 `<skills>` 섹션에는 **이름 + 1~2줄 요약 + 파일 경로(경량 인덱스)**만 등록됩니다:
  ```markdown
  Available skills:
  - a11y-debugging (.../SKILL.md): Uses Chrome DevTools MCP for accessibility...
  - android-cli (.../SKILL.md): Orchestrates Android development tasks...
  - chrome-devtools (.../SKILL.md): Uses Chrome DevTools via MCP for debugging...
  - modern-web-guidance (.../SKILL.md): Search tool for modern web development...
  ```
* 시스템 규칙: *"작업과 관련된 스킬이 있다면 실행 전 반드시 `view_file`로 해당 `SKILL.md` 지침을 읽어라."*
* **효과**: 프롬프트에는 스킬당 단 10~20토큰의 목차만 주입되며, **전체 스키마/지침은 필요할 때만 LLM이 `view_file`을 통해 온디맨드로 인출**하므로 시스템 프롬프트 토큰이 90% 이상 절감됩니다.

### 3) 서브에이전트(Subagent)를 통한 컨텍스트 격리
* 브라우저 조작처럼 수십 개의 세부 도구(click, type, scroll, DOM 파싱 등)가 필요한 헤비한 작업은 메인 에이전트 프롬프트에 도구를 전부 붙이지 않고, **`browser_subagent`라는 단일 위임 도구만 노출**합니다.
* 서브에이전트가 격리된 샌드박스에서 자체 도구셋으로 작업을 마친 뒤 **결과 요약본만 메인 에이전트에게 반환**하므로, 메인 에이전트의 컨텍스트 윈도우와 어텐션 품질이 오염되지 않습니다.

---

## 4. 자비스(JARVIS) 맞춤형 개선 로드맵 (내일 진행 계획)

### 1단계: Phase 기반 도구 동적 필터링 (Phase-Based Dynamic Tool Injection)
자비스는 이미 `WorkingMemory.current_phase`와 `Milestone`을 정밀하게 관리하고 있으므로, 이를 그대로 활용합니다.

```python
# Phase별 허용 도구 화이트리스트 매핑 (예시)
PHASE_TOOL_MAP = {
    "INIT": ["scan_directory", "read_file", "inspect_excel"],
    "SEARCH": ["scan_directory", "read_file", "inspect_excel"],
    "PROCESS": ["batch_transform_orders", "transform_excel", "create_excel", "write_file"],
    "VERIFY": ["inspect_excel", "read_file", "scan_directory"],
    "COMPLETE": []  # 추가 도구 호출 없이 최종 보고서 작성 유도
}
```
- **기대 효과**:
  - 매 턴 주입되는 도구가 **14개 -> 2~3개**로 축소.
  - 도구 스키마 토큰이 **2,500토큰 -> 400토큰 (84% 절감)**.
  - 추론 속도 2배 이상 향상, 도구 선택 오류 원천 차단.

### 2단계: JSON Schema 압축 (Minification)
- `"description": "Parameter path"`와 같은 무의미한 자동 생성 필드 제거.
- `ToolRegistry.get_compact_definitions()` 구현으로 필수 설명과 타입만 컴팩트하게 직렬화.

---

## 5. 참고 파일 및 위치
- 도구 등록 및 스키마 생성: [`src/jarvis/tools/registry.py`](../src/jarvis/tools/registry.py)
- 에이전트 루프 및 스키마 주입: [`src/jarvis/brain/agent.py`](../src/jarvis/brain/agent.py)
- 프로바이더 프롬프트 조립: [`src/jarvis/providers/ollama.py`](../src/jarvis/providers/ollama.py), [`src/jarvis/providers/gemini.py`](../src/jarvis/providers/gemini.py)
- 실행 로그 검증: [`logs/`](../logs)
