# Cross-family findings

_Auto-generated. Logic gates listed at top; stages emitting 'skipped: <reason>' did not pass them._

## Gates in effect
```
  silhouette_min = 0.05
  cluster_k_min = 2
  cluster_k_max = 12
  min_cluster_size = 4
  leadlag_corr_min = 0.05
  leadlag_max_lag = 30
  stability_min = 0.6
  stability_n_windows = 5
  granger_p_max = 0.1
  granger_max_lag = 5
  bootstrap_n = 30
  bootstrap_frac = 0.7
  bootstrap_ari_min = 0.5
```

## Primary cluster assignment: families

Round-5's 10 named families × 5 products are used as the primary cluster assignment for lead-lag analysis (10 well-balanced clusters, 5 each).

## Validation: data-driven clustering on standardised features
- k= 2  silhouette=+0.5922  min_cluster=4  <-- chosen
- k= 3  silhouette=+0.2886  min_cluster=4
- k= 4  silhouette=+0.2903  min_cluster=1
- k= 5  silhouette=+0.2992  min_cluster=1
- k= 6  silhouette=+0.3126  min_cluster=1
- k= 7  silhouette=+0.2772  min_cluster=1
- k= 8  silhouette=+0.3165  min_cluster=1
- k= 9  silhouette=+0.3117  min_cluster=1
- k=10  silhouette=+0.3064  min_cluster=1
- k=11  silhouette=+0.2875  min_cluster=1

k-means chose k=2, silhouette=+0.5922

k-means cluster membership (does the data agree with families?):
- **C0** (46 products, families GALAXY_SOUNDS, MICROCHIP, OXYGEN_SHAKE, PANEL, PEBBLES, ROBOT, SLEEP_POD, SNACKPACK, TRANSLATOR, UV_VISOR)
  - dominant family: GALAXY_SOUNDS (5/46, purity=0.11)
- **C1** (4 products, families OXYGEN_SHAKE, ROBOT)
  - dominant family: ROBOT (2/4, purity=0.50)

## Bootstrap stability (timestamp resampling vs family assignment)
- mean ARI = **0.138** (std 0.029, frac >= 0.6: 0.00, n=30)
- _gate fired: mean ARI 0.14 < gate 0.5; family structure is not robust to timestamp resampling — treat lead-lag results with caution_

## Cluster rolling-performance ranking
Mean rank across the rolling window (1 = best):
- SLEEP_POD : 4.02
- GALAXY_SOUNDS : 4.30
- OXYGEN_SHAKE : 5.32
- UV_VISOR : 5.61
- PANEL : 5.75
- SNACKPACK : 5.75
- PEBBLES : 5.79
- MICROCHIP : 6.10
- ROBOT : 6.18
- TRANSLATOR : 6.19

Final-tick cumulative aggregate return:
- OXYGEN_SHAKE : +139.00
- TRANSLATOR : +123.10
- PANEL : +49.50
- ROBOT : +41.50
- PEBBLES : +0.10
- SNACKPACK : -13.30
- GALAXY_SOUNDS : -120.60
- MICROCHIP : -138.20
- UV_VISOR : -171.30
- SLEEP_POD : -238.30

## Cross-cluster lead-lag — global pairs (top by |corr|)
- OXYGEN_SHAKE -> SNACKPACK  lag=1t  corr=-0.069
- SNACKPACK -> UV_VISOR  lag=1t  corr=-0.061
- SNACKPACK -> OXYGEN_SHAKE  lag=1t  corr=-0.059
- UV_VISOR -> SNACKPACK  lag=1t  corr=-0.058
- GALAXY_SOUNDS -> SNACKPACK  lag=1t  corr=-0.056
- TRANSLATOR -> SNACKPACK  lag=1t  corr=-0.056
- SNACKPACK -> GALAXY_SOUNDS  lag=1t  corr=-0.055
- PANEL -> SNACKPACK  lag=1t  corr=-0.051

