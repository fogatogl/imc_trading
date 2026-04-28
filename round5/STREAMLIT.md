# Round 5 Pipeline Visualizer — Streamlit deployment

Public Streamlit Cloud entry point: [`round5/visualizer.py`](visualizer.py).

## Deploy on Streamlit Community Cloud

1. Sign in at <https://share.streamlit.io> with the GitHub account that
   owns this repo.
2. **New app** → pick this repository.
3. Branch: `main`. Main file path: `round5/visualizer.py`.
4. Python version: 3.11. The platform reads [`requirements.txt`](../requirements.txt)
   from the repo root automatically.
5. Submodules: this repo has [`imc_commun`](../imc_commun) as a submodule
   that the pipeline imports (`from imc_commun.stats import …`). Streamlit
   Cloud supports submodules by default — the build step runs
   `git submodule update --init --recursive`. No extra configuration.
6. Click **Deploy**.

## What the visualizer reads

The app is read-only over the artifacts already committed to the repo:

| Folder | Purpose |
|---|---|
| `round5/reports/<FAMILY>/` | per-family pipeline outputs (CSVs + figures) |
| `round5/reports/CROSS/` | cross-family clustering / lead-lag analysis |
| `round5/reports/CROSS/vol_spikes/` | volatility-spike survey |
| `round5/reports/CROSS/vol_spikes/anatomy/` | spike-mechanism analysis + strategy sim |
| `round5/reports/CALIBRATION/` | gate threshold validation |
| `dataset/ROUND_5/prices_round_5_day_{2,3,4}.csv` | raw prices (Product Detail page) |
| `dataset/ROUND_5/trades_round_5_day_{2,3,4}.csv` | raw trades (Product Detail page) |

To regenerate artifacts before deploying:

```bash
.venv/Scripts/python.exe round5/family_report.py --family ALL
.venv/Scripts/python.exe round5/calibration.py
.venv/Scripts/python.exe round5/cross_analysis.py
.venv/Scripts/python.exe round5/vol_spikes.py
.venv/Scripts/python.exe round5/spike_anatomy.py
.venv/Scripts/python.exe round5/spike_strategy_sim.py
```

Then commit the regenerated CSVs / PNGs and push — Streamlit Cloud
auto-redeploys on every push to the configured branch.

## Local run

```bash
.venv/Scripts/streamlit.exe run round5/visualizer.py
```
