from pydantic_settings import BaseSettings
import os


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://aline:aline@localhost:5432/aline"
    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 8
    file_storage_root: str = "/data/aline_docs"
    # Removed Ollama settings since we're using OpenAI only
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    run_tasks_inline: bool = True
    # Added for document processing
    allowed_file_types: str = "pdf,docx,xlsx,txt,jpg,png,doc,xls"
    # OpenAI API settings
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_base_url: str = "https://coding.dashscope.aliyuncs.com/v1"
    model_name: str = "qwen3-coder-plus"
    ai_unrestricted_tool_execution: bool = True
    ai_autonomous_execute: bool = True
    auto_approve_proposals: bool = True


settings = Settings()
