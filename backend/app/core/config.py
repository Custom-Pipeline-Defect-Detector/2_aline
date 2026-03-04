from pydantic_settings import BaseSettings
import os


class Settings(BaseSettings):
    model_config = {'protected_namespaces': ()}
    
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./aline.db")
    jwt_secret_key: str = os.getenv("JWT_SECRET", "change-me")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 8
    file_storage_root: str = os.getenv("FILE_STORAGE_ROOT", "./data/aline_docs")
    # Removed Ollama settings since we're using OpenAI only
    celery_broker_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    celery_result_backend: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    run_tasks_inline: bool = True
    # Added for document processing
    allowed_file_types: str = "pdf,docx,xlsx,txt,jpg,png,doc,xls"
    # OpenAI API settings
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_base_url: str = os.getenv("OPENAI_BASE_URL", "https://coding.dashscope.aliyuncs.com/v1")
    model_name: str = os.getenv("MODEL_NAME", "qwen3-coder-plus")
    ai_unrestricted_tool_execution: bool = True
    ai_autonomous_execute: bool = True
    auto_approve_proposals: bool = True


settings = Settings()