## Stable lead-lag pairs (cluster level)
- **OXYGEN_SHAKE -> SNACKPACK**  global_lag=1t  corr=-0.069  stability=1.00  per-window lags=[1;1;1;1;1]
- **SNACKPACK -> UV_VISOR**  global_lag=1t  corr=-0.061  stability=1.00  per-window lags=[1;1;1;1;1]
- **SNACKPACK -> OXYGEN_SHAKE**  global_lag=1t  corr=-0.059  stability=1.00  per-window lags=[1;1;1;1;1]
- **UV_VISOR -> SNACKPACK**  global_lag=1t  corr=-0.058  stability=1.00  per-window lags=[1;1;1;1;1]
- **GALAXY_SOUNDS -> SNACKPACK**  global_lag=1t  corr=-0.056  stability=1.00  per-window lags=[1;1;1;1;1]
- **TRANSLATOR -> SNACKPACK**  global_lag=1t  corr=-0.056  stability=1.00  per-window lags=[1;1;1;1;1]
- **SNACKPACK -> GALAXY_SOUNDS**  global_lag=1t  corr=-0.055  stability=1.00  per-window lags=[1;1;1;1;1]
- **PANEL -> SNACKPACK**  global_lag=1t  corr=-0.051  stability=1.00  per-window lags=[1;1;1;1;1]

## Granger confirmation on stable pairs
- OXYGEN_SHAKE->SNACKPACK: best p = 0.0000  [{'granger_p_lag1': 1.65871531169603e-14, 'granger_p_lag2': 1.2430858227844779e-14, 'granger_p_lag3': 7.134869133556076e-14, 'granger_p_lag4': 2.5373836586654755e-13, 'granger_p_lag5': 8.652007685882284e-13}]
- SNACKPACK->UV_VISOR: best p = 0.0000  [{'granger_p_lag1': 5.331020472720391e-25, 'granger_p_lag2': 1.4850475517056623e-24, 'granger_p_lag3': 9.447435136218286e-24, 'granger_p_lag4': 1.795415149563753e-23, 'granger_p_lag5': 5.1915000796711925e-23}]
- SNACKPACK->OXYGEN_SHAKE: best p = 0.0000  [{'granger_p_lag1': 9.282040080989234e-20, 'granger_p_lag2': 4.2294114415870736e-20, 'granger_p_lag3': 2.640450508755515e-19, 'granger_p_lag4': 5.675094071684544e-19, 'granger_p_lag5': 1.6971362263578568e-18}]
- UV_VISOR->SNACKPACK: best p = 0.0000  [{'granger_p_lag1': 5.660369729416604e-07, 'granger_p_lag2': 8.454064166906518e-08, 'granger_p_lag3': 1.3207935952702962e-07, 'granger_p_lag4': 4.997628365303709e-07, 'granger_p_lag5': 8.690264667574074e-07}]
- GALAXY_SOUNDS->SNACKPACK: best p = 0.0000  [{'granger_p_lag1': 3.0560881270324606e-07, 'granger_p_lag2': 2.117933569690289e-07, 'granger_p_lag3': 6.014705580427051e-07, 'granger_p_lag4': 1.0104679636997814e-06, 'granger_p_lag5': 3.5467274291051923e-06}]
- TRANSLATOR->SNACKPACK: best p = 0.0000  [{'granger_p_lag1': 3.962561298137774e-09, 'granger_p_lag2': 3.4338229542995733e-09, 'granger_p_lag3': 4.869172006566308e-10, 'granger_p_lag4': 1.6718133291063823e-09, 'granger_p_lag5': 6.293632776914416e-09}]
- SNACKPACK->GALAXY_SOUNDS: best p = 0.0000  [{'granger_p_lag1': 8.239473148636059e-20, 'granger_p_lag2': 1.3570074794923802e-19, 'granger_p_lag3': 6.396607619815761e-19, 'granger_p_lag4': 1.1544048156384431e-18, 'granger_p_lag5': 5.021590879021328e-18}]
- PANEL->SNACKPACK: best p = 0.0000  [{'granger_p_lag1': 9.343959733248611e-08, 'granger_p_lag2': 7.707824022780381e-08, 'granger_p_lag3': 3.086850906565707e-07, 'granger_p_lag4': 1.0898434104469662e-06, 'granger_p_lag5': 2.5261296818067614e-06}]
