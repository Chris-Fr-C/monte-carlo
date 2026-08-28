from dataclasses import dataclass
from typing import Protocol, final
import pendulum
import polars as pl
import fintools.interface as i
from enum import StrEnum

class SignalDirection(StrEnum):
    UNSPECIFIED="unspecified"
# Directional Trend
    UP = "up"
    DOWN = "down"

    # Volatility Dynamics
    VOLATILITY_EXPANSION = "expansion"
    VOLATILITY_CONTRACTION = "contraction"

    # Momentum Dynamics
    MOMENTUM_ACCELERATION = "acceleration"  # Rapidly increasing velocity (e.g., RSI/MACD histogram expansion)
    MOMENTUM_DECELERATION = "deceleration"  # Velocity slowing down (e.g., trend continues but momentum weakens)
    OVERBOUGHT = "overbought"              # Momentum overextended high (e.g., RSI > 70, Williams %R > -20)
    OVERSOLD = "oversold"                  # Momentum overextended low (e.g., RSI < 30, Williams %R < -80)
    BULLISH_DIVERGENCE = "bullish_divergence"  # Price lower low, momentum higher low
    BEARISH_DIVERGENCE = "bearish_divergence"  # Price higher high, momentum lower high

type NormedFloat = float
"""Float between 0 and 1."""

@final
class SignalDf():
    DataFrame = pl.DataFrame
    @final
    class Columns():
        TS="ts"
        CATEGORY="category"
        CONFIDENCE="confidence"
        SYMBOL: str = "symbol"
        NAME: str = "name"
        TOPOLOGY : str="topology"
        """Trend, momentum, volatility ..."""

class SignalInterface():
    def name(self)->str:
        ...

    def topology(self)->str:
        ...
    def __call__(self,
                 df: i.QuotesDf.DataFrame,
                 symbol: str,
                 )->SignalDf.DataFrame:
        # Last point will be evaluated for the signal in any case.
        ...
