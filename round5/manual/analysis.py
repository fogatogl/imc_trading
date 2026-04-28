"""
Manual Trading Study — Round 5 Ignith Market
Comprehensive analysis: optimal allocation, Monte Carlo, sensitivity, risk.
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from scipy import stats

np.random.seed(42)
plt.rcParams['figure.facecolor'] = 'white'
plt.rcParams['axes.facecolor'] = 'white'
plt.rcParams['font.family'] = 'DejaVu Sans'

BUDGET = 1_000_000
N_TRIALS = 100_000

# ============================================================
# PRODUCT UNIVERSE — calibrated from Ashflow Alpha analysis
# ============================================================
# r_est : signed point estimate of return (negative = short-thesis)
# sigma : standard deviation around that estimate (uncertainty)
#         calibrated so that wider sigma reflects weaker evidence
PRODUCTS = [
    # name,                  r_est,   sigma,  conviction,        signal_summary
    ('Lava Cakes',          -0.40,   0.15,   'High',           'Sales halt + lawsuits + vendor returns'),
    ('Pyroflex Cells',      -0.30,   0.13,   'High',           'Tax doubles tomorrow, industry warns of slowdown'),
    ('Thermalite Cores',    +0.30,   0.13,   'High',           '2.7x user growth, hard data'),
    ('Sulfur Ltd.',         +0.20,   0.10,   'High',           'Index inclusion → forced fund buying'),
    ('Magma Ink',           +0.25,   0.15,   'Medium-High',    'Sold-out launch, six-hour queues'),
    ('Volcanic Incense',    -0.25,   0.18,   'Medium-High',    'Pump pattern around Nostralico calls'),
    ('Ashes of Phoenix',    -0.18,   0.13,   'Medium',         'Viral PR scandal, defensive corporate response'),
    ('Obsidian Cutlery',    -0.15,   0.15,   'Medium-Low',     'Production halt + safety story (mixed signal)'),
    ('Scoria Paste',        +0.05,   0.15,   'Low',            'Influencer hype only, structurally suspect'),
]
df = pd.DataFrame(PRODUCTS, columns=['product', 'r_est', 'sigma', 'conviction', 'signal'])
N = len(df)
print(df[['product', 'r_est', 'sigma', 'conviction']].to_string(index=False))


# ============================================================
# CORE PnL FUNCTIONS
# ============================================================
def pnl_per_product(allocation, returns, budget=BUDGET):
    """Net PnL per product: x*r*B - x^2*B (fee is quadratic on |x|)."""
    return budget * (allocation * returns - allocation**2)

def total_pnl(allocation, returns, budget=BUDGET):
    return pnl_per_product(allocation, returns, budget).sum()

def budget_used(allocation):
    return np.sum(np.abs(allocation))


# ============================================================
# DERIVE OPTIMAL ALLOCATION
# ============================================================
# Unconstrained optimum: x* = r/2 per product (from dPnL/dx = 0).
# If sum |x*| > 1, scale down. If sum |x*| < 1, leave excess unused.
def optimal_allocation(r_estimates, max_budget=1.0):
    x_star = r_estimates / 2.0
    used = np.sum(np.abs(x_star))
    if used > max_budget:
        x_star = x_star * (max_budget / used)
    return x_star


# ============================================================
# STRATEGIES
# ============================================================
strategies = {}

# 1. Optimal Half-r (theoretical optimum, scaled if over budget)
strategies['Optimal Half-r']      = optimal_allocation(df['r_est'].values)

# 2. Optimal Half-r (no Scoria — drop weakest signal)
r_no_scoria = df['r_est'].values.copy()
r_no_scoria[-1] = 0
strategies['Optimal (no Scoria)'] = optimal_allocation(r_no_scoria)

# 3. Recommended (manual rounded portfolio from prior analysis)
strategies['Recommended']         = np.array([-0.20, -0.15, +0.15, +0.10, +0.12, -0.12, -0.09, -0.07, 0.00])

# 4. Conservative (recommended × 0.75, holds ~25% cash)
strategies['Conservative (75%)']  = strategies['Recommended'] * 0.75

# 5. Top-4 Concentrated (only the highest-conviction names, larger sizes)
strategies['Top-4 Concentrated']  = np.array([-0.27, -0.22, +0.22, +0.15, 0, 0, 0, 0, 0])

# 6. Equal Weight Directional (1/9 each, in proper direction)
strategies['Equal Weight']        = np.sign(df['r_est'].values) * (1.0/9)

# 7. All-In Lava Cakes (illustrative — what concentration costs)
strategies['All-In Lava (50%)']   = np.array([-0.50, 0, 0, 0, 0, 0, 0, 0, 0])

# 8. High-conviction only, optimal-sized (5 names)
hc_mask = df['conviction'].isin(['High', 'Medium-High']).values
r_hc = np.where(hc_mask, df['r_est'].values, 0)
strategies['High-Conv Optimal']   = optimal_allocation(r_hc)

# Sanity check
print("\n--- Strategy Budget Usage ---")
for name, x in strategies.items():
    print(f"  {name:25s}: {budget_used(x)*100:5.1f}% deployed,  positions = {(x != 0).sum()}")


# ============================================================
# EXPECTED PnL (closed-form, no simulation)
# ============================================================
# E[PnL] = budget * sum(x_i * mu_i - x_i^2)
# Var[PnL] = budget^2 * sum(x_i^2 * sigma_i^2)  (assuming independence)
def expected_pnl(allocation, df, budget=BUDGET):
    mu = df['r_est'].values
    return budget * np.sum(allocation * mu - allocation**2)

def std_pnl(allocation, df, budget=BUDGET):
    sig = df['sigma'].values
    return budget * np.sqrt(np.sum((allocation * sig)**2))

print("\n--- Expected PnL & Std (closed-form, returns ~ Normal, independent) ---")
results = []
for name, x in strategies.items():
    e = expected_pnl(x, df)
    s = std_pnl(x, df)
    sharpe = e/s if s > 0 else 0
    results.append({'strategy': name, 'E[PnL]': e, 'Std[PnL]': s, 'Sharpe-like': sharpe,
                    'budget_used': budget_used(x)})
    print(f"  {name:25s}: E[PnL] = {e:>9,.0f},  Std = {s:>9,.0f},  E/Std = {sharpe:5.2f}")
res_df = pd.DataFrame(results)


# ============================================================
# MONTE CARLO SIMULATION
# ============================================================
print(f"\n--- Monte Carlo: {N_TRIALS:,} trials ---")
mu = df['r_est'].values
sigma = df['sigma'].values
# Sample returns: each row is one trial, each col is a product
returns_samples = np.random.normal(loc=mu, scale=sigma, size=(N_TRIALS, N))
# Cap returns at sensible bounds [-0.95, +1.5] to avoid pathological draws
returns_samples = np.clip(returns_samples, -0.95, 1.50)

mc_results = {}
for name, x in strategies.items():
    pnls = (returns_samples * x).sum(axis=1) * BUDGET - np.sum(x**2) * BUDGET
    mc_results[name] = pnls

# Statistics
print(f"\n{'Strategy':<25s} {'Mean':>10s} {'Std':>10s} {'P5':>10s} {'P50':>10s} {'P95':>10s} {'P(loss)':>10s}")
mc_stats = []
for name, pnls in mc_results.items():
    p5, p25, p50, p75, p95 = np.percentile(pnls, [5, 25, 50, 75, 95])
    p_loss = (pnls < 0).mean()
    p_neg10k = (pnls < -10_000).mean()
    p_pos100k = (pnls > 100_000).mean()
    mc_stats.append({
        'strategy': name,
        'mean': pnls.mean(),
        'std': pnls.std(),
        'p5': p5, 'p25': p25, 'p50': p50, 'p75': p75, 'p95': p95,
        'p_loss': p_loss, 'p_lose10k': p_neg10k, 'p_win100k': p_pos100k,
        'min': pnls.min(), 'max': pnls.max(),
    })
    print(f"  {name:<25s} {pnls.mean():>10,.0f} {pnls.std():>10,.0f} {p5:>10,.0f} {p50:>10,.0f} {p95:>10,.0f} {p_loss*100:>9.1f}%")

mc_df = pd.DataFrame(mc_stats)


# ============================================================
# SENSITIVITY: scale all returns by factor k
# ============================================================
print("\n--- Sensitivity to return scale (signal_strength_multiplier) ---")
scales = np.linspace(0.3, 1.5, 13)
sens_data = {name: [] for name in strategies}
for k in scales:
    mu_k = mu * k
    for name, x in strategies.items():
        e = BUDGET * np.sum(x * mu_k - x**2)
        sens_data[name].append(e)
print(f"  Scale  | " + " | ".join(f"{n[:14]:>14s}" for n in strategies))
for i, k in enumerate(scales):
    row = f"  {k:5.2f}  | " + " | ".join(f"{sens_data[n][i]:>14,.0f}" for n in strategies)
    print(row)


# ============================================================
# WRONG-DIRECTION ANALYSIS (per-product impact if a single signal flips)
# ============================================================
# For each product, what happens to the Recommended portfolio's PnL if
# that product's true return is opposite of estimated?
print("\n--- Wrong-Direction Sensitivity (Recommended portfolio) ---")
rec = strategies['Recommended']
base_pnl = expected_pnl(rec, df)
print(f"  Baseline expected PnL: {base_pnl:,.0f}")
flip_results = []
for i, prod in enumerate(df['product']):
    mu_flipped = mu.copy()
    mu_flipped[i] = -mu[i]
    new_pnl = BUDGET * np.sum(rec * mu_flipped - rec**2)
    delta = new_pnl - base_pnl
    flip_results.append({'product': prod, 'allocation': rec[i], 'baseline_E': base_pnl,
                         'flipped_E': new_pnl, 'delta': delta})
    print(f"  Flip {prod:<20s} (alloc {rec[i]*100:+5.1f}%): PnL = {new_pnl:>9,.0f}  (Δ {delta:+,.0f})")
flip_df = pd.DataFrame(flip_results)


# ============================================================
# CORRELATION STRESS TEST
# ============================================================
# What if Ignith economic conditions create correlated returns?
# Add a common factor with weight rho.
print("\n--- Correlation Stress Test (rho = systemic correlation) ---")
def mc_correlated(rho, x, n=20_000):
    common = np.random.normal(0, 1, size=(n, 1))
    idio = np.random.normal(0, 1, size=(n, N))
    z = rho * common + np.sqrt(1 - rho**2) * idio
    rets = mu + sigma * z
    rets = np.clip(rets, -0.95, 1.50)
    pnls = (rets * x).sum(axis=1) * BUDGET - np.sum(x**2) * BUDGET
    return pnls

corr_data = {}
for rho in [0.0, 0.2, 0.4, 0.6]:
    for name in ['Recommended', 'Optimal (no Scoria)', 'Top-4 Concentrated', 'Equal Weight']:
        pnls = mc_correlated(rho, strategies[name])
        corr_data[(rho, name)] = pnls

print(f"  {'Strategy':<25s} | " + " | ".join(f"rho={r:.1f}" for r in [0.0, 0.2, 0.4, 0.6]))
print(f"  {'':25s} | " + " | ".join("Mean    Std    P5    " for _ in [0,1,2,3]))
for name in ['Recommended', 'Optimal (no Scoria)', 'Top-4 Concentrated', 'Equal Weight']:
    parts = []
    for rho in [0.0, 0.2, 0.4, 0.6]:
        p = corr_data[(rho, name)]
        parts.append(f"{p.mean():>5,.0f} {p.std():>5,.0f} {np.percentile(p,5):>6,.0f}")
    print(f"  {name:<25s} | " + " | ".join(parts))


# ============================================================
# SAVE INTERMEDIATES
# ============================================================
res_df.to_csv('/home/claude/study/strategy_summary.csv', index=False)
mc_df.to_csv('/home/claude/study/mc_stats.csv', index=False)
flip_df.to_csv('/home/claude/study/flip_sensitivity.csv', index=False)

# Save MC samples for later plotting
np.save('/home/claude/study/mc_samples.npy', np.array([mc_results[n] for n in strategies]))
with open('/home/claude/study/strategy_names.txt', 'w') as f:
    for n in strategies:
        f.write(n + '\n')
np.save('/home/claude/study/strategies.npy', np.array(list(strategies.values())))

print("\nDone.")
