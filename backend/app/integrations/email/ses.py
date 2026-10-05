"""Amazon SES (v2) email sender.

SES sandbox: until production access is granted, both the sender and every
recipient must be verified identities. See docs/email_setup.md.
"""

from __future__ import annotations

from typing import Any

import boto3


class SESEmailSender:
    name = "ses"

    def __init__(self, from_email: str, region: str, endpoint_url: str | None = None) -> None:
        self._from = from_email
        self._client: Any = boto3.client("sesv2", region_name=region, endpoint_url=endpoint_url)

    def send(self, *, to: str, subject: str, html: str, text: str) -> str:
        resp = self._client.send_email(
            FromEmailAddress=self._from,
            Destination={"ToAddresses": [to]},
            Content={
                "Simple": {
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {
                        "Html": {"Data": html, "Charset": "UTF-8"},
                        "Text": {"Data": text, "Charset": "UTF-8"},
                    },
                }
            },
        )
        return str(resp.get("MessageId", ""))
