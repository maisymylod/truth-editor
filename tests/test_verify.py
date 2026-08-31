import json

from truth_editor.verify import Verdict, _extract_json, verify_claim


class TestExtractJson:
    def test_bare_object(self):
        assert _extract_json('{"a": 1}') == {"a": 1}

    def test_fenced_with_language_tag(self):
        assert _extract_json('```json\n{"a": 1}\n```') == {"a": 1}

    def test_fenced_without_language_tag(self):
        assert _extract_json('```\n{"a": 1}\n```') == {"a": 1}

    def test_object_preceded_by_prose(self):
        assert _extract_json('Here is my verdict:\n{"a": 1}') == {"a": 1}

    def test_object_followed_by_prose(self):
        assert _extract_json('{"a": 1}\nThat is my answer.') == {"a": 1}

    def test_surrounding_whitespace(self):
        assert _extract_json('\n\n  {"a": 1}  \n') == {"a": 1}


VERDICT = {
    "status": "SUPPORTED",
    "confidence": "high",
    "note": "Two independent sources confirm this.",
    "sources": ["https://example.com/a", "https://example.com/b"],
}


def test_parses_a_well_formed_verdict(fake_client, text_response):
    fake_client.messages.queue.append(text_response(json.dumps(VERDICT)))
    v = verify_claim("The Earth orbits the Sun.")
    assert v.status == "SUPPORTED"
    assert v.confidence == "high"
    assert len(v.sources) == 2


def test_sources_default_to_empty_when_absent(fake_client, text_response):
    payload = {k: v for k, v in VERDICT.items() if k != "sources"}
    fake_client.messages.queue.append(text_response(json.dumps(payload)))
    assert verify_claim("a claim").sources == []


def test_unparseable_output_degrades_to_unverified(fake_client, text_response):
    """A bad reply must never be reported as SUPPORTED."""
    fake_client.messages.queue.append(text_response("the model rambled and never emitted JSON"))
    v = verify_claim("a claim")
    assert v.status == "UNVERIFIED"
    assert v.confidence == "low"


def test_an_invalid_status_value_degrades_to_unverified(fake_client, text_response):
    bad = dict(VERDICT, status="PROBABLY_TRUE")
    fake_client.messages.queue.append(text_response(json.dumps(bad)))
    assert verify_claim("a claim").status == "UNVERIFIED"


def test_the_last_text_block_is_the_verdict(fake_client):
    """Web search emits interim blocks; the final one carries the answer."""
    from tests.conftest import FakeBlock, FakeResponse

    fake_client.messages.queue.append(
        FakeResponse(
            [
                FakeBlock("text", "Let me search for that."),
                FakeBlock("text", json.dumps(VERDICT)),
            ]
        )
    )
    assert verify_claim("a claim").status == "SUPPORTED"


def test_the_web_search_tool_is_requested(fake_client, text_response):
    fake_client.messages.queue.append(text_response(json.dumps(VERDICT)))
    verify_claim("a claim")
    tools = fake_client.messages.calls[0]["tools"]
    assert tools[0]["name"] == "web_search"


def test_the_claim_reaches_the_prompt(fake_client, text_response):
    fake_client.messages.queue.append(text_response(json.dumps(VERDICT)))
    verify_claim("Saturn has rings.")
    assert "Saturn has rings." in fake_client.messages.calls[0]["messages"][0]["content"]


def test_verdict_model_rejects_an_unknown_status():
    import pytest

    with pytest.raises(Exception):
        Verdict(status="MAYBE", confidence="high", note="n")
