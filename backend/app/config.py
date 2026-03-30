"""
Configuration management
Loads configuration uniformly from the .env file in the project root directory
"""

import os
from dotenv import load_dotenv

# Load the .env file from the project root directory
# Path: MiroFish/.env (relative to backend/app/config.py)
project_root_env = os.path.join(os.path.dirname(__file__), '../../.env')

if os.path.exists(project_root_env):
    load_dotenv(project_root_env, override=True)
else:
    # If root directory has no .env, try loading environment variables (for production)
    load_dotenv(override=True)


class Config:
    """Flask configuration class"""

    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY', 'mirofish-secret-key')
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'

    # JSON configuration - Disable ASCII escaping to display non-ASCII characters directly (instead of \uXXXX format)
    JSON_AS_ASCII = False

    # LLM configuration (unified OpenAI format) — shared fallback
    LLM_API_KEY = os.environ.get('LLM_API_KEY')
    LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'https://api.openai.com/v1')
    LLM_MODEL_NAME = os.environ.get('LLM_MODEL_NAME', 'gpt-4o-mini')

    # Simulation LLM (ontology, profile, simulation config generation)
    # Falls back to LLM_* if not set
    SIMULATION_LLM_API_KEY = os.environ.get('SIMULATION_LLM_API_KEY') or os.environ.get('LLM_API_KEY')
    SIMULATION_LLM_BASE_URL = os.environ.get('SIMULATION_LLM_BASE_URL') or os.environ.get('LLM_BASE_URL', 'https://api.openai.com/v1')
    SIMULATION_LLM_MODEL_NAME = os.environ.get('SIMULATION_LLM_MODEL_NAME') or os.environ.get('LLM_MODEL_NAME', 'gpt-4o-mini')

    # Report LLM (report generation — benefits from large context window)
    # Falls back to LLM_* if not set
    REPORT_LLM_API_KEY = os.environ.get('REPORT_LLM_API_KEY') or os.environ.get('LLM_API_KEY')
    REPORT_LLM_BASE_URL = os.environ.get('REPORT_LLM_BASE_URL') or os.environ.get('LLM_BASE_URL', 'https://api.openai.com/v1')
    REPORT_LLM_MODEL_NAME = os.environ.get('REPORT_LLM_MODEL_NAME') or os.environ.get('LLM_MODEL_NAME', 'gpt-4o-mini')

    # Zep configuration
    ZEP_API_KEY = os.environ.get('ZEP_API_KEY')

    # File upload configuration
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '../uploads')
    ALLOWED_EXTENSIONS = {'pdf', 'md', 'txt', 'markdown'}

    # Text processing configuration
    DEFAULT_CHUNK_SIZE = 500  # Default chunk size
    DEFAULT_CHUNK_OVERLAP = 50  # Default overlap size

    # OASIS simulation configuration
    OASIS_DEFAULT_MAX_ROUNDS = int(os.environ.get('OASIS_DEFAULT_MAX_ROUNDS', '10'))
    OASIS_SIMULATION_DATA_DIR = os.path.join(os.path.dirname(__file__), '../uploads/simulations')

    # OASIS platform available actions configuration
    OASIS_TWITTER_ACTIONS = [
        'CREATE_POST', 'LIKE_POST', 'REPOST', 'FOLLOW', 'DO_NOTHING', 'QUOTE_POST'
    ]
    OASIS_REDDIT_ACTIONS = [
        'LIKE_POST', 'DISLIKE_POST', 'CREATE_POST', 'CREATE_COMMENT',
        'LIKE_COMMENT', 'DISLIKE_COMMENT', 'SEARCH_POSTS', 'SEARCH_USER',
        'TREND', 'REFRESH', 'DO_NOTHING', 'FOLLOW', 'MUTE'
    ]

    # Report Agent configuration
    REPORT_AGENT_MAX_TOOL_CALLS = int(os.environ.get('REPORT_AGENT_MAX_TOOL_CALLS', '5'))
    REPORT_AGENT_MAX_REFLECTION_ROUNDS = int(os.environ.get('REPORT_AGENT_MAX_REFLECTION_ROUNDS', '2'))
    REPORT_AGENT_TEMPERATURE = float(os.environ.get('REPORT_AGENT_TEMPERATURE', '0.5'))

    @classmethod
    def validate(cls):
        """Validate required configuration"""
        errors = []
        if not cls.LLM_API_KEY:
            errors.append("LLM_API_KEY not configured")
        if not cls.ZEP_API_KEY:
            errors.append("ZEP_API_KEY not configured")
        return errors

    @classmethod
    def get_simulation_llm_config(cls) -> dict:
        """Return LLM config for simulation role.
        Priority: settings_store > SIMULATION_LLM_* env > LLM_* env"""
        from .utils.settings_store import get_setting
        return {
            "api_key": get_setting('SIMULATION_LLM_API_KEY', cls.LLM_API_KEY),
            "base_url": get_setting('SIMULATION_LLM_BASE_URL', cls.LLM_BASE_URL),
            "model": get_setting('SIMULATION_LLM_MODEL_NAME', cls.LLM_MODEL_NAME),
        }

    @classmethod
    def get_report_llm_config(cls) -> dict:
        """Return LLM config for report role.
        Priority: settings_store > REPORT_LLM_* env > LLM_* env

        Generation parameters:
          max_tokens         — max output tokens per section (default 4096)
          temperature        — sampling temperature (default 0.5)
          tool_result_limit  — max chars per tool response before truncation (default 3000)
          sim_req_limit      — max chars of simulation_requirement in system prompt (default 800)
          prev_section_limit — max chars per previous section in context (default 1000)
        """
        from .utils.settings_store import get_setting
        return {
            "api_key":            get_setting('REPORT_LLM_API_KEY', cls.LLM_API_KEY),
            "base_url":           get_setting('REPORT_LLM_BASE_URL', cls.LLM_BASE_URL),
            "model":              get_setting('REPORT_LLM_MODEL_NAME', cls.LLM_MODEL_NAME),
            "max_tokens":         int(get_setting('REPORT_LLM_MAX_TOKENS', '4096')),
            "temperature":        float(get_setting('REPORT_LLM_TEMPERATURE', '0.5')),
            "tool_result_limit":  int(get_setting('REPORT_LLM_TOOL_RESULT_LIMIT', '3000')),
            "sim_req_limit":      int(get_setting('REPORT_LLM_SIM_REQ_LIMIT', '800')),
            "prev_section_limit": int(get_setting('REPORT_LLM_PREV_SECTION_LIMIT', '1000')),
        }
