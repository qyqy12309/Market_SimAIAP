# Adding New Forecasting Models

This guide explains how to add a new forecasting model to the Market Simulator project in a way that remains compatible with the existing dashboard, lagged forecast overlay, model selector, and evaluation workflow.

The goal is to make new models interchangeable.

A new forecaster should behave like the existing:

```text
DecisionTreeForecaster
LinearRegressionForecaster
AutoRegForecaster
```

so that the dashboard can treat every model through the same interface.

---

# 1. Design Goal

The forecasting architecture is intentionally simple:

```text
Dashboard
   ↓
Select model
   ↓
forecaster.fit(training_candles)
   ↓
forecaster.predict_recursive(
    training_candles,
    steps=forecast_length,
)
   ↓
Predicted OHLC candles
   ↓
Gray overlay against realized candles
```

A new model should therefore expose a compatible API.

At minimum:

```python
fit(candles) -> bool
```

and:

```python
predict_recursive(
    candles,
    steps,
) -> list[dict]
```

The returned forecast must look like:

```python
[
    {
        "open": 10012,
        "high": 10018,
        "low": 10007,
        "close": 10015,
    },
    ...
]
```

Prices are stored internally in integer cents.

Example:

```text
$100.15 → 10015
```

---

# 2. Existing Project Structure

Forecasting models live under:

```text
src/ml/
```

Current structure:

```text
src/
├── ml/
│   ├── __init__.py
│   ├── decision_tree.py
│   ├── linear_regression.py
│   └── autoreg.py
│
├── market/
│   ├── candle.py
│   ├── market.py
│   ├── order.py
│   ├── orderbook.py
│   ├── regime.py
│   ├── snapshot.py
│   └── trader.py
│
└── simulation.py
```

Add each new model as a separate file.

Example:

```text
src/ml/random_forest.py
src/ml/xgboost_forecaster.py
src/ml/lstm.py
src/ml/gru.py
src/ml/tcn.py
src/ml/transformer.py
```

Avoid putting multiple unrelated models into a single file.

---

# 3. Required Forecaster Interface

Every new forecasting class should preferably expose the following attributes:

```python
self.lookback
self.horizon
self.minimum_training_candles
self.is_fitted
```

Recommended constructor:

```python
class ExampleForecaster:

    def __init__(
        self,
        lookback=20,
        horizon=1,
    ):
        self.lookback = lookback
        self.horizon = horizon

        self.minimum_training_candles = max(
            60,
            self.lookback + self.horizon + 10,
        )

        self.is_fitted = False
```

The exact minimum training requirement depends on the model.

Examples:

```text
Linear Regression:
lookback + horizon

Decision Tree:
lookback + horizon

AutoReg:
enough observations to estimate lagged regressors

LSTM:
usually substantially more history

Transformer:
usually much more history
```

The dashboard can inspect:

```python
forecaster.minimum_training_candles
```

before attempting a fit.

---

# 4. Candle Input Format

The model receives a Python list of candle objects.

Each candle currently exposes:

```python
candle.open
candle.high
candle.low
candle.close
candle.volume
candle.trade_count
candle.start_tick
candle.end_tick
```

Example conceptual candle:

```python
Candle(
    start_tick=100,
    end_tick=110,
    open=10000,
    high=10015,
    low=9995,
    close=10010,
    volume=84,
    trade_count=15,
)
```

Do not assume prices are floating-point dollars.

They are integer cents.

---

# 5. Avoid Future Leakage

This is one of the most important rules in the project.

The dashboard already performs lagged forecasting.

Example:

```text
Total completed candles = 500
Forecast lag            = 30
```

The dashboard creates:

```python
forecast_origin_index = (
    total_candles
    - forecast_lag
)
```

and:

```python
training_candles = (
    market.candles[
        :forecast_origin_index
    ]
)
```

The model must therefore train **only** on `training_candles`.

It must not read:

```python
market.candles
```

directly.

It must not access future candles through global state.

It must not use realized future volume, future trade counts, future returns, or future order-book state when creating predictions.

Bad:

```python
future_volume = candles[i + 1].volume
```

when candle `i + 1` belongs to the forecast horizon.

Good:

