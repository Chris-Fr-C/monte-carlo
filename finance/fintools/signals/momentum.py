from dataclasses import dataclass, field
from typing import override
import numpy as np
import pandas as pd
import fintools.signals.interface as si
import pendulum
import fintools.interface as i

import ta.momentum
import polars as pl



from dataclasses import dataclass, field
from typing import override
import polars as pl
import ta.momentum
import fintools.interface as i
import fintools.signals.interface as si


@dataclass()
class AwesomeOscillatorSignal(si.SignalInterface):
    window1: int = field(default=5)
    window2: int = field(default=34)

    @override
    def topology(self)->str:
        return "momentum"

    @override
    def name(self) -> str:
        return f"awesome-oscillator-{self.window1}d-{self.window2}d"

    @override
    def __call__(
        self,
        df: i.QuotesDf.DataFrame,
        symbol: str,
    ) -> si.SignalDf.DataFrame:
        pdf = df.to_pandas()
        c = i.QuotesDf.Columns
        o = si.SignalDf.Columns

        _ao = "ao"
        _ao_diff = "ao_diff"

        # Compute AO via ta library
        ao_indicator = ta.momentum.AwesomeOscillatorIndicator(
            high=pdf[c.HIGH],
            low=pdf[c.LOW],
            window1=self.window1,
            window2=self.window2,
        )

        ao_series = pl.Series(ao_indicator.awesome_oscillator()).alias(_ao)
        df = df.insert_column(0, ao_series)

        # Calculate momentum metrics: line cross, zero cross, and bar direction (slope)
        df = df.with_columns(
            (pl.col(_ao) - pl.col(_ao).shift(1)).alias(_ao_diff),
            (
                (pl.col(_ao).sign())
                .ne(pl.col(_ao).shift(1).sign())
                & pl.col(_ao).shift(1).is_not_null()
            ).alias("zero_cross"),
            (
                (pl.col(_ao) - pl.col(_ao).shift(1)).sign()
                .ne((pl.col(_ao).shift(1) - pl.col(_ao).shift(2)).sign())
                & pl.col(_ao).shift(2).is_not_null()
            ).alias("peak_trough"),
        )

        # Signal Classification Strategy:
        # 1. Zero-line Cross -> Primary UP / DOWN signal
        # 2. Peak/Trough reversals -> MOMENTUM_ACCELERATION / MOMENTUM_DECELERATION
        # 3. Bar color changes (Green/Red) -> MOMENTUM_ACCELERATION / DECELERATION
        df = df.with_columns(
            pl.when(pl.col("zero_cross") & (pl.col(_ao) > 0))
            .then(pl.lit(si.SignalDirection.UP))
            .when(pl.col("zero_cross") & (pl.col(_ao) < 0))
            .then(pl.lit(si.SignalDirection.DOWN))
            .when(pl.col("peak_trough") & (pl.col(_ao_diff) > 0))
            .then(pl.lit(si.SignalDirection.MOMENTUM_ACCELERATION))
            .when(pl.col("peak_trough") & (pl.col(_ao_diff) < 0))
            .then(pl.lit(si.SignalDirection.MOMENTUM_DECELERATION))
            .otherwise(pl.lit(si.SignalDirection.UNSPECIFIED))
            .alias(o.CATEGORY)
        ).with_columns(pl.lit(self.name()).alias(o.NAME))

        # Confidence Calculation (0.0 to 1.0):
        # Normalizes absolute AO value using a rolling min-max standardizer
        df = df.with_columns(
            pl.when(pl.col(o.CATEGORY) != si.SignalDirection.UNSPECIFIED)
            .then(
                (
                    (pl.col(_ao).abs() - pl.col(_ao).abs().rolling_min(window_size=100, min_samples=20))
                    / (
                        pl.col(_ao).abs().rolling_max(window_size=100, min_samples=20)
                        - pl.col(_ao).abs().rolling_min(window_size=100, min_samples=20)
                        + 1e-6
                    )
                ).clip(0.0, 1.0)
            )
            .otherwise(pl.lit(0.0))
            .alias(o.CONFIDENCE)
        )

        out = df.select(
            *(pl.col(x) for x in [o.CATEGORY, o.CONFIDENCE, o.NAME, o.SYMBOL, o.TS])
        )

        return out


