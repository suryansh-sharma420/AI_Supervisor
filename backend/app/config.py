from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    TEST_DATABASE_URL: str
    GROQ_API_KEY: str = ""
    GROQ_CLASSIFIER_MODEL: str = "llama-3.1-8b-instant"
    GROQ_AGENT_MODEL: str = "llama-3.3-70b-versatile"
    ENVIRONMENT: str = "development"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
