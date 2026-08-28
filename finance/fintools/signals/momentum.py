from dataclasses import dataclass, field
from typing import override
import numpy as np
import pandas as pd
import fintools.signals.interface as si
import pendulum
import fintools.interface as i

import ta.trend
import polars as pl


@dataclass()
class AwesomeOscillatorCrossing(si.SignalInterface):
    """
    code: https://technical-analysis-library-in-python.readthedocs.io/en/latest/ta.html#ta.momentum.AwesomeOscillatorIndicator
    description: https://www.ifcm.co.uk/ntx-indicators/awesome-oscillator

     The AO indicator is a good indicator for measuring the market dynamics,
     it reflects specific changes in the driving force of the market,
     which helps to identify the strength of the trend, including the points of its formation and reversal.
    """

    fast_period: int = field(default=5)
    slow_period: int = field(default=34)

    @override
    def name(self) -> str:
        return f"ao-crossing-{self.fast_period}d-{self.slow_period}d"

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

        # Calculate Awesome Oscillator via ta library
        ao_indicator = ta.momentum.AwesomeOscillatorIndicator(
            high=pdf[c.HIGH],
            low=pdf[c.LOW],
            window1=self.fast_period,
            window2=self.slow_period,
        )
        ao_series = pl.Series(ao_indicator.awesome_oscillator()).alias(_ao)

        df = df.insert_column(0, ao_series)

        # Detect zero-line crossings using sign changes
        df = df.with_columns(
            (pl.col(_ao).sign().ne(pl.col(_ao).shift(1).sign())).alias("sign_change"),
            pl.col(_ao).sign().alias("delta_sign"),
        )

        sign_changed = pl.col("sign_change") > 0

        # UP when AO crosses from negative to positive; DOWN when AO crosses from positive to negative
        df = df.with_columns(
            pl.when(sign_changed & (pl.col("delta_sign") > 0))
            .then(pl.lit(si.SignalDirection.UP))
            .when(sign_changed & (pl.col("delta_sign") < 0))
            .then(pl.lit(si.SignalDirection.DOWN))
            .otherwise(pl.lit(si.SignalDirection.UNSPECIFIED))
            .alias(o.CATEGORY)
        ).with_columns(pl.lit(self.name()).alias(o.NAME))

        df = df.with_columns(
            pl.lit(1.0).alias(o.CONFIDENCE),
        )

        out = df.select(
            *(pl.col(x) for x in [o.CATEGORY, o.CONFIDENCE, o.NAME, o.SYMBOL, o.TS])
        )
        return out


@dataclass()
class KAMACrossing(si.SignalInterface):
    window: int = field(default=10)
    pow1: int = field(default=2)
    pow2: int = field(default=30)

    @override
    def name(self) -> str:
        return f"kama-crossing-{self.window}d-{self.pow1}-{self.pow2}"

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

        # Calculate Kaufman's Adaptive Moving Average (KAMA)
        kama_indicator = ta.momentum.KAMAIndicator(
            close=pdf[c.CLOSE],
            window=self.window,
            pow1=self.pow1,
            pow2=self.pow2,
        )
        kama_series = pl.Series(kama_indicator.kama()).alias(_kama)

        df = df.insert_column(0, kama_series)

        # Calculate difference between price and KAMA to identify crossings
        df = df.with_columns(
            (pl.col(c.CLOSE) - pl.col(_kama)).alias("diff")
        )

        df = df.with_columns(
            (
                pl.col("diff").sign()
                .ne(pl.col("diff").shift(1).sign())
            ).alias("sign_change"),
            pl.col("diff").sign().alias("delta_sign"),
        )

        sign_changed = pl.col("sign_change") > 0

        # UP when Close crosses above KAMA; DOWN when Close crosses below KAMA
        df = df.with_columns(
            pl.when(sign_changed & (pl.col("delta_sign") > 0))
            .then(pl.lit(si.SignalDirection.UP))
            .when(sign_changed & (pl.col("delta_sign") < 0))
            .then(pl.lit(si.SignalDirection.DOWN))
            .otherwise(pl.lit(si.SignalDirection.UNSPECIFIED))
            .alias(o.CATEGORY)
        ).with_columns(pl.lit(self.name()).alias(o.NAME))

        df = df.with_columns(
            pl.lit(1.0).alias(o.CONFIDENCE),
        )

        out = df.select(
            *(pl.col(x) for x in [o.CATEGORY, o.CONFIDENCE, o.NAME, o.SYMBOL, o.TS])
        )
        return out