@dataclass()
class KAMASignal(si.SignalInterface):
    window: int = field(default=10)
    pow1: int = field(default=2)
    pow2: int = field(default=30)

    @override
    def topology(self)->str:
        return "momentum"
    @override
    def name(self) -> str:
        return f"kama-signal-{self.window}d-{self.pow1}-{self.pow2}"

    @override
    def __call__(
        self,
        df: i.QuotesDf.DataFrame,
        symbol: str,
    ) -> si.SignalDf.DataFrame:
        pdf = df.to_pandas()
        c = i.QuotesDf.Columns
        o = si.SignalDf.Columns

        _kama = "kama"
        _kama_diff = "kama_diff"

        # Compute KAMA via ta library
        kama_indicator = ta.momentum.KAMAIndicator(
            close=pdf[c.CLOSE],
            window=self.window,
            pow1=self.pow1,
            pow2=self.pow2,
        )

        kama_series = pl.Series(kama_indicator.kama()).alias(_kama)
        df = df.insert_column(0, kama_series)

        # Calculate Price-vs-KAMA cross and KAMA slope dynamics
        df = df.with_columns(
            (pl.col(c.CLOSE) - pl.col(_kama)).alias("price_kama_diff"),
            (pl.col(_kama) - pl.col(_kama).shift(1)).alias(_kama_diff),
            (
                (pl.col(c.CLOSE) - pl.col(_kama)).sign()
                .ne((pl.col(c.CLOSE).shift(1) - pl.col(_kama).shift(1)).sign())
                & pl.col(_kama).shift(1).is_not_null()
            ).alias("price_kama_cross"),
        )

        # Calculate slope directional change (Inflection Point)
        df = df.with_columns(
            (
                (pl.col(_kama_diff).sign())
                .ne(pl.col(_kama_diff).shift(1).sign())
                & pl.col(_kama_diff).shift(1).is_not_null()
            ).alias("slope_inflection")
        )

        # Signal Classification Strategy:
        # 1. Price crosses KAMA line -> Primary UP / DOWN signal
        # 2. Slope flips upwards/downwards -> MOMENTUM_ACCELERATION / MOMENTUM_DECELERATION
        df = df.with_columns(
            pl.when(pl.col("price_kama_cross") & (pl.col(c.CLOSE) > pl.col(_kama)))
            .then(pl.lit(si.SignalDirection.UP))
            .when(pl.col("price_kama_cross") & (pl.col(c.CLOSE) < pl.col(_kama)))
            .then(pl.lit(si.SignalDirection.DOWN))
            .when(pl.col("slope_inflection") & (pl.col(_kama_diff) > 0))
            .then(pl.lit(si.SignalDirection.MOMENTUM_ACCELERATION))
            .when(pl.col("slope_inflection") & (pl.col(_kama_diff) < 0))
            .then(pl.lit(si.SignalDirection.MOMENTUM_DECELERATION))
            .otherwise(pl.lit(si.SignalDirection.UNSPECIFIED))
            .alias(o.CATEGORY)
        ).with_columns(pl.lit(self.name()).alias(o.NAME))

        # Confidence Calculation (0.0 to 1.0):
        # Based on normalized relative distance between close price and KAMA
        df = df.with_columns(
            pl.when(pl.col(o.CATEGORY) != si.SignalDirection.UNSPECIFIED)
            .then(
                (
                    (pl.col(c.CLOSE) - pl.col(_kama)).abs() / pl.col(_kama)
                ) / (
                    (pl.col(c.CLOSE) - pl.col(_kama)).abs() / pl.col(_kama)
                ).rolling_max(window_size=100, min_samples=20).add(1e-6)
            )
            .otherwise(pl.lit(0.0))
            .clip(0.0, 1.0)
            .alias(o.CONFIDENCE)
        )

        out = df.select(
            *(pl.col(x) for x in [o.CATEGORY, o.CONFIDENCE, o.NAME, o.SYMBOL, o.TS])
        )
        return out



@dataclass()
class PPOSignal(si.SignalInterface):
    window_slow: int = field(default=26)
    window_fast: int = field(default=12)
    window_sign: int = field(default=9)

    @override
    def topology(self)->str:
        return "momentum"
    @override
    def name(self) -> str:
        return f"ppo-signal-{self.window_fast}d-{self.window_slow}d-{self.window_sign}d"

    @override
    def __call__(
        self,
        df: i.QuotesDf.DataFrame,
        symbol: str,
    ) -> si.SignalDf.DataFrame:
        pdf = df.to_pandas()
        c = i.QuotesDf.Columns
        o = si.SignalDf.Columns

        _ppo = "ppo"
        _ppo_signal = "ppo_signal"
        _ppo_hist = "ppo_hist"

        # Compute PPO components via ta library
        ppo_indicator = ta.momentum.PercentagePriceOscillator(
            close=pdf[c.CLOSE],
            window_slow=self.window_slow,
            window_fast=self.window_fast,
            window_sign=self.window_sign,
        )

        ppo_series = pl.Series(ppo_indicator.ppo()).alias(_ppo)
        signal_series = pl.Series(ppo_indicator.ppo_signal()).alias(_ppo_signal)
        hist_series = pl.Series(ppo_indicator.ppo_hist()).alias(_ppo_hist)

        df = (
            df.insert_column(0, ppo_series)
            .insert_column(0, signal_series)
            .insert_column(0, hist_series)
        )

        # Signal Logic: Signal Line Crosses, Zero Line Crosses, and Overbought/Oversold thresholds
        df = df.with_columns(
            # PPO crossing Signal Line
            (
                (pl.col(_ppo) - pl.col(_ppo_signal)).sign()
                .ne((pl.col(_ppo).shift(1) - pl.col(_ppo_signal).shift(1)).sign())
                & pl.col(_ppo_signal).shift(1).is_not_null()
            ).alias("signal_cross"),
            # Histogram Expansion/Contraction
            (
                (pl.col(_ppo_hist) - pl.col(_ppo_hist).shift(1)).sign()
                .ne((pl.col(_ppo_hist).shift(1) - pl.col(_ppo_hist).shift(2)).sign())
                & pl.col(_ppo_hist).shift(2).is_not_null()
            ).alias("hist_inflection"),
        )

        # Threshold-based levels (PPO is percentage-based, typically +/- 5% to 10% indicates extremities)
        ppo_upper_bound = 5.0
        ppo_lower_bound = -5.0

        # Signal Classification Strategy:
        # 1. PPO crossing Signal Line -> Primary UP / DOWN signal
        # 2. Histogram slope reversal -> MOMENTUM_ACCELERATION / MOMENTUM_DECELERATION
        # 3. Extremes beyond percentage thresholds -> OVERBOUGHT / OVERSOLD
        df = df.with_columns(
            pl.when(pl.col("signal_cross") & (pl.col(_ppo) > pl.col(_ppo_signal)))
            .then(pl.lit(si.SignalDirection.UP))
            .when(pl.col("signal_cross") & (pl.col(_ppo) < pl.col(_ppo_signal)))
            .then(pl.lit(si.SignalDirection.DOWN))
            .when(pl.col(_ppo) > ppo_upper_bound)
            .then(pl.lit(si.SignalDirection.OVERBOUGHT))
            .when(pl.col(_ppo) < ppo_lower_bound)
            .then(pl.lit(si.SignalDirection.OVERSOLD))
            .when(
                pl.col("hist_inflection")
                & (pl.col(_ppo_hist) > pl.col(_ppo_hist).shift(1))
            )
            .then(pl.lit(si.SignalDirection.MOMENTUM_ACCELERATION))
            .when(
                pl.col("hist_inflection")
                & (pl.col(_ppo_hist) < pl.col(_ppo_hist).shift(1))
            )
            .then(pl.lit(si.SignalDirection.MOMENTUM_DECELERATION))
            .otherwise(pl.lit(si.SignalDirection.UNSPECIFIED))
            .alias(o.CATEGORY)
        ).with_columns(pl.lit(self.name()).alias(o.NAME))

        # Confidence Calculation (0.0 to 1.0):
        # Uses the normalized absolute magnitude of the PPO Histogram relative to its rolling range
        df = df.with_columns(
            pl.when(pl.col(o.CATEGORY) != si.SignalDirection.UNSPECIFIED)
            .then(
                (
                    (
                        pl.col(_ppo_hist).abs()
                        - pl.col(_ppo_hist)
                        .abs()
                        .rolling_min(window_size=100, min_samples=20)
                    )
                    / (
                        pl.col(_ppo_hist)
                        .abs()
                        .rolling_max(window_size=100, min_samples=20)
                        - pl.col(_ppo_hist)
                        .abs()
                        .rolling_min(window_size=100, min_samples=20)
                        + 1e-6
                    )
                ).clip(0.0, 1.0)
            )
            .otherwise(pl.lit(0.0))
            .alias(o.CONFIDENCE)
        )

        out = df.select(
            *(pl.col(x) for x in [o.CATEGORY, o.CONFIDENCE, o.NAME, o.SYMBOL, o.TS])
        )
        return out



