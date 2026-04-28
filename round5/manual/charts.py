"""
Generate the visualization suite for the manual trading study.
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import matplotlib.cm as cm
from scipy import stats

plt.rcParams['figure.facecolor'] = 'white'
plt.rcParams['axes.facecolor'] = 'white'
plt.rcParams['axes.spines.top'] = False
plt.rcParams['axes.spines.right'] = False
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['axes.grid'] = True
plt.rcParams['grid.alpha'] = 0.25

# Reload data
mc_samples = np.load('/home/claude/study/mc_samples.npy')
strategies_arr = np.load('/home/claude/study/strategies.npy')
with open('/home/claude/study/strategy_names.txt') as f:
    strategy_names = [l.strip() for l in f]

products = ['Lava Cakes', 'Pyroflex Cells', 'Thermalite Cores', 'Sulfur Ltd.',
            'Magma Ink', 'Volcanic Incense', 'Ashes of Phoenix',
            'Obsidian Cutlery', 'Scoria Paste']
r_est = np.array([-0.40, -0.30, +0.30, +0.20, +0.25, -0.25, -0.18, -0.15, +0.05])
sigma = np.array([0.15, 0.13, 0.13, 0.10, 0.15, 0.18, 0.13, 0.15, 0.15])
BUDGET = 1_000_000

# Color palette per conviction
conv_colors = {
    'High':         '#1B5E20',
    'Medium-High':  '#558B2F',
    'Medium':       '#F9A825',
    'Medium-Low':   '#EF6C00',
    'Low':          '#C62828',
}
conviction = ['High', 'High', 'High', 'High', 'Medium-High', 'Medium-High',
              'Medium', 'Medium-Low', 'Low']
prod_colors = [conv_colors[c] for c in conviction]


# ============================================================
# CHART 1: PnL distribution comparison (violin)
# ============================================================
fig, ax = plt.subplots(figsize=(11, 6))
positions = list(range(len(strategy_names)))
parts = ax.violinplot([mc_samples[i] for i in range(len(strategy_names))],
                      positions=positions, showmeans=False, showmedians=True,
                      widths=0.78)
strat_colors = ['#1565C0', '#1976D2', '#1E88E5', '#43A047', '#FB8C00',
                '#FFB300', '#E53935', '#8E24AA']
for i, pc in enumerate(parts['bodies']):
    pc.set_facecolor(strat_colors[i])
    pc.set_edgecolor('black')
    pc.set_alpha(0.65)
parts['cmedians'].set_color('black')
parts['cbars'].set_color('gray')

# Overlay mean as white diamond
means = [s.mean() for s in mc_samples]
ax.scatter(positions, means, marker='D', s=70, color='white',
           edgecolors='black', linewidths=1.2, zorder=5, label='Mean')

ax.axhline(0, color='red', linestyle='--', linewidth=1, alpha=0.5)
ax.set_xticks(positions)
ax.set_xticklabels(strategy_names, rotation=18, ha='right', fontsize=9)
ax.set_ylabel('Net PnL  ($)', fontsize=11)
ax.set_title('PnL Distribution by Strategy   (100,000 Monte Carlo trials)',
             fontsize=13, fontweight='bold', loc='left')
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x/1000:.0f}k'))
ax.legend(loc='lower left', frameon=False)
plt.tight_layout()
plt.savefig('/home/claude/study/fig1_pnl_distribution.png', dpi=140, bbox_inches='tight')
plt.close()
print("Saved fig1_pnl_distribution.png")


# ============================================================
# CHART 2: Risk vs Return scatter (efficient-frontier style)
# ============================================================
fig, ax = plt.subplots(figsize=(10, 6.5))
for i, name in enumerate(strategy_names):
    samples = mc_samples[i]
    e, s = samples.mean(), samples.std()
    p5 = np.percentile(samples, 5)
    color = strat_colors[i]
    ax.scatter(s, e, s=320, color=color, edgecolors='black', linewidths=1.3,
               alpha=0.85, zorder=5)
    # Label
    offset_x = 2500 if name not in ['Recommended', 'Optimal Half-r', 'Optimal (no Scoria)'] else 2500
    offset_y = 0
    ha = 'left'
    if name == 'Recommended': offset_y = -7000
    if name == 'Optimal Half-r': offset_y = +7000
    if name == 'Optimal (no Scoria)': offset_y = -1000; offset_x = -2500; ha = 'right'
    ax.annotate(name, (s, e), xytext=(s + offset_x, e + offset_y),
                fontsize=9, ha=ha, va='center')

# Annotation: dominated region
ax.set_xlabel('Std of PnL  (risk)', fontsize=11)
ax.set_ylabel('Expected PnL  (return)', fontsize=11)
ax.set_title('Risk-Return Map   (top-left = better)', fontsize=13,
             fontweight='bold', loc='left')
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x/1000:.0f}k'))
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x/1000:.0f}k'))
ax.axhline(0, color='red', linestyle='--', linewidth=0.8, alpha=0.5)
plt.tight_layout()
plt.savefig('/home/claude/study/fig2_risk_return.png', dpi=140, bbox_inches='tight')
plt.close()
print("Saved fig2_risk_return.png")


# ============================================================
# CHART 3: Sensitivity to return scale
# ============================================================
fig, ax = plt.subplots(figsize=(10, 6))
scales = np.linspace(0.3, 1.5, 13)
focus_strategies = ['Optimal (no Scoria)', 'Recommended', 'Conservative (75%)',
                    'Top-4 Concentrated', 'Equal Weight', 'All-In Lava (50%)']
strat_idx = {n: i for i, n in enumerate(strategy_names)}
for i, name in enumerate(focus_strategies):
    x = strategies_arr[strat_idx[name]]
    pnls = [BUDGET * np.sum(x * (r_est * k) - x**2) for k in scales]
    ax.plot(scales, pnls, marker='o', linewidth=2.2, markersize=7, label=name)

ax.axhline(0, color='red', linestyle='--', linewidth=0.8, alpha=0.6)
ax.axvline(1.0, color='gray', linestyle=':', linewidth=0.8, alpha=0.6)
ax.text(1.01, ax.get_ylim()[1]*0.92, 'baseline', fontsize=9, color='gray')
ax.set_xlabel('Return-magnitude multiplier   (1.0 = baseline estimate)', fontsize=11)
ax.set_ylabel('Expected PnL  ($)', fontsize=11)
ax.set_title('Sensitivity to Signal Strength',
             fontsize=13, fontweight='bold', loc='left')
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x/1000:.0f}k'))
ax.legend(loc='upper left', frameon=False, fontsize=9)
plt.tight_layout()
plt.savefig('/home/claude/study/fig3_sensitivity.png', dpi=140, bbox_inches='tight')
plt.close()
print("Saved fig3_sensitivity.png")


# ============================================================
# CHART 4: Wrong-direction impact (bar chart, Recommended portfolio)
# ============================================================
rec = strategies_arr[strat_idx['Recommended']]
base_e = BUDGET * np.sum(rec * r_est - rec**2)
flip_deltas = []
for i in range(9):
    mu_flip = r_est.copy()
    mu_flip[i] = -r_est[i]
    new_e = BUDGET * np.sum(rec * mu_flip - rec**2)
    flip_deltas.append(new_e - base_e)
flip_deltas = np.array(flip_deltas)

fig, ax = plt.subplots(figsize=(11, 6))
bars = ax.barh(products, flip_deltas, color='#C62828', alpha=0.85,
               edgecolor='black', linewidth=0.6)
ax.axvline(0, color='black', linewidth=0.8)
xmin = min(flip_deltas) * 1.15
for bar, d, alloc in zip(bars, flip_deltas, rec):
    label = f'  Δ {d:+,.0f}   (alloc {alloc*100:+.1f}%)'
    # If the bar is very long, put the label INSIDE the bar (at the right edge of the bar)
    if d < -100_000:
        ax.text(d + 5000, bar.get_y() + bar.get_height()/2, label.strip(),
                va='center', ha='left', fontsize=9, color='white', fontweight='bold')
    else:
        ax.text(d, bar.get_y() + bar.get_height()/2, label,
                va='center', ha='left', fontsize=9, color='black')
ax.set_xlabel('Change in expected PnL if this signal is wrong   ($)', fontsize=11)
ax.set_title('Single-Signal Failure Impact   (Recommended portfolio)',
             fontsize=13, fontweight='bold', loc='left')
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x/1000:.0f}k'))
ax.invert_yaxis()
ax.set_xlim(left=xmin, right=15_000)
plt.tight_layout()
plt.savefig('/home/claude/study/fig4_wrong_direction.png', dpi=140, bbox_inches='tight')
plt.close()
print("Saved fig4_wrong_direction.png")


# ============================================================
# CHART 5: Allocation heatmap (strategies × products)
# ============================================================
fig, ax = plt.subplots(figsize=(11, 5.5))
display_strats = ['Optimal (no Scoria)', 'Recommended', 'Conservative (75%)',
                  'High-Conv Optimal', 'Top-4 Concentrated', 'Equal Weight',
                  'All-In Lava (50%)']
mat = np.array([strategies_arr[strat_idx[s]] for s in display_strats]) * 100  # percent

im = ax.imshow(mat, cmap='RdBu_r', vmin=-30, vmax=30, aspect='auto')
ax.set_xticks(range(len(products)))
ax.set_xticklabels(products, rotation=22, ha='right', fontsize=9)
ax.set_yticks(range(len(display_strats)))
ax.set_yticklabels(display_strats, fontsize=10)

# Annotate cells
for i in range(len(display_strats)):
    for j in range(len(products)):
        v = mat[i, j]
        if abs(v) >= 0.5:
            ax.text(j, i, f'{v:+.0f}%', ha='center', va='center',
                    fontsize=9, color='white' if abs(v) > 15 else 'black',
                    fontweight='bold' if abs(v) > 15 else 'normal')

cbar = plt.colorbar(im, ax=ax, fraction=0.04, pad=0.02)
cbar.set_label('Allocation (%)   negative = short, positive = long', fontsize=10)
ax.set_title('Allocation Map   (rows = strategies, columns = products)',
             fontsize=13, fontweight='bold', loc='left')
plt.tight_layout()
plt.savefig('/home/claude/study/fig5_allocation_heatmap.png', dpi=140, bbox_inches='tight')
plt.close()
print("Saved fig5_allocation_heatmap.png")


# ============================================================
# CHART 6: Per-product expected PnL contribution (Recommended)
# ============================================================
contrib_e = BUDGET * (rec * r_est - rec**2)
gross = BUDGET * rec * r_est
fees  = BUDGET * rec**2

fig, ax = plt.subplots(figsize=(10, 6))
y = np.arange(len(products))
bar1 = ax.barh(y - 0.20, gross, height=0.38, color='#43A047', alpha=0.9,
               edgecolor='black', linewidth=0.6, label='Gross expected return')
bar2 = ax.barh(y + 0.20, -fees, height=0.38, color='#E53935', alpha=0.9,
               edgecolor='black', linewidth=0.6, label='Fee  (negative)')
# Net markers
for i, c in enumerate(contrib_e):
    ax.scatter(c, i, color='black', s=55, zorder=5,
               label='Net contribution' if i == 0 else None)

ax.axvline(0, color='black', linewidth=0.8)
ax.set_yticks(y)
ax.set_yticklabels(products, fontsize=10)
ax.invert_yaxis()
ax.set_xlabel('Expected PnL  ($)', fontsize=11)
ax.set_title('Per-Product Contribution Decomposition   (Recommended portfolio)',
             fontsize=13, fontweight='bold', loc='left')
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x/1000:.0f}k'))
ax.legend(loc='lower right', frameon=False)
plt.tight_layout()
plt.savefig('/home/claude/study/fig6_contribution.png', dpi=140, bbox_inches='tight')
plt.close()
print("Saved fig6_contribution.png")


# ============================================================
# CHART 7: Return distribution priors (per product, with allocations marked)
# ============================================================
fig, axes = plt.subplots(3, 3, figsize=(12, 8.5), sharex=True)
xs = np.linspace(-1.0, 1.0, 400)
for i, ax in enumerate(axes.flat):
    pdf = (1/(sigma[i]*np.sqrt(2*np.pi))) * np.exp(-0.5*((xs - r_est[i])/sigma[i])**2)
    ax.fill_between(xs, pdf, color=prod_colors[i], alpha=0.45)
    ax.plot(xs, pdf, color=prod_colors[i], linewidth=1.5)
    ax.axvline(r_est[i], color=prod_colors[i], linestyle='-', linewidth=1.2)
    ax.axvline(0, color='gray', linestyle='--', linewidth=0.8, alpha=0.6)
    ax.axvline(rec[i], color='black', linestyle=':', linewidth=1.4)
    ax.set_title(f'{products[i]}  ({conviction[i]})', fontsize=10, loc='left')
    p_correct = stats.norm.cdf(0, r_est[i], sigma[i]) if r_est[i] < 0 else 1 - stats.norm.cdf(0, r_est[i], sigma[i])
    ax.text(0.02, 0.92, f'r={r_est[i]:+.0%}, σ={sigma[i]:.0%}\nP(correct)={p_correct:.0%}\nalloc={rec[i]*100:+.0f}%',
            transform=ax.transAxes, fontsize=8, va='top',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.85, edgecolor='gray'))
    ax.set_yticks([])
    ax.set_xlim(-0.95, 0.85)
fig.suptitle('Return Priors  (fill = belief distribution; dotted = chosen allocation)',
             fontsize=13, fontweight='bold', y=1.00, x=0.05, ha='left')
plt.tight_layout()
plt.savefig('/home/claude/study/fig7_priors.png', dpi=140, bbox_inches='tight')
plt.close()
print("Saved fig7_priors.png")


# ============================================================
# CHART 8: Cumulative PnL distribution (CDF) for top strategies
# ============================================================
fig, ax = plt.subplots(figsize=(10, 6))
focus = ['Recommended', 'Conservative (75%)', 'Top-4 Concentrated',
         'Equal Weight', 'All-In Lava (50%)']
focus_colors = ['#1565C0', '#43A047', '#E53935', '#FB8C00', '#8E24AA']
for name, color in zip(focus, focus_colors):
    samples = mc_samples[strat_idx[name]]
    sorted_p = np.sort(samples)
    cdf = np.arange(1, len(sorted_p)+1) / len(sorted_p)
    ax.plot(sorted_p, cdf, label=name, linewidth=2.2, color=color)

ax.axvline(0, color='red', linestyle='--', linewidth=1, alpha=0.6)
ax.axhline(0.05, color='gray', linestyle=':', linewidth=0.8)
ax.text(ax.get_xlim()[0]+5000, 0.06, 'P5 (worst-5%)', fontsize=9, color='gray')
ax.set_xlabel('Net PnL  ($)', fontsize=11)
ax.set_ylabel('Cumulative probability', fontsize=11)
ax.set_title('PnL Cumulative Distributions',
             fontsize=13, fontweight='bold', loc='left')
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x/1000:.0f}k'))
ax.legend(loc='lower right', frameon=False)
plt.tight_layout()
plt.savefig('/home/claude/study/fig8_cdf.png', dpi=140, bbox_inches='tight')
plt.close()
print("Saved fig8_cdf.png")

print("\nAll charts saved.")
