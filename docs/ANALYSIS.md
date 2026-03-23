# MiroFish 소스코드 분석 문서

## 1. 프로젝트 개요

MiroFish는 문서 기반 시드 정보를 활용하여 수십~수백 개의 AI 에이전트로 소셜 미디어 시뮬레이션을 수행하는 예측 엔진이다.

**핵심 파이프라인:**
```
문서 업로드 → 온톨로지 생성 → 지식 그래프 구축 → 에이전트 생성 → 시뮬레이션 실행 → 리포트 생성 → 대화형 분석
```

---

## 2. 디렉터리 구조

### Backend (Python/Flask)
```
backend/
├── run.py                              # 진입점 (Flask 서버 시작)
├── pyproject.toml                      # Python 프로젝트 설정
├── requirements.txt                    # 의존성
├── app/
│   ├── __init__.py                     # Flask 앱 팩토리 (CORS, Blueprint 등록)
│   ├── config.py                       # 설정 관리
│   ├── api/                            # API 라우트 (Blueprint)
│   │   ├── graph.py                    # 그래프 구축 API
│   │   ├── simulation.py              # 시뮬레이션 API
│   │   └── report.py                  # 리포트 생성 & 채팅 API
│   ├── services/                       # 핵심 비즈니스 로직
│   │   ├── ontology_generator.py      # LLM으로 엔티티/관계 정의 생성
│   │   ├── graph_builder.py           # Zep 지식 그래프 구축
│   │   ├── zep_entity_reader.py       # Zep에서 엔티티 읽기
│   │   ├── oasis_profile_generator.py # 에이전트 프로필 생성
│   │   ├── simulation_config_generator.py  # 시뮬레이션 파라미터 생성
│   │   ├── simulation_manager.py      # 시뮬레이션 상태 관리
│   │   ├── simulation_runner.py       # OASIS 시뮬레이션 실행
│   │   ├── simulation_ipc.py         # 시뮬레이션 서브프로세스 IPC
│   │   ├── report_agent.py           # ReACT 기반 리포트 생성
│   │   ├── zep_tools.py              # 그래프 검색 & 분석 도구
│   │   ├── zep_graph_memory_updater.py # 시뮬레이션 결과로 그래프 업데이트
│   │   └── text_processor.py         # 텍스트 청킹 & 전처리
│   ├── models/                         # 데이터 모델
│   │   ├── project.py                 # 프로젝트 상태 관리
│   │   └── task.py                    # 비동기 작업 추적
│   └── utils/                          # 유틸리티
│       ├── llm_client.py              # OpenAI 호환 LLM 래퍼
│       ├── file_parser.py             # PDF/MD/TXT 파싱
│       ├── logger.py                  # 로깅
│       ├── retry.py                   # 재시도 메커니즘
│       └── zep_paging.py             # Zep API 페이지네이션
└── scripts/                            # OASIS 실행 스크립트
```

### Frontend (Vue 3/Vite)
```
frontend/
├── src/
│   ├── api/                            # 백엔드 API 서비스 레이어
│   │   ├── index.js                   # Axios 설정, 인터셉터, 재시도
│   │   ├── graph.js                   # 그래프 구축 API
│   │   ├── simulation.js             # 시뮬레이션 생명주기 API
│   │   └── report.js                 # 리포트 생성 API
│   ├── components/                     # 워크플로우 단계별 컴포넌트
│   │   ├── Step1GraphBuild.vue        # 온톨로지 생성 & 그래프 구축
│   │   ├── Step2EnvSetup.vue          # 에이전트 프로필 & 환경 설정
│   │   ├── Step3Simulation.vue        # 실시간 시뮬레이션 실행
│   │   ├── Step4Report.vue            # 리포트 생성 워크플로우
│   │   ├── Step5Interaction.vue       # 에이전트와 대화/설문
│   │   ├── GraphPanel.vue             # D3 기반 지식 그래프 시각화
│   │   └── HistoryDatabase.vue        # 프로젝트 히스토리 대시보드
│   ├── views/                          # 페이지 레벨 컨테이너
│   │   ├── Home.vue                   # 랜딩 페이지
│   │   ├── MainView.vue               # Step 1-2 레이아웃
│   │   ├── SimulationRunView.vue      # Step 3 실행 뷰
│   │   ├── ReportView.vue             # Step 4 리포트 뷰
│   │   └── InteractionView.vue        # Step 5 인터랙션 뷰
│   ├── router/index.js                # Vue Router 설정
│   └── store/pendingUpload.js         # 파일/요구사항 임시 상태
├── vite.config.js                     # Vite 빌드 설정
└── package.json                       # 의존성
```

