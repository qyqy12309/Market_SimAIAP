# Market Simulator

An agent-based financial market simulator written in Python.

The project simulates a simplified electronic limit-order-book market in which autonomous traders submit orders, orders interact through a matching engine, trades determine market prices, and executed trades are aggregated into candlestick data.

A live Streamlit dashboard provides a visual view of the simulated market, including price action, bid/ask quotes, spread, order-book depth, recent trades, market statistics, market-maker state, and machine-learning forecast overlays.

The project is being built incrementally from first principles to study market microstructure, trader behavior, liquidity, price formation, volatility, and forecasting.

---

## Current Features

The simulator currently includes:

- Limit buy and sell orders
- Price-time priority matching
- FIFO matching within the same price level
- Partial order fills
- Order cancellation
- Order quantity reduction
- Stochastic order cancellation
- Forced expiration of stale orders
- Bid and ask order books
- Best bid and best ask calculation
- Bid-ask spread calculation
- Trade recording
- Trader ownership of orders and executions
- Buyer/seller and maker/taker attribution
- Discrete simulation ticks
- OHLCV candlestick generation
- Continuous candles during periods without trades
- Market snapshots
- Midprice tracking
- Best-level market depth tracking
- Order-book imbalance tracking
- Trade-rate statistics
- Realized-volatility statistics
- Total-volume statistics
- Noise traders
- Momentum traders
- Mean-reversion traders
- Liquidity takers
- Market makers
- Market-maker quote cancellation and replacement
- Market-maker inventory tracking
- Inventory-aware market-maker quoting
- Market-maker cash, equity, and P&L tracking
- Deterministic simulation through random seeds
- Per-agent-type order statistics
- Parquet export for trades and candles
- Live Streamlit dashboard
- Plotly candlestick visualization
- Order-book depth ladder
- Order-book depth bars overlaid on the price chart
- Recent trade tape
- Market-activity panel
- Adjustable simulation speed
- Play, pause, step, and reset controls
- Configurable chart history
- Forecast-model selector
- Lagged walk-forward forecast overlays
- Decision Tree forecasting
- Linear Regression forecasting
- AutoReg time-series forecasting
- Persistent market-regime controller
- Calm, normal, trending-up, trending-down, and high-volatility regimes
- Regime-dependent noise-trader behavior

---

# Core Idea

The simulator does **not** generate a price series directly.

Instead, price emerges from interactions between traders and the order book.

```text
Trader Strategy
      ↓
    Order
      ↓
  Order Book
      ↓
   Matching
      ↓
    Trade
      ↓
 Market Price
      ↓
   Candles
      ↓
 Dashboard
```

The market price is therefore an output of the simulated market rather than an input to a random price generator.

The same principle is used for volatility regimes. A regime does not directly modify `last_price`. Instead, it modifies trader behavior such as participation, directional bias, order size, and price placement. Prices still emerge through executions.

---

# Prelude

To run the project on a new system:

```bash
conda env create -f environment.yml
conda activate market_sim
streamlit run dashboard.py
```

---

# Architecture

The project is organized into several conceptual layers.

## 1. Agents

Agents decide whether and how to trade.

### Noise Traders

Noise traders provide stochastic background order flow.

Their behavior can include:

- Probabilistic participation
- Buy/sell selection
- Randomized limit-price placement
- Randomized order quantity
- Regime-dependent participation
- Regime-dependent directional bias
- Regime-dependent order size
- Regime-dependent price offsets

The regime controller currently influences noise-trader behavior, allowing persistent periods of calm, directional pressure, and elevated activity without directly forcing the market price.

### Momentum Traders

Momentum traders compare the current price with a historical price over a configurable lookback window.

Conceptually:

```text
Recent upward move   → buy
Recent downward move → sell
No strong move       → do nothing
```

They provide trend-following pressure and can reinforce persistent price movement.

### Mean-Reversion Traders

Mean-reversion traders respond in the opposite direction to sufficiently large recent price moves.

Conceptually:

```text
Price rose strongly → sell
Price fell strongly → buy
No strong move      → do nothing
```

They provide a stabilizing force against sustained directional movement.

### Liquidity Takers

Liquidity takers inspect the top of the order book and react to strong bid/ask imbalance.

When imbalance is sufficiently large and the spread is acceptable, they submit an aggressive marketable limit order that crosses the spread.

Conceptually:

```text
Strong bid-side depth → aggressive buy
Strong ask-side depth → aggressive sell
```