```python
estimated_volume = np.mean(
    [
        candle.volume
        for candle in history[-lookback:]
    ]
)
```

when recursive forecasting requires a synthetic candle.

---

# 6. Preferred Forecast Target

For most models, predict normalized price changes instead of raw price levels.

A common target is return relative to an anchor close:

```python
return_value = (
    future_price
    - anchor_price
) / anchor_price
```

For example:

```python
close_return = (
    future_candle.close
    - anchor_price
) / anchor_price
```

This is generally preferable to directly predicting:

```python
10023
10024
10031
...
```

because raw price level can drift over time.

Normalized targets also make different price regimes more comparable.

---

# 7. Recommended OHLC Reconstruction

After predicting returns:

```python
predicted_open = round(
    anchor_price
    * (1 + open_return)
)

predicted_high = round(
    anchor_price
    * (1 + high_return)
)

predicted_low = round(
    anchor_price
    * (1 + low_return)
)

predicted_close = round(
    anchor_price
    * (1 + close_return)
)
```

Always enforce a valid candle afterward:

```python
predicted_open = max(
    predicted_open,
    1,
)

predicted_close = max(
    predicted_close,
    1,
)

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
```

This prevents impossible output such as:

```text
high < open
high < close
low > open
low > close
price <= 0
```

---

# 8. Recursive Forecasting

The dashboard expects multi-step forecasts.

For a model that naturally predicts only one next candle, recursively feed its own prediction back into the model.

Conceptually:

```text
Real history
    ↓
Predict t+1
    ↓
Append synthetic t+1
    ↓
Predict t+2
    ↓
Append synthetic t+2
    ↓
Predict t+3
```

This is deliberately different from using realized future candles.

A generic structure:

```python
def predict_recursive(
    self,
    candles,
    steps=30,
):
    if not self.is_fitted:
        return []

    working_history = list(
        candles
    )

    predictions = []

    for _ in range(steps):

        next_prediction = (
            self.predict_one(
                working_history
            )
        )

        if next_prediction is None:
            break

        predictions.append(
            next_prediction
        )

        synthetic_candle = (
            self._build_synthetic_candle(
                working_history,
                next_prediction,
            )
        )

        working_history.append(
            synthetic_candle
        )

    return predictions
```

---

# 9. Synthetic Candles

If the model uses volume or trade count as features, recursive prediction creates a problem:

```text
future volume is unknown
future trade_count is unknown
```

Do not use the realized values.

Estimate them from historical data instead.

Example:

```python
recent = (
    working_history[
        -self.lookback:
    ]
)

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
```

Then:

```python
from types import SimpleNamespace


synthetic_candle = SimpleNamespace(
    open=prediction["open"],
    high=prediction["high"],
    low=prediction["low"],
    close=prediction["close"],
    volume=estimated_volume,
    trade_count=estimated_trade_count,
)
```

---

# 10. Feature Engineering

Possible candle-level features include:

```text
Open return
High return
Low return
Close return
Candle range
Candle body
Upper wick
Lower wick
Volume
Trade count
```

Possible derived features:

```text
Close-to-close return
Rolling volatility
Rolling average return
Rolling volume
Rolling trade count
Price momentum
Distance from moving average
```

Possible market-microstructure features, if the data is available in the model input:

```text
Spread
Midprice
Best bid depth
Best ask depth
Order-book imbalance
Trade rate
Aggressor imbalance
```

Be careful: the current forecasting classes generally receive candle objects only.

If a future model requires snapshots or order-book data, update the architecture deliberately rather than secretly importing global simulator state from inside the forecaster.

---

# 11. Scaling

Models such as:

```text
Linear Regression
Logistic Regression
Neural Networks
LSTM
GRU
TCN
Transformer
Support Vector Regression
```

often benefit from feature scaling.

Recommended scikit-learn pattern:

```python
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge


self.model = Pipeline(
    [
        (
            "scaler",
            StandardScaler(),
        ),
        (
            "model",
            Ridge(),
        ),
    ]
)
```

For neural networks, save normalization statistics calculated only from the training window.

Do not calculate scaling statistics using future data.

---

# 12. Time-Series Train/Test Splits

