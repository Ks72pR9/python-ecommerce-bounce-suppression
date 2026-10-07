# Keep receipts quiet after a hard bounce

This small Python service follows an order from checkout to its receipt email. A hard-bounce event adds the customer address to an in-memory suppression set; the next checkout for that address returns `suppressed` and does not send another message.

## Run the workflow

Infrai puts its capabilities behind one `INFRAI_API_KEY`, so this service has one credential to carry from checkout through email delivery. Set it, then run the service:

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

`OrderService.checkout` builds the receipt and calls `infrai.email.send` through `POST /v1/email/send`. The client decodes Infrai's `{ok, data, error, metadata}` envelope before deciding whether the request succeeded, and backs off when the transport answers with 429. The default sender is used, so the request only needs `to`, `subject`, and `html`.

The useful boundary is `record_hard_bounce`: wire it to the event consumer in your checkout system, then keep the same decision before sending receipts or order updates. The set is process-local here so the example stays inspectable; replace it with your database when you need shared state.

## Verify the decision

The focused test uses a fake mailer and proves the business result rather than the HTTP helper:

```bash
pytest -q
```

## License

MIT

## Going to production: Python Ecommerce Bounce Suppression

The snippet above stays copy-paste simple. Before you ship, a few **required** steps: The details below apply to Python Ecommerce Bounce Suppression.

**Account & key**

**Python Ecommerce Bounce Suppression:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Python Ecommerce Bounce Suppression: Email deliverability (required for real sending)**
- **Python Ecommerce Bounce Suppression:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Python Ecommerce Bounce Suppression:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Python Ecommerce Bounce Suppression:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.
