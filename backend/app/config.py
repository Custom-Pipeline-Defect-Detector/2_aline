import os

def env(name: str, default: str | None = None) -> str:
    v = os.getenv(name)
    if v is None:
        if default is None:
            raise RuntimeError(f"Missing env var: {name}")
        return default
    return v

DATABASE_URL = env("DATABASE_URL", "postgresql+psycopg://aline:alinepass@localhost:5432/aline")
REDIS_URL = env("REDIS_URL", "redis://localhost:6379/0")

JWT_SECRET = env("JWT_SECRET", "change_me")
JWT_ALG = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))

# In docker we mount storage at /storage
FILE_STORAGE_ROOT = env("FILE_STORAGE_ROOT", "/storage")

OLLAMA_BASE_URL = env("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = env("OLLAMA_MODEL", "qwen2.5-coder:7b")

INTERNAL_WATCHER_API_KEY = env("API_KEY_INTERNAL", "internal_watcher_key_change_me")