@dataclass()
class PVOSignal(si.SignalInterface):
    window_slow: int = field(default=26)
    window_fast: int = field(default=12)
    window_sign: int = field(default=9)

    @override
    def topology(self)->str:
        return "momentum"
    @override
    def name(self) -> str:
        return f"pvo-signal-{self.window_fast}d-{self.window_slow}d-{self.window_sign}d"

    @override
    def __call__(
        self,
        df: i.QuotesDf.DataFrame,
        symbol: str,
    ) -> si.SignalDf.DataFrame:
        pdf = df.to_pandas()
        c = i.QuotesDf.Columns
        o = si.SignalDf.Columns

        _pvo = "pvo"
        _pvo_signal = "pvo_signal"
        _pvo_hist = "pvo_hist"

        # Compute PVO components via ta library
        pvo_indicator = ta.momentum.PercentageVolumeOscillator(
            volume=pdf[c.VOLUME],
            window_slow=self.window_slow,
            window_fast=self.window_fast,
            window_sign=self.window_sign,
        )

        pvo_series = pl.Series(pvo_indicator.pvo()).alias(_pvo)
        signal_series = pl.Series(pvo_indicator.pvo_signal()).alias(_pvo_signal)
        hist_series = pl.Series(pvo_indicator.pvo_hist()).alias(_pvo_hist)

        df = (
            df.insert_column(0, pvo_series)
            .insert_column(0, signal_series)
            .insert_column(0, hist_series)
        )

        # Signal Logic: Crosses and Volatility Dynamics
        df = df.with_columns(
            # PVO line crossing Signal Line
            (
                (pl.col(_pvo) - pl.col(_pvo_signal)).sign()
                .ne((pl.col(_pvo).shift(1) - pl.col(_pvo_signal).shift(1)).sign())
                & pl.col(_pvo_signal).shift(1).is_not_null()
            ).alias("signal_cross"),
            # Zero-Line Crossovers (Volume expansion vs contraction)
            (
                (pl.col(_pvo).sign())
                .ne(pl.col(_pvo).shift(1).sign())
                & pl.col(_pvo).shift(1).is_not_null()
            ).alias("zero_cross"),
        )

        # Signal Classification Strategy:
        # PVO measures volume dynamics rather than price direction.
        # 1. PVO > 0 or crossing above signal -> VOLATILITY_EXPANSION
        # 2. PVO < 0 or crossing below signal -> VOLATILITY_CONTRACTION
        df = df.with_columns(
            pl.when(pl.col("zero_cross") & (pl.col(_pvo) > 0))
            .then(pl.lit(si.SignalDirection.VOLATILITY_EXPANSION))
            .when(pl.col("zero_cross") & (pl.col(_pvo) < 0))
            .then(pl.lit(si.SignalDirection.VOLATILITY_CONTRACTION))
            .when(pl.col("signal_cross") & (pl.col(_pvo) > pl.col(_pvo_signal)))
            .then(pl.lit(si.SignalDirection.VOLATILITY_EXPANSION))
            .when(pl.col("signal_cross") & (pl.col(_pvo) < pl.col(_pvo_signal)))
            .then(pl.lit(si.SignalDirection.VOLATILITY_CONTRACTION))
            .otherwise(pl.lit(si.SignalDirection.UNSPECIFIED))
            .alias(o.CATEGORY)
        ).with_columns(pl.lit(self.name()).alias(o.NAME))

        # Confidence Calculation (0.0 to 1.0):
        # Based on normalized absolute magnitude of the PVO relative to its 100-bar rolling range
        df = df.with_columns(
            pl.when(pl.col(o.CATEGORY) != si.SignalDirection.UNSPECIFIED)
            .then(
                (
                    (
                        pl.col(_pvo).abs()
                        - pl.col(_pvo)
                        .abs()
                        .rolling_min(window_size=100, min_samples=20)
                    )
                    / (
                        pl.col(_pvo)
                        .abs()
                        .rolling_max(window_size=100, min_samples=20)
                        - pl.col(_pvo)
                        .abs()
                        .rolling_min(window_size=100, min_samples=20)
                        + 1e-6
                    )
                ).clip(0.0, 1.0)
            )
            .otherwise(pl.lit(0.0))
            .alias(o.CONFIDENCE)
        )

        out = df.select(
            *(pl.col(x) for x in [o.CATEGORY, o.CONFIDENCE, o.NAME, o.SYMBOL, o.TS])
        )
        return out



