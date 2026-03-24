# MiroFish Internationalization (i18n) Implementation Plan

## Overview

Add English/Korean bilingual support to MiroFish. When Korean is selected, ALL output — UI text, LLM-generated personas, simulation conversations, reports, and interview responses — must be in Korean.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Frontend (Vue 3)                                       │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────────┐ │
│  │ en.json   │  │ ko.json   │  │ useI18n() composable │ │
│  └──────────┘  └──────────┘  └───────────────────────┘ │
│       │              │              │                    │
│       └──────────────┴──────────────┘                   │
│                      │                                   │
│            localStorage('mirofish_lang')                 │
│                      │                                   │
│            axios header: X-Language: en|ko               │
└──────────────────────┼──────────────────────────────────┘
                       │
┌──────────────────────┼──────────────────────────────────┐
│  Backend (Flask)     │                                   │
│                      ▼                                   │
│            Flask g.language (from X-Language header)     │
│                      │                                   │
│            ┌─────────┴─────────┐                        │
│            │  language.py      │                        │
│            │  LANGUAGE_CONFIG  │                        │
│            └─────────┬─────────┘                        │
│                      │                                   │
│    ┌─────────┬───────┼───────┬──────────┐              │
│    ▼         ▼       ▼       ▼          ▼              │
│ profile   sim_cfg  report  zep_tools  sim_api          │
│ generator generator agent   service   endpoints        │
└─────────────────────────────────────────────────────────┘
```

---

## Phase 1: Frontend i18n Infrastructure

### 1a. Translation Files (NEW)

**`frontend/src/i18n/en.json`** — English translation map
**`frontend/src/i18n/ko.json`** — Korean translation map

Structure:
```json
{
  "nav.brand": "MIROFISH",
  "home.tagline": "A Concise and Universal Swarm Intelligence Engine",
  "home.title.line1": "Upload Any Report",
  "home.title.line2": "Simulate the Future Instantly",
  "status.completed": "Completed",
  "status.generating": "Generating",
  "status.waiting": "Waiting",
  "btn.startEngine": "Start Engine",
  "steps.graphConstruction": "Graph Construction",
  "steps.envSetup": "Environment Setup",
  "steps.startSim": "Start Simulation",
  "steps.reportGen": "Report Generation",
  "steps.deepInteraction": "Deep Interaction",
  ...
}
```

Korean example:
```json
{
  "nav.brand": "MIROFISH",
  "home.tagline": "간결하고 범용적인 군집 지능 엔진",
  "home.title.line1": "보고서를 업로드하면",
  "home.title.line2": "즉시 미래를 시뮬레이션합니다",
  "status.completed": "완료",
  "status.generating": "생성 중",
  "status.waiting": "대기 중",
  "btn.startEngine": "엔진 시작",
  "steps.graphConstruction": "그래프 구축",
  "steps.envSetup": "환경 설정",
  "steps.startSim": "시뮬레이션 시작",
  "steps.reportGen": "리포트 생성",
  "steps.deepInteraction": "심층 인터랙션",
  ...
}
```

### 1b. i18n Composable (NEW)

**`frontend/src/i18n/index.js`**

```javascript
import { ref } from 'vue'
import en from './en.json'
import ko from './ko.json'

const messages = { en, ko }
const currentLocale = ref(localStorage.getItem('mirofish_lang') || 'en')

