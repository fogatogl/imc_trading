from datamodel import OrderDepth, TradingState, Order
from typing import List, Dict

class Trader:

    def run(self, state: TradingState) -> Dict[str, List[Order]]:
        