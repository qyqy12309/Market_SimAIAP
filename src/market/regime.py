class MarketRegimeController:

    def __init__(
        self,
        rng,
        config,
    ):
        self.rng = rng
        self.config = config

        self.min_duration = (
            config.min_duration
        )

        self.max_duration = (
            config.max_duration
        )

        self.current_regime = (
            config.initial_regime
        )

        self.ticks_remaining = (
            self._random_duration()
        )

        self.regime_history = []

    # ======================================================
    # RANDOM DURATION
    # ======================================================

    def _random_duration(self):

        return self.rng.randint(
            self.min_duration,
            self.max_duration,
        )

    # ======================================================
    # CURRENT REGIME CONFIG
    # ======================================================

    @property
    def current_config(self):

        return self.config.regimes[
            self.current_regime
        ]

    # ======================================================
    # CHOOSE NEXT REGIME
    # ======================================================

    def _choose_next_regime(self):

        transitions = (
            self.config.transitions[
                self.current_regime
            ]
        )

        regimes = list(
            transitions.keys()
        )

        probabilities = list(
            transitions.values()
        )

        return self.rng.choices(
            regimes,
            weights=probabilities,
            k=1,
        )[0]

    # ======================================================
    # UPDATE
    # ======================================================

    def step(
        self,
        tick,
    ):

        self.ticks_remaining -= 1

        if self.ticks_remaining > 0:
            return False

        previous_regime = (
            self.current_regime
        )

        self.current_regime = (
            self._choose_next_regime()
        )

        self.ticks_remaining = (
            self._random_duration()
        )

        self.regime_history.append(
            {
                "tick": tick,

                "from":
                    previous_regime,

                "to":
                    self.current_regime,

                "duration":
                    self.ticks_remaining,
            }
        )

        return True