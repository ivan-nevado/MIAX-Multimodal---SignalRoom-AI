"""Cognito pre sign-up trigger: only invited emails can create an account.

ALLOWED_EMAILS: comma-separated emails and/or domains prefixed with "@".
Raising an exception makes Cognito reject the sign-up; the SPA shows the message.
"""

import os


def handler(event, context):
    allowed = [x.strip().lower() for x in os.environ.get("ALLOWED_EMAILS", "").split(",") if x.strip()]
    email = event.get("request", {}).get("userAttributes", {}).get("email", "").strip().lower()
    if allowed and not any(email == a or (a.startswith("@") and email.endswith(a)) for a in allowed):
        raise Exception("This SignalRoom demo is invite-only. Ask the team to add your email.")
    return event
