"""
LLM Settings Store
Persists LLM configuration to a JSON file so changes take effect
without restarting the server. Settings in this file override .env values.
"""

import json
import os
from typing import Dict, Any

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), '../../uploads/llm_settings.json')


def _load() -> Dict[str, Any]:
    """Load settings from file. Returns empty dict if file doesn't exist."""
    path = os.path.abspath(SETTINGS_FILE)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def _save(data: Dict[str, Any]) -> None:
    """Write settings to file."""
    path = os.path.abspath(SETTINGS_FILE)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_setting(key: str, fallback: str = None) -> str:
    """Return a single setting value, falling back to env or default."""
    return _load().get(key) or os.environ.get(key) or fallback


def get_all_settings() -> Dict[str, Any]:
    """Return all persisted settings (raw, not merged with env)."""
    return _load()


def save_settings(data: Dict[str, Any]) -> None:
    """Merge and persist settings. Empty string values are removed (revert to env)."""
    current = _load()
    for key, value in data.items():
        if value == '' or value is None:
            current.pop(key, None)
        else:
            current[key] = value
    _save(current)
