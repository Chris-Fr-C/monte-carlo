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
class ADXSignal(si.SignalInterface):
    """Generates directional and volatility signals based on the Average Directional Index (ADX).

    This class computes the ADX alongside the positive (+DI) and negative (-DI)
    directional indicators using the `ta` library. It determines market signal directions
    (UP, DOWN, or UNSPECIFIED) based on directional index crossovers and calculates signal
    confidence normalized between 0.0 and 1.0 based on the underlying ADX trend strength.

    Attributes:
        window (int): The time period window used for ADX calculation. Defaults to 14.
        threshold (float): Minimum ADX value required to consider the market in a
            strong trend. Defaults to 25.0.
    """

    window: int = field(default=14)
    threshold: float = field(default=25.0)

    @override
    def topology(self)->str:
        return "trend"

    @override
    def name(self) -> str:
        """Generates the unique identifier string for this signal instance.

        Returns:
            str: Signal name formatted as 'adx-w{window}-t{threshold}'.
        """
        return f"adx-w{self.window}-t{int(self.threshold)}"

    @override
    def __call__(
        self,
        df: i.QuotesDf.DataFrame,
        symbol: str,
    ) -> si.SignalDf.DataFrame:
        """Executes the ADX signal calculation pipeline over stock quote data.

        Calculates +DI, -DI, and ADX metrics, identifies directional crossover
        events, assigns corresponding signal directions, and scales the confidence
        score according to trend strength.

        Args:
            df (i.QuotesDf.DataFrame): The input quotes DataFrame containing High, Low,
                and Close price series.
            symbol (str): Ticker or symbol string corresponding to the quotes data.

        Returns:
            si.SignalDf.DataFrame: A Polars DataFrame containing the computed signal
                columns (CATEGORY, CONFIDENCE, NAME, SYMBOL, TS).
        """
        pdf = df.to_pandas()
        c = i.QuotesDf.Columns
        o = si.SignalDf.Columns

        _adx = "adx"
        _pos_di = "pos_di"
        _neg_di = "neg_di"

        # Initialize technical indicator
        indicator = ta.trend.ADXIndicator(
            high=pdf[c.HIGH],
            low=pdf[c.LOW],
            close=pdf[c.CLOSE],
            window=self.window,
        )

        adx_series = pl.Series(indicator.adx()).alias(_adx)
        pos_di_series = pl.Series(indicator.adx_pos()).alias(_pos_di)
        neg_di_series = pl.Series(indicator.adx_neg()).alias(_neg_di)

        df = df.insert_column(0, adx_series).insert_column(0, pos_di_series).insert_column(0, neg_di_series)

        # Crossover Detection between +DI and -DI
        df = df.with_columns(
            (
                (pl.col(_pos_di) - pl.col(_neg_di))
                .sign()
                .ne((pl.col(_pos_di).shift(1) - pl.col(_neg_di).shift(1)).sign())
            ).alias("sign_change"),
            ((pl.col(_pos_di) - pl.col(_neg_di)).sign()).alias("delta_sign"),
        )

        sign_changed = pl.col("sign_change") > 0

        # Signal Direction Logic:
        # Crossover +DI > -DI -> UP
        # Crossover -DI > +DI -> DOWN
        df = df.with_columns(
            pl.when(sign_changed & (pl.col("delta_sign") > 0))
            .then(pl.lit(si.SignalDirection.UP))
            .when(sign_changed & (pl.col("delta_sign") < 0))
            .then(pl.lit(si.SignalDirection.DOWN))
            .otherwise(pl.lit(si.SignalDirection.UNSPECIFIED))
            .alias(o.CATEGORY)
        ).with_columns(pl.lit(self.name()).alias(o.NAME))

        # Confidence Calculation:
        # Normalized ADX bounded in range [0.0, 1.0].
        # ADX values typically range up to 50-75 (values over 50 indicate extreme trends).
        df = df.with_columns(
            pl.col(_adx)
            .fill_null(0.0)
            .clip(0.0, 75.0)
            .truediv(75.0)
            .alias(o.CONFIDENCE)
        )

        out = df.select(
            *(pl.col(x) for x in [o.CATEGORY, o.CONFIDENCE, o.NAME, o.SYMBOL, o.TS])
        )
        return out

@dataclass()
class AroonSignal(si.SignalInterface):
    """Generates directional trend signals using the Aroon Indicator.

    This class computes Aroon Up and Aroon Down indicators to identify
    the emergence of new directional trends and measure trend strength.
    Directional signals (UP, DOWN, or UNSPECIFIED) are triggered on line
    crossovers, while confidence is derived from the absolute magnitude
    of the Aroon Oscillator (Aroon Up - Aroon Down) normalized between 0.0 and 1.0.

    Attributes:
        window (int): The lookback period window used for Aroon calculations. Defaults to 25.
    """

    window: int = field(default=25)
    @override
    def topology(self)->str:
        return "trend"

    @override
    def name(self) -> str:
        """Generates the unique identifier string for this signal instance.

        Returns:
            str: Signal name formatted as 'aroon-{window}d'.
        """
        return f"aroon-{self.window}d"

    @override
    def __call__(
        self,
        df: i.QuotesDf.DataFrame,
        symbol: str,
    ) -> si.SignalDf.DataFrame:
        """Executes the Aroon signal calculation pipeline over stock quote data.

        Calculates Aroon Up and Aroon Down lines, identifies crossover
        events to trigger directional signals, and computes trend confidence
        based on the absolute spread between the up and down components.

        Args:
            df (i.QuotesDf.DataFrame): The input quotes DataFrame containing High and Low price series.
            symbol (str): Ticker or symbol string corresponding to the quotes data.

        Returns:
            si.SignalDf.DataFrame: A Polars DataFrame containing the computed signal
                columns (CATEGORY, CONFIDENCE, NAME, SYMBOL, TS).
        """
        pdf = df.to_pandas()
        c = i.QuotesDf.Columns
        o = si.SignalDf.Columns

        _aroon_up = "aroon_up"
        _aroon_down = "aroon_down"

        # Initialize technical indicator
        indicator = ta.trend.AroonIndicator(
            high=pdf[c.HIGH],
            low=pdf[c.LOW],
            window=self.window,
        )

        aroon_up_series = pl.Series(indicator.aroon_up()).alias(_aroon_up)
        aroon_down_series = pl.Series(indicator.aroon_down()).alias(_aroon_down)

        df = df.insert_column(0, aroon_up_series).insert_column(0, aroon_down_series)

        # Crossover Detection between Aroon Up and Aroon Down
        df = df.with_columns(
            (
                (pl.col(_aroon_up) - pl.col(_aroon_down))
                .sign()
                .ne((pl.col(_aroon_up).shift(1) - pl.col(_aroon_down).shift(1)).sign())
            ).alias("sign_change"),
            ((pl.col(_aroon_up) - pl.col(_aroon_down)).sign()).alias("delta_sign"),
        )

        sign_changed = pl.col("sign_change") > 0

        # Signal Direction Logic:
        # Crossover Aroon Up > Aroon Down -> UP
        # Crossover Aroon Down > Aroon Up -> DOWN
        df = df.with_columns(
            pl.when(sign_changed & (pl.col("delta_sign") > 0))
            .then(pl.lit(si.SignalDirection.UP))
            .when(sign_changed & (pl.col("delta_sign") < 0))
            .then(pl.lit(si.SignalDirection.DOWN))
            .otherwise(pl.lit(si.SignalDirection.UNSPECIFIED))
            .alias(o.CATEGORY)
        ).with_columns(pl.lit(self.name()).alias(o.NAME))

        # Confidence Calculation:
        # Computed using normalized Aroon Oscillator |Aroon Up - Aroon Down| / 100.0.
        # Max difference is 100 (high confidence), min difference is 0 (low confidence).
        df = df.with_columns(
            (pl.col(_aroon_up) - pl.col(_aroon_down))
            .abs()
            .fill_null(0.0)
            .truediv(100.0)
            .clip(0.0, 1.0)
            .alias(o.CONFIDENCE)
        )

        out = df.select(
            *(pl.col(x) for x in [o.CATEGORY, o.CONFIDENCE, o.NAME, o.SYMBOL, o.TS])
        )
        return out

