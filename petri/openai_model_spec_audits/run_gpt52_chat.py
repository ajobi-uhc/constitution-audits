"""
GPT-5.2-chat-latest OpenAI Model Spec Audit.

Same eval framework as gpt52_reasoning run but with gpt-5.2-chat-latest target.
No reasoning_effort parameter — standard chat model.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import dotenv
dotenv.load_dotenv(override=True)

import look_at_logs; look_at_logs.start()

from inspect_ai import eval as inspect_eval
from inspect_ai.model import GenerateConfig, get_model
from openai_model_spec_audit import openai_model_spec_audit

SECTIONS = [
    "redline",
    "chain_of_command",
    "content",
    "safety",
    "truth",
    "best_work",
    "style",
    "under18",
]

section = sys.argv[1] if len(sys.argv) > 1 else "all"
if section != "all" and section not in SECTIONS:
    print(f"Unknown section: {section}. Options: {SECTIONS} or 'all'")
    sys.exit(1)

sections_to_run = SECTIONS if section == "all" else [section]

target_model = get_model(
    "openai/gpt-5.2-chat-latest",
    responses_api=False,
    config=GenerateConfig(max_connections=50),
)

auditor_model = get_model(
    "openrouter/anthropic/claude-sonnet-4.5",
    config=GenerateConfig(max_connections=50),
)

judge_model = get_model(
    "openrouter/anthropic/claude-opus-4.5",
    config=GenerateConfig(max_connections=50),
)

output_base = "./results/openai_spec/gpt52_chat_audit"

for s in sections_to_run:
    print(f"\n{'='*60}")
    print(f"Running section: {s}")
    print(f"{'='*60}\n")

    task_obj = openai_model_spec_audit(
        max_turns=30,
        spec_section=s,
        transcript_save_dir=f"{output_base}/{s}",
    )

    inspect_eval(
        task_obj,
        model_roles={
            "auditor": auditor_model,
            "target": target_model,
            "judge": judge_model,
        },
        log_dir=f"{output_base}/{s}_logs",
        fail_on_error=0.2,
    )
