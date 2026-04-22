import os
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

_SHARED_ENV = Path.home() / "goldsmith-report" / "config.env"
_LOCAL_ENV = Path(__file__).resolve().parent.parent / ".env"

for path in (_SHARED_ENV, _LOCAL_ENV):
    if path.exists():
        load_dotenv(path, override=False)

if not os.environ.get("ANTHROPIC_API_KEY"):
    raise RuntimeError(
        "ANTHROPIC_API_KEY not set. Add it to ~/.env, ./.env, "
        f"or {_SHARED_ENV}."
    )

client = Anthropic()

MODEL = "claude-opus-4-7"