@dataclass()
class ROCSignal(si.SignalInterface):
    window: int = field(default=12)

    @override
    def topology(self)->str:
        return "momentum"
    @override
    def name(self) -> str:
        return f"roc-signal-{self.window}d"

    @override
    def __call__(
        self,
        df: i.QuotesDf.DataFrame,
        symbol: str,
    ) -> si.SignalDf.DataFrame:
        pdf = df.to_pandas()
        c = i.QuotesDf.Columns
        o = si.SignalDf.Columns

        _roc = "roc"
        _roc_diff = "roc_diff"

        # Compute ROC via ta library
        roc_indicator = ta.momentum.ROCIndicator(
            close=pdf[c.CLOSE],
            window=self.window,
        )

        roc_series = pl.Series(roc_indicator.roc()).alias(_roc)
        df = df.insert_column(0, roc_series)

        # Calculate dynamics: Zero-line crosses, slope changes, and thresholds
        df = df.with_columns(
            (pl.col(_roc) - pl.col(_roc).shift(1)).alias(_roc_diff),
            # Zero-Line Crossover (Shift in primary directional bias)
            (
                (pl.col(_roc).sign())
                .ne(pl.col(_roc).shift(1).sign())
                & pl.col(_roc).shift(1).is_not_null()
            ).alias("zero_cross"),
            # Inflection / Peak-Trough Reversals
            (
                (pl.col(_roc) - pl.col(_roc).shift(1)).sign()
                .ne((pl.col(_roc).shift(1) - pl.col(_roc).shift(2)).sign())
                & pl.col(_roc).shift(2).is_not_null()
            ).alias("peak_trough"),
        )

        # Standard ROC Overbought / Oversold percentage thresholds
        roc_upper_bound = 10.0
        roc_lower_bound = -10.0

        # Signal Classification Strategy:
        # 1. Zero-line Cross -> Primary UP / DOWN signal
        # 2. Extreme ROC values -> OVERBOUGHT / OVERSOLD
        # 3. Peak/Trough reversals -> MOMENTUM_ACCELERATION / MOMENTUM_DECELERATION
        df = df.with_columns(
            pl.when(pl.col("zero_cross") & (pl.col(_roc) > 0))
            .then(pl.lit(si.SignalDirection.UP))
            .when(pl.col("zero_cross") & (pl.col(_roc) < 0))
            .then(pl.lit(si.SignalDirection.DOWN))
            .when(pl.col(_roc) > roc_upper_bound)
            .then(pl.lit(si.SignalDirection.OVERBOUGHT))
            .when(pl.col(_roc) < roc_lower_bound)
            .then(pl.lit(si.SignalDirection.OVERSOLD))
            .when(pl.col("peak_trough") & (pl.col(_roc_diff) > 0))
            .then(pl.lit(si.SignalDirection.MOMENTUM_ACCELERATION))
            .when(pl.col("peak_trough") & (pl.col(_roc_diff) < 0))
            .then(pl.lit(si.SignalDirection.MOMENTUM_DECELERATION))
            .otherwise(pl.lit(si.SignalDirection.UNSPECIFIED))
            .alias(o.CATEGORY)
        ).with_columns(pl.lit(self.name()).alias(o.NAME))

        # Confidence Calculation (0.0 to 1.0):
        # Uses normalized absolute value of ROC relative to a 100-period rolling range
        df = df.with_columns(
            pl.when(pl.col(o.CATEGORY) != si.SignalDirection.UNSPECIFIED)
            .then(
                (
                    (
                        pl.col(_roc).abs()
                        - pl.col(_roc)
                        .abs()
                        .rolling_min(window_size=100, min_samples=20)
                    )
                    / (
                        pl.col(_roc)
                        .abs()
                        .rolling_max(window_size=100, min_samples=20)
                        - pl.col(_roc)
                        .abs()
                        .rolling_min(window_size=100, min_samples=20)
                        + 1e-6
                    )
                ).clip(0.0, 1.0)
            )
            .otherwise(pl.lit(0.0))
            .alias(o.CONFIDENCE)
        )

        out = df.select(
            *(pl.col(x) for x in [o.CATEGORY, o.CONFIDENCE, o.NAME, o.SYMBOL, o.TS])
        )
        return out



