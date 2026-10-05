from __future__ import annotations

import re
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, field_validator

from app.schemas.common import Model

_TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


def _validate_tz(value: str) -> str:
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError(f"Unknown timezone: {value}") from exc
    return value


class BriefingPreferences(Model):
    enabled: bool = False
    local_time: str = "08:00"
    timezone: str = "Europe/Madrid"
    email_enabled: bool = False
    audio_enabled: bool = True
    voice: Literal["professional"] = "professional"

    @field_validator("local_time")
    @classmethod
    def _time(cls, v: str) -> str:
        if not _TIME_RE.match(v):
            raise ValueError("local_time must be HH:MM (24h)")
        return v

    @field_validator("timezone")
    @classmethod
    def _tz(cls, v: str) -> str:
        return _validate_tz(v)


class BriefingPreferencesPatch(Model):
    enabled: bool | None = None
    local_time: str | None = None
    timezone: str | None = None
    email_enabled: bool | None = None
    audio_enabled: bool | None = None

    @field_validator("local_time")
    @classmethod
    def _time(cls, v: str | None) -> str | None:
        if v is not None and not _TIME_RE.match(v):
            raise ValueError("local_time must be HH:MM (24h)")
        return v

    @field_validator("timezone")
    @classmethod
    def _tz(cls, v: str | None) -> str | None:
        return _validate_tz(v) if v is not None else v


class UserPreferences(Model):
    timezone: str = "Europe/Madrid"
    display_currency: str = "USD"
    briefing: BriefingPreferences = Field(default_factory=BriefingPreferences)


class UserPreferencesPatch(Model):
    timezone: str | None = None
    display_currency: str | None = Field(default=None, max_length=3)

    @field_validator("timezone")
    @classmethod
    def _tz(cls, v: str | None) -> str | None:
        return _validate_tz(v) if v is not None else v


class UserRecord(Model):
    user_id: str
    email: str
    preferences: UserPreferences = Field(default_factory=UserPreferences)
    last_briefing_date: str | None = None
    created_at: str


class MeResponse(Model):
    user_id: str
    email: str
    preferences: UserPreferences
    created_at: str
    auth_mode: str


class AuthenticatedUser(Model):
    user_id: str
    email: str | None = None


class LocalAuthRequest(Model):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            raise ValueError("Invalid email address")
        return v


class LocalAuthResponse(Model):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    email: str
