from .order import Order
from .orderbook import OrderBook
from .candle import Candle
from .snapshot import MarketSnapshot

class Market:
    def __init__(
        self,
        initial_price=10000,
        ticks_per_candle=10,
    ):
        self.orderbook = OrderBook()

        self.tick = 0
        self.ticks_per_candle = ticks_per_candle

        self.last_price = initial_price

        self.current_candle_trades = []
        self.candles = []
        self.snapshots = []

        self.next_order_id = 1

        self.orders_submitted = 0
        self.stochastic_cancellations = 0
        self.forced_expirations = 0
        self.orders_by_type = {
            "noise": 0,
            "momentum": 0,
            "mean_reversion": 0,
            "liquidity_taker": 0,
            "market_maker": 0,
        }

    def submit_order(
        self,
        trader_id,
        side,
        price,
        quantity,
        trader_type="unknown",
    ):
        self.orders_submitted += 1

        if trader_type not in self.orders_by_type:
            self.orders_by_type[trader_type] = 0

        self.orders_by_type[trader_type] += 1

        order = Order(
            order_id=self.next_order_id,
            trader_id=trader_id,
            side=side,
            price=price,
            quantity=quantity,
            timestamp=self.tick,
        )

        self.next_order_id += 1

        before_trade_count = len(
            self.orderbook.trades
        )

        self.orderbook.add_order(order)

        new_trades = self.orderbook.trades[
            before_trade_count:
        ]

        for trade in new_trades:
            trade["tick"] = self.tick

            self.last_price = trade["price"]

            self.current_candle_trades.append(
                trade
            )

        return order.order_id
    
    def cancel_stale_orders(
        self,
        rng,
        num_noise_traders,
        cancel_probability=0.02,
        max_order_age=200,
    ):
        stochastic_ids = []
        expired_ids = []

        # ---------------------------------------------
        # CHECK BIDS
        # ---------------------------------------------

        for queue in self.orderbook.bids.values():

            for order in queue:

                # Ignore market-maker orders
                if (
                    order.trader_id is None
                    or order.trader_id >= num_noise_traders
                ):
                    continue

                age = (
                    self.tick
                    - order.timestamp
                )

                if age >= max_order_age:
                    expired_ids.append(
                        order.order_id
                    )

                elif (
                    rng.random()
                    < cancel_probability
                ):
                    stochastic_ids.append(
                        order.order_id
                    )

        # ---------------------------------------------
        # CHECK ASKS
        # ---------------------------------------------

        for queue in self.orderbook.asks.values():

            for order in queue:

                if (
                    order.trader_id is None
                    or order.trader_id >= num_noise_traders
                ):
                    continue

                age = (
                    self.tick
                    - order.timestamp
                )

                if age >= max_order_age:
                    expired_ids.append(
                        order.order_id
                    )

                elif (
                    rng.random()
                    < cancel_probability
                ):
                    stochastic_ids.append(
                        order.order_id
                    )

        # ---------------------------------------------
        # APPLY STOCHASTIC CANCELLATIONS
        # ---------------------------------------------

        for order_id in stochastic_ids:

            cancelled = (
                self.orderbook.cancel_order(
                    order_id
                )
            )

            if cancelled:
                self.stochastic_cancellations += 1

        # ---------------------------------------------
        # APPLY FORCED EXPIRATIONS
        # ---------------------------------------------

        for order_id in expired_ids:

            cancelled = (
                self.orderbook.cancel_order(
                    order_id
                )
            )

            if cancelled:
                self.forced_expirations += 1

    def next_tick(self):
        self.tick += 1

        if self.tick % self.ticks_per_candle == 0:
            self._close_candle()

        self._record_snapshot()

    def _close_candle(self):

        start_tick = (
            self.tick
            - self.ticks_per_candle
        )

        end_tick = self.tick

        # No trades occurred during this candle.
        if not self.current_candle_trades:

            candle = Candle(
                start_tick=start_tick,
                end_tick=end_tick,

                open=self.last_price,
                high=self.last_price,
                low=self.last_price,
                close=self.last_price,

                volume=0,
                trade_count=0,
            )

            self.candles.append(candle)

            return

        prices = [
            trade["price"]
            for trade
            in self.current_candle_trades
        ]

        volume = sum(
            trade["quantity"]
            for trade
            in self.current_candle_trades
        )

        candle = Candle(
            start_tick=start_tick,
            end_tick=end_tick,

            open=prices[0],
            high=max(prices),
            low=min(prices),
            close=prices[-1],

            volume=volume,

            trade_count=len(
                self.current_candle_trades
            ),
        )

        self.candles.append(candle)

        self.current_candle_trades = []

    def _record_snapshot(self):
        best_bid = self.orderbook.best_bid()
        best_ask = self.orderbook.best_ask()

        if best_bid is not None:
            bid_depth = sum(
                order.quantity
                for order in self.orderbook.bids[best_bid]
            )
        else:
            bid_depth = 0

        if best_ask is not None:
            ask_depth = sum(
                order.quantity
                for order in self.orderbook.asks[best_ask]
            )
        else:
            ask_depth = 0

        if best_bid is not None and best_ask is not None:
            spread = best_ask - best_bid
            mid_price = (best_bid + best_ask) / 2

            total_depth = bid_depth + ask_depth

            if total_depth > 0:
                imbalance = (
                    bid_depth - ask_depth
                ) / total_depth
            else:
                imbalance = None
        else:
            spread = None
            mid_price = None
            imbalance = None

        snapshot = MarketSnapshot(
            tick=self.tick,
            last_price=self.last_price,
            best_bid=best_bid,
            best_ask=best_ask,
            spread=spread,
            mid_price=mid_price,
            bid_depth=bid_depth,
            ask_depth=ask_depth,
            imbalance=imbalance,
        )

        self.snapshots.append(snapshot)

    def resting_order_count(self):
        bid_orders = sum(
            len(queue)
            for queue
            in self.orderbook.bids.values()
        )

        ask_orders = sum(
            len(queue)
            for queue
            in self.orderbook.asks.values()
        )

        return (
            bid_orders
            + ask_orders
        )
    def get_statistics(self):
        valid_snapshots = [
            snapshot
            for snapshot in self.snapshots
            if (
                snapshot.spread is not None
                and snapshot.mid_price is not None
            )
        ]

        if not valid_snapshots:
            return {
                "average_spread": None,
                "average_imbalance": None,
                "trade_rate": 0.0,
                "total_volume": 0,
                "realized_volatility": 0.0,
            }

        # ---------------------------------------------
        # AVERAGE SPREAD
        # ---------------------------------------------

        average_spread = sum(
            snapshot.spread
            for snapshot in valid_snapshots
        ) / len(valid_snapshots)

        # ---------------------------------------------
        # AVERAGE ABSOLUTE IMBALANCE
        # ---------------------------------------------

        imbalances = [
            snapshot.imbalance
            for snapshot in valid_snapshots
            if snapshot.imbalance is not None
        ]

        average_imbalance = (
            sum(abs(x) for x in imbalances)
            / len(imbalances)
            if imbalances
            else None
        )

        # ---------------------------------------------
        # TRADE RATE
        # ---------------------------------------------

        trade_rate = (
            len(self.orderbook.trades)
            / self.tick
            if self.tick > 0
            else 0.0
        )

        # ---------------------------------------------
        # TOTAL VOLUME
        # ---------------------------------------------

        total_volume = sum(
            trade["quantity"]
            for trade in self.orderbook.trades
        )

        # ---------------------------------------------
        # REALIZED VOLATILITY
        # ---------------------------------------------

        prices = [
            snapshot.mid_price
            for snapshot in valid_snapshots
        ]

        returns = []

        for i in range(
            1,
            len(prices),
        ):
            previous_price = prices[i - 1]
            current_price = prices[i]

            if previous_price > 0:
                returns.append(
                    (
                        current_price
                        - previous_price
                    )
                    / previous_price
                )

        if returns:
            mean_return = (
                sum(returns)
                / len(returns)
            )

            variance = (
                sum(
                    (
                        r
                        - mean_return
                    ) ** 2
                    for r in returns
                )
                / len(returns)
            )

            realized_volatility = (
                variance ** 0.5
            )

        else:
            realized_volatility = 0.0

        return {
            "average_spread":
                average_spread,

            "average_imbalance":
                average_imbalance,

            "trade_rate":
                trade_rate,

            "total_volume":
                total_volume,

            "realized_volatility":
                realized_volatility,
        }