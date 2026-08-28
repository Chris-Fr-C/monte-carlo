from dataclasses import dataclass, field
from typing import override
import numpy as np
import pandas as pd
import fintools.signals.interface as si
import pendulum
import fintools.interface as i

import ta.volatility
import polars as pl


from dataclasses import dataclass, field
from typing import override
import polars as pl
import ta.volatility



@dataclass
class AverageTrueRange(si.SignalInterface):
    """Calculates Average True Range (ATR) volatility expansion and contraction signals.

    This signal measures relative volatility by expressing the ATR as a percentage
    of the closing price. It identifies volatility expansions when relative ATR
    crosses above its historical moving average and contractions when it crosses
    below.

    Attributes:
        window (int): The lookback period for the ATR calculation. Defaults to 14.
        sma_window (int): The moving average window used to determine the relative
            ATR threshold. Defaults to 20.
    """

    window: int = field(default=14)
    sma_window: int = field(default=20)

    @override
    def topology(self) -> str:
        """Returns the signal classification category.

        Returns:
            str: "volatility" topology classification.
        """
        return "volatility"

    @override
    def name(self) -> str:
        """Generates a unique identifier for the configured signal parameters.

        Returns:
            str: Formatted string specifying the window parameters.
        """
        return f"atr-{self.window}d-sma-{self.sma_window}d"

    @override
    def __call__(
        self,
        df: i.QuotesDf.DataFrame,
        symbol: str,
    ) -> si.SignalDf.DataFrame:
        """Executes the signal calculation on provided OHLCV quote data.

        Args:
            df (i.QuotesDf.DataFrame): Polars dataframe containing quote data.
            symbol (str): Ticker symbol associated with the quotes.

        Returns:
            si.SignalDf.DataFrame: Polars dataframe formatted with standard signal columns
                including category, confidence, name, symbol, and timestamp.
        """
        pdf = df.to_pandas()
        c = i.QuotesDf.Columns
        o = si.SignalDf.Columns

        _rel_atr = "rel_atr"
        _atr_sma = "atr_sma"

        # Calculate base ATR via ta library
        raw_atr = ta.volatility.average_true_range(
            high=pdf[c.HIGH],
            low=pdf[c.LOW],
            close=pdf[c.CLOSE],
            window=self.window,
        )

        # Express ATR as percentage of price to normalize across assets/price ranges
        rel_atr_series = (pl.Series(raw_atr) / pl.Series(pdf[c.CLOSE])).alias(_rel_atr)

        df = df.insert_column(0, rel_atr_series)
        df = df.with_columns(
            pl.col(_rel_atr).rolling_mean(window_size=self.sma_window).alias(_atr_sma)
        )

        # Detect crossover signals relative to the moving average
        df = df.with_columns(
            (
                (pl.col(_rel_atr) - pl.col(_atr_sma))
                .sign()
                .ne((pl.col(_rel_atr).shift(1) - pl.col(_atr_sma).shift(1)).sign())
            ).alias("sign_change"),
            ((pl.col(_rel_atr) - pl.col(_atr_sma)).sign()).alias("delta_sign"),
        )

        sign_changed = pl.col("sign_change") > 0

        # Classify signal category based on direction of ATR relative to its SMA
        df = df.with_columns(
            pl.when(sign_changed & (pl.col("delta_sign") > 0))
            .then(pl.lit(si.SignalDirection.VOLATILITY_EXPANSION))
            .when(sign_changed & (pl.col("delta_sign") < 0))
            .then(pl.lit(si.SignalDirection.VOLATILITY_CONTRACTION))
            .otherwise(pl.lit(si.SignalDirection.UNSPECIFIED))
            .alias(o.CATEGORY)
        ).with_columns(pl.lit(self.name()).alias(o.NAME))

        # Confidence: Absolute distance between relative ATR and its SMA, bounded to [0.0, 1.0]
        df = df.with_columns(
            pl.when(pl.col(o.CATEGORY) != si.SignalDirection.UNSPECIFIED)
            .then(
                ((pl.col(_rel_atr) - pl.col(_atr_sma)).abs() / pl.col(_atr_sma)).clip(
                    0.0, 1.0
                )
            )
            .otherwise(pl.lit(0.0))
            .alias(o.CONFIDENCE)
        )

        out = df.select(
            *(pl.col(x) for x in [o.CATEGORY, o.CONFIDENCE, o.NAME, o.SYMBOL, o.TS])
        )
        return out



