"""Phone OTP login for the release console.

A maintainer asks for a code, Infrai's captcha check decides whether the
request is human, and only then does a challenge exist. Verification is a
single-use state transition: a code burns whether it matched or not.
"""
from __future__ import annotations

import hmac
import secrets
import time
from typing import Dict

from .infrai_captcha import CaptchaClient, InfraiError
from .models import Decision, LoginAttempt, OtpChallenge, OtpRequest

CODE_TTL_SECONDS = 300

SCOPES: Dict[str, tuple[str, ...]] = {
    "release_approval": ("release:approve", "build:read"),
    "build_replay": ("build:replay", "build:read"),
    "diagnostics": ("build:read", "trace:read"),
}


class CaptchaRejected(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class OtpLogin:
    def __init__(self, captcha: CaptchaClient, ttl_seconds: int = CODE_TTL_SECONDS) -> None:
        self.captcha = captcha
        self.ttl_seconds = ttl_seconds
        self._pending: Dict[str, OtpChallenge] = {}

    def request_code(self, request: OtpRequest, now: float | None = None) -> OtpChallenge:
        try:
            self.captcha.verify(
                request.captcha_token,
                ip=request.ip,
                action=f"otp_{request.purpose}",
                score_threshold=0.6,
            )
        except InfraiError as err:
            raise CaptchaRejected(err.code, err.message) from err

        now = time.time() if now is None else now
        challenge = OtpChallenge(
            request_id=secrets.token_hex(8),
            phone=request.phone,
            purpose=request.purpose,
            code=f"{secrets.randbelow(1_000_000):06d}",
            expires_at=now + self.ttl_seconds,
        )
        self._pending[challenge.request_id] = challenge
        return challenge

    def verify_code(self, attempt: LoginAttempt) -> Decision:
        challenge = self._pending.pop(attempt.request_id, None)
        if challenge is None:
            return Decision(False, "unknown_or_used_request")
        if attempt.now > challenge.expires_at:
            return Decision(False, "expired")
        if not hmac.compare_digest(challenge.code, attempt.code):
            return Decision(False, "code_mismatch")
        return Decision(True, "granted", SCOPES[challenge.purpose])
