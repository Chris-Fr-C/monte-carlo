from enum import StrEnum
import pandera.polars as pa
import pandera.typing.polars as pat
import pendulum
from typing import Annotated

type Symbol = str
"""Symbol of a stock. Example: NSNX"""


class Currency(StrEnum):
    """Currency value. 3 letter char."""
    EUR="EUR"
    CHF="CHF"
    USD="USD"

class Quotes(pa.DataFrameModel):
    ts: pat.Series[Annotated[pendulum.DateTime, True, "ms", None]]
    symbol: pat.Series[str]
    currency: pat.Series[str]
    open: pat.Series[float]
    high: pat.Series[float]
    low: pat.Series[float]
    close: pat.Series[float]
    volume: pat.Series[int]
    dividends: pat.Series[float]
    stock_splits: pat.Series[float]
