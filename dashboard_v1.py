import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.simulation import Simulation


st.set_page_config(
    page_title="Market Simulator",
    layout="wide",
)


# --------------------------------------------------
# Create persistent simulation
# --------------------------------------------------

if "simulation" not in st.session_state:
    st.session_state.simulation = Simulation(
        seed=42,
        num_traders=1000,
        participation_rate=0.0005,
        initial_price=10000,
        ticks_per_candle=10,
    )


simulation = st.session_state.simulation
market = simulation.market


# --------------------------------------------------
# Controls
# --------------------------------------------------

st.title("Market Simulator")

control1, control2, control3, control4 = st.columns(4)


with control1:
    if st.button("Step 1 Tick"):
        simulation.step()


with control2:
    if st.button("Run 10 Ticks"):
        simulation.run(10)


with control3:
    if st.button("Run 100 Ticks"):
        simulation.run(100)


with control4:
    if st.button("Reset"):
        st.session_state.simulation = Simulation(
            seed=42,
            num_traders=1000,
            participation_rate=0.0005,
            initial_price=10000,
            ticks_per_candle=10,
        )

        st.rerun()


# Refresh references after simulation changes
simulation = st.session_state.simulation
market = simulation.market


# --------------------------------------------------
# Market statistics
# --------------------------------------------------

best_bid = market.orderbook.best_bid()
best_ask = market.orderbook.best_ask()

spread = market.orderbook.spread()


metric1, metric2, metric3, metric4, metric5 = st.columns(5)


metric1.metric(
    "Tick",
    market.tick,
)


metric2.metric(
    "Last Price",
    f"${market.last_price / 100:.2f}",
)


metric3.metric(
    "Best Bid",
    (
        f"${best_bid / 100:.2f}"
        if best_bid is not None
        else "-"
    ),
)


metric4.metric(
    "Best Ask",
    (
        f"${best_ask / 100:.2f}"
        if best_ask is not None
        else "-"
    ),
)


metric5.metric(
    "Spread",
    (
        f"${spread / 100:.2f}"
        if spread is not None
        else "-"
    ),
)


st.divider()


# --------------------------------------------------
# Candle data
# --------------------------------------------------

candles = market.candles.copy()


# --------------------------------------------------
# Add currently forming candle
# --------------------------------------------------

current_trades = market.current_candle_trades


if current_trades:

    prices = [
        trade["price"]
        for trade in current_trades
    ]

    current_candle = {
        "start_tick":
            market.tick
            - (market.tick % market.ticks_per_candle),

        "end_tick":
            market.tick,

        "open":
            prices[0],

        "high":
            max(prices),

        "low":
            min(prices),

        "close":
            prices[-1],

        "volume":
            sum(
                trade["quantity"]
                for trade in current_trades
            ),

        "trade_count":
            len(current_trades),
    }

else:

    current_candle = {
        "start_tick":
            market.tick
            - (market.tick % market.ticks_per_candle),

        "end_tick":
            market.tick,

        "open":
            market.last_price,

        "high":
            market.last_price,

        "low":
            market.last_price,

        "close":
            market.last_price,

        "volume":
            0,

        "trade_count":
            0,
    }


# --------------------------------------------------
# Convert candles to dataframe
# --------------------------------------------------

rows = []


for candle in candles:

    rows.append(
        {
            "start_tick": candle.start_tick,
            "end_tick": candle.end_tick,

            "open": candle.open / 100,
            "high": candle.high / 100,
            "low": candle.low / 100,
            "close": candle.close / 100,

            "volume": candle.volume,
            "trade_count": candle.trade_count,

            "forming": False,
        }
    )


# Add live candle
rows.append(
    {
        "start_tick":
            current_candle["start_tick"],

        "end_tick":
            current_candle["end_tick"],

        "open":
            current_candle["open"] / 100,

        "high":
            current_candle["high"] / 100,

        "low":
            current_candle["low"] / 100,

        "close":
            current_candle["close"] / 100,

        "volume":
            current_candle["volume"],

        "trade_count":
            current_candle["trade_count"],

        "forming":
            True,
    }
)


df = pd.DataFrame(rows)


# Only show recent candles
df_chart = df.tail(100)


# --------------------------------------------------
# Candlestick chart
# --------------------------------------------------

fig = go.Figure(
    data=[
        go.Candlestick(
            x=df_chart["start_tick"],

            open=df_chart["open"],
            high=df_chart["high"],
            low=df_chart["low"],
            close=df_chart["close"],

            name="Price",
        )
    ]
)


fig.update_layout(
    title="Simulated Market",

    xaxis_title="Tick",
    yaxis_title="Price ($)",

    xaxis_rangeslider_visible=False,

    height=600,
)


st.plotly_chart(
    fig,
    use_container_width=True,
)


# --------------------------------------------------
# Bottom section
# --------------------------------------------------

left, right = st.columns(2)


with left:

    st.subheader("Market Activity")

    st.write(
        "Total trades:",
        len(market.orderbook.trades),
    )

    st.write(
        "Completed candles:",
        len(market.candles),
    )

    st.write(
        "Current candle trades:",
        len(market.current_candle_trades),
    )


with right:

    st.subheader("Recent Trades")

    if market.orderbook.trades:

        trades_df = pd.DataFrame(
            market.orderbook.trades[-10:]
        )

        trades_df["price"] = (
            trades_df["price"] / 100
        )

        st.dataframe(
            trades_df,
            use_container_width=True,
        )

    else:

        st.write(
            "No trades yet."
        )