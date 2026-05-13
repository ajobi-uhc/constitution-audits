# Petri

Eval framework for testing constitutional alignment in frontier language models. Red-teams models against their own published constitutions and produces human-reviewed violation reports.

## What's Here

### [Validation Reports](../validation_reports/)

Human-reviewed reports documenting confirmed violations for each model. Start here.

- **6 models** tested against the [Anthropic Constitution](constitutions/anthropic_soul_doc.md) (211 tenets)
- **5 models** tested against the [OpenAI Model Spec](constitutions/openai_model_spec.md) (197 tenets)
- Violation rates range from 1.0% (Sonnet 4.6) to 12.8% (Sonnet 4)

### [Tenet References](tenets/)

Browsable catalog of every tenet tested, with deep links from violation reports.

- [anthropic_constitution.md](tenets/anthropic_constitution.md) — 211 tenets across 20 sections
- [openai_model_spec.md](tenets/openai_model_spec.md) — 197 tenets across 8 sections

### Eval Definitions

- [claude_soul_doc_audits/soul_doc_audit.py](claude_soul_doc_audits/soul_doc_audit.py) — Anthropic Constitution eval
- [openai_model_spec_audits/openai_model_spec_audit.py](openai_model_spec_audits/openai_model_spec_audit.py) — OpenAI Model Spec eval

### [Results](../results/)

Raw multi-branch conversation transcripts (JSON) between adversarial auditor and target model, plus eval logs.

- `results/soul_doc/<model>/` — Anthropic Constitution eval transcripts
- `results/openai_spec/<model>/` — OpenAI Model Spec eval transcripts

## How It Works

1. An adversarial **auditor** (Claude Opus/Sonnet) red-teams a **target** model through multi-turn conversations, branching into different attack strategies
2. A **judge** (Claude Opus) scores each transcript on 38 behavioral dimensions
3. Transcripts exceeding score thresholds are flagged for human-equivalent review
4. **Triage agents** (Haiku) classify each flag as CONFIRMED, FALSE_POSITIVE, or BORDERLINE
5. **Resolution agents** resolve borderlines to binary verdicts
6. A **compiler** (Opus) produces the final validation report

See [methodology](evals/validation_methodology.md) and [OpenAI methodology](evals/openai_validation_methodology.md) for details.

## Running Evals

Requires [inspect_ai](https://inspect.ai-safety-institute.org.uk/) and the `petri` package.

```bash
pip install -e .

# Anthropic Constitution eval
inspect eval claude_soul_doc_audits/soul_doc_audit.py \
    --model-role auditor=openrouter/anthropic/claude-opus-4 \
    --model-role target=openrouter/anthropic/claude-sonnet-4.5 \
    --model-role judge=openrouter/anthropic/claude-opus-4 \
    -T max_turns=30 \
    -T transcript_save_dir=./results/soul_doc

# OpenAI Model Spec eval
inspect eval openai_model_spec_audits/openai_model_spec_audit.py \
    --model-role auditor=openrouter/anthropic/claude-sonnet-4.5 \
    --model-role target=openai/gpt-4o \
    --model-role judge=openrouter/anthropic/claude-opus-4 \
    -T max_turns=30 \
    -T transcript_save_dir=./results/openai_spec
```