@dataclass()
class StochRSISignal(si.SignalInterface):
    window: int = field(default=14)
    smooth1: int = field(default=3)
    smooth2: int = field(default=3)
    overbought_threshold: float = field(default=0.8)
    oversold_threshold: float = field(default=0.2)

    @override
    def topology(self)->str:
        return "momentum"
    @override
    def name(self) -> str:
        return f"stoch-rsi-{self.window}d-{self.smooth1}d-{self.smooth2}d"

    @override
    def __call__(
        self,
        df: i.QuotesDf.DataFrame,
        symbol: str,
    ) -> si.SignalDf.DataFrame:
        pdf = df.to_pandas()
        c = i.QuotesDf.Columns
        o = si.SignalDf.Columns

        _stoch_rsi = "stoch_rsi"
        _stoch_k = "stoch_k"
        _stoch_d = "stoch_d"

        # Compute Stochastic RSI components via ta library
        stoch_rsi_indicator = ta.momentum.StochRSIIndicator(
            close=pdf[c.CLOSE],
            window=self.window,
            smooth1=self.smooth1,
            smooth2=self.smooth2,
        )

        stoch_rsi_series = pl.Series(stoch_rsi_indicator.stochrsi()).alias(_stoch_rsi)
        k_series = pl.Series(stoch_rsi_indicator.stochrsi_k()).alias(_stoch_k)
        d_series = pl.Series(stoch_rsi_indicator.stochrsi_d()).alias(_stoch_d)

        df = (
            df.insert_column(0, stoch_rsi_series)
            .insert_column(0, k_series)
            .insert_column(0, d_series)
        )

        # Calculate dynamics: %K vs %D crossovers, zone exits, and momentum inflections
        df = df.with_columns(
            # %K line crossing %D line
            (
                (pl.col(_stoch_k) - pl.col(_stoch_d)).sign()
                .ne((pl.col(_stoch_k).shift(1) - pl.col(_stoch_d).shift(1)).sign())
                & pl.col(_stoch_d).shift(1).is_not_null()
            ).alias("kd_cross"),
            # Exiting Oversold/Overbought bounds
            (
                (pl.col(_stoch_k).shift(1) < self.oversold_threshold)
                & (pl.col(_stoch_k) >= self.oversold_threshold)
            ).alias("oversold_exit"),
            (
                (pl.col(_stoch_k).shift(1) > self.overbought_threshold)
                & (pl.col(_stoch_k) <= self.overbought_threshold)
            ).alias("overbought_exit"),
            # Momentum direction (inflection points of %K)
            (
                (pl.col(_stoch_k) - pl.col(_stoch_k).shift(1)).sign()
                .ne((pl.col(_stoch_k).shift(1) - pl.col(_stoch_k).shift(2)).sign())
                & pl.col(_stoch_k).shift(2).is_not_null()
            ).alias("k_inflection"),
        )

        # Signal Classification Strategy:
        # 1. %K crossing %D outside extreme zones / exiting zones -> Primary UP / DOWN signal
        # 2. Extreme levels (>0.8 or <0.2) -> OVERBOUGHT / OVERSOLD
        # 3. Directional shifts in %K slope -> MOMENTUM_ACCELERATION / MOMENTUM_DECELERATION
        df = df.with_columns(
            pl.when(
                (pl.col("kd_cross") & (pl.col(_stoch_k) > pl.col(_stoch_d)))
                | pl.col("oversold_exit")
            )
            .then(pl.lit(si.SignalDirection.UP))
            .when(
                (pl.col("kd_cross") & (pl.col(_stoch_k) < pl.col(_stoch_d)))
                | pl.col("overbought_exit")
            )
            .then(pl.lit(si.SignalDirection.DOWN))
            .when(pl.col(_stoch_k) > self.overbought_threshold)
            .then(pl.lit(si.SignalDirection.OVERBOUGHT))
            .when(pl.col(_stoch_k) < self.oversold_threshold)
            .then(pl.lit(si.SignalDirection.OVERSOLD))
            .when(
                pl.col("k_inflection")
                & (pl.col(_stoch_k) > pl.col(_stoch_k).shift(1))
            )
            .then(pl.lit(si.SignalDirection.MOMENTUM_ACCELERATION))
            .when(
                pl.col("k_inflection")
                & (pl.col(_stoch_k) < pl.col(_stoch_k).shift(1))
            )
            .then(pl.lit(si.SignalDirection.MOMENTUM_DECELERATION))
            .otherwise(pl.lit(si.SignalDirection.UNSPECIFIED))
            .alias(o.CATEGORY)
        ).with_columns(pl.lit(self.name()).alias(o.NAME))

        # Confidence Calculation (0.0 to 1.0):
        # Measures distance of %K from mid-level (0.5), amplified by convergence/divergence of %K and %D
        df = df.with_columns(
            pl.when(pl.col(o.CATEGORY) != si.SignalDirection.UNSPECIFIED)
            .then(
                (
                    ((pl.col(_stoch_k) - 0.5).abs() * 2.0)
                    * (1.0 + (pl.col(_stoch_k) - pl.col(_stoch_d)).abs())
                )
                .truediv(2.0)
                .clip(0.0, 1.0)
            )
            .otherwise(pl.lit(0.0))
            .alias(o.CONFIDENCE)
        )

        out = df.select(
            *(pl.col(x) for x in [o.CATEGORY, o.CONFIDENCE, o.NAME, o.SYMBOL, o.TS])
        )
        return out