### Market Makers

Market makers continuously provide liquidity by maintaining both bid and ask quotes around a reference price.

They:

1. Cancel stale quotes
2. Track executed inventory
3. Track cash resulting from executions
4. Adjust their reference price based on inventory
5. Submit replacement bid and ask orders
6. Expose equity and mark-to-market P&L

This creates a feedback mechanism between executions, inventory, liquidity, and future order placement.

---

## 2. Matching Engine

The order book maintains resting buy and sell orders.

Orders follow **price-time priority**.

For bids:

```text
Higher price = higher priority
```

For asks:

```text
Lower price = higher priority
```

Orders at the same price are processed in FIFO order.

Example:

```text
Bid #1: BUY 5 @ $100.00
Bid #2: BUY 7 @ $100.00
Bid #3: BUY 4 @ $100.00
```

If an incoming sell order sells 8 shares at $100.00:

```text
Bid #1 fills 5
Bid #2 fills 3
Bid #3 remains untouched
```

The engine also supports:

- Partial executions
- Resting residual quantities
- Cancellation
- Quantity reduction
- Maker/taker attribution
- Buyer/seller attribution

---

# Price Formation

Prices are represented internally as integer cents.

```text
$100.00 → 10000
$99.17  → 9917
```

This avoids unnecessary floating-point issues when representing monetary prices.

The current market price is the latest execution price:

```text
last_price = latest trade price
```

A buy order can execute when its limit price is greater than or equal to the best available ask.

A sell order can execute when its limit price is less than or equal to the best available bid.

Crossing limit orders therefore behave like marketable limit orders.

---

# Bid-Ask Spread

The best bid is:

```text
highest resting buy price
```

The best ask is:

```text
lowest resting sell price
```

The spread is:

```text
spread = best ask - best bid
```

Example:

```text
Best Bid: $99.17
Best Ask: $99.19
Spread = $0.02
```

The spread is generated by the state of the simulated order book.

---

# Market Snapshots and Statistics

The market records snapshots over simulation time.

A snapshot can contain:

- Tick
- Last traded price
- Best bid
- Best ask
- Spread
- Midprice
- Best-bid depth
- Best-ask depth
- Order-book imbalance

Order-book imbalance is derived from best-level depth:

```text
imbalance = (bid_depth - ask_depth)
            / (bid_depth + ask_depth)
```

The market also exposes aggregate statistics used by the dashboard, including:

- Midprice
- Best-bid depth
- Best-ask depth
- Imbalance
- Trade rate
- Realized volatility
- Total traded volume

---

# Order Lifecycle

Noise-trader orders can be cancelled or expired after resting in the book.

The simulator tracks:

- Total orders submitted
- Stochastic cancellations
- Forced expirations
- Current resting-order count
- Orders submitted by trader type

Market-maker quote replacement is handled separately from stochastic noise-order cancellation.

---

# Market-Maker Inventory and P&L

Each market maker tracks its net inventory:

```text
inventory = cumulative shares bought - cumulative shares sold
```

Therefore:

```text
inventory > 0 → long
inventory < 0 → short
inventory = 0 → flat
```

Market makers modify their quotes according to inventory.

A simplified reservation-price rule is used:

```text
adjusted_price = market_price - inventory_skew × inventory
```

or:

```text
P* = P - kI
```

where:

- `P` = reference market price
- `I` = market-maker inventory
- `k` = inventory sensitivity
- `P*` = inventory-adjusted reference price

If a market maker becomes too long, its quotes move downward.

This makes it:

- Less aggressive when buying
- More aggressive when selling

If the market maker becomes short, the opposite occurs.

The feedback loop is:

```text
Trades
   ↓
Inventory + Cash
   ↓
Quote Adjustment
   ↓
Order Book
   ↓
Future Trades
```

Market-maker equity is marked to the current price:

```text
equity = cash + inventory × mark_price
```

and:

```text
PnL = equity - initial_cash
```

---

# Market Regimes

The simulator now includes a persistent market-regime controller.

Current regimes:

```text
CALM
NORMAL
TRENDING_UP
TRENDING_DOWN
HIGH_VOLATILITY
```

Regimes persist for multiple simulation ticks and transition according to a probability matrix.

The controller can adjust behavioral parameters such as:

- Buy probability
- Participation multiplier
- Order-size multiplier
- Price-offset multiplier
- Market-maker spread multiplier
- Market-maker size multiplier

The regime mechanism is designed so that **price is never directly changed by the regime**.

