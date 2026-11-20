import json

import app
from conftest import make_event


def call(route, body=None, item_id=None):
    return app.lambda_handler(make_event(route, body, item_id), None)


def test_health(table):
    resp = call("GET /health")
    assert resp["statusCode"] == 200
    assert json.loads(resp["body"])["status"] == "ok"


def test_create_and_get_item(table):
    created = call("POST /items", {"name": "Learn Lambda", "description": "zero to hero"})
    assert created["statusCode"] == 201
    item = json.loads(created["body"])
    assert item["name"] == "Learn Lambda"

    fetched = call("GET /items/{id}", item_id=item["id"])
    assert fetched["statusCode"] == 200
    assert json.loads(fetched["body"])["id"] == item["id"]


def test_list_items(table):
    call("POST /items", {"name": "one"})
    call("POST /items", {"name": "two"})
    resp = call("GET /items")
    assert resp["statusCode"] == 200
    assert len(json.loads(resp["body"])["items"]) == 2


def test_get_missing_item_returns_404(table):
    resp = call("GET /items/{id}", item_id="does-not-exist")
    assert resp["statusCode"] == 404


def test_delete_item(table):
    item = json.loads(call("POST /items", {"name": "temp"})["body"])
    assert call("DELETE /items/{id}", item_id=item["id"])["statusCode"] == 204
    assert call("GET /items/{id}", item_id=item["id"])["statusCode"] == 404


def test_create_requires_name(table):
    assert call("POST /items", {"description": "no name"})["statusCode"] == 400


def test_invalid_json_returns_400(table):
    event = make_event("POST /items")
    event["body"] = "{not json"
    assert app.lambda_handler(event, None)["statusCode"] == 400


def test_unknown_route_returns_404(table):
    assert call("GET /nope")["statusCode"] == 404