@dataclass()
class CCISignal(si.SignalInterface):
    """Generates directional, overbought, and oversold signals using the Commodity Channel Index (CCI).

    This class computes the CCI to detect cyclical trends and momentum extremes.
    - Directional crossovers across the zero line trigger UP or DOWN signals.
    - Extreme threshold crossings (+100 / -100) trigger OVERBOUGHT or OVERSOLD signals.
    - Signal confidence is normalized between 0.0 and 1.0 based on the absolute
      magnitude of the CCI value relative to an extreme limit.

    Attributes:
        window (int): The lookback period window used for SMA and mean deviation. Defaults to 20.
        constant (float): The scaling constant factor. Defaults to 0.015.
        overbought_threshold (float): Positive CCI level defining overbought conditions. Defaults to 100.0.
        oversold_threshold (float): Negative CCI level defining oversold conditions. Defaults to -100.0.
    """

    window: int = field(default=20)
    constant: float = field(default=0.015)
    overbought_threshold: float = field(default=100.0)
    oversold_threshold: float = field(default=-100.0)

    @override
    def topology(self)->str:
        return "trend"
    @override
    def name(self) -> str:
        """Generates the unique identifier string for this signal instance.

        Returns:
            str: Signal name formatted as 'cci-w{window}'.
        """
        return f"cci-w{self.window}"

    @override
    def __call__(
        self,
        df: i.QuotesDf.DataFrame,
        symbol: str,
    ) -> si.SignalDf.DataFrame:
        """Executes the CCI signal calculation pipeline over stock quote data.

        Calculates the Commodity Channel Index, evaluates zero-line crossovers for
        directional trends and threshold crossings for momentum extremes, and normalizes
        the confidence metric based on the scaled distance from the baseline.

        Args:
            df (i.QuotesDf.DataFrame): The input quotes DataFrame containing High, Low,
                and Close price series.
            symbol (str): Ticker or symbol string corresponding to the quotes data.

        Returns:
            si.SignalDf.DataFrame: A Polars DataFrame containing the computed signal
                columns (CATEGORY, CONFIDENCE, NAME, SYMBOL, TS).
        """
        pdf = df.to_pandas()
        c = i.QuotesDf.Columns
        o = si.SignalDf.Columns

        _cci = "cci"

        # Initialize technical indicator
        indicator = ta.trend.CCIIndicator(
            high=pdf[c.HIGH],
            low=pdf[c.LOW],
            close=pdf[c.CLOSE],
            window=self.window,
            constant=self.constant,
        )

        cci_series = pl.Series(indicator.cci()).alias(_cci)
        df = df.insert_column(0, cci_series)

        # Crossover Detection relative to 0 (Zero-line crossover)
        df = df.with_columns(
            (
                pl.col(_cci)
                .sign()
                .ne(pl.col(_cci).shift(1).sign())
            ).alias("zero_cross"),
            pl.col(_cci).sign().alias("cci_sign"),
        )

        zero_crossed = pl.col("zero_cross") > 0

        # Signal Direction & Momentum Logic:
        # 1. Overbought / Oversold conditions on threshold breaches
        # 2. Crossovers above zero -> UP
        # 3. Crossovers below zero -> DOWN
        df = df.with_columns(
            pl.when(pl.col(_cci) >= self.overbought_threshold)
            .then(pl.lit(si.SignalDirection.OVERBOUGHT))
            .when(pl.col(_cci) <= self.oversold_threshold)
            .then(pl.lit(si.SignalDirection.OVERSOLD))
            .when(zero_crossed & (pl.col("cci_sign") > 0))
            .then(pl.lit(si.SignalDirection.UP))
            .when(zero_crossed & (pl.col("cci_sign") < 0))
            .then(pl.lit(si.SignalDirection.DOWN))
            .otherwise(pl.lit(si.SignalDirection.UNSPECIFIED))
            .alias(o.CATEGORY)
        ).with_columns(pl.lit(self.name()).alias(o.NAME))

        # Confidence Calculation:
        # CCI typically fluctuates between -200 and +200.
        # Absolute CCI normalized against a cap of 200.0 bounds confidence in [0.0, 1.0].
        df = df.with_columns(
            pl.col(_cci)
            .abs()
            .fill_null(0.0)
            .clip(0.0, 200.0)
            .truediv(200.0)
            .alias(o.CONFIDENCE)
        )

        out = df.select(
            *(pl.col(x) for x in [o.CATEGORY, o.CONFIDENCE, o.NAME, o.SYMBOL, o.TS])
        )
        return out



@dataclass()
class DPOSignal(si.SignalInterface):
    """Generates directional trend signals using the Detrended Price Oscillator (DPO).

    This class computes the DPO to isolate short-term cycles from long-term trends
    by removing a centered moving average.
    - Zero-line crossovers trigger UP (bullish shift) or DOWN (bearish shift) directional signals.
    - Signal confidence is computed by normalizing the absolute DPO relative to the underlying
      Close price, mapping relative price cycle amplitude to a bounded range [0.0, 1.0].

    Attributes:
        window (int): The lookback period window used for SMA calculation. Defaults to 20.
    """

    window: int = field(default=20)

    @override
    def topology(self)->str:
        return "trend"
    @override
    def name(self) -> str:
        """Generates the unique identifier string for this signal instance.

        Returns:
            str: Signal name formatted as 'dpo-w{window}'.
        """
        return f"dpo-w{self.window}"

    @override
    def __call__(
        self,
        df: i.QuotesDf.DataFrame,
        symbol: str,
    ) -> si.SignalDf.DataFrame:
        """Executes the DPO signal calculation pipeline over stock quote data.

        Calculates the Detrended Price Oscillator series, identifies baseline zero
        crossovers to assign directional signals, and normalizes the confidence score
        based on cycle magnitude relative to price.

        Args:
            df (i.QuotesDf.DataFrame): The input quotes DataFrame containing the Close price series.
            symbol (str): Ticker or symbol string corresponding to the quotes data.

        Returns:
            si.SignalDf.DataFrame: A Polars DataFrame containing the computed signal
                columns (CATEGORY, CONFIDENCE, NAME, SYMBOL, TS).
        """
        pdf = df.to_pandas()
        c = i.QuotesDf.Columns
        o = si.SignalDf.Columns

        _dpo = "dpo"

        # Initialize technical indicator
        indicator = ta.trend.DPOIndicator(
            close=pdf[c.CLOSE],
            window=self.window,
        )

        dpo_series = pl.Series(indicator.dpo()).alias(_dpo)
        df = df.insert_column(0, dpo_series)

        # Crossover Detection relative to 0 (Zero-line crossover)
        df = df.with_columns(
            (
                pl.col(_dpo)
                .sign()
                .ne(pl.col(_dpo).shift(1).sign())
            ).alias("zero_cross"),
            pl.col(_dpo).sign().alias("dpo_sign"),
        )

        zero_crossed = pl.col("zero_cross") > 0

        # Signal Direction Logic:
        # Crossover above zero -> UP (Short-term cycle above displaced moving average)
        # Crossover below zero -> DOWN (Short-term cycle below displaced moving average)
        df = df.with_columns(
            pl.when(zero_crossed & (pl.col("dpo_sign") > 0))
            .then(pl.lit(si.SignalDirection.UP))
            .when(zero_crossed & (pl.col("dpo_sign") < 0))
            .then(pl.lit(si.SignalDirection.DOWN))
            .otherwise(pl.lit(si.SignalDirection.UNSPECIFIED))
            .alias(o.CATEGORY)
        ).with_columns(pl.lit(self.name()).alias(o.NAME))

        # Confidence Calculation:
        # Measure DPO relative amplitude: |DPO| / Close.
        # A 10% displacement relative to price represents strong cyclic momentum (scaled against 0.10 factor).
        df = df.with_columns(
            (pl.col(_dpo).abs() / pl.col(c.CLOSE))
            .fill_null(0.0)
            .truediv(0.10)
            .clip(0.0, 1.0)
            .alias(o.CONFIDENCE)
        )

        out = df.select(
            *(pl.col(x) for x in [o.CATEGORY, o.CONFIDENCE, o.NAME, o.SYMBOL, o.TS])
        )
        return out



