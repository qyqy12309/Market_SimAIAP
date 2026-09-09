import random

from .order import Side


class NoiseTrader:

    def __init__(
        self,
        trader_id,
        participation_rate=0.0005,
        max_price_offset=0.01,
        max_quantity=10,
    ):
        self.trader_id = trader_id

        self.participation_rate = (
            participation_rate
        )

        self.max_price_offset = (
            max_price_offset
        )

        self.max_quantity = (
            max_quantity
        )


    def act(
        self,
        market,
        rng: random.Random,
        regime_config=None,
    ):

        # ==============================================
        # PARTICIPATION
        # ==============================================

        effective_participation_rate = (
            self.participation_rate
        )

        if regime_config is not None:

            effective_participation_rate *= (
                regime_config
                .participation_multiplier
            )

        effective_participation_rate = min(
            effective_participation_rate,
            1.0,
        )

        if (
            rng.random()
            >= effective_participation_rate
        ):
            return


        # ==============================================
        # BUY / SELL BIAS
        # ==============================================

        buy_probability = 0.50

        if regime_config is not None:

            buy_probability = (
                regime_config.buy_probability
            )


        if rng.random() < buy_probability:

            side = Side.BUY

        else:

            side = Side.SELL


        # ==============================================
        # PRICE OFFSET
        # ==============================================

        effective_price_offset = (
            self.max_price_offset
        )

        if regime_config is not None:

            effective_price_offset *= (
                regime_config
                .price_offset_multiplier
            )


        offset = rng.uniform(
            -effective_price_offset,
            effective_price_offset,
        )


        price = round(
            market.last_price
            * (1 + offset)
        )

        price = max(
            price,
            1,
        )


        # ==============================================
        # ORDER SIZE
        # ==============================================

        quantity = rng.randint(
            1,
            self.max_quantity,
        )


        if regime_config is not None:

            quantity = round(
                quantity
                * regime_config.size_multiplier
            )


        quantity = max(
            quantity,
            1,
        )


        # ==============================================
        # SUBMIT ORDER
        # ==============================================

        market.submit_order(
            trader_id=self.trader_id,
            side=side,
            price=price,
            quantity=quantity,
            trader_type="noise",
        )
class MomentumTrader:
    def __init__(
        self,
        trader_id,
        lookback=20,
        threshold_cents=5,
        quantity=5,
        participation_rate=0.1,
        price_offset_cents=0,
    ):
        self.trader_id = trader_id
        self.lookback = lookback
        self.threshold_cents = threshold_cents
        self.quantity = quantity
        self.participation_rate = participation_rate
        self.price_offset_cents = price_offset_cents

    def act(
        self,
        market,
        rng: random.Random,
    ):
        # Not enough history yet
        if len(market.snapshots) < self.lookback:
            return

        # Optional participation filter
        if rng.random() >= self.participation_rate:
            return

        current_price = market.last_price

        past_snapshot = market.snapshots[
            -self.lookback
        ]

        past_price = past_snapshot.last_price

        momentum = (
            current_price
            - past_price
        )

        # ---------------------------------------------
        # UPWARD MOMENTUM -> BUY
        # ---------------------------------------------

        if momentum >= self.threshold_cents:

            side = Side.BUY

            price = (
                current_price
                + self.price_offset_cents
            )

        # ---------------------------------------------
        # DOWNWARD MOMENTUM -> SELL
        # ---------------------------------------------

        elif momentum <= -self.threshold_cents:

            side = Side.SELL

            price = (
                current_price
                - self.price_offset_cents
            )

        else:
            return

        price = max(
            price,
            1,
        )

        market.submit_order(
            trader_id=self.trader_id,
            side=side,
            price=price,
            quantity=self.quantity,
            trader_type="momentum",
        )

class MeanReversionTrader:
    def __init__(
        self,
        trader_id,
        lookback=20,
        threshold_cents=5,
        quantity=5,
        participation_rate=0.1,
    ):
        self.trader_id = trader_id
        self.lookback = lookback
        self.threshold_cents = threshold_cents
        self.quantity = quantity
        self.participation_rate = participation_rate

    def act(
        self,
        market,
        rng: random.Random,
    ):
        if len(market.snapshots) < self.lookback:
            return

        if rng.random() >= self.participation_rate:
            return

        current_price = market.last_price

        past_price = (
            market.snapshots[
                -self.lookback
            ].last_price
        )

        move = (
            current_price
            - past_price
        )

        # Price rose strongly -> sell
        if move >= self.threshold_cents:
            side = Side.SELL
            price = current_price

        # Price fell strongly -> buy
        elif move <= -self.threshold_cents:
            side = Side.BUY
            price = current_price

        else:
            return

        market.submit_order(
            trader_id=self.trader_id,
            side=side,
            price=price,
            quantity=self.quantity,
            trader_type="mean_reversion",
        )

