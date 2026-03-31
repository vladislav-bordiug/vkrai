from __future__ import annotations

from datetime import datetime, timezone

from app.integrations.http_client import HttpClient
from app.integrations.google_oauth import GoogleOAuthClient
from app.config import settings


class GoogleCalendarTool:
    def __init__(self):
        self.http = HttpClient()
        self.oauth = GoogleOAuthClient()
        self.base_url = settings.google_calendar_base_url

    async def list_events(self, calendar_id: str = "primary", max_results: int = 10, include_past: bool = False) -> dict:
        access_token = await self.oauth.get_access_token()
        headers = {"Authorization": f"Bearer {access_token}"}
        params = {
            "maxResults": max_results,
            "singleEvents": True,
            "orderBy": "startTime",
        }
        if not include_past:
            params["timeMin"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        response = await self.http.get(f"{self.base_url}/calendars/{calendar_id}/events", headers=headers, params=params)
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
                    "start": (item.get("start") or {}).get("dateTime") or (item.get("start") or {}).get("date"),
                    "end": (item.get("end") or {}).get("dateTime") or (item.get("end") or {}).get("date"),
                    "organizer": ((item.get("organizer") or {}).get("email") or ""),
                    "attendees": [
                        attendee.get("email")
                        for attendee in (item.get("attendees") or [])
                        if isinstance(attendee, dict) and attendee.get("email")
                    ],
                }
            )

        return {
            "items": normalized_items,
            "nextPageToken": response.get("nextPageToken"),
            "timeZone": response.get("timeZone"),
        }

    async def create_event(self, summary: str, start_iso: str, end_iso: str, calendar_id: str = "primary") -> dict:
        access_token = await self.oauth.get_access_token()
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "summary": summary,
            "start": {"dateTime": start_iso},
            "end": {"dateTime": end_iso},
        }
        return await self.http.post(
            f"{self.base_url}/calendars/{calendar_id}/events",
            headers=headers,
            json_body=payload,
        )
