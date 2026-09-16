# 🛠️ LLM 도구 스키마 비대화 문제 분석 및 해결 아키텍처 가이드

## 1. 개요 (Background)
자비스(JARVIS) 실행 세션 로그([Session Log](file:///c:/Users/majun/Coding/javis/logs)) 분석 결과, 매 ReAct 턴마다 주입되는 시스템 프롬프트 중 **도구 명세 스키마(Tool JSON Schema)**의 비중이 과도하게 커지는 현상이 발견되었습니다.

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
- 도구 등록 및 스키마 생성: [`src/jarvis/tools/registry.py`](file:///c:/Users/majun/Coding/javis/src/jarvis/tools/registry.py)
- 에이전트 루프 및 스키마 주입: [`src/jarvis/brain/agent.py`](file:///c:/Users/majun/Coding/javis/src/jarvis/brain/agent.py)
- 프로바이더 프롬프트 조립: [`src/jarvis/providers/ollama.py`](file:///c:/Users/majun/Coding/javis/src/jarvis/providers/ollama.py), [`src/jarvis/providers/gemini.py`](file:///c:/Users/majun/Coding/javis/src/jarvis/providers/gemini.py)
- 실행 로그 검증: [`logs/`](file:///c:/Users/majun/Coding/javis/logs)
