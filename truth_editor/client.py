import os
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

_LOCAL_ENV = Path(__file__).resolve().parent.parent / ".env"
if _LOCAL_ENV.exists():
    load_dotenv(_LOCAL_ENV, override=False)

if not os.environ.get("ANTHROPIC_API_KEY"):
    raise RuntimeError("ANTHROPIC_API_KEY not set. Add it to ./.env or the environment.")

client = Anthropic(max_retries=4)

MODEL = os.environ.get("TRUTH_EDITOR_MODEL", "claude-opus-4-7")
MAX_INPUT_CHARS = int(os.environ.get("TRUTH_EDITOR_MAX_INPUT_CHARS", "20000"))
