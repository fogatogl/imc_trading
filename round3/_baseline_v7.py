"""Baseline wrapper: runs trader_gamma_v7 unmodified after patching LIMITS."""
import _bt_setup  # noqa: F401  -- patches prosperity4bt.data.LIMITS in place
from trader_gamma_v7 import Trader  # noqa: F401
