# 🗺️ JARVIS 개발 로드맵: 능동적 엑셀 매크로 자동화

> **최종 목표**: 로컬 LLM 기반 독립형 사무 자동화 SaaS  
> **현재 집중 목표**: LLM을 통한 **능동적 엑셀 매크로 자동화** (시나리오 1 송장 변환 + 사무직 빈출 엑셀 업무 전반)  
> **기준 환경**: Windows 10/11, Python 3.11+  
> **문서 버전**: v2.0.0 (엑셀 집중 로드맵 개편)

---

## 1. 🎯 프로젝트 방향성 및 비전

### 1) 최종 목표 (Long-term Vision)
* **로컬 LLM 기반 독립형 사무 자동화 SaaS**: 기업 및 개인의 중요 데이터가 외부로 유출되지 않도록 사용자 로컬 환경에서 완전히 자율 동작하는 지능형 오피스 에이전트.

### 2) 현재 집중 목표 (Current Core Focus)
* **LLM을 통한 능동적 엑셀 매크로 자동화**:
  * **전통 매크로(VBA/고정 스크립트)의 한계**: 열 이름이나 순서가 하나만 바뀌어도 코드가 멈추고 유지보수 비용 발생.
  * **JARVIS 능동 자동화**: LLM이 제각각인 원본 엑셀의 헤더와 데이터를 지능적으로 파악하여, **별도 코딩 없이 원하는 양식으로 실시간 매핑·정제·변환·집계** 수행.
  * **적용 범위 (엑셀 실무 전반)**:
    1. **[기반] 다채널 이커머스 송장 변환**: [시나리오 1: 다채널 주문서 취합 및 송장 변환](./scenarios/01_다채널_주문서_취합_및_송장_변환/01_다채널_주문서_취합_및_송장_변환.md)
    2. **[확장] 일반 사무직 엑셀 업무**: 서로 다른 양식의 다채널 데이터 취합, 매출/비용 정산 및 통계 집계, 기업 보고서 양식 표준화, 결측치 및 데이터 오류 자동 검증

### 3) AI 모델 운영 전략 (Dual Engine Strategy)
* **기본 모드 (Single Model Default - 1개 모델 단독 운용)**:
  * **로컬 고성능 환경**: **Ollama (Qwen2.5 14B)** 단독 운용 (오프라인 보안, 제로 API 비용, 프라이버시 완벽 보호).
  * **GPU 사양 부족 환경 (대안)**: 로컬 GPU가 없거나 사양이 낮은 사용자를 위해 **Google Gemini (2.5/3.6 Flash)** 단독 운용 (초저사양 PC에서도 가볍고 빠른 클라우드 실행).
* **병행 모드 (Dual-Model Hybrid Option - 선택 옵션)**:
  * 사용자가 설정에서 "듀얼 모델 병행 사용"을 명시적으로 체크/활성화했을 때만 작동.
  * 가벼운 텍스트/판단은 로컬 Ollama, 복합 비전 분석 및 고난도 스키마 추론은 Gemini로 분담.

---

## 2. ✅ 핵심 작업 체크리스트 (Action Checklist)

앞으로 진행해야 할 작업들을 직관적이고 간단명료하게 정리한 실행 목록입니다.

### [Step 1] 도구 스키마 경량화 및 추론 지연 시간 단축
- [ ] **Phase 기반 도구 동적 필터링 구현**:
  - `WorkingMemory.current_phase`(`INIT`, `SEARCH`, `PROCESS`, `VERIFY`)에 따라 현재 필요한 도구만 2~3개 선별 주입.
- [ ] **프롬프트 토큰 및 TTFT 최적화**:
  - 도구 스키마 토큰 소모를 70% 이상 절감하여 로컬 LLM(Ollama) 추론 지연을 턴당 15초 이내로 단축.
- [ ] **단위/통합 테스트 검증**:
  - 도구 필터링 후에도 기존 123개 테스트 및 에이전트 완주 기능이 정상 통과하는지 확인.