@dataclass()
class EMASignal(si.SignalInterface):
    """Generates directional trend signals using a single Exponential Moving Average (EMA).

    This class evaluates price action relative to an EMA line:
    - Crossovers where the Close price moves above the EMA trigger UP signals.
    - Crossovers where the Close price drops below the EMA trigger DOWN signals.
    - Signal confidence is normalized between 0.0 and 1.0 based on the percentage
      distance between the Close price and the EMA line.

    Attributes:
        window (int): The lookback window period for EMA calculation. Defaults to 14.
    """

    window: int = field(default=14)

    @override
    def topology(self)->str:
        return "trend"
    @override
    def name(self) -> str:
        """Generates the unique identifier string for this signal instance.

        Returns:
            str: Signal name formatted as 'ema-w{window}'.
        """
        return f"ema-w{self.window}"

    @override
    def __call__(
        self,
        df: i.QuotesDf.DataFrame,
        symbol: str,
    ) -> si.SignalDf.DataFrame:
        """Executes the EMA signal generation workflow over input quote data.

        Calculates the Exponential Moving Average, detects price crossings
        relative to the indicator baseline, and normalizes confidence by measuring
        the price displacement from the trendline.

        Args:
            df (i.QuotesDf.DataFrame): Input quotes DataFrame containing Close prices.
            symbol (str): Ticker or asset identifier string.

        Returns:
            si.SignalDf.DataFrame: A Polars DataFrame containing the resulting signal
                columns (CATEGORY, CONFIDENCE, NAME, SYMBOL, TS).
        """
        pdf = df.to_pandas()
        c = i.QuotesDf.Columns
        o = si.SignalDf.Columns

        _ema = "ema"

        # Compute Technical Indicator
        indicator = ta.trend.EMAIndicator(
            close=pdf[c.CLOSE],
            window=self.window,
        )

        ema_series = pl.Series(indicator.ema_indicator()).alias(_ema)
        df = df.insert_column(0, ema_series)

        # Crossover Detection between Close price and EMA
        df = df.with_columns(
            (
                (pl.col(c.CLOSE) - pl.col(_ema))
                .sign()
                .ne((pl.col(c.CLOSE).shift(1) - pl.col(_ema).shift(1)).sign())
            ).alias("sign_change"),
            ((pl.col(c.CLOSE) - pl.col(_ema)).sign()).alias("delta_sign"),
        )

        sign_changed = pl.col("sign_change") > 0

        # Signal Direction Logic:
        # Price crosses above EMA -> UP
        # Price crosses below EMA -> DOWN
        df = df.with_columns(
            pl.when(sign_changed & (pl.col("delta_sign") > 0))
            .then(pl.lit(si.SignalDirection.UP))
            .when(sign_changed & (pl.col("delta_sign") < 0))
            .then(pl.lit(si.SignalDirection.DOWN))
            .otherwise(pl.lit(si.SignalDirection.UNSPECIFIED))
            .alias(o.CATEGORY)
        ).with_columns(pl.lit(self.name()).alias(o.NAME))

        # Confidence Calculation:
        # Measured as relative percentage distance |Close - EMA| / EMA.
        # A 5% price separation (0.05) corresponds to max confidence (1.0).
        df = df.with_columns(
            ((pl.col(c.CLOSE) - pl.col(_ema)).abs() / pl.col(_ema))
            .fill_null(0.0)
            .truediv(0.05)
            .clip(0.0, 1.0)
            .alias(o.CONFIDENCE)
        )

        out = df.select(
            *(pl.col(x) for x in [o.CATEGORY, o.CONFIDENCE, o.NAME, o.SYMBOL, o.TS])
        )
        return out



