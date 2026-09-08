from src.simulation import Simulation
from src.data.recorder import MarketRecorder


simulation = Simulation(
    seed=42,
    num_traders=1000,
    participation_rate=0.0005,
    initial_price=10000,
    ticks_per_candle=10,
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