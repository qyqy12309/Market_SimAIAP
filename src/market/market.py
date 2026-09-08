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

    def submit_order(
        self,
        trader_id,
        side,
        price,
        quantity,
    ):
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

    def next_tick(self):
        self.tick += 1

        if self.tick % self.ticks_per_candle == 0:
            self._close_candle()

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