---

## 3. 기술 스택

| 레이어 | 기술 | 버전 |
|--------|------|------|
| Backend Framework | Flask | >= 3.0.0 |
| Frontend Framework | Vue 3 (Composition API) | ^3.5.24 |
| Build Tool | Vite | ^7.2.4 |
| LLM Client | OpenAI SDK | >= 1.0.0 (호환 포맷) |
| Knowledge Graph | Zep Cloud | 3.13.0 |
| Simulation Engine | OASIS (CAMEL-AI) | 0.2.5 / 0.2.78 |
| Graph Visualization | D3.js | ^7.9.0 |
| HTTP Client | Axios | ^1.13.2 |
| File Parsing | PyMuPDF | >= 1.24.0 |

---

## 4. 워크플로우 파이프라인 (5단계)

### Step 1: 그래프 구축

**API:** `POST /api/graph/ontology/generate` → `POST /api/graph/build`

```
사용자가 문서 업로드 + 시뮬레이션 요구사항 입력
    ↓
FileParser: PDF/MD/TXT에서 텍스트 추출
    ↓
TextProcessor: 전처리 (공백 정리, 개행 정규화)
    ↓
OntologyGenerator (LLM): 엔티티 타입 10개 + 관계 타입 6~10개 설계
    - 필수 포함: Person, Organization (폴백 타입)
    - 엔티티는 실제 행위자만 (추상 개념 X)
    ↓
GraphBuilderService: Zep 그래프 생성
    - 텍스트를 500자 단위로 청킹 (50자 오버랩)
    - 배치 단위(3개)로 Zep에 에피소드 추가
    - Zep이 NLP 파이프라인으로 엔티티/관계 추출
    ↓
지식 그래프 완성 (노드 + 엣지)
```

**핵심 설계:**
- 엔티티는 소셜 미디어에서 발언할 수 있는 실제 행위자여야 함
- "감정", "트렌드" 같은 추상 개념은 엔티티로 만들지 않음
- 온톨로지는 정확히 10개 엔티티 타입 (8개 도메인 특화 + 2개 기본)

### Step 2: 환경 설정

**API:** `POST /api/simulation/create` → `POST /api/simulation/prepare`

```
ZepEntityReader: 정의된 엔티티만 필터링
    - 기본 Entity/Node 레이블 제외
    - 실제 타입 레이블이 있는 노드만 선택
    ↓
OasisProfileGenerator (LLM): 에이전트 프로필 생성
    - 개인 엔티티 → 상세 페르소나 (나이, 성별, MBTI, 직업, 관심사)
    - 그룹 엔티티 → 대표 에이전트 (영향력 1.5배)
    - 병렬 생성 (기본 3개 동시)
    ↓
SimulationConfigGenerator (LLM): 시뮬레이션 파라미터 생성
    - 시간 설정: 총 시뮬레이션 시간, 라운드당 분, 피크 시간
    - 에이전트 설정: 활동 수준, 시간당 게시물, 감정 편향
    - 이벤트 설정: 초기 게시물, 예약 이벤트, 핫 토픽
    - 플랫폼 설정: 최신성 가중치, 바이럴 임계값, 에코챔버 강도
    ↓
프로필 + 설정 저장 (JSON/CSV)
```

**에이전트 프로필 구조:**
```python
OasisAgentProfile:
    user_id: int              # 순차 ID
    user_name: str            # 소셜 미디어 사용자명
    name: str                 # 표시 이름
    bio: str                  # 짧은 소개
    persona: str              # 상세 캐릭터 설명
    age, gender, mbti         # 인구통계
    profession, interests     # 역할 & 관심사
    karma / follower_count    # 플랫폼별 영향력
    source_entity_uuid: str   # Zep 엔티티 역추적
```

### Step 3: 시뮬레이션 실행

**API:** `POST /api/simulation/start`

```
SimulationRunner: OASIS 서브프로세스 생성
    - run_twitter.py & run_reddit.py 병렬 실행
    - 각 에이전트가 프로필 기반으로 자율적 행동
    ↓
실시간 모니터링:
    - actions.jsonl에 에이전트 행동 기록
    - 현재 라운드, 경과 시간, 행동 통계 추적
    - 최근 50개 행동 큐 유지 (실시간 표시)
    ↓
(선택) ZepGraphMemoryUpdater:
    - 에이전트 행동을 자연어로 변환
    - Zep에 에피소드로 전송 → 그래프 업데이트
    - 시뮬레이션 결과가 지식 그래프에 반영
```

