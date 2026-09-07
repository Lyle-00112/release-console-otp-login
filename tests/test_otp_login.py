from __future__ import annotations

import pytest

from release_console.models import LoginAttempt, OtpRequest
from release_console.otp_login import CaptchaRejected, OtpLogin
from release_console.infrai_captcha import InfraiError


class FakeCaptcha:
    def __init__(self, error: InfraiError | None = None) -> None:
        self.error = error
        self.calls: list[dict] = []

    def verify(self, token, *, ip, action, vendor="turnstile", score_threshold=0.5):
        self.calls.append({"token": token, "ip": ip, "action": action, "score_threshold": score_threshold})
        if self.error:
            raise self.error
        return {"success": True, "score": 0.9}


def make_request(token="tok-good"):
    return OtpRequest(
        phone="+14155550142",
        purpose="build_replay",
        ip="203.0.113.9",
        captcha_token=token,
        device_id="cli-macbook-01",
    )


def test_correct_code_grants_purpose_scopes():
    login = OtpLogin(FakeCaptcha())
    challenge = login.request_code(make_request(), now=1000.0)
    decision = login.verify_code(LoginAttempt(challenge.request_id, challenge.code, 1010.0))
    assert decision.granted
    assert decision.scopes == ("build:replay", "build:read")


def test_code_is_single_use_even_after_a_wrong_guess():
    login = OtpLogin(FakeCaptcha())
    challenge = login.request_code(make_request(), now=1000.0)
    assert login.verify_code(LoginAttempt(challenge.request_id, "000000", 1001.0)).reason == "code_mismatch"
    replay = login.verify_code(LoginAttempt(challenge.request_id, challenge.code, 1002.0))
    assert not replay.granted
    assert replay.reason == "unknown_or_used_request"


def test_expired_code_is_refused():
    login = OtpLogin(FakeCaptcha(), ttl_seconds=60)
    challenge = login.request_code(make_request(), now=1000.0)
    decision = login.verify_code(LoginAttempt(challenge.request_id, challenge.code, 1100.0))
    assert (decision.granted, decision.reason) == (False, "expired")


def test_low_score_captcha_issues_no_challenge():
    captcha = FakeCaptcha(InfraiError("CAPTCHA_SCORE_TOO_LOW", "score below threshold", 422))
    login = OtpLogin(captcha)
    with pytest.raises(CaptchaRejected) as caught:
        login.request_code(make_request("tok-bot"), now=1000.0)
    assert caught.value.code == "CAPTCHA_SCORE_TOO_LOW"
    assert captcha.calls[0]["action"] == "otp_build_replay"