@dataclass()
class IchimokuSignal(si.SignalInterface):
    """Generates directional trend signals using the Ichimoku Kinko Hyo indicator.

    This class evaluates trend shifts and momentum using the Ichimoku components:
    - Conversion Line (Tenkan-sen) crossing above/below Base Line (Kijun-sen) triggers UP/DOWN signals.
    - Additional confirmation is derived from price position relative to the Cloud (Kumo).
    - Confidence is computed based on the price displacement relative to the Cloud span,
      normalized between 0.0 and 1.0.

    Attributes:
        window1 (int): Conversion line period (Tenkan-sen). Defaults to 9.
        window2 (int): Base line period (Kijun-sen). Defaults to 26.
        window3 (int): Leading span B period (Senkou Span B). Defaults to 52.
        visual (bool): If True, shifts Senkou Spans forward by window2 days. Defaults to False.
    """

    window1: int = field(default=9)
    window2: int = field(default=26)
    window3: int = field(default=52)
    visual: bool = field(default=False)

    @override
    def topology(self)->str:
        return "trend"
    @override
    def name(self) -> str:
        """Generates the unique identifier string for this signal instance.

        Returns:
            str: Signal name formatted as 'ichimoku-w{window1}-{window2}-{window3}'.
        """
        return f"ichimoku-w{self.window1}-{self.window2}-{self.window3}"

    @override
    def __call__(
        self,
        df: i.QuotesDf.DataFrame,
        symbol: str,
    ) -> si.SignalDf.DataFrame:
        """Executes the Ichimoku signal calculation pipeline over stock quote data.

        Calculates Tenkan-sen, Kijun-sen, Senkou Span A, and Senkou Span B,
        identifies crossover events between Tenkan and Kijun lines, and computes
        confidence based on price distance from the Cloud boundary.

        Args:
            df (i.QuotesDf.DataFrame): Input quotes DataFrame containing High, Low, and Close columns.
            symbol (str): Ticker or symbol string corresponding to the quotes data.

        Returns:
            si.SignalDf.DataFrame: A Polars DataFrame containing the computed signal
                columns (CATEGORY, CONFIDENCE, NAME, SYMBOL, TS).
        """
        pdf = df.to_pandas()
        c = i.QuotesDf.Columns
        o = si.SignalDf.Columns

        _tenkan = "ichimoku_a"
        _kijun = "ichimoku_b"
        _span_a = "ichimoku_span_a"
        _span_b = "ichimoku_span_b"

        # Initialize technical indicator
        indicator = ta.trend.IchimokuIndicator(
            high=pdf[c.HIGH],
            low=pdf[c.LOW],
            window1=self.window1,
            window2=self.window2,
            window3=self.window3,
            visual=self.visual,
        )

        tenkan_series = pl.Series(indicator.ichimoku_conversion_line()).alias(_tenkan)
        kijun_series = pl.Series(indicator.ichimoku_base_line()).alias(_kijun)
        span_a_series = pl.Series(indicator.ichimoku_a()).alias(_span_a)
        span_b_series = pl.Series(indicator.ichimoku_b()).alias(_span_b)

        df = df.insert_column(0, tenkan_series).insert_column(0, kijun_series)
        df = df.insert_column(0, span_a_series).insert_column(0, span_b_series)

        # Detect Crossovers: Tenkan-sen (Conversion) vs Kijun-sen (Base)
        df = df.with_columns(
            (
                (pl.col(_tenkan) - pl.col(_kijun))
                .sign()
                .ne((pl.col(_tenkan).shift(1) - pl.col(_kijun).shift(1)).sign())
            ).alias("tk_cross"),
            ((pl.col(_tenkan) - pl.col(_kijun)).sign()).alias("tk_delta_sign"),
        )

        tk_crossed = pl.col("tk_cross") > 0

        # Signal Direction Logic:
        # Tenkan crosses above Kijun -> UP
        # Tenkan crosses below Kijun -> DOWN
        df = df.with_columns(
            pl.when(tk_crossed & (pl.col("tk_delta_sign") > 0))
            .then(pl.lit(si.SignalDirection.UP))
            .when(tk_crossed & (pl.col("tk_delta_sign") < 0))
            .then(pl.lit(si.SignalDirection.DOWN))
            .otherwise(pl.lit(si.SignalDirection.UNSPECIFIED))
            .alias(o.CATEGORY)
        ).with_columns(pl.lit(self.name()).alias(o.NAME))

        # Confidence Calculation:
        # Measures distance between price and the Cloud (max of Span A & Span B).
        # Distance normalized against 5% price offset bound in range [0.0, 1.0].
        df = df.with_columns(
            pl.max_horizontal(pl.col(_span_a), pl.col(_span_b)).alias("cloud_top"),
            pl.min_horizontal(pl.col(_span_a), pl.col(_span_b)).alias("cloud_bottom"),
        )

        df = df.with_columns(
            pl.when(pl.col(c.CLOSE) > pl.col("cloud_top"))
            .then((pl.col(c.CLOSE) - pl.col("cloud_top")) / pl.col(c.CLOSE))
            .when(pl.col(c.CLOSE) < pl.col("cloud_bottom"))
            .then((pl.col("cloud_bottom") - pl.col(c.CLOSE)) / pl.col(c.CLOSE))
            .otherwise(0.0)
            .fill_null(0.0)
            .truediv(0.05)
            .clip(0.0, 1.0)
            .alias(o.CONFIDENCE)
        )

        out = df.select(
            *(pl.col(x) for x in [o.CATEGORY, o.CONFIDENCE, o.NAME, o.SYMBOL, o.TS])
        )
        return out

@dataclass()
class KSTSignal(si.SignalInterface):
    """Generates directional trend signals using the Know Sure Thing (KST) Oscillator.

    This class evaluates momentum shifts by tracking crossovers between the KST line
    and its signal line across four smoothed rate-of-change (ROC) periods:
    - KST crossing above the Signal line triggers UP signals.
    - KST crossing below the Signal line triggers DOWN signals.
    - Signal confidence is normalized between 0.0 and 1.0 based on the absolute
      distance between the KST line and the Signal line.

    Attributes:
        roc1 (int): Lookback period for ROC 1. Defaults to 10.
        roc2 (int): Lookback period for ROC 2. Defaults to 15.
        roc3 (int): Lookback period for ROC 3. Defaults to 20.
        roc4 (int): Lookback period for ROC 4. Defaults to 30.
        window1 (int): SMA window period for ROC 1. Defaults to 10.
        window2 (int): SMA window period for ROC 2. Defaults to 10.
        window3 (int): SMA window period for ROC 3. Defaults to 10.
        window4 (int): SMA window period for ROC 4. Defaults to 15.
        nsig (int): Moving average window period for the signal line. Defaults to 9.
    """

    roc1: int = field(default=10)
    roc2: int = field(default=15)
    roc3: int = field(default=20)
    roc4: int = field(default=30)
    window1: int = field(default=10)
    window2: int = field(default=10)
    window3: int = field(default=10)
    window4: int = field(default=15)
    nsig: int = field(default=9)

    @override
    def topology(self)->str:
        return "trend"
    @override
    def name(self) -> str:
        """Generates the unique identifier string for this signal instance.

        Returns:
            str: Signal name formatted as 'kst-sig{nsig}'.
        """
        return f"kst-sig{self.nsig}"

    @override
    def __call__(
        self,
        df: i.QuotesDf.DataFrame,
        symbol: str,
    ) -> si.SignalDf.DataFrame:
        """Executes the KST signal calculation pipeline over stock quote data.

        Calculates the KST line and KST Signal line, detects line crossover
        events to dictate directional signals, and scales confidence based on line separation.

        Args:
            df (i.QuotesDf.DataFrame): Input quotes DataFrame containing Close price series.
            symbol (str): Ticker or symbol string corresponding to the quotes data.

        Returns:
            si.SignalDf.DataFrame: A Polars DataFrame containing the computed signal
                columns (CATEGORY, CONFIDENCE, NAME, SYMBOL, TS).
        """
        pdf = df.to_pandas()
        c = i.QuotesDf.Columns
        o = si.SignalDf.Columns

        _kst = "kst"
        _kst_sig = "kst_sig"

        # Initialize technical indicator
        indicator = ta.trend.KSTIndicator(
            close=pdf[c.CLOSE],
            roc1=self.roc1,
            roc2=self.roc2,
            roc3=self.roc3,
            roc4=self.roc4,
            window1=self.window1,
            window2=self.window2,
            window3=self.window3,
            window4=self.window4,
            nsig=self.nsig,
        )

        kst_series = pl.Series(indicator.kst()).alias(_kst)
        kst_sig_series = pl.Series(indicator.kst_sig()).alias(_kst_sig)

        df = df.insert_column(0, kst_series).insert_column(0, kst_sig_series)

        # Crossover Detection between KST and Signal line
        df = df.with_columns(
            (
                (pl.col(_kst) - pl.col(_kst_sig))
                .sign()
                .ne((pl.col(_kst).shift(1) - pl.col(_kst_sig).shift(1)).sign())
            ).alias("sign_change"),
            ((pl.col(_kst) - pl.col(_kst_sig)).sign()).alias("delta_sign"),
        )

        sign_changed = pl.col("sign_change") > 0

        # Signal Direction Logic:
        # KST crosses above Signal -> UP
        # KST crosses below Signal -> DOWN
        df = df.with_columns(
            pl.when(sign_changed & (pl.col("delta_sign") > 0))
            .then(pl.lit(si.SignalDirection.UP))
            .when(sign_changed & (pl.col("delta_sign") < 0))
            .then(pl.lit(si.SignalDirection.DOWN))
            .otherwise(pl.lit(si.SignalDirection.UNSPECIFIED))
            .alias(o.CATEGORY)
        ).with_columns(pl.lit(self.name()).alias(o.NAME))

        # Confidence Calculation:
        # Based on the absolute distance |KST - KST_SIG|.
        # A spread of 20 points represents significant momentum separation (scaled against 20.0).
        df = df.with_columns(
            (pl.col(_kst) - pl.col(_kst_sig))
            .abs()
            .fill_null(0.0)
            .truediv(20.0)
            .clip(0.0, 1.0)
            .alias(o.CONFIDENCE)
        )

        out = df.select(
            *(pl.col(x) for x in [o.CATEGORY, o.CONFIDENCE, o.NAME, o.SYMBOL, o.TS])
        )
        return out

