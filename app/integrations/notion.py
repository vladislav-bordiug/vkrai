from __future__ import annotations

from datetime import datetime

from app.config import settings
from app.integrations.http_client import HttpClient


class NotionTool:
    DEFAULT_PARENT_PAGE_ID = "334e9061e78b80a78be0f4d9e365415b"

    def __init__(self):
        self.http = HttpClient()
        self.base_url = "https://api.notion.com/v1"

    async def search(self, query: str) -> dict:
        headers = {
            "Authorization": f"Bearer {settings.notion_api_key}",
            "Notion-Version": settings.notion_api_version,
            "Content-Type": "application/json",
        }
        return await self.http.post(
            f"{self.base_url}/search",
            headers=headers,
            json_body={"query": query, "sort": {"direction": "descending", "timestamp": "last_edited_time"}},
        )

    async def create_note(self, content: str, title: str | None = None) -> dict:
        headers = {
            "Authorization": f"Bearer {settings.notion_api_key}",
            "Notion-Version": settings.notion_api_version,
            "Content-Type": "application/json",
        }

        inferred_title = title or self._build_title(content)
        parent_page_id = await self._resolve_default_parent_page_id(inferred_title)

        paragraphs = [line.strip() for line in content.splitlines() if line.strip()]
        if not paragraphs:
            paragraphs = [content.strip() or "Empty note"]

        children = [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": paragraph[:2000]}}],
                },
            }
            for paragraph in paragraphs
        ]

        payload = {
            "parent": {"page_id": parent_page_id},
            "properties": {
                "title": {
                    "title": [
                        {
                            "type": "text",
                            "text": {"content": inferred_title[:2000]},
                        }
                    ]
                }
            },
            "children": children,
        }
        return await self.http.post(f"{self.base_url}/pages", headers=headers, json_body=payload)

    async def _resolve_default_parent_page_id(self, query_hint: str) -> str:
        _ = query_hint
        if not self.DEFAULT_PARENT_PAGE_ID:
            raise ValueError("DEFAULT_PARENT_PAGE_ID is not configured.")
        return self.DEFAULT_PARENT_PAGE_ID

    @staticmethod
    def _build_title(content: str) -> str:
        first_line = next((line.strip() for line in content.splitlines() if line.strip()), "")
        if first_line:
            return first_line[:120]
        return f"Quick note {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"
