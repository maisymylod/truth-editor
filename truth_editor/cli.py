import argparse
import sys
from concurrent.futures import ThreadPoolExecutor

from .client import MAX_INPUT_CHARS
from .edit import ClaimVerdict, build_annotated, rewrite_text
from .extract import extract_claims
from .verify import verify_claim


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fact-check LLM output against the web. "
        "Reads text from an argument or stdin."
    )
    parser.add_argument("text", nargs="?", help="Text to check (default: stdin)")
    parser.add_argument(
        "--rewrite",
        action="store_true",
        help="Also emit a rewritten version with unverified claims flagged",
    )
    parser.add_argument(
        "--parallel",
        type=int,
        default=5,
        help="Parallel verification workers (default: 5)",
    )
    args = parser.parse_args()

    text = args.text if args.text is not None else sys.stdin.read()
    if not text.strip():
        print("No input text provided.", file=sys.stderr)
        return 1
    if len(text) > MAX_INPUT_CHARS:
        print(
            f"Input too long: {len(text)} chars (limit {MAX_INPUT_CHARS}). "
            f"Set TRUTH_EDITOR_MAX_INPUT_CHARS to override.",
            file=sys.stderr,
        )
        return 1

    print("[1/3] Extracting claims...", file=sys.stderr)
    claims = extract_claims(text)

    if not claims:
        print("No verifiable factual claims found.", file=sys.stderr)
        print(text)
        return 0

    print(f"[2/3] Verifying {len(claims)} claim(s) via web search...", file=sys.stderr)
    with ThreadPoolExecutor(max_workers=args.parallel) as pool:
        verdicts = list(pool.map(verify_claim, claims))

    results = [ClaimVerdict(c, v) for c, v in zip(claims, verdicts)]

    print("[3/3] Building report...", file=sys.stderr)
    print(build_annotated(text, results))

    if args.rewrite:
        print("\n---\n\n## Cleaned version\n")
        print(rewrite_text(text, results))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
