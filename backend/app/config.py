from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    gonka_api_key: str
    gonka_api_url: str = "https://api.gonkarouter.io/v1"

    gonka_model_deepseek: str
    gonka_model_minimax: str
    gonka_model_kimi: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()