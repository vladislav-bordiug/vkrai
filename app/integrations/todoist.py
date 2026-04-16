from __future__ import annotations

import json

from app.config import settings
from app.integrations.http_client import HttpClient

http = HttpClient()
base_url = "https://api.todoist.com/api/v1"


async def tool_todoist_list_tasks() -> dict:
    """
    tool_todoist_list_tasks: List current Todoist tasks.;
    args={
    }
    """

    headers = {"Authorization": f"Bearer {settings.todoist_api_key}"}

    return json.dumps(
        await http.get(f"{base_url}/tasks", headers=headers),
        ensure_ascii=False,
    )


async def tool_todoist_create_task(
    content: str,
    due_string: str | None = None,
    due_date: str | None = None,
    description: str | None = None,
) -> dict:
    """
    tool_todoist_create_task: Create a new task in Todoist.;
    args={
        content: "string, required. Task title.",
        due_string: "string, optional. Natural language due date.",
        due_date: "string, optional. Due date in YYYY-MM-DD.",
        description: "string, optional. Task description/details.",
    }
    """

    headers = {
        "Authorization": f"Bearer {settings.todoist_api_key}",
        "Content-Type": "application/json",
    }
    payload = {"content": content}
    if description:
        payload["description"] = description
    if due_string:
        payload["due_string"] = due_string
    if due_date:
        payload["due_date"] = due_date

    return json.dumps(
        await http.post(f"{base_url}/tasks", headers=headers, json_body=payload),
        ensure_ascii=False,
    )


async def tool_todoist_update_task(
    task_id: str,
    content: str | None = None,
    due_string: str | None = None,
    due_date: str | None = None,
    description: str | None = None,
) -> dict:
    """
    tool_todoist_update_task: Update existing Todoist task fields.;
    args={
        task_id: "string, required. Todoist task id.",
        content: "string, optional. New task title.",
        due_string: "string, optional. Natural language due date.",
        due_date: "string, optional. Due date in YYYY-MM-DD.",
        description: "string, optional. Task description/details.",
    }
    """

    headers = {
        "Authorization": f"Bearer {settings.todoist_api_key}",
        "Content-Type": "application/json",
    }
    payload: dict[str, str] = {}
    if content:
        payload["content"] = content
    if description is not None:
        payload["description"] = description
    if due_string:
        payload["due_string"] = due_string
    if due_date:
        payload["due_date"] = due_date

    if not payload:
        raise ValueError(
            "At least one editable field must be provided for Todoist task update."
        )

    return json.dumps(
        await http.post(
            f"{base_url}/tasks/{task_id}", headers=headers, json_body=payload
        ),
        ensure_ascii=False,
    )
