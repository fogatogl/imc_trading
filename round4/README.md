# Round 4 — The More The Merrier

**Closed:** 2026-04-28
**Products:** same instruments as round 3 (`HYDROGEL_PACK`,
`VELVETFRUIT_EXTRACT`, 10× `VEV_*`) — now annotated with counterparty
identifiers — plus the manual `AETHER_CRYSTAL` exotic.
**Official PnL:** **+99,202 SeaShells** (single live day = day 4)
**Platform doc:** [`Round 4 - "The More The Merrier" ...md`](Round%204%20-%20%E2%80%9CThe%20More%20The%20Merrier%E2%80%9D%201e43d50cdd2383929a6981dced4dbc53.md)

## Final submission

[`544098/544098.py`](544098/544098.py) — concat of `final_hydro` +
`final_voucher` + `final_ve`. Round-3 hydrogel block + OU-corrected BS
pricer trading 5000–5500 only + M67-boosted VE underlying.

| Product | PnL |
|---|---:|
| `HYDROGEL_PACK` | +39,970 |
| `VEV_5100` | +22,704 |
| `VEV_5000` | +13,870 |
| `VELVETFRUIT_EXTRACT` | +12,760 |
| `VEV_5200` | +6,001 |
| `VEV_5300` | +2,919 |
| `VEV_5400` | +779 |
| `VEV_5500` | +197 |
| `VEV_{4000, 4500, 6000, 6500}` | 0 each (not quoted) |
| **Total** | **+99,202** |

### Submission progression

Each numbered folder is one re-run on a different practice/live day:

- [`417667/`](../417667/) (day 2) — +16,410
- [`515364/`](515364/) (day 3) — −23,531 (gradinv VEV pinned long, VE drifted −42 ticks)
- [`516536/`](516536/) (day 3) — +19,881 (post-fix variant)
- [`544098/`](544098/) (day 4, final live) — **+99,202**

## What worked vs round 3

- **HP +39,970** (vs r3 +19,712, +103 %) — trending-aware anchor lifted hydrogel. The anchor was raised, not the model replaced.
- **VE +12,760** (vs r3 −2,531) — M67 boost flipped VE from drag to alpha.
- **VEV +46,470** (vs r3 +18,933) — skipping deep-ITM (4000/4500) and far-OTM (6000/6500) avoided round 3's −9 k VEV_4000 + VEV_4500 pit.
- No catastrophic strike. **Tightening the smile beat trying to fix it.**

## Research artefacts

- [`round4_research.md`](round4_research.md) — overarching round-4 research log
- [`round4_options_research.md`](round4_options_research.md) — VEV options pricer derivation, smile geometry, BS vs empirical delta
- [`round4_ve_vev_research.md`](round4_ve_vev_research.md) — VE/VEV joint dynamics, lead-lag, returns spread
- [`round4_vev6000_6500_research.md`](round4_vev6000_6500_research.md) — explicit case for skipping the far-OTM strikes
- [`research_round4.ipynb`](research_round4.ipynb), [`research_options.ipynb`](research_options.ipynb), [`research_ve_vev_combined.ipynb`](research_ve_vev_combined.ipynb) — analysis notebooks driving the docs above

## Reproducibility

```powershell
$env:PYTHONPATH="imc_trading/imc-prosperity-4-backtester"
.venv/Scripts/python.exe -m prosperity4bt round4/544098/544098.py 1--2 1--1 1-0
```
