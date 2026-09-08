from dataclasses import dataclass


@dataclass
class Candle:
    start_tick: int
    end_tick: int

    open: int
    high: int
    low: int
    close: int

    volume: int
    trade_count: int