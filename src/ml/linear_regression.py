import numpy as np

from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error
from types import SimpleNamespace


class LinearRegressionForecaster:

    def __init__(
        self,
        lookback=20,
        horizon=3,
    ):
        self.lookback = lookback
        self.horizon = horizon

        self.model = LinearRegression()

        self.is_fitted = False


    # ======================================================
    # FEATURE ENGINEERING
    # ======================================================

    def _candle_features(
        self,
        candle,
    ):
        open_price = candle.open
        high_price = candle.high
        low_price = candle.low
        close_price = candle.close

        if open_price <= 0:
            return [
                0.0,
                0.0,
                0.0,
                candle.volume,
                candle.trade_count,
            ]

        candle_return = (
            close_price
            - open_price
        ) / open_price

        candle_range = (
            high_price
            - low_price
        ) / open_price

        candle_body = (
            close_price
            - open_price
        ) / open_price

        return [
            candle_return,
            candle_range,
            candle_body,
            candle.volume,
            candle.trade_count,
        ]


    def _build_feature_vector(
        self,
        candles,
    ):
        features = []

        for candle in candles:
            features.extend(
                self._candle_features(
                    candle
                )
            )

        return features


    # ======================================================
    # DATASET
    # ======================================================

    def build_dataset(
        self,
        candles,
    ):
        X = []
        y = []

        required = (
            self.lookback
            + self.horizon
        )

        if len(candles) < required:
            return (
                np.empty((0, 0)),
                np.empty((0, 0)),
            )

        for i in range(
            self.lookback,
            len(candles)
            - self.horizon
            + 1,
        ):
            history = candles[
                i - self.lookback:i
            ]

            future = candles[
                i:i + self.horizon
            ]

            feature_vector = (
                self._build_feature_vector(
                    history
                )
            )

            anchor_price = (
                history[-1].close
            )

            target = []

            for candle in future:
                target.extend(
                    [
                        (
                            candle.open
                            - anchor_price
                        ) / anchor_price,

                        (
                            candle.high
                            - anchor_price
                        ) / anchor_price,

                        (
                            candle.low
                            - anchor_price
                        ) / anchor_price,

                        (
                            candle.close
                            - anchor_price
                        ) / anchor_price,
                    ]
                )

            X.append(feature_vector)
            y.append(target)

        return (
            np.asarray(
                X,
                dtype=float,
            ),
            np.asarray(
                y,
                dtype=float,
            ),
        )


    # ======================================================
    # FIT
    # ======================================================

    def fit(
        self,
        candles,
    ):
        X, y = self.build_dataset(
            candles
        )

        if len(X) == 0:
            return False

        self.model.fit(
            X,
            y,
        )

        self.is_fitted = True

        return True


    # ======================================================
    # PREDICT
    # ======================================================

    def predict(
        self,
        candles,
    ):
        if not self.is_fitted:
            return []

        if len(candles) < self.lookback:
            return []

        history = candles[
            -self.lookback:
        ]

        X = np.asarray(
            [
                self._build_feature_vector(
                    history
                )
            ],
            dtype=float,
        )

        prediction = (
            self.model.predict(X)[0]
        )

        anchor_price = (
            history[-1].close
        )

        predicted_candles = []

        for i in range(
            self.horizon
        ):
            start = i * 4

            predicted_open = round(
                anchor_price
                * (1 + prediction[start])
            )

            predicted_high = round(
                anchor_price
                * (1 + prediction[start + 1])
            )

            predicted_low = round(
                anchor_price
                * (1 + prediction[start + 2])
            )

            predicted_close = round(
                anchor_price
                * (1 + prediction[start + 3])
            )

            # Keep OHLC structurally valid
            predicted_high = max(
                predicted_high,
                predicted_open,
                predicted_close,
            )

            predicted_low = min(
                predicted_low,
                predicted_open,
                predicted_close,
            )

            predicted_candles.append(
                {
                    "open": predicted_open,
                    "high": predicted_high,
                    "low": predicted_low,
                    "close": predicted_close,
                }
            )

        return predicted_candles


    # ======================================================
    # RECURSIVE FORECAST
    # ======================================================

    def predict_recursive(
        self,
        candles,
        steps=30,
    ):
        if not self.is_fitted:
            return []

        if len(candles) < self.lookback:
            return []

        working_history = list(
            candles
        )

        predictions = []

        for _ in range(steps):

            next_predictions = (
                self.predict(
                    working_history
                )
            )

            if not next_predictions:
                break

            next_candle = (
                next_predictions[0]
            )

            predictions.append(
                next_candle
            )

            recent = working_history[
                -self.lookback:
            ]

            estimated_volume = round(
                sum(
                    candle.volume
                    for candle in recent
                )
                / len(recent)
            )

            estimated_trade_count = round(
                sum(
                    candle.trade_count
                    for candle in recent
                )
                / len(recent)
            )

            synthetic_candle = (
                SimpleNamespace(
                    open=next_candle["open"],
                    high=next_candle["high"],
                    low=next_candle["low"],
                    close=next_candle["close"],
                    volume=estimated_volume,
                    trade_count=estimated_trade_count,
                )
            )

            working_history.append(
                synthetic_candle
            )

        return predictions


    # ======================================================
    # EVALUATION
    # ======================================================

    def evaluate(
        self,
        candles,
        train_fraction=0.8,
    ):
        X, y = self.build_dataset(
            candles
        )

        if len(X) < 10:
            return None

        split_index = int(
            len(X)
            * train_fraction
        )

        X_train = X[:split_index]
        y_train = y[:split_index]

        X_test = X[split_index:]
        y_test = y[split_index:]

        self.model.fit(
            X_train,
            y_train,
        )

        predictions = self.model.predict(
            X_test
        )

        model_mae = mean_absolute_error(
            y_test,
            predictions,
        )

        baseline_predictions = (
            np.zeros_like(
                y_test
            )
        )

        baseline_mae = (
            mean_absolute_error(
                y_test,
                baseline_predictions,
            )
        )

        improvement = (
            baseline_mae
            - model_mae
        )

        improvement_pct = (
            improvement
            / baseline_mae
            * 100
            if baseline_mae > 0
            else 0.0
        )

        return {
            "train_samples":
                len(X_train),

            "test_samples":
                len(X_test),

            "model_mae":
                model_mae,

            "baseline_mae":
                baseline_mae,

            "improvement":
                improvement,

            "improvement_pct":
                improvement_pct,
        }