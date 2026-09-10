import numpy as np

from statsmodels.tsa.ar_model import AutoReg


class AutoRegForecaster:

    def __init__(
        self,
        lookback=20,
        horizon=1,
        lags=20,
        minimum_training_candles=60,
    ):
        self.lookback = lookback
        self.horizon = horizon
        self.lags = lags

        self.minimum_training_candles = max(
            minimum_training_candles,
            2 * self.lags + 10,
        )

        self.models = {}
        self.is_fitted = False


    # ======================================================
    # BUILD RETURN SERIES
    # ======================================================

    def _build_series(
        self,
        candles,
    ):
        open_returns = []
        high_returns = []
        low_returns = []
        close_returns = []

        for i in range(
            1,
            len(candles),
        ):
            previous_close = (
                candles[i - 1].close
            )

            candle = candles[i]

            if previous_close <= 0:
                continue

            open_returns.append(
                (
                    candle.open
                    - previous_close
                )
                / previous_close
            )

            high_returns.append(
                (
                    candle.high
                    - previous_close
                )
                / previous_close
            )

            low_returns.append(
                (
                    candle.low
                    - previous_close
                )
                / previous_close
            )

            close_returns.append(
                (
                    candle.close
                    - previous_close
                )
                / previous_close
            )

        return {
            "open": np.asarray(
                open_returns,
                dtype=float,
            ),

            "high": np.asarray(
                high_returns,
                dtype=float,
            ),

            "low": np.asarray(
                low_returns,
                dtype=float,
            ),

            "close": np.asarray(
                close_returns,
                dtype=float,
            ),
        }


    # ======================================================
    # FIT
    # ======================================================

    def fit(
        self,
        candles,
    ):
        self.models = {}
        self.is_fitted = False
        
        if (
            len(candles)
            < self.minimum_training_candles
        ):
            return False

        series = self._build_series(
            candles
        )

        for name, values in series.items():

            if len(values) <= self.lags:
                return False

            try:

                model = AutoReg(
                    values,
                    lags=self.lags,
                    trend="ct",
                )

                self.models[name] = (
                    model.fit()
                )

            except ValueError:

                self.models = {}
                self.is_fitted = False

                return False

        self.is_fitted = True

        return True


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

        if not candles:
            return []

        forecasts = {}

        for name, model in self.models.items():

            nobs = model.nobs

            forecasts[name] = np.asarray(
                model.predict(
                    start=nobs,
                    end=nobs + steps - 1,
                    dynamic=False,
                ),
                dtype=float,
            )


        previous_close = (
            candles[-1].close
        )

        predicted_candles = []


        for i in range(steps):

            open_return = (
                forecasts["open"][i]
            )

            high_return = (
                forecasts["high"][i]
            )

            low_return = (
                forecasts["low"][i]
            )

            close_return = (
                forecasts["close"][i]
            )


            predicted_open = round(
                previous_close
                * (1 + open_return)
            )

            predicted_high = round(
                previous_close
                * (1 + high_return)
            )

            predicted_low = round(
                previous_close
                * (1 + low_return)
            )

            predicted_close = round(
                previous_close
                * (1 + close_return)
            )


            # ----------------------------------------------
            # KEEP PRICE POSITIVE
            # ----------------------------------------------

            predicted_open = max(
                predicted_open,
                1,
            )

            predicted_close = max(
                predicted_close,
                1,
            )


            # ----------------------------------------------
            # ENFORCE VALID OHLC
            # ----------------------------------------------

            predicted_high = max(
                predicted_high,
                predicted_open,
                predicted_close,
            )

            predicted_low = max(
                min(
                    predicted_low,
                    predicted_open,
                    predicted_close,
                ),
                1,
            )


            predicted_candles.append(
                {
                    "open":
                        predicted_open,

                    "high":
                        predicted_high,

                    "low":
                        predicted_low,

                    "close":
                        predicted_close,
                }
            )


            # The next forecast is anchored
            # to the previous predicted close.
            previous_close = (
                predicted_close
            )


        return predicted_candles