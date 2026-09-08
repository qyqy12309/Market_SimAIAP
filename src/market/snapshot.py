from dataclasses import dataclass


@dataclass
class MarketSnapshot:
    tick: int
    last_price: int

    best_bid: int | None
    best_ask: int | None

    spread: int | None
    mid_price: float | None

    bid_depth: int
    ask_depth: int

    imbalance: float | None