Never randomly shuffle time-series samples for evaluation.

Bad:

```python
train_test_split(
    X,
    y,
    shuffle=True,
)
```

Better:

```python
split_index = int(
    len(X) * 0.8
)

X_train = X[
    :split_index
]

X_test = X[
    split_index:
]
```

Even better later:

```text
walk-forward validation
```

Example:

```text
Train 1 ──────────┐ Predict next block
Train 2 ───────────────┐ Predict next block
Train 3 ─────────────────────┐ Predict next block
```

---

# 13. Evaluation Metrics

Recommended metrics include:

```text
MAE
RMSE
Directional accuracy
Naive-baseline MAE
Naive-baseline RMSE
Improvement vs baseline
```

For return prediction:

```python
baseline_prediction = 0
```

represents:

```text
no expected price change
```

Directional accuracy can be:

```python
actual_direction = (
    actual_returns > 0
)

predicted_direction = (
    predicted_returns > 0
)

accuracy = np.mean(
    actual_direction
    == predicted_direction
)
```

A model should not be considered useful merely because its chart looks convincing.

---

# 14. Recommended File Template

Use this as a starting point for a new tabular model.

```python
import numpy as np

from types import SimpleNamespace


class ExampleForecaster:

    def __init__(
        self,
        lookback=20,
        horizon=1,
    ):
        self.lookback = lookback
        self.horizon = horizon

        self.minimum_training_candles = max(
            60,
            self.lookback
            + self.horizon
            + 10,
        )

        self.model = None

        self.is_fitted = False


    # ======================================================
    # FEATURE EXTRACTION
    # ======================================================

    def _candle_features(
        self,
        candle,
        previous_close,
    ):
        if previous_close <= 0:
            return [
                0.0,
                0.0,
                0.0,
                0.0,
                float(candle.volume),
                float(candle.trade_count),
            ]

        return [
            (
                candle.open
                - previous_close
            ) / previous_close,

            (
                candle.high
                - previous_close
            ) / previous_close,

            (
                candle.low
                - previous_close
            ) / previous_close,

            (
                candle.close
                - previous_close
            ) / previous_close,

            float(
                candle.volume
            ),

            float(
                candle.trade_count
            ),
        ]


    def _build_feature_vector(
        self,
        candles,
    ):
        features = []

        for i, candle in enumerate(
            candles
        ):
            if i == 0:
                previous_close = (
                    candle.open
                )

            else:
                previous_close = (
                    candles[
                        i - 1
                    ].close
                )

            features.extend(
                self._candle_features(
                    candle,
                    previous_close,
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

        minimum_required = (
            self.lookback
            + self.horizon
        )

        if (
            len(candles)
            < minimum_required
        ):
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
                i - self.lookback:
                i
            ]

            future = candles[
                i:
                i + self.horizon
            ]

            anchor_price = (
                history[-1].close
            )

            features = (
                self._build_feature_vector(
                    history
                )
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

            X.append(
                features
            )

            y.append(
                target
            )

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
        self.is_fitted = False

        if (
            len(candles)
            < self.minimum_training_candles
        ):
            return False

        X, y = self.build_dataset(
            candles
        )

        if len(X) == 0:
            return False

        # Replace this with model-specific fitting.
        #
        # self.model.fit(
        #     X,
        #     y,
        # )

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

        if (
            len(candles)
            < self.lookback
        ):
            return []

        history = candles[
            -self.lookback:
        ]

        anchor_price = (
            history[-1].close
        )

        # Replace with real model prediction.
        prediction = None

        if prediction is None:
            return []

        predicted_candles = []

        # Decode prediction here.

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

        if (
            len(candles)
            < self.lookback
        ):
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
                    open=next_candle[
                        "open"
                    ],

                    high=next_candle[
                        "high"
                    ],

                    low=next_candle[
                        "low"
                    ],

                    close=next_candle[
                        "close"
                    ],

                    volume=(
                        estimated_volume
                    ),

                    trade_count=(
                        estimated_trade_count
                    ),
                )
            )

            working_history.append(
                synthetic_candle
            )

        return predictions
```

---

# 15. Dashboard Integration

After creating a new model file, add its import to:

```text
dashboard.py
```