class LiquidityTaker:
    def __init__(
        self,
        trader_id,
        participation_rate=0.05,
        imbalance_threshold=0.4,
        max_spread_cents=5,
        quantity=5,
    ):
        self.trader_id = trader_id
        self.participation_rate = participation_rate
        self.imbalance_threshold = imbalance_threshold
        self.max_spread_cents = max_spread_cents
        self.quantity = quantity

    def act(
        self,
        market,
        rng: random.Random,
    ):
        if rng.random() >= self.participation_rate:
            return

        best_bid = market.orderbook.best_bid()
        best_ask = market.orderbook.best_ask()

        if best_bid is None or best_ask is None:
            return

        spread = best_ask - best_bid

        if spread > self.max_spread_cents:
            return

        bid_depth = sum(
            order.quantity
            for order in market.orderbook.bids[
                best_bid
            ]
        )

        ask_depth = sum(
            order.quantity
            for order in market.orderbook.asks[
                best_ask
            ]
        )

        total_depth = (
            bid_depth
            + ask_depth
        )

        if total_depth == 0:
            return

        imbalance = (
            bid_depth
            - ask_depth
        ) / total_depth

        # Strong bid-side pressure -> aggressive buy
        if imbalance >= self.imbalance_threshold:

            side = Side.BUY

            # Cross the spread
            price = best_ask

        # Strong ask-side pressure -> aggressive sell
        elif imbalance <= -self.imbalance_threshold:

            side = Side.SELL

            # Cross the spread
            price = best_bid

        else:
            return

        market.submit_order(
            trader_id=self.trader_id,
            side=side,
            price=price,
            quantity=self.quantity,
            trader_type="liquidity_taker",
        )
        
class MarketMaker:
    def __init__(
        self,
        trader_id,
        spread_cents=4,
        quantity=10,
        refresh_rate=1.0,
        inventory_skew=0.05,
        initial_cash=1_000_000_00,
    ):
        self.trader_id = trader_id

        self.spread_cents = spread_cents
        self.quantity = quantity
        self.refresh_rate = refresh_rate
        self.inventory_skew = inventory_skew

        self.inventory = 0

        # Stored in cents
        self.initial_cash = initial_cash
        self.cash = initial_cash

        self.bid_order_id = None
        self.ask_order_id = None

        self.last_trade_index = 0

    def update_inventory(
        self,
        trades,
    ):
        new_trades = trades[
            self.last_trade_index:
        ]

        for trade in new_trades:

            quantity = trade["quantity"]
            price = trade["price"]

            trade_value = (
                price * quantity
            )

            # ---------------------------------------------
            # MARKET MAKER BOUGHT
            # ---------------------------------------------

            if (
                trade["buyer_trader_id"]
                == self.trader_id
            ):
                self.inventory += quantity
                self.cash -= trade_value

            # ---------------------------------------------
            # MARKET MAKER SOLD
            # ---------------------------------------------

            if (
                trade["seller_trader_id"]
                == self.trader_id
            ):
                self.inventory -= quantity
                self.cash += trade_value

        self.last_trade_index = len(
            trades
        )

    def act(
        self,
        market,
        rng: random.Random,
    ):
        if rng.random() >= self.refresh_rate:
            return

        # Cancel previous quotes
        if self.bid_order_id is not None:
            market.orderbook.cancel_order(
                self.bid_order_id
            )

        if self.ask_order_id is not None:
            market.orderbook.cancel_order(
                self.ask_order_id
            )

        # ---------------------------------------------
        # INVENTORY-AWARE REFERENCE PRICE
        # ---------------------------------------------

        inventory_adjustment = round(
            self.inventory
            * self.inventory_skew
        )

        reference_price = (
            market.last_price
            - inventory_adjustment
        )

        half_spread = max(
            self.spread_cents // 2,
            1,
        )

        bid_price = max(
            reference_price
            - half_spread,
            1,
        )

        ask_price = max(
            reference_price
            + half_spread,
            bid_price + 1,
        )

        # ---------------------------------------------
        # SUBMIT FRESH QUOTES
        # ---------------------------------------------

        self.bid_order_id = (
            market.submit_order(
                trader_id=self.trader_id,
                side=Side.BUY,
                price=bid_price,
                quantity=self.quantity,
                trader_type="market_maker",
            )
        )

        self.ask_order_id = (
            market.submit_order(
                trader_id=self.trader_id,
                side=Side.SELL,
                price=ask_price,
                quantity=self.quantity,
                trader_type="market_maker",
            )
        )
    def equity(
        self,
        mark_price,
    ):
        return (
            self.cash
            + self.inventory
            * mark_price
        )


    def pnl(
        self,
        mark_price,
    ):
        return (
            self.equity(mark_price)
            - self.initial_cash
        )
