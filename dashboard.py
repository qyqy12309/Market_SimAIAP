import time
from copy import deepcopy
from src.config import DEFAULT_CONFIG

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.simulation import Simulation
from src.ml.decision_tree import DecisionTreeForecaster
from src.ml.linear_regression import LinearRegressionForecaster
from src.ml.autoreg import AutoRegForecaster

st.set_page_config(
    page_title="Market Simulator",
    layout="wide",
)


# ==========================================================
# INITIAL STATE
# ==========================================================
if "config" not in st.session_state:
    st.session_state.config = deepcopy(
        DEFAULT_CONFIG
    )

cfg = st.session_state.config

if "simulation" not in st.session_state:
    st.session_state.simulation = Simulation(
        config=deepcopy(
            st.session_state.config
        )
    )

if "running" not in st.session_state:
    st.session_state.running = False

if "speed" not in st.session_state:
    st.session_state.speed = (
        cfg.dashboard
        .default_speed
    )

if "last_update" not in st.session_state:
    st.session_state.last_update = time.monotonic()

if "tick_budget" not in st.session_state:
    st.session_state.tick_budget = 0.0

if "forecast_model" not in st.session_state:
    st.session_state.forecast_model = cfg.forecast.default_model

if "decision_tree_forecaster" not in st.session_state:
    st.session_state.decision_tree_forecaster = (
        DecisionTreeForecaster(
            lookback=(
                cfg.decision_tree.lookback
            ),
            horizon=(
                cfg.decision_tree.horizon
            ),
            max_depth=(
                cfg.decision_tree.max_depth
            ),
            min_samples_leaf=(
                cfg.decision_tree.min_samples_leaf
            ),
        )
    )
if "active_forecast" not in st.session_state:
    st.session_state.active_forecast = None

if "linear_regression_forecaster" not in st.session_state:

    st.session_state.linear_regression_forecaster = (
        LinearRegressionForecaster(
            lookback=(
                cfg.linear_regression.lookback
            ),
            horizon=(
                cfg.linear_regression.horizon
            ),
        )
    )

if "autoreg_forecaster" not in st.session_state:

    st.session_state.autoreg_forecaster = (
        AutoRegForecaster(
            lookback= cfg.autoreg.lookback,
            horizon= cfg.autoreg.horizon,
            lags= cfg.autoreg.lags,
            minimum_training_candles= cfg.autoreg.minimum_training_candles
            ))

# ==========================================================
# HEADER
# ==========================================================

st.title("Market Simulator")


# ==========================================================
# LIVE DASHBOARD
# ==========================================================