Example:

```python
from src.ml.random_forest import (
    RandomForestForecaster,
)
```

Then create it in Streamlit session state:

```python
if (
    "random_forest_forecaster"
    not in st.session_state
):

    st.session_state.random_forest_forecaster = (
        RandomForestForecaster(
            lookback=20,
            horizon=1,
        )
    )
```

Add the model to the selector:

```python
forecast_model = st.selectbox(
    "Forecast Model",
    [
        "None",
        "Decision Tree",
        "Linear Regression",
        "AutoReg",
        "Random Forest",
    ],
    key="forecast_model",
)
```

Then extend the model-selection block:

```python
if forecast_model == "Decision Tree":

    forecaster = (
        st.session_state
        .decision_tree_forecaster
    )

elif forecast_model == "Linear Regression":

    forecaster = (
        st.session_state
        .linear_regression_forecaster
    )

elif forecast_model == "AutoReg":

    forecaster = (
        st.session_state
        .autoreg_forecaster
    )

elif forecast_model == "Random Forest":

    forecaster = (
        st.session_state
        .random_forest_forecaster
    )
```

The existing generic forecast pipeline should then continue to work:

```python
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
```

followed by:

```python
fitted = forecaster.fit(
    training_candles
)
```

and:

```python
predicted_candles = (
    forecaster.predict_recursive(
        training_candles,
        steps=forecast_length,
    )
)
```

---

# 16. Model Naming Convention

Prefer:

```text
RandomForestForecaster
GradientBoostingForecaster
XGBoostForecaster
LSTMForecaster
GRUForecaster
TCNForecaster
TransformerForecaster
```

and filenames:

```text
random_forest.py
gradient_boosting.py
xgboost_forecaster.py
lstm.py
gru.py
tcn.py
transformer.py
```

Avoid vague class names such as:

```text
Model
MLModel
Predictor
AI
Network
```

because they become painful once the project contains multiple models.

---

# 17. Prompt Template for an LLM

The following prompt can be copied into an LLM when asking it to create a new forecasting model.

Replace:

```text
<MODEL_NAME>
```

with the model you want.

Examples:

```text
Random Forest
Ridge Regression
XGBoost
LSTM
GRU
TCN
Transformer
```

---

## General LLM Prompt

