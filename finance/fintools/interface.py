from enum import StrEnum
from typing import final
import polars as pl



type Symbol = str
"""Symbol of a stock. Example: NSNX"""


class Currency(StrEnum):
    """Currency value. 3 letter char."""
    EUR="EUR"
    CHF="CHF"
    USD="USD"

@final
class QuotesDf():
    type DataFrame = pl.DataFrame

    @final
    class Columns:
        TS="ts"
        """Timestamp"""
        SYMBOL="symbol"
        CURRENCY="currency"
        OPEN="open"
        CLOSE="close"
        HIGH="high"
        LOW="low"
        VOLUME="volume"
        DIVIDENDS="dividends"
        STOCK_SPLITS="stock_splits"
