"""
solver.py — Inspect solver that runs a moltbook audit conversation.

The auditor (Petri) makes plain LLM calls — no tools, sees the full thread
each turn, writes one comment. The target (Wren) runs through the normal
moltbook sim with heartbeat + tools.
"""

import asyncio
import json
import os
import random
import re
from pathlib import Path

import openai
from dotenv import load_dotenv
from inspect_ai.model import get_model, ChatMessageUser, ChatMessageAssistant
from inspect_ai.solver import solver, TaskState

from .agents import AgentConfig, WREN_IDENTITY
from .auditor_prompt import build_auditor_system_prompt
from .runner import run_agent_turn, build_heartbeat_msg
from .sim import MoltbookSim

from petri.stores import AuditStore

load_dotenv()


def _strip_or_prefix(model_name: str) -> str:
    """Strip 'openrouter/' prefix to get the raw OpenRouter model ID."""
    if model_name.startswith("openrouter/"):
        return model_name[len("openrouter/"):]
    return model_name


def _load_feed(feed_path: str | None, n_posts: int, seed: int) -> list[dict]:
    """Load feed posts from a JSON file, or return the bundled default."""
    if feed_path:
        with open(feed_path) as f:
            all_posts = json.load(f)
    else:
        default = Path(__file__).parent / "default_feed.json"
        with open(default) as f:
            all_posts = json.load(f)
    rng = random.Random(seed)
    return rng.sample(all_posts, min(n_posts, len(all_posts)))


def _parse_auditor_response(text: str) -> tuple[str | None, str]:
    """Parse POST_ID and COMMENT from the auditor's response.

    Turn 1 format:
        POST_ID: <id>
        COMMENT: <text>

    Later turns:
        COMMENT: <text>

    Returns (post_id_or_none, comment_text).
    """
    post_id = None
    post_match = re.search(r"POST_ID:\s*(.+)", text)
    if post_match:
        post_id = post_match.group(1).strip().strip("`")

    comment_match = re.search(r"COMMENT:\s*([\s\S]+)", text)
    if comment_match:
        comment = comment_match.group(1).strip()
        # If COMMENT came after POST_ID, the regex may have captured both;
        # but since COMMENT: comes after POST_ID: in the text, the greedy
        # POST_ID regex won't eat into it. Just clean up.
        return post_id, comment

    # Fallback: if the model didn't use the format, treat the whole thing
    # as the comment (best effort).
    return post_id, text.strip()


def _format_as_chat_messages(result: dict) -> list[ChatMessageUser | ChatMessageAssistant]:
    """Convert moltbook comment threads into inspect ChatMessages for transcript display."""
    messages = []
    threads = result.get("comment_threads", {})
    agents = result.get("agents", {})
    auditor_names = {name for name, info in agents.items() if info.get("emoji") == "🧫"}

    for post_id, comments in threads.items():
        for comment in comments:
            author = comment.get("author", "")
            content = f"[{author} on {post_id}] {comment.get('content', '')}"
            if author in auditor_names:
                messages.append(ChatMessageAssistant(content=content))
            else:
                messages.append(ChatMessageUser(content=content))
    return messages


# ---------------------------------------------------------------------------
# Auditor turn (plain LLM call, no tools)
# ---------------------------------------------------------------------------

def _run_auditor_turn(
    client: openai.OpenAI,
    model: str,
    system_prompt: str,
    user_content: str,
) -> str:
    """Make a single LLM call for the auditor. Returns raw text."""
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        temperature=0.9,
        max_tokens=1024,
    )
    return response.choices[0].message.content or ""


# ---------------------------------------------------------------------------
# Core audit conversation loop
# ---------------------------------------------------------------------------

def _target_replied_to_thread(sim: MoltbookSim, post_id: str, target_name: str, prev_count: int) -> bool:
    """Check if the target posted a new comment to the active thread."""
    thread = sim.comment_threads.get(post_id, [])
    new_comments = thread[prev_count:]
    return any(c["author"] == target_name for c in new_comments)


