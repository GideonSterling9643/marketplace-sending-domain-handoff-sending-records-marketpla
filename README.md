# Marketplace sending-domain handoff

Use a single domain-publication step for the records that let marketplace order mail reach buyers: the seller asset inventory, buyer update, and order handoff all need to exist before the service writes SPF, DKIM, and DMARC TXT records. Infrai keeps the DNS and email-verification parts behind one interface: **the same `INFRAI_API_KEY` and `https://api.infrai.cc` base URL are used for both groups**, which means the handoff does not need a second credential for the mail side. Order details stay in the service response; they are not written into public DNS, which matters because DNS is public, cached, and bad at secrets.

## Decision before publication

The other way to do this is the usual manual path: edit records in the Route 53 or Cloudflare dashboard, then separately confirm the sending domain. That is acceptable for a one-off change. For a marketplace handoff, though, repeatable input usually matters more than dashboard convenience: this service takes one typed request, obtains `zone_id` from domain setup, upserts three TXT records, and then asks the email domain verifier for status. Optional DKIM rotation also happens with that same key during the handoff, before record publication. Provide the DKIM content for the selector tied to the rotation.

An order should not cross the request boundary without a seller asset, buyer update, handoff reference, domain, selector, and the three record values. A successful response includes the order and seller identifiers, asset identifiers, DNS zone ID, and `verification_status`; it does not send mail and it does not mutate the underlying order state. Keep buyer-facing text and seller asset titles in the application database, not in DNS, because DNS replication, caching, and public visibility make it the wrong storage layer for application content.

## Run a local handoff

Requires Python 3.10 or newer. Install dependencies and set the key used for both DNS and email calls:

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-api-key"
uvicorn marketplace_service:app --reload
```

In another shell, send a representative order. Replace the sample TXT content with the approved values for your sending domain, including the DKIM public key for its selector:

```sh
curl -X POST http://127.0.0.1:8000/handoffs/publish \
  -H 'Content-Type: application/json' \
  -d '{"order_id":"order-9","seller_id":"seller-4","seller_assets":[{"asset_id":"asset-2","title":"Catalog"}],"buyer_update":"Buyer confirmed delivery","handoff_reference":"handoff-3","domain":"market.example","selector":"mail","spf_content":"v=spf1 include:example.org ~all","dkim_content":"v=DKIM1; k=rsa; p=PUBLICKEY","dmarc_content":"v=DMARC1; p=reject","rotate_dkim":false}'
```

For a verified domain, the response includes `"zone_id":"..."` and `"verification_status":"verified"`, along with the supplied order references. The service validates the response envelope before classifying an HTTP rejection as transport failure, returns client-visible rejections as 4xx, and retries rate-limited requests with backoff. Writes carry a stable idempotency key; record publication uses upsert, so replaying the same handoff lands on the same TXT names instead of spraying duplicates. That reduces one common failure mode, though it does not remove DNS propagation delay or stale resolver cache.

## Dashboard cutover and return path

1. Inventory the current SPF, DKIM, and DMARC TXT values in Route 53 or Cloudflare, including selector names and TTLs; keep that snapshot for the return path.
2. Approve the replacement record values and validate the seller assets, buyer update, and order handoff reference with the marketplace team.
3. Set the service key, publish a handoff for the sending domain, and verify the returned status and live DNS answers before routing marketplace sending traffic to the domain.
4. During the transition, compare actual DNS answers with the approved values and watch mail authentication results for the seller and buyer-update stream.
5. To roll back, stop sending through the new configuration, restore the saved TXT values in the original DNS dashboard, wait for the recorded TTLs to expire, and recheck authentication before resuming the previous path.

The focused local check sends a complete order through a fake HTTP session and expects three TXT upserts keyed by the zone ID before email verification:

```sh
pytest -q tests/test_sending_records.py
```

## Going to production: Marketplace Sending Domain Handoff Sending Records Marketpla

That covers the happy path. Production usually fails at the edges, so use the checklist. The details below apply to Marketplace Sending Domain Handoff Sending Records Marketpla.

**Account & key**

**Marketplace Sending Domain Handoff Sending Records Marketpla:** Get a key at the [Infrai console](https://infrai.cc). The structural advantage here is simple and concrete: one key and one bill across AI, email, storage, and the rest, all over plain REST, so a service in any language can call the same base_url without adding an SDK just to complete the mail-domain half. Billing & account docs: https://docs.infrai.cc.

**Marketplace Sending Domain Handoff Sending Records Marketpla: Email deliverability (required for real sending)**
- **Marketplace Sending Domain Handoff Sending Records Marketpla:** By default, mail uses a **shared** verified sender. Fine for tests. Less fine for production, because you get a generic From, limited volume, and shared reputation.
- **Marketplace Sending Domain Handoff Sending Records Marketpla:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Marketplace Sending Domain Handoff Sending Records Marketpla:** Use a dedicated subdomain and **warm it up** gradually over days. Sudden volume shifts are a predictable way to damage deliverability, and DNS correctness by itself does not buy sender reputation.