Instead:

```text
Regime
   ↓
Trader behavior / liquidity conditions
   ↓
Orders
   ↓
Order book
   ↓
Executions
   ↓
Price movement
```

At the current stage, regime-dependent behavior has been connected to noise traders. Additional regime sensitivity for other agent classes can be added incrementally and calibrated separately.

---

# Simulation Time

The market operates using discrete simulation ticks.

```text
Tick 0
Tick 1
Tick 2
...
Tick 1000
```

A tick represents a simulation step rather than a fixed amount of real-world time.

A simulation step currently includes the following broad sequence:

```text
Update market regime
        ↓
Process stale-order cancellation / expiration
        ↓
Noise traders act
        ↓
Momentum traders act
        ↓
Mean-reversion traders act
        ↓
Liquidity takers act
        ↓
Market makers update inventory
        ↓
Market makers refresh quotes
        ↓
Orders may execute
        ↓
Market-maker inventory is updated
        ↓
Market advances one tick
```

---

# Candlestick Generation

Trades are aggregated into OHLCV candles.

By default:

```text
10 simulation ticks = 1 candle
```

Each candle contains:

- Open
- High
- Low
- Close
- Volume
- Trade count
- Start tick
- End tick

For a collection of trades:

```text
Open  = first execution price
High  = highest execution price
Low   = lowest execution price
Close = final execution price
Volume = total executed quantity
```

If no trade occurs during a candle interval, the candle remains continuous using the previous market price with zero volume and zero trade count.

Therefore:

```text
1000 ticks / 10 ticks per candle = 100 candles
```

even when some intervals contain no executions.

---

# Forecasting and Machine Learning

The dashboard includes experimental forecasting models.

Current models:

```text
Decision Tree
Linear Regression
AutoReg
```

The user can select a model from the dashboard or disable forecasting entirely.

## Lagged Walk-Forward Overlay

Forecasts are evaluated using a lagged historical cutoff.

For example, with:

```text
Completed candles = 500
Forecast lag      = 30
Prediction length = 30
```

the model trains only on candles before candle 470.

It then recursively predicts candles 470 through 499.

Those predictions are drawn as gray candlesticks at the same timestamps as the realized candles.

This provides a visual backtest without training on the future observations being predicted.

Conceptually:

```text
Known history
     ↓
Forecast origin
     ↓
Recursive prediction
     ↓
Gray predicted candles
     ↓
Overlay against realized candles
```

The forecast length and lag are configurable from the dashboard.

## Decision Tree

The Decision Tree model uses lagged candle features and predicts future OHLC returns relative to an anchor price.

It serves as a nonlinear machine-learning baseline.

## Linear Regression

Linear Regression uses the same general forecasting interface and acts as a simple linear benchmark.

This makes it useful for comparing whether model complexity materially improves performance.

## AutoReg

AutoReg is a classical time-series model implemented with `statsmodels`.

It models lagged return series directly.

Separate autoregressive models are currently fitted for:

```text
Open returns
High returns
Low returns
Close returns
```

Future prices are reconstructed recursively from predicted returns.

Unlike the Decision Tree and Linear Regression models, AutoReg is explicitly time-series-oriented.

---

# Dashboard

The Streamlit dashboard provides a live interface to the running simulator.

Current functionality includes:

- Play simulation
- Pause simulation
- Advance one tick
- Reset simulation
- Adjustable ticks per second
- View current tick
- View last price
- View best bid
- View best ask
- View spread
- View total trades
- View total volume
- View trade rate
- View realized volatility
- View order-book imbalance
- View bid/ask depth
- View candlestick chart
- View current forming candle
- Change visible chart history
- Toggle order-book bars
- Change visible order-book depth levels
- View order-book ladder
- View recent trade tape
- View market activity
- View market-maker inventory
- View market-maker cash
- View market-maker equity
- View market-maker P&L
- Select forecasting model
- Configure forecast lag
- Configure forecast length
- View lagged predicted candles over realized candles

---

# Data Output

Simulation data is written to:

```text
data/raw/
```

Current datasets:

```text
candles.parquet
trades.parquet
```

Parquet provides compact, typed, columnar storage and integrates well with Python data-analysis tools.

---

# Project Structure

