from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str
    app_env: str
    app_host: str
    app_port: int
    cors_origins: str
    database_url: str

    ai_api_key: str
    ai_model: str
    ai_base_url: str

    notion_api_key: str
    notion_api_version: str

    openweathermap_api_key: str

    tavily_api_key: str

    todoist_api_key: str

    google_client_id: str
    google_client_secret: str
    google_refresh_token: str
    google_token_url: str
    gmail_base_url: str

    google_calendar_base_url: str
    google_calendar_default_timezone: str

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [
            origin.strip() for origin in self.cors_origins.split(",") if origin.strip()
        ]


settings = Settings()
