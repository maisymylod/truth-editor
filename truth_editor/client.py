import os
from functools import lru_cache
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

_LOCAL_ENV = Path(__file__).resolve().parent.parent / ".env"
if _LOCAL_ENV.exists():
    load_dotenv(_LOCAL_ENV, override=False)

MODEL = os.environ.get("TRUTH_EDITOR_MODEL", "claude-opus-4-7")
MAX_INPUT_CHARS = int(os.environ.get("TRUTH_EDITOR_MAX_INPUT_CHARS", "20000"))


@lru_cache(maxsize=1)
def get_client() -> Anthropic:
    """Build the Anthropic client on first use.

    The key is checked here rather than at import time so the package can be
    imported, inspected, and tested without credentials. Callers that actually
    reach the API still fail fast with the same message.
    """
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError(
            "ANTHROPIC_API_KEY not set. Add it to ./.env or the environment."
        )
    return Anthropic(max_retries=4)