@dataclass()
class MACDSignal(si.SignalInterface):
    """Generates directional trend signals using Moving Average Convergence Divergence (MACD).

    This class tracks momentum and trend shifts by evaluating the interaction between
    the MACD line, its Signal line, and the MACD Histogram:
    - MACD line crossing above the Signal line triggers UP signals.
    - MACD line crossing below the Signal line triggers DOWN signals.
    - Signal confidence is calculated by scaling the absolute value of the MACD
      histogram relative to the Close price, normalized to [0.0, 1.0].

    Attributes:
        window_slow (int): Period for the slow exponential moving average. Defaults to 26.
        window_fast (int): Period for the fast exponential moving average. Defaults to 12.
        window_sign (int): Period for the signal line moving average. Defaults to 9.
    """

    window_slow: int = field(default=26)
    window_fast: int = field(default=12)
    window_sign: int = field(default=9)

    @override
    def topology(self)->str:
        return "trend"
    @override
    def name(self) -> str:
        """Generates the unique identifier string for this signal instance.

        Returns:
            str: Signal name formatted as 'macd-f{window_fast}-s{window_slow}-sig{window_sign}'.
        """
        return f"macd-f{self.window_fast}-s{self.window_slow}-sig{self.window_sign}"

    @override
    def __call__(
        self,
        df: i.QuotesDf.DataFrame,
        symbol: str,
    ) -> si.SignalDf.DataFrame:
        """Executes the MACD signal calculation pipeline over stock quote data.

        Calculates the MACD line, Signal line, and MACD Histogram, identifies line
        crossovers to assign directional signals, and normalizes confidence based on
        relative histogram amplitude.

        Args:
            df (i.QuotesDf.DataFrame): Input quotes DataFrame containing Close prices.
            symbol (str): Ticker or asset identifier string.

        Returns:
            si.SignalDf.DataFrame: A Polars DataFrame containing the computed signal
                columns (CATEGORY, CONFIDENCE, NAME, SYMBOL, TS).
        """
        pdf = df.to_pandas()
        c = i.QuotesDf.Columns
        o = si.SignalDf.Columns

        _macd = "macd"
        _macd_sig = "macd_sig"
        _macd_diff = "macd_diff"

        # Compute Technical Indicator
        indicator = ta.trend.MACD(
            close=pdf[c.CLOSE],
            window_slow=self.window_slow,
            window_fast=self.window_fast,
            window_sign=self.window_sign,
        )

        macd_series = pl.Series(indicator.macd()).alias(_macd)
        macd_sig_series = pl.Series(indicator.macd_signal()).alias(_macd_sig)
        macd_diff_series = pl.Series(indicator.macd_diff()).alias(_macd_diff)

        df = df.insert_column(0, macd_series)
        df = df.insert_column(0, macd_sig_series)
        df = df.insert_column(0, macd_diff_series)

        # Detect Crossovers: MACD Line vs Signal Line (equivalent to Histogram sign change)
        df = df.with_columns(
            (
                pl.col(_macd_diff)
                .sign()
                .ne(pl.col(_macd_diff).shift(1).sign())
            ).alias("sign_change"),
            pl.col(_macd_diff).sign().alias("delta_sign"),
        )

        sign_changed = pl.col("sign_change") > 0

        # Signal Direction Logic:
        # MACD Line crosses above Signal Line (Histogram shifts positive) -> UP
        # MACD Line crosses below Signal Line (Histogram shifts negative) -> DOWN
        df = df.with_columns(
            pl.when(sign_changed & (pl.col("delta_sign") > 0))
            .then(pl.lit(si.SignalDirection.UP))
            .when(sign_changed & (pl.col("delta_sign") < 0))
            .then(pl.lit(si.SignalDirection.DOWN))
            .otherwise(pl.lit(si.SignalDirection.UNSPECIFIED))
            .alias(o.CATEGORY)
        ).with_columns(pl.lit(self.name()).alias(o.NAME))

        # Confidence Calculation:
        # Normalized relative histogram spread: |MACD Histogram| / Close.
        # A 1% histogram displacement relative to price (0.01) represents full confidence (1.0).
        df = df.with_columns(
            (pl.col(_macd_diff).abs() / pl.col(c.CLOSE))
            .fill_null(0.0)
            .truediv(0.01)
            .clip(0.0, 1.0)
            .alias(o.CONFIDENCE)
        )

        out = df.select(
            *(pl.col(x) for x in [o.CATEGORY, o.CONFIDENCE, o.NAME, o.SYMBOL, o.TS])
        )
        return out


