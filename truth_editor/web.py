from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from .edit import ClaimVerdict, rewrite_text
from .extract import extract_claims
from .verify import verify_claim

app = FastAPI(title="Truth Editor")

_STATIC = Path(__file__).resolve().parent.parent / "static"


class CheckRequest(BaseModel):
    text: str
    rewrite: bool = False


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (_STATIC / "index.html").read_text()


@app.post("/api/check")
def check(req: CheckRequest) -> dict:
    claims = extract_claims(req.text)
    if not claims:
        return {
            "claims": [],
            "cleaned": req.text if req.rewrite else None,
        }

    with ThreadPoolExecutor(max_workers=5) as pool:
        verdicts = list(pool.map(verify_claim, claims))

    results = [ClaimVerdict(c, v) for c, v in zip(claims, verdicts)]

    payload = {
        "claims": [
            {
                "text": cv.claim,
                "status": cv.verdict.status,
                "confidence": cv.verdict.confidence,
                "note": cv.verdict.note,
                "sources": cv.verdict.sources,
            }
            for cv in results
        ],
    }
    if req.rewrite:
        payload["cleaned"] = rewrite_text(req.text, results)
    return payload
