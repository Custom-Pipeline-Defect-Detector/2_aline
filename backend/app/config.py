import os
import logging

def env(name: str, default: str | None = None) -> str:
    v = os.getenv(name)
    if v is None:
        if default is None:
            raise RuntimeError(f"Missing env var: {name}")
        return default
    return v

DATABASE_URL = env("DATABASE_URL", "postgresql+psycopg://aline:aline@localhost:5432/aline")
REDIS_URL = env("REDIS_URL", "redis://localhost:6379/0")

JWT_SECRET = env("JWT_SECRET", "change_me")
JWT_ALG = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))

# In docker we mount storage at /storage
FILE_STORAGE_ROOT = env("FILE_STORAGE_ROOT", "/storage")

# OpenAI-compatible API configuration
OPENAI_API_KEY = env("OPENAI_API_KEY", "your-openai-api-key-here")  # Require API key to be set
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://coding.dashscope.aliyuncs.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "qwen3-coder-plus")

# Remove Ollama fallback configuration
OLLAMA_BASE_URL = None  # No longer used
OLLAMA_MODEL = None     # No longer used

INTERNAL_WATCHER_API_KEY = env("API_KEY_INTERNAL", "internal_watcher_key_change_me")

# Additional robustness settings
REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "60"))  # Default 60 seconds
MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "50"))  # Default 50MB in MB
ALLOWED_FILE_TYPES: str = os.getenv("ALLOWED_FILE_TYPES", "pdf,docx,xlsx,txt,jpg,png,doc,xls")
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
HEALTH_CHECK_INTERVAL: int = int(os.getenv("HEALTH_CHECK_INTERVAL", "30"))  # seconds

# Security settings
SECURE_COOKIES: bool = os.getenv("SECURE_COOKIES", "true").lower() == "true"
MAX_LOGIN_ATTEMPTS: int = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
LOGIN_LOCKOUT_TIME: int = int(os.getenv("LOGIN_LOCKOUT_TIME", "300"))  # seconds

# Configure logging
logging.basicConfig(level=getattr(logging, LOG_LEVEL.upper()))
logger = logging.getLogger(__name__)
logger.info("Application configuration loaded successfully")