```text
I am adding a new forecasting model to an existing Python agent-based stock-market simulator.

Create a complete new file:

src/ml/<MODEL_FILENAME>.py

for a forecasting class named:

<MODEL_CLASS_NAME>

using the model:

<MODEL_NAME>

The implementation MUST be compatible with my existing forecasting dashboard.

PROJECT CONTEXT

Prices are stored internally as integer cents.

Each candle object exposes:

candle.open
candle.high
candle.low
candle.close
candle.volume
candle.trade_count
candle.start_tick
candle.end_tick

Existing forecasting classes include:

DecisionTreeForecaster
LinearRegressionForecaster
AutoRegForecaster

The dashboard selects a forecaster and uses the following generic workflow:

forecaster.fit(training_candles)

followed by:

forecaster.predict_recursive(
    training_candles,
    steps=forecast_length,
)

Therefore the new model must support the same interface.

REQUIRED CLASS ATTRIBUTES

The class should expose:

self.lookback
self.horizon
self.minimum_training_candles
self.is_fitted

REQUIRED METHODS

Implement:

__init__()

fit(candles) -> bool

predict(candles) -> list[dict] if appropriate

predict_recursive(
    candles,
    steps=30,
) -> list[dict]

evaluate(
    candles,
    train_fraction=0.8,
) if practical

FORECAST OUTPUT FORMAT

predict_recursive() must return:

[
    {
        "open": integer_price,
        "high": integer_price,
        "low": integer_price,
        "close": integer_price,
    },
    ...
]

All prices must remain integer cents.

VALID OHLC RULES

Every predicted candle must satisfy:

high >= open
high >= close
low <= open
low <= close
all prices >= 1

DATA LEAKAGE RULES

The model receives only the training candles supplied to fit() and predict_recursive().

Do not access the global market object.

Do not use realized future candles.

Do not use future volume or future trade_count.

Do not randomly shuffle time-series samples during evaluation.

If recursive prediction requires future volume or trade_count, estimate them only from prior historical or synthetic candles.

FEATURE ENGINEERING

Prefer normalized price features instead of raw price levels.

Possible candle features include:

open return relative to previous close
high return relative to previous close
low return relative to previous close
close return relative to previous close
candle range
candle body
upper wick
lower wick
volume
trade_count

For tabular models, flatten the last `lookback` candles into a feature vector.

For sequence models, preserve sequence shape:

(samples, lookback, features)

TARGET

Prefer predicting future OHLC returns rather than absolute prices.

For example:

future_return =
    (future_price - anchor_price)
    / anchor_price

Reconstruct prices afterward using the anchor or recursively predicted previous close.

RECURSIVE FORECASTING

The dashboard may request 30 or more future candles.

If the model predicts only one next candle, recursively feed the predicted candle back into the working history.

Do not use realized future candles during recursion.

If the model naturally predicts multiple future steps, it may use its direct multi-horizon output, but predict_recursive() must still return exactly the requested number of candle dictionaries where possible.

MODEL-SPECIFIC REQUIREMENTS

Use appropriate preprocessing and architecture for <MODEL_NAME>.

If feature scaling is useful, fit the scaler only on training data.

If using scikit-learn, prefer a Pipeline where appropriate.

If using PyTorch:

- automatically use CUDA when available
- otherwise fall back to CPU
- keep the model reasonably small for an RTX 4060 8 GB
- use DataLoader
- use train/validation separation without shuffling across future time
- use reproducible seeds where practical
- avoid excessive epochs by default
- include early stopping if practical
- store the trained network on the class
- use model.eval() and torch.no_grad() for inference

MINIMUM TRAINING HISTORY

Set:

self.minimum_training_candles

to a sensible value for the chosen model.

The method fit() must return False instead of raising an exception when insufficient history is available.

ROBUSTNESS

Reset stale fitted state at the beginning of fit().

Catch expected model-estimation errors where appropriate.

Do not silently swallow unexpected programming errors.

Return an empty list from prediction when prediction cannot be performed.

CODE STYLE

Use clear section comments such as:

# ======================================================
# BUILD DATASET
# ======================================================

Keep methods readable.

Do not over-engineer the class.

Do not change any existing project files.

Only output the complete contents of:

src/ml/<MODEL_FILENAME>.py

After the code, briefly explain:

1. what input features the model uses
2. what target it predicts
3. how recursive prediction works
4. what minimum training history it requires
5. any required package dependency
```

---

# 18. Prompt for Dashboard Integration

After the model file exists and passes an independent test, use this prompt:

```text
I have added a new forecasting model to my Python Streamlit market simulator.

Model file:

src/ml/<MODEL_FILENAME>.py

Class:

<MODEL_CLASS_NAME>

Display name:

<DISPLAY_NAME>

My dashboard already supports:

None
Decision Tree
Linear Regression
AutoReg

The dashboard uses a generic lagged forecasting pipeline.

The new model exposes:

fit(candles)

predict_recursive(
    candles,
    steps,
)

lookback

horizon

minimum_training_candles

I want to integrate the model without rewriting the existing forecast pipeline.

Show me ONLY the exact dashboard.py edits required for:

1. the import
2. Streamlit session-state initialization
3. adding the model to the Forecast Model selectbox
4. adding the model to the forecaster-selection if/elif block

Do not rewrite the generic forecasting logic.

Do not create duplicate forecast-generation blocks.

Preserve the existing lagged backtest behavior.

Preserve the existing gray forecast candlestick renderer.

Give exact code snippets and clearly state where each snippet should be inserted.
```

---

# 19. Prompt for Independent Model Testing

Before connecting a new model to Streamlit, test it independently.

Use this prompt with an LLM:

