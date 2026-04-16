from __future__ import annotations

import base64
import json
from email.message import EmailMessage

from app.config import settings
from app.integrations.google_oauth import GoogleOAuthClient
from app.integrations.http_client import HttpClient

http = HttpClient()
oauth = GoogleOAuthClient()
base_url = settings.gmail_base_url


async def tool_gmail_list_messages(
    user_id: str = "me", query: str | None = None, max_results: int = 10
) -> dict:
    """
    tool_gmail_list_messages: List Gmail messages by query filter.;
    args={
        user_id: "string, optional. GMail user id. Default me. If user didn't specify, use always default(me).",
        query: "string, optional. Gmail search query.",
        max_results: "integer, optional. Default 10.",
    }
    """

    access_token = await oauth.get_access_token()
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {"maxResults": max_results}
    if query:
        params["q"] = query
    list_response = await http.get(
        f"{base_url}/users/{user_id}/messages", headers=headers, params=params
    )

    messages = list_response.get("messages") or []
    detailed_messages: list[dict] = []
    for item in messages:
        message_id = item.get("id")
        if not message_id:
            continue

        full_message = await http.get(
            f"{base_url}/users/{user_id}/messages/{message_id}",
            headers=headers,
            params={"format": "full"},
        )
        payload = full_message.get("payload") or {}
        header_map = headers_to_map(payload.get("headers") or [])
        detailed_messages.append(
            {
                "id": full_message.get("id", message_id),
                "threadId": full_message.get("threadId"),
                "subject": header_map.get("subject", ""),
                "from": header_map.get("from", ""),
                "date": header_map.get("date", ""),
                "snippet": full_message.get("snippet", ""),
                "body": extract_plain_text_from_payload(payload),
            }
        )

    return json.dumps(
        {
            "messages": detailed_messages,
            "nextPageToken": list_response.get("nextPageToken"),
            "resultSizeEstimate": list_response.get("resultSizeEstimate"),
        },
        ensure_ascii=False,
    )


async def tool_gmail_send_message(
    to_email: str,
    subject: str,
    body: str,
    from_email: str,
    user_id: str = "me",
) -> dict:
    """
    tool_gmail_send_message: Send Gmail message from structured fields; backend builds RFC2822/base64 payload internally.;
    args={
        to_email: "string, required. Recipient email.",
        subject: "string, required. Email subject.",
        body: "string, required. Plain text body.",
        from_email: "string, required. Sender email used in From header.",
        user_id: "string, optional. GMail user id. Default me. If user didn't specify, use always default(me).",
    }
    """

    access_token = await oauth.get_access_token()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    raw_base64_message = build_raw_message(
        to_email=to_email,
        subject=subject,
        body=body,
        from_email=from_email,
    )

    return json.dumps(
        await http.post(
            f"{base_url}/users/{user_id}/messages/send",
            headers=headers,
            json_body={"raw": raw_base64_message},
        ),
        ensure_ascii=False,
    )


def build_raw_message(to_email: str, subject: str, body: str, from_email: str) -> str:
    message = EmailMessage()
    message["To"] = to_email
    message["From"] = from_email
    message["Subject"] = subject
    message.set_content(body)
    return base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")


def headers_to_map(headers: list[dict]) -> dict[str, str]:
    return {
        str(h.get("name", "")).strip().lower(): str(h.get("value", "")).strip()
        for h in headers
        if isinstance(h, dict)
    }


def extract_plain_text_from_payload(payload: dict) -> str:
    def walk(node: dict) -> str | None:
        if not isinstance(node, dict):
            return None

        mime_type = str(node.get("mimeType", "")).lower()
        body = node.get("body") or {}
        data = body.get("data")
        if mime_type.startswith("text/plain") and isinstance(data, str):
            return decode_base64url(data)

        for part in node.get("parts") or []:
            text = walk(part)
            if text:
                return text

        if isinstance(data, str):
            return decode_base64url(data)
        return None

    text = walk(payload)
    return (text or "").strip()


def decode_base64url(data: str) -> str:
    padding = "=" * (-len(data) % 4)
    try:
        decoded = base64.urlsafe_b64decode(data + padding)
        return decoded.decode("utf-8", errors="replace")
    except Exception:
        return ""
