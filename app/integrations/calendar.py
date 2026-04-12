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

    async def create_event(
        self,
        summary: str,
        start_iso: str,
        end_iso: str,
        location: str | None = None,
        calendar_id: str = "primary",
    ) -> dict:
        access_token = await self.oauth.get_access_token()
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "summary": summary,
            "start": self._build_datetime_payload(start_iso),
            "end": self._build_datetime_payload(end_iso),
        }
        if location is not None:
            payload["location"] = location
        return await self.http.post(
            f"{self.base_url}/calendars/{calendar_id}/events",
            headers=headers,
            json_body=payload,
        )

    async def update_event(
        self,
        event_id: str,
        summary: str | None = None,
        start_iso: str | None = None,
        end_iso: str | None = None,
        description: str | None = None,
        location: str | None = None,
        calendar_id: str = "primary",
    ) -> dict:
        access_token = await self.oauth.get_access_token()
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        payload: dict[str, dict | str] = {}
        if summary:
            payload["summary"] = summary
        if start_iso:
            payload["start"] = self._build_datetime_payload(start_iso)
        if end_iso:
            payload["end"] = self._build_datetime_payload(end_iso)
        if description is not None:
            payload["description"] = description
        if location is not None:
            payload["location"] = location

        if not payload:
            raise ValueError("At least one editable field must be provided for calendar update.")

        return await self.http.patch(
            f"{self.base_url}/calendars/{calendar_id}/events/{event_id}",
            headers=headers,
            json_body=payload,
        )

    @staticmethod
    def _has_timezone(iso_value: str) -> bool:
        if "T" not in iso_value:
            return False
        time_part = iso_value.split("T", 1)[1]
        return time_part.endswith("Z") or "+" in time_part or "-" in time_part[1:]

    @staticmethod
    def _build_datetime_payload(iso_value: str) -> dict[str, str]:
        normalized = iso_value.strip()
        if GoogleCalendarTool._has_timezone(normalized):
            return {"dateTime": normalized}
        return {
            "dateTime": normalized,
            "timeZone": settings.google_calendar_default_timezone,
        }
