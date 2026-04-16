from __future__ import annotations

import json
from datetime import datetime, timezone

from app.config import settings
from app.integrations.google_oauth import GoogleOAuthClient
from app.integrations.http_client import HttpClient

http = HttpClient()
oauth = GoogleOAuthClient()
base_url = settings.google_calendar_base_url


async def tool_calendar_list_events(
    calendar_id: str = "primary",
    max_results: int = 10,
    include_past: bool = False,
) -> dict:
    """
    tool_calendar_list_events: List upcoming Google Calendar events.;
    args={
        calendar_id: "string, optional. Google calendar id. Default primary. If user didn't specify, use always default(primary).",
        max_results: "integer, optional. Default 10.",
        include_past: "boolean, optional. Default false (only upcoming events)."
    }
    """

    access_token = await oauth.get_access_token()
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "maxResults": max_results,
        "singleEvents": True,
        "orderBy": "startTime",
    }
    if not include_past:
        params["timeMin"] = (
            datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        )

    response = await http.get(
        f"{base_url}/calendars/{calendar_id}/events",
        headers=headers,
        params=params,
    )
    items = response.get("items") or []

    normalized_items: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        normalized_items.append(
            {
                "id": item.get("id"),
                "summary": item.get("summary", ""),
                "description": item.get("description", ""),
                "location": item.get("location", ""),
                "status": item.get("status", ""),
                "htmlLink": item.get("htmlLink", ""),
                "start": (item.get("start") or {}).get("dateTime")
                or (item.get("start") or {}).get("date"),
                "end": (item.get("end") or {}).get("dateTime")
                or (item.get("end") or {}).get("date"),
                "organizer": ((item.get("organizer") or {}).get("email") or ""),
                "attendees": [
                    attendee.get("email")
                    for attendee in (item.get("attendees") or [])
                    if isinstance(attendee, dict) and attendee.get("email")
                ],
            }
        )

    return json.dumps(
        {
            "items": normalized_items,
            "nextPageToken": response.get("nextPageToken"),
            "timeZone": response.get("timeZone"),
        },
        ensure_ascii=False,
    )


async def tool_calendar_create_event(
    summary: str,
    start_iso: str,
    end_iso: str,
    location: str | None = None,
    calendar_id: str = "primary",
) -> dict:
    """
    tool_calendar_create_event: Create Google Calendar event with ISO datetimes.;
    args={
        summary: "string, required. Event title.",
        start_iso: "string, required. ISO datetime start.",
        end_iso: "string, required. ISO datetime end.",
        location: "string, optional. Event location.",
        calendar_id: "string, optional. Google calendar id. Default primary. If user didn't specify, use always default(primary).",
    }
    """

    access_token = await oauth.get_access_token()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "summary": summary,
        "start": build_datetime_payload(start_iso),
        "end": build_datetime_payload(end_iso),
    }
    if location is not None:
        payload["location"] = location

    return json.dumps(
        await http.post(
            f"{base_url}/calendars/{calendar_id}/events",
            headers=headers,
            json_body=payload,
        ),
        ensure_ascii=False,
    )


async def tool_calendar_update_event(
    event_id: str,
    summary: str | None = None,
    start_iso: str | None = None,
    end_iso: str | None = None,
    description: str | None = None,
    location: str | None = None,
    calendar_id: str = "primary",
) -> dict:
    """
    tool_calendar_update_event: Update existing Google Calendar event fields.;
    args={
        event_id: "string, required. Existing event id.",
        summary: "string, optional. New title.",
        start_iso: "string, optional. New ISO datetime start.",
        end_iso: "string, optional. New ISO datetime end.",
        description: "string, optional. Event description.",
        location: "string, optional. Event location.",
        calendar_id: "string, optional. Google calendar id. Default primary. If user didn't specify, use always default(primary).",
    }
    """

    access_token = await oauth.get_access_token()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    payload: dict[str, dict | str] = {}
    if summary:
        payload["summary"] = summary
    if start_iso:
        payload["start"] = build_datetime_payload(start_iso)
    if end_iso:
        payload["end"] = build_datetime_payload(end_iso)
    if description is not None:
        payload["description"] = description
    if location is not None:
        payload["location"] = location

    if not payload:
        raise ValueError(
            "At least one editable field must be provided for calendar update."
        )

    return json.dumps(
        await http.patch(
            f"{base_url}/calendars/{calendar_id}/events/{event_id}",
            headers=headers,
            json_body=payload,
        ),
        ensure_ascii=False,
    )


def has_timezone(iso_value: str) -> bool:
    if "T" not in iso_value:
        return False
    time_part = iso_value.split("T", 1)[1]
    return time_part.endswith("Z") or "+" in time_part or "-" in time_part[1:]


def build_datetime_payload(iso_value: str) -> dict[str, str]:
    normalized = iso_value.strip()
    if has_timezone(normalized):
        return {"dateTime": normalized}
    return {
        "dateTime": normalized,
        "timeZone": settings.google_calendar_default_timezone,
    }
