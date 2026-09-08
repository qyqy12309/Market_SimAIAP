from collections import defaultdict, deque

from .order import Order, Side


class OrderBook:
    def __init__(self):
        # price -> queue of resting orders
        self.bids = defaultdict(deque)
        self.asks = defaultdict(deque)

        self.trades = []

    def add_order(self, order: Order):
        if order.side == Side.BUY:
            self._process_buy(order)
        else:
            self._process_sell(order)

    def _process_buy(self, order: Order):
        remaining = order.quantity

        for ask_price in sorted(self.asks.keys()):
            if ask_price > order.price:
                break

            queue = self.asks[ask_price]

            while queue and remaining > 0:
                resting_order = queue[0]

                trade_quantity = min(
                    remaining,
                    resting_order.quantity,
                )

                self._record_trade(
                    price=ask_price,
                    quantity=trade_quantity,
                    aggressor=Side.BUY,

                    maker_order_id=resting_order.order_id,
                    taker_order_id=order.order_id,

                    maker_trader_id=resting_order.trader_id,
                    taker_trader_id=order.trader_id,
                )

                remaining -= trade_quantity
                resting_order.quantity -= trade_quantity

                if resting_order.quantity == 0:
                    queue.popleft()

            if not queue:
                del self.asks[ask_price]

            if remaining == 0:
                break

        if remaining > 0:
            resting_order = Order(
                order_id=order.order_id,
                trader_id=order.trader_id,
                side=order.side,
                price=order.price,
                quantity=remaining,
                timestamp=order.timestamp,
            )

            self.bids[order.price].append(resting_order)

    def _process_sell(self, order: Order):
        remaining = order.quantity

        for bid_price in sorted(self.bids.keys(), reverse=True):
            if bid_price < order.price:
                break

            queue = self.bids[bid_price]

            while queue and remaining > 0:
                resting_order = queue[0]

                trade_quantity = min(
                    remaining,
                    resting_order.quantity,
                )

                self._record_trade(
                    price=bid_price,
                    quantity=trade_quantity,
                    aggressor=Side.SELL,

                    maker_order_id=resting_order.order_id,
                    taker_order_id=order.order_id,

                    maker_trader_id=resting_order.trader_id,
                    taker_trader_id=order.trader_id,
                )

                remaining -= trade_quantity
                resting_order.quantity -= trade_quantity

                if resting_order.quantity == 0:
                    queue.popleft()

            if not queue:
                del self.bids[bid_price]

            if remaining == 0:
                break

        if remaining > 0:
            resting_order = Order(
                order_id=order.order_id,
                trader_id=order.trader_id,
                side=order.side,
                price=order.price,
                quantity=remaining,
                timestamp=order.timestamp,
            )

            self.asks[order.price].append(resting_order)

    def cancel_order(self, order_id: int):
        """
        Cancel a resting order completely.

        Returns True if the order was found and cancelled.
        Returns False if the order does not exist.
        """

        for book in (self.bids, self.asks):
            for price in list(book.keys()):
                queue = book[price]

                for order in list(queue):
                    if order.order_id == order_id:
                        queue.remove(order)

                        if not queue:
                            del book[price]

                        return True

        return False

    def reduce_order(self, order_id: int, new_quantity: int):
        """
        Reduce the remaining quantity of a resting order.

        The new quantity must be smaller than the current quantity
        and greater than zero.

        Returns True if successful.
        Returns False otherwise.
        """

        if new_quantity <= 0:
            return False

        for book in (self.bids, self.asks):
            for price in book:
                queue = book[price]

                for order in queue:
                    if order.order_id == order_id:

                        if new_quantity >= order.quantity:
                            return False

                        order.quantity = new_quantity
                        return True

        return False

    def _record_trade(
        self,
        price: int,
        quantity: int,
        aggressor: Side,
        maker_order_id: int,
        taker_order_id: int,
        maker_trader_id: int | None,
        taker_trader_id: int | None,
    ):
        if aggressor == Side.BUY:
            buyer_trader_id = taker_trader_id
            seller_trader_id = maker_trader_id

        else:
            buyer_trader_id = maker_trader_id
            seller_trader_id = taker_trader_id

        self.trades.append(
            {
                "price": price,
                "quantity": quantity,

                "aggressor": aggressor.value,

                "maker_order_id": maker_order_id,
                "taker_order_id": taker_order_id,

                "maker_trader_id": maker_trader_id,
                "taker_trader_id": taker_trader_id,

                "buyer_trader_id": buyer_trader_id,
                "seller_trader_id": seller_trader_id,
            }
        )

    def best_bid(self):
        if not self.bids:
            return None

        return max(self.bids.keys())

    def best_ask(self):
        if not self.asks:
            return None

        return min(self.asks.keys())

    def spread(self):
        bid = self.best_bid()
        ask = self.best_ask()

        if bid is None or ask is None:
            return None

        return ask - bid

    def display(self):
        print("\nORDER BOOK")

        print("\nASKS")
        for price in sorted(self.asks.keys()):
            total_quantity = sum(
                order.quantity for order in self.asks[price]
            )

            print(
                f"${price / 100:.2f} -> "
                f"{total_quantity} shares "
                f"({len(self.asks[price])} orders)"
            )

        print("\nBIDS")
        for price in sorted(self.bids.keys(), reverse=True):
            total_quantity = sum(
                order.quantity for order in self.bids[price]
            )

            print(
                f"${price / 100:.2f} -> "
                f"{total_quantity} shares "
                f"({len(self.bids[price])} orders)"
            )

        print()