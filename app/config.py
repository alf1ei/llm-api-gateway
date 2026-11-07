import json
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    gateway_api_key: str = "change-me"
    database_url: str = "sqlite:///./gateway.db"
    request_timeout: float = 60.0
    providers_json: str = "{}"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    def providers(self) -> dict:
        try:
            value = json.loads(self.providers_json)
        except json.JSONDecodeError as exc:
            raise ValueError("PROVIDERS_JSON must contain valid JSON") from exc
        if not isinstance(value, dict):
            raise ValueError("PROVIDERS_JSON must be a JSON object")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
