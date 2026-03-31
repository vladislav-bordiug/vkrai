from __future__ import annotations

from app.config import settings
from app.integrations.http_client import HttpClient


class OpenWeatherTool:
    def __init__(self):
        self.http = HttpClient()
        self.base_url = "https://api.openweathermap.org/data/2.5"

    async def current_weather(self, city: str, units: str = "metric", lang: str = "ru") -> dict:
        return await self.http.get(
            f"{self.base_url}/weather",
            params={
                "q": city,
                "appid": settings.openweathermap_api_key,
                "units": units,
                "lang": lang,
            },
        )

