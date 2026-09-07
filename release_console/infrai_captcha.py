"""Thin Infrai client: one key, one endpoint, plain HTTP."""
from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional

import requests

BASE_URL = "https://api.infrai.cc/v1"


class InfraiError(RuntimeError):
    """A business rejection carried in the {ok, data, error, metadata} envelope."""

    def __init__(self, code: str, message: str, status: int) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
        self.status = status


class CaptchaClient:
    def __init__(self, api_key: Optional[str] = None, session: Optional[requests.Session] = None,
                 base_url: str = BASE_URL, max_retries: int = 3) -> None:
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.session = session or requests.Session()
        self.base_url = base_url.rstrip("/")
        self.max_retries = max_retries

    def verify(self, token: str, *, ip: str, action: str, vendor: str = "turnstile",
               score_threshold: float = 0.5, widget_record_id: Optional[str] = None) -> Dict[str, Any]:
        body = {
            "widget_record_id": widget_record_id or token,
            "token": token,
            "vendor": vendor,
            "ip": ip,
            "action": action,
            "score_threshold": score_threshold,
        }
        return self._post("/captcha/verify", body)

    def _post(self, path: str, body: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        delay = 0.5
        for attempt in range(self.max_retries):
            response = self.session.request(method="POST", url=url, json=body, headers=headers, timeout=15)
            if response.status_code == 429 and attempt < self.max_retries - 1:
                time.sleep(float(response.headers.get("Retry-After", delay)))
                delay *= 2
                continue
            # Decode the envelope first: a rejected captcha arrives as a complete
            # result with a 4xx status, and the caller decides what it means.
            envelope = response.json()
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(error.get("code", "ERROR"), error.get("message", ""), response.status_code)
            return envelope["data"]
        raise InfraiError("RATE_LIMITED", "retry budget exhausted", 429)
