"""Integration / smoke test against a DEPLOYED stack.

Usage:
    API_URL=https://xxxx.execute-api.ap-south-1.amazonaws.com/dev \
        python tests/integration/test_api.py
"""
import json
import os
import sys
import urllib.error
import urllib.request

API_URL = os.environ.get("API_URL", "").rstrip("/")
if not API_URL:
    sys.exit("Set API_URL to the deployed API base URL")


def request(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        API_URL + path, data=data, method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode()
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as err:
        raw = err.read().decode()
        return err.code, (json.loads(raw) if raw else None)


def main():
    status, body = request("GET", "/health")
    assert status == 200 and body["status"] == "ok", (status, body)
    print("OK  GET /health")

    status, item = request("POST", "/items", {"name": "smoke-test"})
    assert status == 201, (status, item)
    print("OK  POST /items")

    status, got = request("GET", f"/items/{item['id']}")
    assert status == 200 and got["name"] == "smoke-test", (status, got)
    print("OK  GET /items/{id}")

    status, _ = request("DELETE", f"/items/{item['id']}")
    assert status == 204, status
    print("OK  DELETE /items/{id}")

    status, _ = request("GET", f"/items/{item['id']}")
    assert status == 404, status
    print("OK  item is gone (404)")
    print("All smoke tests passed")


if __name__ == "__main__":
    main()
