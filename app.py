"""Web wrapper around emailchk.py — turns the CLI into a FastAPI service."""
from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from emailchk import FreeSession, check_email_api

app = FastAPI(title="Email Validator API", version="1.0.0")

# Enable CORS for the Next.js frontend (dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_free_session: Optional[FreeSession] = None


def _free() -> FreeSession:
    global _free_session
    if _free_session is None:
        s = FreeSession()
        s._init_session()
        _free_session = s
    return _free_session


class CheckRequest(BaseModel):
    email: str
    api_key: Optional[str] = None
    mode: str = "auto"


class BulkRequest(BaseModel):
    emails: list[str]
    api_key: Optional[str] = None
    mode: str = "auto"


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/check")
def check(req: CheckRequest) -> dict:
    if not req.email.strip():
        raise HTTPException(400, "email is required")
    if req.api_key:
        return check_email_api(req.email, api_key=req.api_key, mode=req.mode)
    return _free().check(req.email)


@app.post("/api/check-bulk")
def check_bulk(req: BulkRequest) -> dict:
    emails = [e.strip() for e in req.emails if e and e.strip()]
    if not emails:
        raise HTTPException(400, "emails is required")
    if len(emails) > 50:
        raise HTTPException(400, "max 50 emails per request")

    results = []
    sess = None if req.api_key else _free()
    for e in emails:
        try:
            if req.api_key:
                results.append(check_email_api(e, api_key=req.api_key, mode=req.mode))
            else:
                results.append(sess.check(e))
        except Exception as ex:  # noqa: BLE001
            results.append({"email": e, "status": "error", "_error": str(ex)})
    return {"count": len(results), "results": results}



if __name__ == "__main__":
    import os
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
