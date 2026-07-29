from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "Triomed Connect"
    token_ttl_seconds: int = 840  # 14 min (< 15 min MyDenta session timeout)
    mydenta_request_timeout: float = 30.0
    mydenta_verify_ssl: bool = False  # MyDenta uses self-signed / invalid cert (curl -k)

    # CORS for amoCRM / Kommo widgets (browser → Connect)
    cors_allow_origins: list[str] = [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]
    cors_allow_origin_regex: str = r"https://.*\.(amocrm\.(ru|com)|kommo\.com)"


settings = Settings()
