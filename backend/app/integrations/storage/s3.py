"""Private S3 storage. Browsers only ever see short-lived presigned URLs."""

from __future__ import annotations

from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError


class S3Storage:
    name = "s3"

    def __init__(self, bucket: str, region: str, endpoint_url: str | None = None) -> None:
        self._bucket = bucket
        # SigV4 + regional virtual-host addressing so presigned URLs work from browsers.
        self._client: Any = boto3.client(
            "s3",
            region_name=region,
            endpoint_url=endpoint_url,
            config=Config(
                signature_version="s3v4", s3={"addressing_style": "path" if endpoint_url else "virtual"}
            ),
        )

    def put_bytes(self, key: str, data: bytes, content_type: str) -> None:
        self._client.put_object(
            Bucket=self._bucket, Key=key, Body=data, ContentType=content_type, ServerSideEncryption="AES256"
        )

    def get_bytes(self, key: str) -> bytes:
        obj = self._client.get_object(Bucket=self._bucket, Key=key)
        data: bytes = obj["Body"].read()
        return data

    def read_head(self, key: str, length: int = 16) -> bytes:
        obj = self._client.get_object(Bucket=self._bucket, Key=key, Range=f"bytes=0-{length - 1}")
        data: bytes = obj["Body"].read()
        return data

    def size(self, key: str) -> int | None:
        try:
            head = self._client.head_object(Bucket=self._bucket, Key=key)
        except ClientError:
            return None
        return int(head["ContentLength"])

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)

    def delete_prefix(self, prefix: str) -> int:
        deleted = 0
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self._bucket, Prefix=prefix):
            objects = [{"Key": o["Key"]} for o in page.get("Contents", [])]
            if objects:
                self._client.delete_objects(Bucket=self._bucket, Delete={"Objects": objects, "Quiet": True})
                deleted += len(objects)
        return deleted

    def presign_put(
        self, key: str, content_type: str, size_bytes: int, expires: int = 900
    ) -> tuple[str, dict[str, str]]:
        url: str = self._client.generate_presigned_url(
            "put_object",
            Params={"Bucket": self._bucket, "Key": key, "ContentType": content_type},
            ExpiresIn=expires,
        )
        return url, {"Content-Type": content_type}

    def presign_get(self, key: str, expires: int = 3600, filename: str | None = None) -> str:
        params: dict[str, Any] = {"Bucket": self._bucket, "Key": key}
        if filename:
            params["ResponseContentDisposition"] = f'inline; filename="{filename}"'
        url: str = self._client.generate_presigned_url("get_object", Params=params, ExpiresIn=expires)
        return url
