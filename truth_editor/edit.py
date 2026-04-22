from dataclasses import dataclass
from typing import List

from .client import MODEL, client
from .verify import Verdict


@dataclass
class ClaimVerdict:
    claim: str
    verdict: Verdict


_MARKERS = {
    "SUPPORTED": "✓",
    "CONTRADICTED": "✗",
    "UNVERIFIED": "?",
}


def build_annotated(original: str, results: List[ClaimVerdict]) -> str:
    lines = [original.rstrip(), "", "---", "", "## Claim audit", ""]
    for i, cv in enumerate(results, 1):
        marker = _MARKERS[cv.verdict.status]
        lines.append(f"{i}. [{marker} {cv.verdict.status}] {cv.claim}")
        lines.append(f"   {cv.verdict.note} (confidence: {cv.verdict.confidence})")
        if cv.verdict.sources:
            for src in cv.verdict.sources[:3]:
                lines.append(f"   - {src}")
        lines.append("")
    return "\n".join(lines)


REWRITE_SYSTEM = """You edit text to reflect fact-check verdicts.

Rules:
- Keep SUPPORTED claims exactly as written
- Remove or correct CONTRADICTED claims. If corrected, add a trailing "[corrected]" marker
- For UNVERIFIED claims, mark them inline with "[unverified]" at the end of the sentence

Preserve the original style, tone, and structure. Make the minimum edits required. Return only the edited text, no preamble or commentary."""


def rewrite_text(original: str, results: List[ClaimVerdict]) -> str:
    verdicts_str = "\n".join(
        f"- [{cv.verdict.status}] \"{cv.claim}\" — {cv.verdict.note}"
        for cv in results
    )
    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=REWRITE_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Original text:\n<text>\n{original}\n</text>\n\n"
                    f"Fact-check verdicts:\n{verdicts_str}\n\n"
                    "Return the edited text."
                ),
            }
        ],
    )
    return next((b.text for b in response.content if b.type == "text"), original)
