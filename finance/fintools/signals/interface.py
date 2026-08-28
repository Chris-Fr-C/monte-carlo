from dataclasses import dataclass
from typing import Protocol, final
import pendulum
import polars as pl
import fintools.interface as i
from enum import StrEnum

class SignalDirection(StrEnum):
    UNSPECIFIED="unspecified"
    UP = "up"
    DOWN= "down"
    INVERSION = "inversion"


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

class SignalInterface():
    def name(self)->str:
        ...
    def __call__(self,
                 df: i.QuotesDf.DataFrame,
                 symbol: str,
                 )->SignalDf.DataFrame:
        # Last point will be evaluated for the signal in any case.
        ...