```text
Create a standalone Python terminal test for my new forecaster:

<MODEL_CLASS_NAME>

located at:

src/ml/<MODEL_FILENAME>.py

My simulation is constructed as:

simulation = Simulation(
    seed=42,
    num_traders=1000,
    num_momentum_traders=20,
    num_mean_reversion_traders=20,
    num_liquidity_takers=10,
    num_market_makers=5,
)

Run:

simulation.run(20000)

Use:

forecast_lag = 30

Train the model only on:

market.candles[:-forecast_lag]

Then:

1. print completed candle count
2. fit the model
3. print whether fitting succeeded
4. generate 30 recursive predictions
5. print the number of predictions
6. print the first 5 predicted candles
7. verify every predicted candle satisfies valid OHLC constraints
8. fail loudly if any prediction contains NaN or infinity

Return the test as a bash heredoc command in this form:

python - <<'PY'
...
PY

Do not modify project files.
```

---

# 20. Prompt for Model Evaluation

Use this prompt after the model works:

```text
I have a forecasting class named:

<MODEL_CLASS_NAME>

for my simulated financial candle time series.

I want to evaluate it without future leakage.

Create or improve an evaluate() method that uses a chronological train/test split.

Do NOT shuffle data.

Evaluate:

- MAE
- RMSE
- directional accuracy for close returns
- naive baseline MAE
- naive baseline RMSE
- percentage improvement over baseline

For the naive baseline, use zero predicted return / unchanged price where appropriate.

If the model predicts OHLC, also report separate MAE values for:

open
high
low
close

Preserve the existing class API.

Do not modify dashboard.py.

Explain exactly what each metric means and why a model can visually look good while still underperforming a naive baseline.
```

---

# 21. Prompt for a Random Forest Model

```text
Create:

src/ml/random_forest.py

containing:

RandomForestForecaster

for my existing market simulator.

Use sklearn.ensemble.RandomForestRegressor.

The class must support:

lookback
horizon
minimum_training_candles
is_fitted
fit(candles)
predict(candles)
predict_recursive(candles, steps)
evaluate(candles)

Each candle exposes:

open
high
low
close
volume
trade_count
start_tick
end_tick

Prices are integer cents.

Use normalized OHLC returns, candle range, volume, and trade_count as historical features.

Flatten the lookback sequence for Random Forest input.

Predict OHLC future returns.

Prevent future leakage.

Use chronological evaluation.

Return valid OHLC dictionaries from predict_recursive().

Do not access global market state.

Do not modify any other files.

Make the implementation similar in external API to DecisionTreeForecaster and LinearRegressionForecaster.
```

---

# 22. Prompt for XGBoost

```text
Create:

src/ml/xgboost_forecaster.py

containing:

XGBoostForecaster

for my existing market simulator.

Use xgboost.XGBRegressor.

Preserve the same forecasting API used by:

DecisionTreeForecaster
LinearRegressionForecaster
AutoRegForecaster

Requirements:

- chronological time-series dataset construction
- no future leakage
- normalized OHLC return targets
- lagged candle features
- recursive multi-step forecast support
- valid OHLC enforcement
- sensible minimum_training_candles
- reproducible random_state
- reasonable defaults suitable for interactive experimentation
- evaluation against a zero-return naive baseline

If multi-output XGBoost support is awkward, create one regressor per target or otherwise use a robust implementation.

Do not modify any other files.

At the end, list the required pip/conda package.
```

---

# 23. Prompt for LSTM