export function useI18n() {
  function t(key) {
    return messages[currentLocale.value]?.[key]
      || messages['en']?.[key]
      || key
  }

  function setLocale(lang) {
    currentLocale.value = lang
    localStorage.setItem('mirofish_lang', lang)
  }

  function getLocale() {
    return currentLocale.value
  }

  return { t, setLocale, getLocale, locale: currentLocale }
}
```

- No external dependency (vue-i18n 불필요, 2개 언어에 경량 솔루션)
- `ref` 기반 반응형 — 언어 전환 시 UI 즉시 업데이트
- 영어 fallback — 한국어 번역 누락 시 영어 표시

### 1c. Language Switcher (MODIFY)

**Files:**
- `frontend/src/views/Home.vue` — 네비게이션 바
- `frontend/src/views/MainView.vue` — 헤더
- `frontend/src/views/SimulationView.vue` — 헤더
- `frontend/src/views/SimulationRunView.vue` — 헤더
- `frontend/src/views/ReportView.vue` — 헤더
- `frontend/src/views/InteractionView.vue` — 헤더

EN | KO 토글 버튼 추가. `setLocale()` 호출로 전환.

### 1d. Replace Hardcoded Strings (MODIFY ~15 files)

All Vue components with hardcoded English text → `t('key')` calls.

| File | Approx. Strings | Priority |
|------|-----------------|----------|
| `Home.vue` | ~30 | High |
| `MainView.vue` | ~15 | High |
| `Step1GraphBuild.vue` | ~15 | Medium |
| `Step2EnvSetup.vue` | ~15 | Medium |
| `Step3Simulation.vue` | ~10 | Medium |
| `Step4Report.vue` | ~10 | Medium |
| `Step5Interaction.vue` | ~10 | Medium |
| `GraphPanel.vue` | ~5 | Low |
| `HistoryDatabase.vue` | ~5 | Low |
| `Process.vue` | ~3 | Low |
| Other views | ~15 | Low |

### 1e. API Language Header (MODIFY)

**`frontend/src/api/index.js`** — axios request interceptor

```javascript
service.interceptors.request.use(config => {
  config.headers['X-Language'] = localStorage.getItem('mirofish_lang') || 'en'
  return config
})
```

모든 API 호출이 자동으로 언어 설정을 백엔드에 전달.

---

## Phase 2: Backend Language Module

### 2a. Language Config Module (NEW)

**`backend/app/utils/language.py`**

```python
LANGUAGE_CONFIG = {
    "en": {
        "name": "English",
        "use_language_directive": "Use English.",
        "use_language_all_fields": "Use English for all fields",
        "report_language_rule": "The report must be written entirely in English",
        "report_translation_rule": "ensure it is in fluent English",
        "timezone_label": "UTC+9 (KST/Beijing Time)",
        "daily_schedule_group": "East Asian",
        "system_prompt_schedule": "Time configuration must conform to East Asian daily schedule.",
        "default_country": "South Korea",
        "countries": ["South Korea", "US", "UK", "Japan", "China",
                      "Germany", "France", "Canada", "Australia"],
        "interview_language_note": "",
    },
    "ko": {
        "name": "Korean",
        "use_language_directive": "한국어를 사용하세요.",
        "use_language_all_fields": "모든 필드에 한국어를 사용하세요",
        "report_language_rule": "보고서는 반드시 한국어로 작성되어야 합니다",
        "report_translation_rule": "도구에서 반환된 내용을 인용할 때 유창한 한국어로 작성하세요",
        "timezone_label": "한국 표준시 (KST)",
        "daily_schedule_group": "한국",
        "system_prompt_schedule": "시간 설정은 한국 일과표를 따라야 합니다.",
        "default_country": "대한민국",
        "countries": ["대한민국", "미국", "영국", "일본", "중국",
                      "독일", "프랑스", "캐나다", "호주"],
        "interview_language_note": "답변은 반드시 한국어로 해주세요.",
    }
}

def get_language(request=None):
    """Extract language from Flask request header."""
    if request:
        lang = request.headers.get('X-Language', 'en')
        return lang if lang in LANGUAGE_CONFIG else 'en'
    return 'en'

def get_lang_config(lang: str) -> dict:
    return LANGUAGE_CONFIG.get(lang, LANGUAGE_CONFIG['en'])
```

### 2b. Flask Request Context (MODIFY)

**`backend/app/__init__.py`**

```python
from flask import g
from .utils.language import get_language

@app.before_request
def set_language():
    g.language = get_language(request)
