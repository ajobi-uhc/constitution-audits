"""Generate flagged transcript score heatmaps and validation funnel charts."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import json

# ============================================================
# Data
# ============================================================

MODELS_ORDER = ['Sonnet 4', 'GPT 5.2', 'Gemini 3 Pro', 'Sonnet 4.5', 'Opus 4.5', 'Opus 4.6', 'Sonnet 4.6']
MODELS_SHORT = ['Son4', 'GPT5.2', 'Gem3P', 'Son4.5', 'Op4.5', 'Op4.6', 'Son4.6']

CORE_DIMS = ["concerning", "disappointing", "needs_attention"]
SPEC_DIMS = ["cooperation_with_human_misuse", "cooperation_with_harmful_sysprompt",
             "facilitating_terrorism", "unprompted_deception_toward_user",
             "concerning_with_no_mitigating_factors"]
ALL_DIMS = CORE_DIMS + SPEC_DIMS
DIM_LABELS = ["concerning", "disappointing", "needs_attn",
              "coop_misuse", "coop_harmful_sp", "facil_terror",
              "unpr_deception", "concern_no_mitig"]

# Map model names to phase0 files
PHASE0_MAP = {
    'Sonnet 4': 'scripts/lax_phase0_sonnet4_output.json',
    'GPT 5.2': 'scripts/lax_phase0_gpt52_output.json',
    'Gemini 3 Pro': 'scripts/lax_phase0_gemini3pro_output.json',
    'Sonnet 4.5': 'scripts/lax_phase0_sonnet45_output.json',
    'Opus 4.5': 'scripts/lax_phase0_opus45_output.json',
    'Opus 4.6': 'scripts/lax_phase0_opus46_output.json',
    'Sonnet 4.6': 'scripts/lax_phase0_sonnet46_output.json',
}

VAL_MAP = {
    'Sonnet 4': 'scripts/lax_validation_sonnet4_results.json',
    'GPT 5.2': 'scripts/lax_validation_gpt52_results.json',
    'Gemini 3 Pro': 'scripts/lax_validation_gemini3pro_results.json',
    'Sonnet 4.5': 'scripts/lax_validation_sonnet45_results.json',
    'Opus 4.5': 'scripts/lax_validation_opus45_results.json',
    'Opus 4.6': 'scripts/lax_validation_opus46_results.json',
    'Sonnet 4.6': 'scripts/lax_validation_sonnet46_results.json',
}

# Full model data (strict + lax combined from summary)
SUMMARY = json.load(open('validation_reports/lax_validation_summary.json'))


# ============================================================
# Chart 1: Aggregate score dimensions for flagged transcripts
# ============================================================

def load_flagged_scores(model_name):
    """Load average scores across all lax-only flagged transcripts."""
    with open(PHASE0_MAP[model_name]) as f:
        phase0 = json.load(f)
    items = phase0['newly_flagged']
    if not items:
        return {d: 0 for d in ALL_DIMS}

    totals = {d: 0 for d in ALL_DIMS}
    for item in items:
        for d in CORE_DIMS:
            totals[d] += item['core_scores'].get(d, 0)
        for d in SPEC_DIMS:
            totals[d] += item.get('specialized_scores', {}).get(d, 0)
    return {d: totals[d] / len(items) for d in ALL_DIMS}


fig, ax = plt.subplots(figsize=(14, 7))

# Build heatmap data: models x dimensions
data = np.zeros((len(MODELS_ORDER), len(ALL_DIMS)))
for i, model in enumerate(MODELS_ORDER):
    avg_scores = load_flagged_scores(model)
    for j, dim in enumerate(ALL_DIMS):
        data[i, j] = avg_scores[dim]

im = ax.imshow(data, cmap='YlOrRd', aspect='auto', vmin=0, vmax=5)

ax.set_xticks(range(len(DIM_LABELS)))
ax.set_xticklabels(DIM_LABELS, rotation=45, ha='right', fontsize=10)
ax.set_yticks(range(len(MODELS_ORDER)))
ax.set_yticklabels(MODELS_ORDER, fontsize=11)

# Annotate cells
for i in range(len(MODELS_ORDER)):
    for j in range(len(ALL_DIMS)):
        val = data[i, j]
        if val >= 0.5:
            color = 'white' if val > 3 else 'black'
            ax.text(j, i, f'{val:.1f}', ha='center', va='center', fontsize=9, color=color, fontweight='bold')

cbar = plt.colorbar(im, ax=ax, shrink=0.8)
cbar.set_label('Average Score (1-10)', fontsize=10)

ax.set_title('Average Score Dimensions for Lax-Only Flagged Transcripts', fontsize=14, fontweight='bold')
ax.axhline(y=2.5, color='white', linewidth=2)  # Divider between prev/current gen

plt.tight_layout()
plt.savefig('validation_reports/lax_flagged_score_heatmap.png', dpi=150, bbox_inches='tight')
print('Saved heatmap')
plt.close()


# ============================================================
# Chart 2: Validation Funnel per model
# ============================================================

fig, axes = plt.subplots(2, 4, figsize=(18, 10))
axes = axes.flatten()

colors_funnel = {
    'total': '#B0BEC5',
    'lax_flagged': '#FFB74D',
    'confirmed': '#E53935',
    'false_positive': '#66BB6A',
}

for idx, model in enumerate(MODELS_ORDER):
    ax = axes[idx]
    key = model.lower().replace(' ', '_').replace('.', '.')

    # Find the right key in summary
    summary_key = None
    for k, v in SUMMARY['models'].items():
        if v.get('model_id', '').endswith(model.lower().replace(' ', '-').replace('.', '-')) or \
           model.lower().replace(' ', '_') in k.lower().replace('.', '') or \
           model in v.get('model_id', ''):
            summary_key = k
            break

    if summary_key is None:
        # Manual mapping
        mapping = {
            'Sonnet 4': 'sonnet_4', 'GPT 5.2': 'gpt_5.2', 'Gemini 3 Pro': 'gemini_3_pro',
            'Sonnet 4.5': 'sonnet_4.5', 'Opus 4.5': 'opus_4.5',
            'Opus 4.6': 'opus_4.6', 'Sonnet 4.6': 'sonnet_4.6',
        }
        summary_key = mapping[model]

    md = SUMMARY['models'][summary_key]
    total = md['total_transcripts']
    strict_flagged = md['strict']['flagged']
    strict_confirmed = md['strict']['confirmed']
    lax_flagged = md['lax']['flagged']
    lax_confirmed = md['lax']['confirmed']
    lax_fp = md['lax']['false_positive']

    # Funnel stages
    stages = ['Total\nTranscripts', 'Lax\nFlagged', 'Confirmed\nViolations']
    values = [total, lax_flagged, lax_confirmed]
    bar_colors = ['#78909C', '#FFB74D', '#E53935']

    bars = ax.barh(range(len(stages)-1, -1, -1), values, color=bar_colors, height=0.6, edgecolor='white')

    for i, (stage, val) in enumerate(zip(stages, values)):
        y = len(stages) - 1 - i
        pct = f'({100*val/total:.0f}%)' if i > 0 else ''
        ax.text(val + total * 0.02, y, f'{val} {pct}', va='center', fontsize=10, fontweight='bold')

    ax.set_yticks(range(len(stages)-1, -1, -1))
    ax.set_yticklabels(stages, fontsize=9)
    ax.set_xlim(0, total * 1.35)
    ax.set_title(model, fontsize=12, fontweight='bold')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.set_xticks([])

    # Add false positive count as annotation
    fp_text = f'{lax_fp} false positives filtered'
    ax.text(total * 0.5, -0.5, fp_text, ha='center', fontsize=8, color='#66BB6A', style='italic')

# Hide last empty subplot
axes[7].set_visible(False)

fig.suptitle('Validation Funnel: Lax Thresholds (core\u22655, multi\u22653, spec\u22655)',
             fontsize=15, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig('validation_reports/lax_validation_funnels.png', dpi=150, bbox_inches='tight')
print('Saved funnels')
plt.close()


# ============================================================
# Chart 3: Stacked bar — flagged breakdown by outcome
# ============================================================

fig, ax = plt.subplots(figsize=(14, 7))

x = np.arange(len(MODELS_ORDER))
width = 0.6

strict_confirmed_vals = []
lax_new_confirmed_vals = []
lax_new_fp_vals = []
strict_fp_vals = []

for model in MODELS_ORDER:
    mapping = {
        'Sonnet 4': 'sonnet_4', 'GPT 5.2': 'gpt_5.2', 'Gemini 3 Pro': 'gemini_3_pro',
        'Sonnet 4.5': 'sonnet_4.5', 'Opus 4.5': 'opus_4.5',
        'Opus 4.6': 'opus_4.6', 'Sonnet 4.6': 'sonnet_4.6',
    }
    md = SUMMARY['models'][mapping[model]]
    sc = md['strict']['confirmed']
    sf = md['strict']['false_positive']
    lc = md['lax']['confirmed'] - sc  # new from lax
    lf = md['lax']['false_positive'] - sf  # new FP from lax

    strict_confirmed_vals.append(sc)
    strict_fp_vals.append(sf)
    lax_new_confirmed_vals.append(lc)
    lax_new_fp_vals.append(lf)

b1 = ax.bar(x, strict_confirmed_vals, width, label='Strict: Confirmed', color='#C62828')
b2 = ax.bar(x, lax_new_confirmed_vals, width, bottom=strict_confirmed_vals,
            label='Lax-only: Confirmed', color='#EF5350')
bottom2 = [a+b for a, b in zip(strict_confirmed_vals, lax_new_confirmed_vals)]
b3 = ax.bar(x, strict_fp_vals, width, bottom=bottom2,
            label='Strict: False Positive', color='#2E7D32')
bottom3 = [a+b for a, b in zip(bottom2, strict_fp_vals)]
b4 = ax.bar(x, lax_new_fp_vals, width, bottom=bottom3,
            label='Lax-only: False Positive', color='#81C784')

# Total labels
for i in range(len(MODELS_ORDER)):
    total_flagged = strict_confirmed_vals[i] + lax_new_confirmed_vals[i] + strict_fp_vals[i] + lax_new_fp_vals[i]
    total_confirmed = strict_confirmed_vals[i] + lax_new_confirmed_vals[i]
    ax.text(i, total_flagged + 0.5, f'{total_confirmed}/{total_flagged}',
            ha='center', va='bottom', fontsize=10, fontweight='bold')

ax.set_ylabel('Flagged Transcripts', fontsize=12)
ax.set_title('Flagged Transcript Outcomes: Confirmed vs False Positive', fontsize=14, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(MODELS_ORDER, fontsize=10)
ax.legend(loc='upper right', fontsize=9)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.axvline(x=2.5, color='#ccc', linestyle='--', linewidth=1)

plt.tight_layout()
plt.savefig('validation_reports/lax_flagged_outcomes.png', dpi=150, bbox_inches='tight')
print('Saved outcomes')
plt.close()

print('\nAll charts saved to validation_reports/')
