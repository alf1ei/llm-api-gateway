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
            value = __import__("json").loads(self.providers_json)
            return value if isinstance(value, dict) else {}
        except Exception:
            return {}

@lru_cache
def get_settings():
    return Settings()
