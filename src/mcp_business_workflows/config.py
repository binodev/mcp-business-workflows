from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"

    # Authentication
    api_token: str = Field(..., alias="MCP_API_TOKEN")

    # GitHub
    github_token: str = Field("", alias="GITHUB_TOKEN")
    github_default_repo: str = Field("", alias="GITHUB_DEFAULT_REPO")

    # Webhook
    webhook_default_url: str = Field("", alias="WEBHOOK_DEFAULT_URL")

    # Notes store
    notes_store_path: str = Field("./data/notes.json", alias="NOTES_STORE_PATH")


settings = Settings()