@dataclass()
class StochasticOscillatorSignal(si.SignalInterface):
    window: int = field(default=14)
    smooth_window: int = field(default=3)
    overbought_threshold: float = field(default=80.0)
    oversold_threshold: float = field(default=20.0)

    @override
    def topology(self)->str:
        return "momentum"
    @override
    def name(self) -> str:
        return f"stoch-oscillator-{self.window}d-{self.smooth_window}d"

    @override
    def __call__(
        self,
        df: i.QuotesDf.DataFrame,
        symbol: str,
    ) -> si.SignalDf.DataFrame:
        pdf = df.to_pandas()
        c = i.QuotesDf.Columns
        o = si.SignalDf.Columns

        _stoch_k = "local_stoch_k"
        _stoch_d = "local_stoch_d"

        # Compute Stochastic Oscillator components via ta library
        stoch_indicator = ta.momentum.StochasticOscillator(
            high=pdf[c.HIGH],
            low=pdf[c.LOW],
            close=pdf[c.CLOSE],
            window=self.window,
            smooth_window=self.smooth_window,
        )

        k_series = pl.Series(stoch_indicator.stoch()).alias(_stoch_k)
        d_series = pl.Series(stoch_indicator.stoch_signal()).alias(_stoch_d)

        df = df.insert_column(0, k_series).insert_column(0, d_series)

        # Calculate dynamics: %K vs %D crossovers, zone exits, and slope inflections
        df = df.with_columns(
            # %K line crossing %D line
            (
                (pl.col(_stoch_k) - pl.col(_stoch_d)).sign()
                .ne((pl.col(_stoch_k).shift(1) - pl.col(_stoch_d).shift(1)).sign())
                & pl.col(_stoch_d).shift(1).is_not_null()
            ).alias("kd_cross"),
            # Exiting Oversold/Overbought bounds
            (
                (pl.col(_stoch_k).shift(1) < self.oversold_threshold)
                & (pl.col(_stoch_k) >= self.oversold_threshold)
            ).alias("oversold_exit"),
            (
                (pl.col(_stoch_k).shift(1) > self.overbought_threshold)
                & (pl.col(_stoch_k) <= self.overbought_threshold)
            ).alias("overbought_exit"),
            # Slope direction changes for %K
            (
                (pl.col(_stoch_k) - pl.col(_stoch_k).shift(1)).sign()
                .ne((pl.col(_stoch_k).shift(1) - pl.col(_stoch_k).shift(2)).sign())
                & pl.col(_stoch_k).shift(2).is_not_null()
            ).alias("k_inflection"),
        )

        # Signal Classification Strategy:
        # 1. Bullish/Bearish %K vs %D crossover or zone exits -> Primary UP / DOWN signal
        # 2. Extreme levels (>80 or <20) -> OVERBOUGHT / OVERSOLD
        # 3. Directional shifts in %K slope -> MOMENTUM_ACCELERATION / MOMENTUM_DECELERATION
        df = df.with_columns(
            pl.when(
                (pl.col("kd_cross") & (pl.col(_stoch_k) > pl.col(_stoch_d)))
                | pl.col("oversold_exit")
            )
            .then(pl.lit(si.SignalDirection.UP))
            .when(
                (pl.col("kd_cross") & (pl.col(_stoch_k) < pl.col(_stoch_d)))
                | pl.col("overbought_exit")
            )
            .then(pl.lit(si.SignalDirection.DOWN))
            .when(pl.col(_stoch_k) > self.overbought_threshold)
            .then(pl.lit(si.SignalDirection.OVERBOUGHT))
            .when(pl.col(_stoch_k) < self.oversold_threshold)
            .then(pl.lit(si.SignalDirection.OVERSOLD))
            .when(
                pl.col("k_inflection")
                & (pl.col(_stoch_k) > pl.col(_stoch_k).shift(1))
            )
            .then(pl.lit(si.SignalDirection.MOMENTUM_ACCELERATION))
            .when(
                pl.col("k_inflection")
                & (pl.col(_stoch_k) < pl.col(_stoch_k).shift(1))
            )
            .then(pl.lit(si.SignalDirection.MOMENTUM_DECELERATION))
            .otherwise(pl.lit(si.SignalDirection.UNSPECIFIED))
            .alias(o.CATEGORY)
        ).with_columns(pl.lit(self.name()).alias(o.NAME))

        # Confidence Calculation (0.0 to 1.0):
        # Measures how deeply %K is pushed into directional territory relative to 50 midpoint
        df = df.with_columns(
            pl.when(pl.col(o.CATEGORY) != si.SignalDirection.UNSPECIFIED)
            .then(
                ((pl.col(_stoch_k) - 50.0).abs() / 50.0).clip(0.0, 1.0)
            )
            .otherwise(pl.lit(0.0))
            .alias(o.CONFIDENCE)
        )

        out = df.select(
            *(pl.col(x) for x in [o.CATEGORY, o.CONFIDENCE, o.NAME, o.SYMBOL, o.TS])
        )
        return out



@dataclass()
class TSISignal(si.SignalInterface):
    window_slow: int = field(default=25)
    window_fast: int = field(default=13)

    @override
    def topology(self)->str:
        return "momentum"
    @override
    def name(self) -> str:
        return f"tsi-signal-{self.window_slow}d-{self.window_fast}d"

    @override
    def __call__(
        self,
        df: i.QuotesDf.DataFrame,
        symbol: str,
    ) -> si.SignalDf.DataFrame:
        pdf = df.to_pandas()
        c = i.QuotesDf.Columns
        o = si.SignalDf.Columns

        _tsi = "tsi"
        _tsi_diff = "tsi_diff"

        # Compute TSI via ta library
        tsi_indicator = ta.momentum.TSIIndicator(
            close=pdf[c.CLOSE],
            window_slow=self.window_slow,
            window_fast=self.window_fast,
        )

        tsi_series = pl.Series(tsi_indicator.tsi()).alias(_tsi)
        df = df.insert_column(0, tsi_series)

        # Calculate dynamics: Zero-line crosses, slope inflections, and thresholds
        df = df.with_columns(
            (pl.col(_tsi) - pl.col(_tsi).shift(1)).alias(_tsi_diff),
            # Zero-Line Crossover (Centerline cross indicates trend bias shift)
            (
                (pl.col(_tsi).sign())
                .ne(pl.col(_tsi).shift(1).sign())
                & pl.col(_tsi).shift(1).is_not_null()
            ).alias("zero_cross"),
            # Directional inflection points in TSI slope
            (
                (pl.col(_tsi) - pl.col(_tsi).shift(1)).sign()
                .ne((pl.col(_tsi).shift(1) - pl.col(_tsi).shift(2)).sign())
                & pl.col(_tsi).shift(2).is_not_null()
            ).alias("tsi_inflection"),
        )

        # TSI standard extreme thresholds (bound between -100 and +100, +/-25 typically signals extremes)
        tsi_upper_bound = 25.0
        tsi_lower_bound = -25.0

        # Signal Classification Strategy:
        # 1. Zero-line Cross -> Primary UP / DOWN signal
        # 2. Extreme TSI levels (>25 or <-25) -> OVERBOUGHT / OVERSOLD
        # 3. TSI slope inflection -> MOMENTUM_ACCELERATION / MOMENTUM_DECELERATION
        df = df.with_columns(
            pl.when(pl.col("zero_cross") & (pl.col(_tsi) > 0))
            .then(pl.lit(si.SignalDirection.UP))
            .when(pl.col("zero_cross") & (pl.col(_tsi) < 0))
            .then(pl.lit(si.SignalDirection.DOWN))
            .when(pl.col(_tsi) > tsi_upper_bound)
            .then(pl.lit(si.SignalDirection.OVERBOUGHT))
            .when(pl.col(_tsi) < tsi_lower_bound)
            .then(pl.lit(si.SignalDirection.OVERSOLD))
            .when(pl.col("tsi_inflection") & (pl.col(_tsi_diff) > 0))
            .then(pl.lit(si.SignalDirection.MOMENTUM_ACCELERATION))
            .when(pl.col("tsi_inflection") & (pl.col(_tsi_diff) < 0))
            .then(pl.lit(si.SignalDirection.MOMENTUM_DECELERATION))
            .otherwise(pl.lit(si.SignalDirection.UNSPECIFIED))
            .alias(o.CATEGORY)
        ).with_columns(pl.lit(self.name()).alias(o.NAME))

        # Confidence Calculation (0.0 to 1.0):
        # TSI is naturally bounded between -100 and +100; confidence maps the absolute magnitude relative to maximum span
        df = df.with_columns(
            pl.when(pl.col(o.CATEGORY) != si.SignalDirection.UNSPECIFIED)
            .then(
                (pl.col(_tsi).abs() / 100.0).clip(0.0, 1.0)
            )
            .otherwise(pl.lit(0.0))
            .alias(o.CONFIDENCE)
        )

        out = df.select(
            *(pl.col(x) for x in [o.CATEGORY, o.CONFIDENCE, o.NAME, o.SYMBOL, o.TS])
        )
        return out