@st.fragment(run_every="100ms")
def live_dashboard():

    simulation = st.session_state.simulation
    market = simulation.market

    # ------------------------------------------------------
    # SIMULATION TIMER
    # ------------------------------------------------------

    now = time.monotonic()

    elapsed = (
        now
        - st.session_state.last_update
    )

    st.session_state.last_update = now


    if st.session_state.running:

        st.session_state.tick_budget += (
            elapsed
            * st.session_state.speed
        )

        ticks_to_run = int(
            st.session_state.tick_budget
        )

        if ticks_to_run > 0:

            simulation.run(
                ticks_to_run
            )

            st.session_state.tick_budget -= (
                ticks_to_run
            )

    else:

        # Prevent a large jump when Play is pressed again
        st.session_state.tick_budget = 0.0


    # ------------------------------------------------------
    # CONTROLS
    # ------------------------------------------------------

    controls = st.columns(
        [1, 1, 1, 1, 2]
    )


    with controls[0]:

        if st.button(
            "▶ Play",
            use_container_width=True,
        ):
            st.session_state.running = True
            st.session_state.last_update = (
                time.monotonic()
            )


    with controls[1]:

        if st.button(
            "⏸ Pause",
            use_container_width=True,
        ):
            st.session_state.running = False


    with controls[2]:

        if st.button(
            "Step 1",
            use_container_width=True,
            disabled=st.session_state.running,
        ):
            simulation.step()


    with controls[3]:

        if st.button("Reset", use_container_width=True):

            st.session_state.running = False
            st.session_state.simulation = Simulation(config=deepcopy(st.session_state.config))
            st.session_state.tick_budget = 0.0
            st.session_state.last_update = (time.monotonic())
            st.rerun()


    with controls[4]:

        st.select_slider(
            "Simulation speed",
            options=[
                1,
                5,
                10,
                25,
                50,
            ],
            key="speed",
            format_func=lambda x: f"{x} ticks/sec",
        )


    # Refresh references after simulation update/reset
    simulation = st.session_state.simulation
    market = simulation.market
    stats = market.get_statistics()

    # ------------------------------------------------------
    # FORECAST
    # ------------------------------------------------------

    predicted_candles = []

    if (
        st.session_state.forecast_model
        == "Decision Tree"
    ):

        forecaster = (
            st.session_state.decision_tree_forecaster
        )

        minimum_candles = (
            forecaster.lookback
            + forecaster.horizon
        )

        if len(market.candles) >= minimum_candles:

            fitted = forecaster.fit(
                market.candles
            )

            if fitted:

                predicted_candles = (
                    forecaster.predict(
                        market.candles
                    )
                )

    # ------------------------------------------------------
    # STATUS
    # ------------------------------------------------------

    if st.session_state.running:
        st.success(
            f"RUNNING • "
            f"{st.session_state.speed} ticks/sec"
        )
    else:
        st.info("PAUSED")

    # ------------------------------------------------------
    # CHART HISTORY CONTROL
    # ------------------------------------------------------

    history_option = st.selectbox(
        "Chart history",
        [
            "50 candles",
            "100 candles",
            "200 candles",
            "500 candles",
            "All",
        ],
        index=1,
    )

    forecast_model = st.selectbox(
        "Forecast Model",
        [
            "None",
            "Decision Tree",
            "Linear Regression",
            "AutoReg",
        ],
        key="forecast_model",
    )
    forecast_lag = st.slider(
        "Forecast lag (candles)",

        min_value=(
            cfg.forecast
            .min_forecast_lag
        ),

        max_value=(
            cfg.forecast
            .max_forecast_lag
        ),

        value=(
            cfg.forecast
            .forecast_lag
        ),

        step=(
            cfg.forecast
            .forecast_lag_step
        ),

        disabled=(
            forecast_model
            == "None"
        ),
    )

    forecast_length = st.slider(
        "Prediction length (candles)",

        min_value=(
            cfg.forecast
            .min_forecast_length
        ),

        max_value=(
            cfg.forecast
            .max_forecast_length
        ),

        value=(
            cfg.forecast
            .forecast_length
        ),

        step=1,

        disabled=(
            forecast_model
            == "None"
        ),
    )
    # ======================================================
    # FORECAST GENERATION
    # ======================================================

    forecaster = None
    predicted_candles = []
    forecast_ticks = []

    if forecast_model == "Decision Tree":

        forecaster = (
            st.session_state.decision_tree_forecaster
        )

    elif forecast_model == "Linear Regression":

        forecaster = (
            st.session_state.linear_regression_forecaster
        )
    elif forecast_model == "AutoReg":

        forecaster = (
            st.session_state.autoreg_forecaster
        )

    if forecaster is not None:

        total_candles = len(
            market.candles
        )

        minimum_training_candles = getattr(
            forecaster,
            "minimum_training_candles",
            (
                forecaster.lookback
                + forecaster.horizon
            ),
        )

        minimum_required = (
            minimum_training_candles
            + forecast_lag
        )

        if total_candles >= minimum_required:

            forecast_origin_index = (
                total_candles
                - forecast_lag
            )

            training_candles = (
                market.candles[
                    :forecast_origin_index
                ]
            )

            fitted = forecaster.fit(
                training_candles
            )

            if fitted:

                predicted_candles = (
                    forecaster.predict_recursive(
                        training_candles,
                        steps=forecast_length,
                    )
                )

                forecast_start_tick = (
                    training_candles[-1].end_tick
                )

                forecast_ticks = [
                    forecast_start_tick
                    + (
                        i
                        * market.ticks_per_candle
                    )
                    for i in range(
                        len(predicted_candles)
                    )
                ]

                st.caption(
                    f"{forecast_model}: "
                    f"{len(predicted_candles)} "
                    f"candles predicted from "
                    f"{forecast_lag} candles ago"
                )

        else:

            st.caption(
                "Waiting for enough history..."
            )

    show_order_bars = st.checkbox(
        "Show Order Book Bars",

        value=(
            cfg.dashboard
            .show_order_bars
        ),
    )

    depth_levels_chart = st.slider(
        "Order Book Levels",

        min_value=5,
        max_value=30,

        value=(
            cfg.dashboard
            .order_book_levels
        ),

        step=1,

        disabled=(
            not show_order_bars
        ),
    )

    # ------------------------------------------------------
    # MARKET METRICS
    # ------------------------------------------------------

    best_bid = market.orderbook.best_bid()
    best_ask = market.orderbook.best_ask()

    spread = market.orderbook.spread()

    total_removed = (
        market.stochastic_cancellations
        + market.forced_expirations
    )

    cancellation_rate = (
        total_removed
        / market.orders_submitted
        if market.orders_submitted > 0
        else 0
    )
    metrics = st.columns(6)


    metrics[0].metric(
        "Tick",
        f"{market.tick:,}",
    )


    metrics[1].metric(
        "Last Price",
        f"${market.last_price / 100:.2f}",
    )


    metrics[2].metric(
        "Best Bid",
        (
            f"${best_bid / 100:.2f}"
            if best_bid is not None
            else "-"
        ),
    )


    metrics[3].metric(
        "Best Ask",
        (
            f"${best_ask / 100:.2f}"
            if best_ask is not None
            else "-"
        ),
    )


    metrics[4].metric(
        "Spread",
        (
            f"${spread / 100:.2f}"
            if spread is not None
            else "-"
        ),
    )


    metrics[5].metric(
        "Trades",
        f"{len(market.orderbook.trades):,}",
    )

    lifecycle_metrics = st.columns(4)

    lifecycle_metrics[0].metric(
        "Orders Submitted",
        f"{market.orders_submitted:,}",
    )

    lifecycle_metrics[1].metric(
        "Random Cancels",
        f"{market.stochastic_cancellations:,}",
    )

    lifecycle_metrics[2].metric(
        "Expired Orders",
        f"{market.forced_expirations:,}",
    )

    lifecycle_metrics[3].metric(
        "Resting Orders",
        f"{market.resting_order_count():,}",
    )

    stats_metrics = st.columns(5)

    stats_metrics[0].metric(
        "Avg Spread",
        (
            f"{stats['average_spread']:.2f}¢"
            if stats["average_spread"] is not None
            else "-"
        ),
    )

    stats_metrics[1].metric(
        "Avg |Imbalance|",
        (
            f"{stats['average_imbalance']:.3f}"
            if stats["average_imbalance"] is not None
            else "-"
        ),
    )

    stats_metrics[2].metric(
        "Trade Rate",
        f"{stats['trade_rate']:.3f}",
    )

    stats_metrics[3].metric(
        "Total Volume",
        f"{stats['total_volume']:,}",
    )

    stats_metrics[4].metric(
        "Realized Vol",
        f"{stats['realized_volatility']:.6f}",
    )

    st.divider()


    # ======================================================
    # BUILD CANDLE DATA
    # ======================================================

    rows = []


    for candle in market.candles:

        rows.append(
            {
                "start_tick":
                    candle.start_tick,

                "end_tick":
                    candle.end_tick,

                "open":
                    candle.open / 100,

                "high":
                    candle.high / 100,

                "low":
                    candle.low / 100,

                "close":
                    candle.close / 100,

                "volume":
                    candle.volume,

                "trade_count":
                    candle.trade_count,

                "forming":
                    False,
            }
        )


    # ------------------------------------------------------
    # CURRENT / FORMING CANDLE
    # ------------------------------------------------------

    current_trades = (
        market.current_candle_trades
    )


    candle_start = (
        market.tick
        - (
            market.tick
            % market.ticks_per_candle
        )
    )


    if current_trades:

        prices = [
            trade["price"]
            for trade
            in current_trades
        ]

        current_open = prices[0]
        current_high = max(prices)
        current_low = min(prices)
        current_close = prices[-1]

        current_volume = sum(
            trade["quantity"]
            for trade
            in current_trades
        )

        current_trade_count = len(
            current_trades
        )


    else:

        current_open = market.last_price
        current_high = market.last_price
        current_low = market.last_price
        current_close = market.last_price

        current_volume = 0
        current_trade_count = 0


    rows.append(
        {
            "start_tick":
                candle_start,

            "end_tick":
                market.tick,

            "open":
                current_open / 100,

            "high":
                current_high / 100,

            "low":
                current_low / 100,

            "close":
                current_close / 100,

            "volume":
                current_volume,

            "trade_count":
                current_trade_count,

            "forming":
                True,
        }
    )


    df = pd.DataFrame(rows)


    # ------------------------------------------------------
    # SELECT VISIBLE CHART HISTORY
    # ------------------------------------------------------

    if history_option == "All":
        df_chart = df
    else:
        history_size = int(
            history_option.split()[0]
        )

        df_chart = df.tail(
            history_size
        )

    # ======================================================
    # CANDLESTICK CHART
    # ======================================================

    fig = go.Figure()


    # ======================================================
    # FROZEN FORECAST CANDLES
    # Draw first so they remain underneath actual candles
    # ======================================================

    if predicted_candles:

        forecast_open = [
            candle["open"] / 100
            for candle in predicted_candles
        ]

        forecast_high = [
            candle["high"] / 100
            for candle in predicted_candles
        ]

        forecast_low = [
            candle["low"] / 100
            for candle in predicted_candles
        ]

        forecast_close = [
            candle["close"] / 100
            for candle in predicted_candles
        ]

        fig.add_trace(
            go.Candlestick(
                x=forecast_ticks,

                open=forecast_open,
                high=forecast_high,
                low=forecast_low,
                close=forecast_close,

                increasing=dict(
                    line=dict(
                        color="rgba(190, 190, 190, 0.90)",
                        width=2,
                    ),
                    fillcolor="rgba(150, 150, 150, 0.25)",
                ),

                decreasing=dict(
                    line=dict(
                        color="rgba(190, 190, 190, 0.90)",
                        width=2,
                    ),
                    fillcolor="rgba(150, 150, 150, 0.25)",
                ),

                name="Decision Tree Forecast",

                opacity=0.70,
            )
        )


    # ======================================================
    # ACTUAL CANDLES
    # Draw second so they overlay the gray forecast
    # ======================================================

    fig.add_trace(
        go.Candlestick(
            x=df_chart["start_tick"],

            open=df_chart["open"],
            high=df_chart["high"],
            low=df_chart["low"],
            close=df_chart["close"],

            name="Actual",
        )
    )
    # ======================================================
    # FROZEN FORECAST CANDLES
    # ======================================================

    if predicted_candles:

        forecast_open = [
            candle["open"] / 100
            for candle in predicted_candles
        ]

        forecast_high = [
            candle["high"] / 100
            for candle in predicted_candles
        ]

        forecast_low = [
            candle["low"] / 100
            for candle in predicted_candles
        ]

        forecast_close = [
            candle["close"] / 100
            for candle in predicted_candles
        ]


        fig.add_trace(
            go.Candlestick(
                x=forecast_ticks,

                open=forecast_open,
                high=forecast_high,
                low=forecast_low,
                close=forecast_close,

                increasing=dict(
                    line=dict(
                        color="rgba(190, 190, 190, 0.85)",
                        width=2,
                    ),

                    fillcolor=(
                        "rgba(150, 150, 150, 0.25)"
                    ),
                ),

                decreasing=dict(
                    line=dict(
                        color="rgba(190, 190, 190, 0.85)",
                        width=2,
                    ),

                    fillcolor=(
                        "rgba(150, 150, 150, 0.25)"
                    ),
                ),

                name="Decision Tree Forecast",

                opacity=0.70,
            )
        )

    # ======================================================
    # CHART BOUNDS
    # ======================================================

    if not df_chart.empty:

        chart_min_tick = (
            df_chart["start_tick"].min()
        )

        chart_max_tick = (
            df_chart["start_tick"].max()
        )

        chart_width = max(
            chart_max_tick
            - chart_min_tick,
            10,
        )

    else:

        chart_min_tick = 0
        chart_max_tick = market.tick
        chart_width = 100

    # ======================================================
    # ORDER BOOK DEPTH BARS
    # ======================================================

    if show_order_bars:

        # ----------------------------------------------
        # FIND VISIBLE ORDER BOOK LEVELS
        # ----------------------------------------------

        ask_prices = sorted(
            market.orderbook.asks.keys()
        )[:depth_levels_chart]

        bid_prices = sorted(
            market.orderbook.bids.keys(),
            reverse=True,
        )[:depth_levels_chart]


        ask_depths = {
            price: sum(
                order.quantity
                for order
                in market.orderbook.asks[price]
            )
            for price in ask_prices
        }

        bid_depths = {
            price: sum(
                order.quantity
                for order
                in market.orderbook.bids[price]
            )
            for price in bid_prices
        }


        # ----------------------------------------------
        # NORMALISATION
        # ----------------------------------------------

        all_depths = (
            list(ask_depths.values())
            + list(bid_depths.values())
        )

        max_depth = (
            max(all_depths)
            if all_depths
            else 1
        )


        # ----------------------------------------------
        # DETERMINE WHERE BARS START
        # ----------------------------------------------

        # Leave some empty space between candles
        # and the order-book visualization.

        bar_start = (
            chart_max_tick
            + chart_width * 0.05
        )

        max_bar_width = (
            chart_width * 0.20
        )

        # ----------------------------------------------
        # ASK BARS
        # ----------------------------------------------

        for price, quantity in ask_depths.items():

            bar_width = (
                quantity
                / max_depth
                * max_bar_width
            )

            order_count = len(
                market.orderbook.asks[price]
            )

            fig.add_trace(
                go.Scatter(
                    x=[
                        bar_start,
                        bar_start + bar_width,
                    ],

                    y=[
                        price / 100,
                        price / 100,
                    ],

                    mode="lines+text",

                    line=dict(
                        color="red",
                        width=4,
                    ),

                    text=[
                        "",
                        str(quantity),
                    ],

                    textposition="middle right",

                    customdata=[
                        [quantity, order_count],
                        [quantity, order_count],
                    ],

                    hovertemplate=(
                        "<b>ASK</b><br>"
                        "Price: $%{y:.2f}<br>"
                        "Quantity: %{customdata[0]}<br>"
                        "Orders: %{customdata[1]}"
                        "<extra></extra>"
                    ),

                    showlegend=False,
                )
            )

        # ----------------------------------------------
        # BID BARS
        # ----------------------------------------------

        for price, quantity in bid_depths.items():

            bar_width = (
                quantity
                / max_depth
                * max_bar_width
            )

            order_count = len(
                market.orderbook.bids[price]
            )

            fig.add_trace(
                go.Scatter(
                    x=[
                        bar_start,
                        bar_start + bar_width,
                    ],

                    y=[
                        price / 100,
                        price / 100,
                    ],

                    mode="lines+text",

                    line=dict(
                        color="lime",
                        width=4,
                    ),

                    text=[
                        "",
                        str(quantity),
                    ],

                    textposition="middle right",

                    customdata=[
                        [quantity, order_count],
                        [quantity, order_count],
                    ],

                    hovertemplate=(
                        "<b>BID</b><br>"
                        "Price: $%{y:.2f}<br>"
                        "Quantity: %{customdata[0]}<br>"
                        "Orders: %{customdata[1]}"
                        "<extra></extra>"
                    ),

                    showlegend=False,
                )
            )
    # ======================================================
    # DETERMINE FORECAST END
    # ======================================================
    if forecast_ticks:
        forecast_end_tick = (
            forecast_ticks[-1]
            + market.ticks_per_candle
        )

    else:

        forecast_end_tick = (
            market.tick
        )

    # ======================================================
    # DETERMINE X-AXIS END
    # ======================================================
    if show_order_bars:

        order_bar_end = (
            bar_start
            + max_bar_width
            + chart_width * 0.05
        )

        x_axis_max = max(
            order_bar_end,
            forecast_end_tick,
        )

    elif predicted_candles:

        x_axis_max = (
            forecast_end_tick
            + market.ticks_per_candle
        )

    else:

        x_axis_max = None

    # ======================================================
    # FORECAST ORIGIN MARKER
    # ======================================================

    active_forecast = (
        st.session_state.active_forecast
    )

    if active_forecast is not None:

        fig.add_annotation(
            x=active_forecast["created_at_tick"],
            y=1,
            yref="paper",

            text="Forecast made here",

            showarrow=True,
            arrowhead=2,
            arrowsize=1,
            arrowwidth=1,

            ax=0,
            ay=-35,

            xanchor="center",
            yanchor="bottom",

            opacity=0.7,
        )

    fig.update_layout(
        xaxis_title="Tick",
        yaxis_title="Price ($)",

        xaxis_rangeslider_visible=False,

        height=570,

        margin=dict(
            l=20,
            r=20,
            t=30,
            b=20,
        ),

        showlegend=False,
    )


    if (
        show_order_bars
        or predicted_candles
    ):

        fig.update_xaxes(
            range=[
                chart_min_tick,
                x_axis_max,
            ]
        )

    st.plotly_chart(
        fig,
        use_container_width=True,
        key="live_price_chart",
    )


    # ======================================================
    # BOTTOM INFORMATION
    # ======================================================

    left, middle, right = st.columns(
        [1.4, 1, 1.6]
    )


    # ------------------------------------------------------
    # ORDER BOOK LADDER
    # ------------------------------------------------------

    with left:

        st.subheader("Order Book")

        depth_levels = 8


        ask_rows = []

        for price in sorted(
            market.orderbook.asks.keys()
        )[:depth_levels]:

            queue = market.orderbook.asks[price]

            ask_rows.append(
                {
                    "Side": "ASK",
                    "Price": f"${price / 100:.2f}",
                    "Quantity": sum(
                        order.quantity
                        for order in queue
                    ),
                    "Orders": len(queue),
                }
            )


        bid_rows = []

        for price in sorted(
            market.orderbook.bids.keys(),
            reverse=True,
        )[:depth_levels]:

            queue = market.orderbook.bids[price]

            bid_rows.append(
                {
                    "Side": "BID",
                    "Price": f"${price / 100:.2f}",
                    "Quantity": sum(
                        order.quantity
                        for order in queue
                    ),
                    "Orders": len(queue),
                }
            )


        if ask_rows:

            st.caption("ASKS")

            asks_df = pd.DataFrame(
                ask_rows[::-1]
            )

            st.dataframe(
                asks_df,
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.write("No asks")


        if spread is not None:

            st.markdown(
                f"**Spread: ${spread / 100:.2f}**"
            )


        if bid_rows:

            st.caption("BIDS")

            bids_df = pd.DataFrame(
                bid_rows
            )

            st.dataframe(
                bids_df,
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.write("No bids")


    # ------------------------------------------------------
    # MARKET ACTIVITY
    # ------------------------------------------------------

    with middle:

        st.subheader("Market Activity")

        st.metric(
            "Completed Candles",
            len(market.candles),
        )

        st.metric(
            "Current Candle Trades",
            len(
                market.current_candle_trades
            ),
        )

        st.metric(
            "Total Volume",
            f"{stats['total_volume']:,}",
        )

        total_bid_depth = sum(
            order.quantity
            for queue
            in market.orderbook.bids.values()
            for order
            in queue
        )


        total_ask_depth = sum(
            order.quantity
            for queue
            in market.orderbook.asks.values()
            for order
            in queue
        )


        st.metric(
            "Bid Depth",
            f"{total_bid_depth:,}",
        )


        st.metric(
            "Ask Depth",
            f"{total_ask_depth:,}",
        )

        st.metric(
            "Cancellation Rate",
            f"{cancellation_rate:.1%}",
        )

        total_maker_pnl = sum(
            maker.pnl(market.last_price)
            for maker
            in simulation.market_makers
        )

        st.metric(
            "Total Market Maker PnL",
            f"${total_maker_pnl / 100:,.2f}",
        )


    # ------------------------------------------------------
    # TRADE TAPE
    # ------------------------------------------------------

    with right:

        st.subheader("Recent Trades")

        if market.orderbook.trades:

            trade_rows = []

            for trade in (
                market.orderbook.trades[-15:]
            ):

                trade_rows.append(
                    {
                        "Tick":
                            trade.get(
                                "tick",
                                "-"
                            ),

                        "Price":
                            f"${trade['price'] / 100:.2f}",

                        "Quantity":
                            trade["quantity"],

                        "Aggressor":
                            trade["aggressor"],

                        "Maker":
                            trade[
                                "maker_order_id"
                            ],

                        "Taker":
                            trade[
                                "taker_order_id"
                            ],
                    }
                )


            trade_df = pd.DataFrame(
                trade_rows[::-1]
            )


            st.dataframe(
                trade_df,
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.write(
                "Waiting for the first trade..."
            )
    # ======================================================
    # MARKET MAKERS
    # ======================================================

    st.divider()

    st.subheader("Market Makers")

    maker_rows = []

    for maker in simulation.market_makers:

        maker_rows.append(
            {
                "Trader ID":
                    maker.trader_id,

                "Inventory":
                    maker.inventory,

                "Cash":
                    f"${maker.cash / 100:,.2f}",

                "Equity":
                    (
                        f"${maker.equity(market.last_price) / 100:,.2f}"
                    ),

                "PnL":
                    (
                        f"${maker.pnl(market.last_price) / 100:,.2f}"
                    ),

                "Bid Order ID":
                    maker.bid_order_id,

                "Ask Order ID":
                    maker.ask_order_id,
            }
        )
    maker_df = pd.DataFrame(
        maker_rows
    )

    st.dataframe(
        maker_df,
        use_container_width=True,
        hide_index=True,
    )


            
live_dashboard()