def _run_audit_conversation(
    auditor_config: AgentConfig,
    target_config: AgentConfig,
    feed_posts: list[dict],
    seed: int,
    n_exchanges: int,
) -> dict:
    """Run the decoupled audit conversation.

    An "exchange" = one Petri comment + one Wren reply in the same thread.
    Wren may take multiple turns (getting distracted by heartbeat, other
    posts, etc.) before replying — that's natural. The auditor waits and
    only posts again once Wren has replied, preventing the auditor from
    talking to itself.
    """
    client = openai.OpenAI(
        api_key=os.environ.get("OPENROUTER_API_KEY", ""),
        base_url="https://openrouter.ai/api/v1",
    )

    rng = random.Random(seed)
    agent_names = [target_config.name, auditor_config.name]
    sim = MoltbookSim(feed_posts, rng, agent_names)

    system_prompt = auditor_config.system_prompt_override or ""
    active_post_id: str | None = None

    # Max target turns per exchange before giving up on that exchange entirely.
    # Wren often needs 3-5 turns (heartbeat, feed browse, other posts) before
    # getting to the notification. 6 gives plenty of room.
    max_target_turns_per_exchange = 6

    # Hard cap on total target turns across the whole conversation to prevent
    # runaway costs if Wren systematically ignores the thread.
    max_total_target_turns = n_exchanges * max_target_turns_per_exchange

    print(f"\nAudit conversation: {auditor_config.name} (auditor) vs {target_config.name} (target)")
    print(f"  exchanges: {n_exchanges}, seed: {seed}, feed posts: {len(feed_posts)}")
    print()

    exchanges = []
    real_exchanges = 0
    total_target_turns = 0

    while real_exchanges < n_exchanges:
        if total_target_turns >= max_total_target_turns:
            print(f"  Hit total target turn cap ({max_total_target_turns}), stopping at {real_exchanges} exchanges")
            break

        print(f"--- Exchange {real_exchanges + 1}/{n_exchanges} ---")
        exchange: dict = {"exchange": real_exchanges + 1}

        # --- Auditor turn (plain LLM call) ---
        if active_post_id is None:
            user_content = sim.get_feed_summary()
        else:
            user_content = sim.get_thread_state(active_post_id)

        raw = _run_auditor_turn(client, auditor_config.model, system_prompt, user_content)
        post_id, comment = _parse_auditor_response(raw)

        if active_post_id is None:
            if post_id:
                active_post_id = post_id
            else:
                active_post_id = feed_posts[0]["id"] if feed_posts else "unknown"
                print(f"  [{auditor_config.name}] WARNING: no POST_ID, defaulting to {active_post_id}")

        # Snapshot thread length after injecting auditor's comment
        sim.inject_comment(auditor_config.name, active_post_id, comment)
        thread_count_after_auditor = len(sim.comment_threads.get(active_post_id, []))

        preview = comment[:80].replace("\n", " ")
        print(f"  [{auditor_config.name}] Comment: {preview}")

        exchange[auditor_config.name] = {
            "agent": auditor_config.name,
            "comment": comment,
            "post_id": active_post_id,
            "raw_response": raw,
        }

        # --- Target turns: keep giving Wren turns until she replies to the thread ---
        target_turns = []
        replied = False

        for attempt in range(max_target_turns_per_exchange):
            if total_target_turns >= max_total_target_turns:
                break

            notifications = sim.drain_notifications(target_config.name)
            heartbeat = build_heartbeat_msg(target_config, notifications, rng)
            turn = run_agent_turn(target_config, sim, heartbeat, client=client)
            target_turns.append(turn)
            total_target_turns += 1

            if _target_replied_to_thread(sim, active_post_id, target_config.name, thread_count_after_auditor):
                replied = True
                break
            else:
                print(f"  [{target_config.name}] Didn't reply to thread (attempt {attempt + 1}/{max_target_turns_per_exchange})")

        exchange[target_config.name] = target_turns if len(target_turns) > 1 else target_turns[0]
        exchange["target_replied"] = replied

        if replied:
            real_exchanges += 1
            exchanges.append(exchange)
            print()
        else:
            # Don't count this as an exchange — the auditor won't post again
            # until Wren has actually replied. Just discard and retry the
            # whole exchange on the next iteration (auditor re-posts seeing
            # no new reply). But to avoid infinite loops, we DO append the
            # exchange for logging and fall through to the total-turns cap.
            exchanges.append(exchange)
            print(f"  [{target_config.name}] Didn't reply after {len(target_turns)} turns, retrying exchange")
            print()

    return {
        "seed": seed,
        "n_exchanges": n_exchanges,
        "agents": {
            auditor_config.name: {"model": auditor_config.model, "emoji": auditor_config.emoji},
            target_config.name: {"model": target_config.model, "emoji": target_config.emoji},
        },
        "exchanges": exchanges,
        "comment_threads": sim.comment_threads,
    }


# ---------------------------------------------------------------------------
# Inspect solver
# ---------------------------------------------------------------------------

@solver
def moltbook_auditor(
    n_exchanges: int = 25,
    feed_path: str | None = None,
    n_posts: int = 5,
    seed: int = 42,
):
    """Solver that runs a moltbook conversation between auditor (Petri) and target (Wren)."""

    async def solve(state: TaskState, generate):
        seed_instructions = state.input_text

        # Get model names from inspect roles
        auditor_model_name = get_model(role="auditor").name
        target_model_name = get_model(role="target").name

        # Build agent configs
        auditor = AgentConfig(
            name="Petri",
            model=_strip_or_prefix(auditor_model_name),
            emoji="🧫",
            system_prompt_override=build_auditor_system_prompt(
                seed_instructions,
                target_name="Wren",
                target_model=_strip_or_prefix(target_model_name),
            ),
        )
        target = AgentConfig(
            name="Wren",
            model=_strip_or_prefix(target_model_name),
            emoji="🐦",
            identity_md=WREN_IDENTITY,
        )

        # Load feed
        feed_posts = _load_feed(feed_path, n_posts, seed)

        # Run the decoupled audit conversation (sync → async)
        result = await asyncio.to_thread(
            _run_audit_conversation,
            auditor,
            target,
            feed_posts,
            seed=seed,
            n_exchanges=n_exchanges,
        )

        # Store result for scorer/cleanup
        audit_store = state.store_as(AuditStore)
        audit_store.seed_instructions = seed_instructions

        # Format comment threads as messages for transcript
        state.messages = _format_as_chat_messages(result)
        state.metadata["moltbook_result"] = result

        return state

    return solve
