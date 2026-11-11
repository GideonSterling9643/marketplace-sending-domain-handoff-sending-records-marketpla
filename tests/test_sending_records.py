from sending_records import MarketplaceHandoff, SendingRecords


class FakeResponse:
    def __init__(self, data):
        self.status_code = 200
        self.headers = {}
        self.data = data

    def json(self):
        return {"ok": True, "data": self.data, "error": None, "metadata": {}}

    def raise_for_status(self):
        pass


class FakeSession:
    def __init__(self):
        self.calls = []

    def request(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs["url"].endswith("/dns/domain/add"):
            return FakeResponse({"zone_id": "zone-17"})
        if kwargs["url"].endswith("/email/domain/verify"):
            return FakeResponse({"verification": {"status": "verified"}})
        return FakeResponse({})


def test_handoff_publishes_three_txt_records_before_verification():
    session = FakeSession()
    handoff = MarketplaceHandoff(
        order_id="order-9", seller_id="seller-4",
        seller_assets=[{"asset_id": "asset-2", "title": "Catalog"}],
        buyer_update="Buyer confirmed delivery", handoff_reference="handoff-3",
        domain="market.example", selector="mail", spf_content="v=spf1 include:example.org ~all",
        dkim_content="v=DKIM1; k=rsa; p=PUBLICKEY", dmarc_content="v=DMARC1; p=reject",
    )
    result = SendingRecords(key="test-key", session=session).publish(handoff)
    writes = session.calls[1:4]
    assert result["verification_status"] == "verified"
    assert result["asset_ids"] == ["asset-2"]
    assert [call["json"]["name"] for call in writes] == [
        "market.example", "mail._domainkey.market.example", "_dmarc.market.example"
    ]
    assert all(call["method"] == "PUT" and call["json"]["zone_id"] == "zone-17" for call in writes)
    assert all(call["json"]["record_type"] == "TXT" and "Idempotency-Key" in call["headers"] for call in writes)
    assert session.calls[-1]["url"].endswith("/v1/email/domain/verify")
