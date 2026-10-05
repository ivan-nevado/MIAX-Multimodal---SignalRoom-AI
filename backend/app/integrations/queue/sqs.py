"""Amazon SQS queue backend. Messages are deleted only after the job succeeds."""

from __future__ import annotations

import json
from typing import Any

import boto3

from app.integrations.queue.base import QueueName, ReceivedMessage


class SQSQueue:
    name = "sqs"

    def __init__(self, urls: dict[str, str], region: str, endpoint_url: str | None = None) -> None:
        self._urls = urls
        self._client: Any = boto3.client("sqs", region_name=region, endpoint_url=endpoint_url)

    def send(self, queue: QueueName, body: dict[str, Any]) -> str:
        resp = self._client.send_message(QueueUrl=self._urls[queue], MessageBody=json.dumps(body))
        return str(resp["MessageId"])

    def receive(
        self, queue: QueueName, max_messages: int = 1, wait_seconds: int = 10
    ) -> list[ReceivedMessage]:
        resp = self._client.receive_message(
            QueueUrl=self._urls[queue],
            MaxNumberOfMessages=max_messages,
            WaitTimeSeconds=wait_seconds,
            MessageSystemAttributeNames=["ApproximateReceiveCount"],
        )
        out: list[ReceivedMessage] = []
        for msg in resp.get("Messages", []):
            try:
                body = json.loads(msg["Body"])
            except json.JSONDecodeError:
                body = {"_invalid": True}
            count = int(msg.get("Attributes", {}).get("ApproximateReceiveCount", "1"))
            out.append(ReceivedMessage(body=body, receipt=msg["ReceiptHandle"], receive_count=count))
        return out

    def ack(self, queue: QueueName, receipt: str) -> None:
        self._client.delete_message(QueueUrl=self._urls[queue], ReceiptHandle=receipt)

    def release(self, queue: QueueName, receipt: str, delay_seconds: int = 0) -> None:
        # Make the message visible again (retry). After maxReceiveCount SQS moves it to the DLQ.
        self._client.change_message_visibility(
            QueueUrl=self._urls[queue], ReceiptHandle=receipt, VisibilityTimeout=delay_seconds
        )
