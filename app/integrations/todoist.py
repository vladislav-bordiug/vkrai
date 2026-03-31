from __future__ import annotations

from app.config import settings
from app.integrations.http_client import HttpClient


class TodoistTool:
    def __init__(self):
        self.http = HttpClient()
        self.base_url = "https://api.todoist.com/api/v1"

    async def list_tasks(self) -> dict:
        headers = {"Authorization": f"Bearer {settings.todoist_api_key}"}
        return await self.http.get(f"{self.base_url}/tasks", headers=headers)

    async def create_task(
        self,
        content: str,
        due_string: str | None = None,
        due_date: str | None = None,
        description: str | None = None,
    ) -> dict:
        headers = {"Authorization": f"Bearer {settings.todoist_api_key}", "Content-Type": "application/json"}
        payload = {"content": content}
        if description:
            payload["description"] = description
        if due_string:
            payload["due_string"] = due_string
        if due_date:
            payload["due_date"] = due_date
        return await self.http.post(f"{self.base_url}/tasks", headers=headers, json_body=payload)
