import random

from src.market.market import Market
from src.market.trader import (
    NoiseTrader,
    MomentumTrader,
    MeanReversionTrader,
    LiquidityTaker,
    MarketMaker,
)
class Simulation:
    def __init__(
        self,
        seed=42,
        num_traders=1000,
        num_momentum_traders=20,
        num_mean_reversion_traders=20,
        num_liquidity_takers=10,
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
        self.num_momentum_traders = (num_momentum_traders)
        self.num_mean_reversion_traders = (num_mean_reversion_traders)
        self.num_liquidity_takers = (num_liquidity_takers)

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

        self.momentum_traders = [
            MomentumTrader(
                trader_id=(
                    self.num_traders + i
                ),
                lookback=20,
                threshold_cents=5,
                quantity=5,
                participation_rate=0.1,
            )
            for i in range(
                self.num_momentum_traders
            )
        ]

        self.mean_reversion_traders = [
            MeanReversionTrader(
                trader_id=(
                    self.num_traders
                    + self.num_momentum_traders
                    + i
                ),
                lookback=20,
                threshold_cents=5,
                quantity=5,
                participation_rate=0.1,
            )
            for i in range(
                self.num_mean_reversion_traders
            )
        ]

        self.liquidity_takers = [
            LiquidityTaker(
                trader_id=(
                    self.num_traders
                    + self.num_momentum_traders
                    + self.num_mean_reversion_traders
                    + i
                ),
                participation_rate=0.05,
                imbalance_threshold=0.4,
                max_spread_cents=5,
                quantity=5,
            )
            for i in range(
                self.num_liquidity_takers
            )
        ]

        self.market_makers = [
            MarketMaker(
                trader_id=(
                    self.num_traders
                    + self.num_momentum_traders
                    + self.num_mean_reversion_traders
                    + self.num_liquidity_takers
                    + i
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
        # CANCEL OLD / RANDOM NOISE-TRADER ORDERS
        # ---------------------------------------------

        self.market.cancel_stale_orders(
            rng=self.rng,
            num_noise_traders=self.num_traders,
            cancel_probability=0.02,
            max_order_age=200,
        )

        # ---------------------------------------------
        # NOISE TRADERS
        # ---------------------------------------------

        for trader in self.traders:
            trader.act(
                market=self.market,
                rng=self.rng,
            )

        # MOMENTUM TRADERS

        for trader in self.momentum_traders:
            trader.act(
                market=self.market,
                rng=self.rng,
            )

        #mean_reversion_traders

        for trader in self.mean_reversion_traders:
            trader.act(
                market=self.market,
                rng=self.rng,
            )

        # liquidity takers

        for trader in self.liquidity_takers:
            trader.act(
                market=self.market,
                rng=self.rng,
            )
            
        # ---------------------------------------------
        # MARKET MAKERS
        # ---------------------------------------------

        for market_maker in self.market_makers:

            market_maker.update_inventory(
                self.market.orderbook.trades
            )

            market_maker.act(
                market=self.market,
                rng=self.rng,
            )

        # Catch executions caused during this tick
        for market_maker in self.market_makers:

            market_maker.update_inventory(
                self.market.orderbook.trades
            )

        # ---------------------------------------------
        # ADVANCE TIME
        # ---------------------------------------------

        self.market.next_tick()

    def run(self, num_ticks):
        """
        Advance the simulation by multiple ticks.
        """

        for _ in range(num_ticks):
            self.step()