**에이전트 행동 유형:**
- Twitter: POST, LIKE, REPOST, COMMENT, FOLLOW
- Reddit: POST, COMMENT, UPVOTE, DOWNVOTE

### Step 4: 리포트 생성

**API:** `POST /api/report/generate`

```
ReportAgent 초기화 (Zep 그래프 + 시뮬레이션 결과)
    ↓
계획 단계: LLM이 리포트 개요 생성
    - [요약, 배경, 주요 발견, 내러티브 진화, ...]
    ↓
섹션별 생성 (ReACT 루프):
    1. LLM: "어떤 정보가 필요한가?"
    2. 도구 호출:
       - search_graph(query) → 그래프 검색 결과
       - get_graph_statistics() → 그래프 통계
       - read_simulation_results() → 에이전트 행동 데이터
    3. LLM: 섹션 내용 작성
    4. 확신도 낮으면 → 추가 도구 호출 후 재작성
    5. 섹션 저장 (section_01.md, section_02.md, ...)
    ↓
최종 리포트 통합 (report.md)
```

**검색 도구 3종:**
- **InsightForge**: LLM이 서브 질문 생성 → 시맨틱 + 엔티티 + 관계 체인 검색
- **PanoramaSearch**: 전체 노드/엣지 (만료된 것 포함) 브로드 검색
- **QuickSearch**: 빠른 시맨틱 검색

### Step 5: 대화형 분석

**API:** `POST /api/report/chat`, `POST /api/simulation/interview/batch`

```
사용자 선택:
    ├─ Report Agent와 대화 → 시뮬레이션 분석 질문
    ├─ 특정 에이전트 인터뷰 → 개별 에이전트와 직접 대화
    └─ 설문 모드 → 다수 에이전트에게 동일 질문 배치 전송
```

---

## 5. API 엔드포인트 목록

### Graph Module (`/api/graph/`)

| 엔드포인트 | 메서드 | 용도 |
|-----------|--------|------|
| `/ontology/generate` | POST | 문서 업로드 → 온톨로지 생성 |
| `/build` | POST | Zep 지식 그래프 구축 (비동기) |
| `/task/<task_id>` | GET | 비동기 작업 진행률 조회 |
| `/data/<graph_id>` | GET | 그래프 노드/엣지 데이터 |
| `/delete/<graph_id>` | DELETE | 그래프 삭제 |
| `/project/<id>` | GET/DELETE | 프로젝트 CRUD |
| `/project/list` | GET | 프로젝트 목록 |
| `/project/<id>/reset` | POST | 프로젝트 리셋 |

### Simulation Module (`/api/simulation/`)

| 엔드포인트 | 메서드 | 용도 |
|-----------|--------|------|
| `/create` | POST | 시뮬레이션 인스턴스 생성 |
| `/prepare` | POST | 에이전트 프로필 & 설정 생성 |
| `/prepare/status` | POST | 준비 진행률 조회 |
| `/start` | POST | 시뮬레이션 실행 시작 |
| `/stop` | POST | 시뮬레이션 중지 |
| `/<sim_id>/run-status` | GET | 실시간 실행 상태 |
| `/<sim_id>/run-status/detail` | GET | 상세 상태 + 최근 행동 |
| `/<sim_id>/posts` | GET | 시뮬레이션 게시물 (페이지네이션) |
| `/<sim_id>/timeline` | GET | 라운드별 타임라인 |
| `/<sim_id>/agent-stats` | GET | 에이전트 활동 통계 |
| `/<sim_id>/actions` | GET | 상세 행동 히스토리 (필터링) |
| `/<sim_id>/profiles` | GET | 생성된 에이전트 프로필 |
| `/<sim_id>/config` | GET | 시뮬레이션 설정 |
| `/interview/batch` | POST | 에이전트 배치 인터뷰 |
| `/history` | GET | 최근 시뮬레이션 목록 |

### Report Module (`/api/report/`)

| 엔드포인트 | 메서드 | 용도 |
|-----------|--------|------|
| `/generate` | POST | 리포트 생성 시작 (비동기) |
| `/generate/status` | POST | 생성 진행률 조회 |
| `/<id>` | GET | 리포트 상세 조회 |
| `/<id>/sections` | GET | 생성된 섹션 목록 |
| `/<id>/download` | GET | 마크다운 다운로드 |
| `/<id>/agent-log` | GET | 에이전트 실행 로그 |
| `/<id>/console-log` | GET | 콘솔 출력 로그 |
| `/chat` | POST | Report Agent와 대화 |
| `/by-simulation/<sim_id>` | GET | 시뮬레이션별 리포트 조회 |

