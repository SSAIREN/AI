from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "SSIREN-AI Agent Server"
    API_V1_STR: str = "/api/v1"
    
    # Application Mode
    DEBUG: bool = True
    
    # API Keys
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-5-nano"

    # Optional Pipeline A external action server
    SPRING_API_URL: str = ""
    SPRING_INTERNAL_API_KEY: str = ""

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, value):
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "prod", "production", "false", "0", "no"}:
                return False
            if normalized in {"debug", "dev", "development", "true", "1", "yes"}:
                return True
        return value
    
    # Pydantic Settings Configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
