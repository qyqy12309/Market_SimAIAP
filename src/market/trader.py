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

        self.participation_rate = participation_rate
        self.max_price_offset = max_price_offset
        self.max_quantity = max_quantity

    def act(
        self,
        market,
        rng: random.Random,
    ):
        # Decide whether this trader participates this tick
        if rng.random() >= self.participation_rate:
            return

        # Randomly choose buy or sell
        side = rng.choice(
            [
                Side.BUY,
                Side.SELL,
            ]
        )

        # Price somewhere around the last traded price
        offset = rng.uniform(
            -self.max_price_offset,
            self.max_price_offset,
        )

        price = round(
            market.last_price * (1 + offset)
        )

        # Prevent impossible/non-positive price
        price = max(price, 1)

        quantity = rng.randint(
            1,
            self.max_quantity,
        )

        market.submit_order(
        trader_id=self.trader_id,
        side=side,
        price=price,
        quantity=quantity,
    )
        
class MarketMaker:
    def __init__(
        self,
        trader_id,
        spread_cents=4,
        quantity=10,
        refresh_rate=1.0,
        inventory_skew=0.05,
    ):
        self.trader_id = trader_id

        self.spread_cents = spread_cents
        self.quantity = quantity
        self.refresh_rate = refresh_rate

        # Price adjustment in cents per share of inventory
        self.inventory_skew = inventory_skew

        self.inventory = 0

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

            if (
                trade["buyer_trader_id"]
                == self.trader_id
            ):
                self.inventory += quantity

            if (
                trade["seller_trader_id"]
                == self.trader_id
            ):
                self.inventory -= quantity

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
            )
        )

        self.ask_order_id = (
            market.submit_order(
                trader_id=self.trader_id,
                side=Side.SELL,
                price=ask_price,
                quantity=self.quantity,
            )
        )