@dataclass()
class BollingerBandsCrossing(si.SignalInterface):
    window: int = field(default=20)
    window_dev: int = field(default=2)

    @override
    def topology(self) -> str:
        """Returns the signal classification category.

        Returns:
            str: "volatility" topology classification.
        """
        return "volatility"
    @override
    def name(self) -> str:
        return f"bb-crossing-{self.window}d-{self.window_dev}std"

    @override
    def __call__(
        self,
        df: i.QuotesDf.DataFrame,
        symbol: str,
    ) -> si.SignalDf.DataFrame:
        pdf = df.to_pandas()
        c = i.QuotesDf.Columns
        o = si.SignalDf.Columns
        _bb_h = "bb_hband"
        _bb_l = "bb_lband"

        # Calculate Bollinger Bands (upper, lower, and middle band)
        bb_indicator = ta.volatility.BollingerBands(
            close=pdf[c.CLOSE],
            window=self.window,
            window_dev=self.window_dev,
        )
        bb_h_series = pl.Series(bb_indicator.bollinger_hband()).alias(_bb_h)
        bb_l_series = pl.Series(bb_indicator.bollinger_lband()).alias(_bb_l)

        df = df.insert_column(0, bb_h_series).insert_column(0, bb_l_series)

        # Reversal signals:
        # UP: Price crosses back above the Lower Band (rebounding from oversold)
        # DOWN: Price crosses back below the Upper Band (reversing from overbought)
        close_prev = pl.col(c.CLOSE).shift(1)
        close_curr = pl.col(c.CLOSE)

        cross_above_lower = (close_prev <= pl.col(_bb_l).shift(1)) & (close_curr > pl.col(_bb_l))
        cross_below_upper = (close_prev >= pl.col(_bb_h).shift(1)) & (close_curr < pl.col(_bb_h))

        df = df.with_columns(
            pl.when(cross_above_lower)
            .then(pl.lit(si.SignalDirection.UP))
            .when(cross_below_upper)
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
class DonchianChannelCrossing(si.SignalInterface):
    window: int = field(default=20)
    offset: int = field(default=0)

    @override
    def topology(self) -> str:
        """Returns the signal classification category.

        Returns:
            str: "volatility" topology classification.
        """
        return "volatility"
    @override
    def name(self) -> str:
        return f"donchian-crossing-{self.window}d"

    @override
    def __call__(
        self,
        df: i.QuotesDf.DataFrame,
        symbol: str,
    ) -> si.SignalDf.DataFrame:
        pdf = df.to_pandas()
        c = i.QuotesDf.Columns
        o = si.SignalDf.Columns
        _dc_h = "dc_hband"
        _dc_l = "dc_lband"

        # Calculate Donchian Channel (Upper and Lower bands)
        dc_indicator = ta.volatility.DonchianChannel(
            high=pdf[c.HIGH],
            low=pdf[c.LOW],
            close=pdf[c.CLOSE],
            window=self.window,
            offset=self.offset,
        )
        dc_h_series = pl.Series(dc_indicator.donchian_channel_hband()).alias(_dc_h)
        dc_l_series = pl.Series(dc_indicator.donchian_channel_lband()).alias(_dc_l)

        df = df.insert_column(0, dc_h_series).insert_column(0, dc_l_series)

        # Breakout signals:
        # UP: Close price crosses above upper Donchian Channel (bullish breakout)
        # DOWN: Close price crosses below lower Donchian Channel (bearish breakout)
        close_prev = pl.col(c.CLOSE).shift(1)
        close_curr = pl.col(c.CLOSE)

        breakout_up = (close_prev < pl.col(_dc_h).shift(1)) & (close_curr >= pl.col(_dc_h))
        breakout_down = (close_prev > pl.col(_dc_l).shift(1)) & (close_curr <= pl.col(_dc_l))

        df = df.with_columns(
            pl.when(breakout_up)
            .then(pl.lit(si.SignalDirection.UP))
            .when(breakout_down)
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
class KeltnerChannelCrossing(si.SignalInterface):
    window: int = field(default=20)
    window_atr: int = field(default=10)
    original_version: bool = field(default=True)
    multiplier: float = field(default=2.0)

    @override
    def topology(self) -> str:
        """Returns the signal classification category.

        Returns:
            str: "volatility" topology classification.
        """
        return "volatility"
    @override
    def name(self) -> str:
        return f"keltner-crossing-{self.window}d-{self.window_atr}atr"

    @override
    def __call__(
        self,
        df: i.QuotesDf.DataFrame,
        symbol: str,
    ) -> si.SignalDf.DataFrame:
        pdf = df.to_pandas()
        c = i.QuotesDf.Columns
        o = si.SignalDf.Columns
        _kc_h = "kc_hband"
        _kc_l = "kc_lband"

        # Calculate Keltner Channel (Upper and Lower Bands)
        kc_indicator = ta.volatility.KeltnerChannel(
            high=pdf[c.HIGH],
            low=pdf[c.LOW],
            close=pdf[c.CLOSE],
            window=self.window,
            window_atr=self.window_atr,
            original_version=self.original_version,
            multiplier=self.multiplier,
        )
        kc_h_series = pl.Series(kc_indicator.keltner_channel_hband()).alias(_kc_h)
        kc_l_series = pl.Series(kc_indicator.keltner_channel_lband()).alias(_kc_l)

        df = df.insert_column(0, kc_h_series).insert_column(0, kc_l_series)

        # Reversal / Mean-Reversion Signals:
        # UP: Price crosses back above Lower Band (rebounding from oversold)
        # DOWN: Price crosses back below Upper Band (reversing from overbought)
        close_prev = pl.col(c.CLOSE).shift(1)
        close_curr = pl.col(c.CLOSE)

        cross_above_lower = (close_prev <= pl.col(_kc_l).shift(1)) & (close_curr > pl.col(_kc_l))
        cross_below_upper = (close_prev >= pl.col(_kc_h).shift(1)) & (close_curr < pl.col(_kc_h))

        df = df.with_columns(
            pl.when(cross_above_lower)
            .then(pl.lit(si.SignalDirection.UP))
            .when(cross_below_upper)
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
class UlcerIndexCrossing(si.SignalInterface):
    window: int = field(default=14)
    threshold: float = field(default=5.0)

    @override
    def topology(self) -> str:
        """Returns the signal classification category.

        Returns:
            str: "volatility" topology classification.
        """
        return "volatility"
    @override
    def name(self) -> str:
        return f"ulcer-index-crossing-{self.window}d-{int(self.threshold)}"

    @override
    def __call__(
        self,
        df: i.QuotesDf.DataFrame,
        symbol: str,
    ) -> si.SignalDf.DataFrame:
        pdf = df.to_pandas()
        c = i.QuotesDf.Columns
        o = si.SignalDf.Columns
        _ui = "ulcer_index"

        # Calculate Ulcer Index (downside risk/volatility indicator)
        ui_indicator = ta.volatility.UlcerIndex(
            close=pdf[c.CLOSE],
            window=self.window,
        )
        ui_series = pl.Series(ui_indicator.ulcer_index()).alias(_ui)

        df = df.insert_column(0, ui_series)

        # Signal logic:
        # UP (Bullish): Ulcer Index drops below risk threshold (downside stress receding)
        # DOWN (Bearish): Ulcer Index rises above risk threshold (downside risk spiking)
        ui_prev = pl.col(_ui).shift(1)
        ui_curr = pl.col(_ui)

        risk_receding = (ui_prev >= self.threshold) & (ui_curr < self.threshold)
        risk_spiking = (ui_prev <= self.threshold) & (ui_curr > self.threshold)

        df = df.with_columns(
            pl.when(risk_receding)
            .then(pl.lit(si.SignalDirection.UP))
            .when(risk_spiking)
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
