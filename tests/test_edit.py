from truth_editor.edit import ClaimVerdict, build_annotated, rewrite_text
from truth_editor.verify import Verdict


def cv(claim, status, note="a note", confidence="high", sources=None):
    return ClaimVerdict(
        claim, Verdict(status=status, confidence=confidence, note=note, sources=sources or [])
    )


class TestBuildAnnotated:
    def test_keeps_the_original_text_first(self):
        out = build_annotated("Original body.", [cv("c", "SUPPORTED")])
        assert out.startswith("Original body.")

    def test_each_status_gets_its_own_marker(self):
        out = build_annotated(
            "t",
            [
                cv("supported claim", "SUPPORTED"),
                cv("contradicted claim", "CONTRADICTED"),
                cv("unverified claim", "UNVERIFIED"),
            ],
        )
        assert "[✓ SUPPORTED] supported claim" in out
        assert "[✗ CONTRADICTED] contradicted claim" in out
        assert "[? UNVERIFIED] unverified claim" in out

    def test_claims_are_numbered_in_order(self):
        out = build_annotated("t", [cv("first", "SUPPORTED"), cv("second", "SUPPORTED")])
        assert out.index("1. ") < out.index("2. ")

    def test_confidence_is_surfaced(self):
        out = build_annotated("t", [cv("c", "SUPPORTED", confidence="low")])
        assert "confidence: low" in out

    def test_sources_are_listed(self):
        out = build_annotated("t", [cv("c", "SUPPORTED", sources=["https://example.com/x"])])
        assert "https://example.com/x" in out

    def test_at_most_three_sources_are_shown(self):
        srcs = [f"https://example.com/{i}" for i in range(6)]
        out = build_annotated("t", [cv("c", "SUPPORTED", sources=srcs)])
        assert out.count("https://example.com/") == 3

    def test_no_claims_still_produces_a_report_header(self):
        out = build_annotated("Body.", [])
        assert "## Claim audit" in out


class TestRewriteText:
    def test_returns_the_edited_text(self, fake_client, text_response):
        fake_client.messages.queue.append(text_response("Edited body."))
        assert rewrite_text("Original.", [cv("c", "UNVERIFIED")]) == "Edited body."

    def test_falls_back_to_the_original_when_no_text_comes_back(self, fake_client):
        from tests.conftest import FakeResponse

        fake_client.messages.queue.append(FakeResponse([]))
        assert rewrite_text("Original.", [cv("c", "SUPPORTED")]) == "Original."

    def test_the_verdicts_reach_the_prompt(self, fake_client, text_response):
        fake_client.messages.queue.append(text_response("out"))
        rewrite_text("Original.", [cv("Mars is red.", "CONTRADICTED", note="Sources disagree.")])
        content = fake_client.messages.calls[0]["messages"][0]["content"]
        assert "Mars is red." in content
        assert "CONTRADICTED" in content
        assert "Original." in content
