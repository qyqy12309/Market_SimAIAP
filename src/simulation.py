import random

from src.market.market import Market
from src.market.trader import (NoiseTrader, MarketMaker,)


class Simulation:
    def __init__(
        self,
        seed=42,
        num_traders=1000,
        num_market_makers=5,
        participation_rate=0.0005,
        initial_price=10000,
        ticks_per_candle=10,
    ):
        self.seed = seed
        self.num_traders = num_traders
        self.num_market_makers = num_market_makers
        self.participation_rate = participation_rate
        self.initial_price = initial_price
        self.ticks_per_candle = ticks_per_candle

        self.reset()

    def reset(self):

        self.rng = random.Random(
            self.seed
        )

        self.market = Market(
            initial_price=self.initial_price,
            ticks_per_candle=self.ticks_per_candle,
        )

        self.traders = [
            NoiseTrader(
                trader_id=i,
                participation_rate=self.participation_rate,
            )
            for i in range(
                self.num_traders
            )
        ]

        self.market_makers = [
            MarketMaker(
                trader_id=(
                    self.num_traders + i
                ),
                spread_cents=4,
                quantity=10,
                refresh_rate=0.2,
            )
            for i in range(
                self.num_market_makers
            )
        ]

    def step(self):

        # ---------------------------------------------
        # NOISE TRADERS
        # ---------------------------------------------

        for trader in self.traders:

            trader.act(
                market=self.market,
                rng=self.rng,
            )

        # ---------------------------------------------
        # MARKET MAKERS
        # ---------------------------------------------

        for market_maker in self.market_makers:

            # First process trades that may have hit
            # the maker's previous resting quotes.
            market_maker.update_inventory(
                self.market.orderbook.trades
            )

            market_maker.act(
                market=self.market,
                rng=self.rng,
            )

        # Catch executions caused during this tick.
        for market_maker in self.market_makers:

            market_maker.update_inventory(
                self.market.orderbook.trades
            )

        self.market.next_tick()

    def run(self, num_ticks):
        """
        Advance the simulation by multiple ticks.
        """

        for _ in range(num_ticks):
            self.step()