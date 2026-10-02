# Constitution Audits

Combined working repo for the paper [*How Well Do Models Follow Their Constitutions?*](https://arxiv.org/abs/2605.24229v1) — merging the Petri multi-turn audit pipeline and the SURF rubric-search pipeline against Anthropic's constitution and OpenAI's Model Spec.

This top level consolidates the audit outputs (validation tables, tenets, methodology, figures) and points to the two underlying tool repos for code and raw transcripts.

## Quick start: where things live

| Want | Go to |
| --- | --- |
| Per-model confirmed violations with severity, tenet IDs, transcript links | [`violation_tables.md`](violation_tables.md) |
| Full Petri validation reports per model | [`validation_reports/anthropic_constitution/`](validation_reports/anthropic_constitution/), [`validation_reports/openai_model_spec/`](validation_reports/openai_model_spec/) |
| Aggregate Petri summaries | [`validation_reports/anthropic_constitution_summary.md`](validation_reports/anthropic_constitution_summary.md), [`validation_reports/openai_model_spec_summary.md`](validation_reports/openai_model_spec_summary.md) |
| SURF validation reports (per Claude variant) | [`validation_reports/surf/`](validation_reports/surf/) |
| SURF appendix tables and transcript walkthroughs | [`validation_reports/surf_appendix_tables.md`](validation_reports/surf_appendix_tables.md), [`validation_reports/surf_transcript_walkthroughs.md`](validation_reports/surf_transcript_walkthroughs.md) |
| System-card comparison | [`validation_reports/model_card_comparison.md`](validation_reports/model_card_comparison.md) |
| Decomposed tenets (anchorable by ID) | [`tenets/anthropic_constitution.md`](tenets/anthropic_constitution.md), [`tenets/openai_model_spec.md`](tenets/openai_model_spec.md) |
| Source specifications | [`constitutions/anthropic_soul_doc.md`](constitutions/anthropic_soul_doc.md), [`constitutions/openai_model_spec.md`](constitutions/openai_model_spec.md) |
| Methodology docs (Petri + SURF validators) | [`methodology/`](methodology/) |
| Plots used in the paper | [`figures/`](figures/) |
| Raw Petri / SURF transcripts | [`results/`](results/) (symlinks; see below) |
| Petri eval code, scripts, evals | [`petri/`](petri) (bundled working copy) |
| SURF tool code, rubrics, validators | [`surf/`](surf) (bundled working copy) |

## Repo layout

```
constitution-audits/
├── README.md                                    # this file
├── violation_tables.md                          # cross-model confirmed Petri violations, severity, tenet+transcript links
├── tenets/
│   ├── anthropic_constitution.md                # 205 evaluated tenets + 6 additional power tests
│   └── openai_model_spec.md                     # 197 tenets, 8 sections
├── constitutions/                               # source documents the tenets were decomposed from
│   ├── anthropic_soul_doc.md
│   └── openai_model_spec.md
├── validation_reports/                          # human-reviewed per-model reports + aggregates
│   ├── anthropic_constitution/                  # Petri per-model reports for the Anthropic constitution
│   │   ├── sonnet46.md  opus46.md  opus45.md
│   │   ├── sonnet45.md  sonnet4.md
│   │   ├── gemini3pro.md  gpt52.md
│   ├── openai_model_spec/                       # Petri per-model reports for the OpenAI Model Spec
│   │   ├── gpt4o.md  gpt5.md  gpt51.md
│   │   ├── gpt52.md  gpt52_chat.md  gpt52_reasoning.md  gpt52_reasoning_low.md
│   │   ├── sonnet46.md  gemini3pro.md
│   ├── surf/                                    # SURF per-model reports + raw-data JSON per Claude variant
│   │   ├── SURF_validation_report_*.md
│   │   ├── data_*.json
│   ├── anthropic_constitution_summary.md
│   ├── openai_model_spec_summary.md
│   ├── surf_appendix_tables.md
│   ├── surf_transcript_walkthroughs.md
│   ├── model_card_comparison.md                 # side-by-side: this audit vs lab-published system cards
│   ├── methodology.md                           # Petri Anthropic validation funnel (shim filename)
│   ├── openai_methodology.md                    # Petri OpenAI validation funnel (shim filename)
│   ├── surf_methodology.md
│   └── validation_summary.json
├── methodology/                                 # canonical methodology docs (same content as the shims above)
│   ├── petri_anthropic_validation_methodology.md
│   ├── petri_openai_validation_methodology.md
│   └── surf_validation_methodology.md
├── figures/                                     # all PNGs used in the paper body
├── results/                                     # transcripts linked from validation reports
│   ├── soul_doc/<model>/transcript_*.json       # Petri Anthropic transcripts cited in reports
│   ├── openai_spec/<audit_dir>/<section>/...    # Petri OpenAI transcripts cited in reports
│   └── surf/                                    # SURF curated honesty-section flagged runs
│       ├── honesty/<run_dir>/                   # raw EM-loop output (violations.txt, summaries)
│       ├── surf_p1_violations_transcripts.txt   # concatenated P1 SURF flags
│       └── validation_output/                   # round-1/round-2 verdict JSONs
├── petri/                                       # Petri eval framework source (no .venv / no raw results)
└── surf/                                        # SURF rubric-search tool source (no .venv / no raw results)
```

`results/` ships **only the ~230 transcripts that any markdown report links to** (≈170 MB) — the confirmed Petri violations plus the false-positive transcripts cited in per-model validation reports, plus the SURF honesty-section run dump. The full ~4.7 GB raw transcript trees from every Petri run and every SURF section sweep are too large for GitHub; they live in the underlying source repos. See the **Reproducing the audits** section for re-running the pipelines and regenerating raw results.

## Accessing transcripts

Paths in `violation_tables.md` and the per-model reports resolve directly into `results/`. Examples:

- [`results/soul_doc/sonnet46/transcript_T5.6a.json`](results/soul_doc/sonnet46/transcript_T5.6a.json) — AI-identity-denial transcript cited in §5
- [`results/soul_doc/opus46/transcript_2026-02-05_18-41-07_DjpYCwYY47ZHSWmxGKnpzb.json`](results/soul_doc/opus46/transcript_2026-02-05_18-41-07_DjpYCwYY47ZHSWmxGKnpzb.json) — the Opus 4.6 2,400-client infrastructure lockdown
- [`results/openai_spec/sonnet46_audit/redline/`](results/openai_spec/sonnet46_audit/redline/) — Petri OpenAI Model Spec transcripts by section
- [`results/surf/surf_p1_violations_transcripts.txt`](results/surf/surf_p1_violations_transcripts.txt) — concatenated SURF P1 flagged interactions

## Reproducing the audits

### Petri (multi-turn adversarial)

Use Python 3.11 or 3.12 and install the locked environment from the repository
root:

```bash
uv sync --locked

# Anthropic constitution
uv run inspect eval petri/claude_soul_doc_audits/soul_doc_audit.py \
    --model-role auditor=openrouter/anthropic/claude-opus-4 \
    --model-role target=openrouter/anthropic/claude-sonnet-4.5 \
    --model-role judge=openrouter/anthropic/claude-opus-4 \
    -T max_turns=30 -T transcript_save_dir=./results/soul_doc

# OpenAI Model Spec
uv run inspect eval petri/openai_model_spec_audits/openai_model_spec_audit.py \
    --model-role auditor=openrouter/anthropic/claude-sonnet-4.5 \
    --model-role target=openai/gpt-4o \
    --model-role judge=openrouter/anthropic/claude-opus-4 \
    -T max_turns=30 -T transcript_save_dir=./results/openai_spec
```

Validation methodology: [`methodology/petri_anthropic_validation_methodology.md`](methodology/petri_anthropic_validation_methodology.md), [`methodology/petri_openai_validation_methodology.md`](methodology/petri_openai_validation_methodology.md).

### SURF (rubric-search single-turn)

```bash
cd surf
uv sync
# set ANTHROPIC_API_KEY, OPENROUTER_API_KEY, HF_TOKEN in .env

# Run a section sweep (e.g. honesty) against a Claude variant
uv run -m surf.cli.main sweep \
    --rubric rubrics/honesty.yaml \
    --output-dir results/honesty \
    --target-model anthropic:claude-sonnet-4-5-20250929
```

Five SURF section rubrics live at `surf/rubrics/`: `honesty.yaml`, `harm_avoidance.yaml`, `hard_constraints.yaml`, `epistemic_autonomy.yaml`, `wellbeing.yaml`.

Validation methodology: [`methodology/surf_validation_methodology.md`](methodology/surf_validation_methodology.md).

## Headline numbers

Anthropic constitution (Petri, per-model violation rate, worst severity):

| Model | N | Viol. rate | Worst sev. |
|---|---:|---:|---:|
| Sonnet 4.6 | 205 | 2.0% | 6 |
| Opus 4.6 | 238 | 2.9% | 9 |
| Opus 4.5 | 204 | 4.4% | 9 |
| Sonnet 4.5 | 205 | 7.3% | 9 |
| Sonnet 4 | 200 | 15.0% | 10 |
| Gemini 3 Pro | 267 | 12.4% | 10 |
| GPT-5.2 | 207 | 15.0% | 10 |

OpenAI Model Spec (Petri):

| Model / config | N | Viol. rate | Worst sev. |
|---|---:|---:|---:|
| GPT-5.2 (reason-med) | 197 | 3.6% | 7 |
| GPT-5.1 (reason-med) | 206 | 3.9% | 7 |
| GPT-5 (reason-med) | 197 | 5.1% | 10 |
| GPT-5.2 (chat) | 197 | 5.6% | 10 |
| GPT-5.2 (reason-low) | 197 | 7.1% | 7 |
| GPT-4o | 197 | 11.7% | 9 |
| Sonnet 4.6 | 197 | 5.6% | 8 |
| Gemini 3 Pro | 196 | 6.1% | 9 |

SURF confirmed violations (latest Claude variants, Anthropic constitution P1/P2 tenets):

| Model | Confirmed | Dominant failure mode |
|---|---:|---|
| Sonnet 4.5 | 101 | Overcautious refusal (34%) + political framing (38%) |
| Sonnet 4.6 | 106 | Fabricated data, esp. math (72%) |
| Opus 4.5 | 93 | Fabricated citations and data (77%) |
| Opus 4.6 | 88 | Fabricated claims with false formalism (75%) |

Full breakdowns: [`validation_reports/anthropic_constitution_summary.md`](validation_reports/anthropic_constitution_summary.md), [`validation_reports/openai_model_spec_summary.md`](validation_reports/openai_model_spec_summary.md), [`validation_reports/surf_appendix_tables.md`](validation_reports/surf_appendix_tables.md).

## Upstream tools

This repo bundles working copies of the two audit tools. Upstream sources:

- Petri (multi-turn agentic auditor + judge): https://github.com/safety-research/petri — bundled in [`petri/`](petri).
- SURF (rubric-search EM loop): https://github.com/seoirsem/SURF — bundled in [`surf/`](surf).
