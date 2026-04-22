# truth-editor

A fact-check layer for LLM output. Extracts the factual claims from a block of
text, verifies each one against the live web, and returns a verdict plus sources.

## How it works

```
text → claim extraction → parallel web-search verification → verdict per claim
                                                              → annotated report
                                                              → optional rewrite
```

Three Claude calls per run:

1. **Extract** — split the text into atomic, self-contained factual claims.
2. **Verify** — for each claim, run web search and return
   `SUPPORTED | CONTRADICTED | UNVERIFIED` with confidence, a one-sentence note,
   and source URLs. Uses Anthropic's native `web_search` tool (no second API
   provider needed).
3. **Rewrite** (opt-in) — edit the original text to strip or flag any claims
   that aren't `SUPPORTED`.

## Install

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Set `ANTHROPIC_API_KEY` via a local `.env`, or the module will also read
`~/goldsmith-report/config.env` if present.

## Use

**CLI**

```bash
.venv/bin/python -m truth_editor "The Eiffel Tower was completed in 1889 and is 330 meters tall. It is located in London."
```

Add `--rewrite` to also print a flagged/edited version.

**Web UI**

```bash
.venv/bin/uvicorn truth_editor.web:app --reload
# open http://localhost:8000
```

## Limits

- Only as good as what web search surfaces. Weak/stale sources → `UNVERIFIED`.
- Claim extraction is lossy: paraphrased claims may miss nuance from the source.
- Not a substitute for human review on anything high-stakes.
