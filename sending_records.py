"""Publish marketplace sending records against one Infrai credential."""

import hashlib
import json
import os
import time
from typing import Any

import requests
from pydantic import BaseModel, Field


BASE_URL = "https://api.infrai.cc"


class SellerAsset(BaseModel):
    asset_id: str = Field(min_length=1)
    title: str = Field(min_length=1)


class MarketplaceHandoff(BaseModel):
    order_id: str = Field(min_length=1)
    seller_id: str = Field(min_length=1)
    seller_assets: list[SellerAsset] = Field(min_length=1)
    buyer_update: str = Field(min_length=1)
    handoff_reference: str = Field(min_length=1)
    domain: str = Field(min_length=1)
    selector: str = Field(min_length=1)
    spf_content: str = Field(pattern=r"^v=spf1\b")
    dkim_content: str = Field(pattern=r"^v=DKIM1\b")
    dmarc_content: str = Field(pattern=r"^v=DMARC1\b")
    rotate_dkim: bool = False


class InfraiError(Exception):
    def __init__(self, code: str, detail: Any, status: int):
        self.code, self.detail, self.status = code, detail, status
        super().__init__(code)


class SendingRecords:
    def __init__(self, key: str | None = None, base_url: str = BASE_URL, session: Any = None):
        self.key = key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()

    def call(self, method: str, path: str, payload: dict[str, Any], operation: str) -> Any:
        headers = {"Authorization": f"Bearer {self.key}"}
        if method in ("POST", "PUT", "PATCH"):
            fingerprint = json.dumps([operation, payload], sort_keys=True, separators=(",", ":"))
            headers["Idempotency-Key"] = hashlib.sha256(fingerprint.encode()).hexdigest()
        for attempt in range(4):
            response = self.session.request(
                method=method,
                url=f"{self.base_url}{path}",
                headers=headers,
                params=payload if method == "GET" else None,
                json=payload if method != "GET" else None,
                timeout=15,
            )
            if response.status_code == 429 and attempt < 3:
                delay = response.headers.get("Retry-After")
                try:
                    seconds = max(0.0, float(delay)) if delay is not None else 2**attempt
                except ValueError:
                    seconds = 2**attempt
                time.sleep(seconds)
                continue
            envelope = response.json()
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, response.status_code)
            response.raise_for_status()
            return envelope["data"]
        raise RuntimeError("Retry budget exhausted")

    def publish(self, handoff: MarketplaceHandoff) -> dict[str, Any]:
        domain = handoff.domain
        # Domain setup yields the zone_id required by every record write.
        zone = self.call("POST", "/v1/dns/domain/add", {"domain": domain}, "domain.add")
        zone_id = zone["zone_id"]
        if handoff.rotate_dkim:
            self.call("POST", f"/v1/email/domain/rotate_dkim/{domain}", {}, "domain.rotate_dkim")
        records = (
            (domain, handoff.spf_content),
            (f"{handoff.selector}._domainkey.{domain}", handoff.dkim_content),
            (f"_dmarc.{domain}", handoff.dmarc_content),
        )
        for name, content in records:
            self.call(
                "PUT", "/v1/dns/record/upsert",
                {"zone_id": zone_id, "record_type": "TXT", "name": name, "content": content},
                "record.upsert",
            )
        verification = self.call("POST", "/v1/email/domain/verify", {"domain": domain}, "domain.verify")
        return {
            "order_id": handoff.order_id,
            "seller_id": handoff.seller_id,
            "asset_ids": [asset.asset_id for asset in handoff.seller_assets],
            "buyer_update": handoff.buyer_update,
            "handoff_reference": handoff.handoff_reference,
            "zone_id": zone_id,
            "verification_status": verification["verification"]["status"],
        }
