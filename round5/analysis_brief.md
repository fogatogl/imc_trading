# Trading Data Analysis Brief

Two in-game hints from an NPC. Both point at the same playbook for a 50-asset dataset: **cluster first, then look for lead-lag between clusters.**

## Hint 1 — "It's a Lot" (handling 50 goods)

- 50 individual time series at once = noise, not signal. Don't analyze product-by-product.
- **Group the products into clusters that share structural characteristics.**
- Look at the cluster level for:
  - Clusters that consistently outperform.
  - Clusters that reliably underperform, round after round, regardless of conditions.
- Patterns at the cluster level are more readable and more actionable than at the individual-product level.
- Use clusters as the lens; individual products only make sense afterward.

## Hint 2 — "Same but Slower" (timing / lead-lag)

- Beyond structural similarity, look for **sequence**: which group moves first, which group follows.
- The lag between related goods is the signal, not a flaw.
- Check for a **recurring, stable timing gap** between related categories.
- If one cluster consistently leads and another consistently follows with a stable lag, the follower's moves are anticipatable from the leader's prior moves.
- Distinction to encode:
  - Structural similarity → tells you what is *related*.
  - Sequence / lag → tells you what is *coming*.

## Pipeline steps to implement

1. **Load & normalize** the 50-product price/return series. Align timestamps, handle missing data.
2. **Cluster** the products by structural characteristics. Reasonable approaches:
   - Correlation-distance hierarchical clustering on returns.
   - K-means / DBSCAN on standardized return features (volatility, drawdown, autocorr, etc.).
   - Validate cluster count with silhouette / gap statistic.
3. **Cluster-level performance**: build per-cluster aggregate series (mean or PCA first component). Rank clusters on consistent over/underperformance across rolling windows.
4. **Lead-lag detection between clusters**:
   - Pairwise cross-correlation of cluster aggregates across lags (e.g. ±1 to ±20 periods).
   - Identify pairs (A, B) where corr(A_t, B_{t+k}) is high and the optimal lag k is **stable across rolling windows**.
   - Optional: Granger causality on cluster aggregates as confirmation.
5. **Stability test**: split the timeline into chunks; require the lead-lag pair and its lag k to persist across chunks. Discard pairs whose lag wanders.
6. **Output**: for each stable leader→follower pair, report the lag k, correlation strength, and stability score. These are the anticipatable setups.

## What to flag in results

- Persistent leader clusters and their followers, with the lag in periods.
- Clusters with consistent absolute over/underperformance (independent of lead-lag).
- Any lead-lag pair whose lag is stable enough that the follower's next move can be predicted from the leader's current move.
