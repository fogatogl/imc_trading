"""
FINAL Manual Trading Strategy — All audit corrections applied.

Methodology corrections from audit:
1. r_est anchored to real-world event-study magnitudes (skeptic calibration)
2. Honest sigma values (75-90% directional confidence, not 99-100%)
3. Apply x*=r/2 directly under realistic priors (no aggressive over-deployment)
4. Multi-world stress test included as standard practice
5. Range-based outcome reporting, not point estimates
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats

np.random.seed(42)
plt.rcParams['figure.facecolor'] = 'white'
plt.rcParams['axes.facecolor'] = 'white'
plt.rcParams['axes.spines.top'] = False
plt.rcParams['axes.spines.right'] = False
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['axes.grid'] = True
plt.rcParams['grid.alpha'] = 0.25

BUDGET = 1_000_000
N_TRIALS = 100_000

# ============================================================
# CORRECTED CALIBRATION (anchored to real-world event studies)
# ============================================================
# Each r_est is justified by an explicit real-world analogue.
# Each sigma is set so directional confidence is 65-90%, NOT 95-100%.
PRODUCTS = [
    # (name, r_est, sigma, direction, anchor)
    ('Lava Cakes',         -0.25, 0.18, 'SHORT', 'Chipotle E.coli (-30%), VW Dieselgate (-20%) day-one'),
    ('Pyroflex Cells',     -0.12, 0.15, 'SHORT', 'Tax doubling on consumer good: -10-15% historically'),
    ('Thermalite Cores',   +0.18, 0.15, 'LONG',  'Strong upside revisions on tech: +10-20% range'),
    ('Sulfur Ltd.',        +0.06, 0.08, 'LONG',  'Index inclusion effect: +3-7% post-2010 average'),
    ('Magma Ink',          +0.12, 0.15, 'LONG',  'Hype product launch: +8-15% typical'),
    ('Volcanic Incense',   -0.15, 0.18, 'SHORT', 'Pump reversal day-of (not full collapse): -10-20%'),
    ('Ashes of Phoenix',   -0.10, 0.13, 'SHORT', 'Cosmetics PR scandal: between Wells Fargo (-8%) and VW (-20%)'),
    ('Obsidian Cutlery',   -0.07, 0.15, 'SHORT', 'Mixed signals (supply vs quality): small net move'),
    ('Scoria Paste',        0.00, 0.15, '—',     'No actionable signal; structurally suspect'),
]
df = pd.DataFrame(PRODUCTS, columns=['product', 'r_est', 'sigma', 'direction', 'anchor'])
N = len(df)

print("=" * 95)
print("CORRECTED CALIBRATION (anchored to real-world event studies)")
print("=" * 95)
for _, row in df.iterrows():
    p_correct = (1 - stats.norm.cdf(0, row['r_est'], row['sigma'])) if row['r_est'] > 0 else \
                (stats.norm.cdf(0, row['r_est'], row['sigma']) if row['r_est'] < 0 else 0.5)
    print(f"  {row['product']:<20s}  r={row['r_est']*100:+5.1f}%  σ={row['sigma']*100:4.1f}%  "
          f"P(correct)={p_correct*100:4.0f}%   {row['anchor']}")


# ============================================================
# OPTIMAL ALLOCATION: x* = r/2 with the corrected r values
# ============================================================
r = df['r_est'].values
sigma = df['sigma'].values
x_optimal = r / 2.0

# If sum |x*| > 1, scale down. (Won't happen here — corrected r values are smaller.)
budget_used = np.sum(np.abs(x_optimal))
if budget_used > 1.0:
    x_optimal = x_optimal * (1.0 / budget_used)
    budget_used = 1.0

# Clean rounding to whole percentages where appropriate (or half-percent)
def clean_round(x, step=0.005):
    """Round to nearest 0.5 percentage point."""
    return np.round(x / step) * step

x_final = clean_round(x_optimal, 0.005)

print(f"\n{'Product':<20s}  {'r/2 raw':>10s}  {'rounded':>10s}  {'volume':>10s}")
for i, p in enumerate(df['product']):
    print(f"  {p:<20s}  {x_optimal[i]*100:>+9.2f}%  {x_final[i]*100:>+9.1f}%  "
          f"${abs(x_final[i])*BUDGET:>10,.0f}")
print(f"  {'TOTAL':<20s}  {budget_used*100:>9.1f}%  {np.sum(np.abs(x_final))*100:>9.1f}%  "
      f"${np.sum(np.abs(x_final))*BUDGET:>10,.0f}")


# ============================================================
# COMPARE FINAL TO ALTERNATIVES
# ============================================================
# Original (flawed) recommended
x_original = np.array([-0.20, -0.15, +0.15, +0.10, +0.12, -0.12, -0.09, -0.07, 0.00])
# Half-recommended (audit's recommendation)
x_half_rec = x_original * 0.5
# Final (skeptic-optimal)
# x_final defined above

# Five calibration worlds for stress testing
worlds = {
    'Aggressive':  np.array([-0.40, -0.30, +0.30, +0.20, +0.25, -0.25, -0.18, -0.15, +0.05]),
    'Skeptic':     np.array([-0.25, -0.12, +0.18, +0.06, +0.12, -0.15, -0.10, -0.07, +0.00]),
    'Consensus':   np.array([-0.20, -0.15, +0.15, +0.10, +0.13, -0.13, -0.09, -0.08, +0.03]),
    'Efficient':   np.array([-0.10, -0.08, +0.10, +0.05, +0.08, -0.07, -0.06, -0.04, +0.02]),
    'Pessimist':   np.array([-0.20, -0.15, +0.15, +0.10, +0.125,-0.125,-0.09, -0.075,+0.025]),
}

strategies = {
    'Original (flawed)':       x_original,
    'Half-Recommended':        x_half_rec,
    'FINAL (skeptic-optimal)': x_final,
}

print("\n" + "=" * 95)
print("EXPECTED PnL UNDER EACH WORLD — Strategy Comparison")
print("=" * 95)
print(f"  {'Strategy':<26s} | " + " | ".join(f"{w:>10s}" for w in worlds) + " || {:>10s}".format("Avg"))
for sname, x in strategies.items():
    cells = []
    for wname, wr in worlds.items():
        e = BUDGET * np.sum(x * wr - x**2)
        cells.append(e)
    avg = np.mean(cells)
    cells_str = " | ".join(f"{c:>+10,.0f}" for c in cells)
    print(f"  {sname:<26s} | {cells_str} || {avg:>+10,.0f}")


# ============================================================
# MONTE CARLO under SKEPTIC priors (the calibration we trust)
# ============================================================
print("\n" + "=" * 95)
print(f"MONTE CARLO ({N_TRIALS:,} trials) under SKEPTIC priors")
print("=" * 95)

# Sample returns
returns = np.random.normal(loc=r, scale=sigma, size=(N_TRIALS, N))
returns = np.clip(returns, -0.95, 1.50)

mc_results = {}
for sname, x in strategies.items():
    pnls = (returns * x).sum(axis=1) * BUDGET - np.sum(x**2) * BUDGET
    mc_results[sname] = pnls
    p5, p25, p50, p75, p95 = np.percentile(pnls, [5, 25, 50, 75, 95])
    print(f"  {sname:<26s}  mean {pnls.mean():>+8,.0f}  "
          f"P5 {p5:>+8,.0f}  P50 {p50:>+8,.0f}  P95 {p95:>+8,.0f}  "
          f"P(loss) {(pnls<0).mean()*100:>4.1f}%")


# ============================================================
# CROSS-WORLD MONTE CARLO for FINAL strategy
# ============================================================
print("\n" + "=" * 95)
print("FINAL STRATEGY: Monte Carlo across all 5 calibration worlds")
print("=" * 95)
np.random.seed(42)
print(f"  {'World':<14s}  {'mean':>10s}  {'P5':>10s}  {'P50':>10s}  {'P95':>10s}  {'P(loss)':>10s}")
final_world_results = {}
for wname, wr in worlds.items():
    # Use skeptic's sigma in all worlds (consistent uncertainty model)
    rets = np.random.normal(loc=wr, scale=sigma, size=(N_TRIALS, N))
    rets = np.clip(rets, -0.95, 1.50)
    pnls = (rets * x_final).sum(axis=1) * BUDGET - np.sum(x_final**2) * BUDGET
    final_world_results[wname] = pnls
    p5, p50, p95 = np.percentile(pnls, [5, 50, 95])
    p_loss = (pnls < 0).mean()
    print(f"  {wname:<14s}  {pnls.mean():>+9,.0f}  {p5:>+9,.0f}  {p50:>+9,.0f}  {p95:>+9,.0f}  "
          f"{p_loss*100:>9.1f}%")


# Save data
np.save('/home/claude/final/x_final.npy', x_final)
np.save('/home/claude/final/x_original.npy', x_original)
np.save('/home/claude/final/x_half_rec.npy', x_half_rec)
np.save('/home/claude/final/mc_skeptic.npy', np.array([mc_results[s] for s in strategies]))
np.save('/home/claude/final/mc_final_worlds.npy',
        np.array([final_world_results[w] for w in worlds]))
df.to_csv('/home/claude/final/final_calibration.csv', index=False)
print("\nDone — final strategy locked in.")
