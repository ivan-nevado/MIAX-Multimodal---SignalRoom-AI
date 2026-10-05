"""DynamoDB table definitions — the single source of truth mirrored by terraform/modules/dynamodb.

Used by tests (moto) and scripts/create_local_tables.py (LocalStack / DynamoDB Local).
"""

from __future__ import annotations

from typing import Any

from app.repositories.dynamodb import USER_INDEX, table_name

TTL_ATTRIBUTE = "expires_at"


def table_specs(prefix: str) -> list[dict[str, Any]]:
    def gsi() -> list[dict[str, Any]]:
        return [
            {
                "IndexName": USER_INDEX,
                "KeySchema": [
                    {"AttributeName": "user_id", "KeyType": "HASH"},
                    {"AttributeName": "created_at", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }
        ]

    s, n = "S", "N"
    return [
        {
            "TableName": table_name(prefix, "users"),
            "KeySchema": [{"AttributeName": "user_id", "KeyType": "HASH"}],
            "AttributeDefinitions": [{"AttributeName": "user_id", "AttributeType": s}],
        },
        {
            "TableName": table_name(prefix, "watchlists"),
            "KeySchema": [
                {"AttributeName": "user_id", "KeyType": "HASH"},
                {"AttributeName": "symbol", "KeyType": "RANGE"},
            ],
            "AttributeDefinitions": [
                {"AttributeName": "user_id", "AttributeType": s},
                {"AttributeName": "symbol", "AttributeType": s},
            ],
        },
        {
            "TableName": table_name(prefix, "investigations"),
            "KeySchema": [{"AttributeName": "investigation_id", "KeyType": "HASH"}],
            "AttributeDefinitions": [
                {"AttributeName": "investigation_id", "AttributeType": s},
                {"AttributeName": "user_id", "AttributeType": s},
                {"AttributeName": "created_at", "AttributeType": s},
            ],
            "GlobalSecondaryIndexes": gsi(),
        },
        {
            "TableName": table_name(prefix, "events"),
            "KeySchema": [
                {"AttributeName": "investigation_id", "KeyType": "HASH"},
                {"AttributeName": "seq", "KeyType": "RANGE"},
            ],
            "AttributeDefinitions": [
                {"AttributeName": "investigation_id", "AttributeType": s},
                {"AttributeName": "seq", "AttributeType": n},
            ],
            "ttl": True,
        },
        {
            "TableName": table_name(prefix, "briefings"),
            "KeySchema": [{"AttributeName": "briefing_id", "KeyType": "HASH"}],
            "AttributeDefinitions": [
                {"AttributeName": "briefing_id", "AttributeType": s},
                {"AttributeName": "user_id", "AttributeType": s},
                {"AttributeName": "created_at", "AttributeType": s},
            ],
            "GlobalSecondaryIndexes": gsi(),
        },
        {
            "TableName": table_name(prefix, "deliveries"),
            "KeySchema": [{"AttributeName": "delivery_key", "KeyType": "HASH"}],
            "AttributeDefinitions": [{"AttributeName": "delivery_key", "AttributeType": s}],
            "ttl": True,
        },
        {
            "TableName": table_name(prefix, "uploads"),
            "KeySchema": [{"AttributeName": "upload_id", "KeyType": "HASH"}],
            "AttributeDefinitions": [
                {"AttributeName": "upload_id", "AttributeType": s},
                {"AttributeName": "user_id", "AttributeType": s},
                {"AttributeName": "created_at", "AttributeType": s},
            ],
            "GlobalSecondaryIndexes": gsi(),
        },
        {
            "TableName": table_name(prefix, "cache"),
            "KeySchema": [{"AttributeName": "cache_key", "KeyType": "HASH"}],
            "AttributeDefinitions": [{"AttributeName": "cache_key", "AttributeType": s}],
            "ttl": True,
        },
    ]


def create_tables(client: Any, prefix: str) -> list[str]:
    created = []
    existing = set(client.list_tables().get("TableNames", []))
    for spec in table_specs(prefix):
        spec = dict(spec)
        ttl = spec.pop("ttl", False)
        if spec["TableName"] in existing:
            continue
        client.create_table(BillingMode="PAY_PER_REQUEST", **spec)
        if ttl:
            client.get_waiter("table_exists").wait(TableName=spec["TableName"])
            client.update_time_to_live(
                TableName=spec["TableName"],
                TimeToLiveSpecification={"Enabled": True, "AttributeName": TTL_ATTRIBUTE},
            )
        created.append(spec["TableName"])
    return created
