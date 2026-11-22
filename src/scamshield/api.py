"""HTTP API. Run: ``uvicorn scamshield.api:app``.

Privacy by design: the submitted message is analysed in memory and never
stored, logged or echoed back. Links in the message are never fetched.
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from .engine import ENGINE_VERSION, MAX_MESSAGE_LENGTH, check_message, load_rules
from .ratelimit import SlidingWindowLimiter

app = FastAPI(
    title="Scam Shield UAE",
    version=ENGINE_VERSION,
    description="Recognises selected documented UAE scam patterns and points to official channels.",
)
limiter = SlidingWindowLimiter(max_requests=30, window_seconds=60)


class CheckRequest(BaseModel):
    message: str = Field(min_length=1, max_length=MAX_MESSAGE_LENGTH)


@app.get("/health")
def health():
    return {"status": "ok", "engine_version": ENGINE_VERSION}


@app.get("/rules")
def rules_metadata():
    doc = load_rules()
    return {
        "version": doc["version"],
        "rules": [
            {"id": r["id"], "category": r["category"], "title": r["title"],
             "source": r["source"], "reviewed": r["reviewed"]}
            for r in doc["rules"] if r["status"] == "active"
        ],
    }


@app.post("/check")
def check(req: CheckRequest, request: Request):
    # Behind a reverse proxy, configure uvicorn --proxy-headers so this is the real client IP.
    client = request.client.host if request.client else "unknown"
    if not limiter.allow(client):
        raise HTTPException(status_code=429, detail="Too many requests. Please wait a minute.")
    try:
        return check_message(req.message).to_dict()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
