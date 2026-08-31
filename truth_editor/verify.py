import json
import re
from typing import List, Literal

from pydantic import BaseModel

from .client import MODEL, get_client


class Verdict(BaseModel):
    status: Literal["SUPPORTED", "CONTRADICTED", "UNVERIFIED"]
    confidence: Literal["high", "medium", "low"]
    note: str
    sources: List[str] = []


VERIFY_SYSTEM = """You are a strict fact-checker. Given a claim, use the web_search tool to verify it against independent sources.

Verdicts:
- SUPPORTED: multiple credible web sources clearly confirm the claim
- CONTRADICTED: credible web sources clearly contradict the claim
- UNVERIFIED: insufficient, weak, or conflicting evidence

Be conservative. Prefer UNVERIFIED over SUPPORTED when sources are weak, stale, or ambiguous. Do not rely on prior knowledge — only evidence surfaced by the web search tool counts.

After you finish searching, respond with ONLY a single JSON object matching this schema:
{
  "status": "SUPPORTED" | "CONTRADICTED" | "UNVERIFIED",
  "confidence": "high" | "medium" | "low",
  "note": "one-sentence explanation citing the evidence",
  "sources": ["url1", "url2", ...]
}

No prose before or after the JSON."""


def _extract_json(text: str) -> dict:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        return json.loads(fence.group(1))
    start = text.find("{")
    if start >= 0:
        obj, _ = json.JSONDecoder().raw_decode(text[start:])
        return obj
    return json.loads(text)


def verify_claim(claim: str) -> Verdict:
    response = get_client().messages.create(
        model=MODEL,
        max_tokens=4096,
        system=VERIFY_SYSTEM,
        tools=[
            {
                "type": "web_search_20260209",
                "name": "web_search",
                "max_uses": 3,
            }
        ],
        messages=[
            {
                "role": "user",
                "content": f"Claim to verify:\n\n{claim}",
            }
        ],
    )

    final_text = ""
    for block in reversed(response.content):
        if block.type == "text" and block.text.strip():
            final_text = block.text
            break

    try:
        data = _extract_json(final_text)
        return Verdict.model_validate(data)
    except Exception as exc:
        return Verdict(
            status="UNVERIFIED",
            confidence="low",
            note=f"Could not parse verdict: {exc}. Raw: {final_text[:200]}",
            sources=[],
        )