```text
Market_SimAIAP/
│
├── dashboard.py
├── main.py
├── environment.yml
│
├── data/
│   └── raw/
│       ├── candles.parquet
│       └── trades.parquet
│
├── src/
│   ├── simulation.py
│   │
│   ├── data/
│   │   ├── __init__.py
│   │   └── recorder.py
│   │
│   ├── ml/
│   │   ├── __init__.py
│   │   ├── decision_tree.py
│   │   ├── linear_regression.py
│   │   └── autoreg.py
│   │
│   └── market/
│       ├── __init__.py
│       ├── candle.py
│       ├── market.py
│       ├── order.py
│       ├── orderbook.py
│       ├── regime.py
│       ├── snapshot.py
│       └── trader.py
│
└── tests/
```

---

# Main Components

## `src/market/order.py`

Defines order-side and order-state information such as:

- Order
- Buy/sell side
- Trader ownership
- Price
- Quantity
- Timestamp / sequence information

## `src/market/orderbook.py`

Implements the matching engine.

Responsibilities include:

- Maintaining bids
- Maintaining asks
- Price priority
- FIFO time priority
- Partial fills
- Trade generation
- Cancellation
- Order reduction
- Best bid
- Best ask
- Spread
- Buyer/seller attribution
- Maker/taker attribution

## `src/market/market.py`

Maintains global market state.

Responsibilities include:

- Current simulation tick
- Last traded price
- Order submission
- Trade collection
- Candle creation
- Market snapshots
- Order lifecycle management
- Market statistics
- Orders-by-type statistics

## `src/market/candle.py`

Defines the candle data structure:

```text
start_tick
end_tick
open
high
low
close
volume
trade_count
```

## `src/market/snapshot.py`

Defines point-in-time market state used for analysis and trader signals.

Snapshot information includes market price, quotes, spread, depth, midprice, and imbalance.

## `src/market/regime.py`

Defines:

- Regime configuration
- Regime transition probabilities
- Persistent regime state
- Regime duration
- Current regime configuration
- Regime-transition history

## `src/market/trader.py`

Contains simulated trading agents:

```text
NoiseTrader
MomentumTrader
MeanReversionTrader
LiquidityTaker
MarketMaker
```

## `src/simulation.py`

Controls the simulation.

It owns or coordinates:

- Market
- Random-number generator
- Market-regime controller
- Noise traders
- Momentum traders
- Mean-reversion traders
- Liquidity takers
- Market makers

It provides:

```python
simulation.step()
```

for one simulation tick and:

```python
simulation.run(num_ticks)
```

for multiple ticks.

## `src/data/recorder.py`

Converts simulation output into datasets and saves them as Parquet files.

Currently records:

```text
candles.parquet
trades.parquet
```

## `src/ml/decision_tree.py`

Implements the Decision Tree candle forecaster.

It supports:

- Dataset construction
- Model fitting
- Forecast generation
- Recursive multi-step prediction
- Held-out evaluation

## `src/ml/linear_regression.py`

Implements the Linear Regression forecasting baseline.

It follows the same general forecasting interface used by the dashboard.

## `src/ml/autoreg.py`

Implements an autoregressive time-series forecaster using `statsmodels.tsa.ar_model.AutoReg`.

It forecasts OHLC return series and reconstructs future candle prices recursively.

## `dashboard.py`

Interactive Streamlit visualization and control surface for the running simulation.

It combines:

- Simulation controls
- Market metrics
- Market statistics
- Candlestick visualization
- Order-book visualization
- Trade tape
- Market-maker diagnostics
- Forecast-model selection
- Lagged forecast overlays

---

# Running the Project

Activate the environment:

```bash
conda activate market_sim
```

Run the simulator directly:

```bash
python main.py
```

Run the live dashboard:

```bash
streamlit run dashboard.py
```

Streamlit will start the dashboard and provide a local browser address.

---

# Current Model Limitations

This project remains an intentionally simplified market model.

It should **not** be interpreted as a calibrated representation of a real financial exchange.

Important limitations currently include:

- Simplified trader behavior
- Simplified market-maker strategy
- Cash and P&L accounting currently focused on market makers rather than all agents
- No margin or leverage
- No fundamental asset-value process
- No full information/news process
- No native unrestricted market-order type
- Simplified cancellation and expiration behavior
- No transaction fees or exchange rebates
- No latency model
- No formal trading sessions
- No exchange-specific tick-size schedule
- No empirical calibration to real order-flow distributions
- Regime parameters are heuristic rather than empirically calibrated
- Regime behavior is currently connected only to selected agent types
- No sophisticated portfolio or risk-management layer
- No realistic institutional execution algorithms
- Forecasting models are experimental and are not intended as trading signals
- Recursive multi-step forecasts can accumulate error
- Current ML evaluation remains relatively simple
- No full walk-forward cross-validation framework yet

