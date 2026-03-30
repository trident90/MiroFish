"""
Settings API
Provides endpoints to read and write LLM configuration at runtime.
"""

from flask import request, jsonify

from . import settings_bp
from ..config import Config
from ..utils.settings_store import get_all_settings, save_settings, get_setting
from ..utils.logger import get_logger

logger = get_logger('mirofish.api.settings')

_MASKED = '••••••••'


def _mask(value: str) -> str:
    """Mask an API key, preserving the last 4 characters."""
    if not value or len(value) <= 4:
        return _MASKED
    return _MASKED + value[-4:]


@settings_bp.route('/llm', methods=['GET'])
def get_llm_settings():
    """Return current LLM settings.
    API keys are masked. An 'is_set' flag indicates whether a value is configured.
    """
    stored = get_all_settings()

    def _entry(store_key, env_key, default=''):
        raw = stored.get(store_key) or Config.__dict__.get(env_key, '') or default
        is_set = bool(stored.get(store_key) or Config.__dict__.get(env_key))
        return {
            'value': _mask(raw) if 'API_KEY' in store_key else raw,
            'is_set': is_set,
            'source': 'settings' if stored.get(store_key) else ('env' if Config.__dict__.get(env_key) else 'default'),
        }

    # Resolve effective values
    sim_cfg = Config.get_simulation_llm_config()
    rep_cfg = Config.get_report_llm_config()

    data = {
        'shared': {
            'api_key':   {'value': _mask(Config.LLM_API_KEY or ''), 'is_set': bool(Config.LLM_API_KEY)},
            'base_url':  {'value': Config.LLM_BASE_URL or '', 'is_set': bool(Config.LLM_BASE_URL)},
            'model':     {'value': Config.LLM_MODEL_NAME or '', 'is_set': bool(Config.LLM_MODEL_NAME)},
        },
        'simulation': {
            'api_key':   {
                'value': _mask(stored.get('SIMULATION_LLM_API_KEY', '')),
                'is_set': bool(stored.get('SIMULATION_LLM_API_KEY') or Config.SIMULATION_LLM_API_KEY != Config.LLM_API_KEY),
                'effective': _mask(sim_cfg['api_key'] or ''),
            },
            'base_url':  {
                'value': stored.get('SIMULATION_LLM_BASE_URL', ''),
                'is_set': bool(stored.get('SIMULATION_LLM_BASE_URL')),
                'effective': sim_cfg['base_url'] or '',
            },
            'model':     {
                'value': stored.get('SIMULATION_LLM_MODEL_NAME', ''),
                'is_set': bool(stored.get('SIMULATION_LLM_MODEL_NAME')),
                'effective': sim_cfg['model'] or '',
            },
        },
        'report': {
            'api_key':   {
                'value': _mask(stored.get('REPORT_LLM_API_KEY', '')),
                'is_set': bool(stored.get('REPORT_LLM_API_KEY') or Config.REPORT_LLM_API_KEY != Config.LLM_API_KEY),
                'effective': _mask(rep_cfg['api_key'] or ''),
            },
            'base_url':  {
                'value': stored.get('REPORT_LLM_BASE_URL', ''),
                'is_set': bool(stored.get('REPORT_LLM_BASE_URL')),
                'effective': rep_cfg['base_url'] or '',
            },
            'model':     {
                'value': stored.get('REPORT_LLM_MODEL_NAME', ''),
                'is_set': bool(stored.get('REPORT_LLM_MODEL_NAME')),
                'effective': rep_cfg['model'] or '',
            },
            # Generation parameters
            'max_tokens':         {
                'value': stored.get('REPORT_LLM_MAX_TOKENS', ''),
                'effective': rep_cfg['max_tokens'],
            },
            'temperature':        {
                'value': stored.get('REPORT_LLM_TEMPERATURE', ''),
                'effective': rep_cfg['temperature'],
            },
            'tool_result_limit':  {
                'value': stored.get('REPORT_LLM_TOOL_RESULT_LIMIT', ''),
                'effective': rep_cfg['tool_result_limit'],
            },
            'sim_req_limit':      {
                'value': stored.get('REPORT_LLM_SIM_REQ_LIMIT', ''),
                'effective': rep_cfg['sim_req_limit'],
            },
            'prev_section_limit': {
                'value': stored.get('REPORT_LLM_PREV_SECTION_LIMIT', ''),
                'effective': rep_cfg['prev_section_limit'],
            },
        },
    }

    return jsonify({'success': True, 'data': data})


@settings_bp.route('/llm', methods=['POST'])
def save_llm_settings():
    """Save LLM settings.
    Only SIMULATION_LLM_* and REPORT_LLM_* fields are accepted (not shared/env values).
    Sending an empty string clears the override and reverts to env fallback.
    API keys containing only '•' characters are ignored (masked placeholder, not changed).
    """
    body = request.get_json(silent=True) or {}

    allowed_keys = {
        'SIMULATION_LLM_API_KEY',
        'SIMULATION_LLM_BASE_URL',
        'SIMULATION_LLM_MODEL_NAME',
        'REPORT_LLM_API_KEY',
        'REPORT_LLM_BASE_URL',
        'REPORT_LLM_MODEL_NAME',
        'REPORT_LLM_MAX_TOKENS',
        'REPORT_LLM_TEMPERATURE',
        'REPORT_LLM_TOOL_RESULT_LIMIT',
        'REPORT_LLM_SIM_REQ_LIMIT',
        'REPORT_LLM_PREV_SECTION_LIMIT',
    }

    filtered = {}
    for key, value in body.items():
        if key not in allowed_keys:
            continue
        # Skip masked placeholder values (user didn't change the key)
        if isinstance(value, str) and value.startswith('•'):
            continue
        filtered[key] = value

    save_settings(filtered)
    logger.info(f"LLM settings updated: {list(filtered.keys())}")

    return jsonify({'success': True, 'message': 'Settings saved'})
