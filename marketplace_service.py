"""HTTP entry point for a marketplace sending-domain handoff."""

from fastapi import FastAPI, HTTPException

from sending_records import InfraiError, MarketplaceHandoff, SendingRecords


app = FastAPI(title="Marketplace sending records")


@app.post("/handoffs/publish")
def publish_handoff(handoff: MarketplaceHandoff) -> dict:
    try:
        return SendingRecords().publish(handoff)
    except InfraiError as error:
        status = error.status if 400 <= error.status < 500 else 502
        raise HTTPException(status_code=status, detail={"code": error.code, "error": error.detail}) from error
