"""Items API - a small AWS Lambda handler behind an API Gateway HTTP API.

Routes (payload format v2, matched on event["routeKey"]):
    GET    /health
    POST   /items
    GET    /items
    GET    /items/{id}
    DELETE /items/{id}
"""
import json
import logging
import os
import time
import uuid
from decimal import Decimal

import boto3

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

_dynamodb = None


def _table():
    """Create the DynamoDB table handle lazily (re-used across warm invocations)."""
    global _dynamodb
    if _dynamodb is None:
        _dynamodb = boto3.resource("dynamodb")
    return _dynamodb.Table(os.environ["TABLE_NAME"])


class _JSONEncoder(json.JSONEncoder):
    """DynamoDB returns numbers as Decimal; convert them for JSON."""

    def default(self, o):
        if isinstance(o, Decimal):
            return int(o) if o % 1 == 0 else float(o)
        return super().default(o)


def _response(status, body):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, cls=_JSONEncoder),
    }


def health(event):
    return _response(200, {"status": "ok", "stage": os.environ.get("STAGE", "unknown")})


def create_item(event):
    try:
        payload = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _response(400, {"message": "Body must be valid JSON"})

    name = payload.get("name")
    if not isinstance(name, str) or not name.strip():
        return _response(400, {"message": "'name' is required"})

    item = {
        "id": str(uuid.uuid4()),
        "name": name.strip(),
        "description": str(payload.get("description", "")),
        "createdAt": int(time.time()),
    }
    _table().put_item(Item=item)
    logger.info("created item %s", item["id"])
    return _response(201, item)


def list_items(event):
    result = _table().scan(Limit=50)
    return _response(200, {"items": result.get("Items", [])})


def get_item(event):
    item_id = event["pathParameters"]["id"]
    result = _table().get_item(Key={"id": item_id})
    item = result.get("Item")
    if not item:
        return _response(404, {"message": "Item not found"})
    return _response(200, item)


def delete_item(event):
    item_id = event["pathParameters"]["id"]
    _table().delete_item(Key={"id": item_id})
    return {"statusCode": 204, "headers": {}, "body": ""}


ROUTES = {
    "GET /health": health,
    "POST /items": create_item,
    "GET /items": list_items,
    "GET /items/{id}": get_item,
    "DELETE /items/{id}": delete_item,
}


def lambda_handler(event, context):
    route = event.get("routeKey", "")
    handler = ROUTES.get(route)
    if handler is None:
        return _response(404, {"message": f"No route for {route}"})
    try:
        return handler(event)
    except Exception:  # noqa: BLE001 - last-resort guard, logged with stack trace
        logger.exception("unhandled error on %s", route)
        return _response(500, {"message": "Internal server error"})
