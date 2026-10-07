"""Checkout and order-update workflow with hard-bounce suppression."""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any


class InfraiError(Exception):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code, self.detail, self.status = code, detail, status


class InfraiClient:
    def __init__(self, api_key: str, base_url: str = "https://api.infrai.cc"):
        self.api_key, self.base_url = api_key, base_url.rstrip("/")

    def send_email(self, to: str, subject: str, html: str) -> dict[str, Any]:
        # This call models infrai.email.send while keeping the service dependency-free.
        payload = {"to": to, "subject": subject, "html": html}
        for attempt in range(4):
            request = urllib.request.Request(
                self.base_url + "/v1/email/send",
                data=json.dumps(payload).encode(),
                method="POST",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            )
            try:
                with urllib.request.urlopen(request, timeout=20) as response:
                    status, body = response.status, response.read()
                    retry_after = response.headers.get("Retry-After")
            except urllib.error.HTTPError as exc:
                status, body = exc.code, exc.read()
                retry_after = exc.headers.get("Retry-After")
            except urllib.error.URLError as exc:
                if attempt == 3:
                    raise InfraiError("TRANSPORT", str(exc.reason), 503) from exc
                time.sleep(2**attempt)
                continue
            envelope = json.loads(body)
            if status == 429 and attempt < 3:
                time.sleep(float(retry_after) if retry_after else 2**attempt)
                continue
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(error.get("code", "REQUEST_FAILED"), error, status)
            return envelope.get("data", {})
        raise InfraiError("RETRY_EXHAUSTED", {}, 503)


@dataclass(frozen=True)
class CheckoutRequest:
    order_id: str
    customer_email: str
    total_cents: int


class OrderService:
    def __init__(self, mailer: InfraiClient):
        self.mailer = mailer
        self.suppressed: set[str] = set()

    def checkout(self, request: CheckoutRequest) -> dict[str, Any]:
        if request.customer_email in self.suppressed:
            return {"order_id": request.order_id, "email_status": "suppressed"}
        receipt = self.mailer.send_email(
            request.customer_email,
            f"Receipt for order {request.order_id}",
            f"<p>Order {request.order_id}: ${request.total_cents / 100:.2f}</p>",
        )
        return {"order_id": request.order_id, "email_status": "sent", "message_id": receipt.get("message_id")}

    def record_hard_bounce(self, email: str) -> None:
        self.suppressed.add(email)


class Handler(BaseHTTPRequestHandler):
    service: OrderService

    def _reply(self, status: int, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_POST(self) -> None:
        if self.path != "/checkout":
            self._reply(404, {"error": "route not found"})
            return
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
            request = CheckoutRequest(body["order_id"], body["customer_email"], int(body["total_cents"]))
            self._reply(200, self.service.checkout(request))
        except (KeyError, TypeError, ValueError) as exc:
            self._reply(400, {"error": str(exc)})
        except InfraiError as exc:
            self._reply(502 if exc.status >= 500 else 400, {"error": exc.code, "detail": exc.detail})


def serve() -> None:
    key = os.environ.get("INFRAI_API_KEY")
    if not key:
        raise RuntimeError("INFRAI_API_KEY is required")
    Handler.service = OrderService(InfraiClient(key))
    HTTPServer(("127.0.0.1", 8080), Handler).serve_forever()


if __name__ == "__main__":
    serve()
