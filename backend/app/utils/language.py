"""
Language Configuration Module
Provides language-specific settings for LLM prompts, timezone, and locale.
"""

LANGUAGE_CONFIG = {
    "en": {
        "name": "English",
        "use_language_directive": "Use English.",
        "use_language_all_fields": "Use English for all fields",
        "report_language_rule": "The report must be written entirely in English",
        "report_translation_rule": "When quoting content returned by tools, ensure it is in fluent English before writing it into the report",
        "daily_schedule_label": "East Asian (KST/UTC+9)",
        "daily_schedule_group": "East Asian",
        "system_prompt_schedule": "Time configuration must conform to East Asian daily schedule (KST, UTC+9).",
        "agent_schedule_note": "Schedule conforms to East Asian daily routine: Almost no activity 0-5 AM, most active 7-10 PM",
        "default_country": "South Korea",
        "countries": [
            "South Korea", "US", "UK", "Japan", "China",
            "Germany", "France", "Canada", "Australia", "India", "Brazil"
        ],
        "interview_language_note": "",
        "interview_question_directive": "",
        "country_example": 'e.g., "South Korea", "United States"',
    },
    "ko": {
        "name": "Korean",
        "use_language_directive": "한국어를 사용하세요. (Use Korean.)",
        "use_language_all_fields": "모든 필드에 한국어를 사용하세요 (Use Korean for all fields, except gender which must be English: male/female/other)",
        "report_language_rule": "보고서는 반드시 한국어로 작성되어야 합니다 (The report must be written entirely in Korean)",
        "report_translation_rule": "도구에서 반환된 내용을 인용할 때 유창한 한국어로 번역하여 작성하세요",
        "daily_schedule_label": "한국 표준시 (KST/UTC+9)",
        "daily_schedule_group": "한국",
        "system_prompt_schedule": "시간 설정은 한국 일과표를 따라야 합니다 (KST, UTC+9).",
        "agent_schedule_note": "한국 일과에 맞춤: 새벽 0-5시 거의 활동 없음, 저녁 7-10시 가장 활발",
        "default_country": "대한민국",
        "countries": [
            "대한민국", "미국", "영국", "일본", "중국",
            "독일", "프랑스", "캐나다", "호주", "인도", "브라질"
        ],
        "interview_language_note": "답변은 반드시 한국어로 해주세요. (Please answer in Korean.)",
        "interview_question_directive": "질문은 한국어로 생성하세요. (Generate questions in Korean.)",
        "country_example": '예: "대한민국", "미국"',
    }
}

# Korea/East Asia daily schedule (KST, UTC+9) - same hours as China config
TIMEZONE_CONFIG = {
    "dead_hours": [0, 1, 2, 3, 4, 5],
    "morning_hours": [6, 7, 8],
    "work_hours": [9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
    "peak_hours": [19, 20, 21, 22],
    "night_hours": [23],
    "activity_multipliers": {
        "dead": 0.05,
        "morning": 0.4,
        "work": 0.7,
        "peak": 1.5,
        "night": 0.5
    }
}


def get_language(request=None):
    """Extract language from Flask request X-Language header, defaulting to 'en'."""
    if request:
        lang = request.headers.get('X-Language', 'en')
        return lang if lang in LANGUAGE_CONFIG else 'en'
    return 'en'


def get_lang_config(lang: str) -> dict:
    """Get language-specific configuration dict."""
    return LANGUAGE_CONFIG.get(lang, LANGUAGE_CONFIG['en'])