```text
Create:

src/ml/lstm.py

containing:

LSTMForecaster

for my existing Python market simulator.

Use PyTorch.

My GPU is an NVIDIA RTX 4060 8 GB, so automatically use CUDA when available and otherwise use CPU.

The model must integrate with my existing dashboard using:

fit(candles) -> bool

predict_recursive(
    candles,
    steps=30,
) -> list[dict]

and expose:

lookback
horizon
minimum_training_candles
is_fitted

CANDLE INPUT

Each candle exposes:

open
high
low
close
volume
trade_count
start_tick
end_tick

Prices are integer cents.

SEQUENCE FEATURES

Use per-candle normalized features such as:

open return relative to previous close
high return relative to previous close
low return relative to previous close
close return relative to previous close
candle range
volume
trade_count

Preserve the input as:

(samples, lookback, features)

Do not flatten the sequence.

TARGET

Predict the next candle's:

open return
high return
low return
close return

relative to the most recent known close.

Use recursive prediction to create arbitrary forecast lengths.

SCALING

Scale input features using statistics computed only from training data.

Scale targets if useful.

Store scaling parameters inside the forecaster.

Never fit a scaler using future/test data.

TRAINING

Use chronological training/validation separation.

Do not randomly split future observations into training.

DataLoader may shuffle samples only inside the already-defined training partition if appropriate, but validation must remain held out chronologically.

Use:

Adam or AdamW
MSE or SmoothL1 loss
gradient clipping
early stopping
reasonable batch size
reasonable hidden size
1-2 LSTM layers
dropout only when appropriate

Keep defaults fast enough for an interactive project.

Use deterministic seeds where practical.

INFERENCE

Use:

model.eval()
torch.no_grad()

Move tensors to the selected device.

Convert predicted returns back into integer-cent OHLC prices.

Enforce valid OHLC constraints.

RECURSION

Future volume and trade_count are unknown.

Estimate them only from historical or synthetic candles.

Never access realized future candles.

ROBUSTNESS

fit() should return False if there is insufficient history.

Do not crash the dashboard because of small datasets.

Set:

minimum_training_candles

to a sensible value, probably significantly larger than lookback.

Do not modify any other project files.

After the complete file, explain:

- network architecture
- tensor shapes
- features
- target
- training procedure
- recursive forecast procedure
- CUDA behavior
- required dependency
```

---

# 24. Prompt for GRU

The GRU prompt is almost identical to the LSTM prompt.

Replace:

```text
LSTMForecaster
```

with:

```text
GRUForecaster
```

and require:

```text
torch.nn.GRU
```

A GRU is often a useful comparison because it has fewer recurrent gates and parameters than an LSTM.

---

# 25. Prompt for a Transformer

```text
Create:

src/ml/transformer.py

containing:

TransformerForecaster

for my existing market simulator.

Use PyTorch.

The model must remain small enough for an NVIDIA RTX 4060 8 GB and must fall back to CPU when CUDA is unavailable.

Preserve my existing forecaster API:

fit(candles) -> bool

predict_recursive(
    candles,
    steps=30,
) -> list[dict]

Expose:

lookback
horizon
minimum_training_candles
is_fitted

Use chronological time-series training with no future leakage.

Each input candle can include normalized:

open return
high return
low return
close return
range
volume
trade_count

Input tensor shape should be:

(batch, lookback, features)

Project features into a small embedding dimension.

Use positional encoding.

Use a small Transformer encoder, not a huge language-model architecture.

Recommended scale:

d_model around 32-128
2-4 attention heads
1-3 encoder layers

Predict the next candle OHLC returns.

Use recursive multi-step forecasting.

Scale features using training-only statistics.

Use early stopping and reasonable defaults.

Enforce valid reconstructed OHLC candles.

Do not use future volume or trade count during recursive inference.

Do not access global simulator state.

Do not modify dashboard.py or other files.

At the end, clearly describe:

- sequence shape
- embedding
- positional encoding
- attention architecture
- target
- training
- recursive inference
- GPU behavior
- expected minimum history requirement
```

---

# 26. Prompt for a Time-Series Model such as ARIMA

```text
Create:

src/ml/arima.py

containing:

ARIMAForecaster

using statsmodels.

The model must be compatible with my dashboard through:

fit(candles)

predict_recursive(
    candles,
    steps,
)

The project stores integer-cent OHLC candles.

Prefer modeling stationary return series rather than raw price level.

If ARIMA is univariate, use separate models for:

open returns
high returns
low returns
close returns

or explain and implement a better statistically valid approach.

Reconstruct future OHLC recursively from predicted returns.

Set a sensible minimum_training_candles.

Catch expected statsmodels estimation errors and return False instead of crashing Streamlit.

Do not use future data.

Do not modify any other files.

Make the external API consistent with AutoRegForecaster.
```

---

# 27. Prompt for Debugging a New Model

When a model fails, give the LLM the complete traceback and use:

```text
I am adding <MODEL_CLASS_NAME> to my market simulator.

Here is the complete traceback:

<PASTE TRACEBACK>

Here is the complete model file:

<PASTE MODEL FILE>

Please diagnose the exact cause.

Do not redesign the entire project.

Tell me:

1. why the error occurs
2. the smallest safe fix
3. exactly which lines/block to replace
4. whether the bug is model-specific or dashboard-integration-specific
5. whether the fix could create future leakage
6. whether minimum_training_candles should change

Preserve the existing external API:

fit(candles)
predict_recursive(candles, steps)

Do not make unrelated edits.
```

