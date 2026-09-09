from dataclasses import dataclass, field


# ==========================================================
# MARKET
# ==========================================================

@dataclass
class MarketConfig:
    initial_price: int = 10_000
    ticks_per_candle: int = 10

    cancellation_probability: float = 0.02
    max_order_age: int = 200


# ==========================================================
# AGENT POPULATIONS
# ==========================================================

@dataclass
class PopulationConfig:
    noise_traders: int = 1000
    momentum_traders: int = 20
    mean_reversion_traders: int = 20
    liquidity_takers: int = 10
    market_makers: int = 5


# ==========================================================
# NOISE TRADERS
# ==========================================================

@dataclass
class NoiseTraderConfig:
    participation_rate: float = 0.0005
    max_price_offset: float = 0.01
    max_quantity: int = 10


# ==========================================================
# MOMENTUM TRADERS
# ==========================================================

@dataclass
class MomentumTraderConfig:
    lookback: int = 20
    threshold_cents: int = 5
    quantity: int = 5
    participation_rate: float = 0.10
    price_offset_cents: int = 0


# ==========================================================
# MEAN-REVERSION TRADERS
# ==========================================================

@dataclass
class MeanReversionTraderConfig:
    lookback: int = 20
    threshold_cents: int = 5
    quantity: int = 5
    participation_rate: float = 0.10


# ==========================================================
# LIQUIDITY TAKERS
# ==========================================================

@dataclass
class LiquidityTakerConfig:
    participation_rate: float = 0.05
    imbalance_threshold: float = 0.40
    max_spread_cents: int = 5
    quantity: int = 5


# ==========================================================
# MARKET MAKERS
# ==========================================================

@dataclass
class MarketMakerConfig:
    spread_cents: int = 4
    quantity: int = 10
    refresh_rate: float = 1.0
    inventory_skew: float = 0.05
    initial_cash: int = 100_000_000


# ==========================================================
# MARKET REGIMES
# ==========================================================

@dataclass
class RegimeConfigValues:
    buy_probability: float
    participation_multiplier: float
    size_multiplier: float
    price_offset_multiplier: float
    mm_spread_multiplier: float
    mm_size_multiplier: float


def default_regimes():
    return {
        "calm": RegimeConfigValues(
            buy_probability=0.50,
            participation_multiplier=0.70,
            size_multiplier=0.70,
            price_offset_multiplier=0.70,
            mm_spread_multiplier=0.80,
            mm_size_multiplier=1.20,
        ),

        "normal": RegimeConfigValues(
            buy_probability=0.50,
            participation_multiplier=1.00,
            size_multiplier=1.00,
            price_offset_multiplier=1.00,
            mm_spread_multiplier=1.00,
            mm_size_multiplier=1.00,
        ),

        "trending_up": RegimeConfigValues(
            buy_probability=0.54,
            participation_multiplier=1.15,
            size_multiplier=1.10,
            price_offset_multiplier=1.15,
            mm_spread_multiplier=1.10,
            mm_size_multiplier=0.90,
        ),

        "trending_down": RegimeConfigValues(
            buy_probability=0.46,
            participation_multiplier=1.15,
            size_multiplier=1.10,
            price_offset_multiplier=1.15,
            mm_spread_multiplier=1.10,
            mm_size_multiplier=0.90,
        ),

        "high_volatility": RegimeConfigValues(
            buy_probability=0.50,
            participation_multiplier=1.60,
            size_multiplier=1.80,
            price_offset_multiplier=2.00,
            mm_spread_multiplier=1.80,
            mm_size_multiplier=0.60,
        ),
    }


def default_regime_transitions():
    return {
        "calm": {
            "calm": 0.55,
            "normal": 0.40,
            "trending_up": 0.02,
            "trending_down": 0.02,
            "high_volatility": 0.01,
        },

        "normal": {
            "calm": 0.20,
            "normal": 0.55,
            "trending_up": 0.10,
            "trending_down": 0.10,
            "high_volatility": 0.05,
        },

        "trending_up": {
            "calm": 0.05,
            "normal": 0.45,
            "trending_up": 0.40,
            "trending_down": 0.03,
            "high_volatility": 0.07,
        },

        "trending_down": {
            "calm": 0.05,
            "normal": 0.45,
            "trending_up": 0.03,
            "trending_down": 0.40,
            "high_volatility": 0.07,
        },

        "high_volatility": {
            "calm": 0.05,
            "normal": 0.45,
            "trending_up": 0.15,
            "trending_down": 0.15,
            "high_volatility": 0.20,
        },
    }


@dataclass
class RegimeControllerConfig:
    initial_regime: str = "normal"
    min_duration: int = 100
    max_duration: int = 300

    regimes: dict = field(
        default_factory=default_regimes
    )

    transitions: dict = field(
        default_factory=default_regime_transitions
    )


# ==========================================================
# DECISION TREE
# ==========================================================

@dataclass
class DecisionTreeModelConfig:
    lookback: int = 20
    horizon: int = 3
    max_depth: int = 6
    min_samples_leaf: int = 5


# ==========================================================
# LINEAR REGRESSION
# ==========================================================

@dataclass
class LinearRegressionModelConfig:
    lookback: int = 20
    horizon: int = 3


# ==========================================================
# AUTOREG
# ==========================================================

@dataclass
class AutoRegModelConfig:
    lookback: int = 20
    horizon: int = 1
    lags: int = 20
    minimum_training_candles: int = 60


# ==========================================================
# FORECAST / BACKTEST DISPLAY
# ==========================================================

@dataclass
class ForecastConfig:
    default_model: str = "None"

    forecast_lag: int = 30
    forecast_length: int = 30

    min_forecast_lag: int = 5
    max_forecast_lag: int = 100
    forecast_lag_step: int = 5

    min_forecast_length: int = 3
    max_forecast_length: int = 50


# ==========================================================
# DASHBOARD
# ==========================================================

@dataclass
class DashboardConfig:
    default_speed: int = 10

    show_order_bars: bool = True
    order_book_levels: int = 12

    chart_history_default: int = 200


# ==========================================================
# TOP-LEVEL APPLICATION CONFIG
# ==========================================================

@dataclass
class AppConfig:
    seed: int = 42

    market: MarketConfig = field(
        default_factory=MarketConfig
    )

    population: PopulationConfig = field(
        default_factory=PopulationConfig
    )

    noise: NoiseTraderConfig = field(
        default_factory=NoiseTraderConfig
    )

    momentum: MomentumTraderConfig = field(
        default_factory=MomentumTraderConfig
    )

    mean_reversion: MeanReversionTraderConfig = field(
        default_factory=MeanReversionTraderConfig
    )

    liquidity_taker: LiquidityTakerConfig = field(
        default_factory=LiquidityTakerConfig
    )

    market_maker: MarketMakerConfig = field(
        default_factory=MarketMakerConfig
    )

    regime: RegimeControllerConfig = field(
        default_factory=RegimeControllerConfig
    )

    decision_tree: DecisionTreeModelConfig = field(
        default_factory=DecisionTreeModelConfig
    )

    linear_regression: LinearRegressionModelConfig = field(
        default_factory=LinearRegressionModelConfig
    )

    autoreg: AutoRegModelConfig = field(
        default_factory=AutoRegModelConfig
    )

    forecast: ForecastConfig = field(
        default_factory=ForecastConfig
    )

    dashboard: DashboardConfig = field(
        default_factory=DashboardConfig
    )


DEFAULT_CONFIG = AppConfig()
