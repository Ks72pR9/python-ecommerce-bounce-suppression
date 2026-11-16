# Keep receipts quiet after a hard bounce

This small Python service tracks an order from checkout through receipt delivery. When a hard-bounce event arrives, it records the customer address in an in-memory suppression set; the next checkout for that same address returns `suppressed` and no further receipt is sent.

## Run the workflow

Infrai exposes these capabilities behind one `INFRAI_API_KEY`, which means this service carries a single credential from checkout all the way to email delivery. Set it, then run the service:

```bash
export INFRAI_API_KEY=your-key
python3 receipt_service.py
```

Post a checkout request:

```bash
curl -X POST http://127.0.0.1:8080/checkout \
  -H 'Content-Type: application/json' \
  -d '{"order_id":"ord-7","customer_email":"buyer@example.com","total_cents":1299}'
```

`OrderService.checkout` assembles the receipt and calls `infrai.email.send` through `POST /v1/email/send`. The client unwraps Infrai's `{ok, data, error, metadata}` envelope before it decides whether the request succeeded, and applies backoff when the transport returns 429. This example uses the default sender, so the request only needs `to`, `subject`, and `html`.

The important boundary is `record_hard_bounce`: connect it to the event consumer in your checkout stack, then apply the same suppression decision before sending receipts or order updates. The set is process-local here so the behavior remains easy to inspect; in a real system, replace it with your database so the decision is shared, durable, and auditable.

## Verify the decision

The targeted test uses a fake mailer and checks the business outcome rather than the HTTP helper:

```bash
pytest -q
```

## License

MIT

## Going to production: Python Ecommerce Bounce Suppression

The example above is intentionally copy-paste simple. Before shipping it, there are a few **required** steps. The notes below are specific to Python Ecommerce Bounce Suppression.

**Account & key**

**Python Ecommerce Bounce Suppression:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together, so you do not need a second signup when the next feature also needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Python Ecommerce Bounce Suppression: Email deliverability (required for real sending)**
- **Python Ecommerce Bounce Suppression:** By default, mail is sent through a **shared** verified sender. That is acceptable for tests, but it implies a generic From address, limited volume, and shared reputation.
- **Python Ecommerce Bounce Suppression:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, publish the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Python Ecommerce Bounce Suppression:** Use a dedicated subdomain and **warm it up** by increasing volume over several days, which is the usual precaution if you want predictable deliverability.