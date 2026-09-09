from src.config import AppConfig
from src.simulation import Simulation
from src.data.recorder import MarketRecorder


config = AppConfig()

# Temporary experiment (comment out and run - note it doesnt override dashboard, only for testing)
#config.noise.participation_rate = 0.001
#config.momentum.participation_rate = 0.20
#config.market_maker.spread_cents = 6
#config.regime.min_duration = 100
#config.regime.max_duration = 250
# (run with: python main.py)

simulation = Simulation(config=config)

print()
print("AGENT CONFIG VALUES")

print(
    "Noise:",
    simulation.traders[0].participation_rate,
)

print(
    "Momentum:",
    simulation.momentum_traders[0].lookback,
    simulation.momentum_traders[0].participation_rate,
)

print(
    "Mean reversion:",
    simulation.mean_reversion_traders[0].lookback,
    simulation.mean_reversion_traders[0].participation_rate,
)

print(
    "Liquidity taker:",
    simulation.liquidity_takers[0].imbalance_threshold,
    simulation.liquidity_takers[0].quantity,
)

print(
    "Market maker:",
    simulation.market_makers[0].spread_cents,
    simulation.market_makers[0].quantity,
)

simulation.run(
    num_ticks=1000
)


market = simulation.market


print("SIMULATION COMPLETE")

print(
    "Ticks:",
    market.tick,
)

print(
    "Trades:",
    len(market.orderbook.trades),
)

print(
    "Candles:",
    len(market.candles),
)

print(
    "Last price:",
    f"${market.last_price / 100:.2f}",
)

print(
    "Best bid:",
    market.orderbook.best_bid(),
)

print(
    "Best ask:",
    market.orderbook.best_ask(),
)


print("\nLAST 10 CANDLES")

for candle in market.candles[-10:]:

    print(
        f"ticks {candle.start_tick:4d}-{candle.end_tick:4d} | "
        f"O ${candle.open / 100:7.2f} | "
        f"H ${candle.high / 100:7.2f} | "
        f"L ${candle.low / 100:7.2f} | "
        f"C ${candle.close / 100:7.2f} | "
        f"V {candle.volume:3d} | "
        f"T {candle.trade_count:2d}"
    )


recorder = MarketRecorder(
    output_dir="data/raw"
)


candle_path = recorder.save_candles(
    market
)

trade_path = recorder.save_trades(
    market
)


print(
    "\nSaved candles to:",
    candle_path,
)

print(
    "Saved trades to:",
    trade_path,
)