@dataclass()
class MassIndexSignal(si.SignalInterface):
    """Generates trend reversal signals using the Mass Index indicator.

    The Mass Index identifies prospective trend reversals by detecting range
    expansions (reversal bulges). A bulge occurs when the index rises above
    the high threshold and subsequently crosses back below the low threshold.
    - Reversal bulges combined with price momentum dictate signal direction (UP or DOWN).
    - Signal confidence is normalized between 0.0 and 1.0 based on the magnitude of the Mass Index.

    Attributes:
        window_fast (int): Fast EMA window period for range calculation. Defaults to 9.
        window_slow (int): Slow EMA window period for range calculation. Defaults to 25.
        threshold_high (float): Upper threshold to establish a reversal bulge state. Defaults to 27.0.
        threshold_low (float): Lower threshold to trigger a reversal bulge completion. Defaults to 26.5.
    """

    window_fast: int = field(default=9)
    window_slow: int = field(default=25)
    threshold_high: float = field(default=27.0)
    threshold_low: float = field(default=26.5)

    @override
    def topology(self)->str:
        return "trend"
    @override
    def name(self) -> str:
        """Generates the unique identifier string for this signal instance.

        Returns:
            str: Signal name formatted as 'mass-index-f{window_fast}-s{window_slow}'.
        """
        return f"mass-index-f{self.window_fast}-s{self.window_slow}"

    @override
    def __call__(
        self,
        df: i.QuotesDf.DataFrame,
        symbol: str,
    ) -> si.SignalDf.DataFrame:
        """Executes the Mass Index signal calculation pipeline over stock quote data.

        Calculates the Mass Index series, identifies reversal bulge setups (dropping
        below the low threshold after breaching the high threshold), determines signal direction,
        and computes confidence scores.

        Args:
            df (i.QuotesDf.DataFrame): Input quotes DataFrame containing High, Low, and Close price series.
            symbol (str): Ticker or symbol string corresponding to the quotes data.

        Returns:
            si.SignalDf.DataFrame: A Polars DataFrame containing the computed signal
                columns (CATEGORY, CONFIDENCE, NAME, SYMBOL, TS).
        """
        pdf = df.to_pandas()
        c = i.QuotesDf.Columns
        o = si.SignalDf.Columns

        _mass_index = "mass_index"

        # Initialize technical indicator
        indicator = ta.trend.MassIndex(
            high=pdf[c.HIGH],
            low=pdf[c.LOW],
            window_fast=self.window_fast,
            window_slow=self.window_slow,
        )

        mass_index_series = pl.Series(indicator.mass_index()).alias(_mass_index)
        df = df.insert_column(0, mass_index_series)

        # Detect Reversal Bulge: Mass Index drops below low threshold after being above high threshold
        df = df.with_columns(
            (
                (pl.col(_mass_index).shift(1) > self.threshold_high)
                & (pl.col(_mass_index) < self.threshold_low)
            ).alias("reversal_bulge")
        )

        # Determine direction based on price movement over the fast window during bulge completion
        price_change = pl.col(c.CLOSE) - pl.col(c.CLOSE).shift(self.window_fast)
        bulge_triggered = pl.col("reversal_bulge")

        df = df.with_columns(
            pl.when(bulge_triggered & (price_change < 0))
            .then(pl.lit(si.SignalDirection.UP))  # Bearish move ending -> Bullish reversal
            .when(bulge_triggered & (price_change > 0))
            .then(pl.lit(si.SignalDirection.DOWN))  # Bullish move ending -> Bearish reversal
            .otherwise(pl.lit(si.SignalDirection.UNSPECIFIED))
            .alias(o.CATEGORY)
        ).with_columns(pl.lit(self.name()).alias(o.NAME))

        # Confidence Calculation:
        # Scale Mass Index range relative to the bulge threshold (e.g., 27.0).
        # Normalizes values between 0.0 and 1.0 using a baseline of 27.0.
        df = df.with_columns(
            pl.col(_mass_index)
            .fill_null(0.0)
            .truediv(self.threshold_high)
            .clip(0.0, 1.0)
            .alias(o.CONFIDENCE)
        )

        out = df.select(
            *(pl.col(x) for x in [o.CATEGORY, o.CONFIDENCE, o.NAME, o.SYMBOL, o.TS])
        )
        return out


@dataclass()
class PSARSignal(si.SignalInterface):
    """Generates directional trend reversal signals using the Parabolic SAR (PSAR).

    This class tracks trend flips by evaluating the position of the Parabolic SAR relative to the price:
    - PSAR flipping from above to below the Close price triggers an UP (bullish reversal) signal.
    - PSAR flipping from below to above the Close price triggers a DOWN (bearish reversal) signal.
    - Signal confidence is calculated by scaling the percentage distance between the Close price
      and the PSAR line, normalized to [0.0, 1.0].

    Attributes:
        step (float): Acceleration factor step increment. Defaults to 0.02.
        max_step (float): Maximum acceleration factor bound. Defaults to 0.2.
    """

    step: float = field(default=0.02)
    max_step: float = field(default=0.2)

    @override
    def topology(self)->str:
        return "trend"
    @override
    def name(self) -> str:
        """Generates the unique identifier string for this signal instance.

        Returns:
            str: Signal name formatted as 'psar-s{step}-m{max_step}'.
        """
        return f"psar-s{self.step}-m{self.max_step}"

    @override
    def __call__(
        self,
        df: i.QuotesDf.DataFrame,
        symbol: str,
    ) -> si.SignalDf.DataFrame:
        """Executes the Parabolic SAR signal calculation pipeline over stock quote data.

        Calculates the PSAR indicator line, detects flip events (crossovers relative
        to Close price) to assign directional signals, and computes trend confidence.

        Args:
            df (i.QuotesDf.DataFrame): Input quotes DataFrame containing High, Low, and Close columns.
            symbol (str): Ticker or asset identifier string.

        Returns:
            si.SignalDf.DataFrame: A Polars DataFrame containing the computed signal
                columns (CATEGORY, CONFIDENCE, NAME, SYMBOL, TS).
        """
        pdf = df.to_pandas()
        c = i.QuotesDf.Columns
        o = si.SignalDf.Columns

        _psar = "psar"

        # Compute Technical Indicator
        indicator = ta.trend.PSARIndicator(
            high=pdf[c.HIGH],
            low=pdf[c.LOW],
            close=pdf[c.CLOSE],
            step=self.step,
            max_step=self.max_step,
        )

        psar_series = pl.Series(indicator.psar()).alias(_psar)
        df = df.insert_column(0, psar_series)

        # Detect PSAR Flips (Price vs PSAR position changes)
        df = df.with_columns(
            (
                (pl.col(c.CLOSE) - pl.col(_psar))
                .sign()
                .ne((pl.col(c.CLOSE).shift(1) - pl.col(_psar).shift(1)).sign())
            ).alias("psar_flip"),
            ((pl.col(c.CLOSE) - pl.col(_psar)).sign()).alias("delta_sign"),
        )

        flipped = pl.col("psar_flip") > 0

        # Signal Direction Logic:
        # PSAR flips below Close price (delta_sign > 0) -> UP
        # PSAR flips above Close price (delta_sign < 0) -> DOWN
        df = df.with_columns(
            pl.when(flipped & (pl.col("delta_sign") > 0))
            .then(pl.lit(si.SignalDirection.UP))
            .when(flipped & (pl.col("delta_sign") < 0))
            .then(pl.lit(si.SignalDirection.DOWN))
            .otherwise(pl.lit(si.SignalDirection.UNSPECIFIED))
            .alias(o.CATEGORY)
        ).with_columns(pl.lit(self.name()).alias(o.NAME))

        # Confidence Calculation:
        # Relative percentage separation: |Close - PSAR| / Close.
        # A 5% separation (0.05) corresponds to max confidence (1.0).
        df = df.with_columns(
            ((pl.col(c.CLOSE) - pl.col(_psar)).abs() / pl.col(c.CLOSE))
            .fill_null(0.0)
            .truediv(0.05)
            .clip(0.0, 1.0)
            .alias(o.CONFIDENCE)
        )

        out = df.select(
            *(pl.col(x) for x in [o.CATEGORY, o.CONFIDENCE, o.NAME, o.SYMBOL, o.TS])
        )
        return out


