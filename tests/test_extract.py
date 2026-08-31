import json

import pytest

from truth_editor.extract import extract_claims


def test_parses_claims_from_the_response(fake_client, text_response):
    fake_client.messages.queue.append(
        text_response(json.dumps({"claims": ["The sky is blue.", "Water boils at 100C."]}))
    )
    assert extract_claims("some text") == ["The sky is blue.", "Water boils at 100C."]


def test_empty_claim_list_is_valid(fake_client, text_response):
    fake_client.messages.queue.append(text_response(json.dumps({"claims": []})))
    assert extract_claims("I think cats are nice.") == []


def test_the_source_text_reaches_the_prompt(fake_client, text_response):
    fake_client.messages.queue.append(text_response(json.dumps({"claims": []})))
    extract_claims("Neptune has 14 moons.")
    call = fake_client.messages.calls[0]
    assert "Neptune has 14 moons." in call["messages"][0]["content"]


def test_requests_a_json_schema_so_the_reply_is_parseable(fake_client, text_response):
    fake_client.messages.queue.append(text_response(json.dumps({"claims": []})))
    extract_claims("text")
    fmt = fake_client.messages.calls[0]["output_config"]["format"]
    assert fmt["type"] == "json_schema"
    assert fmt["schema"]["required"] == ["claims"]


def test_a_malformed_reply_raises_rather_than_returning_junk(fake_client, text_response):
    fake_client.messages.queue.append(text_response("not json at all"))
    with pytest.raises(Exception):
        extract_claims("text")


def test_a_reply_missing_the_claims_key_is_rejected(fake_client, text_response):
    fake_client.messages.queue.append(text_response(json.dumps({"other": []})))
    with pytest.raises(Exception):
        extract_claims("text")
