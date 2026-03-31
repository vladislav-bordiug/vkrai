from __future__ import annotations

import time
from dataclasses import dataclass

import httpx

from app.config import settings


@dataclass
class TokenState:
    access_token: str = ""
    expires_at: float = 0.0


class GoogleOAuthClient:
    def __init__(self):
        self._state = TokenState()

    async def get_access_token(self) -> str:
        # cached refresh-token flow
        now = time.time()
        if self._state.access_token and now < self._state.expires_at - 30:
            return self._state.access_token

        token_data = await self._refresh_access_token()
        self._state.access_token = token_data["access_token"]
        self._state.expires_at = now + int(token_data.get("expires_in", 3600))
        return self._state.access_token

    async def _refresh_access_token(self) -> dict:
        missing = [
            name
            for name, value in [
                ("GOOGLE_CLIENT_ID", settings.google_client_id),
                ("GOOGLE_CLIENT_SECRET", settings.google_client_secret),
                ("GOOGLE_REFRESH_TOKEN", settings.google_refresh_token),
            ]
            if not value
        ]
        if missing:
            raise RuntimeError(
                "Google OAuth credentials are not configured for refresh flow. "
                f"Missing: {', '.join(missing)}"
            )

        data = {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "refresh_token": settings.google_refresh_token,
            "grant_type": "refresh_token",
        }

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(settings.google_token_url, data=data)

        if not response.is_success:
            raise RuntimeError(f"Google token refresh failed: {response.status_code} {response.text}")

        payload = response.json()
        if "access_token" not in payload:
            raise RuntimeError(f"Google token refresh response has no access_token: {payload}")
        return payload