---

## 6. 핵심 클래스 관계도

### 데이터 모델

```
Project
├── project_id, name, status
├── files: [{filename, path, size}]
├── ontology: {entity_types[], edge_types[]}
├── graph_id: str (Zep 그래프)
└── simulation_requirement: str

SimulationState
├── simulation_id, project_id, graph_id
├── status: CREATED → PREPARING → READY → RUNNING → COMPLETED
├── entities_count, profiles_count
└── entity_types: list[str]

Report
├── report_id, simulation_id
├── status: PENDING → GENERATING → COMPLETED/FAILED
├── outline: {sections}
└── markdown_content: str
```

### 서비스 레이어

```
OntologyGenerator          → 문서 분석 → 온톨로지 스키마
GraphBuilderService        → Zep 그래프 생성/관리
ZepEntityReader            → 엔티티 필터링/조회
OasisProfileGenerator      → 에이전트 페르소나 생성
SimulationConfigGenerator  → 시뮬레이션 파라미터 생성
SimulationManager          → 시뮬레이션 상태 관리
SimulationRunner           → OASIS 서브프로세스 실행
ReportAgent                → ReACT 기반 리포트 생성
ZepToolsService            → 그래프 검색 도구 (InsightForge/Panorama/Quick)
ZepGraphMemoryUpdater      → 시뮬레이션 결과 → 그래프 업데이트
```

---

## 7. 설정 및 환경 변수

### 필수

| 변수 | 용도 |
|------|------|
| `LLM_API_KEY` | LLM API 키 (OpenAI 호환 포맷) |
| `LLM_BASE_URL` | LLM API 엔드포인트 |
| `LLM_MODEL_NAME` | 모델 이름 |
| `ZEP_API_KEY` | Zep Cloud API 키 |

### 선택

| 변수 | 기본값 | 용도 |
|------|--------|------|
| `FLASK_HOST` | 0.0.0.0 | 서버 호스트 |
| `FLASK_PORT` | 5001 | 서버 포트 |
| `FLASK_DEBUG` | True | 디버그 모드 |
| `LLM_BOOST_API_KEY` | - | 가속용 별도 LLM |
| `LLM_BOOST_BASE_URL` | - | 가속 LLM 엔드포인트 |
| `LLM_BOOST_MODEL_NAME` | - | 가속 LLM 모델명 |

### Flask 설정 (config.py)

| 설정 | 기본값 | 용도 |
|------|--------|------|
| `MAX_CONTENT_LENGTH` | 50MB | 파일 업로드 제한 |
| `DEFAULT_CHUNK_SIZE` | 500 | 텍스트 청크 크기 |
| `DEFAULT_CHUNK_OVERLAP` | 50 | 청크 오버랩 |

---

## 8. 프론트엔드 라우팅

| 경로 | 컴포넌트 | 단계 |
|------|----------|------|
| `/` | Home.vue | 랜딩 (파일 업로드 + 요구사항 입력) |
| `/process/:projectId` | MainView.vue | Step 1-2 (그래프 + 환경) |
| `/simulation/:simulationId` | SimulationView.vue | Step 2 (환경 준비) |
| `/simulation/:simulationId/start` | SimulationRunView.vue | Step 3 (실행) |
| `/report/:reportId` | ReportView.vue | Step 4 (리포트) |
| `/interaction/:reportId` | InteractionView.vue | Step 5 (인터랙션) |

---

## 9. 실시간 통신 패턴

WebSocket 없이 REST 폴링 기반:
- 그래프 구축: `getTaskStatus` 1~2초 간격
- 시뮬레이션: `getRunStatus` 1~2초 간격
- 리포트: `getReportStatus` 폴링
- 프로필 생성: `getSimulationProfilesRealtime` 스트리밍
- 로그: `getAgentLog`, `getConsoleLog` (from_line 파라미터로 증분 조회)

---

## 10. 에러 처리 & 복원력

- **재시도**: Zep API 최대 3회, 지수 백오프 (2s → 4s → 8s)
- **비동기 작업**: 장기 작업은 task_id 반환 → 클라이언트 폴링
- **프로세스 관리**: 앱 종료 시 시뮬레이션 서브프로세스 정리
- **상태 영속성**: 프로젝트/시뮬레이션 상태를 JSON 파일로 저장
- **Axios 재시도**: 프론트엔드에서 지수 백오프 (1s, 2s, 4s), 최대 3회
