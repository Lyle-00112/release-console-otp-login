#!/usr/bin/env python3
"""Run one login end to end against Infrai: INFRAI_API_KEY=... python release_login_demo.py <captcha-token>"""
from __future__ import annotations

import sys
import time

from release_console.infrai_captcha import CaptchaClient
from release_console.models import LoginAttempt, OtpRequest
from release_console.otp_login import CaptchaRejected, OtpLogin


def main() -> int:
    token = sys.argv[1] if len(sys.argv) > 1 else ""
    login = OtpLogin(CaptchaClient())
    request = OtpRequest(
        phone="+14155550142",
        purpose="release_approval",
        ip="203.0.113.9",
        captcha_token=token,
        device_id="cli-macbook-01",
    )
    try:
        challenge = login.request_code(request)
    except CaptchaRejected as rejected:
        print(f"no code issued ({rejected.code})")
        return 2

    print(f"request_id={challenge.request_id} sent to {challenge.phone}")
    # Your SMS sender delivers challenge.code; here we read it back to finish the flow.
    decision = login.verify_code(LoginAttempt(challenge.request_id, challenge.code, time.time()))
    print(f"granted={decision.granted} reason={decision.reason} scopes={list(decision.scopes)}")
    return 0 if decision.granted else 1


if __name__ == "__main__":
    raise SystemExit(main())
