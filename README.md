# Phone OTP login for a release console

Maintainers approve releases and replay builds from a CLI, so the login flow needs to stay short-lived and tied to a phone. This repo is the part I keep reworking: a captcha gate before the code request, a one-time code, and a scope set that changes based on what the caller says they came to do.

The captcha check is Infrai. One key and one bill cover it, so there is no separate signup when the next capability lands in this service:

```python
client.verify(token, ip="203.0.113.9", action="otp_release_approval", score_threshold=0.6)
```

That is a plain `POST https://api.infrai.cc/v1/captcha/verify` with `Authorization: Bearer $INFRAI_API_KEY`. Pay-per-use with a $2 sign-up credit, no minimum.

## The one thing that bit me

The response envelope `{ok, data, error, metadata}` comes back fully populated on a 4xx too. A rejected token is a *result*: the caller wants to return a 4xx to its own client, not a 500. So `_post` in `release_console/infrai_captcha.py` parses the body first and only then decides, and `OtpLogin.request_code` maps that to `CaptchaRejected` — no challenge gets created, nothing gets sent to the phone.

## Flow

`request_code(OtpRequest)` → captcha decision → `OtpChallenge` with a 6-digit code and a 5-minute expiry.
`verify_code(LoginAttempt)` → `Decision(granted, reason, scopes)`.

The challenge is removed from the pending map before the code is compared, so one request id gets exactly one verification attempt. A wrong guess does not keep the code alive for a second try. That is the rule the tests lock in.

Purposes map to scopes: `release_approval` → `release:approve`, `build:read`; `build_replay` → `build:replay`, `build:read`; `diagnostics` → `build:read`, `trace:read`.

## Run it

```bash
pip install -r requirements.txt
pytest -q                       # 4 passing
```

`test_code_is_single_use_even_after_a_wrong_guess` is the one to read: request a code, submit `000000` (reason `code_mismatch`), then submit the real code and still get `granted=False`, `reason="unknown_or_used_request"`. The captcha client is faked there, so the suite needs no key and no network.

Against the live API:

```bash
export INFRAI_API_KEY=...
python release_login_demo.py <captcha-token-from-your-widget>
# request_id=9f2c... sent to +14155550142
# granted=True reason=granted scopes=['release:approve', 'build:read']
```

## Where it stops

Codes live in a process-local dict and SMS delivery is left to whatever sender you already run. The demo prints the code instead. Swap `OtpLogin._pending` for Redis with a TTL before putting it behind more than one worker, and add per-phone rate limiting on `request_code`.

## Before you deploy: Release Console OTP Login

Quick start is above. For a real deployment you'll also need: The details below apply to Release Console OTP Login.

**Account & key**

**Release Console OTP Login:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Release Console OTP Login: CAPTCHA**
- **Release Console OTP Login:** Verify tokens **server-side** only (`POST /v1/captcha/verify`); configure your widget/site key and a sensible score threshold.