# IMC Prosperity 4 — Backtest Guide

Two independent backtesting tools, each giving a different perspective on your strategy.

---

## Tool 1 — Historical Replay (`backtest_visualize.py`)
> Replays your strategy on the **real recorded market data**. Gives one deterministic result.

### Setup (one-time)
```powershell
# Install the backtester into system Python
pip install git+https://github.com/kevin-fu1/imc-prosperity-4-backtester.git
```

### Run
```powershell
# Make sure NO venv is active (run `deactivate` if needed)
cd C:\Users\fogat\Desktop\imc_trading\imc_trading\TUTORIAL_ROUND_1
python backtest_visualize.py tomates\subtom.py --round 0 --open
```

This generates `backtest_report.html` and opens it in your browser.

### Change strategy
Just swap the path to any file with a `Trader.run()` method:
```powershell
python backtest_visualize.py tomates\subtom.py      # MVA strategy
python backtest_visualize.py artomtrader.py          # AR(5) strategy
python backtest_visualize.py my_new_strategy.py      # any strategy
```

---

## Tool 2 — Monte Carlo Simulator (`prosperity4mcbt`)
> Runs your strategy across **100–1000 synthetic market scenarios**. Shows robustness, not just one outcome.

### Setup (one-time)
```powershell
# 1. Clone the repo (from imc_trading\imc_trading\)
cd C:\Users\fogat\Desktop\imc_trading\imc_trading
git clone https://github.com/chrispyroberts/imc-prosperity-4.git

# 2. Install Python dependencies
cd imc-prosperity-4\backtester
uv venv
uv sync
uv pip install -e .

# 3. Install visualizer dependencies
cd ..\visualizer
npm install
```

> Rust must be installed: https://rustup.rs — restart PowerShell after installing.

### Run (every time)

**Terminal 1** — start the visualizer frontend and leave it running:
```powershell
cd C:\Users\fogat\Desktop\imc_trading\imc_trading\imc-prosperity-4\visualizer
npm run dev
```

**Terminal 2** — activate the venv and run the backtest:
```powershell
cd C:\Users\fogat\Desktop\imc_trading\imc_trading\imc-prosperity-4\backtester
& .venv\Scripts\Activate.ps1   # (.venv) appears in your prompt
cd ..
prosperity4mcbt ..\TUTORIAL_ROUND_1\tomates\subtom.py --quick --vis --out tmp\subtom\dashboard.json
```

Dashboard opens automatically at `http://localhost:5173`.

### Change strategy
```powershell
prosperity4mcbt ..\TUTORIAL_ROUND_1\tomates\subtom.py     --quick --vis --out tmp\subtom\dashboard.json
prosperity4mcbt ..\TUTORIAL_ROUND_1\artomtrader.py         --quick --vis --out tmp\artom\dashboard.json
prosperity4mcbt ..\TUTORIAL_ROUND_1\my_new_strategy.py     --quick --vis --out tmp\new\dashboard.json
```

### Presets
| Flag | Sessions | Use when |
|---|---|---|
| `--quick` | 100 | Fast feedback during development |
| *(default)* | 100 | Same as quick |
| `--heavy` | 1000 | Final validation before submitting |

---

## Which tool to use?

| Question | Tool |
|---|---|
| "What PnL would I have scored on the real days?" | Historical Replay |
| "Is my strategy consistently profitable?" | Monte Carlo |
| "Am I getting lucky or is this robust?" | Monte Carlo |
| "Which of my two strategies is better?" | Both |

A strategy that scores well on **both** is far more trustworthy than one that only looks good on the two real days.

---

## Common errors

| Error | Fix |
|---|---|
| `No module named prosperity4bt` | Run `deactivate` to exit any venv, then retry |
| `prosperity4mcbt not recognized` | Activate the venv first: `& .venv\Scripts\Activate.ps1` |
| `vite not recognized` | Run `npm install` inside the `visualizer\` folder |
| `localhost:5555` unreachable | Use Chrome/Edge instead of Firefox, or load `dashboard.json` manually via the UI |
| `EFTYPE` on npm install | Your Node.js is too new — downgrade to v20 LTS from https://nodejs.org |
