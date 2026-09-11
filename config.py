import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_base_url: str = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")
    main_model: str = os.getenv("MAIN_MODEL", "openai/gpt-oss-120b")
    guard_model: str = os.getenv("GUARD_MODEL", "qwen/qwen3.8-27b")
    session_secret: str = os.getenv("SESSION_SECRET", "development-only-secret")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
