from copy import deepcopy
from src.config import DEFAULT_CONFIG
import random
from src.market.regime import MarketRegimeController
from src.market.market import Market
from src.market.trader import (
    NoiseTrader,
    MomentumTrader,
    MeanReversionTrader,
    LiquidityTaker,
    MarketMaker,
)
class Simulation:
    def __init__(self, config=None):

        if config is None:
            config = deepcopy(DEFAULT_CONFIG)

        self.config = config
        self.seed = config.seed
        self.num_traders = config.population.noise_traders
        self.num_momentum_traders = config.population.momentum_traders
        self.num_mean_reversion_traders = config.population.mean_reversion_traders
        self.num_liquidity_takers = config.population.liquidity_takers
        self.num_market_makers = config.population.market_makers

        self.rng = random.Random(self.seed)
        self.reset()

    def reset(self):

        self.rng = random.Random(self.seed)

        self.regime_controller = (
            MarketRegimeController(
                rng=self.rng,
                config=self.config.regime,
            )
        )
        self.market = Market (
        initial_price= self.config.market.initial_price,
        ticks_per_candle= self.config.market.ticks_per_candle
        )

        self.traders = [
            NoiseTrader(
                trader_id=i,
                participation_rate=(
                    self.config.noise
                    .participation_rate
                ),
                max_price_offset=(
                    self.config.noise
                    .max_price_offset
                ),
                max_quantity=(
                    self.config.noise
                    .max_quantity
                ),
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
                lookback=(
                    self.config.momentum
                    .lookback
                ),
                threshold_cents=(
                    self.config.momentum
                    .threshold_cents
                ),
                quantity=(
                    self.config.momentum
                    .quantity
                ),
                participation_rate=(
                    self.config.momentum
                    .participation_rate
                ),
                price_offset_cents=(
                    self.config.momentum
                    .price_offset_cents
                ),
            )
            for i in range(self.num_momentum_traders)
        ]

        self.mean_reversion_traders = [
            MeanReversionTrader(
                trader_id=(
                    self.num_traders
                    + self.num_momentum_traders
                    + i
                ),
                lookback=(
                    self.config.mean_reversion
                    .lookback
                ),
                threshold_cents=(
                    self.config.mean_reversion
                    .threshold_cents
                ),
                quantity=(
                    self.config.mean_reversion
                    .quantity
                ),
                participation_rate=(
                    self.config.mean_reversion
                    .participation_rate
                ),
            )
            for i in range(self.num_mean_reversion_traders)
        ]

        self.liquidity_takers = [
            LiquidityTaker(
                trader_id=(
                    self.num_traders
                    + self.num_momentum_traders
                    + self.num_mean_reversion_traders
                    + i
                ),
                participation_rate=(
                    self.config.liquidity_taker
                    .participation_rate
                ),
                imbalance_threshold=(
                    self.config.liquidity_taker
                    .imbalance_threshold
                ),
                max_spread_cents=(
                    self.config.liquidity_taker
                    .max_spread_cents
                ),
                quantity=(
                    self.config.liquidity_taker
                    .quantity
                ),
            )
        for i in range(self.num_liquidity_takers)
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
                spread_cents=(
                    self.config.market_maker
                    .spread_cents
                ),
                quantity=(
                    self.config.market_maker
                    .quantity
                ),
                refresh_rate=(
                    self.config.market_maker
                    .refresh_rate
                ),
                inventory_skew=(
                    self.config.market_maker
                    .inventory_skew
                ),
                initial_cash=(
                    self.config.market_maker.initial_cash
                ),
            )
            for i in range(self.num_market_makers)
        ]

    def step(self):

        self.regime_controller.step(
            self.market.tick
        )

        # ---------------------------------------------
        # CANCEL OLD / RANDOM NOISE-TRADER ORDERS
        # ---------------------------------------------

        self.market.cancel_stale_orders(
            rng=self.rng,
            num_noise_traders=(self.config.population.noise_traders),
            cancel_probability=(self.config.market.cancellation_probability),
            max_order_age=(self.config.market.max_order_age)
        )
        # ---------------------------------------------
        # NOISE TRADERS
        # ---------------------------------------------

        for trader in self.traders:
            trader.act(
                self.market,
                self.rng,
                regime_config=(
                    self.regime_controller
                    .current_config
                ),
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