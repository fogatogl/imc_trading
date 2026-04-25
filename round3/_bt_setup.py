"""Round 3 backtester setup.

Patches `prosperity4bt.data.LIMITS` in-place to add Round 3 product limits.
Trader files import this module before declaring their `Trader` class so the
runner sees the correct limits when enforcing per-product position caps.
"""
from prosperity4bt.data import LIMITS

_R3_LIMITS = {
    "HYDROGEL_PACK": 200,
    "VELVETFRUIT_EXTRACT": 200,
    "VEV_4000": 300,
    "VEV_4500": 300,
    "VEV_5000": 300,
    "VEV_5100": 300,
    "VEV_5200": 300,
    "VEV_5300": 300,
    "VEV_5400": 300,
    "VEV_5500": 300,
    "VEV_6000": 300,
    "VEV_6500": 300,
}

for _sym, _lim in _R3_LIMITS.items():
    LIMITS.setdefault(_sym, _lim)
