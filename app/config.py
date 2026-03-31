from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Local AI Assistant"
    app_env: str = "dev"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    database_url: str = "postgresql+asyncpg://assistant:assistant@localhost:5432/assistant"

    openai_api_key: str = ""
    openai_model: str = "gpt-5-mini"

    notion_api_key: str = ""
    notion_api_version: str = "2022-06-28"

    openweathermap_api_key: str = ""

    tavily_api_key: str = ""

    todoist_api_key: str = ""

    google_client_id: str = ""
    google_client_secret: str = ""
    google_refresh_token: str = ""
    google_token_url: str = "https://oauth2.googleapis.com/token"
    gmail_base_url: str = "https://gmail.googleapis.com/gmail/v1"

    google_calendar_base_url: str = "https://www.googleapis.com/calendar/v3"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()

