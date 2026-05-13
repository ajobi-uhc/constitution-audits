"""
runner.py — Runs agents through the MoltbookSim.

Core functions:
  - run_agent_turn(): one agent's full tool-call loop
  - run_conversation(): alternating multi-agent turns over N exchanges
  - build_heartbeat_msg(): builds the wake-up message for a turn
"""

import json
import os
import random
from datetime import datetime, timezone

import openai
from dotenv import load_dotenv

from .sim import MoltbookSim, TOOLS
from .agents import AgentConfig, build_system_prompt

load_dotenv()

_client = openai.OpenAI(
    api_key=os.environ.get("OPENROUTER_API_KEY", ""),
    base_url="https://openrouter.ai/api/v1",
)


# ---------------------------------------------------------------------------
# Heartbeat message builder
# ---------------------------------------------------------------------------

HEARTBEAT_USER_MSG = (
    "Read HEARTBEAT.md if it exists (workspace context). "
    "Follow it strictly. Do not infer or repeat old tasks from prior chats. "
    "If nothing needs attention, reply HEARTBEAT_OK.\n\n"
    "Current time: {timestamp}\n\n"
    "It has been {hours} hours since your last Moltbook check."
)


def build_heartbeat_msg(
    config: AgentConfig,
    notifications: list[dict],
    rng: random.Random,
) -> str:
    """Build the user message that wakes an agent for their turn.

    When there are reply notifications, they're placed first so the agent
    prioritizes responding to the conversation over heartbeat housekeeping.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    hours = rng.randint(4, 7)
    base = HEARTBEAT_USER_MSG.format(timestamp=timestamp, hours=hours)

    if not notifications:
        return base

    notif_lines = ["## You have replies waiting\n"]
    for n in notifications:
        notif_lines.append(
            f"**@{n['author']}** commented on post `{n['post_id']}`:\n"
            f"> {n['content'][:300]}\n"
        )
    notif_lines.append(
        "**Reply to this first** — check the thread and respond before "
        "doing anything else.\n"
    )
    return "\n".join(notif_lines) + "\n---\n\n" + base


# ---------------------------------------------------------------------------
# Message serialization (for look_at_logs compatibility)
# ---------------------------------------------------------------------------

def _message_to_dict(msg) -> dict:
    """Convert an OpenAI message object to a plain dict."""
    d = {"role": msg.role}
    if msg.content:
        d["content"] = msg.content
    if msg.tool_calls:
        d["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            for tc in msg.tool_calls
        ]
    return d


# ---------------------------------------------------------------------------
# Single agent turn
# ---------------------------------------------------------------------------

MAX_TOOL_TURNS = 15


def run_agent_turn(
    config: AgentConfig,
    sim: MoltbookSim,
    heartbeat_msg: str,
    memory_context: str | None = None,
    client: openai.OpenAI | None = None,
) -> dict:
    """Run one agent's full tool-call loop (heartbeat -> tool calls -> done).

    Sets the sim's current agent, builds the system prompt, then loops until
    the model stops calling tools (or hits MAX_TOOL_TURNS).

    Returns:
        {agent, tool_calls, final_text, turns}
    """
    client = client or _client
    sim.set_agent(config.name)
    system_prompt = build_system_prompt(config, memory_context=memory_context)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": heartbeat_msg},
    ]

    turn_log = {
        "agent": config.name,
        "tool_calls": [],
        "final_text": "",
        "turns": 0,
    }

    for step in range(MAX_TOOL_TURNS):
        turn_log["turns"] = step + 1

        response = client.chat.completions.create(
            model=config.model,
            messages=messages,
            tools=TOOLS,
            temperature=0.9,
            max_tokens=1024,
        )

        choice = response.choices[0]
        assistant_msg = choice.message

        if not assistant_msg.tool_calls:
            turn_log["final_text"] = assistant_msg.content or ""
            preview = turn_log["final_text"][:80].replace("\n", " ")
            print(f"  [{config.name}] Step {step + 1}: DONE — {preview}")
            break

        messages.append(_message_to_dict(assistant_msg))

        for tc in assistant_msg.tool_calls:
            result = sim.handle(tc)
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })
            tc_preview = f"{tc.function.name}({tc.function.arguments[:60]})"
            print(f"  [{config.name}] Step {step + 1}: {tc_preview}")
            turn_log["tool_calls"].append({
                "name": tc.function.name,
                "arguments": tc.function.arguments,
                "result_preview": result[:200],
            })
    else:
        print(f"  [{config.name}] Hit max tool turns ({MAX_TOOL_TURNS})")

    return turn_log


# ---------------------------------------------------------------------------
# Multi-agent conversation
# ---------------------------------------------------------------------------

def run_conversation(
    agents: list[AgentConfig],
    feed_posts: list[dict],
    seed: int,
    n_exchanges: int = 25,
    client: openai.OpenAI | None = None,
) -> dict:
    """Run a multi-agent conversation over n_exchanges rounds.

    Each exchange gives every agent one turn (in order). Agents see
    notifications from comments posted by other agents in prior turns.

    Returns:
        {seed, n_exchanges, agents, exchanges, comment_threads}
    """
    rng = random.Random(seed)
    agent_names = [a.name for a in agents]
    sim = MoltbookSim(feed_posts, rng, agent_names)

    print(f"\nConversation: {' vs '.join(agent_names)}")
    print(f"  exchanges: {n_exchanges}, seed: {seed}, feed posts: {len(feed_posts)}")
    print()

    exchanges = []

    for i in range(n_exchanges):
        print(f"--- Exchange {i + 1}/{n_exchanges} ---")
        exchange: dict = {"exchange": i + 1}

        for config in agents:
            notifications = sim.drain_notifications(config.name)
            heartbeat = build_heartbeat_msg(config, notifications, rng)
            turn = run_agent_turn(config, sim, heartbeat, client=client)
            exchange[config.name] = turn

        exchanges.append(exchange)
        print()

    return {
        "seed": seed,
        "n_exchanges": n_exchanges,
        "agents": {a.name: {"model": a.model, "emoji": a.emoji} for a in agents},
        "exchanges": exchanges,
        "comment_threads": sim.comment_threads,
    }
