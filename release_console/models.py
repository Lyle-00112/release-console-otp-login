"""Typed request/decision models for the release console login."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

Purpose = Literal["release_approval", "build_replay", "diagnostics"]


@dataclass(frozen=True)
class OtpRequest:
    phone: str
    purpose: Purpose
    ip: str
    captcha_token: str
    device_id: str
    locale: str = "en-US"


@dataclass(frozen=True)
class OtpChallenge:
    request_id: str
    phone: str
    purpose: Purpose
    code: str
    expires_at: float


@dataclass(frozen=True)
class LoginAttempt:
    request_id: str
    code: str
    now: float


@dataclass(frozen=True)
class Decision:
    granted: bool
    reason: str
    scopes: tuple[str, ...] = field(default=())
