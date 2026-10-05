"""Create LocalStack resources (tables, bucket, queues, secret) for the `aws-local` compose profile.

Never used against real AWS: Terraform owns real infrastructure. The OpenRouter key is
copied from the environment into the LocalStack secret so the containers read it from
"Secrets Manager" exactly as they will in AWS.
"""

from __future__ import annotations

import json
import os

import boto3
from botocore.exceptions import ClientError

from app.repositories.dynamodb_schema import create_tables


def main() -> None:
    endpoint = os.environ["AWS_ENDPOINT_URL"]
    if "localstack" not in endpoint and "localhost" not in endpoint:
        raise SystemExit("bootstrap_local_aws only runs against LocalStack")
    region = os.environ.get("AWS_REGION", "eu-west-1")
    created = create_tables(
        boto3.client("dynamodb", region_name=region, endpoint_url=endpoint),
        os.environ["DYNAMODB_TABLE_PREFIX"],
    )
    print("tables:", created or "already exist")

    s3 = boto3.client("s3", region_name=region, endpoint_url=endpoint)
    bucket = os.environ["S3_BUCKET"]
    try:
        s3.create_bucket(Bucket=bucket, CreateBucketConfiguration={"LocationConstraint": region})
    except ClientError as exc:
        if exc.response["Error"]["Code"] not in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
            raise
    s3.put_bucket_cors(
        Bucket=bucket,
        CORSConfiguration={
            "CORSRules": [
                {
                    "AllowedMethods": ["PUT", "GET"],
                    "AllowedOrigins": ["*"],
                    "AllowedHeaders": ["*"],
                    "MaxAgeSeconds": 3000,
                }
            ]
        },
    )
    print("bucket:", bucket)

    sqs = boto3.client("sqs", region_name=region, endpoint_url=endpoint)
    for url_var in ("SQS_INVESTIGATION_QUEUE_URL", "SQS_BRIEFING_QUEUE_URL"):
        name = os.environ[url_var].rsplit("/", 1)[1]
        dlq = sqs.create_queue(QueueName=f"{name}-dlq")["QueueUrl"]
        dlq_arn = sqs.get_queue_attributes(QueueUrl=dlq, AttributeNames=["QueueArn"])["Attributes"][
            "QueueArn"
        ]
        sqs.create_queue(
            QueueName=name,
            Attributes={
                "VisibilityTimeout": "900",
                "RedrivePolicy": json.dumps({"deadLetterTargetArn": dlq_arn, "maxReceiveCount": "3"}),
            },
        )
        print("queue:", name)

    sm = boto3.client("secretsmanager", region_name=region, endpoint_url=endpoint)
    openrouter = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPEN_ROUTER_API_KEY", "")
    value = json.dumps(
        {
            "OPENROUTER_API_KEY": openrouter,
            "ALPHAVANTAGE_API_KEY": os.environ.get("ALPHAVANTAGE_API_KEY", ""),
            "FRED_API_KEY": os.environ.get("FRED_API_KEY", ""),
            "SEC_USER_AGENT": os.environ.get("SEC_USER_AGENT", ""),
        }
    )
    secret_id = os.environ["SECRETS_MANAGER_SECRET_ID"]
    try:
        sm.create_secret(Name=secret_id, SecretString=value)
    except ClientError:
        sm.put_secret_value(SecretId=secret_id, SecretString=value)
    print("secret:", secret_id)


if __name__ == "__main__":
    main()
