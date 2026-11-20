import json

import boto3
import pytest
from moto import mock_aws


@pytest.fixture
def table(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("TABLE_NAME", "test-items")
    monkeypatch.setenv("STAGE", "test")

    with mock_aws():
        ddb = boto3.resource("dynamodb", region_name="us-east-1")
        tbl = ddb.create_table(
            TableName="test-items",
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        import app

        app._dynamodb = None  # force a fresh resource inside the mock
        yield tbl


def make_event(route, body=None, item_id=None):
    return {
        "routeKey": route,
        "pathParameters": {"id": item_id} if item_id else None,
        "body": json.dumps(body) if body is not None else None,
        "requestContext": {"requestId": "test-request"},
    }
