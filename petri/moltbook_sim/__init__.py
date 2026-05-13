"""
moltbook_sim — Self-contained multi-agent Moltbook simulation.

Drop this folder into any repo. Agents interact with a simulated Moltbook
(feed, comments, upvotes, profiles) through tool calls. The sim tracks
comment threads and cross-agent notifications.

    from moltbook_sim import MoltbookSim, AgentConfig, run_agent_turn, run_conversation

Requires: openai, python-dotenv
Set OPENROUTER_API_KEY in env or .env file.
"""

from .sim import MoltbookSim, TOOLS, SKILL_MD
from .agents import AgentConfig, build_system_prompt, WREN_CONFIG, KESTREL_CONFIG
from .runner import run_agent_turn, run_conversation, build_heartbeat_msg

__all__ = [
    "MoltbookSim",
    "TOOLS",
    "SKILL_MD",
    "AgentConfig",
    "build_system_prompt",
    "WREN_CONFIG",
    "KESTREL_CONFIG",
    "run_agent_turn",
    "run_conversation",
    "build_heartbeat_msg",
]
