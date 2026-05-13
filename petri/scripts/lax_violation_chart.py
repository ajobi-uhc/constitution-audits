"""Generate violation rate comparison chart: strict vs lax thresholds — all 7 models."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

models = ['Sonnet 4', 'GPT 5.2', 'Gemini 3\nPro', 'Sonnet 4.5', 'Opus 4.5', 'Opus 4.6', 'Sonnet 4.6']
strict_rates = [13.5, 14.5, 10.1, 3.9, 3.4, 2.5, 1.0]
lax_rates =    [15.0, 15.0, 12.4, 7.3, 4.4, 2.9, 2.0]
lax_new = [l - s for l, s in zip(lax_rates, strict_rates)]

strict_confirmed = [27, 30, 27, 8, 7, 6, 2]
lax_confirmed =    [30, 31, 33, 15, 9, 7, 4]

x = np.arange(len(models))
width = 0.6

fig, ax = plt.subplots(figsize=(14, 7))

bars_strict = ax.bar(x, strict_rates, width,
                      label='Strict thresholds (core\u22657, multi\u22655, spec\u22657)',
                      color='#4A90D9', edgecolor='white', linewidth=0.5)
bars_lax = ax.bar(x, lax_new, width, bottom=strict_rates,
                   label='Additional at lax (core\u22655, multi\u22653, spec\u22655)',
                   color='#F5A623', edgecolor='white', linewidth=0.5)

# Labels on bars
for i, (s, l) in enumerate(zip(strict_rates, lax_rates)):
    ax.text(i, l + 0.2, f'{l}%', ha='center', va='bottom', fontweight='bold', fontsize=11)
    if s > 1.5:
        ax.text(i, s / 2, f'{s}%', ha='center', va='center', fontsize=9.5, color='white', fontweight='bold')

# Confirmed counts below bars
for i in range(len(models)):
    ax.text(i, -1.0, f'{strict_confirmed[i]}\u2192{lax_confirmed[i]}',
            ha='center', va='top', fontsize=9, color='#555')

ax.set_ylabel('Violation Rate (%)', fontsize=13)
ax.set_title('Soul Doc Violation Rates: Strict vs Lax Thresholds', fontsize=15, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(models, fontsize=10.5)
ax.legend(loc='upper right', fontsize=10)
ax.set_ylim(0, 18)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.axhline(y=0, color='black', linewidth=0.5)

# Divider line between older and newer models
ax.axvline(x=2.5, color='#ccc', linestyle='--', linewidth=1)
ax.text(1.0, 17, 'Previous gen', ha='center', fontsize=9, color='#999')
ax.text(4.75, 17, 'Current gen', ha='center', fontsize=9, color='#999')

# Subtitle
ax.text(3.0, -2.5, 'Numbers below bars: confirmed violations (strict\u2192lax)',
        ha='center', fontsize=9, color='#777', style='italic')

plt.tight_layout()
plt.savefig('validation_reports/lax_violation_rates.png', dpi=150, bbox_inches='tight')
print('Saved to validation_reports/lax_violation_rates.png')
