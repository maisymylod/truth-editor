#!/usr/bin/env python3
"""Deploy a Claude Managed Agent to audit and improve truth-editor.

Creates (or reuses) an environment + agent, starts a session with the repo
mounted, streams events, and leaves a pushed branch for the orchestrator
to open as a PR.
"""

import json
import subprocess
import sys
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env", override=False)

STATE_FILE = REPO_ROOT / "agents" / ".state.json"
GITHUB_REPO_URL = "https://github.com/maisymylod/truth-editor"
MOUNT_PATH = "/workspace/truth-editor"

SYSTEM_PROMPT = """You are a senior software engineer auditing the truth-editor project — a fact-check layer for LLM output that extracts atomic factual claims from text, verifies each against the live web via Anthropic's native web_search tool, and returns SUPPORTED / CONTRADICTED / UNVERIFIED verdicts with sources. The project has a CLI and a minimal FastAPI web UI.

Your mandate: identify the highest-leverage improvements to this codebase and implement them. Focus on changes that meaningfully improve correctness, robustness, UX, or developer experience. Avoid cosmetic changes, premature abstractions, and scope creep.

Workflow:
1. Read the code at {mount} to understand the architecture. Start with README.md, then the truth_editor/ package (client, extract, verify, edit, cli, web).
2. Identify 2-4 concrete, meaningful improvements. Briefly state your plan before implementing each one.
3. Implement them. Test where reasonable (you can install deps and run the CLI — the ANTHROPIC_API_KEY is NOT available in your sandbox, so don't try live API calls; use unit tests or static checks).
4. Configure git identity (name "Maisy Mylod", email "maisymylod@gmail.com"), create a new branch named "agent/<short-description>", commit your changes, and push the branch.
5. Summarize what you did and why.

Style constraints the project follows:
- Minimal code, no unnecessary comments, no backwards-compat shims
- Don't add dependencies without clear justification
- Match existing patterns (pydantic models, threadpool for parallelism, etc.)
- Commits authored by Maisy, NO Claude attribution in commit messages or code

You have full bash + file editing + web access. Use it.""".format(mount=MOUNT_PATH)

KICKOFF = f"""Audit {MOUNT_PATH} and implement the 2-4 highest-leverage improvements. Test where you can. Push a branch named agent/<short-description>, then tell me the branch name and a summary of what changed."""


def gh_token() -> str:
    return subprocess.check_output(["gh", "auth", "token"], text=True).strip()


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def ensure_env_and_agent(client: Anthropic) -> tuple[str, str]:
    state = load_state()

    if "environment_id" not in state:
        print("[setup] creating environment...", flush=True)
        env = client.beta.environments.create(
            name=f"truth-editor-improver-{Path.home().name}",
            config={"type": "cloud", "networking": {"type": "unrestricted"}},
        )
        state["environment_id"] = env.id

    if "agent_id" not in state:
        print("[setup] creating agent...", flush=True)
        agent = client.beta.agents.create(
            name="truth-editor improver",
            model="claude-opus-4-7",
            system=SYSTEM_PROMPT,
            tools=[
                {"type": "agent_toolset_20260401", "default_config": {"enabled": True}},
            ],
        )
        state["agent_id"] = agent.id

    save_state(state)
    return state["agent_id"], state["environment_id"]


def describe_block(block) -> str:
    t = getattr(block, "type", "?")
    if t == "text":
        return getattr(block, "text", "")
    return f"[{t}]"


def main() -> int:
    client = Anthropic()
    agent_id, env_id = ensure_env_and_agent(client)

    print(f"[setup] agent={agent_id} env={env_id}", flush=True)
    print("[setup] mounting repo + starting session...", flush=True)

    session = client.beta.sessions.create(
        agent=agent_id,
        environment_id=env_id,
        title="Audit and improve truth-editor",
        resources=[
            {
                "type": "github_repository",
                "url": GITHUB_REPO_URL,
                "authorization_token": gh_token(),
                "mount_path": MOUNT_PATH,
                "checkout": {"type": "branch", "name": "main"},
            }
        ],
    )
    print(f"[session] {session.id}", flush=True)

    # Stream-first: open stream, then send the kickoff message
    stream_ctx = client.beta.sessions.events.stream(session_id=session.id)
    with stream_ctx as stream:
        client.beta.sessions.events.send(
            session_id=session.id,
            events=[
                {
                    "type": "user.message",
                    "content": [{"type": "text", "text": KICKOFF}],
                }
            ],
        )

        total_in = total_out = 0
        for event in stream:
            t = getattr(event, "type", "?")

            if t == "agent.message":
                for block in getattr(event, "content", []):
                    text = describe_block(block)
                    if text:
                        print(text, end="", flush=True)
                print()

            elif t == "agent.tool_use":
                name = getattr(event, "tool_name", None) or getattr(event, "name", "?")
                inp = getattr(event, "input", "")
                inp_str = json.dumps(inp)[:160] if not isinstance(inp, str) else inp[:160]
                print(f"\n  [tool] {name} {inp_str}", flush=True)

            elif t == "agent.tool_result":
                pass  # results are often huge; rely on the agent's own narration

            elif t == "span.model_request_end":
                usage = getattr(event, "model_usage", None)
                if usage:
                    total_in += getattr(usage, "input_tokens", 0) or 0
                    total_out += getattr(usage, "output_tokens", 0) or 0

            elif t == "session.status_terminated":
                print("\n[session terminated]", flush=True)
                break

            elif t == "session.status_idle":
                stop = getattr(event, "stop_reason", None)
                stop_type = getattr(stop, "type", None) if stop else None
                if stop_type and stop_type != "requires_action":
                    print(f"\n[session idle — {stop_type}]", flush=True)
                    break

            elif t == "session.error":
                print(f"\n[session error] {event}", flush=True)

    print(f"\n[usage] input={total_in} output={total_out} tokens", flush=True)

    # Check for a newly pushed branch
    subprocess.run(["git", "-C", str(REPO_ROOT), "fetch", "origin"], check=False)
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "branch", "-r"],
        capture_output=True,
        text=True,
    )
    branches = [
        line.strip().removeprefix("origin/")
        for line in result.stdout.splitlines()
        if "agent/" in line
    ]
    if branches:
        latest = branches[0]
        print(f"\n[branch pushed] {latest}", flush=True)
        print(f"[pr] gh pr create --base main --head {latest} --fill", flush=True)
    else:
        print("\n[branch] no agent/* branch found — check session log", flush=True)

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n[interrupted]", flush=True)
        sys.exit(130)
