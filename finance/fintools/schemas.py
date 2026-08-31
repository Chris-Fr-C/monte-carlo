from enum import StrEnum
import pandera as pa
import pandera.polars as pat
import datetime
import pendulum
from typing import Annotated

type Symbol = str
"""Symbol of a stock. Example: NSNX"""


class Currency(StrEnum):
    """Currency value. 3 letter char."""
    EUR="EUR"
    CHF="CHF"
    USD="USD"

class Quotes(pat.DataFrameModel):
    ts: pa.typing.Series[Annotated[pendulum.DateTime, True, "ms", None]]
    symbol: pa.typing.Series[str]
    currency: pa.typing.Series[str]
    open: pa.typing.Series[float]
    high: pa.typing.Series[float]
    low: pa.typing.Series[float]
    close: pa.typing.Series[float]
    volume: pa.typing.Series[int]
    dividends: pa.typing.Series[float]
    stock_splits: pa.typing.Series[float]
