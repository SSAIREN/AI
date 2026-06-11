from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "SSIREN-AI Agent Server"
    API_V1_STR: str = "/api/v1"
    
    # Application Mode
    DEBUG: bool = True
    
    # API Keys
    OPENAI_API_KEY: str = ""
    
    # Pydantic Settings Configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
