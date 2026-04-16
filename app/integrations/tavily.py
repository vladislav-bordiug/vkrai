from __future__ import annotations

import json

from app.config import settings
from app.integrations.http_client import HttpClient

http = HttpClient()
base_url = "https://api.tavily.com"


async def tool_tavily_search(query: str, max_results: int = 5) -> dict:
    """
    tool_tavily_search: Search web for fresh public information.;
    args={
        query: "string, required. What to search on the web.",
        max_results: "integer, optional. Default 5.",
    }
    """

    return json.dumps(
        await http.post(
            f"{base_url}/search",
            json_body={
                "api_key": settings.tavily_api_key,
                "query": query,
                "max_results": max_results,
                "include_answer": True,
                "include_raw_content": False,
            },
        ),
        ensure_ascii=False,
    )
