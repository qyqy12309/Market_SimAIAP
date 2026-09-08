from dataclasses import dataclass
from enum import Enum


class Side(Enum):
    BUY = "buy"
    SELL = "sell"


@dataclass
class Order:
    order_id: int
    trader_id: int | None
    side: Side
    price: int
    quantity: int
    timestamp: int