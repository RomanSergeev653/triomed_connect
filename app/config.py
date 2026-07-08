from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "Triomed Connect"
    token_ttl_seconds: int = 840  # 14 min (< 15 min MyDenta session timeout)
    mydenta_request_timeout: float = 30.0


settings = Settings()
