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
class EMACrossing(si.SignalInterface):
    slow_period_days: int = field(default=14)
    fast_period_days: int = field(default=7)

    @override
    def name(self) -> str:
        return f"ema-crossing-{self.fast_period_days}d-{self.slow_period_days}d"

    @override
    def __call__(
        self,
        df: i.QuotesDf.DataFrame,
        symbol: str,
    ) -> si.SignalDf.DataFrame:
        pdf = df.to_pandas()
        c = i.QuotesDf.Columns
        o = si.SignalDf.Columns
        _slow = "slow"
        _fast = "fast"
        slow = pl.Series(
            ta.trend.ema_indicator(close=pdf[c.CLOSE], window=self.slow_period_days)
        ).alias(_slow)
        fast = pl.Series(
            ta.trend.ema_indicator(close=pdf[c.CLOSE], window=self.fast_period_days)
        ).alias(_fast)

        df = df.insert_column(0, slow).insert_column(0, fast)
        df = df.with_columns(
            (
                (pl.col(_fast) - pl.col(_slow)).sign()
                != (pl.col(_fast).shift(1) - pl.col(_slow).shift(1)).sign()
            ).alias("sign_change")
        )
        df = df.with_columns(
            ((pl.col(_fast) - pl.col(_slow)) > 0).alias("fast_goes_up")
        )
        # Default
        df = df.with_columns(
            pl.when((pl.col("sign_change")>0) & (pl.col("fast_goes_up")>0)).then(
                pl.lit(si.SignalDirection.UP)
            ).when(
                (pl.col("sign_change")>0) & (pl.col("fast_goes_up")<0)).then(
                pl.lit(si.SignalDirection.DOWN)
            ).otherwise(
                pl.lit(si.SignalDirection.UNSPECIFIED)
            ).alias(o.CATEGORY)
        ).with_columns(
                pl.lit(self.name()).alias(o.NAME)
        )
        # TODO: Select how to compute the confience (the slope seems a meh idea)
        df= df.with_columns(
            pl.lit(1.0).alias(o.CONFIDENCE),
        )
        return df.select(
            *(pl.col(x) for x in [o.CATEGORY, o.CONFIDENCE, o.NAME, o.SYMBOL, o.TS])
        )
        exit(244)
