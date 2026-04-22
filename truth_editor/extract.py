import json
from typing import List

from pydantic import BaseModel

from .client import MODEL, client


class ClaimList(BaseModel):
    claims: List[str]


EXTRACT_SYSTEM = """You extract atomic factual claims from text for independent fact-checking.

A factual claim is:
- A single, verifiable statement about the world
- Self-contained (resolve pronouns and anaphora)
- Not an opinion, instruction, hypothetical, or first-person statement

Extract claims in the original meaning. Do not invent or infer claims that are not explicitly supported by the text. If a sentence contains multiple claims, split them."""

EXTRACT_USER = """Extract factual claims from this text:

<text>
{text}
</text>

Return a JSON object with a "claims" array of strings. If no verifiable factual claims exist, return {{"claims": []}}."""


def extract_claims(text: str) -> list[str]:
    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=EXTRACT_SYSTEM,
        messages=[{"role": "user", "content": EXTRACT_USER.format(text=text)}],
        output_config={
            "format": {
                "type": "json_schema",
                "schema": {
                    "type": "object",
                    "properties": {
                        "claims": {
                            "type": "array",
                            "items": {"type": "string"},
                        }
                    },
                    "required": ["claims"],
                    "additionalProperties": False,
                },
            }
        },
    )
    text_block = next((b.text for b in response.content if b.type == "text"), "")
    return ClaimList.model_validate(json.loads(text_block)).claims