@dataclass()
class STCSignal(si.SignalInterface):
    """Generates directional, overbought, and oversold signals using the Schaff Trend Cycle (STC).

    This class computes the STC indicator to evaluate cyclical market shifts:
    - Crossovers above the lower threshold (e.g., 20) trigger UP signals.
    - Crossovers below the upper threshold (e.g., 80) trigger DOWN signals.
    - Sustained levels above upper or below lower thresholds trigger OVERBOUGHT or OVERSOLD states.
    - Signal confidence is normalized between 0.0 and 1.0 based on indicator intensity relative to scale [0, 100].

    Attributes:
        window_fast (int): Fast EMA window period. Defaults to 23.
        window_slow (int): Slow EMA window period. Defaults to 50.
        cycle (int): Cycle calculation window length. Defaults to 10.
        smooth1 (int): First smoothing factor window length. Defaults to 3.
        smooth2 (int): Second smoothing factor window length. Defaults to 3.
        threshold_low (float): Lower threshold for oversold/bullish shift detection. Defaults to 20.0.
        threshold_high (float): Upper threshold for overbought/bearish shift detection. Defaults to 80.0.
    """

    window_fast: int = field(default=23)
    window_slow: int = field(default=50)
    cycle: int = field(default=10)
    smooth1: int = field(default=3)
    smooth2: int = field(default=3)
    threshold_low: float = field(default=20.0)
    threshold_high: float = field(default=80.0)

    @override
    def topology(self)->str:
        return "trend"
    @override
    def name(self) -> str:
        """Generates the unique identifier string for this signal instance.

        Returns:
            str: Signal name formatted as 'stc-f{window_fast}-s{window_slow}-c{cycle}'.
        """
        return f"stc-f{self.window_fast}-s{self.window_slow}-c{self.cycle}"

    @override
    def __call__(
        self,
        df: i.QuotesDf.DataFrame,
        symbol: str,
    ) -> si.SignalDf.DataFrame:
        """Executes the STC signal calculation pipeline over stock quote data.

        Calculates the Schaff Trend Cycle series, identifies directional threshold
        crossovers and extreme regime states, and computes normalized confidence scores.

        Args:
            df (i.QuotesDf.DataFrame): Input quotes DataFrame containing Close prices.
            symbol (str): Ticker or asset identifier string.

        Returns:
            si.SignalDf.DataFrame: A Polars DataFrame containing the computed signal
                columns (CATEGORY, CONFIDENCE, NAME, SYMBOL, TS).
        """
        pdf = df.to_pandas()
        c = i.QuotesDf.Columns
        o = si.SignalDf.Columns

        _stc = "stc"

        # Compute Technical Indicator
        indicator = ta.trend.STCIndicator(
            close=pdf[c.CLOSE],
            window_fast=self.window_fast,
            window_slow=self.window_slow,
            cycle=self.cycle,
            smooth1=self.smooth1,
            smooth2=self.smooth2,
        )

        stc_series = pl.Series(indicator.stc()).alias(_stc)
        df = df.insert_column(0, stc_series)

        # Crossover logic across lower and upper thresholds
        df = df.with_columns(
            (
                (pl.col(_stc).shift(1) < self.threshold_low)
                & (pl.col(_stc) >= self.threshold_low)
            ).alias("cross_up"),
            (
                (pl.col(_stc).shift(1) > self.threshold_high)
                & (pl.col(_stc) <= self.threshold_high)
            ).alias("cross_down"),
        )

        # Signal Direction Logic:
        # 1. Extreme levels dictate OVERBOUGHT / OVERSOLD
        # 2. Threshold crossover events trigger UP / DOWN direction
        # 3. Otherwise UNSPECIFIED
        df = df.with_columns(
            pl.when(pl.col(_stc) >= self.threshold_high)
            .then(pl.lit(si.SignalDirection.OVERBOUGHT))
            .when(pl.col(_stc) <= self.threshold_low)
            .then(pl.lit(si.SignalDirection.OVERSOLD))
            .when(pl.col("cross_up"))
            .then(pl.lit(si.SignalDirection.UP))
            .when(pl.col("cross_down"))
            .then(pl.lit(si.SignalDirection.DOWN))
            .otherwise(pl.lit(si.SignalDirection.UNSPECIFIED))
            .alias(o.CATEGORY)
        ).with_columns(pl.lit(self.name()).alias(o.NAME))

        # Confidence Calculation:
        # STC values range strictly between 0 and 100.
        # Confidence measures relative position displacement normalized to [0.0, 1.0].
        df = df.with_columns(
            pl.col(_stc)
            .fill_null(0.0)
            .clip(0.0, 100.0)
            .truediv(100.0)
            .alias(o.CONFIDENCE)
        )

        out = df.select(
            *(pl.col(x) for x in [o.CATEGORY, o.CONFIDENCE, o.NAME, o.SYMBOL, o.TS])
        )
        return out


@dataclass()
class TRIXSignal(si.SignalInterface):
    """Generates directional trend signals using the TRIX (Triple Exponential Average) indicator.

    This class computes the 1-day rate-of-change of a triple exponentially smoothed
    moving average to filter out market noise and identify trend shifts:
    - Zero-line crossovers where TRIX turns positive trigger UP signals.
    - Zero-line crossovers where TRIX turns negative trigger DOWN signals.
    - Signal confidence is calculated by scaling the absolute TRIX value,
      normalized between 0.0 and 1.0.

    Attributes:
        window (int): The lookback window period for triple exponential smoothing. Defaults to 15.
    """

    window: int = field(default=15)

    @override
    def topology(self)->str:
        return "trend"
    @override
    def name(self) -> str:
        """Generates the unique identifier string for this signal instance.

        Returns:
            str: Signal name formatted as 'trix-w{window}'.
        """
        return f"trix-w{self.window}"

    @override
    def __call__(
        self,
        df: i.QuotesDf.DataFrame,
        symbol: str,
    ) -> si.SignalDf.DataFrame:
        """Executes the TRIX signal calculation pipeline over stock quote data.

        Calculates the TRIX oscillator series, identifies zero-line crossover
        events to assign directional signals, and computes normalized confidence scores.

        Args:
            df (i.QuotesDf.DataFrame): Input quotes DataFrame containing Close prices.
            symbol (str): Ticker or asset identifier string.

        Returns:
            si.SignalDf.DataFrame: A Polars DataFrame containing the computed signal
                columns (CATEGORY, CONFIDENCE, NAME, SYMBOL, TS).
        """
        pdf = df.to_pandas()
        c = i.QuotesDf.Columns
        o = si.SignalDf.Columns

        _trix = "trix"

        # Compute Technical Indicator
        indicator = ta.trend.TRIXIndicator(
            close=pdf[c.CLOSE],
            window=self.window,
        )

        trix_series = pl.Series(indicator.trix()).alias(_trix)
        df = df.insert_column(0, trix_series)

        # Detect Zero-Line Crossings
        df = df.with_columns(
            (
                pl.col(_trix)
                .sign()
                .ne(pl.col(_trix).shift(1).sign())
            ).alias("zero_cross"),
            pl.col(_trix).sign().alias("trix_sign"),
        )

        zero_crossed = pl.col("zero_cross") > 0

        # Signal Direction Logic:
        # Zero-line crossover moving positive -> UP
        # Zero-line crossover moving negative -> DOWN
        # Otherwise UNSPECIFIED
        df = df.with_columns(
            pl.when(zero_crossed & (pl.col("trix_sign") > 0))
            .then(pl.lit(si.SignalDirection.UP))
            .when(zero_crossed & (pl.col("trix_sign") < 0))
            .then(pl.lit(si.SignalDirection.DOWN))
            .otherwise(pl.lit(si.SignalDirection.UNSPECIFIED))
            .alias(o.CATEGORY)
        ).with_columns(pl.lit(self.name()).alias(o.NAME))

        # Confidence Calculation:
        # TRIX values typically oscillate closely around zero (e.g., within +/- 1.0%).
        # Absolute value scaled against a factor of 0.5% (0.005) and clipped to [0.0, 1.0].
        df = df.with_columns(
            pl.col(_trix)
            .abs()
            .fill_null(0.0)
            .truediv(0.005)
            .clip(0.0, 1.0)
            .alias(o.CONFIDENCE)
        )

        out = df.select(
            *(pl.col(x) for x in [o.CATEGORY, o.CONFIDENCE, o.NAME, o.SYMBOL, o.TS])
        )
        return out