The fact that generated prices visually resemble financial charts does not demonstrate that the simulator reproduces real financial-market dynamics.

The objective is to build those mechanisms explicitly, measure their effects, and progressively calibrate the simulator.

---

# Development Roadmap

## Completed

- [x] Order representation
- [x] Limit order book
- [x] Price-time priority
- [x] FIFO within price level
- [x] Partial fills
- [x] Order cancellation
- [x] Order quantity reduction
- [x] Trade generation
- [x] Buyer/seller attribution
- [x] Maker/taker attribution
- [x] Best bid and ask
- [x] Bid-ask spread
- [x] Simulation clock
- [x] OHLCV candles
- [x] Continuous empty candles
- [x] Market snapshots
- [x] Midprice tracking
- [x] Order-book imbalance tracking
- [x] Market-depth tracking
- [x] Realized-volatility statistics
- [x] Trade-rate statistics
- [x] Total-volume statistics
- [x] Noise traders
- [x] Momentum traders
- [x] Mean-reversion traders
- [x] Liquidity takers
- [x] Market makers
- [x] Market-maker quote replacement
- [x] Trader ownership tracking
- [x] Market-maker inventory tracking
- [x] Inventory-aware quoting
- [x] Market-maker cash accounting
- [x] Market-maker equity and P&L
- [x] Stochastic order cancellation
- [x] Forced stale-order expiration
- [x] Orders-by-type statistics
- [x] Deterministic random seeds
- [x] Parquet data recording
- [x] Streamlit live dashboard
- [x] Order-book ladder
- [x] Order-book bars on candlestick chart
- [x] Recent trade tape
- [x] Market-activity panel
- [x] Market-maker dashboard table
- [x] Forecast-model selector
- [x] Decision Tree forecasting
- [x] Linear Regression forecasting
- [x] AutoReg forecasting
- [x] Recursive multi-step forecasts
- [x] Lagged forecast/backtest overlay
- [x] Market-regime controller
- [x] Persistent regime transitions
- [x] Regime history tracking
- [x] Regime-dependent noise-trader behavior

## Near-Term

- [ ] Calibrate regime durations and transition probabilities
- [ ] Calibrate directional buy/sell bias
- [ ] Add regime-aware market-maker liquidity response
- [ ] Add regime-aware momentum and liquidity-taker behavior
- [ ] Add heavy-tailed order-size distributions
- [ ] Add persistent order-flow imbalance
- [ ] Add liquidity shocks
- [ ] Add rare information/news shocks
- [ ] Measure volatility clustering
- [ ] Compare return distributions with empirical market data
- [ ] Add common forecast evaluation panel
- [ ] Add MAE, RMSE, and directional-accuracy metrics
- [ ] Add walk-forward model comparison
- [ ] Add Random Forest forecaster
- [ ] Add gradient-boosted forecasting model
- [ ] Add LSTM / GRU sequence models

## Longer-Term

Potential future extensions include:

- Fundamental-value traders
- Heterogeneous agent populations
- Empirical volatility-regime calibration
- News and information processes
- Native market orders
- Stop orders
- Transaction costs
- Exchange fees and rebates
- Trader wealth and capital constraints
- Position limits
- Risk limits
- Latency
- Multiple assets
- Correlated assets
- More realistic order-arrival processes
- Empirical order-size distributions
- Empirical spread and depth calibration
- Backtesting agents inside the simulated market
- Reinforcement-learning agents
- TCN sequence models
- Transformer forecasting models
- Market microstructure experiments

---

# Design Philosophy

The project is being developed from first principles.

Instead of generating realistic-looking price charts directly, the goal is to model mechanisms that can produce market behavior:

```text
Agents
  ↓
Decisions
  ↓
Orders
  ↓
Liquidity
  ↓
Matching
  ↓
Executions
  ↓
Prices
  ↓
Market Statistics
  ↓
Forecasting / Analysis
```

Every new feature should answer two questions:

1. What market mechanism does this represent?
2. What observable behavior should change because of it?

The simulator is primarily an educational and experimental system for understanding how market structure and agent behavior can produce aggregate financial-market dynamics.

---

# Disclaimer

This project is for educational, research, and simulation purposes.

It is not a production trading system, exchange, execution engine, investment strategy, or financial advice.