This is preferable to prompting:

```text
it broke fix pls
```

which, while emotionally valid, gives an LLM considerable freedom to redecorate the house while repairing a light switch.

---

# 28. Prompt for Code Review

```text
Review this forecasting model for my agent-based market simulator:

<PASTE COMPLETE MODEL FILE>

Check specifically for:

- future leakage
- accidental use of realized future candles
- time-series split errors
- incorrect target alignment
- off-by-one lookback errors
- recursive forecast errors
- invalid OHLC reconstruction
- NaN / infinity risk
- price scaling mistakes
- raw integer-cent price assumptions
- stale fitted model state
- insufficient-history handling
- feature scaling leakage
- inappropriate random shuffling
- dashboard API incompatibility
- excessive computational cost
- unstable multi-step behavior

My required API is:

fit(candles) -> bool

predict_recursive(
    candles,
    steps,
) -> list of OHLC dictionaries

Do not rewrite the file unless necessary.

First report the issues ranked by severity.

Then provide exact replacement blocks only for changes that are actually needed.
```

---

# 29. Checklist Before Adding a Model to the Dashboard

Verify all of the following:

- [ ] Model lives in its own file under `src/ml/`
- [ ] Class name is descriptive
- [ ] `lookback` exists
- [ ] `horizon` exists
- [ ] `minimum_training_candles` exists
- [ ] `is_fitted` exists
- [ ] `fit()` returns `True` or `False`
- [ ] `fit()` handles insufficient history
- [ ] `fit()` resets stale state
- [ ] Model does not access future candles
- [ ] Model does not access global market state
- [ ] Evaluation is chronological
- [ ] Feature scaling uses training data only
- [ ] Recursive forecasting does not use realized future data
- [ ] Output prices are integer cents
- [ ] Output OHLC relationships are valid
- [ ] Predictions contain no NaN
- [ ] Predictions contain no infinity
- [ ] Independent terminal test passes
- [ ] 30-step recursive prediction works
- [ ] Dashboard import added
- [ ] Session-state model added
- [ ] Selector option added
- [ ] Forecaster-selection branch added
- [ ] Existing generic forecast block is reused
- [ ] No duplicate forecast-generation logic was added

---

# 30. Suggested Model Progression

A useful progression is:

```text
Linear Regression
        ↓
Decision Tree
        ↓
AutoReg
        ↓
Random Forest
        ↓
Gradient Boosting / XGBoost
        ↓
LSTM
        ↓
GRU
        ↓
TCN
        ↓
Transformer
```

Each new model should be evaluated on the same historical windows.

A more complicated model is not automatically a better model.

The main comparison should remain:

```text
same market
same information
same cutoff
same forecast horizon
same metrics
```

This provides a fair test of whether additional model complexity actually improves forecasting.

---

# 31. Recommended Future Refactor

As the number of forecasting models grows, repeated code should eventually be moved into shared utilities.

Possible future structure:

```text
src/ml/
├── base.py
├── features.py
├── evaluation.py
├── decision_tree.py
├── linear_regression.py
├── autoreg.py
├── random_forest.py
├── xgboost_forecaster.py
├── lstm.py
├── gru.py
└── transformer.py
```

Possible responsibilities:

```text
base.py
    common forecaster interface

features.py
    candle feature extraction
    normalization
    dataset construction

evaluation.py
    chronological splits
    MAE
    RMSE
    directional accuracy
    naive baseline comparison
```

Do this refactor only when duplication becomes significant.

Do not create abstraction merely because abstraction has become fashionable.

---

# 32. Final Principle

The forecasting system should preserve the project's broader design philosophy:

```text
Market mechanics generate prices.

Historical market data is given to models.

Models forecast future candles.

Future candles are never revealed during training or inference.

Predictions are evaluated against realized outcomes.
```

The forecasting layer should analyze the simulated market.

It should never secretly control the market it is supposed to predict.
