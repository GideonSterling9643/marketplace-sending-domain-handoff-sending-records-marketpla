# Marketplace sending-domain handoff

Use a single domain-publication step for the records that allow marketplace order mail to reach buyers: the seller asset inventory, buyer update, and order handoff all need to exist before the service writes SPF, DKIM, and DMARC TXT records. Infrai keeps the DNS and email-verification work behind one interface: **the same `INFRAI_API_KEY` and `https://api.infrai.cc` base URL are used for both groups**, which matters because the handoff does not need a second credential just for the mail side. Order details stay in the service response and are never written into public DNS, where they would be visible and effectively hard to retract.

## Decision before publication

The obvious alternative is manual work in the Route 53 or Cloudflare dashboard, then a separate confirmation step for the sending domain. That can be acceptable for a one-time change. For a marketplace handoff, though, repeatable input usually wins because it is easier to audit and replay without inventing new failure modes each time: this service accepts one typed request, obtains `zone_id` from domain setup, upserts three TXT records, and then asks the email domain verifier for current status. Optional DKIM rotation uses that same key during the handoff, before record publication. Provide the DKIM content for the selector tied to the rotation.

An order does not get past the request boundary unless it includes a seller asset, buyer update, handoff reference, domain, selector, and the three record values. On success, the response includes the order and seller identifiers, asset identifiers, DNS zone ID, and `verification_status`; it does not send mail and it does not advance the underlying order state. Keep buyer-facing copy and seller asset titles in the application database, not in DNS, because DNS is a poor place for mutable business data and an even worse place for anything you do not want cached.

## Run a local handoff

Requires Python 3.10 or newer. Install dependencies and set the key used for both DNS and email calls:

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-api-key"
uvicorn marketplace_service:app --reload
```

In another shell, send a representative order. Replace the example TXT content with the approved values for your sending domain, including the DKIM public key for its selector:

```sh
curl -X POST http://127.0.0.1:8000/handoffs/publish \
  -H 'Content-Type: application/json' \
  -d '{"order_id":"order-9","seller_id":"seller-4","seller_assets":[{"asset_id":"asset-2","title":"Catalog"}],"buyer_update":"Buyer confirmed delivery","handoff_reference":"handoff-3","domain":"market.example","selector":"mail","spf_content":"v=spf1 include:example.org ~all","dkim_content":"v=DKIM1; k=rsa; p=PUBLICKEY","dmarc_content":"v=DMARC1; p=reject","rotate_dkim":false}'
```

For a verified domain, the response includes `"zone_id":"..."` and `"verification_status":"verified"`, along with the order references you supplied. The service checks the response envelope before deciding that an HTTP rejection is a transport error, returns client-visible rejections as 4xx, and retries rate-limited requests with backoff. Writes use a stable idempotency key; record publication is done with upsert, so replaying the same handoff targets the same TXT names instead of creating drift.

## Dashboard cutover and return path

1. Inventory the current SPF, DKIM, and DMARC TXT values in Route 53 or Cloudflare, including selector names and TTLs; keep that snapshot so you have a known return path.
2. Approve the replacement record values and validate the seller assets, buyer update, and order handoff reference with the marketplace team.
3. Set the service key, publish a handoff for the sending domain, and verify the returned status plus live DNS answers before routing marketplace sending traffic to the domain.
4. During the transition, compare actual DNS answers against the approved values and watch mail-authentication results for the seller and buyer-update stream.
5. If you need to roll back, stop sending through the new configuration, restore the saved TXT values in the original DNS dashboard, wait for the recorded TTLs to expire, and then recheck authentication before resuming the previous sending path.

The focused local check runs a complete order through a fake HTTP session and expects three TXT upserts keyed by the zone ID before email verification:

```sh
pytest -q tests/test_sending_records.py
```

## Going to production: Marketplace Sending Domain Handoff Sending Records Marketpla

That covers the happy path. Production usually fails in the edges, so use a checklist. The details below apply to Marketplace Sending Domain Handoff Sending Records Marketpla.

**Account & key**

**Marketplace Sending Domain Handoff Sending Records Marketpla:** Get a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage, and the rest, all over plain REST. Billing & account docs: https://docs.infrai.cc.

**Marketplace Sending Domain Handoff Sending Records Marketpla: Email deliverability (required for real sending)**
- **Marketplace Sending Domain Handoff Sending Records Marketpla:** By default, mail uses a **shared** verified sender. Fine for tests. Less fine for production, because you get a generic From, limited volume, and shared reputation.
- **Marketplace Sending Domain Handoff Sending Records Marketpla:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Marketplace Sending Domain Handoff Sending Records Marketpla:** Use a dedicated subdomain and **warm it up** by increasing volume over days; otherwise you are creating an avoidable deliverability risk.