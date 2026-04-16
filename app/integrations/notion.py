from __future__ import annotations

import json
from datetime import datetime

from app.config import settings
from app.integrations.http_client import HttpClient

DEFAULT_PARENT_PAGE_ID = "334e9061e78b80a78be0f4d9e365415b"

http = HttpClient()
base_url = "https://api.notion.com/v1"


async def tool_notion_search(query: str) -> dict:
    """
    tool_notion_search: Search notes, documents and knowledge base in Notion workspace.;
    args={
        query: "string, required. Search text."
    }
    """

    headers = {
        "Authorization": f"Bearer {settings.notion_api_key}",
        "Notion-Version": settings.notion_api_version,
        "Content-Type": "application/json",
    }

    return json.dumps(
        await http.post(
            f"{base_url}/search",
            headers=headers,
            json_body={
                "query": query,
                "sort": {
                    "direction": "descending",
                    "timestamp": "last_edited_time",
                },
            },
        ),
        ensure_ascii=False,
    )


async def tool_notion_create_note(content: str, title: str | None = None) -> dict:
    """
    tool_notion_create_note: Create a quick note page in Notion from plain text content.;
    args={
        content: "string, required. Note body text.",
        title: "string, optional. Note title. Default first 120 symbols of content.",
    }
    """

    headers = {
        "Authorization": f"Bearer {settings.notion_api_key}",
        "Notion-Version": settings.notion_api_version,
        "Content-Type": "application/json",
    }

    inferred_title = title or build_title(content)
    parent_page_id = await resolve_default_parent_page_id()

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

    return json.dumps(
        await http.post(f"{base_url}/pages", headers=headers, json_body=payload),
        ensure_ascii=False,
    )


def resolve_default_parent_page_id() -> str:
    if not DEFAULT_PARENT_PAGE_ID:
        raise ValueError("DEFAULT_PARENT_PAGE_ID is not configured.")
    return DEFAULT_PARENT_PAGE_ID


def build_title(content: str) -> str:
    first_line = next(
        (line.strip() for line in content.splitlines() if line.strip()), ""
    )
    if first_line:
        return first_line[:120]
    return f"Quick note {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"
