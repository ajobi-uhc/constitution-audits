"""
Test run: GPT-5.2 with reasoning_effort=medium on one section (redline).

Verifies reasoning is actually enabled before kicking off full audit.
Uses direct OpenAI API for target (OpenRouter ignores reasoning params for GPT-5.2).
"""

import dotenv
dotenv.load_dotenv()

from inspect_ai import eval as inspect_eval
from inspect_ai.model import GenerateConfig, get_model
from openai_model_spec_audit import openai_model_spec_audit

target_model = get_model(
    "openai/gpt-5.2",
    config=GenerateConfig(
        max_connections=50,
        reasoning_effort="medium",
    ),
)

auditor_model = get_model(
    "openrouter/anthropic/claude-sonnet-4.5",
    config=GenerateConfig(
        max_connections=50,
        max_tokens=32_000,
        reasoning_tokens=10_000,
    ),
)

judge_model = get_model(
    "openrouter/anthropic/claude-opus-4.5",
    config=GenerateConfig(
        max_connections=50,
        max_tokens=32_000,
        reasoning_tokens=10_000,
    ),
)

task_obj = openai_model_spec_audit(
    max_turns=30,
    spec_section="redline",
    transcript_save_dir="./results/openai_spec/gpt52_reasoning_audit/redline",
)

inspect_eval(
    task_obj,
    model_roles={
        "auditor": auditor_model,
        "target": target_model,
        "judge": judge_model,
    },
    log_dir="./results/openai_spec/gpt52_reasoning_audit/redline_logs",
    max_samples=3,  # just 3 samples to verify reasoning works
    fail_on_error=0.2,
)
