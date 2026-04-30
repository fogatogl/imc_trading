# PEBBLES — Simple-Signal Gate Test

Live-haircut applied: ×0.30
Each signal feeds a 1-feature Ridge calibrating edge in price units.

## Passes (all 4 conditions)

_None._

## Per-condition pass-rate

- cond1: 7.1% pass (5 / 70)
- cond2: 61.4% pass (43 / 70)
- cond3: 32.9% pass (23 / 70)
- cond4: 77.1% pass (54 / 70)

## All combos (IC ranked)

- `PEBBLES_XL | neg_zscore_mid_50 | h=100`: IC=`+0.1269`, gate=FAIL, frac_clear=`0.178`
- `PEBBLES_XS | neg_zscore_mid_50 | h=100`: IC=`+0.1098`, gate=FAIL, frac_clear=`0.856`
- `PEBBLES_XL | neg_zscore_mid_50 | h=50`: IC=`+0.1090`, gate=FAIL, frac_clear=`0.002`
- `PEBBLES_XL | neg_spread | h=100`: IC=`+0.1031`, gate=FAIL, frac_clear=`0.492`
- `PEBBLES_XS | neg_spread | h=100`: IC=`+0.0979`, gate=FAIL, frac_clear=`0.029`
- `PEBBLES_XL | neg_zscore_vwap_50 | h=100`: IC=`+0.0951`, gate=FAIL, frac_clear=`0.220`
- `PEBBLES_M | neg_spread | h=100`: IC=`+0.0938`, gate=FAIL, frac_clear=`0.029`
- `PEBBLES_S | neg_spread | h=100`: IC=`+0.0934`, gate=FAIL, frac_clear=`0.107`
- `PEBBLES_XS | neg_spread | h=50`: IC=`+0.0870`, gate=FAIL, frac_clear=`0.020`
- `PEBBLES_XL | neg_spread | h=50`: IC=`+0.0716`, gate=FAIL, frac_clear=`0.049`
- `PEBBLES_XS | momentum_10 | h=100`: IC=`+0.0702`, gate=FAIL, frac_clear=`0.818`
- `PEBBLES_S | neg_spread | h=50`: IC=`+0.0689`, gate=FAIL, frac_clear=`0.029`
- `PEBBLES_M | neg_spread | h=50`: IC=`+0.0684`, gate=FAIL, frac_clear=`0.029`
- `PEBBLES_XL | momentum_10 | h=50`: IC=`+0.0632`, gate=FAIL, frac_clear=`0.001`
- `PEBBLES_XS | momentum_10 | h=50`: IC=`+0.0581`, gate=FAIL, frac_clear=`0.019`
- `PEBBLES_XL | momentum_10 | h=100`: IC=`+0.0578`, gate=FAIL, frac_clear=`0.026`
- `PEBBLES_M | trade_imbalance | h=50`: IC=`+0.0573`, gate=FAIL, frac_clear=`0.002`
- `PEBBLES_XL | neg_zscore_vwap_50 | h=50`: IC=`+0.0535`, gate=FAIL, frac_clear=`0.001`
- `PEBBLES_S | trade_imbalance | h=50`: IC=`+0.0446`, gate=FAIL, frac_clear=`0.000`
- `PEBBLES_S | trade_imbalance | h=100`: IC=`+0.0443`, gate=FAIL, frac_clear=`0.075`
- `PEBBLES_XL | trade_imbalance | h=50`: IC=`+0.0379`, gate=FAIL, frac_clear=`0.002`
- `PEBBLES_M | neg_zscore_mid_50 | h=100`: IC=`+0.0375`, gate=FAIL, frac_clear=`0.000`
- `PEBBLES_M | trade_imbalance | h=100`: IC=`+0.0352`, gate=FAIL, frac_clear=`0.007`
- `PEBBLES_M | neg_zscore_vwap_50 | h=100`: IC=`+0.0315`, gate=FAIL, frac_clear=`0.006`
- `PEBBLES_M | momentum_10 | h=100`: IC=`+0.0190`, gate=FAIL, frac_clear=`0.000`
- `PEBBLES_L | neg_spread | h=50`: IC=`+0.0183`, gate=FAIL, frac_clear=`0.029`
- `PEBBLES_M | obi_l3 | h=50`: IC=`+0.0160`, gate=FAIL, frac_clear=`0.000`
- `PEBBLES_L | neg_spread | h=100`: IC=`+0.0110`, gate=FAIL, frac_clear=`0.029`
- `PEBBLES_S | obi_l3 | h=100`: IC=`+0.0101`, gate=FAIL, frac_clear=`0.015`
- `PEBBLES_XL | trade_imbalance | h=100`: IC=`+0.0093`, gate=FAIL, frac_clear=`0.009`
