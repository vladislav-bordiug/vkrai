from __future__ import annotations

from app.config import settings
from app.integrations.http_client import HttpClient


class TavilyTool:
    def __init__(self):
        self.http = HttpClient()
        self.base_url = "https://api.tavily.com"

    async def search(self, query: str, max_results: int = 5) -> dict:
        return await self.http.post(
            f"{self.base_url}/search",
            json_body={
                "api_key": settings.tavily_api_key,
                "query": query,
                "max_results": max_results,
                "include_answer": True,
                "include_raw_content": False,
            },
        )

