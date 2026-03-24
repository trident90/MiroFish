<div align="center">

<img src="./static/image/MiroFish_logo_compressed.jpeg" alt="MiroFish Logo" width="75%"/>

<em>간결하고 범용적인 군집 지능 엔진, 만물을 예측합니다</em>

[English](./README-EN.md) | [한국어](./README.md)

</div>

## 프로젝트 개요

**MiroFish**는 멀티 에이전트 기술 기반의 차세대 AI 예측 엔진입니다. 현실 세계의 시드 정보(뉴스, 정책, 금융 신호 등)를 추출하여 고충실도 병렬 디지털 세계를 자동 구축합니다. 이 공간에서 수천 개의 독립적 인격, 장기 기억, 행동 논리를 갖춘 에이전트가 자유롭게 상호작용하며 사회적 진화를 수행합니다.

> 시드 자료(데이터 분석 리포트, 뉴스 등)를 업로드하고 자연어로 예측 요구사항을 기술하면,
> MiroFish가 상세한 예측 리포트와 심층 인터랙션이 가능한 디지털 세계를 반환합니다.

이 포크에는 다음 개선사항이 포함되어 있습니다:
- **이중 언어 UI (영어 / 한국어)** — 언어 전환기로 즉시 전환
- **모든 프롬프트 영어 번역** — 중국어 의존성 제거
- **로컬 LLM 지원 (vLLM)** — NVIDIA H100에서 Qwen3-32B 테스트 완료
- **언어 인식 LLM 프롬프트** — 페르소나, 리포트, 대화가 선택 언어에 맞게 생성

## 워크플로우

1. **그래프 구축**: 시드 추출 → Zep Cloud 기반 GraphRAG 구축
2. **환경 설정**: 엔티티 추출 → 페르소나 생성 → 에이전트 설정
3. **시뮬레이션**: 듀얼 플랫폼 병렬 시뮬레이션 (Twitter + Reddit)
4. **리포트 생성**: ReportAgent의 도구 기반 심층 분석
5. **심층 인터랙션**: 시뮬레이션 세계의 에이전트와 대화

## 빠른 시작

### 사전 요구사항

| 도구 | 버전 | 설명 | 확인 |
| ---- | ---- | ---- | ---- |
| **Node.js** | 18+ | 프론트엔드 런타임 | `node -v` |
| **Python** | 3.11~3.12 | 백엔드 런타임 | `python --version` |
| **uv** | 최신 | Python 패키지 매니저 | `uv --version` |

### 1. 환경 변수 설정

```bash
cp .env.example .env
```

**필수 설정:**

```env
# LLM API 설정 (OpenAI 호환 포맷)
# 옵션 A: 클라우드 API (예: Alibaba Qwen-plus)
LLM_API_KEY=your_api_key
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL_NAME=qwen-plus

# 옵션 B: 로컬 vLLM 서버 (예: Qwen3-32B)
LLM_API_KEY=dummy
LLM_BASE_URL=http://<gpu-server-ip>:8001/v1
LLM_MODEL_NAME=Qwen/Qwen3-32B

# Zep Cloud (무료 티어 사용 가능)
ZEP_API_KEY=your_zep_api_key
```

### 2. 의존성 설치

```bash
npm run setup:all
```

### 3. 서비스 시작

```bash
npm run dev
```

- 프론트엔드: `http://localhost:3000`
- 백엔드 API: `http://localhost:5001`

### 4. (선택) vLLM으로 로컬 LLM 실행

NVIDIA H100에서 Qwen3-32B 실행:

```bash
# vLLM 설치
python3 -m venv ~/vllm-env
~/vllm-env/bin/pip install vllm

# 서빙 시작 (단일 GPU, BF16)
~/vllm-env/bin/python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen3-32B \
  --port 8001 \
  --host 0.0.0.0
```

`.env`에서 `LLM_BASE_URL=http://<gpu-server-ip>:8001/v1`로 설정합니다.

### Docker 배포

```bash
cp .env.example .env
docker compose up -d
```

## 다국어 지원 (i18n)

이 포크는 **영어**와 **한국어**를 원클릭으로 지원합니다:

- 네비게이션 바의 **EN | KO** 토글 클릭
- UI 라벨, 상태 메시지, 모든 텍스트가 즉시 전환
- LLM 생성 콘텐츠(페르소나, 대화, 리포트)도 선택 언어에 맞게 생성
- 언어 설정은 브라우저 localStorage에 저장

자세한 구현 내용은 [docs/I18N_PLAN.md](docs/I18N_PLAN.md)를 참조하세요.

## 프로젝트 문서

| 문서 | 설명 |
| ---- | ---- |
| [docs/ANALYSIS.md](docs/ANALYSIS.md) | 소스코드 분석 (백엔드 + 프론트엔드) |
| [docs/I18N_PLAN.md](docs/I18N_PLAN.md) | 다국어 지원 구현 계획 |

## 기술 스택

| 레이어 | 기술 |
| ------ | ---- |
| 프론트엔드 | Vue 3, Vite, D3.js, Axios |
| 백엔드 | Flask, Python 3.12 |
| LLM | OpenAI 호환 API (vLLM / Qwen 등) |
| 지식 그래프 | Zep Cloud |
| 시뮬레이션 엔진 | OASIS (CAMEL-AI) |

## 감사의 말

- **[MiroFish](https://github.com/666ghj/MiroFish)** — Guo Hangjiang의 원본 프로젝트
- **[OASIS](https://github.com/camel-ai/oasis)** — CAMEL-AI의 시뮬레이션 엔진
- **[Zep](https://www.getzep.com/)** — 메모리 및 지식 그래프 플랫폼

## 라이선스

AGPL-3.0