### [Step 2] 시나리오 1: 다채널 주문서 취합 & 송장 변환 완결
- [ ] **5대 택배사 표준 프리셋 및 커스텀 템플릿 검증**:
  - CJ대한통운, 우체국, 한진, 롯데, 로젠 및 사용자 지정 커스텀 템플릿 변환 테스트셋([set01~set10](../tests/data/scenario1)) 완전 검증.
- [ ] **데이터 무결성 정제 로직 보강**:
  - 전화번호(`010-XXXX-XXXX`), 주소 분할(기본/상세 주소), 수량 정수화 자동 처리 검증.
- [ ] **에이전트 E2E 자율 변환 테스트 완결**:
  - [test_scenario1_agent_e2e.py](../tests/integration/test_scenario1_agent_e2e.py)를 단일 모델 환경(Ollama / Gemini)에서 각각 완주 확인.

### [Step 3] 범용 사무직 엑셀 업무 도구군 확장
- [ ] **[취합] 다채널 시트 자동 병합 (Excel Consolidator)**:
  - 여러 파일의 서로 다른 시트를 공통 기준 열(고유 ID, 일자, 부서명 등)을 기반으로 하나의 통합 엑셀로 자동 병합.
- [ ] **[정산/통계] 피벗 및 집계 수식 자동 주입 (Pivot & Summary Generator)**:
  - 매출/비용 원장 데이터를 기반으로 카테고리별 합계, 평균, 부가세(VAT) 자동 계산 수식(`SUM`, `AVERAGE`, `SUBTOTAL`) 주입.
- [ ] **[검증] 데이터 클렌징 및 이상치 감지 (Data Cleanser & Validator)**:
  - 결측치(공란), 중복 데이터, 유효하지 않은 이메일/사업자번호/주민번호 형식 자동 탐지 및 정제 보고.
- [ ] **[서식] 비즈니스 보고서 스타일 템플릿화 (Corporate Styler)**:
  - 헤더 배경색, 가독성 높은 비즈니스 폰트, 외곽선 테두리, 열 너비 자동 맞춤(Auto-fit Width) 일괄 적용.

### [Step 4] 사용자 보고 카드 및 피드백 강화
- [ ] **터미널 Rich 변환 요약 보고 카드 출력**:
  - 파일 자동 실행(`os.startfile`)은 제외하고, 작업 완료 시 터미널에 **[총 처리 건수 / 자동 정제 건수 / 결측·오류 건수 / 산출물 저장 경로]**가 담긴 깔끔한 Rich 패널 카드 표시.
- [ ] **작업 세션 감사 로그 저장**:
  - 변환 전후의 통계 요약 정보를 `.jarvis/sessions/` 또는 `logs/`에 안전하게 기록.

### [Step 5] 단일 모델 환경별 안정화 및 벤치마크
- [ ] **Gemini 단독 모드 검증**:
  - 저사양 GPU 사용자 환경을 가정한 Gemini 단독 실행 정합성 및 속도 테스트.
- [ ] **Ollama 단독 모드 검증**:
  - RTX 4070 Super 환경에서 오프라인 로컬 LLM 단독 실행 정합성 및 백트래킹 안정성 테스트.
- [ ] **듀얼 병행 모드(선택 옵션) 동작 검증**:
  - 듀얼 모드 활성화 시 비전/스키마 추론과 텍스트 제어가 의도대로 분담되는지 확인.

---

## 3. 🔑 핵심 기술 스택 요약 (실제 프로젝트 코드 기준)

현재 코드베이스(`requirements.txt` 및 실제 구현 모듈)에 100% 정합된 기술 스택 명세입니다:

| 영역 | 기술 / 라이브러리 | 현재 용도 및 세부 구현 모듈 |
| :--- | :--- | :--- |
| **AI & LLM (클라우드)** | `google-genai` (>=1.0.0) | Gemini 2.5/3.6 Flash·Pro VLM/LLM ([gemini.py](../src/jarvis/providers/gemini.py)) (GPU 부족 환경 대안 & 고난도 멀티모달) |
| **AI & LLM (로컬)** | `ollama` (>=0.4.0) | Ollama Qwen2.5 14B 로컬 LLM ([ollama.py](../src/jarvis/providers/ollama.py)) (오프라인 보안 & 제로 비용 기본 엔진) |
| **오피스 & 엑셀 가공** | `openpyxl` (>=3.1.0) | 서식 완비 `.xlsx` 자동 생성, Any-to-Any 송장 변환기 ([excel_transformer.py](../src/jarvis/office/excel_transformer.py), [excel_writer.py](../src/jarvis/office/excel_writer.py)) |
| **문서 입력 처리** | `pypdf` (>=5.0.0) | PDF 문서 텍스트/페이지 파싱 ([file_input.py](../src/jarvis/vision/file_input.py)) |
| **화면 캡처 & 전처리** | `mss`, `Pillow` | 고속 화면 캡처 및 이미지 전처리 ([capture.py](../src/jarvis/vision/capture.py)) |
| **GUI 제어 & 킬스위치** | `pyautogui`, `keyboard` | 마우스/키보드 제어 및 긴급 비상 정지 핫키 ([killswitch.py](../src/jarvis/guardrails/killswitch.py)) |
| **데이터 검증 & 설정** | `pydantic`, `pyyaml`, `python-dotenv` | 도구 인자 유효성 검사, 설정 파일 파싱 ([registry.py](../src/jarvis/tools/registry.py), [config.py](../src/jarvis/utils/config.py)) |
| **터미널 UI** | `rich` (>=13.7.0) | 대화형 인터페이스, 계획 및 작업 완료 요약 카드 렌더링 ([app.py](../src/jarvis/cli/app.py)) |
| **TDD 테스트 프레임워크** | `pytest`, `pytest-mock` | 단위 및 통합 테스트 자동화 (**총 123개 테스트 통과 체계 구축**) |

---

## 4. 📁 프로젝트 디렉터리 구조 (현재 코드베이스 반영)

현재 실제 존재하는 47개의 소스 파일과 26개의 테스트 파일 체계입니다:

```text
javis/
├── config/                          # 시스템 환경 설정
│   ├── .env                         # API 키 및 환경 변수
│   └── config.yaml                  # 모델명, 딜레이, 기본 프로바이더 설정
├── docs/                            # 프로젝트 설계 및 가이드 문서
│   ├── DEVELOPMENT_ROADMAP.md       # 본 개발 로드맵 (엑셀 집중 개편)
│   ├── JARVIS_SPEC.md               # 자비스 시스템 기획 및 PRD
│   ├── BLACKBOARD_BACKTRACKING_ARCHITECTURE.md # 칠판 기억 및 백트래킹 아키텍처
│   ├── TOOL_SCHEMA_OPTIMIZATION_GUIDE.md       # 도구 스키마 경량화 가이드
│   └── scenarios/                   # 외주 5대 핵심 자동화 시나리오
│       ├── 01_다채널_주문서_취합_및_송장_변환/
│       │   ├── 01_다채널_주문서_취합_및_송장_변환.md
│       │   └── test_data_spec.md
│       ├── 02_웹_상품_가격_수집_및_모니터링/
│       ├── 03_영수증_인보이스_시각_자동_정산/
│       ├── 04_대량_문서_렌더링_및_PDF_변환/
│       └── 05_데스크톱_ERP_웹폼_연속_자동입력/
├── outputs/                         # 산출물 기본 저장 디렉터리
├── logs/                            # 세션 로그 및 실행 감사 기록
├── scripts/                         # 시나리오 테스트 데이터 생성 스크립트
│   ├── generate_scenario1_mock_data.py
│   └── generate_scenario1_10_testsets.py
├── src/
│   └── jarvis/
│       ├── __init__.py
│       ├── main.py                  # CLI 진입점 및 시스템 초기화
│       ├── brain/                   # AI 추론 & 작업 기억 코어
│       │   ├── agent.py             # ReAct 실행 루프 및 듀얼 출력 제어
│       │   ├── memory.py            # Working Memory (칠판) 및 KV 캐시 레이아웃
│       │   ├── evaluator.py         # 룰 + 자가성찰 하이브리드 검증기
│       │   ├── checkpoint.py        # ToT 체크포인트 스냅샷 & 롤백 엔진
│       │   └── planner.py           # 상위 마일스톤 생성 및 분해기
│       ├── office/                  # 엑셀/파일 변환 엔진
│       │   ├── excel_transformer.py # Any-to-Any 송장 변환 및 데이터 정제
│       │   ├── excel_writer.py      # 스타일/서식 적용 엑셀 생성
│       │   ├── excel_reader.py      # 기존 엑셀 시트/헤더 파싱
│       │   ├── csv_handler.py       # CSV/TSV 인코딩 감지 및 변환
│       │   ├── file_namer.py        # AI 지능형 파일 작명
│       │   └── file_manager.py      # 경로 단일화 및 중복 넘버링 방지
│       ├── providers/               # LLM 엔진 어댑터
│       │   ├── base.py              # 프로바이더 추상 인터페이스
│       │   ├── factory.py           # 단일/듀얼 프로바이더 인스턴스 팩토리
│       │   ├── gemini.py            # Google Gemini 2.5/3.6 어댑터
│       │   └── ollama.py            # Ollama Qwen2.5 14B 로컬 어댑터
│       ├── tools/                   # 에이전트 실행 가능 도구군
│       │   ├── registry.py          # 도구 등록 및 스키마 유효성 검증기
│       │   ├── office.py            # 엑셀 생성 및 송장 변환 도구
│       │   ├── filesystem.py        # 파일 읽기/쓰기 및 디렉터리 스캔
│       │   └── vision.py            # 화면 분석 및 비전 추출 도구
│       ├── vision/                  # 비전 인식 모듈
│       │   ├── capture.py           # mss 기반 화면 캡처
│       │   ├── analyzer.py          # VLM 이미지/문서 분석기
│       │   ├── anchor.py            # UI Form 앵커 좌표 감지
│       │   └── file_input.py        # 이미지/PDF 파일 로더
│       ├── controller/              # 윈도우 GUI 제어 모듈
│       │   ├── base.py              # 안전 지연시간(Action Delay) 공통 베이스
│       │   ├── mouse.py             # 마우스 이동/클릭/스크롤
│       │   ├── keyboard.py          # 키보드 타이핑/단축키 조합
│       │   └── form_filler.py       # 앵커 기반 순차 양식 입력기
│       ├── guardrails/              # 시스템 안전 가드레일
│       │   ├── killswitch.py        # 긴급 킬스위치 (ESC/단축키 감지)
│       │   ├── permissions.py       # 경로 격리 및 위험 명령 사전 승인
│       │   └── connectivity.py      # 통신 및 API 연결 상태 진단
│       ├── infra/                   # 인프라 & 트랜잭션 격리
│       │   └── staging.py           # .jarvis/staging/ 격리 파일 트랜잭션
│       ├── cli/                     # Rich 기반 터미널 사용자 인터페이스
│       │   └── app.py               # 대화형 대화창 및 보고 카드 UI
│       └── utils/                   # 공통 유틸리티
│           ├── config.py            # 설정 파일 로더 및 환경변수 주입
│           ├── logger.py            # 시스템 로거
│           └── session_logger.py    # 세션 턴별 상세 감사 로거
├── tests/                           # TDD 테스트 스위트 (123개 테스트 통과)
│   ├── conftest.py                  # 공통 Fixture 및 환경 설정
│   ├── data/scenario1/              # 송장 변환 10종 테스트셋 (set01~set10)
│   ├── unit/                        # 20개 단위 테스트 모듈 (2,086 라인)
│   │   ├── test_agent.py
│   │   ├── test_checkpoint.py
│   │   ├── test_excel_transformer.py
│   │   ├── test_evaluator.py
│   │   ├── test_memory.py
│   │   ├── test_staging.py
│   │   ├── test_tool_registry.py
│   │   └── ...
│   └── integration/                 # 5개 통합 테스트 모듈 (604 라인)
│       ├── test_agent_backtracking.py
│       ├── test_scenario1_agent_e2e.py
│       ├── test_pipeline.py
│       └── ...
├── requirements.txt                 # 프로젝트 필수 의존성 명세
└── run_jarvis.bat                   # 윈도우 원클릭 실행 배치 스크립트
```
