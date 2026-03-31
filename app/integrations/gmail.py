from __future__ import annotations

import base64
from email.message import EmailMessage

from app.integrations.http_client import HttpClient
from app.integrations.google_oauth import GoogleOAuthClient
from app.config import settings


class GmailTool:
    def __init__(self):
        self.http = HttpClient()
        self.oauth = GoogleOAuthClient()
        self.base_url = settings.gmail_base_url

    async def list_messages(self, user_id: str = "me", query: str | None = None, max_results: int = 10) -> dict:
        access_token = await self.oauth.get_access_token()
        headers = {"Authorization": f"Bearer {access_token}"}
        params = {"maxResults": max_results}
        if query:
            params["q"] = query
        list_response = await self.http.get(f"{self.base_url}/users/{user_id}/messages", headers=headers, params=params)

        messages = list_response.get("messages") or []
        detailed_messages: list[dict] = []
        for item in messages:
            message_id = item.get("id")
            if not message_id:
                continue

            full_message = await self.http.get(
                f"{self.base_url}/users/{user_id}/messages/{message_id}",
                headers=headers,
                params={"format": "full"},
            )
            payload = full_message.get("payload") or {}
            header_map = self._headers_to_map(payload.get("headers") or [])
            detailed_messages.append(
                {
                    "id": full_message.get("id", message_id),
                    "threadId": full_message.get("threadId"),
                    "subject": header_map.get("subject", ""),
                    "from": header_map.get("from", ""),
                    "date": header_map.get("date", ""),
                    "snippet": full_message.get("snippet", ""),
                    "body": self._extract_plain_text_from_payload(payload),
                }
            )

        return {
            "messages": detailed_messages,
            "nextPageToken": list_response.get("nextPageToken"),
            "resultSizeEstimate": list_response.get("resultSizeEstimate"),
        }

    async def send_message(
        self,
        to_email: str,
        subject: str,
        body: str,
        from_email: str,
        user_id: str = "me",
    ) -> dict:
        access_token = await self.oauth.get_access_token()
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        raw_base64_message = self._build_raw_message(
            to_email=to_email,
            subject=subject,
            body=body,
            from_email=from_email,
        )
        return await self.http.post(
            f"{self.base_url}/users/{user_id}/messages/send",
            headers=headers,
            json_body={"raw": raw_base64_message},
        )

    @staticmethod
    def _build_raw_message(to_email: str, subject: str, body: str, from_email: str) -> str:
        message = EmailMessage()
        message["To"] = to_email
        message["From"] = from_email
        message["Subject"] = subject
        message.set_content(body)
        return base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

    @staticmethod
    def _headers_to_map(headers: list[dict]) -> dict[str, str]:
        return {
            str(h.get("name", "")).strip().lower(): str(h.get("value", "")).strip()
            for h in headers
            if isinstance(h, dict)
        }

    @staticmethod
    def _extract_plain_text_from_payload(payload: dict) -> str:
        def walk(node: dict) -> str | None:
            if not isinstance(node, dict):
                return None

            mime_type = str(node.get("mimeType", "")).lower()
            body = node.get("body") or {}
            data = body.get("data")
            if mime_type.startswith("text/plain") and isinstance(data, str):
                return GmailTool._decode_base64url(data)

            for part in node.get("parts") or []:
                text = walk(part)
                if text:
                    return text

            if isinstance(data, str):
                return GmailTool._decode_base64url(data)
            return None

        text = walk(payload)
        return (text or "").strip()

    @staticmethod
    def _decode_base64url(data: str) -> str:
        padding = "=" * (-len(data) % 4)
        try:
            decoded = base64.urlsafe_b64decode(data + padding)
            return decoded.decode("utf-8", errors="replace")
        except Exception:
            return ""