```

모든 엔드포인트에서 `g.language`로 현재 언어 접근 가능.

---

## Phase 3: Backend Service Modifications

### 3a. oasis_profile_generator.py (MODIFY 4개소)

| Line | Current | Change |
|------|---------|--------|
| 673 | `"...Use English."` | `f"...{lang_config['use_language_directive']}"` |
| 713 | `country: "China"` example | `country: lang_config['default_country']` example |
| 720 | `"Use English for all fields"` | `lang_config['use_language_all_fields']` |
| 769 | `"Use English for all fields"` | `lang_config['use_language_all_fields']` |
| 816, 828 | `"country": "China"` | `"country": lang_config['default_country']` |
| 163-166 | Hardcoded COUNTRIES list | `lang_config['countries']` |

**Note:** gender 필드는 OASIS 호환을 위해 항상 영어 ("male"/"female"/"other") 유지.
**Note:** 온톨로지 엔티티/관계 이름은 기술 식별자이므로 항상 영어 유지.

### 3b. simulation_config_generator.py (MODIFY 5개소)

| Line | Current | Change |
|------|---------|--------|
| 27-47 | `CHINA_TIMEZONE_CONFIG` | 유지 + `KOREA_TIMEZONE_CONFIG` 추가 (동일 시간대) |
| 84 | `"based on Chinese daily schedule"` | `f"based on {lang_config['daily_schedule_group']} daily schedule"` |
| 550 | `"Chinese, Beijing Time"` | `lang_config['daily_schedule_group']` + `lang_config['timezone_label']` |
| 587 | `"Chinese daily schedule"` | `lang_config['system_prompt_schedule']` |
| 841 | `"Chinese daily routine"` | `lang_config['daily_schedule_group']` |
| 866 | `"Chinese daily schedule"` | `lang_config['system_prompt_schedule']` |

### 3c. report_agent.py (MODIFY 1개소)

| Line | Current | Change |
|------|---------|--------|
| 654-659 | `"report must be written entirely in English"` | `lang_config['report_language_rule']` |
| 657 | `"ensure it is in fluent English"` | `lang_config['report_translation_rule']` |

### 3d. zep_tools.py (MODIFY 2개소)

| Line | Current | Change |
|------|---------|--------|
| 1644-1654 | Interview question generation (no language directive) | Append language directive |
| 1352-1362 | Interview prompt prefix | Append `lang_config['interview_language_note']` |

### 3e. API Endpoints (MODIFY 2개소)

**`backend/app/api/simulation.py`:**
- 서비스 객체 생성 시 `g.language` 전달

**`backend/app/api/report.py`:**
- `ReportAgent` 생성 시 `g.language` 전달

---

## Phase 4: Testing

### Test Matrix

| Scenario | English | Korean |
|----------|---------|--------|
| UI labels & buttons | ✅ 기존 동작 유지 | 한국어 표시 확인 |
| Ontology generation | 엔티티명 영어 | 엔티티명 영어 (변경 없음) |
| Agent persona | 영어 bio/persona | 한국어 bio/persona |
| Simulation conversations | 영어 게시물/댓글 | 한국어 게시물/댓글 |
| Report generation | 영어 리포트 | 한국어 리포트 |
| Interview responses | 영어 답변 | 한국어 답변 |
| Language switching | 즉시 반영 | 즉시 반영 |
| Default country | South Korea | 대한민국 |
| Timezone | KST | KST |

### Verification Steps

1. 브라우저에서 KO 선택 → 모든 UI 텍스트 한국어 확인
2. 시드 문서 업로드 → 온톨로지 생성 (엔티티명은 영어 유지)
3. 에이전트 프로필 생성 → bio, persona 한국어 확인
4. 시뮬레이션 실행 → 게시물/댓글 한국어 확인
5. 리포트 생성 → 전체 한국어 확인
6. 인터뷰 → 한국어 질문 및 답변 확인
7. EN 전환 → 모든 것이 영어로 복귀 확인

---

## File Change Summary

| Category | Files | New | Modified |
|----------|-------|-----|----------|
| Frontend i18n | 3 | 3 (en.json, ko.json, index.js) | 0 |
| Frontend Views | 6 | 0 | 6 (language switcher) |
| Frontend Components | 9 | 0 | 9 (string replacement) |
| Frontend API | 1 | 0 | 1 (X-Language header) |
| Backend Language | 1 | 1 (language.py) | 0 |
| Backend Init | 1 | 0 | 1 (g.language) |
| Backend Services | 4 | 0 | 4 (profile, sim_cfg, report, zep) |
| Backend API | 2 | 0 | 2 (simulation, report) |
| **Total** | **27** | **4** | **23** |

---

## Key Design Decisions

1. **Custom i18n vs vue-i18n**: 2개 언어, ~100개 문자열 → 30줄 composable이 더 경량. 추후 vue-i18n 마이그레이션 용이 (JSON 호환).
2. **X-Language 헤더**: API body 수정 없이 모든 요청에 자동 전달.
3. **Flask g.language**: 서비스 생성자 시그니처 최소 변경.
4. **이중 언어 프롬프트**: 한국어 지시에 영어 괄호 주석 추가 — LLM의 한국어 instruction following 보강.
5. **엔티티명 영어 유지**: 기술 식별자로서 Zep API/OASIS 호환성 보장.
6. **한국 타임존**: 중국과 거의 동일 (UTC+8/+9, 유사한 일과표) → 라벨만 변경.
