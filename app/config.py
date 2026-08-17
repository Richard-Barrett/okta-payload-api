from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    github_owner: str
    github_repo: str
    github_token: str = Field(repr=False)
    github_base_branch: str = "main"
    github_catalog_path: str = "catalog/saml_apps.json"
    github_api_url: str = "https://api.github.com"
    github_api_version: str = "2026-03-10"
    app_log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