@dataclass()
class UltimateOscillatorSignal(si.SignalInterface):
    window1: int = field(default=7)
    window2: int = field(default=14)
    window3: int = field(default=28)
    weight1: float = field(default=4.0)
    weight2: float = field(default=2.0)
    weight3: float = field(default=1.0)
    overbought_threshold: float = field(default=70.0)
    oversold_threshold: float = field(default=30.0)

    @override
    def topology(self)->str:
        return "momentum"
    @override
    def name(self) -> str:
        return f"ultimate-oscillator-{self.window1}d-{self.window2}d-{self.window3}d"

    @override
    def __call__(
        self,
        df: i.QuotesDf.DataFrame,
        symbol: str,
    ) -> si.SignalDf.DataFrame:
        pdf = df.to_pandas()
        c = i.QuotesDf.Columns
        o = si.SignalDf.Columns

        _uo = "uo"
        _uo_diff = "uo_diff"

        # Compute Ultimate Oscillator via ta library
        uo_indicator = ta.momentum.UltimateOscillator(
            high=pdf[c.HIGH],
            low=pdf[c.LOW],
            close=pdf[c.CLOSE],
            window1=self.window1,
            window2=self.window2,
            window3=self.window3,
            weight1=self.weight1,
            weight2=self.weight2,
            weight3=self.weight3,
        )

        uo_series = pl.Series(uo_indicator.ultimate_oscillator()).alias(_uo)
        df = df.insert_column(0, uo_series)

        # Calculate dynamics: Midline crossovers, zone exits, and slope inflections
        df = df.with_columns(
            (pl.col(_uo) - pl.col(_uo).shift(1)).alias(_uo_diff),
            # Midline Crossover (50 level center-line cross)
            (
                (pl.col(_uo) - 50.0).sign()
                .ne((pl.col(_uo).shift(1) - 50.0).sign())
                & pl.col(_uo).shift(1).is_not_null()
            ).alias("midline_cross"),
            # Exiting Oversold/Overbought zones
            (
                (pl.col(_uo).shift(1) < self.oversold_threshold)
                & (pl.col(_uo) >= self.oversold_threshold)
            ).alias("oversold_exit"),
            (
                (pl.col(_uo).shift(1) > self.overbought_threshold)
                & (pl.col(_uo) <= self.overbought_threshold)
            ).alias("overbought_exit"),
            # Directional inflection points in UO slope
            (
                (pl.col(_uo) - pl.col(_uo).shift(1)).sign()
                .ne((pl.col(_uo).shift(1) - pl.col(_uo).shift(2)).sign())
                & pl.col(_uo).shift(2).is_not_null()
            ).alias("uo_inflection"),
        )

        # Signal Classification Strategy:
        # 1. Midline cross (50 level) or Zone Exits -> Primary UP / DOWN signal
        # 2. Extreme UO levels (>70 or <30) -> OVERBOUGHT / OVERSOLD
        # 3. UO slope inflection -> MOMENTUM_ACCELERATION / MOMENTUM_DECELERATION
        df = df.with_columns(
            pl.when(
                (pl.col("midline_cross") & (pl.col(_uo) > 50.0))
                | pl.col("oversold_exit")
            )
            .then(pl.lit(si.SignalDirection.UP))
            .when(
                (pl.col("midline_cross") & (pl.col(_uo) < 50.0))
                | pl.col("overbought_exit")
            )
            .then(pl.lit(si.SignalDirection.DOWN))
            .when(pl.col(_uo) > self.overbought_threshold)
            .then(pl.lit(si.SignalDirection.OVERBOUGHT))
            .when(pl.col(_uo) < self.oversold_threshold)
            .then(pl.lit(si.SignalDirection.OVERSOLD))
            .when(pl.col("uo_inflection") & (pl.col(_uo_diff) > 0))
            .then(pl.lit(si.SignalDirection.MOMENTUM_ACCELERATION))
            .when(pl.col("uo_inflection") & (pl.col(_uo_diff) < 0))
            .then(pl.lit(si.SignalDirection.MOMENTUM_DECELERATION))
            .otherwise(pl.lit(si.SignalDirection.UNSPECIFIED))
            .alias(o.CATEGORY)
        ).with_columns(pl.lit(self.name()).alias(o.NAME))

        # Confidence Calculation (0.0 to 1.0):
        # Ultimate Oscillator is naturally bounded between 0 and 100;
        # confidence maps the absolute distance from the neutral 50 midpoint.
        df = df.with_columns(
            pl.when(pl.col(o.CATEGORY) != si.SignalDirection.UNSPECIFIED)
            .then(
                ((pl.col(_uo) - 50.0).abs() / 50.0).clip(0.0, 1.0)
            )
            .otherwise(pl.lit(0.0))
            .alias(o.CONFIDENCE)
        )

        out = df.select(
            *(pl.col(x) for x in [o.CATEGORY, o.CONFIDENCE, o.NAME, o.SYMBOL, o.TS])
        )
        return out




