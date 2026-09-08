from pathlib import Path

import pandas as pd


class MarketRecorder:
    def __init__(self, output_dir="data/raw"):
        self.output_dir = Path(output_dir)

        self.output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

    def save_candles(
        self,
        market,
        filename="candles.parquet",
    ):
        rows = []

        for candle in market.candles:
            rows.append(
                {
                    "start_tick": candle.start_tick,
                    "end_tick": candle.end_tick,
                    "open": candle.open,
                    "high": candle.high,
                    "low": candle.low,
                    "close": candle.close,
                    "volume": candle.volume,
                    "trade_count": candle.trade_count,
                }
            )

        df = pd.DataFrame(rows)

        path = self.output_dir / filename

        df.to_parquet(
            path,
            index=False,
        )

        return path

    def save_trades(
        self,
        market,
        filename="trades.parquet",
    ):
        df = pd.DataFrame(
            market.orderbook.trades
        )

        path = self.output_dir / filename

        df.to_parquet(
            path,
            index=False,
        )

        return path
    def save_snapshots(
    self,
    market,
    filename="snapshots.parquet",
):
        rows = []

        for snapshot in market.snapshots:
            rows.append(
                {
                    "tick": snapshot.tick,
                    "last_price": snapshot.last_price,
                    "best_bid": snapshot.best_bid,
                    "best_ask": snapshot.best_ask,
                    "spread": snapshot.spread,
                    "mid_price": snapshot.mid_price,
                    "bid_depth": snapshot.bid_depth,
                    "ask_depth": snapshot.ask_depth,
                    "imbalance": snapshot.imbalance,
                }
            )

        df = pd.DataFrame(rows)

        path = self.output_dir / filename

        df.to_parquet(
            path,
            index=False,
        )

        return path