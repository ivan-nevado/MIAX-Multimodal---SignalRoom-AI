"""Invite-only access control for the demo deployment (protects the API budget).

ALLOWED_EMAILS is a comma-separated list of exact emails and/or domains prefixed with "@",
e.g. "ana@gmail.com,luis@gmail.com,@alumnos.miax.es". Empty = open sign-up.
The same list is enforced by the Cognito pre-sign-up Lambda (Terraform) and here, as
defence in depth (a token from a non-invited user is rejected by every endpoint).
"""

from __future__ import annotations

from app.services.errors import ServiceError


class NotInvited(ServiceError):
    status_code = 403
    code = "not_invited"


INVITE_ONLY_MESSAGE = (
    "This SignalRoom demo is invite-only. Ask the team to add your email to the access list."
)


def parse_allowlist(raw: str) -> list[str]:
    return [item.strip().lower() for item in raw.replace(";", ",").split(",") if item.strip()]


def is_email_allowed(email: str | None, raw_allowlist: str) -> bool:
    allowlist = parse_allowlist(raw_allowlist)
    if not allowlist:
        return True
    if not email:
        return False
    email = email.strip().lower()
    return any(email == entry or (entry.startswith("@") and email.endswith(entry)) for entry in allowlist)


def ensure_allowed(email: str | None, raw_allowlist: str) -> None:
    if not is_email_allowed(email, raw_allowlist):
        raise NotInvited(INVITE_ONLY_MESSAGE)
