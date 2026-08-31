import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class FakeBlock:
    """Stands in for an Anthropic content block."""

    def __init__(self, type_: str, text: str = ""):
        self.type = type_
        self.text = text


class FakeResponse:
    def __init__(self, blocks):
        self.content = blocks


class FakeMessages:
    """Records each create() call and replays queued responses."""

    def __init__(self):
        self.calls = []
        self.queue = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if not self.queue:
            raise AssertionError("unexpected API call: no response queued")
        return self.queue.pop(0)


class FakeClient:
    def __init__(self):
        self.messages = FakeMessages()


@pytest.fixture
def fake_client(monkeypatch):
    """Replace get_client() everywhere it is imported."""
    client = FakeClient()
    for module in ("extract", "verify", "edit"):
        mod = __import__(f"truth_editor.{module}", fromlist=["get_client"])
        monkeypatch.setattr(mod, "get_client", lambda: client)
    return client


@pytest.fixture
def text_response():
    def _make(text: str):
        return FakeResponse([FakeBlock("text", text)])

    return _make
