import os

import pytest

from truth_editor import client as client_module


def test_modules_import_without_credentials():
    """The package must be importable with no API key, or it cannot be tested."""
    import truth_editor.cli  # noqa: F401
    import truth_editor.edit  # noqa: F401
    import truth_editor.extract  # noqa: F401
    import truth_editor.verify  # noqa: F401
    import truth_editor.web  # noqa: F401


def test_get_client_fails_fast_without_a_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    client_module.get_client.cache_clear()
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY not set"):
        client_module.get_client()


def test_get_client_is_cached(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
    client_module.get_client.cache_clear()
    assert client_module.get_client() is client_module.get_client()
    client_module.get_client.cache_clear()


def test_max_input_chars_is_an_int():
    assert isinstance(client_module.MAX_INPUT_CHARS, int)
    assert client_module.MAX_INPUT_CHARS > 0
