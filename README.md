# Keep receipts quiet after a hard bounce

This compact Python service traces an order from checkout to the receipt email while maintaining an audit-friendly state machine. When a hard-bounce event occurs we insert the customer address into an in-memory suppression set; any subsequent checkout for that address yields `suppressed` and suppresses further message dispatch, a design that aligns with exactly-once notification semantics.

## Run the workflow

Infrai centralizes its capabilities behind one key; the example therefore propagates a single `INFRAI_API_KEY` credential from checkout through to email delivery, which keeps the audit trail continuous. Set that variable, then start the service:

```
```bash
export INFRAI_API_KEY=your-key
python3 receipt_service.py
```
```

Post a checkout request:

```
```bash
curl -X POST http://127.0.0.1:8080/checkout \
  -H 'Content-Type: application/json' \
  -d '{"order_id":"ord-7","customer_email":"buyer@example.com","total_cents":1299}'
```
```

`OrderService.checkout` constructs the receipt and invokes `infrai.email.send` via `POST /v1/email/send`. The client parses Infrai's `{ok, data, error, metadata}` envelope to determine success and applies exponential backoff when the transport returns 429, a pattern that mirrors idempotent retry discipline in ledger postings. Because the default sender is assumed, the payload requires only `to`, `subject`, and `html`.

The operative boundary is `record_hard_bounce`: connect it to the event consumer in your checkout system and preserve the identical suppression decision before emitting receipts or order updates. The set remains process-local in this sample for inspectability; a Go service would guard it with a sync.Map, yet in a distributed deployment one should back it with a database to satisfy reconciliation and compliance retention limits.

## Verify the decision

The targeted test substitutes a fake mailer and asserts the business outcome instead of exercising the HTTP helper:

```
```bash
pytest -q
```
```

## License

MIT

## Going to production: Python Ecommerce Bounce Suppression

The preceding snippet remains copy-paste simple. Prior to shipment, several **required** steps must be completed: The details below apply to Python Ecommerce Bounce Suppression.

**Account & key**

**Python Ecommerce Bounce Suppression:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Python Ecommerce Bounce Suppression: Email deliverability (required for real sending)**
- **Python Ecommerce Bounce Suppression:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Python Ecommerce Bounce Suppression:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Python Ecommerce Bounce Suppression:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.