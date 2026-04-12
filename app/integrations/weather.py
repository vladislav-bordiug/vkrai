from __future__ import annotations

from datetime import datetime, timezone

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

    async def weather_for_datetime(
        self,
        city: str,
        target_iso: str,
        units: str = "metric",
        lang: str = "ru",
    ) -> dict:
        forecast = await self.http.get(
            f"{self.base_url}/forecast",
            params={
                "q": city,
                "appid": settings.openweathermap_api_key,
                "units": units,
                "lang": lang,
            },
        )

        target_dt = self._parse_iso_datetime(target_iso)
        items = forecast.get("list") or []
        if not items:
            return {
                "target_iso": target_iso,
                "message": "No forecast data available.",
                "raw": forecast,
            }

        best_item = None
        best_delta = None
        for item in items:
            dt_txt = item.get("dt_txt")
            if not isinstance(dt_txt, str):
                continue
            try:
                item_dt = datetime.strptime(dt_txt, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            except ValueError:
                continue

            delta = abs((item_dt - target_dt).total_seconds())
            if best_delta is None or delta < best_delta:
                best_delta = delta
                best_item = item

        return {
            "target_iso": target_iso,
            "closest_forecast": best_item,
            "closest_delta_hours": round((best_delta or 0) / 3600, 2),
            "note": "OpenWeather forecast endpoint provides 5-day forecast with 3-hour granularity.",
        }

    @staticmethod
    def _parse_iso_datetime(value: str) -> datetime:
        normalized = value.strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