@dataclass()
class VortexSignal(si.SignalInterface):
    """Generates directional trend signals using the Vortex Indicator (VI).

    This class computes positive (+VI) and negative (-VI) vortex movements
    to identify the initiation of directional price trends:
    - +VI crossing above -VI triggers UP signals.
    - -VI crossing above +VI triggers DOWN signals.
    - Signal confidence is normalized between 0.0 and 1.0 based on the absolute
      spread between +VI and -VI relative to a max threshold offset.

    Attributes:
        window (int): The lookback window period for parameter calculation. Defaults to 14.
    """

    window: int = field(default=14)

    @override
    def topology(self)->str:
        return "trend"
    @override
    def name(self) -> str:
        """Generates the unique identifier string for this signal instance.

        Returns:
            str: Signal name formatted as 'vortex-w{window}'.
        """
        return f"vortex-w{self.window}"

    @override
    def __call__(
        self,
        df: i.QuotesDf.DataFrame,
        symbol: str,
    ) -> si.SignalDf.DataFrame:
        """Executes the Vortex Indicator signal calculation pipeline over stock quote data.

        Calculates +VI and -VI series, identifies line crossover events to dictating
        trend direction, and scales confidence based on line separation.

        Args:
            df (i.QuotesDf.DataFrame): Input quotes DataFrame containing High, Low, and Close prices.
            symbol (str): Ticker or asset identifier string.

        Returns:
            si.SignalDf.DataFrame: A Polars DataFrame containing the computed signal
                columns (CATEGORY, CONFIDENCE, NAME, SYMBOL, TS).
        """
        pdf = df.to_pandas()
        c = i.QuotesDf.Columns
        o = si.SignalDf.Columns

        _vip = "vip"
        _vin = "vin"

        # Compute Technical Indicator
        indicator = ta.trend.VortexIndicator(
            high=pdf[c.HIGH],
            low=pdf[c.LOW],
            close=pdf[c.CLOSE],
            window=self.window,
        )

        vip_series = pl.Series(indicator.vortex_indicator_pos()).alias(_vip)
        vin_series = pl.Series(indicator.vortex_indicator_neg()).alias(_vin)

        df = df.insert_column(0, vip_series).insert_column(0, vin_series)

        # Crossover Detection between +VI (vip) and -VI (vin)
        df = df.with_columns(
            (
                (pl.col(_vip) - pl.col(_vin))
                .sign()
                .ne((pl.col(_vip).shift(1) - pl.col(_vin).shift(1)).sign())
            ).alias("sign_change"),
            ((pl.col(_vip) - pl.col(_vin)).sign()).alias("delta_sign"),
        )

        sign_changed = pl.col("sign_change") > 0

        # Signal Direction Logic:
        # +VI crosses above -VI -> UP
        # -VI crosses above +VI -> DOWN
        # Otherwise UNSPECIFIED
        df = df.with_columns(
            pl.when(sign_changed & (pl.col("delta_sign") > 0))
            .then(pl.lit(si.SignalDirection.UP))
            .when(sign_changed & (pl.col("delta_sign") < 0))
            .then(pl.lit(si.SignalDirection.DOWN))
            .otherwise(pl.lit(si.SignalDirection.UNSPECIFIED))
            .alias(o.CATEGORY)
        ).with_columns(pl.lit(self.name()).alias(o.NAME))

        # Confidence Calculation:
        # Measured as absolute spread |+VI - -VI|.
        # Standard Vortex lines oscillate around 1.0; a spread of 0.4 represents a strong trend.
        df = df.with_columns(
            (pl.col(_vip) - pl.col(_vin))
            .abs()
            .fill_null(0.0)
            .truediv(0.4)
            .clip(0.0, 1.0)
            .alias(o.CONFIDENCE)
        )

        out = df.select(
            *(pl.col(x) for x in [o.CATEGORY, o.CONFIDENCE, o.NAME, o.SYMBOL, o.TS])
        )
        return out


@dataclass()
class WMASignal(si.SignalInterface):
    """Generates directional trend signals using a Weighted Moving Average (WMA).

    This class evaluates price action relative to a WMA baseline:
    - Crossovers where the Close price moves above the WMA trigger UP signals.
    - Crossovers where the Close price drops below the WMA trigger DOWN signals.
    - Signal confidence is normalized between 0.0 and 1.0 based on the percentage
      distance between the Close price and the WMA line.

    Attributes:
        window (int): The lookback window period for WMA calculation. Defaults to 9.
    """

    window: int = field(default=9)

    @override
    def topology(self)->str:
        return "trend"
    @override
    def name(self) -> str:
        """Generates the unique identifier string for this signal instance.

        Returns:
            str: Signal name formatted as 'wma-w{window}'.
        """
        return f"wma-w{self.window}"

    @override
    def __call__(
        self,
        df: i.QuotesDf.DataFrame,
        symbol: str,
    ) -> si.SignalDf.DataFrame:
        """Executes the WMA signal generation workflow over input quote data.

        Calculates the Weighted Moving Average, detects price crossing events
        relative to the WMA baseline, and normalizes confidence by measuring
        price displacement from the trendline.

        Args:
            df (i.QuotesDf.DataFrame): Input quotes DataFrame containing Close prices.
            symbol (str): Ticker or asset identifier string.

        Returns:
            si.SignalDf.DataFrame: A Polars DataFrame containing the computed signal
                columns (CATEGORY, CONFIDENCE, NAME, SYMBOL, TS).
        """
        pdf = df.to_pandas()
        c = i.QuotesDf.Columns
        o = si.SignalDf.Columns

        _wma = "wma"

        # Compute Technical Indicator
        indicator = ta.trend.WMAIndicator(
            close=pdf[c.CLOSE],
            window=self.window,
        )

        wma_series = pl.Series(indicator.wma()).alias(_wma)
        df = df.insert_column(0, wma_series)

        # Crossover Detection between Close price and WMA
        df = df.with_columns(
            (
                (pl.col(c.CLOSE) - pl.col(_wma))
                .sign()
                .ne((pl.col(c.CLOSE).shift(1) - pl.col(_wma).shift(1)).sign())
            ).alias("sign_change"),
            ((pl.col(c.CLOSE) - pl.col(_wma)).sign()).alias("delta_sign"),
        )

        sign_changed = pl.col("sign_change") > 0

        # Signal Direction Logic:
        # Price crosses above WMA -> UP
        # Price crosses below WMA -> DOWN
        # Otherwise UNSPECIFIED
        df = df.with_columns(
            pl.when(sign_changed & (pl.col("delta_sign") > 0))
            .then(pl.lit(si.SignalDirection.UP))
            .when(sign_changed & (pl.col("delta_sign") < 0))
            .then(pl.lit(si.SignalDirection.DOWN))
            .otherwise(pl.lit(si.SignalDirection.UNSPECIFIED))
            .alias(o.CATEGORY)
        ).with_columns(pl.lit(self.name()).alias(o.NAME))

        # Confidence Calculation:
        # Relative percentage distance: |Close - WMA| / WMA.
        # A 5% price separation (0.05) maps to full confidence (1.0).
        df = df.with_columns(
            ((pl.col(c.CLOSE) - pl.col(_wma)).abs() / pl.col(_wma))
            .fill_null(0.0)
            .truediv(0.05)
            .clip(0.0, 1.0)
            .alias(o.CONFIDENCE)
        )

        out = df.select(
            *(pl.col(x) for x in [o.CATEGORY, o.CONFIDENCE, o.NAME, o.SYMBOL, o.TS])
        )
        return out