@dataclass()
class WilliamsRSignal(si.SignalInterface):
    lbp: int = field(default=14)
    overbought_threshold: float = field(default=-20.0)
    oversold_threshold: float = field(default=-80.0)

    @override
    def topology(self)->str:
        return "momentum"
    @override
    def name(self) -> str:
        return f"williams-r-{self.lbp}d"


    @override
    def __call__(
        self,
        df: i.QuotesDf.DataFrame,
        symbol: str,
    ) -> si.SignalDf.DataFrame:
        pdf = df.to_pandas()
        c = i.QuotesDf.Columns
        o = si.SignalDf.Columns

        _williams_r = "williams_r"
        _wr_diff = "wr_diff"

        # Compute Williams %R via ta library
        wr_indicator = ta.momentum.WilliamsRIndicator(
            high=pdf[c.HIGH],
            low=pdf[c.LOW],
            close=pdf[c.CLOSE],
            lbp=self.lbp,
        )

        wr_series = pl.Series(wr_indicator.williams_r()).alias(_williams_r)
        df = df.insert_column(0, wr_series)

        # Calculate dynamics: Midline cross (-50), zone exits, and slope inflections
        df = df.with_columns(
            (pl.col(_williams_r) - pl.col(_williams_r).shift(1)).alias(_wr_diff),
            # Midline Crossover (-50 level center-line cross)
            (
                (pl.col(_williams_r) - (-50.0)).sign()
                .ne((pl.col(_williams_r).shift(1) - (-50.0)).sign())
                & pl.col(_williams_r).shift(1).is_not_null()
            ).alias("midline_cross"),
            # Exiting Oversold/Overbought zones
            (
                (pl.col(_williams_r).shift(1) < self.oversold_threshold)
                & (pl.col(_williams_r) >= self.oversold_threshold)
            ).alias("oversold_exit"),
            (
                (pl.col(_williams_r).shift(1) > self.overbought_threshold)
                & (pl.col(_williams_r) <= self.overbought_threshold)
            ).alias("overbought_exit"),
            # Directional inflection points in Williams %R slope
            (
                (pl.col(_williams_r) - pl.col(_williams_r).shift(1)).sign()
                .ne((pl.col(_williams_r).shift(1) - pl.col(_williams_r).shift(2)).sign())
                & pl.col(_williams_r).shift(2).is_not_null()
            ).alias("wr_inflection"),
        )

        # Signal Classification Strategy:
        # 1. Midline cross (-50 level) or Zone Exits -> Primary UP / DOWN signal
        # 2. Extreme Williams %R levels (>-20 or <-80) -> OVERBOUGHT / OVERSOLD
        # 3. Slope inflection -> MOMENTUM_ACCELERATION / MOMENTUM_DECELERATION
        df = df.with_columns(
            pl.when(
                (pl.col("midline_cross") & (pl.col(_williams_r) > -50.0))
                | pl.col("oversold_exit")
            )
            .then(pl.lit(si.SignalDirection.UP))
            .when(
                (pl.col("midline_cross") & (pl.col(_williams_r) < -50.0))
                | pl.col("overbought_exit")
            )
            .then(pl.lit(si.SignalDirection.DOWN))
            .when(pl.col(_williams_r) > self.overbought_threshold)
            .then(pl.lit(si.SignalDirection.OVERBOUGHT))
            .when(pl.col(_williams_r) < self.oversold_threshold)
            .then(pl.lit(si.SignalDirection.OVERSOLD))
            .when(pl.col("wr_inflection") & (pl.col(_wr_diff) > 0))
            .then(pl.lit(si.SignalDirection.MOMENTUM_ACCELERATION))
            .when(pl.col("wr_inflection") & (pl.col(_wr_diff) < 0))
            .then(pl.lit(si.SignalDirection.MOMENTUM_DECELERATION))
            .otherwise(pl.lit(si.SignalDirection.UNSPECIFIED))
            .alias(o.CATEGORY)
        ).with_columns(pl.lit(self.name()).alias(o.NAME))

        # Confidence Calculation (0.0 to 1.0):
        # Williams %R is bounded between -100 and 0 with a neutral midpoint of -50.
        df = df.with_columns(
            pl.when(pl.col(o.CATEGORY) != si.SignalDirection.UNSPECIFIED)
            .then(
                ((pl.col(_williams_r) - (-50.0)).abs() / 50.0).clip(0.0, 1.0)
            )
            .otherwise(pl.lit(0.0))
            .alias(o.CONFIDENCE)
        )

        out = df.select(
            *(pl.col(x) for x in [o.CATEGORY, o.CONFIDENCE, o.NAME, o.SYMBOL, o.TS])
        )
        return out
